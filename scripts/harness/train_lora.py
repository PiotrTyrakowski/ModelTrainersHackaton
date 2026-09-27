"""LoRA SFT of Qwen3.5 (0.8B/2B) on the non-essay matura set. Runs on a CUDA GPU (Colab).

python train_lora.py --model /content/models/Qwen3.5-0.8B --data nonessay-v1.jsonl --out /content/runs/q08-v1 --merge
Records: {"item": {...}, "answer": "...", "context": optional}. Prompt = common.messages() rendered with the
model's own chat template (non-thinking generation prompt), target = answer + <|im_end|>.
Adapted from the teammate's ~/Downloads/finetuine/mat/train.py.
"""
import argparse, json, math, random, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import messages

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--data", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--epochs", type=float, default=3)
ap.add_argument("--lr", type=float, default=2e-4)
ap.add_argument("--rank", type=int, default=64)
ap.add_argument("--alpha", type=int, default=64)
ap.add_argument("--bs", type=int, default=8)
ap.add_argument("--accum", type=int, default=2)
ap.add_argument("--max-len", type=int, default=3072)
ap.add_argument("--full", action="store_true", help="full fine-tune instead of LoRA")
ap.add_argument("--merge", action="store_true")
ap.add_argument("--max-steps", type=int, default=0)
args = ap.parse_args()

import torch
from transformers import AutoTokenizer, AutoModelForImageTextToText, get_cosine_schedule_with_warmup

tok = AutoTokenizer.from_pretrained(args.model)
END = "<|im_end|>"


def encode(rec):
    p = tok.apply_chat_template(messages(rec["item"], rec.get("context")), add_generation_prompt=True, tokenize=False)
    pi = tok(p, add_special_tokens=False)["input_ids"]
    ci = tok(rec["answer"].strip() + END + "\n", add_special_tokens=False)["input_ids"]
    if len(pi) + len(ci) > args.max_len:  # keep the answer, trim the prompt from the left of the context
        pi = pi[: max(0, args.max_len - len(ci))]
    return pi + ci, [-100] * len(pi) + ci


recs = [json.loads(l) for l in open(args.data, encoding="utf-8")]
data = [encode(r) for r in recs]
print("examples", len(data), "max len", max(len(d[0]) for d in data), "tokens", sum(len(d[0]) for d in data), flush=True)
print("SAMPLE:\n" + tok.decode(data[0][0])[-1200:], flush=True)

model = AutoModelForImageTextToText.from_pretrained(args.model, dtype=torch.bfloat16, device_map={"": 0})
model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
model.enable_input_require_grads()
if args.full:
    for n, p in model.named_parameters():
        p.requires_grad = ("language_model" in n) and ("embed" not in n)
else:
    from peft import LoraConfig, get_peft_model
    cfg = LoraConfig(r=args.rank, lora_alpha=args.alpha, lora_dropout=0.05, bias="none",
                     target_modules=r".*language_model.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj|in_proj_qkv|in_proj_z|out_proj)")
    model = get_peft_model(model, cfg)
    model.print_trainable_parameters()

params = [p for p in model.parameters() if p.requires_grad]
print("trainable", sum(p.numel() for p in params), flush=True)
opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.0)
steps_per_epoch = math.ceil(len(data) / (args.bs * args.accum))
total = int(steps_per_epoch * args.epochs) if not args.max_steps else args.max_steps
sched = get_cosine_schedule_with_warmup(opt, max(5, total // 20), total)
pad = tok.pad_token_id if tok.pad_token_id is not None else 0
model.train(); step = 0; random.seed(0); t0 = time.time()
while step < total:
    order = sorted(range(len(data)), key=lambda i: random.random())
    for b0 in range(0, len(order), args.bs * args.accum):
        block = order[b0:b0 + args.bs * args.accum]
        ntok = sum(sum(1 for x in data[i][1] if x != -100) for i in block)
        tot = 0.0
        for m0 in range(0, len(block), args.bs):
            mb = [data[i] for i in block[m0:m0 + args.bs]]
            L = max(len(x[0]) for x in mb)
            K = max(sum(1 for y in x[1] if y != -100) for x in mb) + 1  # answers sit at the end (left padding)
            ids = torch.tensor([[pad] * (L - len(x[0])) + x[0] for x in mb], device="cuda")
            lab = torch.tensor([[-100] * (L - len(x[1])) + x[1] for x in mb], device="cuda")
            att = torch.tensor([[0] * (L - len(x[0])) + [1] * len(x[0]) for x in mb], device="cuda")
            logits = model(input_ids=ids, attention_mask=att, logits_to_keep=K).logits[:, -K:-1].float()
            tgt = lab[:, L - K + 1:]
            loss = torch.nn.functional.cross_entropy(logits.reshape(-1, logits.size(-1)), tgt.reshape(-1), ignore_index=-100, reduction="sum") / ntok
            loss.backward(); tot += loss.item()
            del logits, loss
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step(); sched.step(); opt.zero_grad(set_to_none=True); step += 1
        if step % 5 == 0 or step == 1:
            print(f"step {step}/{total} loss {tot:.4f} lr {sched.get_last_lr()[0]:.2e} {time.time()-t0:.0f}s mem {torch.cuda.max_memory_allocated()/2**30:.1f}G", flush=True)
        if step >= total:
            break

out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
if not args.full:
    model.save_pretrained(out / "adapter"); tok.save_pretrained(out / "adapter")
    if args.merge:
        model = model.merge_and_unload()
if args.full or args.merge:
    model.save_pretrained(out / "merged", safe_serialization=True)
    tok.save_pretrained(out / "merged")
    import shutil
    for f in ["preprocessor_config.json", "video_preprocessor_config.json", "chat_template.jinja", "config.json"]:
        s = Path(args.model) / f
        if s.exists() and not (out / "merged" / f).exists():
            shutil.copy(s, out / "merged" / f)
print("DONE", time.time() - t0, flush=True)
