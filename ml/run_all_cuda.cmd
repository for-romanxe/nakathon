@echo off
REM PC(RTX 3060)에서 세 모델 바닐라 평가 -> QLoRA 600 iter -> 어댑터 평가. 결과 ml\results_cuda.jsonl, 로그 D:\adapters\*.log
set PY=D:\venv\Scripts\python
set ML=C:\Users\tyler\nasa-space-apps-2026\ml
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
mkdir D:\adapters 2>nul
cd /d %ML%
for %%M in (Ministral-3-8B-Instruct-2512-unsloth-bnb-4bit gemma-4-E4B-it-unsloth-bnb-4bit) do (
  echo == %%M vanilla %TIME% >> D:\adapters\run_all.log
  %PY% eval_cuda.py --model D:\models\%%M --no-think >> D:\adapters\%%M-eval-vanilla.log 2>&1
  echo == %%M train %TIME% >> D:\adapters\run_all.log
  %PY% train_cuda.py --model D:\models\%%M --out D:\adapters\%%M-symptoms >> D:\adapters\%%M-train.out 2>&1
  echo == %%M lora %TIME% rc=%ERRORLEVEL% >> D:\adapters\run_all.log
  %PY% eval_cuda.py --model D:\models\%%M --adapter D:\adapters\%%M-symptoms --no-think >> D:\adapters\%%M-eval-lora.log 2>&1
  echo == %%M done %TIME% >> D:\adapters\run_all.log
)
echo ALL-DONE >> D:\adapters\run_all.log
