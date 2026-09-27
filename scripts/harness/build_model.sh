#!/usr/bin/env bash
# Rebuild the harness solver model from the public base model (CUDA GPU + a llama.cpp build; ~1.5 h on a Colab A100).
#
#   LLAMA=/path/to/llama.cpp scripts/harness/build_model.sh <workdir>
#
# 1. LoRA SFT of Qwen/Qwen3.5-4B on data/sft/nonessay-v1.jsonl (train_lora.py defaults: r64, 3 epochs), merged.
# 2. The merged HF export lacks the multi-token-prediction (MTP) tensors; fix_mtp.py copies them from the base so
#    convert_hf_to_gguf.py accepts it. strip_mtp.py then removes the MTP block from the GGUF: llama.cpp does not
#    decode with it and llama-imatrix cannot calibrate it.
# 3. Importance matrix from Polish-history calibration text (build_calib.py: retrieval passages + old-formula items;
#    no development or final exam papers).
# 4. IQ2_M with the per-tensor types of Unsloth's Qwen3.5-4B-UD-IQ2_M (recipes/ud-iq2_m.txt, made by recipe.py).
# 5. Vision projector: the base model's (not fine-tuned) mmproj converted to Q8_0.
set -euo pipefail
W=$1; mkdir -p "$W"
ROOT=$(cd "$(dirname "$0")/../.." && pwd); H=$ROOT/scripts/harness
LLAMA=${LLAMA:-/content/llama.cpp}; BIN=$LLAMA/build/bin
export GGUF_PY=$LLAMA/gguf-py
BASE=${BASE:-$W/Qwen3.5-4B}
[ -d "$BASE" ] || python3 -c "from huggingface_hub import snapshot_download as s; s('Qwen/Qwen3.5-4B', local_dir='$BASE')"

python3 "$H/train_lora.py" --model "$BASE" --data "$ROOT/data/sft/nonessay-v1.jsonl" --out "$W/q4b-v1" --merge
python3 "$H/fix_mtp.py" "$BASE" "$W/q4b-v1/merged"
python3 "$LLAMA/convert_hf_to_gguf.py" "$W/q4b-v1/merged" --outtype bf16 --outfile "$W/q4b-v1-bf16.gguf"
python3 "$H/strip_mtp.py" "$W/q4b-v1-bf16.gguf" "$W/q4b-v1-nomtp-bf16.gguf"
python3 "$H/build_calib.py" --index "$ROOT/data/raw/retrieval/wiki-ehistoria-v1/index.sqlite" \
  --sft "$ROOT/data/sft/nonessay-v1.jsonl" --out "$W/calib-hist.txt"
"$BIN/llama-imatrix" -m "$W/q4b-v1-nomtp-bf16.gguf" -f "$W/calib-hist.txt" -o "$W/imatrix-q4b-hist.gguf" \
  -ngl 99 -c 512 -b 512 --chunks 150
"$BIN/llama-quantize" --imatrix "$W/imatrix-q4b-hist.gguf" --tensor-type-file "$H/recipes/ud-iq2_m.txt" \
  "$W/q4b-v1-nomtp-bf16.gguf" "$W/Qwen3.5-4B-matura-v1-IQ2_M.gguf" IQ2_M
python3 "$LLAMA/convert_hf_to_gguf.py" "$BASE" --mmproj --outtype q8_0 --outfile "$W/mmproj-Qwen3.5-4B-q8_0.gguf"
ls -l "$W/Qwen3.5-4B-matura-v1-IQ2_M.gguf" "$W/mmproj-Qwen3.5-4B-q8_0.gguf"
