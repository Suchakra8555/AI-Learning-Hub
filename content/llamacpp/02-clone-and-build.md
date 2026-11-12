---
title: Clone it and build it
summary: Build llama.cpp from source for CPU, then see the flags for CUDA, Metal, Vulkan and friends, what lands in build/bin, and three ways to skip building.
time: 20 min
---

You can install llama.cpp with a package manager, but developers should build it once. You get the newest code, every tool, the test suite, and the headers to link your own programs. It takes a few minutes.

## What you need

- A C/C++ compiler: GCC or Clang on Linux, Xcode command-line tools on macOS, Visual Studio 2022 on Windows.
- CMake 3.14 or newer.
- Git.
- For GPU builds, the GPU's SDK (CUDA toolkit, Vulkan SDK, ROCm, ...). Not needed for CPU or Apple Metal.

We built on Ubuntu with GCC 13.3, CMake 3.28, and 4 CPU cores.

## Clone

```bash
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
git log -1 --format='%h %cd %s'
```

The project moved from `ggerganov/llama.cpp` to the `ggml-org` organization. Old links redirect. To match this course exactly, check out our commit:

```bash
git checkout 0fb8f15
```

## Build for CPU

Two commands. The first configures, the second compiles:

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j 4
```

`-j 4` compiles 4 files at once; use your number of cores. On our 4 cores it took **about 4.5 minutes**. The configure step told us what it found:

```text
-- llama.cpp version: 0.9.0-dev
-- Warning: ccache not found - consider installing it for faster compilation ...
-- GGML_SYSTEM_ARCH: x86
-- Including CPU backend
-- Adding CPU backend variant ggml-cpu: -march=native
-- ggml version: 0.29.0
```

`-march=native` means the CPU code is compiled for **your** CPU's instructions (AVX2, AVX-512 and so on). It is fast but may crash on an older machine. If you will copy the binaries elsewhere, add `-DGGML_NATIVE=OFF`.

Install `ccache` before you start changing code. It caches compiled files so rebuilds after small edits take seconds.

### One warning you may see

```text
-- UI: downloading from b50: https://huggingface.co/buckets/ggml-org/llama-ui/resolve/b50/dist.tar.gz
-- UI: HF download failed
CMake Warning ... UI: no assets available - building without an embedded UI.
  In a disconnected environment, download the pre-built UI from a llama.cpp
  release at https://github.com/ggml-org/llama.cpp/releases and extract to tools/ui/dist.
```

At our commit, the build downloads the server's web chat page from Hugging Face. Our build machine could not reach Hugging Face, so our `llama-server` had no web page. The API still worked. If you see this, do what the message says, or ignore it if you only need the API.

## What you get

Everything lands in `build/bin/`. We got 127 files (38 MB):

| File | What it is |
|---|---|
| `llama` | The unified binary: `llama serve`, `llama cli`, `llama download`, and more |
| `llama-server` | The HTTP server, OpenAI- and Anthropic-compatible |
| `llama-cli` | Interactive chat in the terminal |
| `llama-completion` | Plain text completion, the old `main` behaviour |
| `llama-quantize` | Convert a GGUF to fewer bits |
| `llama-bench`, `llama-batched-bench`, `llama-perplexity` | Speed and quality measurement |
| `llama-embedding`, `llama-tokenize`, `llama-imatrix`, `llama-gguf-split`, ... | Single-purpose tools |
| `llama-simple`, `llama-simple-chat`, `llama-batched`, ... | Example programs to read |
| `test-*` | 55 unit tests |
| `libllama.so`, `libggml*.so`, `libllama-common.so`, `libmtmd.so` | The libraries, to link your own code |

The unified binary is new. Try it:

```bash
./build/bin/llama --version
./build/bin/llama help
./build/bin/llama help all
```

Our output:

```text
version: 0.9.0-dev (build 50, commit 0fb8f15)
built with GNU 13.3.0 for Linux x86_64

Available commands:
  serve           HTTP API server
  cli             Command-line interactive interface
  download        Download a model
  version         Show version
  licenses        Show third-party licenses
  help            Show available commands
```

`llama help all` adds the hidden ones: `completion`, `bench`, `batched-bench`, `fit-params`, `quantize`, `perplexity`, and `update`. `llama serve` and `llama-server` run the same code. Older guides and most of the docs use the `llama-*` names; this course does too.

## Check it works

Run four of the unit tests. All four passed for us:

```bash
./build/bin/test-gguf          # 101/101 tests passed, 0.1 s
./build/bin/test-rope          # 0.1 s
./build/bin/test-sampling      # 1.2 s
./build/bin/test-quantize-fns  # 4.2 s
```

`./build/bin/llama-cli --list-devices` shows GPUs. On our CPU-only build it printed `Available devices: (none)`, which is correct: the CPU is always there and is not listed.

## GPU builds

Add one flag to the configure step. From `docs/build.md`:

| Hardware | Flag | Notes |
|---|---|---|
| NVIDIA | `-DGGML_CUDA=ON` | Needs the CUDA toolkit. `-DCMAKE_CUDA_ARCHITECTURES="86;89"` to pick GPU generations |
| Apple silicon | (none) | Metal is on by default on macOS |
| AMD | `-DGGML_HIP=ON -DGPU_TARGETS=gfx1030` | Needs ROCm. Set your GPU's target |
| Any GPU with Vulkan | `-DGGML_VULKAN=ON` | Needs the Vulkan SDK. Works on NVIDIA, AMD, Intel |
| Intel GPU | SYCL, see `docs/backend/SYCL.md` | Needs oneAPI |
| CPU with a BLAS library | `-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS` | Can speed up prompt processing on CPU |

You can combine backends, for example `-DGGML_CUDA=ON -DGGML_VULKAN=ON`, then pick at run time with `--device`. We had no GPU, so we did not test any of these.

Other useful build switches:

- `-DBUILD_SHARED_LIBS=OFF`: one static binary per tool, easy to copy.
- `-DGGML_BACKEND_DL=ON`: backends become plug-in libraries, loaded at start-up.
- `--target llama-server`: build only one tool, e.g. `cmake --build build -j --target llama-server`.
- `-DCMAKE_BUILD_TYPE=Debug`: for stepping through the code in a debugger.

## Three ways to skip building

- **Packages.** `brew install llama.cpp`, `winget install llama.cpp`, `conda install -c conda-forge llama.cpp`, `nix profile install nixpkgs#llama-cpp` (from `docs/install.md`). The new installer script from the README: `curl -LsSf https://llama.app/install.sh | sh`. Read a script before piping it to `sh`.
- **Release binaries** from [the releases page](https://github.com/ggml-org/llama.cpp/releases), built for each OS and GPU type.
- **Docker.** `ghcr.io/ggml-org/llama.cpp:server` for the server, with `-cuda`, `-rocm`, `-vulkan`, `-intel` variants (`docs/docker.md`).

For production, pick a release tag and pin it. The `master` branch changes many times a day.

:::try
Build with `-DCMAKE_BUILD_TYPE=Debug` in a second folder (`cmake -B build-debug ...`). Keep the Release build for running models and the Debug build for reading code in a debugger. Both share the same source tree.
:::

:::check Your build works on your laptop, but the binary crashes with "illegal instruction" on a server. Why, and what is the fix?
The default build uses `-march=native`, so it uses instructions your laptop's CPU has and the server's may not. Rebuild with `-DGGML_NATIVE=OFF`, or build on the server itself.
:::

:::check Is `llama serve` a different server from `llama-server`?
No. The unified `llama` binary dispatches to the same server code. It is a new front door, not a new server.
:::
