---
title: Train a tiny model, then convert, quantize and run it
summary: The full path a fine-tuned model takes into llama.cpp, done for real on a CPU. Train a 4M-parameter Llama on this course, convert it to GGUF, check llama.cpp gives the same answer as PyTorch, quantize it, and measure what quantization cost.
time: 35 min (10 of them training)
---

Downloading a ready-made GGUF teaches you to run llama.cpp. It does not teach you what happens when **your** model has to get there: after a fine-tune, after a new architecture, or when a downloaded file behaves oddly. This lesson walks that path end to end with a model small enough to train on a laptop CPU in ten minutes.

We also had a practical reason. Our build machine could not reach Hugging Face, so we could not download a model. Training our own turned out to be the better lesson: we know every number in the model, and we can check llama.cpp against the original.

## The plan

1. **Train** a tiny Llama-shaped model on this course's lessons, with PyTorch and Hugging Face `transformers`. Save it in Hugging Face format.
2. **Convert** it to GGUF with llama.cpp's `convert_hf_to_gguf.py`.
3. **Check** that llama.cpp gives exactly the same output as PyTorch.
4. **Quantize** to Q8_0, Q4_K_M and Q4_0.
5. **Run** and **measure** each one.

`code/llamacpp/pipeline.sh` runs steps 2 to 5 in one go once you have a model.

## Step 1: train

```bash
pip install torch transformers sentencepiece safetensors
python code/llamacpp/train_tiny_llama.py --out tiny-llama --steps 1500
```

On Linux, `pip install torch` pulls the CUDA build, about 900 MB plus some 2 GB of CUDA libraries. For CPU only, add `--index-url https://download.pytorch.org/whl/cpu`. (Our machine could not reach that index, so we installed the CUDA build. It runs on CPU too, just bigger.)

The script does four things:

- Joins all 139 lesson files of this course into 1.18 million characters of text.
- Trains a **SentencePiece** tokenizer with 2,000 tokens. That is the tokenizer family Llama 1 and 2 used. `byte_fallback` means any character can still be written as raw bytes.
- Builds a `LlamaForCausalLM` with 4 layers, hidden size 256, 4 attention heads and 2 key-value heads (**grouped-query attention**: pairs of query heads share one key-value head, which halves the KV cache).
- Trains 1,500 steps of next-token prediction and saves `config.json`, `model.safetensors` and `tokenizer.model`.

Our run:

```text
corpus: 139 files, 1,178,496 characters
tokens: 407,859 (2.9 characters per token)
parameters: 4.0M
step     1  loss 7.641       1s
step   500  loss 3.493     205s
step  1000  loss 2.973     397s
step  1500  loss 2.658     586s
greedy sample from PyTorch: "The KV cache, so the agent's own `code/livekit/lab/docker/types.py`, `lk room list --room de"
```

The loss started at 7.64, which is about ln(2000) = 7.6, a model guessing at random. It ended at 2.66. The sample is nonsense, but nonsense made of this course: agents, a LiveKit path, an `lk` command. Keep that sample. We will compare llama.cpp against it.

## Step 2: convert to GGUF

```bash
python $LLAMA/convert_hf_to_gguf.py tiny-llama --outtype f16 --outfile tiny-llama-F16.gguf
```

It took 4 seconds. The log shows the three jobs of a converter:

```text
INFO:hf-to-gguf:Model architecture: LlamaForCausalLM
INFO:hf-to-gguf:output.weight,              torch.float32 --> F16, shape = {256, 2000}
INFO:hf-to-gguf:token_embd.weight,          torch.float32 --> F16, shape = {256, 2000}
INFO:hf-to-gguf:blk.0.attn_norm.weight,     torch.float32 --> F32, shape = {256}
INFO:hf-to-gguf:blk.0.ffn_down.weight,      torch.float32 --> F16, shape = {704, 256}
...
INFO:hf-to-gguf:gguf: context length = 512
INFO:hf-to-gguf:gguf: head count = 4
INFO:hf-to-gguf:gguf: key-value head count = 2
...
INFO:gguf.vocab:Setting special token type bos to 1
INFO:gguf.gguf_writer:tiny-llama-F16.gguf: n_tensors = 39, total_size = 8.0M
```

1. **Pick a class** from `config.json`'s `architectures` field. `LlamaForCausalLM` maps to `LlamaModel` in `conversion/llama.py`.
2. **Rename and convert tensors.** `model.layers.0.mlp.down_proj.weight` becomes `blk.0.ffn_down.weight`. Weights go to F16; 1D norm weights stay F32. Shapes print in ggml order, innermost first, so PyTorch's `[2000, 256]` shows as `{256, 2000}`.
3. **Write metadata**: hyperparameters from `config.json`, and the tokenizer from `tokenizer.model`.

`--outtype` can be `f32`, `f16`, `bf16`, `q8_0` or `auto`. Converting to F16 or BF16 and quantizing afterwards gives you all the options of `llama-quantize`.

One warning appeared: `Unknown RoPE type: default`. Our `config.json` was written by transformers 5, which stores RoPE settings in a new `rope_parameters` block. The converter fell back to standard RoPE, which is what this model uses, so no harm done. On a real model with scaled RoPE (for long context), a warning like this deserves a careful look.

## Step 3: check llama.cpp matches PyTorch

A converted model should produce the **same** output as the original. Greedy decoding (`--temp 0`, always the top token) makes this easy to check:

```bash
llama-completion -m tiny-llama-F16.gguf -p "The KV cache" -n 24 --temp 0 -no-cnv
```

```text
PyTorch FP32:   The KV cache, so the agent's own `code/livekit/lab/docker/types.py`, `
llama.cpp F16:  The KV cache, so the agent's own `code/livekit/lab/docker/types.
```

Identical, word for word (llama.cpp's output stopped a few characters earlier at its token limit). We also checked the tokenizer: both turned the prompt into the same ids, `[1, 340, 748, 1959, 1772]`, which is `<s>`, ` The`, ` K`, `V`, ` cache`.

This is the test to run after any conversion, especially a new architecture. If the first few greedy tokens differ at F16, something is wrong in the conversion or the graph: a missed permute, a wrong RoPE setting, a different tokenizer. For a deeper check, compare logits; `examples/model-conversion/` has scripts for that.

## Step 4: quantize

```bash
llama-quantize tiny-llama-F16.gguf tiny-llama-Q8_0.gguf   Q8_0
llama-quantize tiny-llama-F16.gguf tiny-llama-Q4_K_M.gguf Q4_K_M
llama-quantize tiny-llama-F16.gguf tiny-llama-Q4_0.gguf   Q4_0
```

Each took well under a second. Sizes:

```text
-rw-r--r-- 8000544 tiny-llama-F16.gguf
-rw-r--r-- 4275744 tiny-llama-Q8_0.gguf
-rw-r--r-- 2663360 tiny-llama-Q4_K_M.gguf
-rw-r--r-- 2421184 tiny-llama-Q4_0.gguf
```

The [quantization lesson](lesson:llamacpp/quantization) reads the Q4_K_M log line by line.

## Step 5: run and measure

Greedy output from each file:

```text
F16:   The KV cache, so the agent's own `code/livekit/lab/docker/types.
Q8_0:  The KV cache, so the agent's own. The agent's own `code/livekit/lab/docker/t
Q4_0:  The KV cache, so the agent's audio. The agent's SDK service is the same in the room. The agent'
```

Q8_0 follows F16 for seven tokens, then picks a full stop instead of a backtick at a point where the model was nearly split between the two. Q4_0 drifts one token earlier. This is what quantization does: it does not break a model, it nudges close calls. Greedy output is a sensitive test for that, so do not expect quantized output to match exactly.

Perplexity on the training text (50 chunks of 128 tokens), from `llama-perplexity`:

| File | Perplexity |
|---|---|
| F16 | 48.07 |
| Q8_0 | 48.08 |
| Q4_K_M | 48.13 |
| Q4_0 | 49.03 |

We also ran a sharper test, **KL divergence**, which compares each quant's full next-token distribution with F16's at every position, on the first 60,000 characters of the text:

| File | Same top token as F16 | Mean KL divergence |
|---|---|---|
| Q8_0 | 98.5% | 0.0005 |
| Q4_K_M | 90.7% | 0.0197 |
| Q4_0 | 88.8% | 0.0277 |

Read the two tables together. By perplexity, Q4_K_M is almost free. By KL divergence, it picks a different top token about once in eleven. Both are true. Whether it matters depends on your task, which is why you finish with your own eval set. The commands are in [benchmark and tune](lesson:llamacpp/benchmark-and-tune).

## The same path for a real fine-tune

Replace step 1 with your fine-tune. If you trained a LoRA adapter, merge it into the base model first (or convert the adapter alone with `convert_lora_to_gguf.py`, see the [playbook](lesson:llamacpp/ai-engineer-playbook)). Then steps 2 to 5 are the same, with three additions:

- Keep the **chat template**. It lives in `tokenizer_config.json` and the converter copies it into the GGUF. Our model has none, which caused a real problem in [the server lesson](lesson:llamacpp/llama-server).
- **Compare greedy output at F16** with the original on a few prompts, as in step 3.
- **Measure the quant on your eval set**, not only perplexity.

:::try
Train with `--steps 300` instead of 1500 (about 2 minutes) and run the pipeline again. Perplexity will be much higher, and the quantized versions will differ more from F16. Undertrained models are less robust to rounding.
:::

:::check After converting your fine-tuned model, its F16 GGUF answers differently from the PyTorch model at temperature 0, from the first token. What do you check?
That the token ids match first (`llama-tokenize` against the original tokenizer); a wrong pre-tokenizer or missing BOS changes everything. Then the converter's warnings (RoPE type, unknown keys), then logits layer by layer. At F16 the greedy output should match.
:::

:::check Why does Q4_0 change the greedy output when perplexity barely moves?
Perplexity averages over all tokens. Greedy decoding follows a single path, and one changed choice at a close call changes everything after it. KL divergence and "same top token" show these close calls directly.
:::
