"""Run LLaMA-Factory's own example configs on a CPU, with a tiny model, and print what passed.

The YAML files are not copied or edited. Each one runs as shipped, plus the same CPU overrides
on the command line. Run from this folder with the venv's Python:

    python run_examples.py            # all examples below
    python run_examples.py dpo kto    # only names containing these words

Needs: the v0.9.5 clone in vendor/LlamaFactory and `pip install -e vendor/LlamaFactory`.
"""
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent.resolve()
REPO = HERE / "vendor" / "LlamaFactory"
OUT = HERE / "saves" / "examples"
CLI = shutil.which("llamafactory-cli", path=str(Path(sys.executable).parent)) or "llamafactory-cli"

# The same overrides for every example: a 2-step run of a randomly initialised tiny Llama 3.
# shortcut: the tiny model proves the config runs, not that training helps. make_dataset.py + train_tracked.py do that.
CPU = [
    "model_name_or_path=llamafactory/tiny-random-Llama-3", "template=llama3", "trust_remote_code=true",
    "bf16=false", "pure_bf16=false",  # bf16 needs a recent GPU; a CPU trains in float32
    "max_steps=2", "max_samples=16", "cutoff_len=128", "logging_steps=1", "save_steps=1000",
    "preprocessing_num_workers=1", "dataloader_num_workers=0",  # worker processes are slow to start on Windows
    "report_to=none", "overwrite_output_dir=true",
]
ADAPTER = "adapter_name_or_path=llamafactory/tiny-random-Llama-3-lora"

# (name, file under examples/, extra overrides). Order follows examples/README.md.
EXAMPLES = [
    ("pretrain", "train_lora/qwen3_lora_pretrain.yaml", []),
    ("sft", "train_lora/qwen3_lora_sft.yaml", []),
    ("dpo", "train_lora/qwen3_lora_dpo.yaml", []),
    ("kto", "train_lora/qwen3_lora_kto.yaml", []),
    ("reward", "train_lora/qwen3_lora_reward.yaml", []),
    ("preprocess", "train_lora/qwen3_preprocess.yaml", [f"tokenized_path={OUT / 'tokenized'}"]),
    ("full-sft", "train_full/qwen3_full_sft.yaml", ["deepspeed=null"]),  # DeepSpeed ZeRO-3 needs GPUs
    ("loraplus", "extras/loraplus/llama3_lora_sft.yaml", []),
    ("pissa", "extras/pissa/llama3_lora_sft.yaml", []),
    ("oft", "extras/oft/llama3_oft_sft.yaml", []),
    ("dft", "extras/dft/qwen2_full_sft.yaml", []),
    ("eaft", "extras/eaft/qwen25_05b_eaft_full.yaml", []),
    ("muon", "extras/muon/qwen2_full_sft.yaml", []),
    ("galore", "extras/galore/llama3_full_sft.yaml", []),
    ("badam", "extras/badam/llama3_full_sft.yaml", []),
    ("apollo", "extras/apollo/llama3_full_sft.yaml", []),
    ("adam-mini", "extras/adam_mini/qwen2_full_sft.yaml", []),
    ("predict", "extras/nlg_eval/llama3_lora_predict.yaml", [ADAPTER]),
]
MERGE = ("merge", "merge_lora/qwen3_lora_sft.yaml",
         ["model_name_or_path=llamafactory/tiny-random-Llama-3", "template=llama3", ADAPTER])


def run(name, yaml, extra, command="train", overrides=CPU):
    args = [CLI, command, f"examples/{yaml}", *overrides, *extra]
    args.append(f"{'export_dir' if command == 'export' else 'output_dir'}={OUT / name}")
    start = time.time()
    # cwd is the clone: the YAMLs point at examples/deepspeed/... and data/ relative to it
    p = subprocess.run(args, cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace")
    errors = [l for l in (p.stderr + p.stdout).splitlines() if "Error" in l or "error:" in l]
    return p.returncode == 0, time.time() - start, (errors[-1].strip()[:110] if errors else "")


if __name__ == "__main__":
    picked = [e for e in EXAMPLES if not sys.argv[1:] or any(w in e[0] for w in sys.argv[1:])]
    results = [(n, y, *run(n, y, x)) for n, y, x in picked]
    if not sys.argv[1:] or "merge" in sys.argv[1:]:
        results.append((MERGE[0], MERGE[1], *run(*MERGE, command="export", overrides=[])))

    print(f"\n{'example':11} {'file':40} {'result':6} {'secs':>5}  last error line")
    for name, yaml, ok, secs, err in results:
        print(f"{name:11} {yaml:40} {'pass' if ok else 'FAIL':6} {secs:5.0f}  {'' if ok else err}")
    print(f"\n{sum(r[2] for r in results)} of {len(results)} passed")
