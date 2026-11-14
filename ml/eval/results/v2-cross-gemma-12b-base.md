# 평가셋 v2 — cross · gemma-12b-base · 2026-11-14T14:48

```
explain  all: first-run pass 10/10  hold 0/10  picked first candidate 10/10  해요체 10/10  avoid-term hits 0
latency  explain median 3.8s  max 38.0s  (n=10)
```

## 증상: 틀린 문항

| # | 종류 | 문장 | 기대 | 금지 | 모델이 낸 코드 |
|---|---|---|---|---|---|

## 기분: 범위 밖 문항

| # | 문장 | 기대 범위 | 모델 (mood / fatigue / stress) |
|---|---|---|---|

## 설명: 문단과 답을 나란히 (뜻이 맞는지는 사람이 읽어야 한다)

### EX-001 · ko · advisory · 후보 co2_headache · 시험 전용 문단

- 문단 `hrp:co2-01#p1`: Noise, heat, cold and still air are cabin conditions a person can notice directly, and living quarters are meant to be neither too hot, too cold nor too loud. Noise can bring irritation, headaches and poorer sleep even when it does not seem harmful, and comfort differs between people, so local airflow and clothing are meant to be adjustable.
- 문단 `nasa:co2-01#p3`: A headache from carbon dioxide is described as responding poorly to ordinary headache treatment and as usually easing once the level of the gas is reduced, for which crews have procedures. Other headaches in flight are commonly managed with sleep, exercise, fluids and common pain relief.
- **1차** 통과 [co2_headache]: 이산화탄소 수치가 높으면 일반적인 두통 치료에 잘 반응하지 않을 가능성이 있어요. / 가스 수치가 낮아지면 증상이 완화될 수 있으니 관련 절차를 확인해 보는 게 좋아요.

### EX-002 · ko · advisory · 후보 dehydration · 시험 전용 문단

- 문단 `lit:dehy-08#p2`: In one study on Earth, skin temperature ran a little above personal baseline around the start of an infection in most participants, yet the same rule also flagged people with no fever and missed some with fever. A rise is a reason to look for a cause, not a sign that fever, infection or dehydration is present.
- 문단 `hrp:dehy-04#p1`: Long-duration crews have passed markedly less urine in flight than before flight. A low urine volume is linked to a higher chance of kidney stones, which is one reason to keep track of urine and fluid intake together.
- **1차** 통과 [dehydration]: 비행 중 소변량이 줄어들면 신장 결석이 생길 가능성이 있을 수 있어요. / 수분 섭취량과 소변량을 함께 확인해 보는 게 좋을 것 같아요.

### EX-003 · ko · advisory · 후보 mood_low · 시험 전용 문단

- 문단 `hrp:mood-02#p4`: Mood and morale can rise and fall over a long mission, and the pattern differs widely from person to person. Studies do not agree on when a low point tends to come, so it makes sense to follow one's own trend over time and not the stage of the mission.
- 문단 `hrp:mood-02#p2`: Support tends to help most when it comes from the people closest to the problem: a crewmate for work stress, family for worries about home. Sharing concerns instead of holding them in, and using the scheduled private talks with family and with medical or psychological staff, are part of how crews are supported.
- **1차** 통과 [mood_low]: 긴 임무 중에는 기분이 떨어질 수 있고, 이는 개인마다 다른 양상으로 나타날 가능성이 있어요. / 자신의 변화를 살피면서 동료나 가족과 고민을 나누는 게 도움이 될 수 있어요.

### EX-004 · ko · advisory · 후보 musculoskeletal_strain · 시험 전용 문단

- 문단 `nasa:msk-08#p1`: In flight, crews have often eaten less than their bodies needed. Eating too little goes with loss of muscle and bone and lower endurance, and exercise adds to the energy required, so meals need to keep pace with training. Limited menu variety can dull appetite, and no wearable signal has been validated as showing an energy shortfall.
- 문단 `nih:msk-05#p1`: For a minor strain, stop the movement that hurts instead of pushing through it, rest the area for a day or two, and then build activity back up gradually. Where a cold pack is available, short sessions may ease pain early on, and heat is better left until about three days have passed.
- **1차** 통과 [musculoskeletal_strain]: 가벼운 통증이 느껴진다면 무리하게 움직이지 말고 휴식을 취하는 게 좋을 수 있어요. / 통증이 있는 부위를 하루 이틀 정도 쉬게 한 뒤에 활동량을 서서히 늘려보세요.

### EX-005 · ko · advisory · 후보 orthostatic_intolerance · 시험 전용 문단

- 문단 `nasa:oi-07#p1`: Standing tolerance has never been measured in partial gravity, so it is unknown whether Mars gravity, about one-third of Earth's, protects against light-headedness on standing. The conservative planning assumption, made so far for the Moon, is that partial gravity does not protect. Fainting there could also have worse consequences, since no medical team is waiting on site.
- 문단 `cdc:oi-09#p1`: A standard clinical check for this problem compares blood pressure taken after lying down for several minutes with readings taken one and three minutes after standing up. A clear fall in pressure, or light-headedness or dizziness on standing, counts as abnormal. After landing or on the surface, it can serve as a simple recheck when a cuff is available.
- **1차** 통과 [orthostatic_intolerance]: 기립 시 어지러움이나 혈압이 떨어지는 증상이 나타날 가능성이 있어요. / 일어설 때 몸의 상태를 살피고, 필요하다면 혈압 변화를 확인해 보는 게 좋아요.

### EX-006 · ko · advisory · 후보 sans_suspect · 시험 전용 문단

- 문단 `hrp:sans-01#p1`: In long periods of weightlessness, blood and the fluid around the brain and spinal cord shift toward the head. This can lead to swelling of the optic nerve, folds in the retina and flattening of the back of the eye, a group of changes known as spaceflight associated neuro-ocular syndrome (SANS).
- 문단 `hrp:sans-02#p1`: When a crew member with SANS notices anything, it is usually blurred near vision or tired eyes during close work, caused by a shift toward far-sightedness. The eye finds this harder to make up for with age, particularly after about forty. A change in near vision is worth mentioning at the next medical check-in.
- **1차** 통과 [sans_suspect]: 무중력 상태에서 체액이 머리 쪽으로 쏠려 시신경이 붓거나 눈의 모양이 변할 가능성이 있어요. / 가까운 곳이 흐릿하게 보이거나 눈이 피로한 느낌이 든다면 다음 검진 때 말씀해 주시는 게 좋아요.

### EX-007 · ko · advisory · 후보 skin_irritation · 시험 전용 문단

- 문단 `lit:skin-01#p1`: Rashes and similar skin complaints have been among the most frequently recorded symptoms on long orbital missions, with many notable episodes starting in the first month. They usually appear as bumps or small scaly patches, with or without redness and itching, and the exact cause is seldom confirmed in flight.
- 문단 `cdc:skin-06#p1`: Flight stressors may reawaken dormant viruses such as the one behind shingles. Shingles shows as a painful, usually itchy, blistering rash in a single stripe on one side of the body or face, and pain, itching or tingling in that area can come several days before the rash.
- **1차** 통과 [skin_irritation]: 장기 임무 중에는 피부 발진이나 비슷한 증상이 나타날 가능성이 있어요. / 작은 돌기나 비늘 같은 부위가 생기는지 잘 살펴보는 게 좋아요.

### EX-008 · ko · advisory · 후보 sleep_deficit · 시험 전용 문단

- 문단 `hrp:sleep-01#p1`: Crews in space have averaged about six hours of sleep a night, somewhat less than before flight. Heavy workloads, abrupt schedule shifts and unusual light–dark cycles can push the body clock out of step with the sleep period, but whether the space environment itself or mission demands matter most is not settled.
- 문단 `hrp:sleep-01#p2`: When nights stay short, performance keeps slipping with each further night, while the feeling of sleepiness rises only a little and then levels off. People can therefore be more impaired than they feel, so it is worth looking at how the last several nights have gone, not only at how awake one feels.
- **1차** 통과 [sleep_deficit]: 수면 시간이 짧아지면 실제 느끼는 것보다 수행 능력이 저하될 가능성이 있어요. / 최근 며칠간의 수면 상태가 어땠는지 한번 살펴보는 게 좋아요.

### EX-009 · ko · advisory · 후보 space_motion_sickness · 시험 전용 문단

- 문단 `hrp:sms-01#p1`: Changes in gravity can bring on motion sickness and disorientation, and most astronauts become motion sick at some point in flight. Whether a person gets sick in cars, boats or planes on Earth does not predict how sick they will be in space.
- 문단 `hrp:sms-01#p2`: A crew member who is motion sick may struggle with mission tasks, vehicle controls or a spacewalk, and vomiting inside a spacesuit is dangerous. For this reason spacewalks are not scheduled in the first three days and the first flight days are kept light. Symptoms still present before such a task are worth reporting beforehand.
- **1차** 통과 [space_motion_sickness]: 중력 변화로 인해 우주 멀미나 방향 감각 상실이 나타날 가능성이 있어요. / 임무 수행에 어려움을 겪을 수 있으니 증상이 있다면 미리 알려주는 게 좋아요.

### EX-010 · ko · advisory · 후보 upper_respiratory · 시험 전용 문단

- 문단 `ochmo:uri-01#p1`: In weightlessness body fluid shifts toward the head, and a stuffy nose, a full-feeling head and a puffy face are expected effects that more than half of crew members experience. This congestion is part of adapting to flight and is not, on its own, a sign of infection.
- 문단 `ochmo:uri-04#p2`: A cold passes on through coughs and sneezes, hands, shared surfaces and close contact. When someone has cold-like symptoms, the measures used in pre-launch isolation can be applied on board as far as the cabin allows: clean hands often, cover coughs and sneezes, and keep some distance from crewmates.
- **1차** 통과 [upper_respiratory]: 무중력 상태에서는 체액이 머리 쪽으로 쏠려 코가 막히거나 얼굴이 부을 수 있어요. / 감염이 의심될 때는 손을 자주 씻고 기침을 가릴 때 거리를 유지하는 게 좋을 수 있어요.

