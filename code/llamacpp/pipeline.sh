#!/usr/bin/env bash
# From a Hugging Face checkpoint to a running llama.cpp model, every step once.
#
#   LLAMA=~/src/llama.cpp bash code/llamacpp/pipeline.sh tiny-llama
#
# $1 is a folder with config.json + model.safetensors + tokenizer files
# (train_tiny_llama.py makes one). $LLAMA is your llama.cpp clone, already built.
# Python needs: torch, numpy, sentencepiece, safetensors (see llama.cpp's requirements/).
set -euo pipefail

SRC=${1:?usage: pipeline.sh <hf-model-folder>}
LLAMA=${LLAMA:?set LLAMA to your llama.cpp folder}
BIN=$LLAMA/build/bin
NAME=$(basename "$SRC")
PY=${PYTHON:-python}

echo "== 1. convert: Hugging Face safetensors -> GGUF (F16)"
$PY "$LLAMA/convert_hf_to_gguf.py" "$SRC" --outtype f16 --outfile "$NAME-F16.gguf"

echo "== 2. quantize: F16 -> Q8_0 and Q4_0"
for q in Q8_0 Q4_0; do
  "$BIN/llama-quantize" "$NAME-F16.gguf" "$NAME-$q.gguf" "$q" 2>&1 | grep -E "model size|quant size"
done
ls -l "$NAME"-*.gguf

echo "== 3. inspect: what is inside the file"
$PY "$(dirname "$0")/gguf_peek.py" "$NAME-Q8_0.gguf" | head -30

echo "== 4. run: greedy completion, no chat template"
"$BIN/llama-completion" -m "$NAME-Q8_0.gguf" -p "The KV cache" -n 30 --temp 0 -no-cnv 2>/dev/null

echo
echo "== 5. measure: perplexity on the training text (low = it learned it)"
"$BIN/llama-perplexity" -m "$NAME-F16.gguf" -f "$SRC/corpus.txt" -c 128 --chunks 50 2>&1 | grep -E "Final estimate"
"$BIN/llama-perplexity" -m "$NAME-Q4_0.gguf" -f "$SRC/corpus.txt" -c 128 --chunks 50 2>&1 | grep -E "Final estimate"
