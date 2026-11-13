---
title: Evaluate before you ship, and gate the release
summary: Score the base model and the tuned one on the same hold-out questions, record the verdict on the training run, and stop the release with an exit code. Also LLaMA-Factory's own prediction path and why its eval command is gone.
time: 20 min
---

:::warn Not run
`evaluate.py` needs the adapter from the [tracked run](lesson:llamafactory/sft-with-mlflow-tracking), which we did not run. The code below is complete and its MLflow calls follow the pattern the [MLflow evaluation lesson](lesson:mlflow/evaluation-and-prompts) ran. No scores are shown, because we have none.
:::

Training loss going down tells you the model learned the training rows. It does not tell you the model got better at the job. For that you need questions it never saw, a score, and the same score for the model you started from.

## LLaMA-Factory's own options

- **`llamafactory-cli eval`** is gone in practice. At v0.9.5 it raises `NotImplementedError: Evaluation will be deprecated in the future.` Tutorials that run MMLU or C-Eval through it are out of date.
- **`do_predict`** still works. `examples/extras/nlg_eval/llama3_lora_predict.yaml` sets `do_predict: true` and `predict_with_generate: true` on an `eval_dataset`, writes the generated answers, and scores them with BLEU and ROUGE. Its own header warns: "The batch generation can be SLOW using this config", and it points to `scripts/vllm_infer.py` plus `scripts/eval_bleu_rouge.py` for speed. It needs `requirements/metrics.txt` (the [catalog](lesson:llamafactory/the-example-catalog) run failed without it).

BLEU and ROUGE count overlapping words with a reference answer. For "does it call itself Nori", word overlap is the wrong tool: "I'm Nori" and "My name is Nori" overlap little and are both right. So we write our own check.

## The check

`code/llamafactory/evaluate.py` asks each of the 9 hold-out questions to two models and scores the answers with two MLflow `@scorer` functions:

```python
@scorer
def says_nori(outputs) -> bool:
    return "Nori" in outputs

@scorer
def says_northwind(outputs) -> bool:
    return "Northwind" in outputs
```

The two models are the same base with and without the adapter, loaded through LLaMA-Factory's own `ChatModel`, so the template and its default system prompt match training exactly:

```python
base  = {"model_name_or_path": p["lf.model_name_or_path"], "template": p["lf.template"]}
adapter = mlflow.artifacts.download_artifacts(run_id=train.info.run_id, artifact_path="adapter")
tuned = {**base, "adapter_name_or_path": adapter, "finetuning_type": "lora"}
```

Three choices in those lines:

- **The model settings come from the run's params, not from a file on disk.** Whatever trained the adapter is what gets evaluated.
- **The adapter is downloaded from MLflow.** On a cluster each pipeline step runs in its own pod with its own disk, so a local path from the training step would not exist.
- **Generation is greedy** (`do_sample: False`), so a re-run gives the same answers and the same score.

Each model's answers go through `mlflow.genai.evaluate`, which stores one trace per question in the `nori-eval` experiment. A failing answer can be opened and read.

## The gate

```python
GATE = 0.8
passed = tuned_rate >= GATE and tuned_rate > base_rate
client.log_metric(train.info.run_id, "holdout_says_nori", tuned_rate)
client.log_metric(train.info.run_id, "holdout_says_nori_base", base_rate)
client.set_tag(train.info.run_id, "gate", "pass" if passed else "fail")
sys.exit(0 if passed else 1)
```

- **Two conditions.** An absolute bar (80%) and "better than where we started". Beating a base that scores 0% is not enough on its own.
- **The verdict goes on the training run**, as metrics and a `gate` tag, through `MlflowClient`. The client writes to a run by id whatever experiment it is in. The fluent `start_run` would refuse to resume a run from another experiment (the [tracking lesson](lesson:llamafactory/sft-with-mlflow-tracking) shows the error).
- **The exit code is the gate.** `register.py` only takes runs tagged `gate=pass`. In the [pipeline](lesson:llamafactory/pipeline-on-kubeflow), exit code 1 fails the step and the register step never starts. Kubeflow's local runner cannot run `dsl.If` branches, so a failing step is the gate that works everywhere.

With 9 questions, each one is 11 points. A one-question difference between two adapters is noise, as the [RAG measurement lesson](lesson:rag/measure-quality) says. The base score matters because the qwen template tells the model "You are Qwen, created by Alibaba Cloud" on every turn (see the [config lesson](lesson:llamafactory/anatomy-of-a-config)). We expect the base to fail almost every question, but we have not measured it.

One more line in the script: it removes `MLFLOW_RUN_ID` from its environment first. Kubeflow's MLflow plugin gives every step a run id, and `mlflow.start_run()` would quietly resume that run instead of creating the evaluation runs.

## Run it

```bash
python evaluate.py              # the newest run in nori-sft
python evaluate.py <run_id>     # a specific one
echo $?                         # 0 = pass, 1 = fail
```

To see the gate fail on purpose, train a run with `max_steps=1` and evaluate it. One step should not be enough to teach the name.

:::check The tuned model scores 9/9, the base 8/9. The gate passes. Should you ship?
Not on this evidence. The base already knew the answer, so the test does not separate them, and one question of difference is noise. Make the hold-out harder first.
:::

:::check Why does `evaluate.py` download the adapter from MLflow instead of reading `saves/nori/lora/sft`?
On a cluster the evaluation step runs in a different pod from training and cannot see its disk. MLflow is the one place both can reach, and it holds exactly the files the run produced.
:::
