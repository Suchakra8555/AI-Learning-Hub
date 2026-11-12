"""Talk to llama-server with only the standard library. Run:

    llama-server -m tiny-llama-Q8_0.gguf -np 2 -c 1024 --metrics   # in one terminal (default port 9931)
    python server_client.py                                                   # in another

Set LLAMA_URL to point somewhere else, and LLAMA_API_KEY if the server was started with --api-key.
Works with any model. With the tiny course model the words are nonsense; the plumbing is the point.
"""
import json
import os
import time
import urllib.request

BASE = os.environ.get("LLAMA_URL", "http://127.0.0.1:9931")
KEY = os.environ.get("LLAMA_API_KEY")


def call(path, body=None, stream=False):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    if KEY:
        req.add_header("Authorization", f"Bearer {KEY}")
    resp = urllib.request.urlopen(req, timeout=120)
    if stream:
        return resp
    raw = resp.read().decode()
    return json.loads(raw) if raw.startswith(("{", "[")) else raw


def stream_chat(messages, **kw):
    """Server-sent events: lines that start with 'data: ', ending with 'data: [DONE]'."""
    resp = call("/v1/chat/completions", {"messages": messages, "stream": True, **kw}, stream=True)
    for line in resp:
        line = line.decode().strip()
        if not line.startswith("data: ") or line == "data: [DONE]":
            continue
        delta = json.loads(line[6:])["choices"][0]["delta"]
        yield delta.get("content") or ""


if __name__ == "__main__":
    print("1. health:", call("/health"))
    print("   model:", call("/v1/models")["data"][0]["id"])

    msgs = [{"role": "user", "content": "What is a KV cache?"}]
    t = time.time()
    r = call("/v1/chat/completions", {"messages": msgs, "max_tokens": 24, "temperature": 0})
    print("\n2. chat:", repr(r["choices"][0]["message"]["content"]))
    print("   usage:", r["usage"], f"in {time.time() - t:.2f}s")
    if "timings" in r:  # llama-server adds its own timing block next to the OpenAI fields
        tm = r["timings"]
        print(f"   prefill {tm['prompt_per_second']:.0f} tok/s, decode {tm['predicted_per_second']:.0f} tok/s")

    print("\n3. stream: ", end="")
    for piece in stream_chat(msgs, max_tokens=16, temperature=0):
        print(piece, end="|", flush=True)
    print()

    # The grammar engine forces the output to match a JSON schema, even from a model this small.
    schema = {"type": "object", "properties": {"answer": {"type": "string", "maxLength": 20}, "sure": {"type": "boolean"}},
              "required": ["answer", "sure"]}
    r = call("/v1/chat/completions", {"messages": msgs, "max_tokens": 64, "temperature": 0,
                                      "response_format": {"type": "json_schema", "json_schema": {"schema": schema}}})
    out = r["choices"][0]["message"]["content"]
    print("\n4. json_schema:", out, "->", "valid JSON" if json.loads(out) else "")

    toks = call("/tokenize", {"content": "llama.cpp runs GGUF models"})["tokens"]
    print("\n5. tokenize:", toks)
    print("   detokenize:", repr(call("/detokenize", {"tokens": toks})["content"]))

    print("\n6. slots:")
    for s in call("/slots"):
        print(f"   slot {s['id']}: n_ctx={s['n_ctx']} processing={s.get('is_processing')}")

    try:
        metrics = call("/metrics")
        print("\n7. metrics (first lines):")
        for line in [l for l in metrics.splitlines() if not l.startswith("#")][:4]:
            print("  ", line)
    except urllib.error.HTTPError as e:
        print("\n7. metrics: start the server with --metrics to enable", e.code)
