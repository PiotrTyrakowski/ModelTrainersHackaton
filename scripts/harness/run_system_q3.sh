#!/usr/bin/env bash
# In-between size of the harness: run_system.sh with the solver LM swapped for the base (not fine-tuned)
# Qwen3.5-4B Q3_K_M from unsloth/Qwen3.5-4B-GGUF, plus the same Q8_0 vision projector (2,660,283,104 learned
# bytes; SHA-256 of the LM d6981ab4d77ba712b48ef69d69042d75b5e39b9dce5fb5a5b054fd08e06afb95), and one change:
# answers may run to 600 tokens instead of 400, because this quantization writes longer answers
# (25 of 154 development answers were cut at 400).
#
#   scripts/harness/run_system_q3.sh <exam.json> <answers.json>
#
# Results and the development gate: docs/results/2026-09-27-harness-of-models.md.
set -euo pipefail
EXAM=$1; OUT=$2
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
MODEL=${MODEL:-$ROOT/artifacts/harness/gguf/Qwen3.5-4B-Q3_K_M.gguf}
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
  --retrieval "$INDEX" --k 4 --images --max-tokens 600 \
  --essay-bank "$BANK" --essay-judge 1 --essay-k 5 --essay-final lexical --workers 8
