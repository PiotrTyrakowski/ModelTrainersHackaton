# recipe.py ref.gguf > types.txt: per-tensor quant types of a reference GGUF as llama-quantize --tensor-type-file lines
import os, re, sys
sys.path.insert(0, os.environ.get("GGUF_PY", "/content/llama.cpp/gguf-py"))
from gguf import GGUFReader
for t in GGUFReader(sys.argv[1]).tensors:
    if t.tensor_type.name in ("F32", "F16", "BF16"): continue
    print("^" + re.escape(t.name) + "$=" + t.tensor_type.name.lower())
