source "$(dirname "$0")/config.sh"

OUTDIR="results/${MODEL//\//_}_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTDIR"

MODEL_ARGS="model=${MODEL},base_url=${OLLAMA_URL},num_concurrent=1,max_retries=3,tokenized_requests=False,max_gen_toks=${MAX_GEN_TOKS}"
LIMIT_FLAG=""
[ -n "$LIMIT" ] && LIMIT_FLAG="--limit ${LIMIT}"

COMMON="--model local-chat-completions --model_args $MODEL_ARGS --apply_chat_template $LIMIT_FLAG --log_samples --output_path $OUTDIR"

echo
echo "================  GSM8K on $MODEL  ================"
lm_eval $COMMON --tasks gsm8k --num_fewshot 5 --fewshot_as_multiturn 2>&1 | tee "$OUTDIR/gsm8k.log"

echo
echo "================  IFEval on $MODEL  ================"
lm_eval $COMMON --tasks ifeval --num_fewshot 0 2>&1 | tee "$OUTDIR/ifeval.log"

echo
echo "================  MMLU 5-shot on $MODEL  ================"
lm_eval $COMMON --tasks mmlu_generative --num_fewshot 5 --fewshot_as_multiturn 2>&1 | tee "$OUTDIR/mmlu.log"
