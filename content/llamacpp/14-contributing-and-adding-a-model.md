---
title: Changing llama.cpp - tests, adding a model, and sending a pull request
summary: How to work on the code itself. Running the tests, the five touch points for a new architecture, the rules for kernels and quant types, and the project's strict AI-use policy.
time: 25 min
---

You have read the [map](lesson:llamacpp/map-of-the-code), [ggml](lesson:llamacpp/ggml-tensors-graphs-backends) and [libllama](lesson:llamacpp/inside-libllama). Now you want to change something: fix a bug, support a new model, speed up a kernel. This lesson is the workflow, from the project's own docs (`CONTRIBUTING.md`, `AGENTS.md`, `docs/development/HOWTO-add-model.md`) at commit `0fb8f15`.

## Set up for development

```bash
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Debug     # or RelWithDebInfo for speed plus symbols
cmake --build build -j
```

Install `ccache` first. The configure step suggests it, and rebuilds after small edits become a few seconds. Our first full Release build took about 4.5 minutes on 4 cores.

The build makes the test programs in `build/bin/test-*` (we got 55 of them). Run them all with CTest:

```bash
ctest --test-dir build --output-on-failure -j 4
```

Or run the one for the area you touched. These ran and passed on our build:

| Test | Checks | Time on our machine |
|---|---|---|
| `test-gguf` | Writing and reading GGUF files (101 cases) | 0.1 s |
| `test-rope` | RoPE variants against reference | 0.1 s |
| `test-sampling` | Every sampler, plus timings | 1.2 s |
| `test-quantize-fns` | Every quant type's quantize, dequantize and dot product | 4.2 s |
| `test-backend-ops test -o SOFT_MAX -b CPU` | 214 softmax cases | a few seconds |

## The test that matters most for kernels: test-backend-ops

`test-backend-ops` runs each ggml op on a backend and compares the result with the CPU backend. Three modes you will use:

```bash
./build/bin/test-backend-ops test -o MUL_MAT -b CUDA0     # correctness vs CPU
./build/bin/test-backend-ops perf -o MUL_MAT -b CPU       # speed
./build/bin/test-backend-ops support                      # which ops each backend supports
```

The contributing guide is direct about it: if you change ggml, run `test-backend-ops`. If you add or change an op, add test cases to it. You need two backends to compare. On a CPU-only machine, `test` mode has nothing to compare against, but `perf` still works.

## Before a pull request: perplexity, speed, CI

From `CONTRIBUTING.md`:

- Run the full CI locally: `mkdir tmp && bash ./ci/run.sh ./tmp/results ./tmp/mnt` (add `GG_BUILD_CUDA=1` for CUDA). We did not run the full CI; it downloads models.
- Check that **perplexity and speed did not get worse**, with `llama-perplexity` and `llama-bench`. The [benchmarking lesson](lesson:llamacpp/benchmark-and-tune) shows both.
- **Bug fixes must include a regression test** that fails before your change and passes after. Fixes without a test may be closed without review.
- **New features start as an issue**, not a PR.
- New contributors: one open PR at a time, and no typo or formatting-only PRs.

Coding style, briefly: plain C-style C++, basic `for` loops, no templates or fancy STL, 4-space indents, `snake_case`, `int32_t` and friends in the public API, `void * ptr` spacing, `struct foo {}` not `typedef struct`. No new third-party dependencies. When unsure, `clang-format`.

## Adding a new model architecture

This is the most common big contribution. A new model on Hugging Face usually needs changes in two places: the Python converter (HF to GGUF) and the C++ side (GGUF to graph). `docs/development/HOWTO-add-model.md` lists the steps; this is the short version.

### 1. Teach the converter

In the `conversion/` package (one module per family), add a class and register it under the HF architecture name from `config.json`. The Llama one, trimmed:

```python
@ModelBase.register("LlamaForCausalLM", "MistralForCausalLM", ...)
class LlamaModel(TextModel):
    model_arch = gguf.MODEL_ARCH.LLAMA
```

Then, as needed:

- Add the architecture and its tensor list to `gguf-py/gguf/constants.py`.
- Map HF tensor names (`model.layers.0.mlp.up_proj`) to GGUF names (`blk.0.ffn_up`) in `gguf-py/gguf/tensor_mapping.py`.
- Override `set_gguf_parameters` (extra hyperparameters), `set_vocab` (tokenizer), and `modify_tensors` (reshape, split, or permute weights). The doc recommends doing tensor surgery here at conversion time rather than in the C++ graph.

### 2. Register the architecture in C++

In `src/llama-arch.h` and `src/llama-arch.cpp`: add an `LLM_ARCH_*` enum value, its name, and any new metadata keys or tensor names. Add a case to `llama_model_rope_type`. Then grep for `LLM_ARCH_` across `src/`: several `switch` statements list architectures, and `test-llama-archs` fails if you miss one.

### 3. Write the graph

Create `src/models/<name>.cpp`: a class that inherits `llama_model_base` and implements `load_arch_hparams`, `load_arch_tensors` and `build_arch_graph`. Copy the closest existing model, not a blank file. Add it to `llama_model_mapping()` in `src/llama-model.cpp`.

### 4. Test it

Convert a real checkpoint, run it, and compare against the reference implementation:

- `examples/model-conversion/` has scripts to compare logits between the PyTorch model and the GGUF one.
- `llama-perplexity` on the converted model should match roughly what the original model gets.
- `llama-eval-callback` prints intermediate tensors so you can find the first layer that drifts.

### 5. Keep the PR small

From the guide: **CPU support only** in the first PR. GPU kernels come in follow-ups. Multimodal encoders and chat-template parsing are separate PRs too.

The repo ships an agent skill for exactly this job, `skills/add-new-model/SKILL.md`. Even if you never use an AI tool, read it. It is the most up-to-date checklist, and it says to look at 3 recent model-adding PRs (`git log --oneline -- src/models`) because "this shows current convention more reliably than the docs, which can lag behind". It also warns: "Never hack around RoPE with a custom sin/cos implementation. Several past PRs tried this and were closed."

## Adding a quant type is a big deal

New `ggml_type` values carry what the guide calls "a disproportionate maintenance burden": every backend may need kernels for them. To propose one you need, at minimum: a small converted model uploaded to Hugging Face, perplexity and KL-divergence comparisons against F16/BF16 and against types of similar size, and CPU speed numbers from `llama-bench`.

## The AI-use policy

llama.cpp has one of the strictest AI policies of any large open-source project. Read `AGENTS.md` and `CONTRIBUTING.md` yourself before contributing. The key lines, quoted:

- "AI-generated code is allowed. What is **not** allowed is submitting code you do not understand. You are 100% responsible for every line, however it was produced."
- "Undisclosed AI usage may result in your account being permanently banned from contributing to the project."
- "It is strictly prohibited to use AI to write your posts for you (bug reports, feature requests, pull request descriptions, Github discussions, responding to humans, ...)."
- The PR template has a required line: "AI usage disclosure: YES / NO - if yes, describe how AI was used".
- For commits made by an assistant on your behalf, use `Assisted-by:`, not `Co-authored-by:`.

The guide also suggests budgeting "something like one hour per 200-400 LOC" for your own manual review. Treat that as the real cost of a PR, whoever typed the code.

## A first contribution that is actually useful

Typo fixes are not welcome from new contributors. These are:

- Reproduce an open bug on your hardware and add a failing test to the issue.
- Run `test-backend-ops` on a backend few people have (an unusual GPU, a RISC-V board) and report failures.
- Measure a model with `llama-perplexity` before and after a recent change and post the numbers on the PR.
- Try a newly added model against its reference and report differences.

Each of these needs the skills from this track and helps maintainers directly.

:::check You fixed a crash in the KV cache. What must the PR include?
A link to a reproducible issue, and a regression test that fails before your fix and passes after. Also: a test run of the related tests, and the AI-use disclosure line in the template.
:::

:::check You added a new op to ggml with CPU and CUDA kernels. What test do you add and run?
Test cases in `tests/test-backend-ops.cpp` for the new op, then `test-backend-ops test -o YOUR_OP` with both backends to show CUDA matches CPU. But the guide prefers CPU-only in the first PR, with CUDA in a follow-up.
:::
