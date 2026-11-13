"""Contiguous KV cache vs paged KV cache. Run: python paged_kv.py

A pool of GPU memory holds the KV cache. We admit requests until it is full.
Memory is counted in tokens. For a Llama 2 7B shape one token needs 0.5 MiB (see kv_cache.py).
shortcut: each request is given its final length up front. A real server only learns it as it decodes.
"""
import math
import random

MIB_PER_TOKEN = 0.5
POOL_TOKENS = 49152  # 24 GiB of KV cache
MAX_LEN = 4096  # the longest a request may grow
BLOCK = 16  # tokens per page
random.seed(3)
# 200 queued requests. Most are short, a few are long.
LENGTHS = [min(MAX_LEN, int(random.expovariate(1 / 700)) + 50) for _ in range(200)]


def admit(cost):
    """Admit requests in order while the pool has room. Return (count, tokens reserved, tokens used)."""
    free, count, used = POOL_TOKENS, 0, 0
    for n in LENGTHS:
        if cost(n) > free:
            break
        free -= cost(n)
        count += 1
        used += n
    return count, POOL_TOKENS - free, used


def gib(tokens):
    return tokens * MIB_PER_TOKEN / 1024


for name, cost in [
    ("contiguous (reserve max length)", lambda n: MAX_LEN),
    (f"paged ({BLOCK}-token blocks)", lambda n: math.ceil(n / BLOCK) * BLOCK),
]:
    count, reserved, used = admit(cost)
    waste = reserved - used
    print(f"{name:32} requests {count:3}  reserved {gib(reserved):5.1f} GiB  "
          f"used {gib(used):5.1f} GiB  wasted {gib(waste):5.1f} GiB ({waste / reserved:.0%})")
