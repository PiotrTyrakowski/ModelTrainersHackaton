"""Copy tensors that the merged HF export lost (Qwen3.5's multi-token-prediction head) back from the base model,
so that llama.cpp's convert_hf_to_gguf.py accepts the fine-tuned checkpoint. strip_mtp.py drops them again later.

python fix_mtp.py <base_hf_dir> <merged_hf_dir>
"""
import sys, json
from safetensors import safe_open
from safetensors.torch import save_file
from pathlib import Path

base, merged = Path(sys.argv[1]), Path(sys.argv[2])


def keys(d):
    ks = {}
    for f in d.glob("model*.safetensors"):
        with safe_open(f, "pt") as s:
            for k in s.keys():
                ks[k] = f
    return ks


bk, mk = keys(base), keys(merged)
missing = [k for k in bk if k not in mk]
print("missing in merged:", len(missing), missing[:5])
extra = [k for k in mk if k not in bk]
print("extra in merged:", len(extra), extra[:5])
t = {}
for k in missing:
    with safe_open(bk[k], "pt") as s:
        t[k] = s.get_tensor(k)
if t:
    save_file(t, str(merged / "model-mtp.safetensors"), metadata={"format": "pt"})
    idx = merged / "model.safetensors.index.json"
    if idx.exists():
        j = json.loads(idx.read_text()); j["weight_map"].update({k: "model-mtp.safetensors" for k in t}); idx.write_text(json.dumps(j))
print("saved", len(t))
