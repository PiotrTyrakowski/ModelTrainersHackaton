# strip_mtp.py in.gguf out.gguf: drop the unused multi-token-prediction layer (last block) of a Qwen3.5 GGUF,
# matching the Unsloth conversions (block_count 32, no nextn/recurrent_layers keys). Tensor data are copied unchanged.
import os, sys
sys.path.insert(0, os.environ.get("GGUF_PY", "/content/llama.cpp/gguf-py"))
import gguf
src, dst = sys.argv[1], sys.argv[2]
r = gguf.GGUFReader(src)
arch = r.fields["general.architecture"].contents()
n = r.fields[f"{arch}.block_count"].contents()
nextn = r.fields[f"{arch}.nextn_predict_layers"].contents() if f"{arch}.nextn_predict_layers" in r.fields else 0
keep_blocks = n - nextn
w = gguf.GGUFWriter(dst, arch=arch, endianess=r.endianess)
al = r.fields.get("general.alignment")
if al is not None: w.data_alignment = al.contents()
for f in r.fields.values():
    if f.name == "general.architecture" or f.name.startswith("GGUF."): continue
    if f.name in (f"{arch}.nextn_predict_layers", f"{arch}.attention.recurrent_layers"): continue
    vt = f.types[0]; st = f.types[-1] if vt == gguf.GGUFValueType.ARRAY else None
    v = keep_blocks if f.name == f"{arch}.block_count" else f.contents()
    w.add_key_value(f.name, v, vt, sub_type=st)
drop = tuple(f"blk.{i}." for i in range(keep_blocks, n))
ts = [t for t in r.tensors if not t.name.startswith(drop)]
for t in ts: w.add_tensor_info(t.name, t.data.shape, t.data.dtype, t.data.nbytes, t.tensor_type)
w.write_header_to_file(); w.write_kv_data_to_file(); w.write_ti_data_to_file()
for t in ts: w.write_tensor_data(t.data)
w.close()
print("kept", len(ts), "of", len(r.tensors), "tensors; blocks", n, "->", keep_blocks)
