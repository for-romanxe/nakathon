# 평가셋 v2 — test · gemma-12b-v2-1500-loc · 2026-11-14T22:18

```
symptom  model 59/60 (exact 59/60)  keyword 18/60  | ko 33/34  en 26/26
  by kind: context 6/6  hard_negative 9/10  indirect 7/7  mixed 8/8  multi 8/8  negation 6/6  none 5/5  paraphrase 6/6  plain 4/4
  urgent codes (chest pain, breathlessness, crisis) caught: model 18/18  keyword 5/18
  schema errors: 0
  body parts (display only): right 54/60  field absent 0  | report names a part 17/22  names none 37/38
latency  symptom median 2.2s  max 15.8s  (n=60)
```

## 증상: 틀린 문항

| # | 종류 | 문장 | 기대 | 금지 | 모델이 낸 코드 |
|---|---|---|---|---|---|
| ST-008 | hard_negative | 창밖으로 지구가 보이는데 가슴이 벅차서 한동안 말이 안 나왔어요. | none | chest_pain, shortness_of_breath | chest_pain |

## 부위: 틀린 문항 (표시용, 증상 점수와 별개)

| # | 문장 | 말한 부위 | 허용 | 모델이 낸 부위 |
|---|---|---|---|---|
| ST-008 | 창밖으로 지구가 보이는데 가슴이 벅차서 한동안 말이 안 나왔어요. | - | - | chest |
| ST-015 | The queasiness from my first two days up here is completely gone. All that's left is a blocked-up nose. | head | - | - |
| ST-025 | 어깨랑 목덜미가 돌처럼 굳더니 이제는 머리까지 지끈거려. | left_arm, right_arm, head, neck | - | head, neck |
| ST-030 | 무중력 나흘째인데 코맹맹이 소리가 나고 냄새도 잘 안 맡아져요. | head | - | - |
| ST-031 | 착륙한 지 이틀째인데, 일어설 때마다 정신이 아득해지고 속도 메슥거려요. | abdomen | head | - |
| ST-041 | 새 hygiene wipe 쓰고 나서 forearm에 rash가 올라왔고 꽤 itchy합니다. | left_arm, right_arm | - | - |

## 기분: 범위 밖 문항

| # | 문장 | 기대 범위 | 모델 (mood / fatigue / stress) |
|---|---|---|---|

## 설명: 문단과 답을 나란히 (뜻이 맞는지는 사람이 읽어야 한다)

