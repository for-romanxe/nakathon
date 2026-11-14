"""증상 JSON 추출 QLoRA 학습 (CUDA, PEFT + bitsandbytes). Mac의 train.sh(MLX)와 같은 데이터·마스킹.

사용: python train_cuda.py --model D:\\models\\X --out D:\\adapters\\X-symptoms [--iters 600]
"""
import argparse, json, math, pathlib, random, time
import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from cuda_common import load_model

HERE = pathlib.Path(__file__).parent

def encode(tok, msgs, max_len):
    full = tok.apply_chat_template(msgs, tokenize=False)
    prompt = tok.apply_chat_template(msgs[:2], tokenize=False, add_generation_prompt=True)
    ids = tok(full, add_special_tokens=False)["input_ids"][:max_len]
    plen = len(tok(prompt, add_special_tokens=False)["input_ids"])
    labels = [-100] * min(plen, len(ids)) + ids[plen:]
    return ids, labels

def batches(rows, tok, bs, max_len, seed):
    rng = random.Random(seed)
    while True:
        rng.shuffle(rows)
        for i in range(0, len(rows) - bs + 1, bs):
            enc = [encode(tok, r["messages"], max_len) for r in rows[i:i + bs]]
            L = max(len(e[0]) for e in enc)
            pad = tok.pad_token_id if tok.pad_token_id is not None else 0
            ids = torch.tensor([e[0] + [pad] * (L - len(e[0])) for e in enc])
            lab = torch.tensor([e[1] + [-100] * (L - len(e[1])) for e in enc])
            att = torch.tensor([[1] * len(e[0]) + [0] * (L - len(e[0])) for e in enc])
            yield ids.cuda(), att.cuda(), lab.cuda()

def main(a):
    t0 = time.time()
    model, tok = load_model(a.model)
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    cfg = LoraConfig(r=a.rank, lora_alpha=2 * a.rank, lora_dropout=0.0, bias="none", task_type="CAUSAL_LM",
                     # 언어 모델 층만. vision/audio 타워의 Linear4bit는 Params4bit가 아니라 peft bnb 디스패치가 깨진다(11/14 확인).
                     target_modules=r"model\.language_model\..*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)")
    model = get_peft_model(model, cfg)
    model.print_trainable_parameters()
    train = [json.loads(l) for l in open(HERE / "data/symptoms/train.jsonl", encoding="utf-8")]
    valid = [json.loads(l) for l in open(HERE / "data/symptoms/valid.jsonl", encoding="utf-8")][:100]
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=a.lr, weight_decay=0.0)
    gen = batches(train, tok, a.batch, a.max_len, a.seed)
    log = open(a.out + ".log", "a", encoding="utf-8")
    def say(s):
        print(s, flush=True); log.write(s + "\n"); log.flush()
    say(f"model={a.model} iters={a.iters} batch={a.batch}x{a.accum} lr={a.lr} r={a.rank}")
    model.train()
    for it in range(1, a.iters + 1):
        lr = a.lr * 0.5 * (1 + math.cos(math.pi * it / a.iters))
        for g in opt.param_groups: g["lr"] = lr
        tot = 0.0
        for _ in range(a.accum):
            ids, att, lab = next(gen)
            loss = model(input_ids=ids, attention_mask=att, labels=lab).loss / a.accum
            loss.backward(); tot += loss.item()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step(); opt.zero_grad(set_to_none=True)
        if it % 20 == 0 or it == 1:
            say(f"iter {it} train_loss {tot:.4f} lr {lr:.2e} mem {torch.cuda.max_memory_allocated()/2**30:.1f}GB t {time.time()-t0:.0f}s")
        if it % 200 == 0 or it == a.iters:
            model.eval(); vl = 0.0
            with torch.no_grad():
                vg = batches(valid, tok, a.batch, a.max_len, 0)
                n = len(valid) // a.batch
                for _ in range(n):
                    ids, att, lab = next(vg)
                    vl += model(input_ids=ids, attention_mask=att, labels=lab).loss.item()
            say(f"iter {it} val_loss {vl/n:.4f}")
            model.train()
            model.save_pretrained(a.out)
    say(f"saved {a.out} total {time.time()-t0:.0f}s")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--iters", type=int, default=600)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--accum", type=int, default=2)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--max-len", type=int, default=640)
    ap.add_argument("--seed", type=int, default=7)
    main(ap.parse_args())
