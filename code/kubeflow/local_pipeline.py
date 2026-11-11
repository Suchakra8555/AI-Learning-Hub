"""Run the wine pipeline with no cluster.

Run (Linux, macOS, WSL, or inside a Linux container on Windows):  python local_pipeline.py
Needs: pip install -r requirements.txt   (kfp 2.18.0)
"""
from kfp import local

from wine_pipeline import wine

# shortcut: reuse this Python. DockerRunner isolates each task, but both runners fail on native Windows.
local.init(runner=local.SubprocessRunner(use_venv=False))

if __name__ == "__main__":
    run = wine(trees=20)
    print("pipeline output (accuracy):", run.output)
