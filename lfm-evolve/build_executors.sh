#!/usr/bin/env bash
# Build executors from their Modelfiles: `ollama pull <FROM>` then `ollama create <name> -f Modelfile.<name>`.
# Every Modelfile raises num_ctx to 16384 (Ollama's default context truncates multi-step transcripts
# silently; run_experiment.py's preflight warns below 16384).
#
#   ./build_executors.sh                    # the dissertation's two executors: lfm2.5-16k qwen3-1.7b-16k
#   ./build_executors.sh all                # every Modelfile.*-16k in this directory
#   ./build_executors.sh granite4-1b-h-16k granite4-1b-16k
#   ./build_executors.sh --list             # names, backbones and sources, nothing pulled
#
# The optimiser (Modelfile.deepseek-coder-v2-16b-8k) is built separately, see vm_use.txt: its Modelfile
# pins num_gpu for the 8 GB laptop card and is not needed when Claude is the optimiser.
set -euo pipefail
cd "$(dirname "$0")"

modelfile_of() { [ "$1" = "lfm2.5-16k" ] && echo Modelfile || echo "Modelfile.$1"; }
from_of() { awk '$1 == "FROM" {print $2; exit}' "$1"; }
note_of() { sed -n '1{s/^# *//p}' "$1"; }

if [ "${1:-}" = "--list" ]; then
    for f in Modelfile Modelfile.*-16k; do
        name=$([ "$f" = Modelfile ] && echo lfm2.5-16k || echo "${f#Modelfile.}")
        printf '%-24s FROM %-36s %s\n' "$name" "$(from_of "$f")" "$(note_of "$f")"
    done
    exit 0
fi

if [ $# -eq 0 ]; then
    names=(lfm2.5-16k qwen3-1.7b-16k)
elif [ "$1" = "all" ]; then
    names=(lfm2.5-16k)
    for f in Modelfile.*-16k; do names+=("${f#Modelfile.}"); done
else
    names=("$@")
fi

failed=()
for name in "${names[@]}"; do
    f=$(modelfile_of "$name")
    if [ ! -f "$f" ]; then echo "!! no $f for $name"; failed+=("$name"); continue; fi
    src=$(from_of "$f")
    echo "== $name  (FROM $src)"
    if ! ollama pull "$src"; then echo "!! pull failed: $src"; failed+=("$name"); continue; fi
    if ! ollama create "$name" -f "$f"; then echo "!! create failed: $name"; failed+=("$name"); continue; fi
    ctx=$(ollama show "$name" | awk '$1 == "num_ctx" {print $2}')
    arch=$(ollama show "$name" 2>/dev/null | awk '$1 == "architecture" {print $2}')
    echo "   built: architecture=${arch:-?} num_ctx=${ctx:-default}"
done
echo
echo "Built ${#names[@]} executor(s); failed: ${#failed[@]}${failed[*]:+ (${failed[*]})}"
echo "Use them with:  python run_experiment.py --models ${names[*]} ..."
[ ${#failed[@]} -eq 0 ]
