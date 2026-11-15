# 평가셋 v2 — test · gemma-12b-base-rules · 2026-11-14T15:22

```
symptom  model 57/60 (exact 57/60)  keyword 18/60  | ko 33/34  en 24/26
  by kind: context 6/6  hard_negative 9/10  indirect 7/7  mixed 8/8  multi 7/8  negation 5/6  none 5/5  paraphrase 6/6  plain 4/4
  urgent codes (chest pain, breathlessness, crisis) caught: model 18/18  keyword 5/18
  schema errors: 0
mood     in range 24/24  schema errors 0
latency  symptom median 2.5s  max 3.0s  (n=60)
latency  mood median 1.8s  max 2.4s  (n=24)
```

## 증상: 틀린 문항

| # | 종류 | 문장 | 기대 | 금지 | 모델이 낸 코드 |
|---|---|---|---|---|---|
| ST-008 | hard_negative | 창밖으로 지구가 보이는데 가슴이 벅차서 한동안 말이 안 나왔어요. | none | chest_pain, shortness_of_breath | chest_pain |
| ST-019 | negation | No nausea at all, but the cabin seems to swing sideways whenever I look up from the tablet. | dizziness | nausea | vision_change |
| ST-029 | multi | Throat feels raw, I'm coughing, and I'm completely run-down even after an early night. | congestion, fatigue | - | fatigue |

## 기분: 범위 밖 문항

| # | 문장 | 기대 범위 | 모델 (mood / fatigue / stress) |
|---|---|---|---|

## 설명: 문단과 답을 나란히 (뜻이 맞는지는 사람이 읽어야 한다)

