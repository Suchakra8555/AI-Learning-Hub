"""Train a tiny Llama-shaped model on this course's own lessons, on a CPU, and save it in
Hugging Face format. The next lessons convert it to GGUF, quantize it, and run it in llama.cpp.

Why train one? It walks the whole path a fine-tuned model takes, from training to llama.cpp,
on any laptop, with no download and no account. It also gives us a model we know every number of.

Install (CPU is fine):
    pip install torch transformers sentencepiece safetensors
Run from the repo root:
    python code/llamacpp/train_tiny_llama.py --out tiny-llama --steps 1500

It takes about 9 minutes on 4 CPU cores. The model is 7.4M parameters, so it writes
lesson-flavoured English that does not make sense. That is expected: we are testing the
plumbing, not the model.

shortcut: no validation split, no learning-rate warmup, one fixed sequence length.
Fine for a toy. For a real fine-tune see the LLMOps track.
"""
import argparse
import glob
import os
import time

import sentencepiece as spm
import torch
from transformers import LlamaConfig, LlamaForCausalLM

p = argparse.ArgumentParser()
p.add_argument("--out", default="tiny-llama")
p.add_argument("--steps", type=int, default=1500)
p.add_argument("--vocab", type=int, default=2000)
p.add_argument("--seq", type=int, default=128)
p.add_argument("--batch", type=int, default=32)
args = p.parse_args()
os.makedirs(args.out, exist_ok=True)
torch.manual_seed(0)

# 1. Text: every lesson in the course, front matter included. About 1 MB.
files = sorted(glob.glob("content/**/*.md", recursive=True))
text = "\n\n".join(open(f, encoding="utf-8").read() for f in files)
corpus = os.path.join(args.out, "corpus.txt")
open(corpus, "w", encoding="utf-8").write(text)
print(f"corpus: {len(files)} files, {len(text):,} characters")

# 2. Tokenizer: a SentencePiece BPE model, the same kind Llama 1 and 2 used.
#    byte_fallback means any character can be written as raw bytes, so nothing is "unknown".
spm.SentencePieceTrainer.train(
    input=corpus, model_prefix=os.path.join(args.out, "tokenizer"), vocab_size=args.vocab,
    model_type="bpe", byte_fallback=True, character_coverage=1.0,
    bos_id=1, eos_id=2, unk_id=0, pad_id=-1, minloglevel=2,
)
# llama.cpp's converter reads tokenizer.model directly, so no Hugging Face tokenizer class is needed.
sp = spm.SentencePieceProcessor(model_file=os.path.join(args.out, "tokenizer.model"))
ids = torch.tensor(sp.encode(text))
print(f"tokens: {len(ids):,} ({len(text) / len(ids):.1f} characters per token)")

# 3. Model: the Llama architecture, shrunk. 2 KV heads for 4 query heads = grouped-query attention.
cfg = LlamaConfig(
    vocab_size=args.vocab, hidden_size=256, intermediate_size=704, num_hidden_layers=4,
    num_attention_heads=4, num_key_value_heads=2, max_position_embeddings=512,
    rms_norm_eps=1e-5, rope_theta=10000.0, tie_word_embeddings=False,
    bos_token_id=1, eos_token_id=2,
)
model = LlamaForCausalLM(cfg)
print(f"parameters: {sum(t.numel() for t in model.parameters()) / 1e6:.1f}M")

# 4. Train: random windows of the token stream, predict the next token.
opt = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=0.01)
sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.steps)
start = time.time()
for step in range(1, args.steps + 1):
    starts = torch.randint(0, len(ids) - args.seq - 1, (args.batch,))
    x = torch.stack([ids[s : s + args.seq] for s in starts])
    loss = model(input_ids=x, labels=x).loss
    opt.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    opt.step()
    sched.step()
    if step % 100 == 0 or step == 1:
        print(f"step {step:5d}  loss {loss.item():.3f}  {time.time() - start:6.0f}s")

# 5. Save in Hugging Face format: config.json and model.safetensors, next to tokenizer.model.
model.save_pretrained(args.out)
model.eval()
prompt = torch.tensor([[1] + sp.encode("The KV cache")])  # 1 = BOS, as llama.cpp adds it
with torch.no_grad():
    out = model.generate(input_ids=prompt, max_new_tokens=30, do_sample=False)
print("greedy sample from PyTorch:", repr(sp.decode(out[0, 1:].tolist())))
print(f"saved to {args.out}/")
