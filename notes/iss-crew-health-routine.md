# ISS 승무원이 실제로 하는 건강 루틴 (조사, 2026-11-11)

목적: "이미 하는 일을 한곳에 모아 가볍게" 만들려면 실제 과업 목록과 주기가 필요. 아래는 NASA 공개 문서에서 확인한 것만. 추측은 표시.

## 1. 실제 하루 (ISS Form 24 타임라인, 2013-10-11, Radiogram 3680u)
출처: https://www.nasa.gov/sites/default/files/files/101113_tl.pdf (같은 양식 2013-08-28: .../082813_tl.pdf)
- 기상 06:00 · 취침 21:30 (수면 블록 8.5h)
- Post-sleep 30분 블록(아침 위생·식사·준비), Pre-sleep 블록 저녁
- 운동: 승무원마다 ARED(저항) 85~90분 + T2(트레드밀) 또는 CEVIS(자전거) 60분 → 하루 약 2.5시간 일정에 박혀 있음. 러시아 측은 БД-2·VELO.
- Reaction Self Test 5분: 기상 직후와 취침 직전 (FE-5, FE-6)
- ENERGY Diet Log of Breakfast 5분 (연구 참여자만)
- Food Frequency Questionnaire 10분 (주 단위 연구 항목)
- SHD Weekly Questionnaire 5분
- 소변 샘플 채취 20분, 타액·혈액 채취 30분 (연구 세션 날만)
- Ocular Health 심장 측정 60분 (주기 연구)

## 2. 의료 요구사항 (NASA OCHMO-STD-100.1A, 2023)
출처: https://www.nasa.gov/wp-content/uploads/2023/04/ochmo-std-100.1a.pdf
| 항목 | 요구 id | 주기 (180일 ISS 예시) | 내용 |
|---|---|---|---|
| Private Medical Conference (비행의와 사적 면담) | [6003] | L+1~7일, 이후 **매주**, EVA 전후, R-5일부터 매일 | 건강 모니터링·상담·거주성 논의 |
| CMO Health Status Evaluation | [6002] | L+14/21, 90, 180, 270일, R-21/14 | 병력 + 활력징후(체온·혈압·맥박·호흡), 필요 시 혈액검사 [6019] |
| 체질량 측정 | [6015] | L+7(기준), 이후 **매월** | 질량 측정 장치 |
| 영양 평가 | [6038] | 식이 설문 **매주**, 체질량 매월 | 섭취 패턴·질량 변화·에너지 소비 |
| 수면 평가 | [6039] | **매일** 수면 질·양 기록 → **매주** PMC에서 보고 | 승무원과 비행의가 함께 봄 |
| 근력·컨디셔닝 모니터링 | [6025] | L+14일부터 30일마다 | 운동 장비 데이터·영상이 **지상으로 자동 다운링크**, 전문가 권고 |
| 유산소 능력 검사 | [6028] | 주기적, EVA 전 | 자전거 부하 검사 |
| 개인 선량계 | [6022] | 상시 | 방사선 |
| 안구 평가 | [6012] | L+30, 90, 180, 270 / 일부 30일마다 | 안압·안저 등 |
| 소변검사 | — | L+180, 필요 시 | 비중·단백·케톤 등 |
| 30일 임무 운동 예시 | [6025] | 저항 주3회 60분, 유산소 주3회 30분 | (단기 임무) |

## 3. Standard Measures (HRP 공통 측정, 2020 / BHP 2017)
출처: https://ntrs.nasa.gov/api/citations/20200001281/downloads/20200001281.pdf , https://ntrs.nasa.gov/api/citations/20170005421/downloads/20170005421.pdf
- 손목 액티그래피(Actiwatch Spectrum) FD1~R-0 **연속 착용** (활동·광노출)
- 짧은 post-sleep 설문 **매일**(지상 구간에 명시; 비행 중은 월간 설문)
- Sleep Quality/Team Questionnaire **매월** (수면 양·질, 기분, 정서, 팀 결속, 거주성)
- Cognition 10과제 배터리 FD30, R-30
- 혈액·타액·소변·미생물 샘플 FD30, R-30 (24h 소변은 의료 채취와 공유)
- BHP: 기분·피로·갈등·스트레스 VAS **매일** 짧은 설문, 팀 기능 설문 매일, 사회성 배지 착용
- 비행 중 승무원 시간 합계 15.25h / 180일 ≈ 하루 5분

## 4. 우리 시스템에 주는 결론
- **운동은 손으로 기록할 필요가 없다.** 장비가 데이터를 내려보낸다. 밴드로도 대체 가능. → 자동.
- **식이는 매일이 아니라 매주다.** 일일 식사 기록은 연구 참여자만. → 주 1회 짧은 설문.
- **수면 평가는 진짜 매일 요구사항**이고 매주 PMC에 보고된다. → 아침 체크인의 핵심, 주간 요약 자동 생성.
- **기분·피로·스트레스 VAS 매일**이 실제 있다. → 아침 또는 저녁에 슬라이더 2~3개.
- **Reaction Self Test**(5분)가 아침·취침 전에 있다. → 선택 항목으로 연결 가능(우리가 만들진 않음).
- **매주 PMC, 매월 체질량, 분기 HSE 활력징후**는 일정형 과업. → 시스템이 날짜를 세고 띄우며, 결과값(혈압·체온·질량)을 받는 입력 화면이 필요.
- **수분 섭취 기록은 어느 문서에도 없다.** → 넣지 않거나 주간 식이 설문에 포함.
- 승무원 시간 예산: 연구 측정 전체가 하루 5분 수준. 우리 체크인도 그 안에 있어야 설득력 있음.

## 5. 체크인 양식 초안 (조사 기반 · 결정 전)
- 아침(post-sleep 블록 안, 30초): 수면 질 1~5 · 수면 시간 자동 확인 · 기분/피로 슬라이더 · 증상 "없음" 기본
- 저녁(pre-sleep, 선택): 운동 자동 확인 · 스트레스 슬라이더 · 증상
- 주 1회(2분): 식이 설문 · PMC 전 주간 요약 확인
- 월 1회 / 분기: 체질량 · 활력징후 입력 (측정 날짜는 시스템이 띄움)

## 6. Space Apps 챌린지 페이지 (2026-11-11 확인)
출처: https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/
- **Resources 탭: "Resources will be available on Friday, November 13."** → 11/13 다시 확인 필요. 지금은 자료 없음.
- Details 탭에서 우리 방향과 직접 맞는 문장:
  - "Your tool could prompt astronauts to take measurements or complete specific actions from time to time as a part of the mission routine." → 루틴 과업 관리가 명시적으로 권장됨.
  - 기능 예시: gamification, dynamic charts over time, color coding at a glance, clickable human figure, simple instructions/explanations covering measurements, indicators, risks.
  - "Do not assume that astronauts know everything about how to assess their health." → 측정법·지표·위험 설명이 필요.
  - 입력은 keyboard text, mouse clicks, camera images 등 무엇이든. 데이터는 건강 지표를 나타내면 무엇이든(혈당 등).
  - 환경: spacecraft, space station, rover, base on another planet or moon.
- 난이도 Intermediate · Subjects: Human Exploration, Software, Space Exploration
