#!/usr/bin/env bash
# Larger alternative of the harness: run_system.sh unchanged, with only the solver LM swapped for the base
# (not fine-tuned) Qwen3.5-4B Q4_K_M from unsloth/Qwen3.5-4B-GGUF, plus the same Q8_0 vision projector
# (3,107,832,544 learned bytes; SHA-256 of the LM 00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4).
#
#   scripts/harness/run_system_q4.sh <exam.json> <answers.json>
#
# Results on the four June papers: docs/results/2026-09-27-harness-of-models.md.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
MODEL=${MODEL:-$ROOT/artifacts/harness/gguf/Qwen3.5-4B-Q4_K_M.gguf} exec bash "$ROOT/scripts/harness/run_system.sh" "$@"
