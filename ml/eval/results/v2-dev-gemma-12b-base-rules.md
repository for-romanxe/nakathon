# 평가셋 v2 — dev · gemma-12b-base-rules · 2026-11-14T15:19

```
symptom  model 28/30 (exact 28/30)  keyword 13/30  | ko 15/17  en 13/13
  by kind: context 3/3  hard_negative 4/6  indirect 4/4  mixed 4/4  multi 4/4  negation 3/3  none 3/3  paraphrase 2/2  plain 1/1
  urgent codes (chest pain, breathlessness, crisis) caught: model 10/10  keyword 5/10
  schema errors: 1
mood     in range 12/12  schema errors 0
latency  symptom median 2.4s  max 7.8s  (n=30)
latency  mood median 1.8s  max 1.9s  (n=12)
```

## 증상: 틀린 문항

| # | 종류 | 문장 | 기대 | 금지 | 모델이 낸 코드 |
|---|---|---|---|---|---|
| SD-004 | hard_negative | 야간 근무 끝났더니 졸려 죽겠네. 얼른 자야겠다. | fatigue | crisis | sleep_issue |
| SD-006 | hard_negative | 선장님이 아침부터 어지럽다고 하셔서 오늘 점검은 제가 대신 합니다. 저는 허리만 좀 뻐근해요. | musculoskeletal_pain | dizziness | 오류: symptom: severity: not an integer |

## 기분: 범위 밖 문항

| # | 문장 | 기대 범위 | 모델 (mood / fatigue / stress) |
|---|---|---|---|

## 설명: 문단과 답을 나란히 (뜻이 맞는지는 사람이 읽어야 한다)

