"""Build a tiny training file, split it, and check the split. Run: python training_data.py

Writes train.jsonl and holdout.jsonl next to this file. The hold-out set is never trained on.
It is how you spot a model that only memorised its examples.
"""
import json
import random
from pathlib import Path

# shortcut: 10 made-up rows. Real tuning needs far more, in your own style. OpenAI's guide suggests starting near 50.
ROWS = [{"messages": [{"role": "user", "content": f"Question {i}?"},
                      {"role": "assistant", "content": f"Answer {i}."}]} for i in range(10)]


def split(rows, holdout_share=0.2, seed=42):
    rows = rows[:]
    random.Random(seed).shuffle(rows)  # fixed seed so everyone gets the same split
    cut = round(len(rows) * holdout_share)
    return rows[cut:], rows[:cut]


def write_jsonl(path, rows):
    # bytes, not text: text mode writes \r\n on Windows, so the same rows would hash differently per OS
    path.write_bytes(("\n".join(json.dumps(r) for r in rows) + "\n").encode("utf-8"))


if __name__ == "__main__":
    train, holdout = split(ROWS)
    here = Path(__file__).parent
    write_jsonl(here / "train.jsonl", train)
    write_jsonl(here / "holdout.jsonl", holdout)
    print(f"train {len(train)}, holdout {len(holdout)}")
    assert not {json.dumps(r) for r in train} & {json.dumps(r) for r in holdout}, "rows leaked across the split"
    assert split(ROWS) == split(ROWS), "split must be repeatable"
