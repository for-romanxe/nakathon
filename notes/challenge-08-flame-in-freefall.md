# 주제 8 · Flame in Freefall: AI-Powered Fire Safety Insights from Microgravity Combustion Data

확인일 2026-10-06. 출처: Space Apps 공개 GraphQL API (`api.spaceappschallenge.org/graphql`), 2026 이벤트 챌린지 14개.
"8번"은 사이트 기본 정렬(알파벳순) 기준 8번째. 공식 번호 체계가 따로 있는지는 확인 필요.

## 공개된 요약 (원문)
> For decades, NASA has studied how flames and fire behave in microgravity, gathering a trove of experimental data along the way. That knowledge matters more than ever as humans gear up to return to the Moon and press on to Mars, yet the volume of results makes them hard to find, compare, and understand. Your challenge is to create an interactive, AI-powered dashboard that summarizes, ranks, and interprets those findings to deliver fire safety insights for human space exploration.

- 상세 설명·리소스 탭은 아직 비어 있음(10/6 기준). 전문·데이터셋 공개는 10/28 예정이라는 보도.

## 요구 사항 해석
- 산출물: **인터랙티브 AI 대시보드**
- 동사 셋: 요약(summarize) · 순위(rank) · 해석(interpret)
- 대상: "수십 년"치 미세중력 연소 결과 → 실험 **하나**가 아니라 **여러 실험을 가로지르는** 비교

## PSI의 연소 과학 실험 24건 (PSI 검색 API 기준)
ACME 계열(PSI-10, 20~23, 159) · BASS(PSI-26) · **BASS-II(PSI-25)** · CFI(39) · DAFT(47) · FLEX/FLEX-2(69/68) · SAFFIRE I~III(98~100) · SAME/SAME-R(102/101) · SLICE(106) · SPICE(107) · 모델링·분석 과제 6건(60, 62, 115, 117, 142 등)
- "Spacecraft Fire Safety" 하위 분야만 10건

## PSI-25와의 관계
- 주제와 잘 맞음: ISS 미세중력 고체 연소, 연구 목적 자체가 우주선 화재 안전
- 다만 주제는 여러 실험의 결과 비교라서 PSI-25는 **후보 데이터 중 하나**. 공식 데이터셋 목록에 들어가는지는 10/28 확인 필요
- PSI-25 단독으로는 결과 수치가 없고 영상만 있음 → 대시보드 재료로는 메타데이터(목적·가설·조건)와 논문 결과가 더 직접적
