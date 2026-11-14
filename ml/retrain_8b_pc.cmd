@echo off
REM E4B 학습이 끝나길 기다린 뒤 Ministral 8B QLoRA를 행사 중 타임스탬프로 재학습 + 평가 (11/14)
set PY=D:\venv\Scripts\python
set ML=C:\Users\tyler\nasa-space-apps-2026\ml
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set M=Ministral-3-8B-Instruct-2512-unsloth-bnb-4bit
set OUT=D:\adapters\%M%-symptoms-1114
cd /d %ML%
:wait
REM 우리 학습·평가 프로세스(train_cuda.py, eval_cuda.py)만 기다린다. 무관한 python.exe 는 보지 않는다.
powershell -NoProfile -Command "if (Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'train_cuda\.py|eval_cuda\.py' }) { exit 1 }"
if errorlevel 1 (timeout /t 60 /nobreak >nul & goto wait)
echo == 8B retrain start %DATE% %TIME% >> D:\adapters\run_all.log
%PY% data\gen_symptoms.py >> D:\adapters\retrain-8b-1114.out 2>&1
%PY% train_cuda.py --model D:\models\%M% --out %OUT% >> D:\adapters\retrain-8b-1114.out 2>&1
echo == 8B retrain lora %TIME% rc=%ERRORLEVEL% >> D:\adapters\run_all.log
%PY% eval_cuda.py --model D:\models\%M% --adapter %OUT% --no-think >> D:\adapters\retrain-8b-1114-eval.log 2>&1
echo == 8B retrain done %TIME% >> D:\adapters\run_all.log
echo RETRAIN-DONE
