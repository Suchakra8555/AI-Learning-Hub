---
title: GGUF files - what is inside, where to get them, will they fit
summary: Read a GGUF file byte by byte with 130 lines of Python, learn the metadata keys llama.cpp relies on, download models with -hf, and work out memory before you load anything.
time: 25 min
---

Everything llama.cpp runs comes from one **GGUF** file: the weights, the model's shape, the tokenizer, the chat template. When something goes wrong (a garbled answer, a template error, a model that will not load), the first question is often "what is actually in this file?" This lesson answers it.

## The layout

The format is defined in a comment at the top of `ggml/include/gguf.h`. In order:

| Part | Contents |
|---|---|
| Magic | The 4 bytes `GGUF` |
| Version | A 32-bit number, currently 3 |
| Counts | Number of tensors, number of metadata entries (64-bit each) |
| Metadata | Key-value pairs: a string key, a type code, a value. Values can be numbers, booleans, strings, or arrays of those |
| Tensor infos | Per tensor: name, number of dimensions, the size of each, the ggml type (F16, Q4_K, ...), and an offset into the data |
| Padding | Zeros up to the alignment (32 bytes unless `general.alignment` says otherwise) |
| Data | All tensor bytes, each one aligned |

Strings are a 64-bit length followed by the bytes, without a terminating zero. Everything is little-endian.

Because the data block is already laid out the way ggml wants it in memory, llama.cpp can **memory-map** the file: ask the operating system to treat the file as memory and read pages on demand. Loading a 5 GB model starts almost at once, and two processes using the same file share one copy in RAM.

## Read one yourself

`code/llamacpp/gguf_peek.py` reads that layout with Python's `struct` module and nothing else. Try it on a hand-made file first:

```bash
python code/llamacpp/gguf_peek.py --demo
```

Then on a real model. Ours is the Q4_0 file from [lesson 4](lesson:llamacpp/train-convert-run):

```text
GGUF version 3, 25 metadata keys, 39 tensors, data starts at byte 45088

  general.architecture                          llama
  general.type                                  model
  general.name                                  Tiny Llama
  general.size_label                            4.0M
  llama.block_count                             4
  llama.context_length                          512
  llama.embedding_length                        256
  llama.feed_forward_length                     704
  llama.attention.head_count                    4
  llama.attention.head_count_kv                 2
  llama.rope.freq_base                          10000.0
  llama.attention.layer_norm_rms_epsilon        9.999999747378752e-06
  llama.attention.key_length                    64
  llama.attention.value_length                  64
  llama.vocab_size                              2000
  llama.rope.dimension_count                    64
  tokenizer.ggml.model                          llama
  tokenizer.ggml.pre                            default
  tokenizer.ggml.tokens                         [2000 items] ['<unk>', '<s>', '</s>', '<0x00>', '<0x01>'] ...
  tokenizer.ggml.scores                         [2000 items] [0.0, 0.0, 0.0, 0.0, 0.0] ...
  tokenizer.ggml.token_type                     [2000 items] [2, 3, 3, 6, 6] ...
  tokenizer.ggml.bos_token_id                   1
  tokenizer.ggml.eos_token_id                   2
  general.quantization_version                  2
  general.file_type                             2

  tensor                          shape (ne0, ne1, ...)   type          bytes
  output.weight                   [256, 2000]             Q6_K        420,000
  output_norm.weight              [256]                   F32           1,024
  token_embd.weight               [256, 2000]             Q4_0        288,000
  blk.0.attn_k.weight             [256, 128]              Q4_0         18,432
  blk.0.attn_norm.weight          [256]                   F32           1,024
  ...
  tensor data: 2.3 MiB, tensors by type: {'Q6_K': 1, 'F32': 9, 'Q4_0': 29}
```

## Reading the metadata

The keys follow a pattern: `general.*` for everything, `<architecture>.*` for the model's shape, `tokenizer.*` for the vocabulary. The ones to know:

| Key | What it tells you |
|---|---|
| `general.architecture` | Which graph builder llama.cpp uses (`llama`, `qwen3`, `gemma3`, ...). Unknown value = "unknown model architecture" error |
| `<arch>.context_length` | The context length it was trained with. `-c 0` uses this |
| `<arch>.block_count` | Number of layers. What `-ngl` counts |
| `<arch>.attention.head_count_kv` | KV heads. Fewer than `head_count` means grouped-query attention and a smaller KV cache |
| `<arch>.rope.*` | Position encoding settings. Wrong values give fluent nonsense at long range |
| `tokenizer.ggml.model` | Tokenizer family: `llama` (SentencePiece), `gpt2` (BPE), `bert`, `t5`, ... |
| `tokenizer.ggml.pre` | For BPE models, which pre-tokenizer regex to use. A wrong value silently changes tokens |
| `tokenizer.ggml.token_type` | Per token: 1 normal, 2 unknown, 3 control (like `<s>`), 6 byte. Matches our output: `<unk>` is 2, `<s>` and `</s>` are 3, `<0x00>` is 6 |
| `tokenizer.chat_template` | The Jinja chat template. **Our file has none**, which matters in [the server lesson](lesson:llamacpp/llama-server) |
| `general.file_type` | The quant recipe. 2 is Q4_0, 7 is Q8_0, 15 is Q4_K_M (the numbers `llama-quantize` lists) |

In the tensor list, note three things. Names follow `blk.<layer>.<part>.weight`. Shapes are in ggml order, innermost first. And not every tensor has the file's type: our "Q4_0" file keeps `output.weight` in Q6_K and the norms in F32. A file type is a recipe, not a promise.

For more than reading, llama.cpp's own Python package `gguf` (in `gguf-py/`, also on PyPI as `gguf`) can read and write files. It installs commands such as `gguf-dump` (print everything) and `gguf-set-metadata` and `gguf-new-metadata` (change keys, for example to fix a broken chat template without reconverting).

## Getting models

Three ways, from simplest to most work.

**1. Let llama.cpp download.** Every tool takes `-hf`:

```bash
llama-server -hf ggml-org/gemma-3-4b-it-GGUF            # default quant, Q4_K_M if present
llama-cli    -hf bartowski/Qwen2.5-7B-Instruct-GGUF:Q5_K_M
llama download -hf ggml-org/gemma-3-4b-it-qat-GGUF:Q4_K_M   # just download, print the path
```

The part after `:` picks the quant (case does not matter). For vision models the matching `mmproj` file comes along automatically. Files land in the standard Hugging Face cache (`~/.cache/huggingface/hub`, or wherever `LLAMA_CACHE` or `HF_HOME` points), so they are shared with other Hugging Face tools. Gated models need `-hft` or the `HF_TOKEN` environment variable. `--offline` uses the cache only.

We could not run `-hf`: our build machine had no access to Hugging Face. The flags above are from `common/arg.cpp` and `docs/models.md` at our commit.

**2. Download a GGUF yourself** from a model page on Hugging Face and pass it with `-m`. The `ggml-org` organization publishes official conversions. Large models come split as `model-00001-of-00003.gguf` and so on; pass the first file and llama.cpp finds the rest (`llama-gguf-split` splits and merges such files).

**3. Convert from Hugging Face format** with `convert_hf_to_gguf.py`, then quantize. Needed for your own fine-tunes, brand-new models, and when you do not trust a third-party file. [Lesson 4](lesson:llamacpp/train-convert-run) does this end to end.

:::warn Treat downloaded model files with care
A GGUF file is data, not a program, but llama.cpp parses every byte of it and runs the Jinja chat template inside it. Prefer files from the model's authors or `ggml-org`, check the hash shown on the model page, and keep llama.cpp up to date.
:::

## Will it fit? Do the math first

Memory for a run is roughly **weights + KV cache + compute buffers**.

- **Weights** ≈ the file size. With `-ngl`, the offloaded layers' weights go to VRAM instead of RAM.
- **KV cache** = 2 × layers × context × KV heads × head size × bytes per number. It grows with `-c`, and it is shared by all of a server's slots.
- **Compute buffers** are scratch space for one batch, often a few hundred MB, larger with a bigger `-ub`.

`code/llamacpp/memory_plan.py` does the first two:

```bash
python code/llamacpp/memory_plan.py
```

```text
Llama 3.1 8B weights by quant type (approximate):
  F16      15.0 GiB
  Q8_0      7.9 GiB
  Q6_K      6.1 GiB
  Q5_K_M    5.3 GiB
  Q4_K_M    4.6 GiB
  Q4_0      4.2 GiB

KV cache for the whole context (all slots share it):
    n_ctx       f16      q8_0      q4_0
     4096     0.50G     0.27G     0.14G
     8192     1.00G     0.53G     0.28G
    32768     4.00G     2.12G     1.12G
   131072    16.00G     8.50G     4.50G

Q4_K_M + 32768-token f16 cache: 8.6 GiB before compute buffers
tiny-llama, n_ctx 512, f16 cache: 1.00 MiB
```

The F16 and Q4_K_M weights match the 14.96 GiB and 4.58 GiB in llama.cpp's quantize README. The KV table shows why long context is expensive: at 128K tokens, the cache of an 8B model is bigger than its 4-bit weights. Two levers, from [the CLI lesson](lesson:llamacpp/cli-and-sampling): a smaller `-c`, or a quantized cache with `-ctk q8_0 -ctv q8_0`. A quantized V cache needs flash attention; llama.cpp refuses to start otherwise.

You often do not need to do this by hand. `-fit` is **on by default** at our commit: when you leave settings like `-c` and `-ngl` unset, llama.cpp picks values that fit the free memory on each device, keeping a 1 GiB margin by default (`-fitt`). `llama-fit-params -m model.gguf` prints the flags it would choose, so you can see and pin them. Your explicit flags always win.

:::check A GGUF file says `general.file_type = 15` (Q4_K_M), but one tensor is Q6_K and another Q8_0. Is the file broken?
No. The file type names the recipe. Q4_K_M deliberately keeps some tensors in more bits, and tensors whose row length does not divide by 256 fall back to other types.
:::

:::check Your 8B model at Q4_K_M loads fine with `-c 8192` but runs out of memory with `-c 131072`. Why, and what are two fixes?
The KV cache grows with context: about 1 GiB at 8K and 16 GiB at 128K in F16 for this shape. Use a smaller `-c`, or quantize the cache with `-ctk q8_0 -ctv q8_0` (about half the size).
:::
