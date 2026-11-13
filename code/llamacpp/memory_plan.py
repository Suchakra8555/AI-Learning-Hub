"""Will this model fit? Weights + KV cache for a llama.cpp run. Run: python memory_plan.py

Weights take about (parameters x bits per weight / 8) bytes. The KV cache takes
2 (K and V) x layers x context x kv_heads x head_dim x bytes per number.
llama.cpp can store the cache in a smaller type with --cache-type-k / --cache-type-v
(f16 by default; q8_0 is a common choice). A quantized V cache needs flash attention on.

shortcut: this skips the compute buffer (scratch space for one batch, often a few hundred MiB)
and the OS. Leave 10-20% headroom. llama.cpp prints the real numbers when it loads a model:
look for "KV self size" / "llama_kv_cache" and "compute buffer size" lines.
"""

# Bytes per number for KV cache types: block bytes / block size, from ggml-common.h.
CACHE_BYTES = {"f32": 4.0, "f16": 2.0, "bf16": 2.0, "q8_0": 34 / 32, "q5_0": 22 / 32, "q4_0": 18 / 32}

# Approximate bits per weight for whole-model quant types (embeddings and output may differ).
WEIGHT_BITS = {"F16": 16.0, "Q8_0": 8.5, "Q6_K": 6.5625, "Q5_K_M": 5.7, "Q4_K_M": 4.9, "Q4_0": 4.5}


def kv_cache_bytes(n_layer, n_ctx, n_head_kv, head_dim, cache_type="f16"):
    return 2 * n_layer * n_ctx * n_head_kv * head_dim * CACHE_BYTES[cache_type]


def gib(b):
    return b / 2**30


if __name__ == "__main__":
    # Llama 3.1 8B shape, from its config.json: 32 layers, 8 KV heads (GQA), head_dim 128.
    params, n_layer, n_head_kv, head_dim = 8.03e9, 32, 8, 128

    print("Llama 3.1 8B weights by quant type (approximate):")
    for q, bits in WEIGHT_BITS.items():
        print(f"  {q:<7} {gib(params * bits / 8):5.1f} GiB")

    print("\nKV cache for the whole context (all slots share it):")
    print(f"  {'n_ctx':>7} {'f16':>9} {'q8_0':>9} {'q4_0':>9}")
    for n_ctx in (4096, 8192, 32768, 131072):
        row = [gib(kv_cache_bytes(n_layer, n_ctx, n_head_kv, head_dim, t)) for t in ("f16", "q8_0", "q4_0")]
        print(f"  {n_ctx:>7} " + " ".join(f"{x:8.2f}G" for x in row))

    # A server with 4 parallel slots and -c 32768 gives each slot 8192 tokens.
    total = params * WEIGHT_BITS["Q4_K_M"] / 8 + kv_cache_bytes(n_layer, 32768, n_head_kv, head_dim)
    print(f"\nQ4_K_M + 32768-token f16 cache: {gib(total):.1f} GiB before compute buffers")

    # Our tiny model from train_tiny_llama.py: 4 layers, 2 KV heads, head_dim 64.
    tiny = kv_cache_bytes(4, 512, 2, 64)
    print(f"tiny-llama, n_ctx 512, f16 cache: {tiny / 2**20:.2f} MiB")
    assert tiny == 1 * 2**20  # 2*4*512*2*64*2 bytes = exactly 1 MiB
