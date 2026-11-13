---
title: Voice, LLMOps and inference: source notes
summary: Every page we read for the voice, fine-tuning, serving and edge lessons, with reading paths and what we could not verify.
time: 40 min
---


Date of research: 2026-11-03. Track C (C2, C3, C5) was read again on 2026-11-12, this time from the projects' GitHub sources. Sources are official docs, original papers and standards. "Read" means the page was fetched and summarized by the fetch tool. Items marked UNVERIFIED were not confirmed in a fetched source.

Note on method: pages were read through a fetch tool that returns summaries. Quotes are short. Check the page before quoting it in a lesson.

---

# Track A: Voice AI

## A1. The cascaded voice pipeline (speech-to-text, LLM, text-to-speech)

**Plain explanation.** A voice agent hears audio, turns it into text, asks a language model for a reply, and turns the reply into audio. These three steps are called speech-to-text (STT), the LLM, and text-to-speech (TTS). Each step can start before the one before it finishes, by streaming small pieces. You can swap each step for a different provider. Vapi describes the same three parts and lets you pick each one separately.

**Official URLs read.**
- https://docs.livekit.io/agents/ (pipeline named as core; no internals described)
- https://docs.vapi.ai/quickstart/introduction (three parts, provider list)

**Dig deeper (beginner to advanced).**
1. Read the LiveKit Agents overview and list the three stages.
2. Read the Vapi intro and note which providers fill each stage.
3. Read the LiveKit Agents "build" section on models (page not fetched, see gaps).
4. Compare cascaded with speech-to-speech models (not sourced here).

**Try it yourself (laptop, no GPU).** Write a script that takes a recorded .wav, sends it to any hosted STT, sends the text to any hosted LLM, and sends the answer to a hosted TTS. Print the time each step took. Needs API keys, no GPU.

## A2. Latency budget and where the time goes

**Plain explanation.** After you stop talking, the agent must detect the end of your turn, finish transcribing, wait for the first LLM token, and wait for the first audio chunk. The delays add up. A latency budget is a plan for how many milliseconds each step may use. Measure each step on its own to see which one is the problem.

Numbers that a source states:
- Vapi docs claim "Sub-600ms response times with natural turn-taking". This is a product claim, not a measurement method. (Read.)
- Search results quoting an arXiv paper (https://arxiv.org/pdf/2603.29893) say endpointing plus ASR takes about 150 to 300 ms, TTS about 100 to 200 ms to first audio, and an LLM time-to-first-token target of about 500 ms. UNVERIFIED: I saw this only in a search summary, not the paper itself, and the summary noted near-duplicate text across two papers.
- Deepgram's observability page splits latency into STT, time to first LLM token, TTS and total (https://developers.deepgram.com/docs/voice-agent-observability). UNVERIFIED: seen in search snippet only.
- LiveKit's docs fetched here state no latency figures.

**Official URLs read.** https://docs.vapi.ai/quickstart/introduction ; https://docs.livekit.io/agents/build/turns/ (settings, not latency totals).

**Dig deeper.**
1. Define "time to first token" and "time to first audio byte".
2. Read the Deepgram observability page and see how it splits the total.
3. Find a paper that measures a full pipeline and check its method.
4. Learn why streaming each stage lowers the total.

**Try it yourself (laptop).** Extend A1 with timers around each stage. Run 20 calls. Report median and worst case per stage in a table.

## A3. Turn detection and interruptions

**Plain explanation.** Turn detection decides when the user has finished speaking. Voice activity detection (VAD) separates speech from silence. Simple VAD waits for a pause. LiveKit's default adds a model that reads meaning and sound to predict the end of a turn. When the user talks over the agent, the agent stops and keeps only the part the user heard in its history.

Documented facts (LiveKit turns page, read):
- Modes: turn detector model (default), realtime model server-side detection, VAD only, STT endpointing, manual.
- Silero VAD is named as the bundled VAD.
- Interruption modes: `adaptive` (separates real interruptions from "mm-hmm") and `vad`.
- `false_interruption_timeout` is 2.0 s in Python. `transcript_timeout` default is 2.0 s.
- Endpointing delay has `min_delay` and `max_delay`; defaults not stated on the page.

**Official URL read.** https://docs.livekit.io/agents/build/turns/

**Dig deeper.**
1. Read the modes list and say which has the lowest latency (VAD only, per the page).
2. Read the interruptions section on false interruptions.
3. Read the turn-taking tuning page (linked, not fetched).
4. Read the turn detector model card (not located).

**Try it yourself (laptop).** Install Silero VAD (open source, runs on CPU). Feed it a recording with pauses. Print when it says speech started and stopped. Change the silence threshold and compare. UNVERIFIED: install steps were not read here; use the Silero repository README.

## A4. WebRTC basics

**Plain explanation.** WebRTC lets two devices send audio and video directly. First they must find a network path. ICE tries possible paths. STUN tells a device its public address. TURN relays traffic when a direct path fails. SDP is a text description of the media, such as codecs. You must provide your own signaling channel to swap this information.

**Official URL read.** https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Protocols

**Dig deeper.**
1. Read the MDN protocols page.
2. Read MDN "WebRTC connectivity" (not fetched).
3. Read the WebRTC spec at W3C (not fetched).
4. Look at LiveKit's reasons for using a media server (not sourced here).

**Try it yourself (laptop).** Open two browser tabs on a public WebRTC sample, and open `chrome://webrtc-internals` to see ICE candidates. UNVERIFIED: the sample URL and tool were not fetched.

## A5. SIP and telephony basics

**Plain explanation.** SIP is the signaling protocol that starts, changes and ends calls. A SIP trunk links your system to a phone provider. An inbound trunk takes calls in. An outbound trunk places calls out. In LiveKit, a dispatch rule decides which room each inbound caller joins.

Documented (read):
- RFC 3261 abstract: SIP is an application-layer signaling protocol for sessions. It relies on other protocols for media transport and session description.
- LiveKit: inbound trunks can be limited by IP or number. Outbound trunk settings can be stored or sent inline. Dispatch rules are tied to a trunk.

**Official URLs read.** https://docs.livekit.io/sip/ ; https://datatracker.ietf.org/doc/html/rfc3261 (abstract only; the page has 700,000 characters and only the first 100,000 were read).

**Dig deeper.**
1. Read the LiveKit SIP overview.
2. Read the RFC 3261 abstract and introduction.
3. Read LiveKit's inbound and outbound trunk setup pages (not fetched).
4. Read RFC 3550 for RTP, the media transport (not fetched).

**Try it yourself (laptop).** Run a free SIP softphone and a local test SIP server, and place a call between them. UNVERIFIED: no official softphone doc was read. A real phone number needs a paid provider.

## A6. LiveKit: Agents, SIP, Ingress, Egress

**Plain explanation.** LiveKit is a real-time media platform built on WebRTC. Agents is an open source (Apache 2.0) framework that puts a Python or Node.js program in a room as a participant. SIP connects phone calls into rooms. Ingress brings in non-WebRTC sources such as RTMP, WHIP, HLS files and SRT. Egress exports a room or tracks to MP4, HLS or RTMP.

Documented (read):
- Ingress has push (RTMP or WHIP, via `CreateIngress`) and pull (URL input) workflows.
- Egress sources: TemplateSource (room composite), WebSource, MediaSource. `StartEgress` replaces older per-type calls, which are deprecated. LiveKit Cloud includes egress. Self-hosting needs separate deployment.

**Official URLs read.** https://docs.livekit.io/agents/ ; https://docs.livekit.io/home/ingress/overview/ ; https://docs.livekit.io/home/egress/overview/ ; https://docs.livekit.io/sip/

**Dig deeper.**
1. Read the Agents overview.
2. Read the Ingress and Egress overviews.
3. Read the Agents session and tools pages (not fetched).
4. Read how to self-host LiveKit (not fetched).

**Try it yourself (laptop).** Self-host the LiveKit server in dev mode and run a starter agent, using the Agents quickstart. UNVERIFIED: quickstart not fetched. Needs provider API keys. No GPU.

## A7. Hosted alternative: Vapi

**Plain explanation.** Vapi is a hosted platform for voice agents that make and receive phone calls. It runs the infrastructure. You choose the transcriber, model and voice. Squads combine several assistants. Presets bundle common choices.

**Official URL read.** https://docs.vapi.ai/quickstart/introduction (the "how Vapi works" page returned 404).

**Dig deeper.**
1. Read the intro and list supported providers.
2. Read the Assistants page (not fetched).
3. Read the Squads page (not fetched).
4. Compare cost and control against LiveKit (no source read; do not claim).

**Try it yourself (laptop).** Create a free-tier assistant in the dashboard and call it from the web widget. UNVERIFIED: free-tier terms not checked.

## Proposed lessons: Voice AI

1. **How a voice agent works.** Three stages and the data that flows between them. Build the timer script from A1.
   Sources: LiveKit Agents overview, Vapi intro.
2. **Where the milliseconds go.** Measure each stage, then set a budget. Discuss what published numbers do and do not show.
   Sources: Vapi intro, Deepgram observability page (verify), measurement script.
3. **Knowing when to speak.** VAD, turn detectors, endpointing delay and interruptions. Run Silero VAD on a recording.
   Sources: LiveKit turns page, Silero repository (verify).
4. **WebRTC in plain words.** ICE, STUN, TURN and SDP with a diagram.
   Sources: MDN WebRTC protocols.
5. **Phones: SIP and trunks.** Inbound, outbound, dispatch rules. Diagram a call into a room.
   Sources: RFC 3261, LiveKit SIP overview.
6. **LiveKit building blocks.** Agents, Ingress, Egress, SIP on one map. Record a call with Egress.
   Sources: LiveKit overview pages.
7. **Hosted or self-built.** Build the same agent on Vapi and on LiveKit. Compare setup effort and control.
   Sources: Vapi intro, LiveKit docs.

---

# Track B: LLMOps and fine-tuning

## B1. Fine-tune, prompt, or RAG

**Plain explanation.** Start with prompting and build a small test set. Use RAG when the model lacks facts, such as private or recent data. Use fine-tuning when the model has the facts but behaves inconsistently, for example wrong format or tone. The two can be combined. Exhaust the simpler options first.

OpenAI's guide gives starting sizes: an eval set of 20 or more Q and A pairs, and about 50 high-quality examples for fine-tuning. These are one vendor's guidance.

**Official URL read.** https://developers.openai.com/api/docs/guides/optimizing-llm-accuracy

**Dig deeper.**
1. Read the OpenAI guide.
2. Read Hugging Face TRL "dataset formats" (linked, not fetched).
3. Read the RAG paper by Lewis et al. 2020 (not fetched).
4. Search for provider-neutral guidance (none verified).

**Try it yourself (laptop).** Take 20 questions about one document. Answer them with a plain prompt, then with the document pasted in. Score both by hand. Needs an API key or a local model, no GPU needed for a small local model.

## B2. SFT (supervised fine-tuning)

**Plain explanation.** SFT trains a model on input and output pairs so it learns to produce the output. The loss is the next-token cross-entropy. TRL accepts plain text, conversation, and prompt and completion formats. You can train on the assistant part only.

**Official URL read.** https://huggingface.co/docs/trl/sft_trainer

**Dig deeper.**
1. Read the TRL SFT quick start (a 0.6B model example is shown).
2. Read the dataset formats section.
3. Read about `assistant_only_loss` and packing.
4. Read the TRL taxonomy at https://huggingface.co/docs/trl/index.

**Try it yourself.** Run the TRL quick start with the small Qwen 0.6B model and the Capybara dataset. A GPU is the practical choice. CPU may be very slow. UNVERIFIED: laptop CPU runtime was not documented.

## B3. LoRA, QLoRA, PEFT

**Plain explanation.** PEFT means training a small number of extra parameters instead of the whole model. LoRA freezes the large weight matrices and trains two small matrices whose product approximates the change. After training you can merge them into the base weights so inference adds no delay. QLoRA does LoRA on a model whose weights are stored in 4-bit form to save memory.

Documented numbers:
- LoRA paper abstract: compared with GPT-3 175B fine-tuned with Adam, trainable parameters drop by 10,000 times and GPU memory by 3 times.
- QLoRA paper abstract: fine-tune a 65B model on one 48 GB GPU with 16-bit quality. Guanaco reaches 99.3% of ChatGPT on the Vicuna benchmark after 24 hours on one GPU.
- PEFT LoRA guide: `r` is rank, scale is `lora_alpha / r` by default, `merge_and_unload()` returns a standalone model.
- TRL: `quantization_config` combined with `peft_config` gives QLoRA training.

**Official URLs read.** https://huggingface.co/docs/peft/index ; https://huggingface.co/docs/peft/main/en/conceptual_guides/lora ; https://arxiv.org/abs/2106.09685 ; https://arxiv.org/abs/2305.14314

**Dig deeper.**
1. Read the PEFT index.
2. Read the LoRA concept guide.
3. Read the LoRA abstract.
4. Read the QLoRA abstract, then the paper.

**Try it yourself.** Apply `LoraConfig` to a small model, print the trainable parameter count (PEFT provides a helper for this; UNVERIFIED in the pages read). Loading a small model works on CPU. Training is slow without a GPU. QLoRA needs a GPU (4-bit loading library support on CPU is UNVERIFIED).

## B4. DPO (preference tuning)

**Plain explanation.** DPO trains on pairs of answers to the same prompt, one preferred and one rejected. It widens the gap between how likely the model finds each, relative to a reference model. It needs no separate reward model and no sampling during training. The data has `prompt`, `chosen` and `rejected` fields.

Documented: the DPO abstract says it is simpler than RLHF and matches or beats PPO-based RLHF on sentiment control, summarization and single-turn dialogue. TRL's default `beta` is 0.1 and default learning rate is 1e-6 (1e-5 suggested for adapters).

**Official URLs read.** https://huggingface.co/docs/trl/dpo_trainer ; https://arxiv.org/abs/2305.18290

**Dig deeper.**
1. Read the TRL DPO overview and dataset format.
2. Read the DPO abstract.
3. Read the loss formula section of the TRL page.
4. Read the loss variants table (IPO, KTO family).

**Try it yourself.** Build 20 chosen/rejected pairs by hand. Format them as in the TRL page. Run `DPOTrainer` with a 0.6B model. GPU advised.

## B5. Dataset management

**Plain explanation.** Training data needs a fixed format, versions, and a hold-out set. TRL documents the accepted formats. OpenAI's guide says to keep a hold-out set to spot overfitting. Langfuse also offers datasets for test sets.

**Official URLs read.** https://huggingface.co/docs/trl/sft_trainer ; https://developers.openai.com/api/docs/guides/optimizing-llm-accuracy ; https://langfuse.com/docs

**Dig deeper.**
1. Read the TRL dataset formats.
2. Read the Hugging Face `datasets` docs (not fetched).
3. Read about dataset versioning in MLflow (not fetched).
4. Read about data licensing (not sourced).

**Try it yourself (laptop).** Make a JSONL file of 50 examples in conversation format. Split it 80/20 with a fixed seed. Commit it to version control.

## B6. Experiment tracking and model registry (MLflow)

**Plain explanation.** MLflow Tracking records runs. A run stores parameters, metrics, and output files (artifacts). Experiments group runs. The Model Registry stores model versions. An alias such as `champion` points to one version, and you can load it by name.

**Official URLs read.** https://mlflow.org/docs/latest/ml/tracking/ ; https://mlflow.org/docs/latest/ml/model-registry/

**Dig deeper.**
1. Read the tracking page.
2. Read the registry page on versions and aliases.
3. Read MLflow's LLM evaluation docs (not fetched).
4. Read MLflow tracing docs (not fetched).

**Try it yourself (laptop, no GPU).** `pip install mlflow`, run `mlflow ui`, log two runs with different parameters, compare them in the UI. UNVERIFIED: install command taken from general knowledge, not a fetched page.

## B7. Evaluating RAG (hallucination, relevance, context scoring)

**Plain explanation.** RAGAS gives scores from 0 to 1. Faithfulness: split the answer into claims and count how many the retrieved context supports. Response relevancy: an LLM writes questions the answer would fit, and the score is how close they are to the real question. Context precision: do relevant chunks rank near the top. Context recall is listed but not defined in what I read.

**Official URLs read.**
- https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/
- https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/answer_relevance/
- https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/

**Dig deeper.**
1. Read the faithfulness page and its worked example (score 0.5).
2. Read response relevancy.
3. Read context precision.
4. Read the RAGAS context recall page (not fetched).
5. Read how Opik names hallucination and context recall metrics (see B8).

**Try it yourself.** Run the faithfulness example by hand with 3 claims. Then use RAGAS on 10 questions. The metrics call an LLM judge, so you need an API key or local judge model. No GPU for API use.

## B8. Observability tools (Langfuse, Opik)

**Plain explanation.** These tools record each LLM call and step as a trace. You can see inputs, outputs, cost and errors. They also run evaluations and manage test sets. Langfuse adds prompt versioning with labels. Both are open source and self-hostable.

**Official URLs read.** https://langfuse.com/docs ; https://www.comet.com/docs/opik/

**Dig deeper.**
1. Read the Langfuse overview.
2. Read the Opik overview.
3. Read each tool's self-hosting page (Langfuse: https://langfuse.com/llms-self-hosting.txt, not fetched).
4. Read about OpenTelemetry (Langfuse says it is built on it; not verified at source).

**Try it yourself.** Self-host one with Docker and send traces from a small script. Needs Docker, no GPU. UNVERIFIED: exact commands were not read.

## B9. Monitoring stack (Prometheus, Grafana, cAdvisor, Node Exporter)

**Plain explanation.** Prometheus pulls numeric metrics from targets over HTTP and stores them with labels. PromQL queries them. Alertmanager sends alerts. Node Exporter exposes host hardware and kernel metrics on port 9100. cAdvisor exposes per-container resource use. Grafana draws dashboards from these data sources.

**Official URLs read.** https://prometheus.io/docs/introduction/overview/ ; https://prometheus.io/docs/guides/node-exporter/ ; https://github.com/google/cadvisor ; https://grafana.com/docs/grafana/latest/fundamentals/

**Dig deeper.**
1. Read the Prometheus overview.
2. Follow the Node Exporter guide (it includes a scrape config).
3. Read the cAdvisor README.
4. Read the Grafana fundamentals page, then data source docs (not fetched).

**Try it yourself (laptop, no GPU).** Follow the Node Exporter guide: run `node_exporter`, add the `node` job at `localhost:9100`, and query `node_cpu_seconds_total` at `localhost:9090/graph`. Windows support for Node Exporter is UNVERIFIED (the guide says Linux host); use WSL or a container.

## B10. Staging and deploy pipelines

**Plain explanation.** A staged pipeline moves a model or prompt from test to production in steps, with checks at each step. MLflow aliases (such as `champion`) can mark which version production uses. Langfuse labels deploy prompts to environments without a code change. A full CI/CD recipe was not found in the sources read.

**Official URLs read.** https://mlflow.org/docs/latest/ml/model-registry/ ; https://langfuse.com/docs

**Dig deeper.**
1. Read MLflow aliases.
2. Read Langfuse prompt labels.
3. Read GitHub Actions docs (not fetched).
4. Look for an official guide on evaluation gates (none verified).

**Try it yourself (laptop).** Register two versions of a tiny model in MLflow. Point an alias at version 1, then move it to version 2. Load by alias both times.

## Proposed lessons: LLMOps and fine-tuning

1. **Prompt, RAG, or fine-tune?** A decision flow from symptoms to fix. Test on 20 questions.
   Sources: OpenAI accuracy guide.
2. **Training data that works.** Formats, splits, hold-out sets. Build a 50-example file.
   Sources: TRL SFT and DPO pages.
3. **SFT with a small model.** Run the TRL quick start. Read the logged metrics.
   Sources: TRL SFT page. (GPU recommended.)
4. **LoRA and QLoRA without the math.** Rank, alpha, merging. Count trainable parameters.
   Sources: PEFT docs, LoRA and QLoRA abstracts.
5. **Teaching preferences with DPO.** Chosen and rejected pairs, beta, reference model.
   Sources: TRL DPO page, DPO paper.
6. **Tracking experiments and versions.** MLflow runs, registry, aliases.
   Sources: MLflow tracking and registry pages.
7. **Scoring a RAG system.** Faithfulness, relevancy, context precision by hand, then with RAGAS.
   Sources: RAGAS metric pages.
8. **Seeing inside your app.** Traces in Langfuse or Opik. Compare the two.
   Sources: Langfuse docs, Opik docs.
9. **Watching the servers.** Prometheus, Node Exporter, cAdvisor, Grafana on one laptop.
   Sources: Prometheus, cAdvisor, Grafana docs.
10. **Safe releases.** Staging, aliases, prompt labels, rollback.
    Sources: MLflow registry, Langfuse docs.

---

# Track C: Inference and edge

## C1. How LLM serving works (prefill, decode, KV cache, batching)

**Plain explanation.** Prefill reads the whole prompt at once. This is a large parallel job and keeps the GPU busy. Decode then writes one token at a time. It is memory-bound, which means speed depends on how fast data moves from memory. To avoid recomputing, the server stores the key and value of every earlier token in the KV cache. This cache grows with batch size and length. Batching serves many requests together so the model weights are loaded once for all. In-flight batching lets finished requests leave and new ones join.

Documented numbers (NVIDIA blog, read): Llama 2 7B, 4,096 tokens, batch size 1 needs a KV cache of about 2 GB. Weights are about 14 GB in FP16.

**Official URLs read.** https://developer.nvidia.com/blog/mastering-llm-techniques-inference-optimization/ ; https://arxiv.org/abs/2309.06180

**Dig deeper.**
1. Read the NVIDIA blog.
2. Read the vLLM paper abstract.
3. Read the vLLM docs overview.
4. Read the full vLLM paper.

**Try it yourself (laptop).** Compute the KV cache size for a small model by hand, using the blog's example as a check. Then compare with the reported memory use in llama.cpp (C4).

## C2. vLLM

**Plain explanation.** vLLM is an open source serving library, begun in UC Berkeley's Sky Computing Lab. PagedAttention keeps the KV cache in fixed-size blocks tracked by a block table. Its scheduler is token-budget-based (`max_num_batched_tokens`), with no separate prefill and decode phases. Chunked prefill is on by default in V1 "whenever possible", and decode requests are scheduled first. Preempted requests are recomputed, not swapped. Automatic prefix caching hashes each full block (its tokens plus its prefix) and evicts least-recently-used blocks. `vllm serve MODEL` starts an OpenAI-compatible server on port 8000. The README lists NVIDIA, AMD and Intel GPUs, several CPUs and plugin hardware.

**Read on 2026-11-12, from the GitHub sources** (raw.githubusercontent.com works from our container, docs.vllm.ai does not): README.md; docs/design/prefix_caching.md; docs/design/arch_overview.md; docs/design/paged_attention.md (marked historical in its own header); docs/features/automatic_prefix_caching.md; docs/configuration/optimization.md (chunked prefill, preemption); docs/getting_started/quickstart.md (`vllm serve`); docs/serving/online_serving/README.md; docs/benchmarking/cli.md (TTFT, ITL, TPOT definitions); vllm/config/cache.py (`enable_prefix_caching: bool = True`). Paper abstract (2 to 4 times throughput claim) read in the first pass only: https://arxiv.org/abs/2309.06180

**Dig deeper.**
1. Read the prefix caching design page, including its worked example.
2. Read the architecture overview, scheduler section.
3. Read the optimization guide, chunked prefill and preemption.
4. Read the paper fully.

**Try it yourself.** Run `vllm serve` with a small model and send a request. UNVERIFIED: install steps for your hardware, the default block size (the source we read leaves it to the setup), CPU-only behavior.

## C3. SGLang, TensorRT-LLM, NVIDIA Dynamo

**Plain explanation.** SGLang is hosted by LMSYS. RadixAttention keeps cached prompt prefixes in a radix tree whose nodes hold KV cache for runs of tokens. Eviction is LRU by default (`lfu`, `slru`, `priority` exist). `--schedule-policy` offers `lpm` (longest prefix match, per a source comment), `fcfs` (default) and others. The model gateway has a `cache_aware` policy. Structured output takes JSON schema, regex or EBNF, with XGrammar as the default backend. A Python frontend language exists. Its quickstart uses `sglang serve`. TensorRT-LLM is NVIDIA's library. As of the docs read, the TensorRT engine backend and `trtllm-build` are removed (release notes, 1.2 section; migration guide). PyTorch is the only backend and `trtllm-serve MODEL` loads a Hugging Face checkpoint directly. In-flight batching is its continuous batching. FP8 (H100 and later) and FP4 (B200) are documented. Speculative decoding: "A lightweight drafting mechanism proposes candidate tokens, and the target model verifies them in a single forward pass." NVIDIA Dynamo has its own notes: see [Dynamo source notes](lesson:research/dynamo).

**Read on 2026-11-12, from the GitHub sources.** SGLang: README.md; docs/docs/get-started/quickstart.mdx; advanced_features/hicache_design.mdx (RadixAttention description), radix_eviction_policy.mdx, server_arguments.mdx, structured_outputs.mdx, sgl_model_gateway.mdx, speculative_decoding.mdx; references/frontend/frontend_tutorial.mdx; python/sglang/srt/managers/schedule_policy.py (LPM comment). TensorRT-LLM: README.md (release 1.4.0rc4); docs/source/overview.md, quick-start-guide.md, supported-hardware.md, release-notes.md, legacy/tensorrt-backend-removal.md, features/paged-attention-ifb-scheduler.md, features/quantization.md, features/speculative-decoding.md, commands/trtllm-serve/trtllm-serve.rst. Dynamo: see the separate Dynamo notes.

**Dig deeper.**
1. Read the TensorRT-LLM backend removal migration guide.
2. Read SGLang's `schedule_policy.py` for how `lpm` sorts the queue.
3. Read the TensorRT-LLM kvcache.md feature page (downloaded, only skimmed).
4. Read the SGLang paper (not reachable from our container).

**Try it yourself.** Reading and diagramming on a laptop. SGLang and vLLM list non-NVIDIA hardware. TensorRT-LLM lists NVIDIA GPUs only.

## C4. llama.cpp, GGUF, Q4_K_M

**Plain explanation.** llama.cpp is a C/C++ engine built on ggml. It runs on Apple silicon, x86 CPUs, NVIDIA, AMD and others, and can split a model between CPU and GPU. GGUF is a binary file format that holds both the tensors and standard metadata. Quantization stores weights with fewer bits. Hugging Face's table says Q4_K is 4-bit, uses super-blocks of 8 blocks of 32 weights, and costs 4.5 bits per weight. In llama.cpp's quantize README test, Llama-3.1-8B was 14.96 GiB in F16 and 4.58 GiB in Q4_K_M. The "K" is tied to the "k-quants" family. What the "M" means is not defined in the sources read.

**Official URLs read.** https://github.com/ggml-org/llama.cpp ; https://huggingface.co/docs/hub/gguf ; https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md

**Dig deeper.**
1. Read the llama.cpp README.
2. Read the Hugging Face GGUF page and its quantization table.
3. Read the quantize README size table.
4. Read the k-quants pull request (https://github.com/ggerganov/llama.cpp/pull/1684, linked from the table, not fetched) for the meaning of S, M, L.

**Try it yourself (laptop, no GPU needed).** Download a small GGUF model, run it with `llama-server`, and call the OpenAI-style API. Compare a Q4 file with a Q8 file for size and speed using C5. UNVERIFIED: download steps not read.

## C5. Benchmarking (tokens per second, time to first token)

**Plain explanation.** Two numbers matter. Time to first token (TTFT) shows how long the user waits before output starts. Tokens per second shows how fast the rest comes. llama-bench reports prompt processing (pp) and text generation (tg) as average tokens per second, with a standard deviation over repeated runs (default 5). It excludes tokenization and sampling time. vLLM's benchmarking page (docs/benchmarking/cli.md, read 2026-11-12) defines them: TTFT is the time from sending a request to receiving its first streamed output; ITL records the time between consecutive streamed outputs; TPOT is (end-to-end latency minus TTFT) divided by (output tokens minus 1), calculated once per request. The page warns that metric names are not standardized across tools, and recommends GuideLLM for production benchmarking. AIPerf was not looked up.

**Official URLs read.** https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/README.md ; https://github.com/vllm-project/vllm/blob/main/docs/benchmarking/cli.md

**Dig deeper.**
1. Read the llama-bench README.
2. Run the example command from it.
3. Read the `vllm bench serve` page.
4. Read about goodput (mentioned as an option; not defined).

**Try it yourself (laptop).** Run `./llama-bench -n 0 -p 1024 -b 128,256,512,1024` (from the README) on two quantizations. Plot t/s by batch size.

## C6. ONNX and ONNX Runtime

**Plain explanation.** ONNX is a model file format. ONNX Runtime is a cross-platform engine that loads models exported from PyTorch or TensorFlow. It applies graph optimizations and splits the graph across available hardware. Execution providers are the hardware-specific accelerators that handle each part.

**Official URL read.** https://onnxruntime.ai/docs/

**Dig deeper.**
1. Read the ONNX Runtime docs home.
2. Read the list of execution providers (not fetched).
3. Read ONNX Runtime generative AI docs (not fetched).
4. Read the ONNX spec at onnx.ai (not fetched).

**Try it yourself (laptop).** Export a small PyTorch model to ONNX and run it with ONNX Runtime on CPU. UNVERIFIED: export API not read here.

## Proposed lessons: Inference and edge

Built as eight lessons: 1 what happens when you press enter, 2 batching and GPU memory, 3 vLLM in depth, 4 SGLang in depth, 5 TensorRT-LLM in depth, 6 choosing an engine (sets up the Dynamo track), 7 laptop GGUF quantization, 8 benchmark honestly. ONNX (C6) is not yet a lesson.

---

# What I could not verify

- Typical per-stage voice latency numbers from a first-hand official source. Only Vapi's "sub-600ms" claim was read. The 150 to 300 ms (STT), 100 to 200 ms (TTS) and 500 ms (LLM) figures came from a search summary of an arXiv paper, not the paper.
- LiveKit's own latency guidance, metrics definitions, and default endpointing delays. The pages read gave none.
- Vapi "how it works" page (404). Vapi turn-taking and interruption settings.
- LiveKit SIP trunk setup details, Silero VAD install steps, WebRTC demo tooling, any softphone guide.
- The meaning of "M" in Q4_K_M. Hugging Face and the quantize README do not define it. The k-quants PR is the likely source but was not read.
- Output throughput as a defined term. TTFT, ITL and TPOT are now sourced (vLLM benchmarking page). AIPerf was not looked up.
- NVIDIA Dynamo: read from the GitHub docs tree (the parts the lessons use, not every page) on 2026-11-12. See the Dynamo notes for details and gaps.
- Not run: vLLM, SGLang, TensorRT-LLM. No speed claim was tested. The vLLM paper abstract could not be re-read on 2026-11-12 (arxiv.org is blocked from our container). The default vLLM block size, the Triton Inference Server integration for TensorRT-LLM, the SGLang paper, and exactly which older TensorRT-LLM release dropped each engine-build feature were not checked. The SGLang docs page does not define `lpm`; the meaning comes from a source-code comment. The docs sites (docs.vllm.ai, docs.sglang.io, nvidia.github.io) time out from our container, so we read the same pages as source files on GitHub.
- RAGAS context recall definition. RAGAS hallucination metric (not located; Opik lists "hallucination" as its own metric).
- Whether Node Exporter runs on Windows, whether QLoRA or PEFT training runs on laptop CPU, and the PEFT helper for printing trainable parameters.
- MLflow LLM evaluation and tracing features. Langfuse and Opik self-hosting steps. Any official guide on CI/CD gates for LLM apps.
- Original RAG paper, WebRTC W3C spec, ONNX spec, SGLang paper, Dynamo paper: not fetched.
- Fetch tool returns model-made summaries, not raw pages, so wording in this file may drift from the source.
