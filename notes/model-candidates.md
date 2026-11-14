# 모델 후보 (8~14B, 2026-11-12 조사)

목적: §11·§18의 "Qwen3 4B 또는 11B급"을 실측으로 대체. 후보를 고르고, 정답표 30문항으로 재서 정한다.
확인 수준: Ollama 라이브러리 페이지(11/12 직접 조회)와 공식 블로그·HF 카드. 벤치마크 숫자는 2차 출처라 참고만.

> **서울 3차 안내(11/11 22:42 메일) 반영.** "중국에서 개발·배포한 오픈소스 AI 모델의 사용을 권장하지 않습니다." → Qwen(알리바바)·MiMo(샤오미)는 후보에서 뺀다(금지는 아니지만 심사 불이익 위험). 같은 메일: 조사·설계·구현은 11/14 09:00 이후, 자료 찾기·논문 읽기·계정 생성도 사전 작업, 목록이 있는 자료 다운로드만 허용. → 모델 파일 다운로드(`ollama pull`)는 가능, **30문항 측정·파인튜닝·코퍼스 작성은 행사 중**으로 옮긴다.

## 후보

| 모델 | 출시 | 라이선스 | Ollama 태그·용량 | 기능 | 비고 |
|---|---|---|---|---|---|
| ~~Qwen3.5-9B~~ | 2026-03 | Apache 2.0 | `qwen3.5:9b` | | 성능은 10B 미만 최상위지만 중국 모델 비권장으로 제외 |
| **Gemma 4 12B** | 2026-04 가족 출시, 12B는 6월 추가(공식 확인 못 함) | Apache 2.0 | `gemma4:12b` Q4 약 6.7GB, 256K | vision·audio·tools·thinking | **1순위.** 한국어 강한 계열. 3060 12GB에서 Q4 가능 |
| Ministral 3 8B / 14B | 2025-12 | Apache 2.0 | `ministral-3:8b` 6.0GB, `:14b`, 256K | vision·tools | 2순위. 8B는 속도, 14B는 상한. 한국어는 Gemma보다 약할 가능성 |
| Granite 4.2 8B | 2026-09 | Apache 2.0 | `granite4.2:8b` 5.3GB, 128K | tools·thinking(텍스트만) | 구조화 출력·도구 호출 지향. 한국어 미확인 |
| ~~MiMo V2.6 9B~~ | 2026-11 | MIT | `mimo-v2.6:9b` | | 중국 모델 비권장으로 제외 |
| Olmo 3 7B (와일드카드) | 2025-11 | Apache 2.0 | Ollama `olmo3` 확인 필요 | | AI2, 데이터·학습 과정까지 공개된 완전 오픈. 한국어 약할 가능성 |

제외: Qwen3.8은 공식 소형이 없음(27B만, 9B는 커뮤니티 증류라 제외). EXAONE 4.5는 33B·비상업 라이선스. Kanana-2 dense는 3B까지. Llama 3.1 8B는 라이선스·세대가 뒤짐.

## 확정 후보 (11/12 밤)
Gemma 4 12B · Ministral 3 8B · **Gemma 4 E4B**(4B급). 세 개를 같은 30문항으로 잰다.

4B급 검토(Ollama 11/12 조회): Gemma 4 E4B(Apache 2.0, 6.6GB, 128K, vision·audio·tools·thinking, 4B급 벤치 최상위) / Granite 4.2 3B(Apache 2.0, 2.2GB, JSON 출력 지향, 한국어 미확인) / Phi-4-mini 3.8B(MIT, 2.5GB, 1년 전, 한국어 약함) / bonsai-2 4B(Prism ML, 1.6GB라 저비트 양자화 추정, 검증 안 됨) / Kanana-2 3B(한국어 전용이나 Ollama 없음, GGUF 변환 필요) / d3·pplx-decider-flash(결정 전용·Qwen 기반이라 제외). E4B를 고른 이유: 12B와 같은 가족이라 "크기만 줄였을 때" 비교가 깨끗하고, 한국어도 같은 수준으로 기대. 대안은 Granite 4.2 3B.

## 전제
- 임무 제약은 전력·방사선·교체 불가이지 비용·용량이 아니다. 모델 크기 상한은 우리 개발 기기(3060 12GB, M5 Pro 24GB)와 금요일까지의 파인튜닝 시간이 정한다.
- Ollama structured outputs(JSON schema)는 샘플러 단계 제약이라 어느 모델이든 동작.
- 파인튜닝은 QLoRA 기준 8B까지 3060에서, 12B는 M5 Pro(MLX)에서. 사전 파인튜닝은 3차 안내 기준 사전 작업이라 행사 중 여유가 있을 때만.

## 측정 계획 (행사 시작 후 첫 1~2시간)
1. 같은 30문항(증상 문장 → enum 코드)을 thinking off, JSON schema 강제로 3회씩.
2. 지표: 코드 정확도, 검증기 폐기율(출처·단정 표현·목록 밖 이름), 한국어 설명 문장 10개의 자연스러움(사람 판정), 3060·M5 각각 지연(p50/p95).
3. 순서: Gemma 4 12B → Ministral 3 8B → Gemma 4 E4B. 11/14 09:00 이후 첫 1~2시간에 실행. 파일(`gemma4:12b`, `ministral-3:8b`, `gemma4:e4b`)은 그 전에 내려받아 둔다.
4. 결과로 §11·§18을 고친다.

## 출처
- Qwen3.5 small: https://artificialanalysis.ai/articles/qwen3-5-small-models , https://www.marktechpost.com/2026/03/02/alibaba-just-released-qwen3-5-small-models-a-family-of-0-8b-to-9b-parameters-built-for-on-device-applications/ , https://ollama.com/library/qwen3.5
- Gemma 4: https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/ , https://artificialanalysis.ai/articles/gemma-4-everything-you-need-to-know , https://ollama.com/library/gemma4
- Ministral 3: https://ollama.com/library/ministral-3 , https://huggingface.co/mistralai/Ministral-3-14B-Base-2512
- Granite 4.2: https://ollama.com/library/granite4.2
- MiMo V2.6: https://ollama.com/library/mimo-v2.6
- Qwen3.8(소형 없음): https://ollama.com/library/qwen3.8 , https://www.llm-releases.com/labs/alibaba
- EXAONE 4.5: https://huggingface.co/LGAI-EXAONE/EXAONE-4.5-33B-GGUF
- Kanana-2: https://github.com/kakao/kanana-2

## 학습 파이프라인 검증 (11/12 16시대, Mac M5 Pro)
- 학습셋: `ml/data/gen_symptoms.py` → 2,160/240건, 코드 13개, ko 65%.
- 스모크: Llama-3.2-1B-Instruct-4bit, LoRA 16층, 150 iter, 약 2분.
  - 바닐라: JSON 37.5% · 코드 일치 12.5% · Jaccard 0.15 (목록을 통째로 베낌)
  - LoRA 뒤: JSON 100% · 코드 일치 77.5% · Jaccard 0.84 · onset 100% · worse 97.5% · severity 60% · 목록 밖 코드 0 · p50 0.29s
  - 40건 1회 측정. 스크립트 검증용이지 모델 선택 근거는 아님.
- 다음: Ministral 3 8B → Gemma 4 E4B → Gemma 4 12B 순으로 같은 절차(600 iter), valid 240건 전체 + 사람이 쓴 30문항.

### Ministral 3 8B (mlx-community/Ministral-3-8B-Instruct-2512-4bit, 11/12 저녁)
- 600 iter, LoRA 16층, batch 4, lr 1e-5, mask-prompt. valid 240건 1회 측정.
- 바닐라: JSON 100% · 코드 일치 70% · Jaccard 0.83 · onset 56% · worse 86% · severity 33% · needs_q 16% · 목록 밖 0 · p50 1.22s
- LoRA 뒤: JSON 100% · 코드 일치 99.6% · Jaccard 0.998 · onset 100% · worse 100% · severity 75% · needs_q 85% · 목록 밖 0 · p50 1.64s
- 해석 주의: valid는 train과 같은 템플릿 생성기에서 나왔다. 99.6%는 "템플릿 분포 안"에서의 수치이고 일반화 근거가 아니다. 진짜 판정은 사람이 쓴 30문항.
- 바닐라 오답 중 일부는 학습셋 탓: "since this morning"이 hours/today 양쪽 문구에 있고, "참기 힘들어요"(severity 5 문구)를 fatigue로 읽음. 생성기 문구 겹침 정리 필요.
- 로드 시 토크나이저 정규식 경고(Mistral 계열 알려진 이슈). 생성은 정상.

### Gemma 4 E4B (mlx-community/unsloth-gemma-4-E4B-it-qat-oQ4, 11/12 저녁)
- 같은 설정 600 iter. 기본 템플릿이 thinking을 켜므로 바닐라는 `--no-think`로 측정. valid 240건 1회.
- 바닐라(no-think): JSON 100% · 코드 일치 80.4% · Jaccard 0.87 · onset 57% · worse 39% · severity 48% · needs_q 68% · 목록 밖 1 · p50 1.36s
- LoRA 뒤(thinking 켬/끔 거의 동일): JSON 100% · 코드 일치 98.3% · Jaccard 0.99 · onset 100% · worse 100% · severity 75~76% · needs_q 85% · 목록 밖 0 · p50 1.04s
- **안전 관점 경고**: 어댑터 오답 4건 중 2건이 crisis 누락("다 끝내고 싶어요"가 두 번째 증상으로 붙은 문장에서 crisis를 빼먹음). valid의 crisis 31건 중 2건 누락. Ministral 8B 어댑터는 crisis 누락 0건. 규칙 층이 crisis 키워드를 따로 잡아야 하는 이유가 수치로 확인됨.
- 바닐라 E4B는 코드 일치가 Ministral 바닐라(70%)보다 높지만 worse_when을 "none"으로 자주 채움(39%).
- 학습셋 결함 추가: worse 문구 "서면 더 어지러워요"가 dizziness 라벨 없이 쓰임 → 모델이 dizziness를 추가하면 오답 처리됨. 생성기에서 worse 문구가 증상을 암시하면 코드도 넣어야 함.

### Gemma 4 12B (mlx-community/gemma-4-12B-it-qat-OptiQ-4bit, 11/14 03:46~04:28)
- 600 iter 학습 약 30분(100 iter당 4~5분). 바닐라·어댑터 모두 `--no-think`. valid 240건 1회.
- 바닐라: JSON 100% · 코드 일치 83.8% · Jaccard 0.91 · onset 78% · worse 85% · severity 49% · needs_q 61% · 목록 밖 0 · p50 4.45s
- LoRA 뒤: JSON 100% · 코드 일치 95.4% · Jaccard 0.98 · onset 96% · worse 98% · severity 69% · needs_q 85% · 목록 밖 0 · p50 2.5s
- 오답 10건 중 7건이 "서면 더 어지러워요"에 dizziness를 추가한 것. 라벨이 틀렸고 모델이 맞다. 이걸 빼면 12B 어댑터도 8B와 같은 수준. crisis 누락 0건(crisis+low_mood로 코드 하나 더 붙인 1건은 누락 아님).
- 어댑터를 붙이면 출력이 짧아져 지연이 4.45s→2.5s로 줄지만, 8B(1.6s)·E4B(1.0s)보다 여전히 느리다.

### 세 모델 비교 (LoRA 600 iter, valid 240, 1회, 11/12~14 Mac M5 Pro 24GB)
| | Gemma 4 E4B | Ministral 3 8B | Gemma 4 12B |
|---|---|---|---|
| 바닐라 코드 일치 | 80.4% | 70.0% | 83.8% |
| LoRA 코드 일치 | 98.3% | 99.6% | 95.4%* |
| LoRA severity | 76% | 75% | 69% |
| crisis 누락 (31건 중) | 2 | 0 | 0 |
| LoRA p50 지연 | 1.04s | 1.64s | 2.5s |
| 학습 시간 | ~15분 | ~20분 | ~30분 |
*라벨 결함 7건 제외 시 98%대.
- 읽는 법: 템플릿 분포 안 수치라 모델 간 차이는 작고, 사람 30문항이 진짜 판정. 현 시점 1순위 Ministral 3 8B(crisis 0, 가장 높은 일치, 지연 중간), 12B는 느림이 비용 대비 득이 없음, E4B는 crisis 누락 때문에 단독 사용 불가(규칙 층 필수).
- 생성기 수정 목록: "since this morning" hours/today 중복, "서면 더 어지러워요"·"ARED 하고 나서 더 아파요"처럼 증상을 암시하는 worse 문구에는 코드 추가, "참기 힘들어요"가 fatigue로 읽히는 문제.

## PC(RTX 3060 12GB, CUDA) 재현 — 11/14 새벽
- 환경: Windows 11, torch 2.11+cu128, transformers 5.23, peft 0.21.3, bitsandbytes 0.50.2. 가중치는 unsloth bnb-4bit(8B·E4B), 12B는 bf16 원본(24GB) 받아 둠(w4a16 compressed-tensors는 40토큰 66초로 비실용).
- 스크립트: `ml/train_cuda.py`(PEFT QLoRA r16 α32 lr 2e-4 cosine, batch 1×4, max-len 640, 프롬프트 마스킹), `ml/eval_cuda.py`(MLX 평가와 같은 지표).
- 함정: Ministral 3·Gemma 4는 멀티모달 config → `AutoModelForImageTextToText`로 로드. vision/audio 타워의 Linear4bit는 Params4bit가 비어 있어 peft bnb 디스패치가 깨짐 → LoRA 대상을 `model.language_model.*` 정규식으로 한정.
- Ministral 3 8B 바닐라(PC, no-think): JSON 99.6% · 코드 일치 72.1% · Jaccard 0.83 · onset 62% · worse 79% · severity 34% · needs_q 16% · p50 4.13s. Mac MLX 바닐라(70%)와 같은 수준, 지연은 bnb 추론이라 3배 느림.
- Ministral 3 8B QLoRA: 600 iter 중 580까지 진행(iter당 약 6.3초, VRAM 11.6GB) 후 프로세스가 트레이스백 없이 종료(rc=1). iter 400 체크포인트(val_loss 0.0239) 남음 → 이걸 평가. 같은 새벽 06:52에 PC가 재부팅된 적 있음(E4B 바닐라 평가 중 CUDA unknown error 직후) — GPU/드라이버 불안정 의심, 미확인.
- Gemma 4 E4B: bnb-4bit 로드만 10.2GB → 12GB에서 학습 미시도(OOM 예상). 12B bf16 + bnb 4bit 즉시 양자화도 미시도.
- Ministral 3 8B QLoRA(iter 400 체크포인트) PC 평가(no-think, valid 240, 1회): JSON 100% · 코드 일치 100% · Jaccard 1.0 · onset 100% · worse 100% · severity 73% · needs_q 85% · 목록 밖 0 · p50 5.2s. Mac MLX 어댑터(99.6%)와 같은 결론. 어댑터 사본 `ml/adapters/pc/`(gitignore), 원본 `D:\adapters\...-symptoms` (PEFT 형식, transformers에서 바로 로드).
