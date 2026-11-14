#!/bin/zsh
# 증상 JSON 추출 LoRA 학습 (MLX, Mac). 사용: ml/train.sh <모델 폴더명> [iters]
# 예: ml/train.sh Ministral-3-8B-Instruct-2512-4bit 600
set -e
cd "$(dirname "$0")"
MODEL=${1:?model dir name under ml/models}
ITERS=${2:-600}
NAME=${MODEL}-symptoms
mkdir -p adapters logs
. .venv/bin/activate
python -m mlx_lm lora \
  --model "models/$MODEL" \
  --train \
  --data data/symptoms \
  --fine-tune-type lora \
  --mask-prompt \
  --num-layers 16 \
  --batch-size 4 \
  --iters "$ITERS" \
  --learning-rate 1e-5 \
  --max-seq-length 640 \
  --steps-per-eval 100 \
  --steps-per-report 20 \
  --val-batches 25 \
  --adapter-path "adapters/$NAME" \
  --seed 7 2>&1 | tee "logs/$NAME.log"
echo "adapter -> ml/adapters/$NAME"
