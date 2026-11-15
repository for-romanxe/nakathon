# 팀 계약 (CONTRACT) — 이름·형식·경계

> 이 문서는 **팀원 넷이 서로 맞춰야 하는 것만** 적는다. 제품 명세는 `docs/superpowers/specs/2026-11-11-crew-health-product-spec.md`(이하 "명세")가 원본이고, 이 문서와 명세가 다르면 **이 문서가 이긴다**(여기가 더 늦게 정해졌으므로). 바꾸고 싶으면 PR이 아니라 팀 채팅에서 한 줄 합의 후 이 파일을 고친다.
> 기계가 읽는 사본: `contracts/*.json` (enum·JSON 스키마). 코드는 여기서 import/로드하고 **하드코딩하지 않는다.**

작성 2026-11-14 (행사 시작 후). 표시 없는 항목은 명세에서 그대로 가져온 것, **[결정 11/14]**는 이 문서에서 새로 정한 것.

---

## 0. 꼭 지킬 것 5가지

1. **판정은 규칙 엔진만 한다.** 모델(SLM)은 ① 증상 문장 → enum JSON, ② 기분 문장 → 척도, ③ 설명 문장, ④ 약 안내 문장화만. 모델 출력이 경보를 **올릴 수는 있어도 낮출 수는 없다.**
2. **모든 설명 문장에는 출처 id가 붙는다** (`hrp:sm-03#p5` 형식). 출처 없는 문장은 검증기가 버린다.
3. **상태 이름·증상 코드는 고정 목록(`contracts/enums.json`)에서만.** 목록 밖 이름은 버그다.
4. **API JSON 필드는 snake_case**, 프론트도 변환 없이 그대로 쓴다. 코드 식별자는 영어, UI 문자열은 i18n 사전(ko/en)에만.
5. **제출 규정**: NASA 로고 금지(AI 이미지 포함), 미성년자 식별 정보 금지, AI 사용 내역은 프로젝트 페이지에 공개, 라이선스 Apache-2.0 **[결정 11/14]**.

---

## 1. 레포 구조 **[결정 11/14]**

```
frontend/   React + Vite (프론트 담당)         포트 5173
backend/    FastAPI + SQLite (백엔드 담당)      포트 8000
ml/         모델·학습·평가 (AI 담당)             모델 서버 포트 8080
contracts/  enum·JSON 스키마 (모두가 읽음, AI 담당이 관리)
docs/       명세·계약·발표 자료
notes/      조사·회의 기록
mockup/     정적 HTML 목업 (디자인 참고용, 코드 복붙 금지 아님)
```

- 브랜치: 각자 `main`에 바로 푸시해도 된다. 단 **푸시 전 `git pull --rebase`**, `main`에 force-push 금지, 남의 폴더 파일을 고치면 채팅으로 알린다.
- 커밋 메시지 접두어: `fe:` `be:` `ml:` `docs:` `contract:` (예: `be: 기준선 계산 14일 창`).
- 비밀·대용량(모델 가중치, 어댑터, 원본 데이터) 커밋 금지 — `.gitignore`에 이미 있음.

## 2. 이름 규칙

| 대상 | 규칙 | 예 |
|---|---|---|
| Python 변수·함수·파일 | snake_case | `compute_baseline`, `rules_engine.py` |
| Python 클래스 | PascalCase | `SymptomReport` |
| TS/JS 변수·함수 | camelCase (단, API 응답 타입의 필드는 snake_case 그대로) | `fetchToday`, `event.symptom_text` |
| React 컴포넌트·파일 | PascalCase | `TodayScreen.tsx` |
| API JSON 필드 | snake_case | `needs_question`, `baseline_days` |
| enum 값 | snake_case 영어 소문자 | `shortness_of_breath`, `after_meal` |
| i18n 키 | `screen.section.key` | `today.guide.title`, `common.level.caution` |
| 문서(출처) id | `org:slug#pN` | `hrp:sm-03#p5`, `med:ibuprofen#p2` |
| 승무원 id | `c1`~`c4` **[결정 11/14]** | CMO는 `c2` (목업 기준, 바뀌면 여기 고침) |
| 시간 | `ts` ISO 8601 문자열(가상 시계), `sol` 정수, `date` `YYYY-MM-DD` | `"2026-11-14T14:00:00Z"`, `4` |
| 지연·수치 | 단위는 필드명에 넣지 않고 `contracts/enums.json`의 metric 표를 따른다 | `hr` 는 bpm |

## 3. 고정 목록 (enum) — 원본은 `contracts/enums.json`

**지표 6개** `metric`: `hr`(안정 시 심박, bpm) · `hrv`(야간 RMSSD, ms) · `eda`(µS) · `temp`(피부온 °C) · `sleep`(h) · `act`(활동 min). 목업 `mockup/app/app.js`와 동일.

**경보 계층** `level`: `normal` | `advisory` | `caution` | `warning` | `hold`
- 색: normal=초록(`--normal`), caution=노랑, warning=빨강, advisory·hold=무색. 토큰은 `DESIGN.md`.
- hold = 기준선 14일 미만 또는 검증 2회 실패("판단 보류"). 기준선은 오늘 이전에 측정값이 있고 이벤트가 없었던 최근 14일로 계산한다.

**증상 코드** `codes[]` (14개, ml 학습셋과 동일):
`chest_pain, shortness_of_breath, dizziness, nausea, headache, fatigue, sleep_issue, musculoskeletal_pain, congestion, skin_rash, vision_change, low_mood, crisis, none`
- `onset`: `now | hours | today | days | unknown`
- `worse_when`: `standing | after_meal | exercise | lying | none | unknown`
- `severity`: 정수 1~5, `needs_question`: bool
- `locations`(선택): 보고가 말한 부위. `body_location` 값의 배열이다 — `head, neck, chest, abdomen, back, left_arm, right_arm, left_leg, right_leg, unknown`. 표시에만 쓴다(§5.5).
- **즉시 경보 코드**(규칙이 모델보다 먼저 키워드로 잡음): `chest_pain, shortness_of_breath, crisis` + 의식 변화 키워드. 걸리면 그 이벤트는 `urgent: true` (§5.4).

**체크인 종류** `checkin.kind`: `morning | evening | weekly | monthly | quarterly`
**판정 보류 이유** `metrics[].hold_reason`: `insufficient_baseline | missing_reading | zero_variance` (§5.3)
**이벤트 상태** `event.status`: `open | closed` · **무시 이유** `override.reason`: `post_exercise | wear_fault | action_done | other`
**전송** `tx.priority`: `warning | caution | daily` · `tx.status`: `queued | sent | acked | missing`
**언어** `lang`: `ko | en` · **민감도** `sensitivity`: `standard(2/3σ) | sensitive(1.8/2.6) | relaxed(2.3/3.3)`
**가이드 키** `guide_item.key`: `exercise | sleep | mood | diet_weekly | pmc_prep | body_mass | vitals | temp:<event_id> | advisory`
**상태(condition) 목록** `condition_id`: 문서 코퍼스를 만드는 사람이 `contracts/enums.json`의 `conditions`에 채운다(10~15개, 초안 포함). 모델은 이 목록 밖 이름을 못 낸다.

## 4. 모델 ↔ 백엔드 경계 (AI 담당 제공) **[결정 11/14]**

명세 §11·§18의 "Ollama" 문구는 아래로 대체한다. 측정 결과(`notes/model-candidates.md`)에 따라 기본 모델은 **Ministral 3 8B + LoRA**, 비교용 Gemma 4 E4B.

- 모델 서버는 **OpenAI 호환 `POST /v1/chat/completions`** 하나만 노출한다 (Mac: `mlx_lm.server`, PC: 같은 인터페이스). 백엔드는 이 URL만 안다.
- 백엔드 환경변수: `MODEL=mock|live` (기본 `mock`), `MODEL_URL=http://127.0.0.1:8080`, `MODEL_NAME`.
- `MODEL=mock`이면 `backend/mock/*.json`의 시나리오 응답을 1초 지연으로 돌려준다. **프론트·백엔드 담당은 mock으로 개발한다.**
- 모델 호출 함수는 `backend/model/client.py` 한 곳. 함수 3개 고정:
  - `extract_symptoms(text, lang, recent_summary) -> SymptomReport` (`contracts/symptom.schema.json`)
  - `score_mood(text, lang) -> MoodScore` (`contracts/mood.schema.json`)
  - `explain(level, findings, condition_candidates, paragraphs, lang) -> Explanation` (`contracts/explanation.schema.json`)
- 모델 출력은 **항상 검증기(`backend/verify.py`)를 거친다.** 검사 5개의 이름 고정: `numbers, cites, level, schema, wording`. 결과는 `runs[].fails[]`에 이 이름으로 기록.
- **설명은 `backend/model/pipeline.py`의 `explain_verified(level, findings, condition_candidates, paragraphs, lang)`로 만든다** **[추가 11/14]**. 생성 → 검증 → 폐기되면 한 번 더(상한 2회) → 두 번 폐기되면 판단 보류까지 이 함수가 한다. 반환 `{explanation | null, hold, verified(0~5), runs:[{n, ok, fails[], note}]}`을 이벤트의 `explanation`·`runs`·`verified`에 그대로 넣는다. `hold`가 true면 `explanation`은 null이고 화면에는 수치와 절차서만 보여 준다. `runs[].note`는 폐기 이유를 한 줄로 적은 것이다(예: `numbers: 12`). 이 함수는 예외를 던지지 않는다. 모델 서버에 닿지 못하거나 입력이 잘못돼도(목록 밖 상태 후보, `id` 없는 문단 등) `hold`로 돌아오고, 이유는 `runs[].note`에 적힌다.
- 파이프라인 단계 이름(SSE `stage` 값) 고정: `collect → rules → symptom → question → retrieve → generate → verify → done | hold`.

## 5. API (백엔드 담당 구현, 명세 §18 초안 확정) **[결정 11/14]**

기본 경로 `http://localhost:8000`, JSON, 오류는 `{ "error": { "code": "...", "message": "..." } }`.

| 메서드 | 경로 | 요청 | 응답 |
|---|---|---|---|
| GET | `/crew` | | CMO용 4명 요약 |
| GET | `/mission` | | `{clock:{sol,time}, environment, one_way_delay_min, next_window}` (§5.1) |
| GET | `/crew/{id}/today?lang=` | | `{status:{level,text}, guide:[guide_item], metrics:[{metric,value,baseline,sd,z,level,hold_reason}], events:[event], checkin:{morning_done,evening_done}, streak}` (§5.3) |
| POST | `/crew/{id}/checkin?lang=` | `{kind, answers:{…}, free_text?}` (§5.2) | 갱신된 `/today` |
| POST | `/crew/{id}/symptom` | `{text, lang}` | `{event_id, needs_question, question?}` |
| POST | `/events/{id}/answer` | `{answer:"yes"\|"no"}` | 202, 이후 `GET /events/{id}/stream` (SSE, `stage`) |
| GET | `/events/{id}` | | event 전체 (§명세 9 엔티티, `urgent`·`level`은 §5.4) |
| POST | `/events/{id}/action/{i}/done` · `/share` · `/close` | | event |
| POST | `/events/{id}/override` | `{reason, note?}` | event |
| POST | `/crew/{id}/med/ask` | `{text, lang}` | `{table:{...}, text, cites[]}` |
| POST | `/crew/{id}/med/log` | `{med_id}` | 204 |
| GET | `/crew/{id}/trends?metric=&days=` | | `{points:[{ts,value}], baseline:{mean,sd}, events:[...]}` |
| GET | `/docs` · `/docs/{id}` | | 문서 목록 / `{id,title,org,kind,paragraphs:[{n,text}]}` |
| GET/POST | `/tx` · `/tx/send` | `{event_id}` 또는 `{daily:true}` | tx_packet 목록 |
| GET/PUT | `/settings` | | settings |
| POST | `/demo/clock` | `{sol,time}` 또는 `{advance:"2h"}` | `/mission`과 같은 모양 (§5.1) |
| POST | `/demo/reset` · `/demo/viewer/{id}` | | |
| GET | `/habitat/actions?crew=c1` | | Action array for the selected crew member for the current and previous Sol |
| POST | `/habitat/actions/{id}/approve` · `/undo` | `{reason?}` (trimmed, ≤240 chars) | The updated action object (same fields as GET). Owner only (403), missing 404 `action_not_found`, stale 409 `action_stale` |

프론트 라우트(목업 파일명과 동일): `/today /body /trends /log /procedures /crew /settings /events/:id /warning`.

`?lang=ko|en`(기본 `en`)은 `/today`와 `/checkin` 응답의 `status.text`만 현지화한다. 가이드 문장은 현재 영어.

### 5.1 `/mission` — 임무 시계와 통신 상태 **[추가 11/14, PR #1·#2 구현 기준]**

```json
{ "clock": { "sol": 16, "time": "06:12" }, "environment": "mars_base", "one_way_delay_min": 12, "next_window": "08:00" }
```

| 필드 | 형식 | 뜻 |
|---|---|---|
| `clock.sol` | 정수 ≥ 1 | 임무 일차. 임무 시작일이 1 |
| `clock.time` | `"HH:MM"` (24시간) | 가상 시계의 현재 시각 |
| `environment` | 문자열 | 임무 환경. 현재 값은 `mars_base` 하나. 프론트는 i18n 키 `env.<값>`으로 표시 |
| `one_way_delay_min` | 정수(분) | 지구까지 편도 통신 지연 |
| `next_window` | `"HH:MM"` | blackout을 건너뛴 다음 통신 창이 열리는 시각. `next_window_at.time`과 같다. 창은 임무 시각 08:00·20:00 (명세 §16) |

- `POST /demo/clock` 요청은 `{sol, time}`(둘 다 필수) 또는 `{advance}` 중 **하나만**. `advance`는 `"<1~9999>h"` 또는 `"<1~9999>m"` (예: `"2h"`, `"30m"`).
- 응답은 바뀐 시계를 담은 `/mission`과 같은 모양이다.

#### Communication policy (#47)

`GET /mission` and `POST /demo/clock` include these fields:

```json
{
  "clock": {"sol": 46, "time": "20:00"},
  "environment": "mars_base",
  "one_way_delay_min": 12,
  "next_window": "08:00",
  "comms_state": "blackout",
  "blackout_start_sol": 43,
  "blackout_end_sol": 57,
  "blackout_days_remaining": 11,
  "next_window_at": {"sol": 57, "time": "08:00"},
  "simulation": true
}
```

- `blackout` covers Sol 43 at 00:00 through the end of Sol 56. The remaining
  day count includes the current Sol and is zero outside blackout.
- Outside blackout, `connected` covers 08:00–08:29 and 20:00–20:29. All
  other times are `delayed`.
- `next_window_at` is the next opening strictly after the current time,
  skipping blackout. The legacy `next_window` equals `next_window_at.time`
  and keeps the `HH:MM` format without a sol. Clients should use both fields
  of `next_window_at` to jump to it. A time-only jump can land on the wrong
  sol (known frontend issue FE-06).
- During blackout, warning events and explicit queue requests save packets
  locally. `POST /tx/send` returns HTTP 200 with the existing queue response.
  A newly queued packet has `status: "queued"`, `attempts: 0` and
  `window_id: null` until a window opens. A simulated receipt for an existing
  send attempt can still be recorded locally.

An authenticated non-CMO calling `POST /tx/send` gets HTTP 403:

```json
{"error":{"code":"forbidden","message":"Medical officer access required."}}
```

Submitting a receipt for a visible packet with a mismatched attempt gets HTTP 409:

```json
{"error":{"code":"invalid_receipt","message":"Receipt does not match the packet's current attempt."}}
```

#### Habitat rehearsal actions (#47)

- The `--mission-demo` database enables C1's Sol 16 rehearsal. The server evaluates it at startup and on clock changes. Each target has at most one action for that Sol.
- Lighting is proposed when connected and applied automatically when delayed or in blackout. A same-Sol proposal is applied if the connection becomes delayed while it is still awaiting approval; the same action id is kept and its trigger and settings are updated to those in effect when it is applied. Undone or already applied actions are not changed. The connection state only controls whether a new change starts: an applied lighting action stays applied when the connection returns, with the same stored settings and `applied_at`, and the owner can still undo it on the same Sol. After an undo, reconnecting or another delay does not reapply it. The simulated adjustment schedules amber lighting at 21:00 and moves lights-out from 23:00 to 22:00.
- The schedule proposal moves the simulated EVA from 09:00 to 13:00. It requires low HRV, a sleep deficit, and an EVA assignment. The owner must approve it on the same Sol.
- Each action includes `id`, `crew`, `sol`, `target`, `status`, `tier`, `before`, `after`, `reason`, `reason_text`, `cite_ids`, `approved_by`, and `outcome`. `tier` is `auto` or `approve`, and `status` is `proposed`, `applied`, `undone`, or `released`.
- All three endpoints accept `?lang=en|ko` for the display strings `before` and `after`. The structured values are in `before_values` and `after_values`. `reason` contains `{metric,value,z}`. `reason_text` is null until generated explanations are wired up. `cite_ids` list applicable paragraphs available in the loaded evidence.
- From Sol 17 onward, the server uses the Sol 17 readings to evaluate recovery. `outcome` contains `{sol,released,metrics:[{metric,before,before_z,after,after_z}]}`. Both lighting and schedule are released only when Sol 17 sleep z >= -1 and HRV z > -1. If either reading is missing, evaluation waits. Actions and outcomes persist across restart.
- Only the owner can approve or undo an action. Other viewers receive 403. An unknown action returns 404 `action_not_found`, and an invalid transition returns 409 `action_stale`.

#### Two-person consent and Earth reports (#47)

- `GET /events/{id}/procedure?lang=en|ko` returns `{available,medical_available,required,current_step,hold_reason,steps,simulation}`. Each step contains `step_id`, `text`, `cite_id`, `approvals`, and `done`. The procedure is available only for the C4 urgent chest pain event from Sol 46 in the rehearsal database during blackout.
- `POST /events/{id}/procedure/steps/save_report/approve` returns the updated consent state. Only C1 and C3 can approve. Each contributes one approval, and retries during the active rehearsal return the stored state. The second distinct approval saves one Earth report in the same database transaction.
- The consent step covers saving a report. Clinical guidance stays on hold (`medical_available: false`), and the urgent alert continues independently.
- `GET /earth-reports` returns `{reports:[{report_id,event_id,created_at,level,metrics,approvals,actions,cite_ids,packet}]}`. The report owner and a CMO with access can read it. The designated approvers have access to the consent step.
- `packet` contains `{seq,status,held_reason}` for the existing warning packet. A pending packet shows `held` during blackout and follows the queue's live status after recovery. The saved snapshot contains the summarized readings and approval records.

### 5.2 체크인 `answers` 키 **[추가 11/14, PR #1·#2 구현 기준]**

```json
{ "kind": "morning", "answers": { "sleep_quality": 4, "mood": 3, "fatigue": 2, "symptoms": "none" } }
```

| 키 | 형식 | 어느 kind | 뜻 (1 → 5) |
|---|---|---|---|
| `sleep_quality` | 정수 1~5 | `morning` 필수 | 매우 나쁨 → 매우 좋음 |
| `mood` | 정수 1~5 | `morning` 필수 | 매우 낮음 → 매우 좋음 |
| `fatigue` | 정수 1~5 | `morning` 필수 | 없음 → 탈진 |
| `symptoms` | `"none"` \| `"yes"` | 선택 (프론트 기본 `none`) | `yes`면 프론트가 증상 대화를 열고, 문장은 `POST /crew/{id}/symptom`으로 따로 보낸다 |
| `stress` | 정수 1~5 | `evening` | 없음 → 매우 높음 (모델 ② `MoodScore.stress`와 같은 방향) |
| `day_rating` | 정수 1~5 | `evening` | 매우 나쁨 → 매우 좋음 (명세 §8 "오늘 어땠는지") |
| `hydration_ok` | bool | `evening` | 물을 충분히 마셨는지 (명세 §8) |

- 척도 키는 **정수만** 받는다. 문자열 `"3"`, 소수, 범위 밖 값은 422 `invalid_request`.
- `hydration_ok`는 JSON `true` 또는 `false`만 허용한다. 저녁 응답은 기록으로 저장한다.
- Today responses include `checkin.morning_prefill` with valid scores from the previous sol's morning check-in and `sleep_hours` from the current sol's band readings. Missing scores are omitted and missing sleep is null.
- `baseline_progress` reports `collected_days` and `target_days`. Each metric's `baseline_days` counts prior eligible sols for that metric, capped at the target. The overall count is the smallest metric count.
- `free_text`는 선택, 최대 4000자.
- 같은 승무원·같은 sol·같은 `kind`로 다시 보내면 덮어쓴다(하루 한 건).
- 표에 없는 키도 백엔드가 막지는 않지만, **새 키를 쓰려면 먼저 이 표에 추가한다.** `weekly`·`monthly`·`quarterly`의 키는 만들 때 여기에 적는다.

### 5.3 지표별 `level` — `/today`의 `metrics[]` **[추가 11/14, PR #1·#2 구현 기준]**

```json
{ "metric": "hr", "value": 73, "baseline": 68, "sd": 2, "z": 2.5, "level": "caution", "hold_reason": null }
```

`level`은 백엔드 규칙 엔진이 지표마다 낸 판정이고 값은 §3의 `level` enum이다. **프론트는 `z`로 다시 계산하지 않고 `level`만 보고 표시한다.** 기준값은 민감도 `standard`(2.0 / 3.0, `contracts/enums.json`의 `sensitivity`).

| `level` | 조건 |
|---|---|
| `hold` | `z`가 null이라 판정할 수 없음. 이유는 `hold_reason` |
| `warning` | \|z\| ≥ 3.0 |
| `caution` | 2.0 ≤ \|z\| < 3.0 이고, 오늘 벗어난 지표가 2개 이상이거나 이 지표가 어제도 벗어났음 |
| `advisory` | 2.0 ≤ \|z\| < 3.0 이고 위 조건이 아님 (지표 1개, 하루) |
| `normal` | \|z\| < 2.0 |

- `hold_reason`: `insufficient_baseline`(기준선 14일 미만) · `missing_reading`(오늘 측정값 없음) · `zero_variance`(기준선 표준편차 0). `hold`가 아니면 null. `hold`일 때 `value`·`baseline`·`sd`·`z`는 null일 수 있다.
- 전체 판정 `status.level`도 §3의 `level` enum(`normal | advisory | caution | warning | hold`) 값 중 하나다. 지표별 `level`과 오늘 이벤트 `level` 중 가장 높은 것을 쓰며 순서는 `warning` > `caution` > `advisory`. 벗어난 지표가 없는데 `hold` 지표가 있으면 `hold`, 그 외는 `normal`.

### 5.4 이벤트의 `urgent`와 `level` **[추가 11/14, 백엔드·프론트 미구현 — PR #2·#5 리뷰 결정]**

```json
{ "id": 1, "symptom_text": "가슴이 아파요", "codes": ["chest_pain"], "urgent": true,  "level": "warning" }
{ "id": 2, "symptom_text": "머리가 아파요", "codes": [],             "urgent": false, "level": "normal" }
```

(다른 필드는 생략. `/today`의 `events[]`와 `GET /events/{id}`가 같은 모양으로 준다.)

| 필드 | 형식 | 뜻 |
|---|---|---|
| `urgent` | bool, 항상 있음 | 이 보고 문장이 즉시 경보 규칙(§3의 즉시 경보 코드 키워드, 의식 변화 키워드)에 걸렸는지. 경보의 **원인이 보고 문장**이라는 표시다 |
| `level` | §3의 `level` enum | **이 보고 하나**의 판정. 아래 규칙 |

**이벤트 `level`은 그날 전체 상태를 물려받지 않는다.** 그 보고의 증상 코드에 건 규칙과, 그 이벤트에 같이 저장되는 `findings`(보고 시점의 지표 스냅샷)만으로 정한다. `status.level`과 그날의 다른 이벤트 `level`은 읽지 않는다.

| 보고 | `urgent` | `level` |
|---|---|---|
| 즉시 경보 규칙에 걸림 | `true` | `warning` |
| 그 밖 | `false` | 이 이벤트의 `findings`에 든 지표 `level`만으로 §5.3의 전체 판정 규칙을 적용한 값. 그 값이 `advisory`면 `caution` (명세 §10 "지표 1개 + 증상 보고 = 주의") |

- 방향은 한쪽뿐이다. `status.level`이 이벤트 `level`을 반영하고(§5.3), 이벤트는 `status.level`을 읽지 않는다.

**경보(`warning`)는 원인과 상관없이 똑같이 다룬다 (명세 §10과 같은 규칙).** 전체 화면 경보와 모델 건너뜀은 `level`이 정하고, `urgent`는 원인만 알려 준다.

| 경우 | `level` | `urgent` | 전체 화면 경보 | 모델 |
|---|---|---|---|---|
| 보고 문장이 즉시 경보 규칙에 걸림 | `warning` | `true` | 띄운다 | 건너뛴다 |
| 즉시 경보 증상 없이 측정값만 \|z\| ≥ 3 | `warning` | `false` | 띄운다 | 건너뛴다 |
| 그 밖 (`warning`이 아님) | `normal`·`caution`·`hold` | `false` | 안 띄운다 | 건너뛰지 않는다 |

- **백엔드**: 이벤트 `level`이 `warning`이면 `urgent` 값과 상관없이 모델 단계(`symptom`~`verify`)를 돌리지 않는다. `needs_question`은 false, `explanation`은 null, `runs`는 `[]`, `codes`에는 키워드 규칙이 잡은 코드만 남는다.
- **프론트 — 경보 여부는 `level`로**: 전체 화면 경보(경보 화면으로 가는 버튼 포함)와 "모델을 건너뛰었다"는 안내는 그 이벤트의 `level === "warning"`으로 판단한다. 증상 보고가 없어도 `/today`의 `metrics[]`에 `warning` 지표가 있으면 전체 화면 경보를 띄운다.
- **프론트 — 원인 문구는 `urgent`로**: `true`면 "긴급 증상 보고", "보고 내용으로 규칙이 경보를 올렸다"는 문구를 쓴다. `false`인 경보는 측정값이 기준에서 크게 벗어났다는 문구와 그 수치를 보여 준다. `codes`로 원인을 판단하지 않는다(의식 변화 규칙은 `codes: []`로 온다).
- `title`의 "긴급 증상 보고 / Urgent symptom report"도 `level`이 아니라 `urgent`로 고른다.

근거 — main `bb9b6b9`, 새 DB, `c2`(지표 6개 모두 `normal`)에서 재현:

| 보고 | 지금 `level` | `codes` | 지금 `title` | §5.4대로 하면 |
|---|---|---|---|---|
| ① `가슴이 아파요` | `warning` | `["chest_pain"]` | 긴급 증상 보고 | `urgent: true`, `warning` |
| ② ① 뒤에 `머리가 아파요` | **`warning`** | `[]` | **긴급 증상 보고** | `urgent: false`, `normal` |
| ③ `동료가 의식이 없어요` (단독) | `warning` | `[]` | 긴급 증상 보고 | `urgent: true`, `warning` |

②는 ① 때문에 그날 상태가 `warning`이 된 것을 물려받았다(두통만 보고하면 `normal`). ②와 ③은 `level`과 `codes`가 같아서 지금 응답으로는 구분할 수 없다.

### 5.5 부위 `locations` — 표시 전용 **[추가 11/14, 백엔드 PR #37 · 모델 쪽은 후속 PR]**

증상 보고가 말한 부위를 몸 화면에 표시하기 위한 값이다. **`level`·`urgent`·제목·경보 판정에 쓰지 않는다.**

- **값**: `body_location`의 배열. 좌우는 승무원 본인 기준이다. 얼굴·눈·귀·코는 `head`, 목·목구멍은 `neck`, 배·속은 `abdomen`, 등·허리는 `back`이다. 어깨에서 손까지는 팔, 고관절에서 발까지는 다리다.
- **좌우를 말하지 않은 팔·다리**는 양쪽을 다 넣는다(`["left_arm", "right_arm"]`). 응답에는 "좌우를 말하지 않았다"를 따로 적을 칸이 없다.
- **넣지 않는 것**: 부위를 말하지 않은 증상(피로·어지럼), 부정한 부위, 이미 나은 부위, 남의 부위. 증상 코드와 같은 규칙이다.

| `locations` | 뜻 | 프론트 |
|---|---|---|
| 키 없음 또는 `["unknown"]` | 부위를 모른다. 모델이 칸을 쓰지 않았거나 쓸 수 없는 값만 냈다, 모의 모델, 모델 단계를 돌리지 않는 `warning` 이벤트, 예전 이벤트 | `symptom_text`에서 직접 찾는다 |
| `[]` | 모델이 봤고 보고에 부위가 없다 | 표시하지 않는다 |
| 값 | 모델이 찾은 부위 | 그대로 표시한다 |

- **모델**(`extract_symptoms`, `contracts/symptom.schema.json`): 목록 밖 값과 겹친 값은 그 값만 버리고 보고는 살린다(`onset`·`worse_when`이 목록 밖이면 `unknown`으로 두는 것과 같은 취지). 모델에게는 `unknown`을 고를 수 없게 한다. 낸 값 가운데 쓸 수 있는 것이 하나도 없으면 `["unknown"]`이 된다.
- **백엔드**: 받은 값을 이벤트에 저장하고 `/today`의 `events[]`와 `GET /events/{id}`에 싣는다. 모델이 준 `[]`는 `[]` 그대로 둔다. 값이 없을 때만 `["unknown"]`을 넣는다.

## 6. 작업 분담과 넘겨주는 것 (초안, 팀 미팅에서 확정)

| 담당 | 산출물 | 남에게 주는 것 |
|---|---|---|
| 프론트 | `frontend/` 9화면, i18n ko/en | 없음(API만 소비) |
| 백엔드 | `backend/` 규칙 엔진·기준선·API·SQLite·전송 큐·mock | API(§5), mock 응답 |
| AI(Tyler) | `ml/`, `contracts/`, `backend/model/client.py`, `backend/verify.py`, 평가 30문항 | 스키마·enum, 모델 서버, 검증기 |
| 기획·발표 | 문서 코퍼스(`backend/corpus/*.md`, id 규칙 §2), `conditions` 목록, 슬라이드 7장 or 30초 영상, README(영문), References | 코퍼스·condition enum |

## 7. 아직 안 정한 것 (답이 나오면 여기 고침)

- 증상 보고 없이 측정값만 `warning`이 된 경우, 경보 확인·오경보 종결을 붙일 이벤트를 규칙이 만들지 (지금 백엔드는 증상 보고로만 이벤트를 만든다, §5.4).
- 행사 전 만든 학습셋·어댑터 사용 가능 여부 (팀 미팅/Connect에서 질문; 안 되면 행사 중 재학습 ~45분).
- `conditions` 최종 목록과 코퍼스 출처 표기.
- 승무원 이름·역할 4명(`c1`~`c4`), CMO 지정.
- 슬라이드 7장 vs 30초 영상.
