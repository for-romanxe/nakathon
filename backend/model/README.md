# backend — AI 담당 구성요소 (모델 클라이언트·검증기)

백엔드 API 안내는 `backend/README.md`(백엔드 담당). 이 문서는 AI 담당 몫만 다룬다:

- `contracts.py` — `contracts/*.json` 로더 + 최소 스키마 검사
- `model/client.py` — 모델 호출 3함수 `extract_symptoms / score_mood / explain`. `MODEL=mock`(기본) 또는 `MODEL=live`. 실패는 전부 `ModelOutputError`로 나온다. 모델 서버에 닿지 못한 경우는 그 하위 클래스 `ModelUnavailableError`
- `mock/symptom.json`, `mock/mood.json` — 키워드 매치. 행 순서가 우선순위(급한 코드가 위), 마지막 행이 기본값. 영문 키워드는 단어 시작에서만 맞고, 한글 키워드는 구체적으로 적는다
- `mock/explanation.json` — `condition_id`로 고른다. `explain`은 넘겨받은 후보 순서대로 찾고, 시나리오가 없는 후보는 그 후보에 맞는 일반 문장을 돌려준다
- live 모드에서 코드가 정하는 것: 설명의 `cites`는 모델이 문단 번호로 답하고 코드가 id를 붙인다. `category`는 `condition_id`로 상태 목록에서 가져온다. 증상의 `onset`·`worse_when`이 목록 밖이면 `unknown`으로 둔다(`codes`는 목록 밖이면 거부)
- `model/explain_prompt.json` — 설명 프롬프트. 출력 언어(ko·en)별로 지시문 한 벌과 예시 2개를 둔다. 예시는 앞선 대화로 들어가고, 예시 답은 검증기를 통과해야 한다(테스트로 확인). 후보가 여럿이면 첫 번째 후보를 우선하게 적혀 있다
- 평가 질문셋 30문항과 결과: `ml/eval/README.md`
- `model/pipeline.py` — `explain_verified(level, findings, condition_candidates, paragraphs, lang)`. 설명 생성 → 검증 → 폐기되면 걸린 표현을 알려 주고 한 번 더(상한 2회) → 두 번 폐기되면 판단 보류. 반환은 `{explanation | None, hold, verified, runs[{n, ok, fails, note}]}`이고 이벤트의 `explanation`·`runs`·`verified`에 그대로 넣는다. **백엔드는 설명이 필요할 때 `explain` 대신 이 함수를 부른다**
- `model/pipeline.py`의 `adjustment_reason(target, level, findings, evidence, lang)` — 우주선 조정(이슈 #47) 한 건에 붙일 이유. 근거 문단은 `model/adjustment_evidence.json` 표가 정하고 모델은 이유 문장만 쓴다. 아래 "우주선 조정 이유" 참고
- `verify.py` — 설명 검증기 5검사 (`numbers cites level schema wording`). 숫자는 findings의 value·baseline·z만, 그 지표의 화면 표시 자릿수(`contracts/enums.json`의 `decimals`, z는 1자리)보다 거칠지 않게 반올림한 것만 통과. 부호를 적으면 부호도 맞아야 한다. 결과의 `detail`에 검사별로 걸린 표현이 들어가고, `note`는 그것을 한 줄로 적은 것이다(예: `numbers: 12; wording: 입니다`). 모델 문장에는 시각·분량 같은 다른 숫자를 쓰지 않는다

```sh
# 테스트 (표준 라이브러리만 필요)
python3 -m unittest discover -s backend/tests -t .
# mock 지연 끄기
MOCK_DELAY=0 python3 -c "from backend.model import client; print(client.extract_symptoms('어지러워요','ko'))"
# live: 모델 서버를 띄우고(ml/.venv, 포트 8080) MODEL=live 로 호출. 모델은 Gemma 4 12B(4비트) + 행사 중 학습한 어댑터, thinking 은 끈다
(cd ml && .venv/bin/python -m mlx_lm server --model models/gemma-4-12B-it-qat-OptiQ-4bit --adapter-path adapters/gemma-12b-v2 --chat-template-args '{"enable_thinking":false}' --port 8080)
MODEL=live python3 -c "from backend.model import client; print(client.extract_symptoms('어지러워요','ko'))"
# MODEL_URL 기본 http://127.0.0.1:8080 (끝에 /v1 을 붙여도 된다). MODEL_NAME 기본 default_model = mlx_lm.server 가 띄울 때 받은 모델
```

어댑터 `ml/adapters/gemma-12b-v2`(42MB)는 2026-11-14에 쓰기로 정했고 저장소에 들어 있다(`adapters.safetensors` + `adapter_config.json`, 1500회 학습한 최종본. 중간 저장본은 올리지 않는다). 받으면 위 명령이 그대로 동작한다. 근거와 측정값은 `ml/eval/v2/README.md`에 있다.
- 어댑터 없이 돌리려면 `--adapter-path adapters/gemma-12b-v2`를 빼고 띄운다. 코드는 그대로 동작한다. 그때의 측정값은 `ml/eval/v2/README.md`의 "규칙 지시문" 열이다.
- 다시 학습하려면: 학습셋을 만든 커밋(`1cde53e`)에서 `python3 ml/data/build_v2.py`로 학습셋을 만든 뒤 `(cd ml && .venv/bin/python train_v2.py -c train_v2.yaml)`. 모델 서버를 먼저 내린다. M5 Pro 24GB에서 약 80분 걸렸다. 다시 학습한 결과가 같은 값을 내는지는 확인하지 않았다.

어댑터는 부위(`locations`) 문단을 넣기 전의 지시문으로 학습했다. 부위 문단을 넣은 지금 지시문으로는 다시 재서 확인했다(`ml/eval/v2/README.md`). 지금 코드로 학습셋을 다시 만들면 지시문은 부위를 묻는데 정답에는 부위가 없어서 `train_v2.py`가 멈춘다. 지시문을 더 바꾸면 `ml/eval/run_eval2.py`로 다시 잰다.

모델 파일은 Hugging Face `mlx-community/gemma-4-12B-it-qat-OptiQ-4bit`(디스크 8.4GB)를 `ml/models/` 아래에 받는다. 서버 프로세스는 M5 Pro 24GB에서 메모리 약 12GB(최대 13GB)를 썼다(2026-11-14 측정). 모델을 고른 근거는 `ml/eval/README.md`.

## 맥 한 대에서 전부 돌리기 (2026-11-14 확인)

```sh
# 1) 모델 서버: 위의 live 명령 (포트 8080)
# 2) 근거 파일: 없으면 설명 없이 보류로 끝난다
python3 ml/knowledge/export_evidence.py ko > data/evidence-ko.json
# 3) 백엔드
MODEL=live CREW_HEALTH_EVIDENCE=data/evidence-ko.json python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# 4) 프론트 (http://localhost:5173)
(cd frontend && npm install && printf 'VITE_USE_FIXTURES=false\n' > .env.development.local && npm run dev)
```

M5 Pro 24GB에서 이 구성으로 보고 6건을 HTTP로 끝까지 보냈다(모델은 어댑터 포함, 문단은 한국어). 급하지 않은 5건은 모두 설명이 검사 5개를 통과했고(1건은 두 번째 실행에서), 가슴 통증은 모델을 건너뛰고 경보가 됐다. 연달아 보낼 때 증상 추출은 2~3초, 설명은 6~7초였다.

**쉬었다 보내면 느리다.** 맥의 메모리가 꽉 찬 상태(스왑 30GB 중 29GB 사용)에서, 연달아 보낸 요청은 2초대였지만 12초 넘게 쉰 뒤의 요청은 38~58초 걸렸다(5번). 3초 쉬면 4초, 6초 쉬면 7.5초였다. 쉬는 동안 맥이 모델 메모리를 압축하는 것으로 보인다(서버 12GB 중 8.9GB가 압축돼 있었다). 2초마다 한 토큰짜리 요청을 보내 두면 40초 쉰 뒤에도 2초에 답했지만, 다른 프로그램이 메모리를 쓸 때는 그 요청 자체가 멈췄다(26분 동안 13번, 17~53초). 시연 전에 다른 프로그램을 닫아 메모리를 비우고, 직전에 한 번 호출해 둔다. 메모리를 비운 상태에서 다시 재서 확인하지는 않았다.

## 우주선 조정 이유 (이슈 #47, 2026-11-15)

조정할지, 무엇을 얼마나 바꿀지는 규칙이 정한다. 이 함수는 그 조정 카드에 붙일 이유 문장과 근거 문단 id 만 돌려준다.

```python
from backend import event_flow
from backend.model import pipeline

evidence = event_flow.load_evidence()            # CREW_HEALTH_EVIDENCE 가 가리키는 근거 파일
out = pipeline.adjustment_reason("lighting", "caution", findings, evidence, "ko")      # target: lighting | schedule
# {"reason": "…어요. …어요." | None, "cite_ids": ["hrp:sleep-01#p1", "hrp:sleep-02#p1"], "hold": False, "verified": 5, "runs": [...]}
```

- `cite_ids`는 표가 정한 문단이라 모델과 무관하다. 조정을 만들 때 바로 저장하면 되고, 모델 답을 기다릴 필요가 없다.
- `reason`은 설명과 같은 길(생성 → 5검사 → 한 번 더)을 거친 문장이다. 통과하지 못했거나 모델 서버에 닿지 못하면 `None`이고 `hold`가 `True`다. 그때는 규칙이 쓴 수치 문장과 `cite_ids`만 보여 주면 된다. 조정 자체는 이유 없이도 적용된다.
- 예외를 던지지 않는다. 근거 파일을 안 줬거나 표에 없는 `target`이면 모델을 부르지 않고 `cite_ids`가 빈 보류로 끝난다.
- `findings`는 이벤트의 `findings`와 같은 모양이다. `level`은 그날 규칙이 낸 단계를 그대로 넘긴다.
- 두절 중 "승인 없이 적용, 거부 가능"은 백엔드 정책이고 이 함수는 달라지지 않는다. 거부 처리에는 모델을 쓰지 않는다.
- `MODEL=mock`에서도 문장이 나온다. 이번에 mock 설명이 받은 문단을 인용하도록 고쳤다(전에는 없는 문단 id 를 인용해 실제 근거 파일과 함께 쓰면 항상 보류였다).
- 어느 문단을 어느 조정에 붙일지는 AI가 고른 초안이고 사람이 검토하지 않았다. 일정 조정에는 수면 문단을 쓴다. 심박변이 문단(`lit:card-09#p2`)은 "변화가 작고 연구마다 일정하지 않다"고 적혀 있어 일정을 바꾸는 근거로 쓰지 않았다.

## 경보 절차 단계 (이슈 #47, 2026-11-15)

```python
out = pipeline.procedure_steps("cardiac_emergency", evidence, "ko")
# {"available": True, "steps": [{"step_id": "oxygen", "text": "산소 마스크로 산소를 주세요.", "cite_id": "nasa:card-10#p1", "kind": "treatment"}, ...5개]}
```

- 모델을 부르지 않는다. 단계와 근거 문단은 `model/procedure_steps.json`에 고정돼 있고 지금은 가슴 통증 하나다.
- 단계가 가리키는 문단이 근거 파일에 하나라도 없거나 그 상태의 절차가 없으면 `{"available": False, "steps": []}`다. 출처를 열 수 없는 단계는 보여 주지 않는다. 문단을 더했으므로 근거 파일을 다시 만들어야 한다(`ml/knowledge/README.md`).
- `kind`: `treatment`(환자에게 하는 처치, 두 사람 동의 후보) · `record`(묻고 재서 적는 일) · `cmo`(의료 장비를 쓰는 진찰) · `contact`(연락). 어느 단계에 두 사람 동의를 걸지는 백엔드가 정한다.
- 마지막 단계는 "지상의 담당 의사에게 연락"이다. 두절 중에는 할 수 없으므로 화면에서 어떻게 보일지(예: 지구 보고서에 기록)는 백엔드·프론트가 정한다.
- 단계는 2001년판 점검표를 AI가 요약한 것이고 원문이 아니다. 약이 들어간 갈래는 넣지 않았다. 자세한 한계는 `ml/knowledge/README.md`의 "가슴 통증 절차 문단".

