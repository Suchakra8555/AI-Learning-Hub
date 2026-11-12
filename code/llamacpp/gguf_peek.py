"""Read a GGUF file's header, metadata and tensor list with only the standard library.

Run:
    python gguf_peek.py path/to/model.gguf       # any GGUF file
    python gguf_peek.py --demo                   # writes a tiny GGUF first, then reads it

The layout follows the comment at the top of llama.cpp's ggml/include/gguf.h (commit 0fb8f15):
magic "GGUF", version, tensor count, key-value count, the key-values, the tensor infos,
padding to the alignment, then one blob with all tensor data.

shortcut: the type table below lists the common tensor types only. Others print as "type N".
Look them up in enum ggml_type in ggml/include/ggml.h.
"""
import struct
import sys

# gguf_type in gguf.h: value types for metadata
SCALAR = {0: "<B", 1: "<b", 2: "<H", 3: "<h", 4: "<I", 5: "<i", 6: "<f", 7: "<?", 10: "<Q", 11: "<q", 12: "<d"}
STRING, ARRAY = 8, 9

# ggml_type in ggml.h: (name, weights per block, bytes per block)
GGML_TYPES = {
    0: ("F32", 1, 4), 1: ("F16", 1, 2), 2: ("Q4_0", 32, 18), 3: ("Q4_1", 32, 20),
    6: ("Q5_0", 32, 22), 7: ("Q5_1", 32, 24), 8: ("Q8_0", 32, 34),
    10: ("Q2_K", 256, 84), 11: ("Q3_K", 256, 110), 12: ("Q4_K", 256, 144),
    13: ("Q5_K", 256, 176), 14: ("Q6_K", 256, 210), 30: ("BF16", 1, 2),
}


class Reader:
    def __init__(self, f):
        self.f = f

    def take(self, fmt):
        size = struct.calcsize(fmt)
        return struct.unpack(fmt, self.f.read(size))[0]

    def string(self):
        n = self.take("<Q")
        return self.f.read(n).decode("utf-8", errors="replace")

    def value(self, t):
        if t in SCALAR:
            return self.take(SCALAR[t])
        if t == STRING:
            return self.string()
        if t == ARRAY:
            inner, n = self.take("<I"), self.take("<Q")
            return [self.value(inner) for _ in range(n)]
        raise ValueError(f"unknown gguf value type {t}")


def read_gguf(path):
    with open(path, "rb") as f:
        r = Reader(f)
        if f.read(4) != b"GGUF":
            raise ValueError("not a GGUF file (magic bytes are not 'GGUF')")
        version = r.take("<I")
        n_tensors, n_kv = r.take("<q"), r.take("<q")
        meta = {}
        for _ in range(n_kv):
            key = r.string()
            meta[key] = r.value(r.take("<I"))
        tensors = []
        for _ in range(n_tensors):
            name = r.string()
            dims = [r.take("<q") for _ in range(r.take("<I"))]
            ttype, offset = r.take("<i"), r.take("<Q")
            tensors.append((name, dims, ttype, offset))
        align = meta.get("general.alignment", 32)
        data_start = (f.tell() + align - 1) // align * align
    return version, meta, tensors, data_start


def tensor_bytes(dims, ttype):
    n = 1
    for d in dims:
        n *= d
    _, block, size = GGML_TYPES.get(ttype, ("?", 1, 0))
    return n // block * size


def show(path):
    version, meta, tensors, data_start = read_gguf(path)
    print(f"GGUF version {version}, {len(meta)} metadata keys, {len(tensors)} tensors, data starts at byte {data_start}\n")
    for k, v in meta.items():
        if isinstance(v, list):
            v = f"[{len(v)} items] {v[:5]}{' ...' if len(v) > 5 else ''}"
        print(f"  {k:<45} {v}")
    print(f"\n  {'tensor':<32}{'shape (ne0, ne1, ...)':<24}{'type':<7}{'bytes':>12}")
    total, by_type = 0, {}
    for name, dims, ttype, _ in tensors:
        nbytes = tensor_bytes(dims, ttype)
        tname = GGML_TYPES.get(ttype, (f"type {ttype}",))[0]
        total += nbytes
        by_type[tname] = by_type.get(tname, 0) + 1
        if len(tensors) <= 40 or name.startswith(("blk.0.", "token_embd", "output")):
            print(f"  {name:<32}{str(dims):<24}{tname:<7}{nbytes:>12,}")
    print(f"\n  tensor data: {total / 2**20:.1f} MiB, tensors by type: {by_type}")


def write_demo(path):
    """A two-tensor GGUF by hand. Not a model, just the container."""
    def s(x):
        b = x.encode()
        return struct.pack("<Q", len(b)) + b

    kvs = [
        s("general.architecture") + struct.pack("<I", STRING) + s("demo"),
        s("general.name") + struct.pack("<I", STRING) + s("hand-made"),
        s("demo.block_count") + struct.pack("<I", 4) + struct.pack("<I", 2),
        s("tokenizer.ggml.tokens") + struct.pack("<I", ARRAY) + struct.pack("<IQ", STRING, 3) + s("<s>") + s("hi") + s("!"),
    ]
    # tensor a: 4 x F32 at offset 0; tensor b: 32 x Q8_0 = one 34-byte block at offset 32 (aligned)
    infos = [
        s("a") + struct.pack("<I", 1) + struct.pack("<q", 4) + struct.pack("<iQ", 0, 0),
        s("b") + struct.pack("<I", 1) + struct.pack("<q", 32) + struct.pack("<iQ", 8, 32),
    ]
    head = b"GGUF" + struct.pack("<Iqq", 3, len(infos), len(kvs)) + b"".join(kvs) + b"".join(infos)
    head += b"\0" * (-len(head) % 32)
    data = struct.pack("<4f", 1, 2, 3, 4) + b"\0" * 16 + struct.pack("<e", 0.01) + bytes(range(32))
    with open(path, "wb") as f:
        f.write(head + data)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    target = sys.argv[1]
    if target == "--demo":
        target = "demo.gguf"
        write_demo(target)
    show(target)
