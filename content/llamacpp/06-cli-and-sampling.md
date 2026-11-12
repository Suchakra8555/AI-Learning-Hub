---
title: The command line, and how the next token is chosen
summary: llama-cli for chat, llama-completion for plain text, the flags that matter, and the sampler chain - temperature, top-k, top-p, min-p, penalties, seeds and grammars - with real runs showing what each one does.
time: 30 min
---

Before you put a model behind a server, try it at the command line. It is the fastest way to see whether a model, a quant, a prompt or a sampling setting works. This lesson covers the two text tools and the one idea behind every generation setting: the **sampler chain**.

## Two tools

| Tool | Use it for | Chat template | Default mode |
|---|---|---|---|
| `llama-cli` (`llama cli`) | Chatting with a model | Applied (`--jinja` on by default) | Interactive conversation |
| `llama-completion` | Raw text in, text out; scripts; base models | Off unless `--jinja` | Conversation if the model has a template; `-no-cnv` for plain completion |

A chat with a system prompt, one turn, then exit:

```bash
llama-cli -m model.gguf -sys "You answer in one line." -p "What is GGUF?" -st
```

Plain completion, for base models and for scripts:

```bash
llama-completion -m model.gguf -p "The KV cache" -n 30 --temp 0 -no-cnv
```

We ran both on our tiny model. `llama-cli` showed its slash commands (`/regen`, `/clear`, `/read <file>` to add a file to the chat, `/exit`), answered, and printed speeds:

```text
> What is GGUF?
digest(self, ctx_interrupt_duration(self, c

[ Prompt: 22135.0 t/s | Generation: 2149.1 t/s ]
```

The answer is nonsense because the model is tiny, not because of the tool. Everything below uses `llama-completion -no-cnv` so the template does not get in the way.

## The flags that matter

| Flag | Meaning | Default at our commit |
|---|---|---|
| `-m` / `-hf` | Model file / Hugging Face repo | |
| `-p`, `-f` | Prompt text / prompt from a file | |
| `-sys` | System prompt (cli) | |
| `-n` | Max tokens to generate | -1 = until end of text |
| `-c` | Context size | 0 = the model's training length |
| `-ngl` | Layers on the GPU | auto |
| `-t` | CPU threads | -1 = auto |
| `-fa` | Flash attention: `on`, `off`, `auto` | auto |
| `-ctk`, `-ctv` | KV cache type: `f16`, `q8_0`, `q4_0`, ... | f16 |
| `-b`, `-ub` | Batch and micro-batch size | 2048, 512 |
| `-fit` | Shrink unset settings to fit free memory | on |
| `-j`, `--grammar-file` | Constrain output to a JSON schema or a GBNF grammar | |
| `-s` | Random seed | -1 = random |
| `--temp`, `--top-k`, `--top-p`, `--min-p` | Sampling, below | 0.80, 40, 0.95, 0.05 |
| `-v`, `-lv N` | Verbose logs | |

Almost every flag can also be set by an environment variable. `llama-cli --help` lists them, such as `LLAMA_ARG_CTX_SIZE`.

## From scores to a token

After each step the model gives a **logit** (a raw score) for every token in its vocabulary: 2,000 numbers for our model, 150,000 or more for big ones. Softmax turns logits into probabilities. Then a **sampler chain** narrows and reshapes that list, and the last step draws one token.

llama.cpp's default chain, from `common/common.h`:

```text
penalties -> dry -> top_n_sigma -> top_k -> typical_p -> top_p -> min_p -> xtc -> temperature -> dist
```

`dist` draws the token at random, weighted by the probabilities that are left. With default settings, `dry`, `top_n_sigma`, `typical_p` and `xtc` do nothing, and the penalty is 1.0 (off). So in practice the default is: **top-k 40, then top-p 0.95, then min-p 0.05, then temperature 0.8, then draw**.

Notice that **temperature comes last**. The cuts see the model's raw distribution, and temperature only reshapes the survivors. Some other engines apply temperature first. Change the order with `--samplers`, for example `--samplers "top_k;temperature"`.

## See each step with numbers

`code/llamacpp/sampler_chain.py` runs the chain on ten made-up candidates after the prompt "The KV", printing what survives each step:

```bash
python code/llamacpp/sampler_chain.py
```

```text
start                  10 left: cache 0.83, model 0.07, token 0.04, runs 0.03, GPU 0.02, llama 0.01, the 0.01, . 0.00, of 0.00, banana 0.00
penalties (1.1)        10 left: cache 0.74, model 0.10, token 0.06, runs 0.04, GPU 0.02, llama 0.01, the 0.01, . 0.01, of 0.00, banana 0.00
top_k (5)               5 left: cache 0.76, model 0.11, token 0.07, runs 0.04, GPU 0.02
top_p (0.95)            4 left: cache 0.78, model 0.11, token 0.07, runs 0.04
min_p (0.1)             2 left: cache 0.88, model 0.12
temperature (0.8)       2 left: cache 0.92, model 0.08

1000 draws: {'cache': 911, 'model': 89}
greedy (temperature <= 0 in llama.cpp): cache
```

What each step did:

- **Repeat penalty 1.1.** "cache" was used recently, so its logit was divided by 1.1. Its share dropped from 0.83 to 0.74. (A negative logit is multiplied instead, so a penalty never makes a token more likely; the source has a comment about that exact bug in the original paper's method.)
- **Top-k 5** kept the five best.
- **Top-p 0.95** kept the smallest set whose probabilities add up to 0.95. "GPU" fell off.
- **Min-p 0.1** kept tokens at least 0.1 times as likely as the best one. Only two survived. Min-p adapts: when the model is sure it cuts hard, when it is unsure it keeps many options.
- **Temperature 0.8** sharpened what was left: 0.88 became 0.92.

## Real runs: same prompt, different settings

Our tiny model, prompt "The KV cache", 20 tokens, Q8_0:

```text
--temp 0                     The KV cache, so the agent's own. The agent's own `code/livekit/lab/
--temp 0.8 -s 1              The KV cache stops the source the room. It gets no audio track, and the other side in a
--temp 0.8 -s 2              The KV cache, one participant joins the room per room, so you can add it. The caller joins the caller
--temp 1.5 --top-k 0
  --top-p 1 --min-p 0 -s 1   The KV cache} `/room~ference. Readfor-412 request`: Sule: alice now turns
--samplers "top_k;temperature"
  --top-k 3 --temp 0.8 -s 1  The KV cache users are a smaller model. Also links the best match. -
```

- **`--temp 0`** is greedy: always the top token, the same output every time. Use it for tests and extraction.
- **Same temperature, different seeds** give different text. The same seed gives the same text again on the same build and hardware; we ran `-s 1` twice and got byte-identical output. Fix `-s` when you need repeatable samples.
- **High temperature with all cuts off** lets rare tokens through: `}`, `~`, broken words. This is why the cuts exist.
- **A custom chain** (`top_k;temperature` with k=3) only ever picks among the top three, so the output stays closer to the greedy text.

## Grammars: rule out bad tokens entirely

Samplers make bad tokens unlikely. A **grammar** makes them impossible. Before sampling, the grammar sampler removes every token that would break the rules. JSON Schemas are converted to llama.cpp's grammar format, **GBNF**, automatically:

```bash
llama-completion -m tiny-llama-Q8_0.gguf -p "The KV cache" -n 40 --temp 0 -no-cnv \
  -j '{"type":"object","properties":{"tool":{"enum":["search","calculator"]},"n":{"type":"integer"}},"required":["tool","n"]}'
```

```text
The KV cache{ "tool": "search", "n": 17941330050} [end of text]
```

Our model knows nothing about tools, yet the output is valid JSON, `tool` is one of the two allowed values, and `n` is an integer. Then generation stopped by itself, because the grammar allowed nothing after the closing brace. (The prompt is echoed in front; with the server you only get the generated part.)

You can also write GBNF by hand. `grammars/` in the repo has examples (`json.gbnf`, `list.gbnf`, `chess.gbnf`, `arithmetic.gbnf`, ...):

```text
root ::= "yes" | "no"
```

The schema or grammar only limits the output; it is not shown to the model. With a real model, describe the format in the prompt as well, or the model may fight the grammar and produce valid but poor answers.

## Settings that work

| Job | Settings |
|---|---|
| Extraction, classification, tests | `--temp 0`, plus a JSON schema |
| Chat, general use | The defaults, or the model card's recommended values |
| Creative writing | `--temp 1.0` and `--min-p 0.05` to 0.1, with `--top-k 0 --top-p 1` so min-p does the cutting |
| Code | `--temp 0.2` or lower |
| Repetition loops | `--repeat-penalty 1.05` to 1.1, or the DRY sampler (`--dry-multiplier 0.8`) |

Model cards often give recommended values; they beat these general rules. The server takes the same settings per request (`temperature`, `top_k`, `top_p`, `min_p`, `seed`, `samplers`, ...).

:::check Your extraction job sometimes returns invalid JSON at temperature 0.7. What two changes fix it for good?
Set temperature to 0 for repeatable output, and pass a JSON schema (`-j` or `response_format`), so invalid JSON cannot be produced at all.
:::

:::check Why can top-p 0.95 keep 2 tokens for one step and 200 for the next?
It keeps the smallest set of top tokens whose probabilities add up to 0.95. When the model is sure, one or two tokens cover that. When it is unsure, the probability is spread out and many tokens are needed.
:::
