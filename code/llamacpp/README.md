# llama.cpp track code

Everything here was run against llama.cpp commit `0fb8f15` (12 November 2026), built for CPU on Linux.

| File | Lesson | Needs |
|---|---|---|
| `quant_blocks.py` | Quantization | Python standard library |
| `gguf_peek.py` | GGUF and getting models | Python standard library (`--demo` writes a tiny file first) |
| `sampler_chain.py` | CLI and sampling | Python standard library |
| `memory_plan.py` | GGUF and getting models, the server | Python standard library |
| `train_tiny_llama.py` | Train, convert, run | `torch`, `transformers`, `sentencepiece`, `safetensors` |
| `pipeline.sh` | Train, convert, run | A built llama.cpp (`LLAMA=...`) and the converter's Python packages |
| `server_client.py` | The server | Python standard library and a running `llama-server` |
| `ggml_hello.c` | ggml | A built llama.cpp (links `libggml`) |
| `mini_generate.cpp` | Your own program | A built llama.cpp (links `libllama`) |

Quick start, from the repo root:

```bash
git clone https://github.com/ggml-org/llama.cpp ~/src/llama.cpp
cd ~/src/llama.cpp && git checkout 0fb8f15 && cmake -B build && cmake --build build -j && cd -

pip install torch transformers sentencepiece safetensors   # CPU-only torch: add --index-url https://download.pytorch.org/whl/cpu
python code/llamacpp/train_tiny_llama.py --out tiny-llama
LLAMA=~/src/llama.cpp bash code/llamacpp/pipeline.sh tiny-llama
```

Model files (`*.gguf`) are ignored by git.
