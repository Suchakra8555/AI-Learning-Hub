"""Call the champion model through LLaMA-Factory's OpenAI-style API, and trace each call in MLflow.

Start the server first, in another terminal (from this folder, with the venv active):
  mlflow artifacts download -u models:/nori@champion -d saves/champion
  API_PORT=8000 API_MODEL_NAME=nori llamafactory-cli api vendor/LlamaFactory/examples/inference/qwen3.yaml \
      model_name_or_path=saves/champion/model template=qwen
  (That is Git Bash or WSL. In PowerShell set $env:API_PORT and $env:API_MODEL_NAME first.)
Run:  python call_api.py
"""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

import mlflow

HERE = Path(__file__).parent.resolve()
os.environ.setdefault("MLFLOW_TRACKING_URI", f"sqlite:///{HERE / 'mlflow.db'}")
BASE = "http://127.0.0.1:8000"


def call(path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


@mlflow.trace(span_type="LLM")
def ask(question):
    status, body = call("/v1/chat/completions", {
        "model": "nori", "temperature": 0, "max_tokens": 64,
        "messages": [{"role": "user", "content": question}]})
    if status != 200:
        raise RuntimeError(f"{status}: {body}")
    return body["choices"][0]["message"]["content"]


if __name__ == "__main__":
    mlflow.set_experiment("nori-serving")
    print("GET /v1/models", call("/v1/models"))
    for q in ["Who are you?", "Who built this assistant?", "How long do I have to return a tent?"]:
        start = time.time()
        answer = ask(q)
        print(f"[{time.time() - start:4.1f}s] {q}\n        {answer}")
    print("bad request:", call("/v1/chat/completions", {"model": "nori", "messages": []})[0])
    traces = mlflow.search_traces(return_type="list", max_results=3)
    print("traces stored:", len(traces), "| last trace span:", traces[0].data.spans[0].name)
