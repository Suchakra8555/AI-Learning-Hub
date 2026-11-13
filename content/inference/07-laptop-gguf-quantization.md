---
title: Running a model on your laptop, GGUF and quantization
summary: Squeeze a model into fewer bits per weight so it fits on small hardware, and learn to read names like Q4_K_M.
time: 20 min
---

Big models need big memory. **Quantization** stores each weight with fewer bits, so the file is smaller and runs on smaller hardware, at some cost in quality.

## The pieces

- **llama.cpp** is a C/C++ engine that runs models on Apple silicon, x86 CPUs, NVIDIA, AMD and others, and can split a model between CPU and GPU ([repo](https://github.com/ggml-org/llama.cpp)).
- **GGUF** is the file format it uses. It holds the weights and standard metadata in one file ([Hugging Face docs](https://huggingface.co/docs/hub/gguf)).
- **ONNX** is another model file format, and **ONNX Runtime** runs ONNX models across hardware ([docs](https://onnxruntime.ai/docs/)). We did not try the export here.

## Reading "Q4_K_M"

| Part | Meaning |
|---|---|
| **Q4** | About 4 bits per weight |
| **K** | The "k-quants" family. Hugging Face's table says Q4_K groups weights in super-blocks of 8 blocks of 32 and costs 4.5 bits per weight. |
| **M** | "Medium", a mix rule. Most weights get Q4_K, but some `attn_v` and `ffn_down` layers (the first and last eighth, and every third one between) get the bigger Q6_K. S and L are smaller and larger mixes. We read this in `src/llama-quant.cpp`; the [llama.cpp track](lesson:llamacpp/quantization) shows it. |

## A real size comparison

llama.cpp's quantize README shows Llama-3.1-8B at **14.96 GiB in F16** and **4.58 GiB in Q4_K_M** ([README](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md)). That is about a third of the size, which is the difference between needing a big GPU and fitting in ordinary laptop memory.

Quality drops a little with fewer bits. Measure on your own test set before shipping a quantized model. For an app that must run with no cloud connection, this is how a fine-tuned model reaches a small device.

## Try it

Download a small GGUF model, run `llama-server`, and call its OpenAI-style API from the `llm.py` style helper in the [first API call lesson](lesson:foundations/first-api-call). No GPU is needed for a small model. The [llama.cpp track](lesson:llamacpp/what-llama-cpp-is) does all of this step by step, with commands we ran.

:::check Why does a 4-bit model run where the 16-bit one will not?
Each weight takes about a quarter of the memory, so the whole model is much smaller. In the README's example, 14.96 GiB becomes 4.58 GiB.
:::
