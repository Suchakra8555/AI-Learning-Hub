---
title: Plain-words glossary
summary: Every hard word in the course, said simply. If a word is missing, add it.
---

**Agent**: A language model inside a harness, so it can take actions and see the results, not only write text. See [what a harness is](lesson:harness/what-is-a-harness).
**Append-only**: A record you only ever add to at the end. You never edit or delete old lines. Good for logs.
**Approval**: A human saying "yes, do that" before a risky action runs.
**BM25**: A well-known way to rank text by matching words. Rare words count more, and long texts do not win just for being long. See [retrieval](lesson:rag/retrieval-that-works).
**Bundle**: In DeepSeek Harness, a group of plugins and their settings that ship together.
**Cache**: A saved answer, so the same question next time costs nothing. Clear it when the data changes.
**Chunk**: One piece of a document that you store and search on its own. See [chunking](lesson:rag/chunking).
**Citation**: A pointer in an answer to the source it came from, such as [1].
**Compaction**: Replacing the old part of a long conversation with a short summary to save room.
**Context window**: The most text a model can read in one request.
**Cordis**: The open-source plugin framework that DeepSeek Harness is built on.
**Cosine similarity**: A score for how alike two lists of numbers are, by the direction they point. 1 is the same, near 0 is unrelated.
**Embedding**: A list of numbers that stands for the meaning of a piece of text. See [embeddings](lesson:rag/embeddings-and-vectors).
**Eval set**: A list of questions with known right answers, run after every change to check quality. See [measure quality](lesson:rag/measure-quality).
**Garbage in, garbage out**: If the text going in is bad, the answers coming out are bad.
**Guardrail**: A rule or check that keeps a system inside safe limits.
**Hallucination**: When a model states something that is not true as if it were. A plain word for it is "making things up".
**Harness**: Everything around a model that lets it act safely: the loop, tools, permissions, memory, and log. See [what a harness is](lesson:harness/what-is-a-harness).
**Hash**: A short fingerprint of some text. If the text changes, the hash changes. Used to spot changed documents.
**Hook**: A named moment in a program where your own code can step in, such as "before a tool runs".
**Hybrid search**: Running keyword search and vector search together and merging the results.
**Index**: Where chunks are stored so they can be found fast.
**Injection (prompt injection)**: Text the model reads that contains instructions, which the model then follows. See [safety](lesson:rag/fast-cheap-safe).
**JSON**: A plain text way to write structured data, like `{"name": "tent"}`.
**JSONL**: A file with one JSON object on each line. Handy for logs.
**Keyword search**: Finding text by matching the words in it.
**Language model**: A program that predicts text. Give it text, it gives text back.
**Log**: A record of what happened, in order.
**Metadata**: Information about the text, such as its file name, date, or who may see it.
**MRR**: Mean reciprocal rank. One score for how high the right chunk ranks. 1.0 means always first.
**OCR**: Reading text from a picture, such as a scanned page.
**Overlap**: Repeating a little text between neighboring chunks so an idea cut at the edge appears whole in one.
**Permission**: A rule saying whether an action is allowed, needs a yes, or is blocked.
**Plugin**: A piece of code that adds a capability to a larger program and can be loaded or removed.
**POC**: Proof of concept. A quick build that shows an idea can work.
**Profile**: In DeepSeek Harness, a named recipe of which plugins to run.
**Prompt**: The text sent to a model. In RAG it holds the instructions, the retrieved chunks, and the question.
**RAG**: Retrieval-augmented generation. Look up the right pieces of your own documents and give them to the model before it answers. See [what RAG is](lesson:rag/what-is-rag).
**Rank**: Position in a sorted list. Rank 1 is the best match.
**Reranker**: A slower, sharper model that reorders a short list of search results by reading each one with the question.
**Retrieval**: Finding the pieces of text most likely to hold the answer.
**Sandbox**: A box that limits what a program can reach, even if it tries to reach further.
**Semantic search**: Finding text by meaning and not just matching words. Usually done with embeddings.
**Session**: One working run with an agent, from start to finish.
**Step**: One model request plus the tools it calls.
**Sub-agent**: A separate, smaller agent loop started by another agent for one job.
**Token**: A small piece of text, roughly three quarters of a word. Model prices count tokens.
**Tool**: A function a model can ask a harness to run.
**Turn**: One job from your point of view: from your message until the agent stops to wait for you. It may hold many steps.
**Vector**: A list of numbers. An embedding is a vector.
**Vector database**: A database built to find the stored vectors closest to a given one, quickly.
**Vector search**: Finding chunks whose embeddings are closest to the question's embedding.

**API**: A way for one program to ask another to do something, usually over the web.
**Alias (model registry)**: A movable name like "champion" that points at one model version.
**Cross-encoder**: A model that reads a question and one chunk together and scores how well they match. Used for reranking.
**Checkpointer**: Saves a snapshot of an agent's state after each step so it can pause or resume.
**Decode**: The phase where a model writes its answer one token at a time.
**DPO**: Direct preference optimization. Trains a model on pairs of a preferred and a rejected answer.
**Endpointing**: The delay between someone stopping speaking and the system deciding their turn is over.
**Few-shot prompting**: Putting a few input and output examples in the prompt to show the format.
**GGUF**: A single-file format for models that run in llama.cpp.
**Hold-out set**: Examples kept out of training, used to check the model did not just memorize.
**ICE, STUN, TURN**: WebRTC tools for finding a network path between two devices. TURN relays traffic when no direct path works.
**KV cache**: Saved keys and values for earlier tokens, so the model does not recompute them for each new token.
**LoRA**: Fine-tuning that freezes the model and trains small add-on matrices.
**Middleware**: Code that runs before and after each step of an agent loop.
**Prefill**: The phase where a model reads the whole prompt at once.
**QLoRA**: LoRA on a model whose weights are stored in 4 bits to save memory.
**Quantization**: Storing numbers with fewer bits so they take less space. Used for model weights and for stored vectors. See [vectors at scale](lesson:rag/vectors-at-scale).
**Reducer**: In LangGraph, the rule for merging a node's update into the state: replace or append.
**SFT**: Supervised fine-tuning. Training on pairs of input and wanted output.
**SIP**: The protocol that starts, changes, and ends phone calls over the internet.
**Thread**: One conversation's chain of saved states in LangGraph.
**Time to first token (TTFT)**: How long a user waits before any output appears.
**Trace**: A step-by-step record of one request: model calls, tool calls, inputs, outputs, time, cost.
**VAD**: Voice activity detection. A small model that tells speech from silence.
**WebRTC**: A way for browsers and apps to send audio and video directly between devices.
**ANN (approximate nearest neighbour)**: Vector search that returns almost the closest vectors, much faster than checking every one. See [vectors at scale](lesson:rag/vectors-at-scale).
**Answer relevance**: A check that the answer addresses the question that was asked. See [judging answers](lesson:rag/judging-answers).
**Asymmetric embedding**: An embedding model that encodes questions and documents in different modes. Tell it which one you are sending.
**ColBERT**: A search model that keeps one small vector per word and compares question words with chunk words one by one. Also called late interaction.
**Community (graph)**: A cluster of things in a knowledge graph that link to each other much more than to the rest. GraphRAG writes a summary per community.
**Context precision**: Of the chunks you retrieved, the share that were useful for the answer.
**Context recall**: Whether the retrieved chunks held everything needed to answer.
**Faithfulness**: A check that every claim in the answer is backed by the retrieved chunks. Also called groundedness. See [judging answers](lesson:rag/judging-answers).
**GraphRAG**: RAG over a graph of things and their relationships that a model extracted from your text. See [beyond chunks](lesson:rag/beyond-chunks).
**HNSW**: The most common approximate vector index. Each vector links to near neighbours, and search walks the links toward the question.
**HyDE**: Search with a model-written fake answer instead of the question, because it looks more like your documents.
**Late chunking**: Embed the whole document first, then cut the per-token output into chunk vectors, so each chunk vector saw the whole document.
**Layout analysis**: A vision model labels regions of a page (title, text, table, figure) so text comes out in the right order.
**LLM judge**: A language model asked to score another model's answer. Check it against your own labels before you trust it.
**Matryoshka embedding**: An embedding trained so its first few hundred numbers still work alone, letting you store shorter vectors.
**Min-max normalization**: Rescale a list of scores so the best is 1 and the worst is 0. Needed before you add scores from different sources.
**Multi-query**: Search with several rewordings of the question and merge the results.
**NDCG**: A ranking score that can credit several right results and give very relevant ones more points than slightly relevant ones.
**Parent and child chunks**: Search small child pieces for precision, then give the model the bigger parent section they came from.
**Precision@k**: Of the top k results, the share that were right.
**RAPTOR**: A tree of summaries over your chunks, built by grouping and summarizing again and again. Lets search match a detail or the big picture.
**Recall@k**: Of all the right results, the share that made it into the top k.
**RRF (reciprocal rank fusion)**: Merge ranked lists by position, not score. A result high on several lists rises to the top.
**Semantic chunking**: Cut text where the meaning of neighbouring sentences changes, measured with embeddings.
**Sentence window**: Search single sentences, then give the model each found sentence with its neighbours.
**SPLADE**: A model that picks which words, including related words not in the text, a chunk should match on, stored in a keyword-style index.
**Table structure recognition**: A model that finds rows, columns and merged cells inside a table image so it can be rebuilt as a real table.
**Weighted-sum fusion**: Merge keyword and vector search as w times one score plus (1 minus w) times the other. Normalize the scores first.
**µ-law (G.711)**: A phone codec that stores each audio sample in 1 byte, keeping more detail for quiet sounds than loud ones. See [phone audio](lesson:voice-prod/phone-audio-is-different).
**PCM16**: Raw audio where each sample is a signed 16-bit number, 2 bytes per sample.
**Sample rate**: How many times per second audio is measured. Phone calls use 8 kHz; WebRTC's Opus runs at 48 kHz.
**Frame (audio)**: A fixed slice of audio sent as one unit, such as 20 ms.
**API gateway**: The one public entry point that routes each request path to the service that owns it.
**Media bridge**: A service that takes a carrier's WebSocket audio and joins a LiveKit room as an ordinary participant.
**Head-of-line blocking**: When one lost TCP packet makes every later packet wait for its resend.
**Signaling**: The setup messages (SDP, ICE candidates) peers swap before media flows. WebRTC leaves it to you.
**SDP**: Session Description Protocol. A text format describing a media session's codecs, keys and addresses.
**Symmetric NAT**: A NAT that picks a new public port for each destination, so a STUN-learned address does not work for other peers and a TURN relay is needed.
**DTLS-SRTP**: Using a DTLS handshake over UDP to create the keys that encrypt RTP media. WebRTC media is always encrypted this way.
**RTP**: The packet format for real-time media. Each packet has a sequence number and a timestamp.
**RTCP**: RTP's control channel. It carries loss and jitter reports and feedback such as NACKs.
**NACK**: A receiver's message naming a packet it did not get, asking for a resend.
**Opus**: The audio codec WebRTC uses by default. It runs at 48 kHz and can hide some packet loss with in-band FEC.
**Jitter buffer**: A short hold on received audio that absorbs uneven arrival times, at the cost of added delay. See [WebRTC from the wire up](lesson:livekit/webrtc-from-the-wire-up).
**PLC (packet loss concealment)**: The decoder makes up plausible audio for a missing frame.
**SFU (selective forwarding unit)**: A server that forwards encoded media packets to subscribers without decoding them. See [mesh, MCU, SFU](lesson:livekit/mesh-mcu-sfu).
**MCU (multipoint control unit)**: A server that decodes, mixes and re-encodes all streams into one stream per participant.
**Simulcast**: A publisher sends several quality layers so the SFU can forward the one each subscriber can handle.
**Room (LiveKit)**: A session that participants join. Usually one room per call. See [rooms, participants and tracks](lesson:livekit/rooms-participants-tracks).
**Participant**: Anyone or anything in a room: a browser, a phone leg, an agent, a recorder.
**Track**: One stream of audio or video that a participant publishes and others subscribe to.
**Egress**: LiveKit's service for recording or exporting a room or individual tracks.
**Ingress**: LiveKit's service for bringing in media that is not WebRTC, such as RTMP or files.
**Agent dispatch**: How LiveKit decides which agent worker joins which room. Without an agent name, a worker is sent to every room.
**Prewarm**: Loading models once per worker process so each call does not pay the load time.
**Stream ticket**: A one-time token, stored with a short expiry, that a carrier must present when it opens the audio WebSocket. See [who is on this socket](lesson:voice-prod/who-is-on-this-socket).
**HMAC**: A keyed hash. Only someone holding the secret key can produce the right output.
**Timing attack**: Guessing a secret by measuring how long a comparison takes to reject each guess. `hmac.compare_digest` prevents it.
**Event loop**: One thread that switches between many async tasks. A blocking call stalls all of them. See [never block the audio loop](lesson:voice-prod/never-block-the-audio-loop).
**Backpressure**: Slowing down a producer, or dropping its excess, when the consumer cannot keep up.
**Pure function**: A function that returns the same output for the same input and changes nothing else. Easy to test.
**Barge-in**: The caller talking over the agent, so the agent must stop and listen.
**RMS**: Root mean square, a measure of how loud an audio frame is.
**AMD (answering machine detection)**: Deciding whether an outbound call reached a person or voicemail.
**Consumer group**: A named reader of a Redis Stream with its own position. Each entry goes to one consumer in the group. See [events that don't lie](lesson:voice-prod/events-that-dont-lie).
**Pending entries list (PEL)**: Entries a consumer group delivered that nobody has acknowledged yet.
**At-least-once delivery**: Nothing is lost, but a message can arrive more than once, so handlers must ignore repeats.
**Idempotent**: Running it twice has the same effect as running it once.
**Dead-letter queue**: Where a message goes after too many failed tries, for a human to look at.
**Thundering herd**: Many clients that failed together retry together, and the burst knocks over the server that was recovering.
**Full jitter**: Backoff where each retry waits a random time between zero and an exponentially growing cap.
**SKIP LOCKED**: A Postgres option that makes a locking SELECT skip rows another transaction holds, so several workers can share a queue table safely.
**Graceful drain**: On shutdown, stop taking new work and let work in progress finish before exiting. See [timeouts, retries and goodbyes](lesson:voice-prod/timeouts-retries-and-goodbyes).
**SIGTERM**: The polite "please exit" signal a deploy sends first. SIGKILL follows if the process does not exit, and it cannot be caught.
**Percentile (p95)**: The value that 95% of measurements are at or below. It shows the slow cases an average hides.
**TTFS (time to first sentence)**: Time until the LLM has produced its first full sentence, which is when TTS can start speaking.
**Fernet**: Symmetric encryption from Python's cryptography package that also detects tampering.
**Fail closed**: When a check cannot be done, choose the answer that does the least harm, such as not recording.
**PII**: Personally identifiable information, such as names, phone numbers or card numbers.
**Test pyramid**: Many fast, cheap tests at the bottom and a few slow, expensive ones at the top.
**Image tag**: A name that points at one container image version. `latest` is only a default name and can move under you.
**Access token (LiveKit)**: A JWT signed with the LiveKit API secret. It names a participant's identity, the room, and what it may do there (join, publish, subscribe). Mint it on your server, never in the client.
**Auto-subscribe**: LiveKit's default of sending every existing and future track in a room to each participant.
**Dispatch rule**: A LiveKit SIP setting that decides which room an inbound phone caller joins.
**Idle process**: An agent worker process started ahead of time and kept ready, with models already loaded, for the next call.
**livekit-server**: LiveKit's open-source SFU, written in Go on the Pion WebRTC library. See [what LiveKit is](lesson:livekit/what-livekit-is).
**lk**: LiveKit's command-line tool for tokens, rooms, dispatch, egress, ingress, SIP and load tests. Works against self-hosted servers. See [the lk CLI](lesson:livekit/the-lk-cli).
**Distributed mode**: What livekit-server switches to when `redis.address` is set. Rooms and messages go through Redis, so several nodes plus egress, ingress and SIP can work together. See [scaling](lesson:livekit/scaling-and-load).
**Host networking**: Running a Docker container directly on the host's network. LiveKit recommends it because WebRTC needs real UDP ports and IPs.
**Glare**: Both sides of a WebRTC connection sending an offer at once. LiveKit avoids it with separate publisher and subscriber connections.
**Twirp**: The RPC style behind LiveKit's server API: an HTTP POST to `/twirp/<Service>/<Method>` with a JSON body and a Bearer token. See [the server API](lesson:livekit/the-server-api).
**Video grant**: The `video` claim in a LiveKit token. It names the room and what the holder may do there. See [tokens and grants](lesson:livekit/tokens-and-grants).
**Track publication**: The server's record that a track exists. Everyone sees it; only subscribers get the media.
**Participant kind**: What sort of participant it is: STANDARD, AGENT, SIP, CONNECTOR, EGRESS or INGRESS.
**Hidden participant**: A participant others in the room cannot see, such as a recorder.
**Selective subscription**: Turning off auto-subscribe and choosing which tracks to receive.
**Webhook (LiveKit)**: A signed HTTP POST the LiveKit server sends your backend when something happens in a room. Delivery is retried, so handlers must be idempotent. See [webhooks and events](lesson:livekit/webhooks-and-events).
**Dynacast**: The SFU tells a publisher to pause video layers nobody is watching.
**Adaptive stream**: The client asks for the video layer that fits the element showing it, and pauses hidden ones.
**SVC (scalable video coding)**: One video stream that holds several resolution and frame-rate layers. VP9 and AV1 use it.
**RED (redundant audio)**: Sending each audio frame again in later packets, so a lost packet can be rebuilt.
**DTX (discontinuous transmission)**: Opus sends almost nothing during silence, which saves bandwidth.
**E2EE (end-to-end encryption)**: Media encryption the server cannot read. In LiveKit you create and share the keys yourself. See [media in depth](lesson:livekit/media-in-depth).
**Text stream**: A reliable stream of text on a named topic, sent to participants who are connected now. Agents send transcripts on `lk.transcription`. See [data and state](lesson:livekit/data-and-state).
**Byte stream**: Like a text stream, but for files and binary data.
**RPC (LiveKit)**: Calling a named method on another participant and waiting for the reply. Payloads up to 15 KiB, default timeout 10 s.
**Data packet**: One low-level message, reliable (up to 15 KiB) or lossy (about 1300 bytes).
**Data track**: A published track of lossy, in-order data frames for continuous data such as sensor readings.
**Participant attributes**: A small key-value map on each participant (64 KiB total) that LiveKit syncs to everyone. Setting your own needs the `can_update_own_metadata` grant.
**Agent server**: The long-running process that registers with LiveKit and runs each agent job in its own child process. Older code and logs call it a worker. See [agent server and dispatch](lesson:livekit/agent-server-and-dispatch).
**Job metadata**: A string, up to 512 KiB, attached to a dispatch and read by the agent as `ctx.job.metadata`.
**AgentSession**: The object inside a job that runs the voice pipeline, calls the LLM and emits state and error events. See [the agents mental model](lesson:livekit/agents-mental-model).
**RoomIO**: The part of an agent session that subscribes to the user's audio and publishes the agent's audio and transcripts.
**Turn detector**: A model on top of VAD that guesses whether the user has finished their turn. `v1-mini` runs on local CPU; `v1` runs on LiveKit Cloud. See [turns and interruptions](lesson:livekit/turns-and-interruptions).
**False interruption**: A sound that paused the agent but held no words. The agent resumes after a timeout.
**Backchannel**: Short listener sounds such as "uh-huh" that mean "go on", not "stop".
**Function tool**: A Python function the LLM can call during a turn, declared with `@function_tool`. See [tools, tasks and workflows](lesson:livekit/tools-tasks-and-workflows).
**Handoff**: Passing the session to another Agent by returning it from a tool. The new agent starts with empty context unless you pass `chat_ctx`.
**AgentTask**: A short sub-conversation that takes control until it calls `complete()` with a typed result.
**Pipeline node**: An overridable Agent method (stt_node, llm_node, tts_node, transcription_node) that one stage of a turn streams through. See [nodes, hooks, RAG and fallbacks](lesson:livekit/nodes-hooks-rag-fallbacks).
**FallbackAdapter**: A wrapper over several STT, LLM or TTS providers that switches to the next when one fails. Works self-hosted.
**LiveKit Inference**: LiveKit Cloud's model gateway, used through `inference.*` classes. Not available on a self-hosted server. See [models without the Cloud](lesson:livekit/models-without-the-cloud).
**StreamAdapter**: Wraps a non-streaming STT such as Whisper and uses VAD to cut audio into clips.
**MCP (Model Context Protocol)**: A standard way to expose tools from a separate server. LiveKit agents mount one with `MCPToolset`.
**Token endpoint**: Your backend route that returns `server_url` and `participant_token` to a frontend, so the API secret never leaves the server. See [frontends and sessions](lesson:livekit/frontends-and-sessions).
**Scripted LLM**: A fake model that follows fixed rules, so agent tests run offline, free and the same every time. See [testing and observability](lesson:livekit/testing-and-observability).
**PSTN**: The public switched telephone network: the ordinary phone network.
**SIP trunk**: A SIP account at a phone provider that links phone numbers to your server. See [self-hosted SIP](lesson:livekit/self-hosted-sip).
**Dispatch rule types**: How LiveKit SIP picks a room for an inbound call: individual (one room per caller), direct (a fixed room, optional PIN) or callee (named after the called number).
**Early media**: Audio before a call is answered, started by a 183 Session Progress response.
**DTMF**: Keypad tones. On SIP calls they travel as RTP telephone-event packets. See [phone features](lesson:livekit/phone-features).
**IVR**: Interactive voice response, a "press 1 for billing" phone menu.
**SIP REFER**: A SIP request asking the other side to connect the call elsewhere. LiveKit uses it for cold transfers.
**Cold transfer**: Handing a caller to another number without briefing anyone first.
**Warm transfer**: Briefing a human first, then connecting them to the caller.
**SRTP**: Encrypted RTP. On SIP trunks it pairs with TLS signaling on port 5061.
**Media timeout**: LiveKit ends a SIP call if no RTP arrives for 30 s at the start or 15 s after the last packet.
**G.722**: A wideband phone codec carrying 16 kHz audio (HD voice), though its SDP line says 8000.
**Stream key**: The secret part of an RTMP URL that tells ingress which ingress and room a stream belongs to. See [ingress](lesson:livekit/ingress).
**WHIP**: WebRTC-HTTP ingestion protocol, a simple HTTP handshake that starts a WebRTC publish.
**Auto egress**: Recording set on the room itself (in CreateRoom or a token's room config), so it starts with the room. See [egress and recording](lesson:livekit/egress-recording).
**TURN/TLS**: A media relay reached over TLS on port 443, so it looks like HTTPS and passes strict firewalls. See [production deployment](lesson:livekit/production-deployment).
**Node selector**: The livekit-server setting that picks which node hosts a new room, for example region-aware with a `sysload_limit`.
**Playout delay**: How long a subscriber buffers video before showing it. Lower means fresher but choppier.
**Zero-shot prompting**: Asking a model to do a task with no examples in the prompt. See [zero-, one- and few-shot](lesson:prompting/zero-one-few-shot).
**Chain of thought**: Getting a model to write its steps before the final answer. See [chain of thought](lesson:prompting/chain-of-thought).
**ReAct**: A prompt pattern where the model alternates thoughts, tool actions and observations. See [ReAct](lesson:prompting/react).
**Self-consistency**: Sampling several reasoning chains and keeping the answer most of them agree on. See [self-consistency](lesson:prompting/self-consistency).
**Tree of thought**: Reasoning that tries several branches, scores them and drops weak ones. See [tree of thought](lesson:prompting/tree-of-thought).
**Run (MLflow)**: One recorded training or evaluation: its parameters, metrics, tags and files. See [tracking runs](lesson:mlflow/tracking-runs-and-search).
**Experiment (MLflow)**: A named group of runs, such as `wine-forest`.
**Artifact**: A file a run or pipeline step produces: a model, a plot, a dataset.
**Signature (MLflow)**: The input and output schema saved with a model. It makes a wrong column fail at predict time. See [models](lesson:mlflow/models-and-signatures).
**Flavor (MLflow)**: A way to load a saved model, such as `sklearn` or the generic `python_function`.
**Span**: One step inside a trace, with its input, output and timing. See [tracing](lesson:mlflow/tracing-an-llm-app).
**Scorer (MLflow)**: A check that returns a value for one app output; a Python function or an LLM judge. See [evaluation](lesson:mlflow/evaluation-and-prompts).
**Kubernetes**: A system that schedules containers across machines. Kubeflow runs ML work on it.
**Component (KFP)**: One pipeline step: a Python function that runs in its own container. See [your first pipeline](lesson:kubeflow/your-first-pipeline).
**kind**: A tool that runs a small Kubernetes cluster as Docker containers, for local testing.
**TrainJob**: Kubeflow Trainer's object for one distributed training run. See [training and tuning](lesson:kubeflow/training-and-tuning).
**InferenceService**: KServe's Kubernetes object that turns a saved model into a web service. See [KServe](lesson:kubeflow/serving-and-mlflow-bridges).
**ggml**: The C tensor library under llama.cpp. It stores numbers, builds compute graphs, and runs them on CPUs and GPUs. See [ggml](lesson:llamacpp/ggml-tensors-graphs-backends).
**Tensor**: A block of numbers with a shape, such as a 4096 x 4096 matrix. Model weights and activations are tensors.
**Compute graph**: A list of operations and the tensors they connect, built first and run later. ggml runs one per batch.
**Backend (ggml)**: The code that runs a compute graph on one kind of hardware: CPU, CUDA, Metal, Vulkan and others.
**Offload (-ngl)**: Putting some or all of a model's layers on the GPU. `-ngl 20` puts 20 layers there; the rest run on the CPU.
**K-quants**: llama.cpp's quantization types with super-blocks of 256 weights and their own scales, such as Q4_K and Q6_K. Names ending in _S, _M or _L are size mixes.
**imatrix (importance matrix)**: Statistics from running sample text through a model, used to keep the most important weights more accurate when quantizing.
**Perplexity**: A score of how surprised a model is by real text. Lower is better. Used to check that quantization did not hurt a model much.
**mmap (memory mapping)**: Letting the operating system load a file's pages into memory only when they are read. llama.cpp loads GGUF weights this way.
**ubatch (micro-batch)**: The piece of a batch that llama.cpp computes in one graph run. Set with `-ub`.
**Slot (llama-server)**: One conversation's place in the server: its prompt, KV cache sequence and sampler. `-np 4` gives four slots.
**Continuous batching**: Putting tokens from many conversations into one batch every step, so new requests join without waiting for others to finish.
**Sampler chain**: The ordered list of steps that turns a model's scores into one chosen token, such as top-k, top-p, temperature, then a random draw.
**Temperature**: A number that sharpens (below 1) or flattens (above 1) the model's choice. 0 means always take the top token.
**Top-k, top-p, min-p**: Ways to drop unlikely tokens before choosing: keep the k best; keep the best until their chances add up to p; keep tokens at least p times as likely as the best one.
**GBNF**: llama.cpp's grammar format. A grammar limits which tokens may come next, so output always matches a pattern such as valid JSON.
**RoPE**: Rotary position embedding. Encodes a token's position by rotating its query and key vectors.
**Flash attention**: A way to compute attention in one fused step without storing the full attention matrix. Faster and uses less memory.
**Speculative decoding**: A small, fast draft model guesses several tokens and the big model checks them all at once. Same output, often faster.
**SIMD**: CPU instructions that do the same math on many numbers at once, such as AVX2 on x86 and NEON on Arm.
