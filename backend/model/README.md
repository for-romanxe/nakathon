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

어댑터 `ml/adapters/gemma-12b-v2`(42MB)는 2026-11-14에 쓰기로 정했고 저장소에는 없다. 근거와 측정값은 `ml/eval/v2/README.md`에 있다. 파일이 없으면 둘 중 하나로 한다.
- `--adapter-path adapters/gemma-12b-v2`를 빼고 띄운다. 코드는 그대로 동작한다. 그때의 측정값은 `ml/eval/v2/README.md`의 "규칙 지시문" 열이다.
- 직접 학습한다: `python3 ml/data/build_v2.py` 뒤에 `(cd ml && .venv/bin/python train_v2.py -c train_v2.yaml)`. 모델 서버를 먼저 내린다. M5 Pro 24GB에서 약 80분 걸렸다. 다시 학습한 결과가 같은 값을 내는지는 확인하지 않았다.

어댑터는 지금 코드의 지시문(`client.py`)으로 학습했다. 지시문을 바꾸면 어댑터와 어긋날 수 있으니 `ml/eval/run_eval2.py`로 다시 잰다.

모델 파일은 Hugging Face `mlx-community/gemma-4-12B-it-qat-OptiQ-4bit`(디스크 8.4GB)를 `ml/models/` 아래에 받는다. 서버 프로세스는 M5 Pro 24GB에서 메모리 약 12GB(최대 13GB)를 썼다(2026-11-14 측정). 모델을 고른 근거는 `ml/eval/README.md`.
