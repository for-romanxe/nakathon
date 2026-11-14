# 평가셋 v2 — test · gemma-12b-base · 2026-11-14T14:46

```
symptom  model 58/60 (exact 58/60)  keyword 18/60  | ko 32/34  en 26/26
  by kind: context 6/6  hard_negative 8/10  indirect 7/7  mixed 8/8  multi 8/8  negation 6/6  none 5/5  paraphrase 6/6  plain 4/4
  urgent codes (chest pain, breathlessness, crisis) caught: model 18/18  keyword 5/18
  schema errors: 0
mood     in range 23/24  schema errors 0
explain  all: first-run pass 38/40  hold 0/40  picked first candidate 38/40  해요체 20/20  avoid-term hits 0  grounding median 0.58 (min 0.04)
explain  held-out paragraphs: first-run pass 20/20  hold 0/20  picked first candidate 18/20  해요체 10/10  avoid-term hits 0  grounding median 0.60 (min 0.04)
explain  seen paragraphs: first-run pass 18/20  hold 0/20  picked first candidate 20/20  해요체 10/10  avoid-term hits 0  grounding median 0.53 (min 0.19)
latency  symptom median 2.4s  max 41.0s  (n=60)
latency  mood median 1.6s  max 2.0s  (n=24)
latency  explain median 3.5s  max 7.8s  (n=40)
```

## 증상: 틀린 문항

| # | 종류 | 문장 | 기대 | 금지 | 모델이 낸 코드 |
|---|---|---|---|---|---|
| ST-008 | hard_negative | 창밖으로 지구가 보이는데 가슴이 벅차서 한동안 말이 안 나왔어요. | none | chest_pain, shortness_of_breath | chest_pain |
| ST-010 | hard_negative | 어제까지는 두통 때문에 고생했는데 자고 일어나니 말끔히 나았어요. | none | headache | headache |

## 기분: 범위 밖 문항

| # | 문장 | 기대 범위 | 모델 (mood / fatigue / stress) |
|---|---|---|---|
| MT-010 | 밥을 먹어도 무슨 맛인지 모르겠고, 머릿속에는 온통 내일 착륙 절차뿐이에요. | stress 3~4 | 2 / 4 / 5 |

## 설명: 문단과 답을 나란히 (뜻이 맞는지는 사람이 읽어야 한다)

### ET-001 · ko · caution · 후보 co2_headache, sleep_deficit · 시험 전용 문단 · ⚠ 첫 후보 아님

- 문단 `hrp:co2-01#p1`: 소음, 더위, 추위, 공기가 정체된 느낌은 승무원이 직접 느낄 수 있는 선실 환경이며, 거주 공간은 너무 덥거나 춥거나 시끄럽지 않게 만들어야 한다. 소음은 해롭게 느껴지지 않는 수준이라도 짜증과 두통을 일으키고 잠을 방해할 수 있다. 쾌적하게 느끼는 조건은 사람마다 다르므로 주변 공기 흐름과 옷차림은 각자 조절할 수 있게 하는 것이 원칙이다.
- 문단 `nasa:co2-01#p3`: 이산화탄소로 인한 두통은 일반적인 두통 치료에 잘 반응하지 않고 이산화탄소 농도를 낮추면 대개 가라앉는 것으로 알려져 있으며, 승무원에게는 농도를 낮추는 절차가 마련되어 있다. 비행 중에 생기는 다른 두통은 흔히 수면, 운동, 수분 섭취, 일반적인 진통제로 관리한다.
- **1차** 통과 [sleep_deficit]: 수면이 부족하면 두통이 생기거나 컨디션이 저하될 가능성이 있어요. / 수면이나 수분 섭취 등을 통해 상태를 관리해 보는 게 좋아요.

### ET-002 · ko · advisory · 후보 co2_headache

- 문단 `nasa:co2-01#p5`: 선실에서는 이산화탄소 농도가 표시되고 안전 한계를 벗어나면 승무원에게 알림이 가지만, 이 측정값이 한 사람이 실제로 들이마시는 공기를 보여 주는 것은 아니다. 감지기는 정해진 지점의 공기만 측정하며, 개인이 들이마시는 공기를 직접 측정하는 방법은 쓰이고 있지 않다. 이산화탄소로 인한 두통을 나타내는 신호로 검증된 웨어러블 측정값도 없다.
- 문단 `nasa:co2-01#p2`: 승무원은 이산화탄소에 노출되었을 때 자신에게 나타나는 증상을 알아차리도록 비행 전에 훈련을 받으며, 승무원의 증상 보고는 이산화탄소를 감시하는 방법의 일부다. 증상이 생기면 휴대용 측정기로 추가 측정을 하게 되어 있으므로, 두통이 언제 어디에서 시작됐는지 알리면 해당 장소의 공기를 확인하는 데 도움이 된다.
- **1차** 통과 [co2_headache]: 이산화탄소 노출로 인해 두통이 생길 가능성이 있어요. / 증상이 나타나면 언제 어디서 시작됐는지 알려주시면 공기 확인에 도움이 될 수 있어요.

### ET-003 · en · caution · 후보 co2_headache, sleep_deficit · 시험 전용 문단 · ⚠ 첫 후보 아님

- 문단 `hrp:co2-01#p1`: Noise, heat, cold and still air are cabin conditions a person can notice directly, and living quarters are meant to be neither too hot, too cold nor too loud. Noise can bring irritation, headaches and poorer sleep even when it does not seem harmful, and comfort differs between people, so local airflow and clothing are meant to be adjustable.
- 문단 `nasa:co2-01#p3`: A headache from carbon dioxide is described as responding poorly to ordinary headache treatment and as usually easing once the level of the gas is reduced, for which crews have procedures. Other headaches in flight are commonly managed with sleep, exercise, fluids and common pain relief.
- **1차** 통과 [sleep_deficit]: Shortened sleep may be contributing to your current physical strain and could be linked to cabin noise or discomfort. / Other headaches in flight can commonly be managed with sleep, exercise, and fluids.

### ET-004 · en · advisory · 후보 co2_headache

- 문단 `nasa:co2-01#p5`: The cabin displays the carbon dioxide level and notifies the crew when it is outside safe limits, but that reading does not show what one person breathes: sensors sample fixed points, and no method of measuring the air a person actually inhales is in use. No wearable reading has been validated as a sign of headache from carbon dioxide.
- 문단 `ochmo:co2-01#p2`: In crew reports from earlier missions, headaches at raised carbon dioxide came with fatigue, a general unwell feeling and flushing, and at higher levels with poorer sleep and nausea. These reports are anecdotal, and most textbook signs of carbon dioxide poisoning have never been seen in spaceflight, so they are something to note, not proof of the cause.
- **1차** 통과 [co2_headache]: Poorer sleep and a general unwell feeling can be anecdotal signs of elevated carbon dioxide levels. / Note these symptoms as they may be related to the cabin environment.

### ET-005 · ko · caution · 후보 dehydration, orthostatic_intolerance · 시험 전용 문단

- 문단 `lit:dehy-08#p2`: 지상에서 이루어진 한 연구에서는 감염이 시작될 무렵 참가자 대부분의 피부 온도가 개인 기준선보다 조금 높았다. 그러나 같은 판정 기준이 열이 없었던 사람을 발열로 잘못 가려내기도 하고 열이 있었던 사람 일부를 놓치기도 했다. 피부 온도가 올랐다면 원인을 찾아볼 이유는 되지만, 그것만으로 발열이나 감염, 탈수가 있다고 볼 수는 없다.
- 문단 `hrp:dehy-04#p1`: 장기 체류 승무원은 비행 중 소변량이 비행 전보다 뚜렷하게 적었다. 소변량이 적으면 신장 결석이 생길 가능성이 커지므로, 소변 상태와 마신 물의 양을 함께 기록해 두는 것이 좋다.
- **1차** 통과 [dehydration]: 소변량이 줄어들면 신장 결석이 생길 가능성이 있을 수 있어요. / 소변 상태와 마신 물의 양을 함께 기록해 두는 게 좋아요.

### ET-006 · ko · advisory · 후보 dehydration

- 문단 `lit:dehy-08#p1`: 착용형 기기로 잰 피부 온도는 평균도 변동 폭도 사람마다 크게 다르고, 하루 중 시간대에 따라서도 달라진다. 따라서 모든 사람에게 똑같이 적용할 수 있는 기준값은 없다. 피부 온도는 그 사람 자신의 기준선과 비교해야 하고, 그것도 비슷한 시간대에 잰 값끼리 비교해야 의미가 있다.
- 문단 `nasa:dehy-01#p2`: 우주 승무원을 위한 수분 섭취 기준은 모두 하루 두 리터가 넘는 양을 요구하며, 선외 활동을 하는 날에는 더 마시도록 한다. 정확한 양은 체격과 목적에 따라 달라진다. 물을 아끼려고 마시는 양을 줄이는 것은 권장되지 않으며, 비행 중에 물을 지나치게 많이 마셔서 문제가 생길 가능성은 매우 낮은 것으로 본다.
- **1차** 통과 [dehydration]: 수분 섭취량이 부족하면 몸에 무리가 갈 수 있어요. / 체격과 목적에 맞춰 충분한 양의 물을 마시는 게 중요할 수 있어요.

### ET-007 · en · caution · 후보 dehydration, orthostatic_intolerance · 시험 전용 문단

- 문단 `lit:dehy-08#p2`: In one study on Earth, skin temperature ran a little above personal baseline around the start of an infection in most participants, yet the same rule also flagged people with no fever and missed some with fever. A rise is a reason to look for a cause, not a sign that fever, infection or dehydration is present.
- 문단 `hrp:dehy-04#p1`: Long-duration crews have passed markedly less urine in flight than before flight. A low urine volume is linked to a higher chance of kidney stones, which is one reason to keep track of urine and fluid intake together.
- **1차** 통과 [dehydration]: A low urine volume can be linked to a higher chance of kidney stones. / Keep track of your urine and fluid intake together.

### ET-008 · en · advisory · 후보 dehydration

- 문단 `lit:dehy-08#p1`: Skin temperature from a wearable differs widely between people, in both its average and its range, and it changes with the time of day. No fixed cut-off applies: a reading is meaningful only against the same person's baseline, and only when compared with values taken at a similar time of day.
- 문단 `ochmo:dehy-03#p2`: Signs that can go with dehydration include strong thirst, a dry mouth, passing less and darker urine, headache, tiredness, dizziness, sleepiness and trouble concentrating. When they appear, it helps to check how much one has drunk that day.
- **1차** 통과 [dehydration]: Signs of dehydration may include tiredness, dizziness, or trouble concentrating. / If these occur, it helps to check how much fluid you have consumed today.

### ET-009 · ko · caution · 후보 mood_low, sleep_deficit · 시험 전용 문단

- 문단 `hrp:mood-02#p4`: 긴 임무 동안 기분과 사기는 오르내릴 수 있고, 그 양상은 사람마다 크게 다르다. 가장 힘든 시기가 언제쯤 오는지에 대해서는 연구 결과가 일치하지 않는다. 그러므로 임무가 얼마나 지났는지를 따지기보다 자신의 기분이 시간에 따라 어떻게 변해 왔는지를 살펴보는 것이 좋다.
- 문단 `hrp:mood-02#p2`: 도움은 고민의 종류에 맞는 사람에게서 받을 때 효과가 큰 편이다. 그래서 업무 스트레스는 동료와, 집안 걱정은 가족과 나누는 것이 좋다. 걱정을 혼자 담아 두지 않고 털어놓는 것, 정해진 가족 대화 시간과 의료·심리 담당자와의 비공개 상담을 활용하는 것도 승무원을 위해 마련된 지원 방법이다.
- **1차** 통과 [mood_low]: 긴 임무를 수행하다 보면 기분이나 사기가 오르내릴 가능성이 있어요. / 자신의 기분 변화를 잘 살펴보고, 고민이 있다면 동료나 가족과 나누는 게 도움이 될 수 있어요.

### ET-010 · ko · advisory · 후보 mood_low

- 문단 `hrp:mood-01#p1`: 고립되고 좁은 공간에서 오래 생활하면 기분이 가라앉거나 불안해지고, 짜증이 늘거나 동료와 마찰이 생길 수 있으며, 수면과 사기, 의사 결정에도 영향을 줄 수 있다. 지금까지의 우주 비행에서 이런 변화는 대부분 가벼운 수준이었지만, 실제보다 적게 보고되었을 가능성이 있다.
- 문단 `nih:mood-01#p1`: 기분 저하가 늘 슬픔으로만 나타나는 것은 아니어서, 주로 짜증이나 화가 느는 사람도 있다. 흥미를 잃거나, 기운이 없거나, 집중하고 결정하기가 어렵거나, 잠이나 식사가 평소보다 늘거나 줄어드는 것도 눈여겨볼 변화이다. 동료나 지상과의 교류를 피하게 되는 것도 그 가운데 하나이다.
- **1차** 통과 [mood_low]: 좁은 공간에서 생활하다 보면 기분이 가라앉거나 불안해질 가능성이 있어요. / 짜증이 늘거나 집중하기 어려울 수 있으니, 평소보다 기운이 없는지 잘 살펴보는 게 좋아요.

### ET-011 · en · caution · 후보 mood_low, sleep_deficit · 시험 전용 문단

- 문단 `hrp:mood-02#p4`: Mood and morale can rise and fall over a long mission, and the pattern differs widely from person to person. Studies do not agree on when a low point tends to come, so it makes sense to follow one's own trend over time and not the stage of the mission.
- 문단 `hrp:mood-02#p2`: Support tends to help most when it comes from the people closest to the problem: a crewmate for work stress, family for worries about home. Sharing concerns instead of holding them in, and using the scheduled private talks with family and with medical or psychological staff, are part of how crews are supported.
- **1차** 통과 [mood_low]: Mood and morale can fluctuate during a long mission, and it may be helpful to monitor your own personal trends. / Sharing concerns with a crewmate or using scheduled private talks can provide support.

### ET-012 · en · advisory · 후보 mood_low · ⚠ 1차 폐기

- 문단 `hrp:mood-01#p1`: Living for a long time in a small, isolated space can bring low mood, worry, irritability and friction with others, and may affect sleep, morale and decision-making. In past spaceflight such changes have mostly been mild, although they are thought to be under-reported.
- 문단 `nih:mood-02#p1`: Stress usually eases once the situation behind it is resolved, whereas anxiety can persist even with no present threat. A rough day is different from a mood that stays low most of the day, nearly every day, for a couple of weeks, so it is worth noting how long a change lasts.
- **1차** 폐기(model output has the same key twice: 'cites')
- **2차** 통과 [mood_low]: Living in an isolated space can lead to low mood or irritability, which may affect your morale and decision-making. / Note how long these feelings last, as persistent low mood is different from a rough day.

### ET-013 · ko · caution · 후보 musculoskeletal_strain, sleep_deficit · 시험 전용 문단

- 문단 `nasa:msk-08#p1`: 비행 중 승무원들은 몸에 필요한 양보다 적게 먹는 일이 많았다. 먹는 양이 모자라면 근육과 뼈가 줄고 지구력이 떨어질 수 있으며, 운동을 하면 필요한 에너지가 더 늘어나므로 운동량에 맞춰 식사도 충분히 하는 것이 좋다. 식단이 단조로워 입맛이 떨어지는 일도 있으며, 에너지 부족을 알려 준다고 검증된 웨어러블 신호는 없다.
- 문단 `nih:msk-05#p1`: 근육이 늘어나 생긴 통증이 가벼울 때는 아픈 동작을 참고 계속하지 말고 멈춘 뒤, 그 부위를 하루 이틀 쉬게 하고 나서 활동을 조금씩 늘리는 것이 좋다. 냉찜질을 할 수 있다면 초기에 짧게 하는 것이 통증을 덜어 줄 수 있으며, 온찜질은 사흘쯤 지난 뒤로 미루는 편이 낫다.
- **1차** 통과 [musculoskeletal_strain]: 근육이 늘어나서 생기는 통증이 가벼울 때도 무리하게 움직이지 않는 게 좋을 수 있어요. / 통증이 느껴지면 활동을 멈추고 하루 이틀 정도 그 부위를 쉬게 해주는 것이 도움이 될 수 있어요.

### ET-014 · ko · advisory · 후보 musculoskeletal_strain

- 문단 `nih:msk-03#p1`: 근육이 늘어나 생긴 통증은 근육이나 힘줄이 지나치게 늘어나거나 일부 찢어진 상태에서 오며, 갑자기 큰 힘이 실리거나 같은 동작을 되풀이할 때 생기기 쉽다. 우주 비행 중에는 운동 기구 사용과 우주복을 입고 하는 선외 활동 때문에 관절과 근육의 통증이 더 잦아진다.
- 문단 `hrp:msk-04#p1`: 무중력에서는 근육과 뼈가 약해지고 심폐 체력이 떨어지는데, 매일 운동을 하면 이런 변화를 덜 수 있지만 약해지는 정도는 사람마다 크게 다르다. 그래서 착륙한 뒤나 행성 표면에서는 몸을 쓰는 작업이 더 힘들어지고, 발이 걸리거나 넘어져 다칠 가능성이 커질 수 있다. 헛디딘 뒤나 힘든 작업 뒤에 새로 생긴 통증은 적어 두는 것이 좋다.
- **1차** 통과 [musculoskeletal_strain]: 운동 기구나 선외 활동으로 인해 근육이나 관절에 통증이 생길 가능성이 있어요. / 힘든 작업 후에 새로 생긴 통증이 있다면 기록해 두는 게 좋아요.

### ET-015 · en · caution · 후보 musculoskeletal_strain, sleep_deficit · 시험 전용 문단

- 문단 `nasa:msk-08#p1`: In flight, crews have often eaten less than their bodies needed. Eating too little goes with loss of muscle and bone and lower endurance, and exercise adds to the energy required, so meals need to keep pace with training. Limited menu variety can dull appetite, and no wearable signal has been validated as showing an energy shortfall.
- 문단 `nih:msk-05#p1`: For a minor strain, stop the movement that hurts instead of pushing through it, rest the area for a day or two, and then build activity back up gradually. Where a cold pack is available, short sessions may ease pain early on, and heat is better left until about three days have passed.
- **1차** 통과 [musculoskeletal_strain]: A minor strain may occur if you push through pain during activity. / Stop the movement that hurts, rest the area for a day or two, and then build activity back up gradually.

### ET-016 · en · advisory · 후보 musculoskeletal_strain

- 문단 `hrp:msk-07#p1`: A drop in recorded activity minutes shows that the day's routine changed, not why. Illness can lower activity, but so can ordinary variation: exercise is scheduled most days, not every day, sessions differ in type and length, and exercise may be skipped on spacewalk days. No wearable signal has been validated as a sign of a strain.
- 문단 `hrp:msk-04#p1`: Weightlessness weakens muscles, bones and aerobic fitness, and although daily exercise limits the loss, the amount lost varies widely between people. After landing or on a planetary surface, this can make physical tasks harder and trips, falls and injuries more likely, so new aches after a stumble or heavy task are worth noting.
- **1차** 통과 [musculoskeletal_strain]: A drop in activity may be due to routine changes or variation in exercise types. / New aches after a stumble or heavy task may indicate strain and are worth noting.

### ET-017 · ko · caution · 후보 orthostatic_intolerance, dehydration · 시험 전용 문단

- 문단 `nasa:oi-07#p1`: 부분 중력에서 서 있는 자세를 얼마나 견디는지는 측정된 적이 없어, 지구의 삼분의 일쯤인 화성 중력이 일어설 때의 아찔함을 막아 주는지는 알려져 있지 않다. 지금까지 달 임무를 대상으로 세운 보수적인 가정은 부분 중력이 이 문제를 막아 주지 않는다는 것이다. 또한 화성에는 지구에서처럼 곁에서 대기하는 의료진이 없으므로 실신했을 때의 결과가 더 나쁠 수 있다.
- 문단 `cdc:oi-09#p1`: 이 문제를 확인하는 표준적인 방법은 몇 분간 누워 있다가 잰 혈압을, 일어선 지 일 분 뒤와 삼 분 뒤에 잰 혈압과 비교하는 것이다. 혈압이 뚜렷하게 떨어지거나 일어설 때 머리가 아찔하거나 어지러우면 비정상으로 본다. 착륙 후나 화성 표면에서 혈압계를 쓸 수 있다면 다시 확인하는 방법으로 삼을 수 있다.
- **1차** 통과 [orthostatic_intolerance]: 부분 중력 환경에서 일어설 때 어지러움을 느끼거나 혈압이 떨어질 가능성이 있어요. / 일어설 때 머리가 아찔하거나 어지러운지 주의 깊게 살펴보는 게 좋아요.

### ET-018 · ko · advisory · 후보 orthostatic_intolerance

- 문단 `hrp:oi-04#p3`: 심박수는 일어서면 원래 올라가며, 착륙 당일에는 비행 전보다 더 크게 오른다. 그러나 많이 오르는 것 자체가 나쁜 신호는 아니다. 지상 시험에서는 혈압을 유지한 사람들이 실신할 뻔한 사람들보다 심박수가 더 많이 올랐으므로, 심박수만으로는 증상이 얼마나 심한지 알 수 없다.
- 문단 `hrp:oi-03#p1`: 서 있는 자세를 견디는 능력은 대개 착륙 후 하루에서 사흘 사이에 돌아오지만, 며칠 동안 증상이 이어지는 사람도 있다. 그동안 승무원들은 보통 압박복을 계속 착용하고, 무리가 되지 않는 만큼 먹고 마시면서 쉬고, 혈압을 떨어뜨리기 쉬운 활동은 뒤로 미뤄 왔다.
- **1차** 통과 [orthostatic_intolerance]: 서 있는 자세를 견디는 능력이 회복되는 데 며칠이 걸릴 가능성이 있어요. / 무리가 되지 않게 쉬면서, 혈압이 떨어지기 쉬운 활동은 잠시 미뤄두는 게 좋을 수 있어요.

### ET-019 · en · caution · 후보 orthostatic_intolerance, dehydration · 시험 전용 문단

- 문단 `nasa:oi-07#p1`: Standing tolerance has never been measured in partial gravity, so it is unknown whether Mars gravity, about one-third of Earth's, protects against light-headedness on standing. The conservative planning assumption, made so far for the Moon, is that partial gravity does not protect. Fainting there could also have worse consequences, since no medical team is waiting on site.
- 문단 `cdc:oi-09#p1`: A standard clinical check for this problem compares blood pressure taken after lying down for several minutes with readings taken one and three minutes after standing up. A clear fall in pressure, or light-headedness or dizziness on standing, counts as abnormal. After landing or on the surface, it can serve as a simple recheck when a cuff is available.
- **1차** 통과 [orthostatic_intolerance]: Partial gravity may not protect against light-headedness or fainting when standing up. / Watch for dizziness or a clear fall in blood pressure when moving from a lying to a standing position.

### ET-020 · en · advisory · 후보 orthostatic_intolerance

- 문단 `hrp:oi-01#p1`: Orthostatic intolerance means the body cannot keep up blood pressure and blood flow to the brain while upright, so a person feels light-headed or may faint. It belongs to the return of gravity, on landing day or on the Mars surface, not to floating in weightlessness, where there is no standing load.
- 문단 `ochmo:oi-05#p2`: Dizziness after landing can come from low blood pressure when upright, from the balance system re-adjusting to gravity, or from both. The balance-related kind is described with a spinning sensation, unsteady walking, nausea and vomiting. In testing, a returning crew member has had to stop standing because of this sickness with no sign of low blood pressure.
- **1차** 통과 [orthostatic_intolerance]: Orthostatic intolerance may cause light-headedness or fainting as the body adjusts to gravity. / Watch for dizziness or a spinning sensation when standing upright.

### ET-021 · ko · caution · 후보 sans_suspect, co2_headache · 시험 전용 문단

- 문단 `hrp:sans-01#p1`: 무중력 상태가 오래 이어지면 혈액과 뇌척수액이 머리 쪽으로 쏠린다. 그 결과 시신경이 붓고(시신경유두부종), 망막에 주름이 생기고, 눈 뒤쪽이 평평해질 수 있는데, 이런 변화를 묶어 우주 비행과 관련된 신경안구 증후군(SANS)이라고 한다.
- 문단 `hrp:sans-02#p1`: 신경안구 증후군(SANS)이 있는 승무원이 느끼는 변화가 있다면, 대개는 눈이 원시 쪽으로 변하면서 가까운 것이 흐려 보이거나 가까운 작업을 할 때 눈이 피로해지는 것이다. 나이가 들수록, 특히 마흔 무렵 이후에는 눈이 이런 변화를 스스로 보완하기 어려워진다. 가까운 것을 보는 시력이 달라졌다면 다음 의료 상담 때 이야기하는 것이 좋다.
- **1차** 통과 [sans_suspect]: 무중력 상태가 지속되면 머리 쪽으로 혈액이 쏠려 시신경이 붓거나 눈이 피로해질 가능성이 있어요. / 가까운 것이 흐릿하게 보이거나 눈이 피로하다면 다음 의료 상담 때 말씀해 주시는 게 좋아요.

### ET-022 · ko · advisory · 후보 sans_suspect · ⚠ 1차 폐기

- 문단 `nih:sans-01#p1`: 가까운 것을 보는 시력은 나이가 들면서 수정체가 딱딱해져 자연스럽게 떨어지며(노안), 대개 사십 대 중반부터 가까운 것이 잘 안 보이고, 글을 멀리 떼어 놓고 보게 되고, 눈이 피로해진다. 이때는 조명을 밝게 하거나 큰 글씨를 쓰거나 돋보기안경을 쓰는 것이 일반적인 대처법이다. 따라서 근거리 시력이 서서히 달라지는 것만으로는 우주 비행의 영향이라고 볼 수 없다.
- 문단 `hrp:sans-01#p3`: 신경안구 증후군(SANS)을 예방하거나 되돌리는 것으로 검증된 방법은 아직 없다. 영양 보충제나, 허벅지를 조이는 띠처럼 체액이 머리 쪽으로 쏠리는 것을 기계적으로 줄이는 방법이 연구되고 있지만, 지금으로서는 스스로 하는 관리법이 아니라 연구 단계에 있는 방법이다.
- **1차** 폐기(level: 주의) [sans_suspect]: 신경안구 증후군(SANS)을 예방하거나 되돌리는 검증된 방법은 아직 없을 수 있어요. / 현재 연구 단계에 있는 방법들이 있으니 주의 깊게 살펴보는 게 좋아요.
- **2차** 통과 [sans_suspect]: 신경안구 증후군을 예방하거나 되돌리는 검증된 방법은 아직 없을 수도 있어요. / 현재 연구 단계에 있는 방법들이 있으니 참고해 주시면 좋겠어요.

### ET-023 · en · caution · 후보 sans_suspect, co2_headache · 시험 전용 문단

- 문단 `hrp:sans-01#p1`: In long periods of weightlessness, blood and the fluid around the brain and spinal cord shift toward the head. This can lead to swelling of the optic nerve, folds in the retina and flattening of the back of the eye, a group of changes known as spaceflight associated neuro-ocular syndrome (SANS).
- 문단 `hrp:sans-02#p1`: When a crew member with SANS notices anything, it is usually blurred near vision or tired eyes during close work, caused by a shift toward far-sightedness. The eye finds this harder to make up for with age, particularly after about forty. A change in near vision is worth mentioning at the next medical check-in.
- **1차** 통과 [sans_suspect]: Fluid shifts toward the head in weightlessness can lead to changes in the eye known as SANS. / You may notice blurred near vision or tired eyes, which is worth mentioning at your next medical check-in.

### ET-024 · en · advisory · 후보 sans_suspect

- 문단 `hrp:sans-01#p2`: Most crew on long missions show at least an early sign of SANS on eye imaging, but only a minority develop swelling that is clinically significant, and the risk is higher on longer missions. Where focus has shifted, vision has so far been correctable with new lenses, and no permanent loss of sharpness has been documented.
- 문단 `hrp:sans-01#p3`: No measure has yet been proven to prevent or reverse SANS. Nutritional supplements and mechanical ways of countering the fluid shift toward the head, such as tight thigh cuffs, are still being studied, so for now they are research rather than self-care.
- **1차** 통과 [sans_suspect]: Early signs of SANS may appear on eye imaging during long missions, though vision can often be corrected with lenses. / No proven measures exist yet, as fluid shift countermeasures are still under research.

### ET-025 · ko · caution · 후보 skin_irritation · 시험 전용 문단

- 문단 `lit:skin-01#p1`: 발진을 비롯한 피부 증상은 장기 궤도 임무에서 가장 자주 기록된 증상에 속하며, 오래가거나 되풀이된 사례의 상당수가 첫 달에 시작되었다. 대개 오돌토돌한 돌기나 비늘처럼 일어나는 작은 반점으로 나타나고 붉어짐이나 가려움이 따르기도 하며, 비행 중에 정확한 원인이 확인되는 일은 드물다.
- 문단 `cdc:skin-06#p1`: 비행 중의 여러 스트레스 요인은 대상포진을 일으키는 바이러스처럼 몸속에 잠복해 있던 바이러스를 다시 활동하게 할 수 있다. 대상포진은 몸이나 얼굴의 한쪽에 띠 모양으로 물집이 잡히는 발진으로 나타나며, 아프고 대개 가렵다. 발진이 나타나기 며칠 전부터 그 자리에 통증이나 가려움, 저림이 올 수 있다.
- **1차** 통과 [skin_irritation]: 피부 발진이나 가려움 같은 증상이 나타날 가능성이 있어요. / 작은 반점이나 돌기가 생기는지 주의 깊게 살펴보는 게 좋아요.

### ET-026 · ko · advisory · 후보 skin_irritation

- 문단 `hrp:skin-02#p1`: 피부에 닿아 누르거나 마찰을 일으키는 장비는 피부를 상하게 할 수 있다. 우주복의 부드러운 소재 부분은 손목과 팔, 무릎, 발목에 쓸린 상처와 멍을 자주 남기고, 부츠 안의 주름은 물집을 만들 수 있으며, 장갑 속 습기는 손과 손톱의 손상과 관련이 있다. 예전에 쓰던 트레드밀 하네스는 어깨와 골반 부위를 쓸리고 멍들게 했다.
- 문단 `cdc:skin-05#p1`: 직접 닿아서 생긴 자극은 대개 그 물질이 닿은 자리에 머무르지만, 알레르기 반응은 닿은 자리를 넘어 퍼질 수 있고 두 가지는 겉모습이 비슷하다. 그래서 발진이 어디에 있는지, 무언가 닿는 자리와 겹치는지, 며칠 사이에 퍼지는지 가라앉는지를 적어 두면 도움이 된다.
- **1차** 통과 [skin_irritation]: 장비와의 마찰이나 압박으로 인해 피부에 상처나 발진이 생길 가능성이 있어요. / 발진이 있는 위치가 장비와 닿는 곳과 겹치는지, 며칠 사이에 퍼지는지 살펴보는 게 좋아요.

### ET-027 · en · caution · 후보 skin_irritation · 시험 전용 문단

- 문단 `lit:skin-01#p1`: Rashes and similar skin complaints have been among the most frequently recorded symptoms on long orbital missions, with many notable episodes starting in the first month. They usually appear as bumps or small scaly patches, with or without redness and itching, and the exact cause is seldom confirmed in flight.
- 문단 `cdc:skin-06#p1`: Flight stressors may reawaken dormant viruses such as the one behind shingles. Shingles shows as a painful, usually itchy, blistering rash in a single stripe on one side of the body or face, and pain, itching or tingling in that area can come several days before the rash.
- **1차** 통과 [skin_irritation]: Skin complaints like rashes or scaly patches can occur frequently during orbital missions. / Monitor for any new bumps or itching that may appear on your skin.

### ET-028 · en · advisory · 후보 skin_irritation

- 문단 `hrp:skin-02#p1`: Gear that presses or rubs can damage the skin. Soft parts of the spacesuit often cause scrapes and bruises at the wrists, arms, knees and ankles, wrinkles in boots can raise blisters, damp gloves are linked to hand and nail injury, and an earlier treadmill harness chafed and bruised shoulders and hips.
- 문단 `nih:skin-04#p1`: Where a likely trigger can be identified, such as a soap or cleanser, damp clothing, rough fabric, or a strap or sensor resting on the spot, reducing contact with it is a reasonable first step. Avoiding identified irritants is among the measures suggested for persistent skin symptoms in flight.
- **1차** 통과 [skin_irritation]: Gear that presses or rubs can damage the skin and may cause scrapes or bruises. / If a trigger like a strap or sensor is identified, reducing contact with it can help manage symptoms.

### ET-029 · ko · caution · 후보 sleep_deficit, mood_low · 시험 전용 문단

- 문단 `hrp:sleep-01#p1`: 우주에서 승무원이 실제로 잔 시간은 하루 평균 여섯 시간 정도로, 비행 전보다 조금 짧았다. 과중한 업무와 갑작스러운 일정 변경, 지상과 다른 낮과 밤의 주기는 생체 시계를 정해진 수면 시간과 어긋나게 할 수 있다. 다만 우주 환경 자체와 임무 부담 가운데 어느 쪽의 영향이 더 큰지는 아직 밝혀지지 않았다.
- 문단 `hrp:sleep-01#p2`: 잠을 짧게 자는 날이 이어지면 업무 수행 능력은 날이 갈수록 계속 떨어지지만, 졸리다는 느낌은 조금 커지다가 더는 커지지 않는다. 그래서 스스로 느끼는 것보다 실제 능력이 더 떨어져 있을 수 있다. 지금 정신이 얼마나 또렷하게 느껴지는지만 보지 말고 최근 며칠 동안 얼마나 잤는지도 함께 살펴보는 것이 좋다.
- **1차** 통과 [sleep_deficit]: 잠을 짧게 자는 날이 이어지면 스스로 느끼는 것보다 업무 능력이 더 떨어져 있을 가능성이 있어요. / 정신이 또렷한 느낌뿐만 아니라 최근 며칠 동안 얼마나 잤는지도 함께 살펴보는 게 좋아요.

### ET-030 · ko · advisory · 후보 sleep_deficit

- 문단 `nih:sleep-01#p1`: 성인은 대개 하루에 적어도 일곱 시간은 자야 하지만, 필요한 수면 시간은 사람마다 다르다. 필요한 만큼 자지 못하는 날이 이어지면 모자란 잠이 하루하루 쌓이며, 이렇게 쌓인 수면 부족은 질 좋은 잠을 자야만 해소된다.
- 문단 `hrp:sleep-02#p1`: 빛이 모자라거나 빛을 받는 시간대가 맞지 않으면 생체 시계가 흐트러질 수 있어, 우주정거장의 조명은 지구의 낮과 밤 주기를 본뜨도록 만들어져 있다. 일하는 시간에는 밝은 조명을, 잠들기 전에는 더 어두운 조명을 쓰는 것이 이 원리에 맞다. 잠들기 전에 긴장을 풀 시간이 모자라면 잠들기 어렵다는 승무원들의 보고도 있으므로 그 시간을 지키는 것이 좋다.
- **1차** 통과 [sleep_deficit]: 잠이 부족한 날이 계속되면 피로가 쌓여 컨디션에 영향을 줄 수 있어요. / 잠들기 전에 긴장을 풀 수 있는 시간을 확보하고 조명을 조절해 보는 게 좋아요.

### ET-031 · en · caution · 후보 sleep_deficit, mood_low · 시험 전용 문단

- 문단 `hrp:sleep-01#p1`: Crews in space have averaged about six hours of sleep a night, somewhat less than before flight. Heavy workloads, abrupt schedule shifts and unusual light–dark cycles can push the body clock out of step with the sleep period, but whether the space environment itself or mission demands matter most is not settled.
- 문단 `hrp:sleep-01#p2`: When nights stay short, performance keeps slipping with each further night, while the feeling of sleepiness rises only a little and then levels off. People can therefore be more impaired than they feel, so it is worth looking at how the last several nights have gone, not only at how awake one feels.
- **1차** 통과 [sleep_deficit]: Short sleep periods can push your body clock out of step and may lead to performance slips that you might not feel. / It is worth looking at how the last several nights have gone, as you can be more impaired than you feel.

### ET-032 · en · advisory · 후보 sleep_deficit

- 문단 `nih:sleep-01#p1`: Most adults need at least seven hours of sleep a night, though the exact need differs from person to person. When sleep keeps falling short of that need, the shortfall builds up night after night, and only good-quality sleep can make it up.
- 문단 `ochmo:sleep-01#p1`: A sleep space that is cool, with air flowing from head to foot, and shielded from noise and light can make sleep easier. Earplugs, an eye mask and extra layers to adjust warmth can help, and in weightlessness a snugly fastened sleeping bag suits people needing the feeling of being held down.
- **1차** 통과 [sleep_deficit]: Shortfalls in sleep can build up night after night, which may impact your recovery. / Ensure your sleep space is cool and shielded from noise and light to improve sleep quality.

### ET-033 · ko · caution · 후보 space_motion_sickness, dehydration · 시험 전용 문단

- 문단 `hrp:sms-01#p1`: 중력이 달라지면 멀미가 나고 방향 감각이 흐트러질 수 있으며, 우주비행사 대부분은 비행 중에 멀미를 겪는다. 지구에서 차나 배, 비행기를 탈 때 멀미를 하는지 여부로는 우주에서 멀미가 얼마나 심할지 예측할 수 없다.
- 문단 `hrp:sms-01#p2`: 멀미가 난 승무원은 임무 작업이나 우주선 조종, 선외 활동(우주 유영)을 제대로 해내기 어려울 수 있고, 우주복 안에서 구토하면 위험하다. 그래서 비행 첫 사흘 동안은 선외 활동 일정을 잡지 않고 초반 일정을 가볍게 짠다. 이런 작업을 앞두고 증상이 남아 있으면 미리 알리는 것이 좋다.
- **1차** 통과 [space_motion_sickness]: 중력 변화로 인해 멀미가 나거나 방향 감각이 흐트러질 가능성이 있어요. / 증상이 남아 있다면 임무 수행에 어려움이 있을 수 있으니 미리 알려주는 게 좋아요.

### ET-034 · ko · advisory · 후보 space_motion_sickness

- 문단 `hrp:sms-03#p1`: 우주 멀미를 나타내는 신호로 검증된 웨어러블 측정값은 없다. 현재 승무원 연구에 쓰이는 웨어러블 기기는 움직임, 수면, 심장 활동, 피부 온도 등을 기록하지만 이를 멀미와 연결 짓지는 않으며, 지상 실험에서는 멀미에 대한 신체 반응이 사람마다 크게 달랐다. 따라서 본인이 느끼고 알리는 증상이 판단의 기준이 된다.
- 문단 `ochmo:sms-01#p2`: 머리나 온몸을 움직이면 우주 멀미가 시작되거나 심해질 수 있으며, 고개를 앞뒤로 끄덕이는 움직임이 증상을 가장 잘 일으키는 것으로 보고된다. 머리 움직임과 활동을 줄이거나, 잠시 눈을 감거나, 한 가지 작업에 집중하면 증상이 가라앉을 수 있다.
- **1차** 통과 [space_motion_sickness]: 머리나 몸을 움직일 때 우주 멀미 증상이 나타날 가능성이 있어요. / 움직임을 줄이거나 잠시 눈을 감고 한 가지 작업에 집중하는 게 도움이 될 수 있어요.

### ET-035 · en · caution · 후보 space_motion_sickness, dehydration · 시험 전용 문단

- 문단 `hrp:sms-01#p1`: Changes in gravity can bring on motion sickness and disorientation, and most astronauts become motion sick at some point in flight. Whether a person gets sick in cars, boats or planes on Earth does not predict how sick they will be in space.
- 문단 `hrp:sms-01#p2`: A crew member who is motion sick may struggle with mission tasks, vehicle controls or a spacewalk, and vomiting inside a spacesuit is dangerous. For this reason spacewalks are not scheduled in the first three days and the first flight days are kept light. Symptoms still present before such a task are worth reporting beforehand.
- **1차** 통과 [space_motion_sickness]: Changes in gravity can bring on motion sickness and disorientation, which may impact your ability to perform mission tasks. / Symptoms present before a task are worth reporting beforehand.

### ET-036 · en · advisory · 후보 space_motion_sickness

- 문단 `ochmo:sms-01#p1`: The cause of space motion sickness is not known for certain. The most widely accepted explanation is a sensory mismatch: in weightlessness, information from the eyes, the inner ear, and the senses of body position and touch no longer matches the patterns the brain learned under gravity.
- 문단 `ochmo:sms-01#p3`: Being too warm, bad smells, unpleasant sights and certain foods can start or worsen space motion sickness, as can losing a clear visual sense of which way is up. More air movement is one of the listed non-drug measures, so a cooler spot with moving air may help.
- **1차** 통과 [space_motion_sickness]: Sensory mismatches in weightlessness may cause space motion sickness. / Moving to a cooler spot with more air movement may help alleviate symptoms.

### ET-037 · ko · caution · 후보 upper_respiratory, dehydration · 시험 전용 문단

- 문단 `ochmo:uri-01#p1`: 무중력에서는 체액이 머리 쪽으로 쏠리기 때문에 코막힘과 머리가 꽉 찬 느낌, 얼굴 부기가 흔히 나타나며 승무원의 절반 이상이 겪는다. 이런 코막힘은 비행에 적응하는 과정에서 예상되는 변화이며, 그것만으로는 감염의 신호가 아니다.
- 문단 `ochmo:uri-04#p2`: 감기는 기침과 재채기, 손, 함께 쓰는 표면, 가까운 접촉을 통해 옮는다. 그래서 감기 같은 증상이 있을 때는 발사 전 격리에서 쓰는 방법대로 손을 자주 닦고, 기침과 재채기를 가리고, 선내 여건이 되는 만큼 동료와 거리를 두는 것이 좋다.
- **1차** 통과 [upper_respiratory]: 무중력 환경에서는 체액이 머리 쪽으로 쏠려 코막힘이나 얼굴 부기가 나타날 가능성이 있어요. / 감기 같은 증상이 느껴진다면 손을 자주 닦고 동료와 거리를 두는 게 좋을 수 있어요.

### ET-038 · ko · advisory · 후보 upper_respiratory

- 문단 `cdc:uri-03#p1`: 감기는 코와 목에 생기는 바이러스 감염으로, 콧물이나 코막힘, 재채기, 기침, 인후통, 가벼운 몸살 기운이 나타날 수 있고 성인은 열이 나더라도 대개 미열에 그친다. 기침과 재채기로 튀는 침방울, 오염된 손과 표면, 가까운 접촉을 통해 옮으며, 밀폐된 거주 공간에서는 미생물이 사람 사이에 더 쉽게 옮겨 간다.
- 문단 `cdc:uri-03#p2`: 감기 증상은 대개 이삼일 안에 가장 심해지고 일주일이 되기 전에 대부분 가라앉는다. 증상이 나아지고 있는지, 열이 있는지와 며칠째 이어지는지, 좋아지던 증상이 다시 나빠지는지를 날마다 확인해 두는 것이 좋다.
- **1차** 통과 [upper_respiratory]: 코나 목의 감염으로 인해 몸살 기운이나 미열이 나타날 가능성이 있어요. / 증상이 나아지고 있는지, 열이 있는지, 며칠째 이어지는지를 매일 확인해 보는 게 좋아요.

### ET-039 · en · caution · 후보 upper_respiratory, dehydration · 시험 전용 문단

- 문단 `ochmo:uri-01#p1`: In weightlessness body fluid shifts toward the head, and a stuffy nose, a full-feeling head and a puffy face are expected effects that more than half of crew members experience. This congestion is part of adapting to flight and is not, on its own, a sign of infection.
- 문단 `ochmo:uri-04#p2`: A cold passes on through coughs and sneezes, hands, shared surfaces and close contact. When someone has cold-like symptoms, the measures used in pre-launch isolation can be applied on board as far as the cabin allows: clean hands often, cover coughs and sneezes, and keep some distance from crewmates.
- **1차** 통과 [upper_respiratory]: Congestion and a full-feeling head are common effects of fluid shifts in weightlessness and may not indicate an infection. / If you develop cold-like symptoms, you can maintain distance from crewmates and practice frequent hand washing.

### ET-040 · en · advisory · 후보 upper_respiratory

- 문단 `nasa:uri-08#p1`: In flight, people often drink less than before launch and less than recommended, possibly because thirst is blunted, so thirst may be a poor prompt. Drinking too little raises the chance of kidney stones, and a larger fluid shortfall can impair concentration and coordination. Plenty of fluids is also part of basic care for a cold.
- 문단 `lit:uri-02#p2`: Recorded congestion was most frequent in the first week of flight and dropped sharply in the second, but entries continued late into missions, which may point to other triggers. It helps to note when stuffiness began and whether anything new, such as a sore throat, cough or fever, has joined it.
- **1차** 통과 [upper_respiratory]: A higher heart rate may be linked to a cold, as drinking plenty of fluids is part of basic care. / Note if you have any new symptoms like a sore throat, cough, or fever.

