"""A prefix tree for prompts, the idea behind SGLang's RadixAttention. Run: python radix_cache.py

Each prompt is a list of tokens (here, words). The tree remembers every prefix we have already
"computed". A new prompt walks down the tree as far as it matches. Those tokens are reused.
Only the rest needs prefill.
shortcut: one node per token, not one node per run of tokens (a real radix tree merges runs).
shortcut: nothing is ever evicted. A real cache has a size limit and drops old branches.
"""
import random

random.seed(11)
SYSTEM = ("You are a helpful support agent for Acme Cloud. Answer in plain words. "
          "Never share account secrets. Cite the document you used.").split()
TEMPLATES = [
    "Use the context below to answer the question. Context:".split(),
    "Here are the retrieved passages. Read them, then answer. Passages:".split(),
    "Summarize the following context first, then answer the user. Context:".split(),
]
DOCS = [[f"doc{d}w{i}" for i in range(60)] for d in range(5)]  # 5 documents, 60 tokens each


def make_prompts(n=50):
    prompts = []
    for q in range(n):
        template = random.choice(TEMPLATES)
        doc = random.choice(DOCS) if random.random() < 0.8 else []  # 20% have no document
        question = [f"q{q}w{i}" for i in range(random.randint(6, 14))]  # always unique
        prompts.append(SYSTEM + template + doc + question)
    return prompts


def serve(prompts, use_cache):
    tree, computed, reused, nodes = {}, 0, 0, 0
    for p in prompts:
        node, i = tree, 0
        while use_cache and i < len(p) and p[i] in node:  # walk down while the prefix matches
            node, i = node[p[i]], i + 1
        reused += i
        computed += len(p) - i
        for tok in p[i:]:  # remember the new part for next time
            node[tok] = {}
            node = node[tok]
            nodes += 1
    return computed, reused, nodes


prompts = make_prompts()
total = sum(len(p) for p in prompts)
print(f"{len(prompts)} prompts, {total} prompt tokens, system prompt {len(SYSTEM)} tokens")
for name, use in [("no cache", False), ("prefix tree", True)]:
    computed, reused, nodes = serve(prompts, use)
    extra = f"  tree nodes {nodes}" if use else ""
    print(f"{name:11}  computed {computed:5}  reused {reused:5} ({reused / total:.0%}){extra}")
