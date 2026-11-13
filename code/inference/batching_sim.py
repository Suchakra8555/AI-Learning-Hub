"""Static vs continuous batching, on fake requests. Run: python batching_sim.py

One step = one decode step, where every request in the batch makes one token.
The GPU has SLOTS places. A slot is busy while a request sits in it.
shortcut: prefill costs nothing here, and every step costs the same. Real servers differ.
"""
import random

SLOTS = 4
random.seed(7)
# 20 requests: one arrives every 2 steps, and each wants 4 to 60 output tokens.
REQUESTS = [{"arrive": i * 2, "tokens": random.choice([4, 6, 8, 12, 20, 40, 60])} for i in range(20)]


def run(continuous):
    waiting = sorted(REQUESTS, key=lambda r: r["arrive"])
    slots = [None] * SLOTS  # each slot holds [request, tokens_left]
    t, busy, waits, finishes = 0, 0, [], []
    while waiting or any(slots):
        # Static: only fill slots when the whole batch is empty. Continuous: fill any free slot.
        if continuous or not any(slots):
            for i in range(SLOTS):
                if slots[i] is None and waiting and waiting[0]["arrive"] <= t:
                    r = waiting.pop(0)
                    slots[i] = [r, r["tokens"]]
                    waits.append(t - r["arrive"])
        busy += sum(1 for s in slots if s)
        for i, s in enumerate(slots):
            if s:
                s[1] -= 1
                if s[1] == 0:
                    finishes.append(t + 1 - s[0]["arrive"])
                    slots[i] = None
        t += 1
    return t, busy / (t * SLOTS), sum(waits) / len(waits), sum(finishes) / len(finishes)


for name, cont in [("static", False), ("continuous", True)]:
    steps, util, wait, finish = run(cont)
    print(f"{name:10}  total steps {steps:3}  slot use {util:5.1%}  avg wait {wait:5.1f}  avg finish {finish:5.1f}")
