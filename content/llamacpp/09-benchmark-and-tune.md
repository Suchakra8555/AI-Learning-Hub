---
title: Measure, then tune - speed and quality with llama.cpp's own tools
summary: llama-bench for speed, llama-batched-bench for many users, llama-perplexity and KL divergence for quality, test-backend-ops for one kernel, and the settings that actually move the numbers.
time: 25 min
---

"It feels slow" and "the quant seems fine" are not measurements. llama.cpp ships the tools to replace both with numbers. This lesson runs each one and explains the settings worth tuning. The [inference track's benchmarking lesson](lesson:inference/benchmark-honestly) covers the general rules; this one is the llama.cpp toolkit.

Our numbers come from the 4M-parameter course model on 4 cores of a cloud Xeon. They show how to read the tools, not what a real model gets. Run them on your model and your hardware.

## Two speeds, two bottlenecks

Every speed table separates:

- **pp** (prompt processing, also **prefill**): reading the prompt. Many tokens go through at once, so it is limited by **compute**.
- **tg** (text generation, also **decode**): one token at a time. Each token reads every weight, so on real models it is limited by **memory bandwidth**.

They respond to different settings, so always look at both.

## llama-bench: speed of one setup

```bash
llama-bench -m model.gguf -p 512 -n 128
```

`-p 512` times processing a 512-token prompt; `-n 128` times generating 128 tokens. Each test runs 5 times (`-r`) and shows mean ± standard deviation. Comma lists sweep a setting. Our three quants at once:

```bash
llama-bench -m tiny-llama-F16.gguf,tiny-llama-Q8_0.gguf,tiny-llama-Q4_0.gguf -p 512 -n 128 -t 4
```

```text
| model            |     size |  params | backend | threads |  test |                t/s |
| llama ?B F16     | 7.59 MiB |  3.98 M | CPU     |       4 | pp512 | 17745.40 ± 1656.30 |
| llama ?B F16     | 7.59 MiB |  3.98 M | CPU     |       4 | tg128 |   5885.16 ± 749.28 |
| llama ?B Q8_0    | 4.03 MiB |  3.98 M | CPU     |       4 | pp512 | 30475.33 ± 4327.45 |
| llama ?B Q8_0    | 4.03 MiB |  3.98 M | CPU     |       4 | tg128 |   6475.32 ± 661.77 |
| llama ?B Q4_0    | 2.27 MiB |  3.98 M | CPU     |       4 | pp512 |  33164.43 ± 777.17 |
| llama ?B Q4_0    | 2.27 MiB |  3.98 M | CPU     |       4 | tg128 |   8344.40 ± 692.28 |
```

(Columns trimmed to fit.) Smaller quants are faster on both tests. The ± values are large: a model this small finishes a run in milliseconds, so noise from the machine shows. With real models the spread is usually a few percent. If yours is large, close other programs and raise `-r`.

A thread sweep, `-t 1,2,4`:

| Threads | pp512 (tok/s) | tg128 (tok/s) |
|---|---|---|
| 1 | 9,951 | 5,835 |
| 2 | 16,983 | 5,651 |
| 4 | 27,854 | 5,377 |

Prompt processing scaled with threads: it is compute-bound. Generation did not. For our tiny model the limit is per-token overhead; for a real model it is memory bandwidth. Either way, more threads did not help generation. On real CPUs, the best `-t` for generation is often the number of **physical performance cores**, not all logical threads. Measure it.

Other useful columns to sweep: `-ngl 0,10,20,99` (GPU layers), `-fa 0,1` (flash attention), `-ctk f16,q8_0` (KV cache type), `-b` and `-ub`, and `-d 4096` to measure speed **at depth**, with 4,096 tokens already in the context. Generation slows down as the context fills, and `-d` shows by how much. `-o json` or `-o csv` give machine-readable output for tracking over time.

## llama-batched-bench: speed for many users

`llama-bench` runs one sequence. A server runs many. `llama-batched-bench` measures throughput as parallel sequences grow:

```bash
llama-batched-bench -m tiny-llama-Q4_0.gguf -c 4096 -b 2048 -ub 512 -npp 128 -ntg 128 -npl 1,2,4,8,16
```

```text
|    PP |     TG |    B |   N_KV |   T_PP s | S_PP t/s |   T_TG s | S_TG t/s |      T s |    S t/s |
|   128 |    128 |    1 |    256 |    0.004 | 32761.71 |    0.030 |  4224.14 |    0.034 |  7483.41 |
|   128 |    128 |    2 |    512 |    0.006 | 43760.68 |    0.055 |  4638.10 |    0.061 |  8387.26 |
|   128 |    128 |    4 |   1024 |    0.023 | 22429.58 |    0.072 |  7124.37 |    0.095 | 10813.89 |
|   128 |    128 |    8 |   2048 |    0.016 | 64386.32 |    0.123 |  8308.72 |    0.139 | 14718.14 |
|   128 |    128 |   16 |   4096 |    0.045 | 45115.10 |    0.174 | 11739.62 |    0.220 | 18631.14 |
```

`B` is the number of parallel sequences, `PP`/`TG` the prompt and generated tokens per sequence, and `S_TG` the total generation speed of all sequences together. It rose from 4,224 to 11,740 tokens per second at 16 sequences. But divide by B to get what **one user** sees: 4,224 alone, 734 each at 16. Batching trades per-user speed for total throughput. Pick `-np` on a server from this table and your latency target.

## llama-perplexity: quality in one number

**Perplexity** measures how surprised the model is by real text. Lower is better. Compare files on the **same** text with the **same** settings:

```bash
llama-perplexity -m model-Q4_K_M.gguf -f wiki.test.raw -c 512
```

`scripts/get-wikitext-2.sh` downloads the standard test text. For your own use, a sample of your domain's text is more telling. Our quants on our training text:

| File | Perplexity |
|---|---|
| F16 | 48.07 |
| Q8_0 | 48.08 |
| Q4_K_M | 48.13 |
| Q4_0 | 49.03 |

## KL divergence: quality, token by token

Perplexity averages. **KL divergence** compares the quantized model's whole next-token distribution with the original's at every position. Two runs:

```bash
llama-perplexity -m model-F16.gguf    -f text.txt -c 128 --kl-divergence-base f16.kld
llama-perplexity -m model-Q4_K_M.gguf -f text.txt -c 128 --kl-divergence-base f16.kld --kl-divergence
```

The first saves the F16 model's logits (the file gets large on real models; use a modest text). The second compares. Our results, on 60,000 characters:

| File | Mean KLD | 99th percentile KLD | Same top token as F16 |
|---|---|---|---|
| Q8_0 | 0.0005 | 0.0036 | 98.5% |
| Q4_K_M | 0.0197 | 0.2085 | 90.7% |
| Q4_0 | 0.0277 | 0.2284 | 88.8% |

The perplexities of Q8_0 and Q4_K_M differ by 0.05. Their KL divergence differs by 40 times, and Q4_K_M picks a different top token about once in eleven. The **99th percentile** column matters too: it shows the worst positions, where a quant can derail an answer. This is why the contributing guide asks for KL divergence numbers with any new quant type.

## test-backend-ops: one kernel at a time

To compare kernels or check that a code change made something faster, time one op in isolation. One token through a Llama 3 8B-sized feed-forward matrix:

```bash
test-backend-ops perf -o MUL_MAT -b CPU -p 'type_a=(q4_0|f16|q8_0),type_b=f32,m=4096,n=1,k=14336'
```

| Weight type | Time per run |
|---|---|
| F16 | 5.42 ms |
| Q8_0 | 2.90 ms |
| Q4_0 | 1.91 ms |

The [ggml lesson](lesson:llamacpp/ggml-tensors-graphs-backends) explains why smaller types are faster.

## Settings that move the numbers

| Setting | Helps | Costs | Measure with |
|---|---|---|---|
| Smaller quant | tg and pp, memory | Quality | `llama-bench`, KL divergence |
| `-ngl` more layers on GPU | Everything, a lot | VRAM | `llama-bench -ngl 0,20,99` |
| `-fa on` | Usually speed at long context, and memory | Depends on backend; `auto` decides per device | `llama-bench -fa 0,1 -d 8192` |
| `-ctk q8_0 -ctv q8_0` | KV cache memory (about half) | A little quality; needs `-fa` | Memory in the load log, KLD |
| `-t` | pp up to the core count | Can hurt tg past physical cores | `llama-bench -t` sweep |
| `-ub` larger | pp on GPUs | Compute buffer memory | `llama-bench -ub 256,512,1024` |
| `-np` and `-c` on a server | Total throughput | Per-user speed, memory | `llama-batched-bench` |
| Speculative decoding | tg, when drafts are accepted | A draft model's memory | Server log "draft acceptance rate" |
| MoE: `-ncmoe N` | Fits big mixture-of-experts models | Expert layers run on CPU | `llama-bench` |

Two habits make tuning honest. Change **one** setting at a time. And write down the llama.cpp commit (`llama-bench` prints it as `build: 0fb8f15 (50)`), because a new commit can change speed by itself.

:::check Your server feels slow for single users after you raised `-np` from 1 to 8. Is something broken?
Probably not. With 8 sequences in each batch, total throughput rises, but each user's tokens per second fall. Check with `llama-batched-bench`: divide `S_TG` by `B` to see per-user speed, and pick an `-np` that keeps that above your target.
:::

:::check Q4_K_M and Q8_0 show nearly the same perplexity on your text. Can you ship Q4_K_M without more checks?
Not yet. Run KL divergence (mean, 99th percentile, same-top-token) and, above all, your own eval set. A small perplexity gap can hide a 10% change in top-token choices, which matters for tasks like extraction or tool calls.
:::
