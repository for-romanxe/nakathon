# backend — AI 담당 구성요소 (모델 클라이언트·검증기)

백엔드 API 안내는 `backend/README.md`(백엔드 담당). 이 문서는 AI 담당 몫만 다룬다:

- `contracts.py` — `contracts/*.json` 로더 + 최소 스키마 검사
- `model/client.py` — 모델 호출 3함수 `extract_symptoms / score_mood / explain`. `MODEL=mock`(기본) 또는 `MODEL=live`. 실패는 전부 `ModelOutputError`로 나온다. 모델 서버에 닿지 못한 경우는 그 하위 클래스 `ModelUnavailableError`
- `mock/symptom.json`, `mock/mood.json` — 키워드 매치. 행 순서가 우선순위(급한 코드가 위), 마지막 행이 기본값. 영문 키워드는 단어 시작에서만 맞고, 한글 키워드는 구체적으로 적는다
- `mock/explanation.json` — `condition_id`로 고른다. `explain`은 넘겨받은 후보 순서대로 찾고, 시나리오가 없는 후보는 그 후보에 맞는 일반 문장을 돌려준다
- live 모드에서 코드가 정하는 것: 설명의 `cites`는 모델이 문단 번호로 답하고 코드가 id를 붙인다. `category`는 `condition_id`로 상태 목록에서 가져온다. 증상의 `onset`·`worse_when`이 목록 밖이면 `unknown`으로 둔다(`codes`는 목록 밖이면 거부)
- 평가 질문셋 30문항과 결과: `ml/eval/README.md`
- `model/pipeline.py` — `explain_verified(level, findings, condition_candidates, paragraphs, lang)`. 설명 생성 → 검증 → 폐기되면 걸린 표현을 알려 주고 한 번 더(상한 2회) → 두 번 폐기되면 판단 보류. 반환은 `{explanation | None, hold, verified, runs[{n, ok, fails, note}]}`이고 이벤트의 `explanation`·`runs`·`verified`에 그대로 넣는다. **백엔드는 설명이 필요할 때 `explain` 대신 이 함수를 부른다**
- `verify.py` — 설명 검증기 5검사 (`numbers cites level schema wording`). 숫자는 findings의 value·baseline·z만, 그 지표의 화면 표시 자릿수(`contracts/enums.json`의 `decimals`, z는 1자리)보다 거칠지 않게 반올림한 것만 통과. 부호를 적으면 부호도 맞아야 한다. 결과의 `detail`에 검사별로 걸린 표현이 들어가고, `note`는 그것을 한 줄로 적은 것이다(예: `numbers: 12; wording: 입니다`). 모델 문장에는 시각·분량 같은 다른 숫자를 쓰지 않는다

```sh
# 테스트 (표준 라이브러리만 필요)
python3 -m unittest discover -s backend/tests -t .
# mock 지연 끄기
MOCK_DELAY=0 python3 -c "from backend.model import client; print(client.extract_symptoms('어지러워요','ko'))"
# live: 모델 서버를 띄우고(ml/.venv, 포트 8080) MODEL=live 로 호출
(cd ml && .venv/bin/python -m mlx_lm server --model models/<모델> --adapter-path adapters/<어댑터> --port 8080)
MODEL=live python3 -c "from backend.model import client; print(client.extract_symptoms('어지러워요','ko'))"
# MODEL_URL 기본 http://127.0.0.1:8080 (끝에 /v1 을 붙여도 된다). MODEL_NAME 기본 default_model = mlx_lm.server 가 띄울 때 받은 모델
```
