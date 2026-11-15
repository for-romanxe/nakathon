# 평가셋 v2 — dev · gemma-12b-v2-1500-loc · 2026-11-14T22:15

```
symptom  model 30/30 (exact 30/30)  keyword 13/30  | ko 17/17  en 13/13
  by kind: context 3/3  hard_negative 6/6  indirect 4/4  mixed 4/4  multi 4/4  negation 3/3  none 3/3  paraphrase 2/2  plain 1/1
  urgent codes (chest pain, breathlessness, crisis) caught: model 10/10  keyword 5/10
  schema errors: 0
  body parts (display only): right 29/30  field absent 0  | report names a part 10/11  names none 19/19
latency  symptom median 2.1s  max 2.9s  (n=30)
```

## 증상: 틀린 문항

| # | 종류 | 문장 | 기대 | 금지 | 모델이 낸 코드 |
|---|---|---|---|---|---|

## 부위: 틀린 문항 (표시용, 증상 점수와 별개)

| # | 문장 | 말한 부위 | 허용 | 모델이 낸 부위 |
|---|---|---|---|---|
| SD-015 | Both wrists have an itchy red band where the cuffs sit, and both shoulders are sore from the suit fit check. | left_arm, right_arm | - | back, left_arm, right_arm |

## 기분: 범위 밖 문항

| # | 문장 | 기대 범위 | 모델 (mood / fatigue / stress) |
|---|---|---|---|

## 설명: 문단과 답을 나란히 (뜻이 맞는지는 사람이 읽어야 한다)

