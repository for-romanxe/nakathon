"""CUDA 쪽 공통 로더. Ministral 3·Gemma 4는 멀티모달 config라 AutoModelForCausalLM이 거부한다."""
import torch
from transformers import AutoModelForCausalLM, AutoModelForImageTextToText, AutoTokenizer

def load_model(path):
    tok = AutoTokenizer.from_pretrained(path)
    try:
        model = AutoModelForCausalLM.from_pretrained(path, device_map="cuda", dtype=torch.bfloat16)
    except ValueError:
        model = AutoModelForImageTextToText.from_pretrained(path, device_map="cuda", dtype=torch.bfloat16)
    return model, tok
