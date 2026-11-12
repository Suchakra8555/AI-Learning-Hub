---
title: Quantization, byte by byte
summary: What Q8_0, Q4_0 and Q4_K_M really store, rebuilt in 100 lines of Python. How llama-quantize mixes types per layer, what an importance matrix adds, and how to choose a type with numbers instead of guesses.
time: 30 min
---

A model trained in 16-bit numbers takes 2 bytes per weight. An 8-billion-weight model is 15 GiB, which does not fit on most laptops' GPUs. **Quantization** stores each weight in fewer bits. Done well, the model gets 3 to 4 times smaller and faster on CPUs, and quality drops a little. This lesson shows exactly what "done well" means in llama.cpp.

## The idea: blocks with their own scale

You cannot store a weight like `0.01883` in 4 bits directly. 4 bits hold 16 values, the integers -8 to 7. So llama.cpp cuts each row of weights into **blocks** of 32 and gives each block its own **scale** `d`. Each weight is stored as a small integer `q`, and read back as `q × d`.

Per block, the scale is chosen so the biggest weight fits the integer range. Small blocks matter: one huge weight only spoils the precision of its own 31 neighbours, not the whole row.

## Rebuild it in Python

`code/llamacpp/quant_blocks.py` is a line-by-line port of `quantize_row_q8_0_ref`, `quantize_row_q4_0_ref` and `dequantize_row_q4_0` from `ggml/src/ggml-quants.c`. The Q4_0 part:

```python
def quantize_q4_0(block):
    """32 floats -> 2-byte scale + 16 bytes of packed 4-bit numbers = 18 bytes."""
    amax, mx = 0.0, 0.0
    for v in block:  # keep the value with the largest size, sign included
        if amax < abs(v):
            amax, mx = abs(v), v
    d = mx / -8  # the biggest weight maps to -8, the end of the range -8..7
    inv = 1 / d if d else 0.0
    qs = bytearray(16)
    for j in range(16):
        xi0 = min(15, int(block[j] * inv + 8.5))
        xi1 = min(15, int(block[16 + j] * inv + 8.5))
        qs[j] = xi0 | (xi1 << 4)  # weight j in the low nibble, weight j+16 in the high one
    return struct.pack("<e", d) + bytes(qs)
```

Three details from the C code survive in the port:

- The scale is stored as a 16-bit float (`"<e"` in Python, `ggml_half` in C). That is why a block is 2 + 16 = 18 bytes.
- `+ 8.5` shifts -8..7 to 0..15 (stored without a sign) and rounds.
- Weight `j` and weight `j + 16` share a byte. Not `j` and `j + 1`. This order lets SIMD code unpack 16 values with one mask and one shift.

Run it:

```bash
python code/llamacpp/quant_blocks.py
```

Our output, on 32,768 random weights shaped like real ones (normal spread, standard deviation 0.02):

```text
32768 weights, 1024 blocks of 32

type   bytes/block  bits/weight  file size vs F16   RMS error
F16             64        16.00              100%    4.15e-06
Q8_0            34         8.50               53%    1.07e-04
Q4_0            18         4.50               28%    1.70e-03

First Q4_0 block:
  scale d = -0.006011962890625
  first 4 weights    [0.01883, -0.02793, -0.01359, 0.00741]
  after round trip   [0.01804, -0.03006, -0.01202, 0.00601]
  first packed byte  0x05 (low nibble = weight 0, high nibble = weight 16)
```

The **RMS error** is the typical size of the rounding error. Q8_0 is about 16 times more accurate than Q4_0, at almost twice the size. Note the "bits per weight" is 4.5, not 4: the scale costs 16 bits per 32 weights.

The script ends with the same size check that `ggml-common.h` does with `static_assert`: a Q8_0 block is 34 bytes, a Q4_0 block is 18.

## K-quants: blocks inside blocks

Q4_0 spends 16 bits of scale per 32 weights. **K-quants** (Q2_K to Q6_K) use **super-blocks** of 256 weights split into 8 sub-blocks of 32. Each sub-block gets a scale and a minimum stored in 6 bits, and the super-block has two 16-bit numbers that scale those. From `ggml-common.h`:

```c
// 4-bit quantization
// 8 blocks of 32 elements each
// weight is represented as x = a * q + b
// Effectively 4.5 bits per weight
typedef struct {
    ggml_half d;                   // super-block scale for quantized scales
    ggml_half dmin;                // super-block scale for quantized mins
    uint8_t scales[K_SCALE_SIZE];  // scales and mins, quantized with 6 bits
    uint8_t qs[QK_K/2];            // 4-bit quants
} block_q4_K;                      // 4 + 12 + 128 = 144 bytes per 256 weights
```

Same 4.5 bits per weight as Q4_0, but each sub-block has a **minimum** too (`x = a × q + b`), so a block whose weights are all positive does not waste half its range. The result is noticeably better quality at the same size.

**IQ types** (IQ2_XXS, IQ3_S, IQ4_XS, ...) go further with lookup tables of good value combinations. They reach 1.5 to 4 bits per weight, and the low-bit ones need an importance matrix (below).

## What the S, M and L mean: per-layer mixes

`Q4_K_M` is not one type. It is a **recipe**. `llama-quantize` decides per tensor, in `src/llama-quant.cpp`:

- Most weights get Q4_K.
- `attn_v` and `ffn_down` weights in some layers get **Q6_K**. Which layers is decided by `use_more_bits`:

```cpp
auto use_more_bits = [](int i_layer, int n_layers) -> bool {
    return i_layer < n_layers/8 || i_layer >= 7*n_layers/8 || (i_layer - n_layers/8)%3 == 2;
};
```

The first eighth of layers, the last eighth, and every third layer between them. Those tensors were found to hurt quality most when squeezed.

- The output layer (`output.weight`) usually gets Q6_K. Tensors with one dimension, such as norm weights, are never quantized (`ggml_n_dims(tensor) < 2` skips them).

`Q4_K_S` (small) bumps fewer tensors; `Q3_K_L` (large) bumps more. `--pure` turns the mixing off.

## Pick with numbers: the built-in table

Run `llama-quantize` with no arguments. It prints every type with a size and a quality cost measured on Llama 3 8B. From our build:

| Type | Size (8B) | Perplexity increase |
|---|---|---|
| Q2_K | 2.96G | +3.5199 |
| Q3_K_M | 3.74G | +0.6569 |
| Q4_0 | 4.34G | +0.4685 |
| Q4_K_S | 4.37G | +0.2689 |
| **Q4_K_M** | **4.58G** | **+0.1754** |
| Q5_K_M | 5.33G | +0.0569 |
| Q6_K | 6.14G | +0.0217 |
| Q8_0 | 7.96G | +0.0026 |
| F16 | 14.00G | +0.0020 (on Mistral 7B) |

**Perplexity** measures how surprised a model is by real text; lower is better. These numbers are the increase over the full-precision model. Read the table this way:

- Q4_K_M is the popular default because it is the knee of the curve: Q4_0 is barely smaller and almost 3 times worse.
- Q8_0 is close to lossless. Use it when it fits.
- Q2 and Q3 types are for when nothing else fits. The quality drop is large.

These are one model's numbers. Bigger models usually tolerate fewer bits better than small ones. Measure your own model on your own task.

## Quantize a model

```bash
llama-quantize model-F16.gguf model-Q4_K_M.gguf Q4_K_M
```

Always quantize from F16, BF16 or F32. Re-quantizing an already quantized file needs `--allow-requantize` and the tool warns it "can severely reduce quality". Other flags you may need: `--dry-run` (just print the final size), `--output-tensor-type` and `--token-embedding-type` (keep these two bigger), and `--tensor-type attn_q=q8_0` (override one tensor kind).

Our run on the tiny course model (7.4M parameters, from [lesson 4](lesson:llamacpp/train-convert-run)):

OUTPUT_QUANT

## Importance matrix: spend the bits where they count

Rounding errors matter more on weights that multiply big activations. An **importance matrix** (imatrix) records which weights those are, by running sample text through the model. The quantizer then rounds those weights more carefully.

```bash
llama-imatrix -m model-F16.gguf -f calibration.txt -o imatrix.gguf
llama-quantize --imatrix imatrix.gguf model-F16.gguf model-IQ3_M.gguf IQ3_M
```

The calibration text should look like what the model will see: your domain, your languages. A few hundred KB is typical. For the IQ1 and IQ2 types an imatrix is required; for Q4_K_M and above it is optional but usually helps a little.

## Check quality yourself

Two tools, from [benchmark and tune](lesson:llamacpp/benchmark-and-tune):

- `llama-perplexity -m model.gguf -f text.txt` gives one number per model. Compare quants on the same text.
- **KL divergence** compares the quantized model's whole probability distribution to the original's, token by token: run `llama-perplexity` on the F16 model with `--kl-divergence-base base.kld`, then on the quant with `--kl-divergence-base base.kld --kl-divergence`. It catches damage that perplexity averages away.

Neither replaces your own eval set. A quant that adds 0.1 perplexity can still break a specific skill, such as JSON formatting or a less common language.

:::check A Q4_0 block holds 32 weights in 18 bytes. Where do the extra 2 bytes beyond 16 go, and what does that do to bits per weight?
They hold the block's 16-bit scale. 18 bytes × 8 / 32 weights = 4.5 bits per weight, not 4.
:::

:::check Why do Q4_K_M and Q4_K_S differ in size if both are "4-bit K-quants"?
They are different recipes. Q4_K_M stores more tensors (some `attn_v` and `ffn_down` layers, picked by `use_more_bits`) in Q6_K. Q4_K_S bumps fewer. The base type is Q4_K in both.
:::

:::check You have a 70B model and room for 30 GB. The 4-bit file is 40 GB. What do you try, in order?
An imatrix plus a 3-bit K-quant or IQ3 type (about 30 GB), checked with perplexity or KL divergence against a higher-bit version, and then your own eval set. If quality fails, consider a smaller model at 4 bits instead. Often a smaller model at Q4_K_M beats a bigger one at Q2.
:::
