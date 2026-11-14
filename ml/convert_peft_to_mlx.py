"""PC(CUDA, PEFT)에서 학습한 LoRA 어댑터를 Mac 모델 서버(mlx_lm)가 읽는 형식으로 바꾼다.

  ml/.venv/bin/python ml/convert_peft_to_mlx.py <PEFT 어댑터 폴더> <MLX 어댑터 폴더> [--verify <MLX 모델 폴더>]

PEFT: ...layers.N.<모듈>.lora_A.weight [r, in] · lora_B.weight [out, r] · 배율 lora_alpha / r
MLX : language_model.model.layers.N.<모듈>.lora_a [in, r] · lora_b [r, out] · 배율 scale
두 쪽 모두 y = W x + 배율 · B A x 라서 전치만 하면 같은 식이 된다.
주의: 바탕 모델의 4비트 양자화 방식이 다르다(PC bitsandbytes, Mac MLX). 변환 뒤에는 같은 검증셋으로 다시 잰다.
"""
import argparse, json, pathlib, re, sys

import mlx.core as mx

ap = argparse.ArgumentParser()
ap.add_argument("src", type=pathlib.Path)
ap.add_argument("dst", type=pathlib.Path)
ap.add_argument("--verify", type=pathlib.Path, help="이 MLX 모델에 올려 모든 텐서가 실제로 들어갔는지 확인한다")
a = ap.parse_args()

cfg = json.loads((a.src / "adapter_config.json").read_text(encoding="utf-8"))
unsupported = [k for k in ("use_dora", "use_rslora") if cfg.get(k)] + (["bias"] if cfg.get("bias", "none") != "none" else [])
if cfg.get("peft_type") != "LORA" or unsupported:
    sys.exit(f"ERROR cannot convert: peft_type={cfg.get('peft_type')} unsupported={unsupported}. Fix: train plain LoRA without these options.")

KEY = re.compile(r"layers\.(\d+)\.(.+)\.lora_([AB])\.weight$")
out, layers = {}, set()
for name, w in mx.load(str(a.src / "adapter_model.safetensors")).items():
    m = KEY.search(name)
    if not m:
        sys.exit(f"ERROR unexpected tensor {name}. Fix: check that the folder holds a PEFT LoRA adapter.")
    n, module, ab = m.groups()
    layers.add(int(n))
    out[f"language_model.model.layers.{n}.{module}.lora_{ab.lower()}"] = w.T.astype(mx.float32)

a.dst.mkdir(parents=True, exist_ok=True)
mx.save_safetensors(str(a.dst / "adapters.safetensors"), out)
config = {"fine_tune_type": "lora", "num_layers": max(layers) + 1,
          "lora_parameters": {"rank": cfg["r"], "scale": cfg["lora_alpha"] / cfg["r"], "dropout": 0.0},
          "converted_from": {"format": "peft", "base_model": cfg.get("base_model_name_or_path"), "source": a.src.name}}
(a.dst / "adapter_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
print(f"converted {len(out)} tensors · layers {min(layers)}..{max(layers)} · rank {cfg['r']} · scale {config['lora_parameters']['scale']} -> {a.dst}")

if a.verify:      # strict=False 로 읽기 때문에 이름이 어긋나면 조용히 빠진다. 실제로 들어갔는지 본다.
    from mlx.utils import tree_flatten
    from mlx_lm import load
    model, _ = load(str(a.verify), adapter_path=str(a.dst))
    params = dict(tree_flatten(model.parameters()))
    missing = [k for k in out if k not in params]
    differ = [k for k in out if k in params and not (params[k].shape == out[k].shape and mx.allclose(params[k], out[k]).item())]
    if missing or differ:
        sys.exit(f"ERROR adapter not fully applied: {len(missing)} tensors missing (e.g. {missing[:1]}), {len(differ)} differ. "
                 "Fix: compare the key names with an adapter trained by mlx_lm.")
    print(f"verified: all {len(out)} tensors are loaded into {a.verify.name} with the same values")
