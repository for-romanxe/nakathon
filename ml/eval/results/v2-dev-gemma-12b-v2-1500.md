# 평가셋 v2 — dev · gemma-12b-v2-1500 · 2026-11-14T16:48

```
symptom  model 29/30 (exact 29/30)  keyword 13/30  | ko 16/17  en 13/13
  by kind: context 3/3  hard_negative 6/6  indirect 4/4  mixed 4/4  multi 3/4  negation 3/3  none 3/3  paraphrase 2/2  plain 1/1
  urgent codes (chest pain, breathlessness, crisis) caught: model 10/10  keyword 5/10
  schema errors: 0
mood     in range 12/12  schema errors 0
explain  all: first-run pass 20/20  hold 0/20  picked first candidate 20/20  해요체 10/10  avoid-term hits 1  grounding median 0.55 (min 0.19)
latency  symptom median 1.9s  max 3.4s  (n=30)
latency  mood median 1.4s  max 1.7s  (n=12)
latency  explain median 4.0s  max 4.8s  (n=20)
```

## 증상: 틀린 문항

| # | 종류 | 문장 | 기대 | 금지 | 모델이 낸 코드 |
|---|---|---|---|---|---|
| SD-013 | multi | 콧물이 줄줄 흐르고 이마 쪽이 욱신욱신 아파요. 온몸이 노곤하기도 하고요. | congestion, fatigue, headache | - | congestion, fatigue |

## 기분: 범위 밖 문항

| # | 문장 | 기대 범위 | 모델 (mood / fatigue / stress) |
|---|---|---|---|

## 설명: 문단과 답을 나란히 (뜻이 맞는지는 사람이 읽어야 한다)

### ED-001 · ko · caution · 후보 co2_headache, sleep_deficit

- 문단 `nih:co2-01#p2`: 일반 의학에서는 두통의 몇 가지 양상을 스스로 돌보는 것만으로 넘기지 말고 의사의 진료를 받아야 하는 위험 신호로 본다. 며칠이나 몇 주에 걸쳐 점점 심해지거나 양상이 달라지는 두통, 일주일에 두 번 이상 생기는 두통, 전에는 두통이 없던 사람에게 새로 생겨 계속되는 두통이 여기에 해당한다.
- 문단 `nasa:co2-01#p4`: 이산화탄소 농도가 국소적으로 높아지기 쉬운 장소와 상황으로는 개인 침실과 임시로 마련한 잠자리, 몇 시간씩 한자리에서 하는 작업, 환기되는 공간 바깥인 패널 뒤쪽에서 하는 정비 작업, 운동 구역, 제거 장치의 고장이 꼽힌다. 두통이 이런 상황에서 시작됐는지 적어 두면 유용한 정보가 된다.
- **1차** 통과 [co2_headache]: 이산화탄소 농도가 높은 곳에서 작업하거나 잠을 잘 때 두통이 생길 가능성이 있어요. / 두통이 이런 상황에서 시작되었는지 기록해 두는 게 도움이 될 수 있어요.

### ED-002 · en · advisory · 후보 co2_headache

- 문단 `nasa:co2-01#p5`: The cabin displays the carbon dioxide level and notifies the crew when it is outside safe limits, but that reading does not show what one person breathes: sensors sample fixed points, and no method of measuring the air a person actually inhales is in use. No wearable reading has been validated as a sign of headache from carbon dioxide.
- 문단 `nasa:co2-01#p4`: Settings named as prone to locally raised carbon dioxide are sleep stations and improvised sleeping spots, a fixed work position held for several hours, maintenance behind panels outside the ventilated space, exercise areas, and a failure of removal equipment. Noting whether a headache began in one of these settings is useful information.
- **1차** 통과 [co2_headache]: Headaches may occur in areas with locally raised carbon dioxide, such as sleep stations or fixed work positions. / Note if your headache began in one of these specific settings.

### ED-003 · ko · advisory · 후보 dehydration

- 문단 `nasa:dehy-01#p1`: 비행 중 승무원은 대체로 비행 전보다 물을 적게 마시고 권장량에 못 미치는 경우도 많은데, 갈증을 덜 느끼기 때문일 수 있다. 그만큼 탈수 위험이 커지며, 갈증이 날 때만 마시면 필요한 양을 채우지 못할 수 있다.
- 문단 `lit:dehy-06#p1`: 우주에서는 체온이 지상에서보다 높게 유지되는데, 처음 몇 달이 지나면 쉬고 있을 때도 그렇고 운동 중에는 더욱 그렇다. 이 때문에 필요한 수분량이 늘 수 있다. 선외 활동에는 마실 물이 추가로 배정되며, 오래 운동하는 날에도 평소보다 더 마시는 것이 좋다.
- **1차** 통과 [dehydration]: 우주에서는 체온이 높게 유지되어 평소보다 더 많은 수분이 필요할 가능성이 있어요. / 갈증이 나지 않더라도 권장량을 채울 수 있도록 물을 충분히 마시는 게 좋아요.

### ED-004 · en · advisory · 후보 dehydration, orthostatic_intolerance

- 문단 `lit:dehy-08#p1`: Skin temperature from a wearable differs widely between people, in both its average and its range, and it changes with the time of day. No fixed cut-off applies: a reading is meaningful only against the same person's baseline, and only when compared with values taken at a similar time of day.
- 문단 `ochmo:dehy-03#p3`: Dehydration is more likely when exercise lasts longer than an hour, when working in heat, on spacewalk days, and during illness with vomiting, diarrhoea or fever. Too much caffeine can add to fluid loss. These are the days on which to keep a closer eye on drinking.
- **1차** 통과 [dehydration]: Dehydration may occur more easily during long exercise sessions, in heat, or during illness. / Keep a closer eye on your fluid intake and be mindful that too much caffeine can add to fluid loss.

### ED-005 · ko · advisory · 후보 mood_low, sleep_deficit · ⚠ 피할 말: 수면 부족

- 문단 `hrp:mood-02#p1`: 긴 임무에서는 단조로운 일상, 너무 많거나 너무 적은 업무, 가족과 떨어져 지내는 것, 잠을 충분히 자지 못하는 것, 몸의 불편함이 저마다 기분을 끌어내릴 수 있다. 반대로 보람 있는 일, 창밖을 바라보는 시간, 서로 도움을 주고받는 것은 기분을 지켜 주는 편이다.
- 문단 `nih:mood-02#p1`: 스트레스는 원인이 된 상황이 해결되면 대개 가라앉지만, 불안은 당장 위협이 없어도 계속될 수 있다. 하루 이틀 힘든 것과, 가라앉은 기분이 거의 매일, 하루 대부분 이어지면서 두 주쯤 계속되는 것은 다르다. 그러므로 변화가 얼마나 오래 이어지는지 기록해 두는 것이 좋다.
- **1차** 통과 [mood_low]: 단조로운 일상이나 수면 부족 같은 요인들이 기분을 저하시킬 가능성이 있어요. / 기분이 가라앉는 변화가 얼마나 오래 이어지는지 기록해 두는 게 좋아요.

### ED-006 · en · advisory · 후보 mood_low, sleep_deficit

- 문단 `hrp:mood-01#p1`: Living for a long time in a small, isolated space can bring low mood, worry, irritability and friction with others, and may affect sleep, morale and decision-making. In past spaceflight such changes have mostly been mild, although they are thought to be under-reported.
- 문단 `hrp:mood-02#p3`: Aerobic exercise can ease depressive and anxious feelings, especially when they are mild, and physically active members of Antarctic winter crews kept a steadier mood. Keeping regular times for meals, sleep and exercise is part of the same advice.
- **1차** 통과 [mood_low]: Living in an isolated space can lead to low mood or irritability, which may also affect your sleep. / Aerobic exercise can help ease these feelings, and keeping regular times for meals and sleep is recommended.

### ED-007 · ko · caution · 후보 musculoskeletal_strain, sleep_deficit

- 문단 `hrp:msk-02#p1`: 체중이 실리지 않으면 척추가 곧게 펴지면서 길어지기 때문에 무중력에서는 키가 조금 커질 수 있다. 이런 변화가 비행 초기의 허리 통증에 영향을 줄 수 있지만 원인은 아직 분명히 밝혀지지 않았으며, 몸통 근육이 약해지는 것도 원인 가운데 하나로 거론된다.
- 문단 `nasa:msk-06#p1`: 우주비행사 건강 기록을 보면 임무를 마친 뒤 첫 한 해 동안 흔히 디스크라고 부르는 추간판 탈출이 눈에 띄게 잦았다. 이 기록을 바탕으로, 착륙 뒤 첫 이틀가량은 척추에 실리는 하중을 되도록 줄이라는 권고가 나와 있다.
- **1차** 통과 [musculoskeletal_strain]: 무중력 환경에서 척추가 펴지면서 허리 통증이 생길 가능성이 있어요. / 착륙 후 척추에 실리는 하중을 되도록 줄이는 게 도움이 될 수 있어요.

### ED-008 · en · caution · 후보 musculoskeletal_strain

- 문단 `nih:msk-03#p1`: A strain is a muscle or tendon that has been overstretched or partly torn, either by a sudden overload or by repeating the same motion. In spaceflight, joint and muscle pain becomes more frequent because of the exercise equipment and work in the spacesuit.
- 문단 `nasa:msk-01#p2`: For early-flight back ache, curling up with the knees drawn toward the chest and stretching the lower back each helped about nine in ten of those trying them in crew records. General back-pain guidance also favours staying gently active and limiting only the movements that hurt, instead of prolonged bed rest.
- **1차** 통과 [musculoskeletal_strain]: Joint and muscle pain can become more frequent due to exercise equipment and spacesuit work. / Try curling up with knees toward your chest or stretching your lower back while staying gently active.

### ED-009 · ko · caution · 후보 orthostatic_intolerance, dehydration

- 문단 `hrp:oi-04#p3`: 심박수는 일어서면 원래 올라가며, 착륙 당일에는 비행 전보다 더 크게 오른다. 그러나 많이 오르는 것 자체가 나쁜 신호는 아니다. 지상 시험에서는 혈압을 유지한 사람들이 실신할 뻔한 사람들보다 심박수가 더 많이 올랐으므로, 심박수만으로는 증상이 얼마나 심한지 알 수 없다.
- 문단 `ochmo:oi-05#p1`: 중력이 돌아온 뒤 서 있을 때 혈압이 유지되지 않으면 머리가 아찔하고 메스꺼우며, 시야가 좁아지거나 흐려지고, 기운이 빠지고, 심장이 빨리 뛸 수 있다. 이런 느낌은 실신에 앞서 나타날 수 있으므로 일찍 알아차리는 것이 좋다.
- **1차** 통과 [orthostatic_intolerance]: 중력이 돌아온 뒤 일어설 때 머리가 아찔하거나 심장이 빨리 뛸 가능성이 있어요. / 이런 느낌은 실신에 앞서 나타날 수 있으니 몸 상태를 미리 살피는 게 좋아요.

### ED-010 · en · caution · 후보 orthostatic_intolerance

- 문단 `hrp:oi-04#p1`: In weightlessness body fluid moves toward the head, and the body responds by carrying less circulating blood volume; the unloaded heart also pumps less blood per beat once upright. When gravity returns and blood pools in the legs, blood pressure can fall if the blood vessels do not tighten enough in response.
- 문단 `hrp:oi-03#p1`: Standing tolerance usually returns within one to three days after landing, though some people have symptoms for several days. During that time crews have typically kept the compression garment on, eaten and drunk as tolerated, rested, and put off activities that tend to bring on a drop in blood pressure.
- **1차** 통과 [orthostatic_intolerance]: Blood pooling in the legs upon return to gravity can cause blood pressure to fall if vessels do not tighten enough. / You may experience symptoms for several days; during this time, rest and put off activities that tend to bring on a drop in blood pressure.

### ED-011 · ko · advisory · 후보 sans_suspect

- 문단 `hrp:sans-02#p3`: 신경안구 증후군(SANS)은 가까운 것을 보는 시력이 달라지는 것 말고는 증상이 없는 경우가 많고, 가장 이른 징후는 눈 뒤쪽을 찍는 영상 검사에서만 확인된다. 그래서 본인의 느낌이 아니라 시력 검사, 초음파 검사, 광학 영상 검사 같은 정기 눈 검사로 발견된다. 이 변화를 나타내는 신호로 검증된 웨어러블 측정값은 없다.
- 문단 `ochmo:sans-01#p2`: 장기 임무 중에는 가까운 것을 보는 시력이 달라질 수 있어, 도수를 단계적으로 높인 안경 여러 벌을 미리 싣고 간다. 가까운 작업을 할 때 흐려 보이면 도수가 더 높은 안경으로 바꿔 쓸 수 있는데, 이는 흐려 보이는 불편을 덜어 줄 뿐 눈 자체의 변화를 치료하는 것은 아니다.
- **1차** 통과 [sans_suspect]: 장기 임무 중에는 가까운 것을 보는 시력이 달라질 가능성이 있어요. / 가까운 작업을 할 때 흐려 보인다면 미리 준비한 도수가 높은 안경으로 바꿔 쓰는 게 도움이 될 수 있어요.

### ED-012 · en · caution · 후보 sans_suspect, co2_headache

- 문단 `hrp:sans-01#p2`: Most crew on long missions show at least an early sign of SANS on eye imaging, but only a minority develop swelling that is clinically significant, and the risk is higher on longer missions. Where focus has shifted, vision has so far been correctable with new lenses, and no permanent loss of sharpness has been documented.
- 문단 `hrp:sans-02#p2`: After return to Earth, optic nerve swelling has generally eased over weeks to months without treatment. In some astronauts, however, it had not fully returned to the pre-flight level a year later, and the change in focus has lasted for years in some long-mission crew. Eye examinations therefore continue after the flight.
- **1차** 통과 [sans_suspect]: Early signs of SANS may appear on eye imaging during long missions, though vision changes can often be corrected with lenses. / Eye examinations continue after the flight to monitor for any long-term changes in focus.

### ED-013 · ko · advisory · 후보 skin_irritation

- 문단 `lit:skin-03#p1`: 우주비행사들은 주로 손과 발의 피부가 건조하고 벗겨지며 가려움이 있고, 작은 상처가 더디게 아문다고 보고했다. 그러나 궤도에서 소수를 대상으로 한 측정에서는 피부 수분이나 장벽 기능이 나빠지지 않았으므로, 무중력 자체가 피부를 건조하게 하는지는 아직 결론이 나지 않았다. 연구자들은 이런 불편이 우주정거장 환경보다 씻는 여건과 더 관련이 있다고 보았다.
- 문단 `nih:skin-04#p1`: 비누나 세정제, 젖은 옷, 거친 옷감, 그 자리에 닿는 끈이나 센서처럼 원인으로 짐작되는 것이 있으면 먼저 그것과의 접촉을 줄여 보는 것이 무리 없는 첫 단계이다. 비행 중 오래가는 피부 증상에 대해서도 확인된 자극 요인을 피하는 방법이 제시되어 있다.
- **1차** 통과 [skin_irritation]: 피부가 건조해지거나 가려움이 느껴지는 등 피부 자극이 생길 가능성이 있어요. / 비누나 세정제, 거친 옷감 등 자극이 될 만한 것과의 접촉을 줄여 보는 게 좋아요.

### ED-014 · en · caution · 후보 skin_irritation

- 문단 `hrp:skin-02#p1`: Gear that presses or rubs can damage the skin. Soft parts of the spacesuit often cause scrapes and bruises at the wrists, arms, knees and ankles, wrinkles in boots can raise blisters, damp gloves are linked to hand and nail injury, and an earlier treadmill harness chafed and bruised shoulders and hips.
- 문단 `nih:skin-04#p2`: For dry or irritated skin, basic care is gentle: clean with a mild, unscented or non-soap cleanser, pat the skin dry instead of rubbing, and moisturise soon after washing. Try not to scratch or rub the area, and avoid getting overheated.
- **1차** 통과 [skin_irritation]: Gear that presses or rubs can damage the skin and may lead to irritation or blisters. / Clean the area with a mild cleanser, pat dry, and moisturize while avoiding rubbing or overheating.

### ED-015 · ko · caution · 후보 sleep_deficit

- 문단 `nih:sleep-01#p1`: 성인은 대개 하루에 적어도 일곱 시간은 자야 하지만, 필요한 수면 시간은 사람마다 다르다. 필요한 만큼 자지 못하는 날이 이어지면 모자란 잠이 하루하루 쌓이며, 이렇게 쌓인 수면 부족은 질 좋은 잠을 자야만 해소된다.
- 문단 `hrp:sleep-02#p1`: 빛이 모자라거나 빛을 받는 시간대가 맞지 않으면 생체 시계가 흐트러질 수 있어, 우주정거장의 조명은 지구의 낮과 밤 주기를 본뜨도록 만들어져 있다. 일하는 시간에는 밝은 조명을, 잠들기 전에는 더 어두운 조명을 쓰는 것이 이 원리에 맞다. 잠들기 전에 긴장을 풀 시간이 모자라면 잠들기 어렵다는 승무원들의 보고도 있으므로 그 시간을 지키는 것이 좋다.
- **1차** 통과 [sleep_deficit]: 잠이 부족한 날이 계속되면 피로가 쌓여 컨디션에 영향을 줄 수 있어요. / 잠들기 전에 긴장을 풀 수 있는 시간을 확보하고 조명을 조절해 보는 게 좋아요.

### ED-016 · en · caution · 후보 sleep_deficit

- 문단 `nih:sleep-01#p1`: Most adults need at least seven hours of sleep a night, though the exact need differs from person to person. When sleep keeps falling short of that need, the shortfall builds up night after night, and only good-quality sleep can make it up.
- 문단 `cdc:sleep-01#p1`: Caffeine takes about half an hour to work and stays in the body for many hours, so it is better kept to the early part of the waking day. Taken later it can disturb the next sleep; in one study a large amount taken six hours before bedtime still did. It does not replace sleep.
- **1차** 통과 [sleep_deficit]: Shortfalls in sleep can build up night after night, which may impact your recovery. / Avoid caffeine later in the day as it can disturb the next sleep cycle.

### ED-017 · ko · advisory · 후보 space_motion_sickness

- 문단 `hrp:sms-02#p1`: 우주 멀미는 지구에서 겪는 멀미와 느낌이 다를 수 있다. 몸이 찌뿌둥하고 입맛이 없으며 일을 시작할 의욕이 나지 않는 증상은 거의 누구에게나 나타나고, 두통과 졸음, 속이 거북한 느낌이 함께 오는 일이 많다. 구토는 메스꺼움이 거의 없다가 갑자기 나올 수도 있다.
- 문단 `ochmo:sms-01#p5`: 우주 멀미가 경증일 때는 증상이 몇 가지에 그치고 머리를 움직일 때만 나타나기도 하며, 구토는 많아야 한 번이고 업무에 지장이 없으며, 대개 이틀쯤이면 가라앉는다. 중등도일 때도 사흘쯤이면 가라앉는 것이 보통이다. 구토 횟수와 증상이 시작된 뒤 지난 날수를 세어 두면 경과를 가늠하는 데 도움이 된다.
- **1차** 통과 [space_motion_sickness]: 몸이 찌뿌둥하거나 속이 거북한 느낌이 드는 등 우주 멀미 증상이 나타날 가능성이 있어요. / 증상이 시작된 뒤 지난 날수를 세어보며 경과를 살펴보는 게 도움이 될 수 있어요.

### ED-018 · en · advisory · 후보 space_motion_sickness, dehydration

- 문단 `hrp:sms-02#p1`: Space motion sickness does not always feel like motion sickness on Earth. Feeling generally unwell, losing appetite and lacking the drive to start tasks are nearly universal, often with headache, drowsiness and an uneasy awareness of the stomach, and vomiting can come suddenly with little or no nausea beforehand.
- 문단 `ochmo:sms-01#p2`: Head and whole-body movements can start or worsen space motion sickness, and nodding the head forward and back is reported as the most provoking. Limiting head movement and activity, closing the eyes for a while, or concentrating on a task can ease the symptoms.
- **1차** 통과 [space_motion_sickness]: You may be experiencing space motion sickness, which can manifest as feeling generally unwell or having a lack of drive. / Limiting head movement and activity or closing your eyes for a while can help ease these symptoms.

### ED-019 · ko · caution · 후보 upper_respiratory

- 문단 `lit:uri-02#p1`: 우주정거장 건강 기록에서 코막힘은 우주비행사 네 명 가운데 세 명꼴로 기록되었지만, 귀와 코, 목의 감염이 기록된 사람은 몇 명에 그쳤다. 따라서 코막힘을 곧 감염으로 받아들여서는 안 되며, 다만 이 기록에는 둘을 가려내는 검증된 방법이 제시되어 있지 않다.
- 문단 `cdc:uri-03#p2`: 감기 증상은 대개 이삼일 안에 가장 심해지고 일주일이 되기 전에 대부분 가라앉는다. 증상이 나아지고 있는지, 열이 있는지와 며칠째 이어지는지, 좋아지던 증상이 다시 나빠지는지를 날마다 확인해 두는 것이 좋다.
- **1차** 통과 [upper_respiratory]: 코막힘이 감염으로 이어질 가능성도 있지만, 단순히 코막힘만으로 감염이라 단정하기는 어려울 수 있어요. / 증상이 나아지는지, 열이 있는지, 며칠째 이어지는지를 매일 확인해 두는 게 좋아요.

### ED-020 · en · advisory · 후보 upper_respiratory

- 문단 `cdc:uri-03#p1`: A cold is a viral infection of the nose and throat that can bring a runny or blocked nose, sneezing, cough, sore throat, mild aches and, in adults, usually only a low fever. It spreads through droplets from coughs and sneezes, contaminated hands and surfaces and close contact, and microbes pass between people more easily in a closed habitat.
- 문단 `lit:uri-02#p2`: Recorded congestion was most frequent in the first week of flight and dropped sharply in the second, but entries continued late into missions, which may point to other triggers. It helps to note when stuffiness began and whether anything new, such as a sore throat, cough or fever, has joined it.
- **1차** 통과 [upper_respiratory]: A low fever may be a sign of a viral infection of the nose and throat, which can spread easily in a closed habitat. / Note when stuffiness began and if symptoms like a sore throat or cough have joined it.

