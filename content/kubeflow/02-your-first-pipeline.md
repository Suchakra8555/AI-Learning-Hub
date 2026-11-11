---
title: Your first pipeline, with no cluster
summary: Write three KFP components, join them into a pipeline, and run it locally. Includes what failed on Windows and the exact fix we used. Run on kfp 2.18.0.
time: 25 min
---

A **pipeline** is a list of steps where each step's output feeds the next. In Kubeflow Pipelines (KFP) each step is a **component**: a Python function that runs in its own container ([docs](https://www.kubeflow.org/docs/components/pipelines/)). Splitting steps this way lets you cache, retry and re-run one step without repeating the others.

## Three components

`code/kubeflow/wine_pipeline.py` makes data, fits a forest, and scores it:

```python
@dsl.component(base_image=BASE, packages_to_install=["scikit-learn", "pandas"])
def make_data(test_size: float, train: Output[Dataset], test: Output[Dataset]): ...

@dsl.component(base_image=BASE)
def fit(train: Input[Dataset], trees: int, model: Output[Model]): ...

@dsl.component(base_image=BASE)
def score(test: Input[Dataset], model: Input[Model], metrics: Output[Metrics]) -> float: ...

@dsl.pipeline(name="wine-pipeline")
def wine(trees: int = 50, test_size: float = 0.3) -> float:
    data = make_data(test_size=test_size)
    trained = fit(train=data.outputs["train"], trees=trees)
    result = score(test=data.outputs["test"], model=trained.outputs["model"])
    return result.outputs["Output"]
```

Two kinds of values pass between steps:

- **Parameters** are small things (numbers, strings). They arrive as normal function arguments.
- **Artifacts** are files. `Output[Dataset]` gives the function a path at `train.path`. Write the file there, and KFP stores it and hands the same file to the next step as `Input[Dataset]`. Types include `Dataset`, `Model`, `Metrics` and `ClassificationMetrics`.

Imports go **inside** the function. Each component runs alone in a fresh container, so the code at the top of the file is not there.

:::warn One lookup that failed
A task with an `Output[Metrics]` and a return value has two outputs, so `result.output` raises `AttributeError: The task has multiple outputs. Please reference the output by its name`. Use `result.outputs["Output"]`. The return value is named `Output`.
:::

:::tip Set the base image yourself
Without `base_image`, the SDK uses `python:3.11` and prints a warning that the default moves to 3.12 on 2027-10-01.
:::

## Run it locally

```python
from kfp import local
from wine_pipeline import wine

local.init(runner=local.SubprocessRunner(use_venv=False))
run = wine(trees=20)
print(run.output)
```

`SubprocessRunner` runs each component as a subprocess. `DockerRunner` runs each one in its container, which is closer to a real cluster. The docs say only the Docker runner handles every component type, and loops, branches and exit handlers do not run locally yet.

### On Windows, both runners failed

We tried both on Windows 11 with Python 3.12.

- `SubprocessRunner` failed in the first task: `sh: ... python.exe: command not found`. KFP builds a shell command from the Windows path `C:\Users\...\python.exe`, and `sh` swallows the backslashes.
- `DockerRunner` failed with `mount denied ... too many colons`. It builds a volume string from `E:\...` and the drive letter's colon breaks it.

We did not find either problem in the docs. The fix we used was to run the script inside a Linux container:

```bash
docker run --rm -v "$(pwd -W):/work" -w /work python:3.12-slim \
  sh -c "pip install -q -r requirements.txt && python local_pipeline.py"
```

(`pwd -W` is Git Bash; use `%cd%` in cmd.) WSL does the same job.

## The result

Inside the container, all three tasks finished with `SUCCESS`:

```text
Task 'score' outputs:
    Output: 1.0
    metrics: Metrics( name='metrics', ... metadata={'accuracy': 1.0} )
Pipeline 'wine-pipeline' finished with status SUCCESS
pipeline output (accuracy): 1.0
```

Accuracy 1.0 on 54 test rows is a toy result, as with the [MLflow lesson](lesson:mlflow/tracking-runs-and-search). It took about 2.5 minutes, mostly installing packages.

## Compile to YAML

```python
compiler.Compiler().compile(wine, "wine_pipeline.yaml")
```

That wrote 239 lines of YAML. It is the **intermediate representation**: the pipeline's real definition. It names the image (`python:3.12`) for each step. A cluster never sees your Python, only this file.

:::check Why must a component import its libraries inside the function?
Each component runs by itself in a container that has only the function's code, not the rest of your file.
:::
