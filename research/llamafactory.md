# LLaMA-Factory: source notes for the fine-tuning track

Date of research: 2026-11-11 and 2026-11-12. Sources are the LLaMA-Factory repository at tag **v0.9.5** (cloned into `code/llamafactory/vendor/LlamaFactory`), its README, `examples/`, `data/README.md` and `src/`; the GitHub releases API and PyPI JSON for versions; the Hugging Face transformers source for the MLflow callback; and the MLflow v3.18.0 source for logging a local checkpoint. "Read" means the file was opened in this session, not summarized by a tool.

Note on the docs site: the official Chinese docs at https://llamafactory.readthedocs.io/zh-cn/latest/ were **not read**. A subagent sent to summarize them was stopped by a safety filter, so every fact below comes from the repository at the pinned tag. Where the README and the code disagree, the code wins and the disagreement is listed.

---

## 1. Versions

| Item | Value | Source |
|---|---|---|
| LLaMA-Factory release | v0.9.5, published 2026-05-30 | GitHub releases API |
| Earlier releases | v0.9.4 2025-12-31, v0.9.3 2025-06-16, v0.9.2 2025-03-11 | GitHub releases API |
| PyPI package | `llamafactory` 0.9.5, `requires_python >=3.11.0` | PyPI JSON |
| `main` vs tag | 87 commits ahead of v0.9.5 on 2026-11-11; core example files unchanged | GitHub compare API |
| Repo name | `hiyouga/LlamaFactory` (the welcome banner still prints `hiyouga/LLaMA-Factory`) | repo, `launcher.py` |
| Dependency pins at v0.9.5 | torch>=2.4.0; transformers >=4.55.0, <=5.6.0, not 4.52.0 or 4.57.0; datasets <=4.0.0; accelerate <=1.11.0; peft 0.18.x; trl <=0.24.0; gradio <=5.50.0 | `pyproject.toml` |
| What pip resolved for us (Windows 11, Python 3.12.4) | torch 2.15.0 (CPU wheel from PyPI), transformers 5.6.0, peft 0.18.1, trl 0.24.0, datasets 4.0.0, accelerate 1.11.0, gradio 5.50.0, mlflow 3.18.0 | `pip list` |

The README's "Requirement" table (torch 2.6.0 recommended, transformers 4.50.0 recommended, trl 0.9.6 recommended) is older than `pyproject.toml`. Trust the pins.

## 2. Commands

From `src/llamafactory/launcher.py` (read): `api`, `chat`, `eval`, `export`, `train`, `webchat`, `webui`, `env`, `version`, `help`. `lmf` is a shortcut for `llamafactory-cli`.

- `eval` raises `NotImplementedError("Evaluation will be deprecated in the future.")` at v0.9.5. The README still describes MMLU-style evaluation in places. Use `do_predict` instead (section 6).
- Arguments: if the first argument ends in `.yaml`/`.yml` (or `.json`), the file is loaded and every later `key=value` is merged on top with OmegaConf (`hparams/parser.py`, `read_args`). Otherwise the arguments are parsed as `--key value` flags.
- `USE_V1=1` switches to the new `llamafactory.v1` launcher (`examples/v1/` uses it). Not covered in the lessons.
- Distributed launch: `train` re-launches itself through `torchrun` when `FORCE_TORCHRUN=1` or more than one device is visible (and Ray and KTransformers are off). It reads `NNODES`, `NODE_RANK`, `NPROC_PER_NODE`, `MASTER_ADDR`, `MASTER_PORT`, plus `RDZV_ID`, `MIN_NNODES`, `MAX_NNODES`, `MAX_RESTARTS` for elastic jobs. `USE_RAY=1` uses Ray instead. `USE_MCA=1` forces torchrun.
- API server: `API_HOST` (default `0.0.0.0`), `API_PORT` (default `8000`), `API_KEY` (optional bearer check), `API_MODEL_NAME` (the id `/v1/models` returns, default `gpt-3.5-turbo`), `FASTAPI_ROOT_PATH`. Routes: `GET /v1/models`, `POST /v1/chat/completions` (streaming supported), `POST /v1/score/evaluation` (reward models only). `api/app.py`, read.

## 3. Configuration

Five argument groups come back from `get_train_args` (`train/tuner.py`, read): `model_args`, `data_args`, `training_args`, `finetuning_args`, `generating_args`. The classes live in `src/llamafactory/hparams/`:

- `ModelArguments` (`model_args.py`): base model, adapter path, `infer_backend` (huggingface, vllm, sglang, ktransformers), `infer_dtype`, quantization (`quantization_bit`, `quantization_method`), export (`export_dir`, `export_size`, `export_device`, `export_quantization_bit`, `export_quantization_dataset`, `export_legacy_format`, `export_hub_model_id`), vLLM, SGLang and KTransformers settings.
- `DataArguments` (`data_args.py`): `template`, `dataset`, `dataset_dir`, `cutoff_len` (default 2048), `val_size` (default 0.0), `default_system`, `enable_thinking`, `tokenized_path`.
- `TrainingArguments` (`training_args.py`): Hugging Face's `Seq2SeqTrainingArguments` plus Ray, profiler and FP8 settings.
- `FinetuningArguments` (`finetuning_args.py`): freeze, LoRA (`lora_rank`, `lora_alpha` default `lora_rank * 2`, `lora_dropout` default 0.0, `lora_target`, `loraplus_lr_ratio`, `use_dora`, `pissa_init`), OFT, RLHF (`pref_beta`, `pref_loss` in sigmoid, hinge, ipo, kto_pair, orpo, simpo), GaLore, APOLLO, BAdam, SwanLab, `plot_loss`.
- `GeneratingArguments` (`generating_args.py`): sampling settings for chat, api and predict.

Templates (`data/template.py`, read): the `qwen` template is ChatML and sets `default_system="You are Qwen, created by Alibaba Cloud. You are a helpful assistant."`. Every training row and every chat therefore gets that system prompt unless you set `default_system`. `extras/constants.py` maps `Qwen/Qwen2.5-0.5B-Instruct` to `template="qwen"`.

## 4. Data

From `data/README.md` and `data/dataset_info.json` (read):

- Every dataset you train on needs an entry in `dataset_info.json` inside `dataset_dir` (default `./data`). Sources: `file_name`, `hf_hub_url`, `ms_hub_url`, `script_url`, `cloud_file_name` (s3/gcs). File types: json, jsonl, csv, parquet, arrow.
- Two formats: **alpaca** (`instruction`, `input`, `output`, optional `system`, `history`) and **sharegpt** (a list of messages). For sharegpt, `columns` maps field names and `tags` maps role names. The defaults are `from`/`value`/`human`/`gpt`. OpenAI-style rows use `"tags": {"role_tag": "role", "content_tag": "content", "user_tag": "user", "assistant_tag": "assistant"}`, as the shipped `kto_en_demo` entry does.
- Preference data: `"ranking": true`, plus `chosen` and `rejected` columns, each a single assistant message. KTO data: a `kto_tag` column holding a boolean.
- In alpaca format the responses in `history` are also trained on.
- `identity.json` has 91 rows; 16 are English. Its answers contain `{{name}}` and `{{author}}` placeholders that you replace before training.

## 5. Tracking with MLflow

- Example YAMLs at v0.9.5 carry `report_to: none  # choices: [none, wandb, tensorboard, swanlab, mlflow]`.
- LLaMA-Factory's own `ReporterCallback` (`train/callbacks.py`, read) handles wandb, trackio and SwanLab (`use_swanlab`). It does **not** handle MLflow. `report_to: mlflow` goes straight to Hugging Face's `MLflowCallback`.
- `MLflowCallback` (transformers `integrations/integration_utils.py`, read at v4.57.1; check the 5.6 copy before quoting line numbers) reads `HF_MLFLOW_LOG_ARTIFACTS`, `MLFLOW_TRACKING_URI`, `MLFLOW_EXPERIMENT_NAME`, `MLFLOW_TAGS` (a JSON string), `MLFLOW_NESTED_RUN`, `MLFLOW_RUN_ID` ("When `MLFLOW_RUN_ID` environment variable is set, `start_run` attempts to resume a run with the specified run ID"), `MLFLOW_FLATTEN_PARAMS` and `MLFLOW_MAX_LOG_PARAMS`. `DISABLE_MLFLOW_INTEGRATION=TRUE` turns it off.
- The bridge to Kubeflow: KFP's MLflow plugin injects `MLFLOW_RUN_ID` (the task's nested run), `MLFLOW_TRACKING_URI` and `MLFLOW_EXPERIMENT_ID` into components (research/kubeflow.md K9). A LLaMA-Factory step inside such a pipeline therefore reattaches to its task's run.
- MLflow 3.18.0 `mlflow.transformers.log_model` accepts a local checkpoint directory as a string. It then requires `task` and `save_pretrained=True`. `save_local_checkpoint` copies the whole directory into the model's `model/` folder (`mlflow/transformers/__init__.py`, `model_io.py`, read). A merged LLaMA-Factory export, tokenizer included, therefore survives as a plain Hugging Face folder.

## 6. Evaluation

- `examples/extras/nlg_eval/llama3_lora_predict.yaml`: `do_predict: true`, `predict_with_generate: true`, `eval_dataset`. Its header says batch generation "can be SLOW" and points to `scripts/vllm_infer.py`.
- `scripts/eval_bleu_rouge.py` scores a predictions file; it needs `requirements/metrics.txt`.
- LLaMA-Factory's own tests run on CPU with `llamafactory/tiny-random-Llama-3`, the adapter `llamafactory/tiny-random-Llama-3-lora` and `REMOTE:llamafactory/demo_data`, for stages pt, sft, dpo, kto and rm. rm is marked xfail on Windows ("OS error"). `tests/e2e/test_train.py`, read.

## 7. Export and serving

- `export_model` (`train/tuner.py`, read) refuses to merge an adapter onto a quantized model ("Cannot merge adapters to a quantized model"). It also refuses to quantize while an adapter is attached ("Please merge adapters before quantizing the model"). With `infer_dtype: auto` a float32 model is saved in bfloat16 when the machine supports it.
- `examples/merge_lora/qwen3_lora_sft.yaml` starts with "DO NOT use quantized model or quantization_bit when merging lora adapters". `qwen3_gptq.yaml` shows export-time GPTQ quantization.
- `examples/inference/*.yaml` set `infer_backend: huggingface  # choices: [huggingface, vllm, sglang, ktransformers]`. README: `API_PORT=8000 llamafactory-cli api examples/inference/qwen3.yaml infer_backend=vllm vllm_enforce_eager=true`.
- Docker: the official image `hiyouga/llamafactory:latest` is "built on Ubuntu 22.04 (x86_64), CUDA 12.4, Python 3.11, PyTorch 2.6.0, and Flash-attn 2.7.4" (README). There is no CPU image. `docker/` has cuda, npu, rocm and xpu variants.

## 8. Hardware (README, "estimated")

| Method | Bits | 7B | 14B | 30B | 70B | xB |
|---|---|---|---|---|---|---|
| Full (bf16 or fp16) | 32 | 120GB | 240GB | 600GB | 1200GB | 18x GB |
| Full (pure_bf16) | 16 | 60GB | 120GB | 300GB | 600GB | 8x GB |
| Freeze/LoRA/GaLore/APOLLO/BAdam/OFT | 16 | 16GB | 32GB | 64GB | 160GB | 2x GB |
| QLoRA / QOFT | 8 | 10GB | 20GB | 40GB | 80GB | x GB |
| QLoRA / QOFT | 4 | 6GB | 12GB | 24GB | 48GB | x/2 GB |
| QLoRA / QOFT | 2 | 4GB | 8GB | 16GB | 24GB | x/4 GB |

Windows notes (README): install a CUDA build of PyTorch yourself; bitsandbytes for QLoRA needs a matching CUDA build; FlashAttention-2 must be compiled. Nothing in the README covers CPU-only training.

## 9. The examples folder at v0.9.5 (132 files)

`train_lora/` (pretrain, sft, sft .sh, sft with DeepSpeed ZeRO-3, sft with Ray, preprocess, dpo, kto, reward, plus vision-language sft and dpo), `train_qlora/` (on-the-fly bitsandbytes/HQQ/EETQ, GPTQ, AWQ, AQLM, bitsandbytes on Ascend NPU), `train_full/`, `merge_lora/`, `inference/`, `extras/` (adam_mini, apollo, asft, badam, dft, eaft, fp8, fsdp_qlora, galore, llama_pro, loraplus, mod, multi_tokens, muon, nlg_eval, oft, pissa, qoft), `deepspeed/` (ZeRO 0/2/3, offload, fp8 configs), `accelerate/` (FSDP and FSDP2 configs), `ascend/`, `ktransformers/`, `megatron/`, `megatron_bridge/`, `v1/`. The README says to run them from the repository root, because paths inside are relative to it.

## 10. What we ran (Windows 11, Python 3.12.4, CPU only)

- `llamafactory-cli env`: 53 s, versions as in section 1.
- `run_examples.py`, 19 official configs with a tiny random model: 13 passed (pretrain, sft, dpo, kto, reward, preprocess, full-sft with `deepspeed=null`, loraplus, pissa, oft, dft, eaft, merge). Five failed on missing optional packages (galore, badam, apollo, adam-mini; predict needs `requirements/metrics.txt`). Muon failed with "ValueError: I/O operation on closed file", not explained. After the packages were installed, the re-run of those six was stopped twice when the laptop ran low on memory, so they are unverified.
- Tiny-model facts: SFT loss 11.76 = ln(128,256), the vocabulary size; DPO loss 0.6931 = ln 2; KTO loss 0.5; the reward model writes `value_head.safetensors`; `lora_target: all` became the 7 linear layers; the merge wrote `model.safetensors`, the tokenizer and an Ollama `Modelfile`.
- `make_dataset.py`: 40 rows (16 from identity.json + 24 ours), train 28, hold-out 9, 6 DPO pairs. Text-mode writes on Windows produced CRLF (28 in 28 rows). After switching to bytes, the Docker build (Linux) printed the same digests as the laptop.
- Docker image `nori-lf:0.9.5`: built in 6 min 23 s, 2.52 GB.
- MLflow 3.18.0 behaviour, tested against a throwaway database: resuming a run while a different experiment is set fails ("active experiment ID does not match environment run ID"); resuming without `set_experiment` works; `start_run(run_name=...)` with `MLFLOW_RUN_ID` set renames the resumed run. In transformers 5.6, `run_name` defaults to `None`, and LLaMA-Factory only warns ("Consider setting --run_name ...").
- Not run: the real Qwen2.5-0.5B training, `evaluate.py`, `register.py`, `call_api.py`, `pipeline.py`, any GPU example, any cluster.

## 11. Gaps (UNVERIFIED)

1. Everything on the readthedocs site, including any guidance on MLflow, CPU training or Windows.
2. Settled by reading the code: the callback logs `args.to_dict()` (the trainer's arguments) plus the model config, so LLaMA-Factory's fine-tuning settings (LoRA rank, dataset, template) are not logged. `train_tracked.py` logs the YAML itself under `lf.`.
3. Whether the KFP MLflow plugin and Kubeflow Trainer's `torch-distributed` runtime set env vars that LLaMA-Factory's torchrun relaunch would conflict with. Not tested.
4. A supported CPU path for `infer_backend: vllm` in LLaMA-Factory. Not tested.
