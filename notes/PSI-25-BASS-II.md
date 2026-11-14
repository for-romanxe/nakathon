# PSI-25 · BASS-II (Burning and Suppression of Solids II) 데이터셋 훑어보기

조사일 2026-10-06. 출처: https://psi.nasa.gov/physci/repo/data/investigations/PSI-25
주제 8(Flame in Freefall)과 잘 맞음. 다만 주제는 여러 실험 비교라 PSI-25는 후보 중 하나 → [[challenge-08-flame-in-freefall]]

## 개요
- ISS 미세중력 고체 연료 연소 실험. Microgravity Science Glovebox 안의 소형 풍동(기류 최대 40 cm/s)
- 연구 분야: 연소 과학 / 우주선 화재 안전. 관리 센터 GRC
- 기간 메타데이터 2010~2022, 실제 시험은 2014년(2/19 ~ 8월)
- DOI 10.60555/4qc4-de67 · 라이선스 CC0 · 공개 다운로드 가능(로그인 불필요)
- 가설: 환기가 충분하면 미세중력에서 재료가 지상보다 같거나 더 잘 탈 수 있다 → 지상 상향 연소 시험(NASA-STD-6001 Test 1)이 우주에선 보수적이지 않을 수 있음
- 주요 변수: 기류 속도·방향(대향류/동향류), 산소 농도(질소로 21% 이하로 낮춤), 시료 형상(봉, 구 단면, 슬랩, 필름, 직물)

## 파일 (총 694개, 약 275 GB)
| 종류 | 개수 | 용량 | 내용 |
|---|---|---|---|
| mp4 | 296 | 17.7 GB | 시험별 영상, 2nd view, Still_Sequence |
| zip `iss0xxe…` | 91 | 대부분 | Nikon D300S RAW(NEF, 4288×2848) 고해상도 스틸 연속 촬영 |
| zip `… original videos` | 약 80 | 각 ~10 MB | 원본 `.ts` (h264 720×480, 29.97fps, 예: 58초) |
| zip `GMT…_BASS_S…` | 21+ | 최대 3.5 GB | 시험별 묶음(내용 미확인) |
| pdf | 127 | 0.17 GB | 시험별 ProofSheet(사진 밀착 인화) + 논문 |
| 문서 | 소수 | 작음 | 실험 표 CSV, 팬 보정 xlsx, ReadMe·Test Matrices·Ops(현재 404) |

## 실험 표 (data/PSI-25_Experimental table_BASS-II.csv, 129건 × 17열)
- 열: PI, Test #, 날짜, GMT일, 시료 번호, 연료 재질, 유량 제한기, 팬 표시값, 공기 표시값, 복사계 게인, 촬영 프레임 수, 초기/최종 O2 %, 초기/최종 CO2 %, 초기/최종 CO ppm
- PI 6명별 시험군: T'ien 29, Olson 27, Fernandez-Pello 27, Bhattacharjee 22, Miller 20, Ferkul 4
- 연료 예: PMMA 필름(100~300 µm), PMMA 봉(1/4", 3/8" 투명·검정), SIBAL 직물(1·2 cm)
- **정리 필요**: 숫자 열에 `none`, `video`, `250>50`, `55 47 etc` 같은 자유 텍스트가 섞여 있음. 팬 값은 표시값이라 유속(cm/s)으로 바꾸려면 팬 보정 표가 필요

## 해커톤 관점 메모
- 숫자로 바로 쓸 수 있는 건 표 하나(129행)뿐. 화염 확산 속도 같은 결과값은 **영상·사진에서 직접 뽑아야** 함
- 작은 단위부터: 시험별 원본 `.ts`(~10 MB)나 mp4 몇 개로 화염 선단 추적 프로토타입 가능
- NEF zip은 개당 수 GB → 전부 받지 말고 표본만
- 다운로드 방식: `GET https://psi.nasa.gov/geode-py/ws/studies/PSI-25/download?file=<파일명>&redirect=false` → S3 presigned URL 반환
- 메타데이터 API: `https://psi.nasa.gov/geode-py/ws/repo/investigations/PSI-25` (파일 목록은 `added` 필드)

## 영상 확인 (2026-10-08, 시험 B2 원본 .ts 1개)
- 불꽃이 선명하게 찍힘: 점화 → 옆으로 길어지며 번짐 → 마지막 장면에서 사라짐
- 화면 위에 측정값이 글자로 박혀 있음: `FUEL AIR FAN RAD` + 날짜·시각. RAD(복사계)는 0.06 → 1.51로 오르다 끝에서 0.94, FAN은 62 → 38
- → 글자 인식(OCR)으로 시각별 측정값을 뽑을 수 있음. 불꽃 길이·밝기는 영상에서 직접 측정 가능
- 주의: 화면 날짜는 02/20/14, 실험 표의 B2 날짜는 2/19/2014 → 기준 시간대 차이인지 확인 필요
