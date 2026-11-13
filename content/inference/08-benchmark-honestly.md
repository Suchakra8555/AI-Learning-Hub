---
title: Benchmark honestly
summary: Two numbers matter, how long until the first word and how fast the rest arrives. Measure them the same way every time.
time: 15 min
---

"Which server is faster?" is not a question until you say faster at what, with which model, prompt, and load.

## Two numbers

- **Time to first token (TTFT).** How long the user waits before any output appears. Mostly prefill.
- **Tokens per second.** How fast the rest of the answer streams. Mostly decode.

llama.cpp's `llama-bench` reports **pp** (prompt processing) and **tg** (text generation) as average tokens per second, with a standard deviation over repeated runs, five by default. It leaves tokenization and sampling out of the timing ([README](https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/README.md)). Its example command from the docs:

```bash
./llama-bench -n 0 -p 1024 -b 128,256,512,1024
```

vLLM's `vllm bench serve` reports TTFT, TPOT and ITL. The vLLM benchmarking page defines them ([docs](https://github.com/vllm-project/vllm/blob/main/docs/benchmarking/cli.md), read 2026-11-12):

- **TTFT** is "the time from sending a request to receiving its first streamed output".
- **ITL** (inter-token latency) "records the time between consecutive streamed outputs".
- **TPOT** (time per output token) is "calculated once per request, excluding the first token": end-to-end latency minus TTFT, divided by the number of output tokens minus 1.

<figure>
<svg viewBox="0 0 600 258" role="img" aria-labelledby="t-lat d-lat">
  <title id="t-lat">TTFT and inter-token latency on one request</title>
  <desc id="d-lat">A timeline for one request. A bracket from the moment the request is sent to the first token is labelled TTFT. Short brackets between later tokens are labelled ITL. A long bracket across the whole timeline is end-to-end latency.</desc>
  <defs><marker id="ah-lat" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <path class="arrow" d="M20 120 H590"/>
  <text x="40" y="34" font-size="13" text-anchor="middle">send</text>
  <path class="arrow" d="M40 52 V120"/>
  <circle class="box hot" cx="230" cy="120" r="7"/>
  <text x="230" y="150" font-size="12" text-anchor="middle" class="small">tok 1</text>
  <path class="arrow" stroke-dasharray="3 5" d="M230 112 V100"/>
  <circle class="box hot" cx="280" cy="120" r="7"/>
  <text x="280" y="150" font-size="12" text-anchor="middle" class="small">tok 2</text>
  <path class="arrow" stroke-dasharray="3 5" d="M280 112 V100"/>
  <circle class="box hot" cx="330" cy="120" r="7"/>
  <text x="330" y="150" font-size="12" text-anchor="middle" class="small">tok 3</text>
  <path class="arrow" stroke-dasharray="3 5" d="M330 112 V100"/>
  <circle class="box hot" cx="380" cy="120" r="7"/>
  <text x="380" y="150" font-size="12" text-anchor="middle" class="small">tok 4</text>
  <path class="arrow" stroke-dasharray="3 5" d="M380 112 V100"/>
  <circle class="box hot" cx="430" cy="120" r="7"/>
  <text x="430" y="150" font-size="12" text-anchor="middle" class="small">tok 5</text>
  <path class="arrow" stroke-dasharray="3 5" d="M430 112 V100"/>
  <circle class="box hot" cx="480" cy="120" r="7"/>
  <text x="480" y="150" font-size="12" text-anchor="middle" class="small">tok 6</text>
  <path class="arrow" stroke-dasharray="3 5" d="M480 112 V100"/>
  <path class="arrow" d="M44 84 H226" marker-end="url(#ah-lat)"/>
  <path class="arrow" d="M226 84 H44" marker-end="url(#ah-lat)"/>
  <text x="135" y="72" font-size="14" text-anchor="middle" class="small">TTFT</text>
  <text x="135" y="104" font-size="12" text-anchor="middle" class="small">wait + prefill</text>
  <path class="arrow" d="M236 84 H274" marker-end="url(#ah-lat)"/>
  <path class="arrow" d="M274 84 H236" marker-end="url(#ah-lat)"/>
  <path class="arrow" d="M286 84 H324" marker-end="url(#ah-lat)"/>
  <path class="arrow" d="M324 84 H286" marker-end="url(#ah-lat)"/>
  <text x="255" y="66" font-size="14" text-anchor="middle" class="small">ITL</text>
  <text x="330" y="66" font-size="12" text-anchor="start" class="small">gap between two tokens</text>
  <path class="arrow" d="M44 190 H476" marker-end="url(#ah-lat)"/>
  <path class="arrow" d="M476 190 H44" marker-end="url(#ah-lat)"/>
  <text x="260" y="182" font-size="14" text-anchor="middle" class="small">end-to-end latency</text>
  <text x="10" y="222" font-size="13" text-anchor="start" class="small">TTFT: request sent until the first token arrives.</text>
  <text x="10" y="242" font-size="13" text-anchor="start" class="small">ITL: time between consecutive tokens.</text>
</svg>
<figcaption>One request, one clock. The first gap is long because of waiting and prefill. The later gaps are short and steady.</figcaption>
</figure>

The same page warns that "metric terminology is not standardized across benchmarking tools", so compare measurement points and formulas, not names alone. It also notes that with speculative decoding one streamed output can hold several tokens, which changes what ITL means. The page recommends GuideLLM for benchmarking production servers. We did not try it, and did not check whether NVIDIA's AIPerf tool exists in the docs.

## Rules for a fair test

1. **Same model, same quantization, same prompts** on every setup.
2. **Warm up first.** Throw away the first run.
3. **Repeat and report spread.** A mean with no spread hides noise. Use the median and the worst case, as in the [voice timer](lesson:voice/where-the-milliseconds-go).
4. **Test with realistic load.** One request at a time says nothing about 50 at once.
5. **Write down the hardware and versions.** A number without them cannot be reproduced.
6. **Treat vendor numbers as claims.** Dynamo's README cites a 2x faster time to first token. That is one benchmark by the project, not your workload.

:::try
Run the same `llama-bench` command on a Q4 file and a Q8 file of the same model. Compare size, pp and tg. Which one would you ship, and what would you check before you did?
:::

:::check Your server shows great average tokens per second, but users complain it feels slow. Which number do you check?
Time to first token and the worst case. Users feel the wait before output starts and the slow requests, which an average can hide.
:::

You now have the map from prompt to hardware. For the whole picture of shipping, see [going to production](lesson:rag/going-to-production).
