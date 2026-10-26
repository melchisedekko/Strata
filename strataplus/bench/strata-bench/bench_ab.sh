#!/usr/bin/env bash
# Wrapper: esempio di lancio sulle GPU (non eseguito in questa box, che non ha GPU).
# Uso: ./bench_ab.sh <strata-binary> "<model args: --pack ... --mtp ...>" <prompts_tokens.jsonl>
set -euo pipefail
cd "$(dirname "$0")"
python3 bench_ab.py --strata "$1" --model-args "$2" --prompts "$3" --configs B,A1,A2,A3,A4 --reps 3 --max-new 256 --spec-trace --out runs
