"""A toy timing model: one pool of GPUs doing everything, or two pools. Run: python disagg_sim.py

THIS IS A TOY, NOT A BENCHMARK. Every number below is made up so the shapes are easy to see.
It was not fitted to any real GPU, model or engine, and it says nothing about how fast Dynamo is.

The setup: 8 GPUs, a steady stream of requests, 200 output tokens each.
  colocated   every GPU does prefill and decode. A prefill pauses the decode on that GPU.
  split       some GPUs only prefill, the rest only decode. The KV cache travels between them.
Load is set so that, in the colocated setup, prefill takes 25% of each GPU's time. Same traffic
for both setups. For the split we try every pool size and keep the one with the lowest TTFT
among those where no pool is over 90% busy.

Made-up numbers:
  prefill        0.12 ms per prompt token
  decode step    15 ms + 0.5 ms for each sequence in the batch
  KV transfer    0.1 MB per token over a 25 GB/s link, plus 10 ms of setup per request
shortcut: waiting in the prefill queue uses the textbook formula for one queue with steady
service times. Decode batches never queue. No chunked prefill, no prefix reuse, no failures.
"""
GPUS = 8
OUT_TOKENS = 200
PREFILL_BUSY = 0.25  # share of each GPU's time spent on prefill when colocated
MS_PER_PROMPT_TOKEN = 0.12
STEP_BASE_MS, STEP_PER_SEQ_MS = 15.0, 0.5
MB_PER_TOKEN, LINK_GB_PER_S, SETUP_MS = 0.1, 25.0, 10.0


def queue_wait(busy, service_ms):
    """Mean wait before service starts: M/D/1 queue."""
    return busy * service_ms / (2 * (1 - busy))


def decode_step(rate_per_s):
    """Step time and batch size on one GPU taking rate_per_s requests/s. None if it cannot keep up."""
    k = rate_per_s * OUT_TOKENS * STEP_PER_SEQ_MS / 1000
    if k >= 0.9:
        return None
    seqs = rate_per_s * OUT_TOKENS * STEP_BASE_MS / 1000 / (1 - k)
    return STEP_BASE_MS + STEP_PER_SEQ_MS * seqs, seqs


def colocated(tokens):
    p = tokens * MS_PER_PROMPT_TOKEN
    rate = PREFILL_BUSY / (p / 1000)  # requests per second per GPU
    step, _ = decode_step(rate)
    ttft = queue_wait(PREFILL_BUSY, p) + p
    itl = step + PREFILL_BUSY * p / 2  # on average a token boundary sometimes lands inside a prefill
    return ttft, itl, step + p  # TTFT, mean ITL, worst ITL (a token just before a prefill starts)


def split(tokens):
    p = tokens * MS_PER_PROMPT_TOKEN
    total_rate = GPUS * PREFILL_BUSY / (p / 1000)
    xfer = tokens * MB_PER_TOKEN / (LINK_GB_PER_S * 1000) * 1000 + SETUP_MS
    best = None
    for gp in range(1, GPUS):
        busy = total_rate * p / 1000 / gp
        d = decode_step(total_rate / (GPUS - gp))
        if busy >= 0.9 or d is None:
            continue
        ttft = queue_wait(busy, p) + p + xfer
        if best is None or ttft < best[0]:
            best = (ttft, d[0], gp, xfer)
    return best  # TTFT, ITL, prefill GPUs, transfer ms (or None)


print(f"toy model, {GPUS} GPUs, {OUT_TOKENS} output tokens per request. Times in ms. Not a benchmark.")
print(f"{'prompt':>7} | {'colocated':^26} | {'split':^40} | verdict")
print(f"{'tokens':>7} | {'TTFT':>7} {'ITL':>7} {'worst ITL':>9} | {'pools P+D':>9} {'TTFT':>7} {'ITL':>7} {'transfer':>8} |")
for tokens in [500, 4000, 16000]:
    c_ttft, c_itl, c_worst = colocated(tokens)
    s = split(tokens)
    if s is None:
        print(f"{tokens:7} | {c_ttft:7.0f} {c_itl:7.1f} {c_worst:9.0f} | {'no stable split':^40} | stay colocated")
        continue
    s_ttft, s_itl, gp, xfer = s
    verdict = ("split wins on TTFT and ITL" if s_ttft < c_ttft and s_itl < c_itl
               else "split wins on ITL only" if s_itl < c_itl
               else "split wins on TTFT only" if s_ttft < c_ttft
               else "stay colocated")
    print(f"{tokens:7} | {c_ttft:7.0f} {c_itl:7.1f} {c_worst:9.0f} | {gp:>4}+{GPUS - gp:<4} {s_ttft:7.0f} {s_itl:7.1f} {xfer:8.0f} | {verdict}")
