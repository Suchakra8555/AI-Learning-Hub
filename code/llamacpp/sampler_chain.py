"""How llama.cpp picks the next token: a chain of samplers. Run: python sampler_chain.py

Each sampler takes the list of candidate tokens and their logits, and cuts or reshapes it.
The last one (dist) draws one token. This follows src/llama-sampler.cpp and the default
order and values in common/common.h (commit 0fb8f15):

    penalties -> dry -> top_n_sigma -> top_k(40) -> typical_p -> top_p(0.95) -> min_p(0.05) -> xtc -> temperature(0.8) -> dist

Note that temperature comes *after* the cuts by default. So top_p and min_p see the raw
logits, and temperature only reshapes what survived. Change the order with --samplers.

shortcut: only penalties (repeat), top_k, top_p, min_p, temperature and dist are written here.
The others are off by default (dry, typical_p, xtc, top_n_sigma).
"""
import math
import random


def softmax(cands):
    m = max(l for _, l in cands)
    exps = [math.exp(l - m) for _, l in cands]
    s = sum(exps)
    return [e / s for e in exps]


def penalties(cands, last_tokens, repeat=1.1):
    """Repeat penalty: shrink the logit of any token seen recently (divide if > 0, multiply if < 0)."""
    seen = set(last_tokens)
    return [(t, (l / repeat if l > 0 else l * repeat) if t in seen else l) for t, l in cands]


def top_k(cands, k=40):
    return sorted(cands, key=lambda c: -c[1])[:k]


def top_p(cands, p=0.95):
    """Keep the smallest set of best tokens whose probabilities add up to at least p."""
    cands = sorted(cands, key=lambda c: -c[1])
    probs, total = softmax(cands), 0.0
    for i, pr in enumerate(probs):
        total += pr
        if total >= p:
            return cands[: i + 1]
    return cands


def min_p(cands, p=0.05):
    """Keep tokens at least p times as likely as the best one. In logits: l >= l_max + ln(p)."""
    cut = max(l for _, l in cands) + math.log(p)
    return [c for c in cands if c[1] >= cut]


def temperature(cands, t=0.8):
    return [(tok, l / t) for tok, l in cands]


def dist(cands, rng):
    return rng.choices([t for t, _ in cands], weights=softmax(cands))[0]


if __name__ == "__main__":
    vocab = ["the", "cache", "model", "token", "GPU", "banana", "llama", ".", "of", "runs"]
    # Pretend logits from a model after the prompt "The KV".
    logits = [1.0, 6.0, 3.5, 3.0, 2.0, -2.0, 1.5, 0.5, 0.2, 2.5]
    cands = list(enumerate(logits))

    def show(name, cs):
        probs = softmax(cs)
        row = ", ".join(f"{vocab[t]} {p:.2f}" for (t, _), p in sorted(zip(cs, probs), key=lambda x: -x[1]))
        print(f"{name:<22}{len(cs):>3} left: {row}")

    show("start", cands)
    cands = penalties(cands, last_tokens=[1], repeat=1.1)  # "cache" was said a moment ago
    show("penalties (1.1)", cands)
    cands = top_k(cands, 5)
    show("top_k (5)", cands)
    cands = top_p(cands, 0.95)
    show("top_p (0.95)", cands)
    cands = min_p(cands, 0.1)
    show("min_p (0.1)", cands)
    cands = temperature(cands, 0.8)
    show("temperature (0.8)", cands)

    rng = random.Random(42)  # llama.cpp also takes a --seed
    picks = [vocab[dist(cands, rng)] for _ in range(1000)]
    print("\n1000 draws:", {w: picks.count(w) for w in sorted(set(picks), key=picks.count, reverse=True)})
    print("greedy (temperature <= 0 in llama.cpp):", vocab[max(enumerate(logits), key=lambda c: c[1])[0]])
