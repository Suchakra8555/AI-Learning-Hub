---
title: The whole lifecycle on one page
summary: Every stage of the Nori run, which tool did it, and what makes it repeatable. A versioning table, the retrain loop, and a launch checklist.
time: 15 min
---

Twelve lessons built the path from a data file to a served, versioned endpoint. Some of it ran on our laptop and some was only built; each lesson says which. Here is the whole path on one page.

## The loop

```text
 data ──► train ──► evaluate ──► gate ──► register ──► serve ──► watch
  ▲                                │                               │
  │                              fail                              │
  └──────────── new rows, fixed rows, or a new base model ◄────────┘
```

| Stage | What happens | Tool | In this track |
|---|---|---|---|
| Data | Build rows, split, write `dataset_info.json` | Python, LLaMA-Factory's data formats | `make_dataset.py`, [lesson 5](lesson:llamafactory/your-own-data) |
| Train | LoRA SFT (or DPO, KTO) from one YAML | LLaMA-Factory | `train_tracked.py`, [lesson 6](lesson:llamafactory/sft-with-mlflow-tracking) |
| Track | Config, data digest, code and library versions, loss curve, adapter | MLflow Tracking | the same run |
| Evaluate | Base vs tuned on hold-out questions | LLaMA-Factory `ChatModel`, `mlflow.genai.evaluate` | `evaluate.py`, [lesson 9](lesson:llamafactory/evaluate-before-you-ship) |
| Gate | Stop unless the tuned model passes and beats the base | exit code 1 | `evaluate.py` |
| Register | Merge, log the folder, new version, `staging` alias | LLaMA-Factory `export`, MLflow Registry | `register.py`, [lesson 10](lesson:llamafactory/merge-register-and-version) |
| Promote | A person moves `champion` | MLflow Registry | `register.py promote` |
| Serve | OpenAI-style endpoint for `@champion` | `llamafactory-cli api`; KServe on a cluster | `call_api.py`, [lesson 11](lesson:llamafactory/serve-trace-and-shrink) |
| Watch | One trace per request | MLflow Tracing | `call_api.py` |
| Orchestrate | The same steps as one job, passing a run id | Kubeflow Pipelines | `pipeline.py`, [lesson 12](lesson:llamafactory/pipeline-on-kubeflow) |

## What versions what

A result is repeatable only if every input to it has a version you can look up. For the Nori model:

| Input | Its version | Where it is recorded |
|---|---|---|
| Our code | git commit, with `-dirty` if there were uncommitted changes | tag `git_commit` on the run |
| Libraries | LLaMA-Factory, transformers, PEFT, torch versions | tags `version.*` |
| Config | the YAML file, every key | artifact `config/`, params `lf.*` |
| Data | MLflow's digest of the rows, and the file's path | the run's dataset input, tag `data_digest` |
| Base model | Hugging Face repo name and commit sha | tags `base_model`, `base_model_revision` |
| Adapter | the files the run produced | artifact `adapter/` |
| Merged model | a registered model version | `nori` version N, with the tags above copied onto it |
| What is live | an alias | `nori@champion` |
| The pipeline | compiled YAML and the image tag | `nori_pipeline.yaml`, `nori-lf:0.9.5` |

Two of those are easy to forget. A model name such as `Qwen/Qwen2.5-0.5B-Instruct` is not a version: its owner can push new weights under the same name. The commit sha is the version. And "the data" is not the file name; it is the digest of the bytes, which is why [lesson 5](lesson:llamafactory/your-own-data) had to fix line endings first.

## Who changes what

- The pipeline may create runs and registered versions, and move `staging`.
- Only a person moves `champion`. A gate catches what you thought to test. A person reads the answers.
- Rollback is moving `champion` back to the previous version ([MLflow registry](lesson:mlflow/registry-and-aliases)). No retraining, no redeploy of serving code.

## When to retrain

Retrain when you have new information, not on a timer:

- **Watching shows a pattern.** Traces show a question type the model handles badly. Write corrected rows, add them, and the data digest changes.
- **The hold-out stops being hard.** If every candidate scores 100%, the test no longer tells you anything. Add harder questions before you train again.
- **A new base model.** A new revision is a different input. Run the whole loop again, base score included.

Each retrain is a new run with new tags. Compare it with the current champion's run the way the [MLflow track](lesson:mlflow/tracking-runs-and-search) compares runs.

## Launch checklist

- [ ] Base model pinned to a commit sha, not only a repo name.
- [ ] Data digest recorded, and stable across machines.
- [ ] Hold-out set kept out of training, with the check that proves it.
- [ ] Base model scored on the same hold-out, so "better" has a meaning.
- [ ] Gate fails closed: a crash or a missing score stops the release.
- [ ] The served model is loaded by alias, never by version number or file path.
- [ ] The system prompt at serving matches the one used in training (the [template lesson](lesson:llamafactory/anatomy-of-a-config)).
- [ ] Every request is traced, with a way to find the bad ones.
- [ ] Rollback tested once, before you need it.
- [ ] Anything not run is written down as not run.

## What you can now explain

If someone asks what an LLMOps pipeline for fine-tuning looks like, you can walk them through:
- a real one built from LoRA, SFT and DPO configs
- experiment tracking with data and code versions
- an evaluation gate
- a model registry with staging and champion aliases
- an OpenAI-compatible endpoint with tracing
- an orchestrated pipeline

You can also point to the parts that need GPUs, QLoRA, DeepSpeed and vLLM, and say how they would change it.

:::check A teammate says "we used the same model and the same data, but the new adapter is worse". Name two inputs from the versioning table that could still differ.
For example the base model revision (same repo name, new weights) and the library versions. The config or the code commit could also differ. The tags on both runs show which.
:::
