#!/usr/bin/env bash
# Harness of models: one command from an organiser exam.json to a submission answers.json.
#
#   scripts/harness/run_system.sh <exam.json> <answers.json>
#
# The solver is one small multimodal model behind llama-server (started here unless $SERVER is set):
# Qwen3.5-4B fine-tuned on old-formula matura items, IQ2_M with a history imatrix, plus the Q8_0 vision
# projector (build_model.sh; 2,126,891,136 learned bytes). The GGUFs live in artifacts/ (not in git).
# Open/closed items: BM25 passages from the local wiki + e-Historia index, item images, one greedy answer.
# Essay: never generated. The same model only votes which prepared bank essay matches each offered topic
# (rotated multiple choice), and the topic whose chosen essay has the best lexical match is submitted.
set -euo pipefail
EXAM=$1; OUT=$2
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
MODEL=${MODEL:-$ROOT/artifacts/harness/gguf/Qwen3.5-4B-matura-v1-IQ2_M.gguf}
MMPROJ=${MMPROJ:-$ROOT/artifacts/harness/gguf/mmproj-Qwen3.5-4B-q8_0.gguf}
LLAMA_SERVER=${LLAMA_SERVER:-llama-server}
PORT=${PORT:-8080}
INDEX=${INDEX:-$ROOT/data/raw/retrieval/wiki-ehistoria-v1/index.sqlite}
BANK=${BANK:-$ROOT/data/essay-bank/v2/bank.jsonl}

# --cache-ram 0: the default 8 GB RAM prompt cache made a 16 GB Mac swap; it only saves prompt recomputation
if [ -z "${SERVER:-}" ]; then
  "$LLAMA_SERVER" -m "$MODEL" --mmproj "$MMPROJ" -ngl 99 -c 65536 -np 8 --cache-ram 0 --jinja --host 127.0.0.1 --port "$PORT" \
    > "${OUT}.server.log" 2>&1 &
  SPID=$!; trap 'kill $SPID 2>/dev/null' EXIT
  for _ in $(seq 1 120); do curl -sf "localhost:$PORT/health" >/dev/null && break; sleep 2; done
  SERVER=http://127.0.0.1:$PORT/v1
fi

python3 "$ROOT/scripts/harness/run_exam.py" --exam "$EXAM" --out "$OUT" --server "$SERVER" \
  --retrieval "$INDEX" --k 4 --images \
  --essay-bank "$BANK" --essay-judge 1 --essay-k 5 --essay-final lexical --workers 8
