---
title: SGLang in depth
summary: How SGLang keeps shared prompts in a tree so it never computes the same start twice, and what else it offers on top.
time: 25 min
---

**SGLang** is an open-source inference framework. Its README says it is hosted by LMSYS, a non-profit, and lists NVIDIA, AMD, Google TPU, Intel, Apple Silicon and other hardware ([README](https://github.com/sgl-project/sglang/blob/main/README.md)).

We did not run SGLang. We read its docs and source on 2026-11-12. The script in this lesson is ours.

## The problem: the same start, again and again

Think of a support bot. Every request begins with the same system prompt. Many add one of a few RAG templates, and many paste the same document. Without reuse, the server runs prefill on that shared start for every single request.

SGLang's docs describe the idea this way: when requests share a prefix, the KV cache for that prefix is identical, so caching and reusing it avoids redundant work. They say SGLang introduced **RadixAttention** for this, using idle GPU memory to keep prefix KV caches ([HiCache design page](https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/hicache_design.mdx)).

## The radix tree

A **radix tree** is a tree where each path from the top spells out a sequence, and branches appear only where sequences differ. Think of a library index where "Chapter 3" is stored once and every entry under it hangs below. The docs say each node holds the KV cache of a run of tokens in GPU memory, and a path from the root to a leaf is the prefix of a request. Shared prefixes reuse the same nodes.

<figure>
<svg viewBox="0 0 600 300" role="img" aria-labelledby="t-radix d-radix">
  <title id="t-radix">A radix tree of shared prompts</title>
  <desc id="d-radix">A tree that starts with one system prompt node. It splits into two RAG templates. Each template leads to documents, and each document leads to different user questions. The shared parts are stored once.</desc>
  <defs><marker id="ah-radix" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <rect class="box hot" x="8" y="120" width="92" height="40" rx="6"/><text x="54.0" y="137.0" font-size="12" text-anchor="middle">system</text><text x="54.0" y="152.0" font-size="10" class="small" text-anchor="middle">22 tokens</text>
  <rect class="box" x="130" y="70" width="100" height="40" rx="6"/><text x="180.0" y="87.0" font-size="12" text-anchor="middle">template A</text><text x="180.0" y="102.0" font-size="10" class="small" text-anchor="middle">Use the context</text>
  <rect class="box" x="130" y="175" width="100" height="40" rx="6"/><text x="180.0" y="192.0" font-size="12" text-anchor="middle">template B</text><text x="180.0" y="207.0" font-size="10" class="small" text-anchor="middle">Here are the...</text>
  <rect class="box" x="262" y="30" width="86" height="40" rx="6"/><text x="305.0" y="54.2" font-size="12" text-anchor="middle">doc 1</text>
  <rect class="box" x="262" y="90" width="86" height="40" rx="6"/><text x="305.0" y="114.2" font-size="12" text-anchor="middle">doc 2</text>
  <rect class="box" x="262" y="160" width="86" height="40" rx="6"/><text x="305.0" y="184.2" font-size="12" text-anchor="middle">doc 1</text>
  <rect class="box" x="262" y="220" width="86" height="40" rx="6"/><text x="305.0" y="244.2" font-size="12" text-anchor="middle">no doc</text>
  <rect class="box" x="380" y="6" width="92" height="40" rx="6"/><text x="426.0" y="30.2" font-size="12" text-anchor="middle">q: refund?</text>
  <rect class="box" x="380" y="46" width="92" height="40" rx="6"/><text x="426.0" y="70.2" font-size="12" text-anchor="middle">q: invoice?</text>
  <rect class="box" x="380" y="90" width="92" height="40" rx="6"/><text x="426.0" y="114.2" font-size="12" text-anchor="middle">q: reset?</text>
  <rect class="box" x="380" y="160" width="92" height="40" rx="6"/><text x="426.0" y="184.2" font-size="12" text-anchor="middle">q: refund?</text>
  <rect class="box" x="380" y="220" width="92" height="40" rx="6"/><text x="426.0" y="244.2" font-size="12" text-anchor="middle">q: hello</text>
  <path class="arrow" d="M100 140 H115 V90 H130"/>
  <path class="arrow" d="M100 140 H115 V195 H130"/>
  <path class="arrow" d="M230 90 H246 V50 H262"/>
  <path class="arrow" d="M230 90 H246 V110 H262"/>
  <path class="arrow" d="M230 195 H246 V180 H262"/>
  <path class="arrow" d="M230 195 H246 V240 H262"/>
  <path class="arrow" d="M348 50 H364 V26 H380"/>
  <path class="arrow" d="M348 50 H364 V66 H380"/>
  <path class="arrow" d="M348 110 H380"/>
  <path class="arrow" d="M348 180 H380"/>
  <path class="arrow" d="M348 240 H380"/>
  <text x="8" y="288" font-size="13" text-anchor="start" class="small">Every path from the left is a prompt prefix. Shared start = shared node = computed once.</text>
</svg>
<figcaption>Five prompts share one stored system prompt. Only the last box on each path, the user&#x27;s question, is unique.</figcaption>
</figure>

A new request walks down from the root while its tokens match. If a match stops in the middle of a node, the docs say the node is split to make an exact boundary.

<figure>
<svg viewBox="0 0 500 260" role="img" aria-labelledby="t-hit d-hit">
  <title id="t-hit">A cache hit and a cache miss</title>
  <desc id="d-hit">Request one shares its system prompt, template and document with cached prompts, so only its new question is computed. Request two starts with a different system prompt, so nothing matches and everything is computed.</desc>
  <defs><marker id="ah-hit" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <text x="8" y="22" font-size="14" text-anchor="start" font-weight="700">New request 1: same system prompt, template A, doc 1, new question</text>
  <rect class="box hot" x="10" y="36" width="120" height="50" rx="8"/><text x="70.0" y="58.0" font-size="13" text-anchor="middle">system</text><text x="70.0" y="74.0" font-size="11" class="small" text-anchor="middle">reused</text>
  <rect class="box hot" x="134" y="36" width="110" height="50" rx="8"/><text x="189.0" y="58.0" font-size="13" text-anchor="middle">template A</text><text x="189.0" y="74.0" font-size="11" class="small" text-anchor="middle">reused</text>
  <rect class="box hot" x="248" y="36" width="80" height="50" rx="8"/><text x="288.0" y="58.0" font-size="13" text-anchor="middle">doc 1</text><text x="288.0" y="74.0" font-size="11" class="small" text-anchor="middle">reused</text>
  <rect class="box" x="332" y="36" width="150" height="50" rx="8"/><text x="407.0" y="58.0" font-size="13" text-anchor="middle">new question</text><text x="407.0" y="74.0" font-size="11" class="small" text-anchor="middle">computed</text>
  <text x="10" y="108" font-size="13" text-anchor="start" class="small">Walk down the tree: 3 nodes match. Only the question needs prefill.</text>
  <text x="8" y="158" font-size="14" text-anchor="start" font-weight="700">New request 2: a different system prompt</text>
  <rect class="box" x="10" y="172" width="472" height="50" rx="8"/><text x="246.0" y="194.0" font-size="13" text-anchor="middle">nothing matches at the root</text><text x="246.0" y="210.0" font-size="11" class="small" text-anchor="middle">everything is computed</text>
  <text x="10" y="244" font-size="13" text-anchor="start" class="small">The cache only helps when the start of the prompt repeats.</text>
</svg>
<figcaption>Hit: reuse the shared start, compute the end. Miss: compute it all.</figcaption>
</figure>

## Run it

`code/inference/radix_cache.py` builds a prefix tree over 50 made-up chat prompts. Each has a 22-token system prompt, one of 3 RAG templates, a 60-token document in 80% of cases (5 documents), and a unique question. It counts tokens as words.

```text
50 prompts, 4397 prompt tokens, system prompt 22 tokens
no cache     computed  4397  reused     0 (0%)
prefix tree  computed  1423  reused  2974 (68%)
```

With the tree, 68% of prompt tokens were found already computed. That number comes from our invented prompts, where the shared parts are large by design. Your reuse rate depends on how much of your traffic really repeats.

The script uses one node per token and never evicts anything. A real cache merges runs into one node and has a size limit. SGLang's docs say that when memory is full it evicts prefixes from the leaves. The default policy is `lru`, least recently used, and `lfu`, `slru` and `priority` also exist ([eviction policies](https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/radix_eviction_policy.mdx)).

## Cache-aware scheduling

Which waiting request should go next? SGLang's `--schedule-policy` flag accepts `lpm`, `random`, `fcfs`, `dfs-weight`, `lof`, `priority` and `routing-key` ([server arguments](https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/server_arguments.mdx)). The docs page does not explain them. In the source, `lpm` is commented as "longest prefix match" and sorts the waiting queue that way. The idea: serve the request that reuses the most cache first. The default is `fcfs`, first come, first served.

There is a second, separate place for this. SGLang's model gateway, a router that sits in front of several servers, has a `cache_aware` policy that "combines cache locality with load balancing", and the docs call it the default ([gateway docs](https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/sgl_model_gateway.mdx)). That is a hint of the fleet problem the [engine comparison](lesson:inference/choosing-an-engine) comes back to.

## Structured output

Sometimes you need the model to return valid JSON. SGLang lets a request pass a JSON schema, a regular expression or an EBNF grammar to constrain the output. The docs say the output "will be guaranteed to follow the given constraints". XGrammar is the default backend, and Outlines and Llguidance are alternatives ([structured outputs](https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/structured_outputs.mdx)). The docs still advise telling the model the format in the prompt too, for better quality. vLLM lists structured outputs as well, so this is not unique to SGLang.

## The frontend language

SGLang also ships a Python **frontend language** for writing a multi-step prompt as a program. In the tutorial, a function adds system, user and assistant parts to a state and calls `gen("answer", max_tokens=512)` to generate text ([tutorial](https://github.com/sgl-project/sglang/blob/main/docs/docs/references/frontend/frontend_tutorial.mdx)). It also covers multi-turn chats and fork parallelism. We read the tutorial and did not run it.

## Start a server

The quickstart says:

```bash
sglang serve MODEL_PATH --host 0.0.0.0 --port 30000
curl http://localhost:30000/v1/chat/completions ...
```

It targets Linux with an NVIDIA GPU and says to wait for `The server is fired up and ready to roll!` ([quickstart](https://github.com/sgl-project/sglang/blob/main/docs/docs/get-started/quickstart.mdx)). Other pages in the docs use `python -m sglang.launch_server --model-path ...`, so both forms exist. Not run here.

:::check What does a radix tree save you from doing twice?
Prefill on text that many requests share at their start, such as a system prompt or a template. That start is stored once and reused.
:::

:::check Our script reused 68% of tokens. Why might your traffic reuse less?
The prompts were made so that a large share is shared. If your requests start differently, or the cache evicts old branches, fewer tokens match.
:::
