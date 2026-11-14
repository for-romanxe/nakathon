# Tyler PC (RTX 3060 12GB) 세팅 — 11/14 05:20 KST

- 접속: `ssh tyler-pc` (Tailscale 100.122.56.56, Windows 11, OpenSSH 기본 셸 cmd). 맥 `~/.ssh/config`에 등록돼 있음.
- 설치돼 있던 것: Ollama 0.40.13(앱 상주), Python 3.12.10, Git, winget, WSL Ubuntu(실행 중). uv 없음.
- 디스크: C: 211GB · D: 3.5TB 여유. Ollama 모델은 기본 위치 `C:\Users\tyler\.ollama`.
- 레포: `C:\Users\tyler\nasa-space-apps-2026` (맥에서 tar로 복사, 1f7e57f 시점, ml/models·.venv·logs 제외, MLX 어댑터 4개 포함). git remote가 아닌 복사본이라 맥에서 바뀌면 다시 복사해야 함. 빈 bare 레포 `C:\Users\tyler\repos\nasa-space-apps-2026.git`도 만들어 둠(push는 권한 거부로 못 했음, 사용자가 직접 `git push pc main` 가능).
- 모델 pull: gemma4:e4b → ministral-3:8b → gemma4:12b 순서로 진행 중 (약 15MB/s, 모델당 7~10분). 로그 `C:\Users\tyler\pull-rest.log`.
- 맥에서 PC Ollama 쓰기: Ollama를 0.0.0.0에 열지 않고 SSH 터널로 쓴다.
  `ssh -f -N -L 11435:127.0.0.1:11434 tyler-pc` 후 `http://127.0.0.1:11435` (확인: /api/version → 0.40.13 200).
- 맥(MLX)에서 만든 LoRA 어댑터 → Ollama로 옮기는 GGUF 변환 경로는 아직 미정.
