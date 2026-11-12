"""Q8_0 and Q4_0 quantization by hand, the way ggml does it. Run: python quant_blocks.py

This is a line-by-line port of quantize_row_q8_0_ref, quantize_row_q4_0_ref and
dequantize_row_q4_0 in llama.cpp's ggml/src/ggml-quants.c (commit 0fb8f15).
Standard library only. struct format "e" is a 16-bit float, the same as ggml_half.

shortcut: real ggml runs the dot product on the packed blocks with SIMD and never
unpacks a whole matrix to floats. Here we unpack to show the rounding error.
"""
import math
import random
import struct

QK = 32  # QK4_0 and QK8_0: one block holds 32 weights


def fp16(x):
    """Round a float to 16 bits and back, like GGML_FP32_TO_FP16 then FP16_TO_FP32."""
    return struct.unpack("<e", struct.pack("<e", x))[0]


def quantize_q8_0(block):
    """32 floats -> 2-byte scale + 32 signed bytes = 34 bytes."""
    amax = max(abs(v) for v in block)
    d = amax / 127
    inv = 1 / d if d else 0.0
    # C roundf rounds halves away from zero. Python's round() does not, so do it by hand.
    qs = [int(math.copysign(math.floor(abs(v * inv) + 0.5), v)) for v in block]
    raw = struct.pack("<e", d) + struct.pack("<32b", *qs)
    return raw


def dequantize_q8_0(raw):
    d = struct.unpack("<e", raw[:2])[0]
    return [q * d for q in struct.unpack("<32b", raw[2:34])]


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
        x0 = block[j] * inv
        x1 = block[16 + j] * inv
        xi0 = min(15, int(x0 + 8.5))  # C cast to int8 truncates toward zero
        xi1 = min(15, int(x1 + 8.5))
        qs[j] = xi0 | (xi1 << 4)  # weight j in the low nibble, weight j+16 in the high one
    return struct.pack("<e", d) + bytes(qs)


def dequantize_q4_0(raw):
    d = struct.unpack("<e", raw[:2])[0]
    out = [0.0] * 32
    for j, byte in enumerate(raw[2:18]):
        out[j] = ((byte & 0x0F) - 8) * d
        out[j + 16] = ((byte >> 4) - 8) * d
    return out


def rms_error(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))


if __name__ == "__main__":
    random.seed(0)
    # Real weights are small numbers centred on zero. A normal spread is a fair stand-in.
    weights = [random.gauss(0, 0.02) for _ in range(QK * 1024)]
    blocks = [weights[i : i + QK] for i in range(0, len(weights), QK)]

    print(f"{len(weights)} weights, {len(blocks)} blocks of {QK}\n")
    print(f"{'type':<6}{'bytes/block':>12}{'bits/weight':>13}{'file size vs F16':>18}{'RMS error':>12}")
    f16 = [fp16(w) for w in weights]
    print(f"{'F16':<6}{64:>12}{16.0:>13.2f}{'100%':>18}{rms_error(weights, f16):>12.2e}")
    for name, q, dq in (("Q8_0", quantize_q8_0, dequantize_q8_0), ("Q4_0", quantize_q4_0, dequantize_q4_0)):
        raws = [q(b) for b in blocks]
        back = [x for r in raws for x in dq(r)]
        size = len(raws[0])
        print(f"{name:<6}{size:>12}{size * 8 / QK:>13.2f}{size / 64:>18.0%}{rms_error(weights, back):>12.2e}")

    # One block, up close.
    b = blocks[0]
    raw = quantize_q4_0(b)
    print("\nFirst Q4_0 block:")
    print("  scale d =", struct.unpack("<e", raw[:2])[0])
    print("  first 4 weights   ", [round(x, 5) for x in b[:4]])
    print("  after round trip  ", [round(x, 5) for x in dequantize_q4_0(raw)[:4]])
    print("  first packed byte ", f"0x{raw[2]:02x}", "(low nibble = weight 0, high nibble = weight 16)")

    assert len(quantize_q8_0(b)) == 34 and len(raw) == 18  # matches the static_asserts in ggml-common.h
