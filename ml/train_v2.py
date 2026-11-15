"""학습 v2 (MLX, Mac): 서비스와 똑같은 입력 모양으로 LoRA를 학습한다.

mlx-lm 의 기본 학습은 Gemma 4 에서 서비스와 입력이 어긋난다. 서버는 생각 끄기(enable_thinking=false)로
답 바로 앞에 빈 생각 칸("<|channel>thought\n<channel|>")을 붙이는데, 학습 쪽 템플릿은 붙이지 않는다.
--mask-prompt 의 경계도 그만큼 밀려 답의 첫 토큰들이 손실에서 빠진다.
여기서는 프롬프트를 서버와 같은 호출로 만들고, 그 뒤에 답과 턴 끝 토큰을 붙인다.

사용 (ml 폴더에서): .venv/bin/python train_v2.py -c train_v2.yaml
점검:              .venv/bin/python train_v2.py --show data/v2/train.jsonl
"""
import json, re, sys

from mlx_lm import lora
from mlx_lm.tuner import datasets

TEMPLATE_ARGS = {"enable_thinking": False}   # backend/model/README.md 의 서버 실행 옵션과 같아야 한다
TURN_END = "<turn|>"                         # Gemma 4 의 턴 끝 토큰. 서버는 여기서 생성을 멈춘다


ASKED = re.compile(r"([a-z_]+): (?:array from|one of|integer|true or false)")      # 지시문이 답에 넣으라고 한 칸 이름


def process(self, d):
    messages = d[self.chat_key]
    # 지시문이 묻는 칸이 정답에 없으면 멈춘다. 그대로 학습하면 모델이 그 칸을 쓰지 않도록 배운다.
    asked = ASKED.findall(messages[0]["content"]) if messages[0]["role"] == "system" else []
    if asked and (missing := [k for k in asked if k not in json.loads(messages[-1]["content"])]):
        sys.exit(f"ERROR training answers lack {missing}, which the instruction asks for. Add them to the labels (ml/data/v2) and rebuild, "
                 "or build the set at the commit the adapter was trained from (1cde53e).")
    prompt = list(self.tokenizer.apply_chat_template(messages[:-1], add_generation_prompt=True, return_dict=False, **TEMPLATE_ARGS))
    answer = self.tokenizer.encode(messages[-1]["content"] + TURN_END, add_special_tokens=False)
    return (prompt + answer, len(prompt) if self.mask_prompt else 0)


datasets.ChatDataset.process = process

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--show":      # 첫 문항이 어떻게 토큰으로 바뀌는지, 길이 분포가 어떤지 본다
        import pathlib
        from mlx_lm.tokenizer_utils import load as load_tokenizer
        tok = load_tokenizer(pathlib.Path("models/gemma-4-12B-it-qat-OptiQ-4bit"))      # 토크나이저만 읽는다
        rows = [json.loads(l) for l in open(sys.argv[2], encoding="utf-8") if l.strip()]
        ds = datasets.ChatDataset(rows, tok, mask_prompt=True)
        sizes = sorted(len(ds.process(r)[0]) for r in rows)
        tokens, offset = ds.process(rows[0])
        assert tok.encode(TURN_END, add_special_tokens=False) == tokens[-1:], "turn-end marker is not a single token"
        print("prompt tail :", repr(tok.decode(tokens[offset - 12:offset])))
        print("trained part:", repr(tok.decode(tokens[offset:])))
        print(f"tokens per item: median {sizes[len(sizes) // 2]}  p95 {sizes[int(len(sizes) * 0.95)]}  max {sizes[-1]}  (n={len(sizes)})")
    else:
        lora.main()
