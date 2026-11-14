# backend

FastAPI + SQLite (백엔드 담당). 지금 들어 있는 것은 AI 담당 몫만:

- `contracts.py` — `contracts/*.json` 로더 + 최소 스키마 검사
- `model/client.py` — 모델 호출 3함수 `extract_symptoms / score_mood / explain`. `MODEL=mock`(기본) 또는 `MODEL=live`
- `mock/*.json` — mock 시나리오. 키워드 매치, 마지막 행이 기본값. 시나리오 추가는 여기에
- `verify.py` — 설명 검증기 5검사 (`numbers cites level schema wording`)

```sh
# 테스트 (표준 라이브러리만 필요)
python3 -m unittest discover -s backend/tests -t .
# mock 지연 끄기
MOCK_DELAY=0 python3 -c "from backend.model import client; print(client.extract_symptoms('어지러워요','ko'))"
# live: MODEL=live MODEL_URL=http://127.0.0.1:8080 MODEL_NAME=<served name>
```
