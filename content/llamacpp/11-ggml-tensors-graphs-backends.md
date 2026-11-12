---
title: ggml, the engine room - tensors, graphs, backends
summary: How ggml stores numbers, why defining a computation does no math, how one graph is split between GPU and CPU, and how a quantized matrix multiply actually runs. With a 90-line C program you can build.
time: 30 min
---

Every token llama.cpp produces comes out of **ggml**, the tensor library in the `ggml/` folder. If you want to add an op, speed up a kernel, support new hardware, or just understand why a setting changes speed, you need this layer. It is smaller than it looks: four ideas carry most of it.

## Idea 1: a tensor is a header plus a pointer

`struct ggml_tensor` is in `ggml/include/ggml.h` (around line 690). The fields that matter:

```c
enum ggml_type type;                // F32, F16, Q4_0, Q4_K, ...
struct ggml_backend_buffer * buffer; // which memory it lives in (RAM, VRAM, ...)
int64_t ne[GGML_MAX_DIMS];          // number of elements per dimension (max 4)
size_t  nb[GGML_MAX_DIMS];          // stride in bytes per dimension
enum ggml_op op;                    // how this tensor is computed (NONE for inputs/weights)
struct ggml_tensor * src[GGML_MAX_SRC]; // the inputs of that op
void * data;                        // the numbers
char name[GGML_MAX_NAME];           // e.g. "blk.0.attn_q.weight"
```

Two things trip people up:

- **`ne[0]` is the innermost dimension**, the one whose numbers sit next to each other in memory. A 4096 x 11008 weight matrix with rows of 4096 numbers has `ne = [4096, 11008]`. It is the reverse of how PyTorch prints shapes.
- **`nb` is in bytes, and for quantized types it counts blocks.** For Q4_0, 32 weights take 18 bytes, so `nb[1] = 18 * (ne[0] / 32)`. Views, transposes and permutes only change `ne` and `nb`; they never copy data.

## Idea 2: define first, compute later

Calling `ggml_mul_mat(ctx, a, b)` does no math. It makes a new tensor and writes down what it will be. This is the whole function body, from `ggml/src/ggml.c`:

```c
const int64_t ne[4] = { a->ne[1], b->ne[1], b->ne[2], b->ne[3] };
struct ggml_tensor * result = ggml_new_tensor(ctx, GGML_TYPE_F32, 4, ne);
result->op     = GGML_OP_MUL_MAT;
result->src[0] = a;
result->src[1] = b;
return result;
```

You chain such calls to describe a whole model layer. Then `ggml_build_forward_expand(graph, output)` walks back through the `src` pointers and lists every node in an order where inputs come before outputs. That list is a **compute graph** (`struct ggml_cgraph`). Only when you hand the graph to a backend does anything get computed.

Why bother? Because with the whole graph in hand, ggml can plan memory once, reuse buffers between nodes, fuse ops, and give different nodes to different devices. llama.cpp rebuilds or reuses this graph for every batch.

Note the shape rule in that snippet: `mul_mat(a, b)` gives `[a.ne[1], b.ne[1]]`. Each output number is a dot product of a **row** of `a` with a column of `b`. Weights are always `a`, activations are always `b`.

## Try it: ggml with no model at all

`code/llamacpp/ggml_hello.c` builds one tiny layer, `y = silu(W x) + b`, twice: once with `W` in F32 and once with `W` quantized to Q4_0. Build it against your llama.cpp build:

```bash
LLAMA=~/src/llama.cpp   # wherever you cloned and built it
gcc -O2 code/llamacpp/ggml_hello.c -I$LLAMA/ggml/include -L$LLAMA/build/bin \
    -lggml -lggml-base -lggml-cpu -lm -Wl,-rpath,$LLAMA/build/bin -o ggml_hello
./ggml_hello
```

Our output:

```text
W:  f32, 1024 bytes
Wq: q4_0, 144 bytes

after defining: y->op = ADD, y->src[0]->op = UNARY
graph has 6 nodes:
  0: MUL_MAT  shape [4, 1]  inputs: W, x
  1: SILU     shape [4, 1]  inputs: node_0
  2: ADD      shape [4, 1]  inputs: node_1, b
  3: MUL_MAT  shape [4, 1]  inputs: W_q4_0, x
  4: SILU     shape [4, 1]  inputs: node_3
  5: ADD      shape [4, 1]  inputs: node_4, b

row           F32       Q4_0       diff
0         0.02187    0.01646    0.00540
1         0.33650    0.31551    0.02098
2         0.16562    0.16188    0.00374
3         0.47235    0.47731    0.00496
```

Read it top to bottom. The weights shrank from 1024 to 144 bytes. After "defining", `y` only knows it is an `ADD` of a `UNARY` (SILU). The graph lists the six nodes in run order. After compute, the quantized layer is close to the F32 one but not equal. A real model stacks thousands of these, which is why you [measure quality](lesson:llamacpp/benchmark-and-tune) after quantizing.

The ggml header itself opens with a similar tutorial (`ggml/include/ggml.h`, lines 40 to 75). One small catch: it passes `&gf` to `ggml_graph_compute_with_ctx`, but `gf` is already a pointer. Pass `gf`.

## Idea 3: backends and the scheduler

A **backend** is ggml's word for one kind of hardware plus the code to drive it. `ggml/include/ggml-backend.h` defines five handle types:

| Type | What it is | Example |
|---|---|---|
| `ggml_backend_reg_t` | One backend library, which lists its devices | "CUDA" |
| `ggml_backend_dev_t` | One device | GPU 0 |
| `ggml_backend_buffer_type_t` | A kind of memory | "CUDA0", "CPU" |
| `ggml_backend_buffer_t` | One block of that memory | The 4 GiB holding layers 10 to 31 |
| `ggml_backend_t` | A stream that runs graphs on a device | |

Each backend lives in its own folder (`ggml-cpu/`, `ggml-cuda/`, `ggml-metal/`, `ggml-vulkan/`, ...). Each one answers two questions per op: `supports_op` (can I run this?) and `offload_op` (do I want it?).

With `-DGGML_BACKEND_DL=ON` (needs shared libraries), backends become plug-ins: `ggml_backend_load_all()` scans for `libggml-<name>-*.so` files and picks the best variant by score. That is how one release binary picks AVX2 or AVX-512 CPU code at runtime.

The **scheduler** (`ggml_backend_sched`, in `ggml/src/ggml-backend.cpp`) is what makes `-ngl 20` work. Given a graph and a list of backends in priority order (CPU last), `ggml_backend_sched_split_graph` assigns each node a backend in five passes. The rules, in plain words:

1. **An op runs where its weights are.** If `blk.12.ffn_up.weight` was loaded into VRAM, the matmul that uses it runs on the GPU.
2. **Inputs start on the CPU.** Token ids arrive in RAM.
3. **Neighbours follow.** Small ops next to a GPU op go to the GPU too, to avoid copies.
4. **Unsupported ops fall back** to the next backend that supports them, usually the CPU.
5. **The graph is cut into splits**, runs of nodes on one backend. Between splits the scheduler inserts copies.

One more rule, `op_offload`: if the weights sit in RAM but a GPU supports the op and wants it, the GPU can still run it, copying the weights over. This is why a big prompt can be fast even when most layers are on the CPU.

Every split boundary costs a copy between devices, and every layer left on the CPU runs at CPU speed. So measure partial offload with `llama-bench -ngl` at a few values before you trust a guess. We had no GPU to measure this ourselves.

## Idea 4: how a quantized matmul runs on the CPU

The CPU backend is in `ggml/src/ggml-cpu/`. Compute goes like this:

1. `ggml_graph_compute` starts a thread pool. The calling thread is worker 0.
2. Every worker walks the same node list. For each node it calls `ggml_compute_forward`, a big `switch (tensor->op)`, and does its share of the rows. A barrier waits for all threads before the next node.
3. For `GGML_OP_MUL_MAT`, the code looks up the weight type in a table, `type_traits_cpu[]`. For Q4_0:

```c
[GGML_TYPE_Q4_0] = {
    .from_float   = quantize_row_q4_0,
    .vec_dot      = ggml_vec_dot_q4_0_q8_0,
    .vec_dot_type = GGML_TYPE_Q8_0,
```

So the CPU never turns Q4_0 weights back into floats. It **quantizes the activations to Q8_0** first, then multiplies blocks of 4-bit and 8-bit integers directly. Integer SIMD instructions do this fast. K-quants (Q4_K and friends) pair with Q8_K the same way.

4. `vec_dot` has one version per chip family under `arch/x86/`, `arch/arm/`, `arch/riscv/` and others, plus a plain C fallback in `quants.c`. Faster paths exist for some cases: `llamafile` sgemm, weights repacked into SIMD-friendly order (`repack.cpp`), Intel AMX, Arm KleidiAI.

This is why quantization speeds things up on a CPU, not only shrinks the file. Token generation is limited by how fast weights stream from RAM. Fewer bytes per weight means more tokens per second.

We measured it. `test-backend-ops` has a perf mode. This times one matrix-vector product the size of a Llama 3 8B feed-forward weight (4096 x 14336), as in generating one token:

```bash
./build/bin/test-backend-ops perf -o MUL_MAT -b CPU \
  -p 'type_a=(q4_0|f16|q8_0),type_b=f32,m=4096,n=1,k=14336'
```

| Weight type | Time per run | Speed vs F16 |
|---|---|---|
| F16 | 5.42 ms | 1x |
| Q8_0 | 2.90 ms | 1.9x |
| Q4_0 | 1.91 ms | 2.8x |

That was on 4 cores of a cloud Xeon at 2.3 GHz. Your numbers will differ; the order will not.

## The quant block formats

Every quant type is a fixed-size block. From `ggml/src/ggml-common.h`:

| Type | Weights per block | Bytes | Bits per weight | Layout |
|---|---|---|---|---|
| Q8_0 | 32 | 34 | 8.5 | one fp16 scale + 32 int8 |
| Q4_0 | 32 | 18 | 4.5 | one fp16 scale + 16 bytes of 4-bit pairs |
| Q4_K | 256 | 144 | 4.5 | super-block: fp16 scale and min, 12 bytes of 6-bit sub-scales, 128 bytes of 4-bit values |
| Q6_K | 256 | 210 | 6.56 | |

The [quantization lesson](lesson:llamacpp/quantization) re-implements Q8_0 and Q4_0 in Python, byte for byte.

## GGUF, the file ggml reads

GGUF is defined by the comment at the top of `ggml/include/gguf.h` and parsed by `ggml/src/gguf.cpp`. It is covered in the [GGUF lesson](lesson:llamacpp/gguf-and-getting-models). The point for this lesson: tensor data in a GGUF file is laid out exactly as ggml wants it in memory, aligned to 32 bytes. So loading can be a plain `mmap`, with no parsing or copying of weights.

## Where to go next in ggml

- `ggml/src/ggml-cpu/ggml-cpu.c`: `ggml_compute_forward_mul_mat` and the thread pool.
- `tests/test-backend-ops.cpp`: runs every op on every backend and compares with the CPU. The first thing to run after touching a kernel.
- `docs/ops.md` and `docs/ops/*.csv`: which ops each backend supports.
- ggml is also its own repo ([ggml-org/ggml](https://github.com/ggml-org/ggml)); changes are synced between the two.

:::check Why does `ggml_mul_mat` return immediately, even for a 4096 x 4096 matrix?
It only creates a result tensor and records the op and its two sources. The math happens later, when the whole graph is computed on a backend.
:::

:::check With `-ngl 16` on a 32-layer model, where does the matmul for layer 20 run, and why?
On the CPU, because layer 20's weights were loaded into RAM, and an op runs where its weights live. (The exception is `op_offload`, mostly for big prompt batches, where a GPU may pull the weights over and run it.)
:::

:::check Why is Q4_0 faster than F16 on a CPU, not just smaller?
Generating a token reads every weight once, so speed is limited by memory bandwidth. Q4_0 moves about 3.5 times fewer bytes. The dot product also runs on packed integers with SIMD, against activations quantized to Q8_0.
:::
