# NASA Space Apps Challenge 2026 — 서울 준비

팀 `Nakathon` 공용 레포. **먼저 읽을 것: [`docs/CONTRACT.md`](docs/CONTRACT.md)** (이름·enum·API·모델 경계 계약, 기계용 사본은 `contracts/`). 제품 명세는 `docs/superpowers/specs/2026-11-11-crew-health-product-spec.md`.

## 확인된 사실
- 행사: NASA Space Apps Challenge, 서울 로컬 이벤트
- 일정: 2026-11-14 09:00 시작 ~ 11-15 23:59 제출 마감(23:55 권장), 100% 온라인(서울 1차 안내 11/8)
- 규칙: 제출용 코드·디자인·발표 자료·영상은 행사 중에만 제작. 사전엔 챌린지 검토·자료 탐색·도구 학습만
- 등록: 2026-09-30 14:35
- 팀: `Nakathon` (가입 승인 2026-09-30 20:02)
- 주제(11/11 팀 결정): Create Health Monitoring Software for Astronauts on Space Missions → `notes/health-monitoring-decisions.md`
- 방향: 온디바이스 SLM + 규칙 기반 판단 + 근거 검색 + 검증 → `notes/health-monitoring-idea-context.md`

## 확인 필요
- 제출 항목 상세 (11/14 08:00 Zoom에서 설명)
- AI 코딩 도구 사용 가능 여부 (안내 메일에 언급 없음)

## 폴더
- `frontend/` `backend/` — 행사 중 생성(계약 §1 참조)
- `contracts/` — enum·JSON 스키마 (코드에서 로드, 하드코딩 금지)
- `docs/` — 명세·계약·운영진 안내 슬라이드
- `ml/` — 모델 학습·평가 파이프라인 (결과: `notes/model-candidates.md`)
- `mockup/` — 정적 HTML 목업
- `notes/` — 챌린지 조사, 아이디어, 회의 기록
- `data/` — 공개 데이터 등 (대용량은 커밋하지 않음). PSI-25 자료는 이전 후보 주제 8의 흔적
