# MLflow: source research for a multi-lesson track

Date of research: 2026-11-11. Sources are the official MLflow docs (mlflow.org/docs/latest, both the "Machine Learning" and the "LLMs & Agents" trees, plus the Self-Hosting tree and the API reference), the MLflow GitHub releases (github.com/mlflow/mlflow, read through the GitHub releases API), and PyPI (pypi.org/pypi/mlflow/json). "Read" means the page was fetched in this session. Items marked UNVERIFIED were not confirmed on a fetched official page.

Note on method: most pages were read through a fetch tool that returns summaries made by a small model. That tool can shorten or reword code. A few pages were also read as raw HTML with curl (the Span concept page, the Tracking overview, the CLI reference, the Kubernetes redirect, the docker-compose README and the release notes bodies). Quotes are short. Copy any code from the live page and run it before it goes into a lesson.

Note on doc drift: the MLflow docs are large and not fully in sync. Several pages contradict each other or describe older behaviour. Every conflict I found is listed in the section where it matters and again in "Version and deprecation notes" at the end.

---

## 0. Version snapshot

**Plain explanation.** MLflow ships a new minor version about once a month. The current major line is 3.x. MLflow 3 came out in June 2025. The newest release is 3.18.0.

**Documented facts.**
- Current version on PyPI: **mlflow 3.18.0**. `requires_python` is `>=3.10`. (PyPI JSON, read.)
- PyPI upload time of the 3.18.0 wheel: 2026-11-03T23:46:06Z. GitHub release published 2026-11-04T06:51Z. So the release date is **2026-11-04** (GitHub) / 2026-11-03 UTC (PyPI upload).
- PyPI extras for 3.18.0 (read from `requires_dist`): `genai` and `gateway` (both pull fastapi, uvicorn, slowapi, tiktoken, boto3, watchfiles), `auth` (Flask-WTF), `databricks` (databricks-agents, cloud storage clients), `extras` (pyarrow, boto3, google-cloud-storage, azureml-core, pysftp, kubernetes, prometheus-flask-exporter). The docs also use `mlflow[mcp]` (MCP server page). There is **no** `mlserver` extra in 3.18.0.
- Separate packages named in docs: `mlflow-tracing` (lightweight tracing SDK), `mlflow-skinny` UNVERIFIED (not seen on a fetched page this session). A TypeScript SDK has its own GitHub releases (`ts/v0.2.0`, 2026-05-15).
- Release history (GitHub releases API, read):

| Version | Published (UTC) | Notes from release notes |
|---|---|---|
| 3.18.0 | 2026-11-04 | Issue detection, Skill Registry (exp.), online eval with job containers, `compare_evaluations` (exp.) |
| 3.17.2 / 3.17.1 / 3.17.0 | 2026-10-21 / 10-13 / 10-07 | Fine-grained RBAC (sub-resource tiers, DENY), trace analytics rollups |
| 2.11.5 | 2026-09-23 | A 2.x patch release (content not read) |
| 3.16.1 / 3.16.0 | 2026-09-17 / 09-04 | not read |
| 3.15.2 / 3.15.1 / 3.15.0 | 2026-08-26 / 08-03 / 07-31 | MCP Registry, presigned artifact transfers |
| 3.14.0 | 2026-06-17 | not read |
| 3.13.0 | 2026-06-01 | RBAC, Helm chart, MLServer removed, file store errors by default |
| 3.12.0 | 2026-05-05 | not read |
| 3.11.1 | 2026-04-08 | not read |
| 3.10.0 | 2026-02-20 | Workspaces ("organization support"), `migrate-filestore`, demo experiment |
| 3.9.0 | 2026-01-29 | not read |
| 3.8.0 | 2025-12-22 | not read |
| 3.7.0 | 2025-12-05 | **SQLite becomes the default backend** |
| 3.6.0 | 2025-11-08 | not read (docs say OTLP ingestion is 3.6.0+) |
| 3.5.0 | 2025-10-16 | Security middleware, `optimize_prompts`, Claude Code tracing |
| 3.4.0 | 2025-09-17 | not read (docs say `make_judge` is 3.4.0+) |
| 3.1.0 | 2025-06-10 | "MLflow 3" launch notes; v3.0.0 tag (2025-06-11) points to these |

**Official URLs read.**
- https://pypi.org/pypi/mlflow/json and https://pypi.org/pypi/mlflow/3.18.0/json
- https://github.com/mlflow/mlflow/releases and https://api.github.com/repos/mlflow/mlflow/releases
- https://github.com/mlflow/mlflow/releases/tag/v3.18.0, v3.13.0, v3.1.0, v3.5.0, v3.7.0, v3.10.0, v3.15.0, v3.17.0

**Gaps / UNVERIFIED.**
- The pypi.org HTML page did not render for the fetch tool; I used the PyPI JSON API instead.
- Release notes for 3.4, 3.6, 3.8, 3.9, 3.11, 3.12, 3.14, 3.16 were not read.
- Why a 2.11.5 release appeared in 2026 is not known (UNVERIFIED; probably a security backport).

---

## 1. What MLflow is now

**Plain explanation.** MLflow is an open-source platform for building, testing and running AI. It started as a tool for classic machine learning: log experiments, save models, serve them. Since MLflow 3 it puts equal weight on LLM apps and agents: tracing, evaluation with LLM judges, prompt management and an AI Gateway. The docs are split into two trees, one for each audience. You can run MLflow yourself, or use a managed version from Databricks and other clouds.

**Documented facts.**
- The docs landing page offers two tracks: **LLMs & Agents** (`/docs/latest/genai/`) and **Machine Learning** (`/docs/latest/ml/`). There is also a third tree, **Self-Hosting** (`/docs/latest/self-hosting/`), and an API Reference.
- Site title: "MLflow AI Platform". The ML overview calls MLflow "the largest open source AI engineering platform for agents, LLMs, and ML models". The GenAI overview calls it an open-source "AI engineering platform for agents and LLMs".
- Each track offers two paths: "Open Source" (mlflow.org) and "MLflow on Databricks" (docs.databricks.com).
- Classic ML components named on the ML overview: Tracking and experiments, Model Registry, Model deployment, ML library integrations (scikit-learn, XGBoost, TensorFlow, PyTorch, Keras, Spark MLlib), Model evaluation.
- GenAI components named on the GenAI overview: Tracing (observability, OpenTelemetry-compatible), Evaluation & Monitoring (LLM judges), Prompt Management & Optimization, AI Gateway. "More Features": Version Tracking, Packaging & Deployment, Skill Registry, MCP Registry, Agent Serving. References: MLflow MCP Server.
- Architecture (Self-Hosting > Architecture overview): MLflow SDK (Python, TypeScript, Java, R), Backend Store, Artifact Store, Tracking Server (FastAPI; serves the UI and REST API; "optional for local development").
- Managed options named on the Self-Hosting overview: Databricks, AWS SageMaker, Azure Machine Learning, Nebius, GCP (GKE).
- Fastest start for GenAI: `uvx mlflow demo` (no server needed per the GenAI overview) or the "Start Demo" button in the UI. `mlflow demo` has `--port`, `--tracking-uri`, `--no-browser`, `--debug`, `--refresh` (CLI reference).
- The 3.10 release notes say the UI has a "workflow type selector" to switch between GenAI and Classical ML views.

**Official URLs read.**
- https://mlflow.org/docs/latest/
- https://mlflow.org/docs/latest/ml/
- https://mlflow.org/docs/latest/genai/
- https://mlflow.org/docs/latest/self-hosting/
- https://mlflow.org/docs/latest/self-hosting/architecture/overview/

**Gaps / UNVERIFIED.**
- No single official "components" page was found; the footer "Components" link goes to the mlflow.org home page.
- A feature-by-feature comparison of open source vs Databricks managed MLflow was not found. Only scattered notes (for example two judges that are Databricks-only, see section 8).

---

## 2. Tracking (experiments, runs, logging, autolog, search, datasets)

**Plain explanation.** An experiment is a folder for related work. A run is one execution of your code, such as one training job. Inside a run you log parameters (settings), metrics (numbers that can change by step), tags (labels) and artifacts (files). MLflow 3 adds a "logged model" with its own ID, so a run can produce many model checkpoints and each metric can point at a model and a dataset. Autologging records all of this for popular libraries with one line. You can search runs with a small SQL-like filter language.

**Documented facts.**
- Concepts (Tracking overview): Runs = "executions of some piece of data science code"; Experiments group runs and models; Models (Logged Models) have their own metadata and artifacts.
- Fluent API calls named on the Tracking API page: `mlflow.start_run()` (context manager, `run_name=`, `nested=True`, `log_system_metrics=`), `end_run(status="FINISHED")`, `active_run()`, `last_active_run()`, `log_param`, `log_params`, `log_metric(key, value, step=, timestamp=)`, `log_metrics(dict, step=)`, `set_tag`, `set_tags`, `log_artifact(path)`, `log_artifacts(dir)`, `log_input(dataset, context=)`.
- Metric `step` must be a 64-bit integer; steps may be negative, out of order, or have gaps. `timestamp` is in milliseconds.
- `mlflow.note.content` tag holds the run note shown in the UI.
- Nested runs: child runs get the system tag `mlflow.parentRunId`; query with `"tags.mlflow.parentRunId = '<id>'"`.
- Multiprocessing: set the tracking URI and experiment inside each process (spawn start method).
- Experiment setup: `mlflow.create_experiment(name, artifact_location="s3://...")`, `mlflow.set_experiment(name)`. The tracing quickstart notes `set_experiment` takes a name positionally and `experiment_id=` as a keyword.
- MLflow 3 checkpoints (Tracking overview, raw HTML read): `mlflow.pytorch.log_model(pytorch_model=model, name=f"checkpoint-epoch-{epoch}", step=epoch, input_example=...)` returns `model_info.model_id`. Then `mlflow.log_metric(key="accuracy", value=..., step=epoch, model_id=model_info.model_id, dataset=validation_dataset)` links the metric to that checkpoint and dataset.
- `mlflow.search_logged_models(experiment_ids=[...], filter_string=..., datasets=[{"dataset_name":..., "dataset_digest":...}], order_by=[{"field_name": "metrics.f1_score", "ascending": False}], max_results=, output_format="pandas"|"list")`. Default output is pandas. Docs warn: do not search over more than 10 experiments. `name` supports only `=`, `!=`, `IN`, `NOT IN`. `source_run_id='<id>'` works as a filter. Load the winner with `mlflow.pyfunc.load_model(f"models:/{best.model_id}")`.
- `MlflowClient().search_runs(experiment_id, order_by=["metrics.val_loss ASC"], max_results=1)` (Tracking overview example).
- Async logging for fluent APIs: `MLFLOW_ENABLE_ASYNC_LOGGING` ("mlflow.log_metric will log asynchronously"); `MLFLOW_ASYNC_LOGGING_THREADPOOL_SIZE` default 10 (environment variables reference).
- **Autologging** (Autolog page): `mlflow.autolog()` turns on autologging for every supported library that is installed. Per-library: `mlflow.tensorflow.autolog()` (tensorflow>=2.3), `mlflow.lightgbm.autolog()`, `mlflow.paddle.autolog()`, `mlflow.pyspark.ml.autolog()`, `mlflow.pytorch.autolog()` (PyTorch Lightning only), `mlflow.sklearn.autolog()`, `mlflow.spark.autolog()` (datasource info only), `mlflow.statsmodels.autolog()`, `mlflow.xgboost.autolog()`. Arguments shown: `log_model_signatures`, `extra_tags`, `disable`. Spark datasource autolog with PySpark 3.2.0+ needs `PYSPARK_PIN_THREAD=false`.
- **System metrics** (System Metrics page): enable with `MLFLOW_ENABLE_SYSTEM_METRICS_LOGGING=true`, `mlflow.enable_system_metrics_logging()`, or `start_run(log_system_metrics=True)` (per-run setting overrides global). Needs `psutil`; NVIDIA GPU needs `nvidia-ml-py`; AMD needs `pyrsmi`. Metric names are prefixed `system/`: `cpu_utilization_percentage`, `system_memory_usage_megabytes`, `system_memory_usage_percentage`, `gpu_utilization_percentage`, `gpu_memory_usage_megabytes`, `gpu_memory_usage_percentage`, `gpu_power_usage_watts`, `gpu_power_usage_percentage`, `network_receive_megabytes`, `network_transmit_megabytes`, `disk_usage_megabytes`, `disk_available_megabytes`. Sampled "every 10 seconds" by default. Tune with `MLFLOW_SYSTEM_METRICS_SAMPLING_INTERVAL` / `mlflow.set_system_metrics_sampling_interval()` and `MLFLOW_SYSTEM_METRICS_SAMPLES_BEFORE_LOGGING` / `mlflow.set_system_metrics_samples_before_logging()`.
- **`search_runs` filter syntax** (Search Runs page):
  - Prefixes: `metrics.`, `params.`, `tags.` (system tags under `mlflow.`), `attributes.`, `datasets.` (only `datasets.name`, `datasets.digest`, `datasets.context`).
  - Field names with special characters: backticks (`` metrics.`f1 score` ``) or double quotes. Values: single or double quotes. Params and tags are strings, so `params.batch_size = "2"`.
  - Numeric operators `= != > >= < <=`. String operators `= != LIKE ILIKE`. `IS NULL` / `IS NOT NULL` only for tags and params. `IN` only for `datasets.*` and `attributes.run_id`, with single-quoted values.
  - "the `OR` keyword is not supported"; use `AND`.
  - Python args: `filter_string`, `experiment_names=[...]`, `search_all_experiments=True`, `run_view_type=ViewType.ACTIVE_ONLY|ALL`, `order_by=["metrics.accuracy DESC"]`, `max_results`. Default order: start_time DESC, then run_id ASC.
  - Examples: `metrics.loss > 0.8`, `params.model LIKE "GPT%" AND params.batch_size = "2"`, `tags.task IS NULL`, `attributes.start_time >= 1664067852747`, `datasets.context = "train"`.
- **Datasets** (`mlflow.data`, Datasets page): `mlflow.data.from_pandas(df, targets="quality")`, `from_spark` (also Delta tables via `delta://` source). Types listed include NumpyDataset, HuggingFaceDataset, `MetaDataset` (lineage without data). Dataset properties: `name` (default "dataset"), `digest`, `source`, `schema`, `profile`. `mlflow.data.get_source()` and `load()` fetch the data. Log with `mlflow.log_input(dataset, context="training")`. Context labels are free-form. `from_pandas(..., predictions=...)` lets `mlflow.models.evaluate` run without a model.

**Official URLs read.**
- https://mlflow.org/docs/latest/ml/tracking/
- https://mlflow.org/docs/latest/ml/tracking/tracking-api/
- https://mlflow.org/docs/latest/ml/tracking/autolog/
- https://mlflow.org/docs/latest/ml/tracking/system-metrics/
- https://mlflow.org/docs/latest/ml/search/search-runs/
- https://mlflow.org/docs/latest/ml/search/search-models/
- https://mlflow.org/docs/latest/ml/dataset/
- https://mlflow.org/docs/latest/ml/getting-started/quickstart/
- https://mlflow.org/docs/latest/api_reference/python_api/mlflow.environment_variables.html

**Gaps / UNVERIFIED.**
- `log_dict`, `log_figure`, `log_image`, `log_table`, `log_text` are not on the Tracking API page. The 3.18.0 notes mention `mlflow.log_image` and `log_table` exist (bug fixes), but their signatures were not read.
- Python `MlflowClient` logging methods (`log_param`, `log_metric`, `log_batch`) were not shown on a fetched page (only Java). UNVERIFIED for Python signatures.
- `start_run(parent_run_id=...)` is not documented on the fetched page.
- `search_runs(output_format=...)` is not documented on the Search Runs page. `max_results` default not stated.
- Full `mlflow.autolog()` argument list and defaults (`log_models`, `log_input_examples`, `log_datasets`, `exclusive`, `silent`) are only in the API reference, not read.
- The autolog page says its example disables "model checkpoints" but the code sets `log_model_signatures=False`. Page error.
- The Search Logged Models page contradicts itself on tag filters (one section says tags are not supported, another says use `tags.`).
- Default value of `MLFLOW_SYSTEM_METRICS_SAMPLES_BEFORE_LOGGING` not stated.

---

## 3. Tracking server and storage architecture

### 3a. Stores, defaults and the `mlflow server` command

**Plain explanation.** MLflow keeps two kinds of data. Small metadata (runs, params, metrics, traces) goes to the backend store, which is a database. Big files (models, images) go to the artifact store, which is a folder or a cloud bucket. The tracking server is a web app that sits in front of both and serves the UI and the REST API. Since MLflow 3.7 the default backend is a local SQLite file called `mlflow.db`, not the old `./mlruns` folder.

**Documented facts.**
- Default backend: `sqlite:///mlflow.db` in the current directory. Self-Hosting overview: "Since MLflow 3.7.0, the default backend is SQLite", replacing `./mlruns`. 3.7.0 release notes: "SQLite is now the default backend for the MLflow Tracking server." Existing `./mlruns` data is detected and used automatically.
- Backend store URI forms (Backend Store page): `file:/my/local/dir`; `<dialect>+<driver>://<username>:<password>@<host>:<port>/<database>` with dialects `mysql`, `mssql`, `sqlite`, `postgresql`; `https://my-server:5000`; `databricks` or `databricks://<profileName>`. Set via `MLFLOW_TRACKING_URI`, `mlflow.set_tracking_uri()`, or `--backend-store-uri`.
- `MLFLOW_TRACKING_URI` default is `None` (env var reference).
- Model Registry "requires a database-backed store".
- Documented scenarios (Architecture overview): (1) localhost default, solo; (2) local tracking with a local database, solo; (3) remote tracking server for teams, with proxied artifact access and access control.
- `mlflow server` options (CLI reference, read in full for this command):

| Option | Default |
|---|---|
| `--backend-store-uri` | `sqlite:///mlflow.db`; uses `./mlruns` if an existing store is present |
| `--read-replica-backend-store-uri` | none (reads go to the backend store) |
| `--registry-store-uri` | same as backend store |
| `--default-artifact-root` | `mlflow-artifacts:/` when serving artifacts, otherwise `./mlruns` |
| `--serve-artifacts` / `--no-serve-artifacts` | serve (proxy) = `True` |
| `--artifacts-destination` | `./mlartifacts` |
| `--artifacts-only` | `False` |
| `--artifacts-presigned-only` | `False` |
| `-h, --host` | `127.0.0.1` ("not a security control") |
| `-p, --port` | `5000` |
| `-w, --workers` | `4` |
| `--static-prefix` | none |
| `--allowed-hosts` | localhost plus private IPs |
| `--cors-allowed-origins` | localhost origins on any port |
| `--disable-security-middleware` | off |
| `--x-frame-options` | `SAMEORIGIN` |
| `--uvicorn-opts`, `--gunicorn-opts`, `--waitress-opts` | none (uvicorn used by default) |
| `--dev` | `False`; not on Windows; not with gunicorn/uvicorn opts |
| `--expose-prometheus <dir>` | off; enables `/metrics` |
| `--app-name` | `mlflow.server:app`; options `basic-auth`, `custom_app` |
| `--trace-archival-config` | none (also `MLFLOW_TRACE_ARCHIVAL_CONFIG`) |
| `--secrets-cache-ttl` | `60` s (range 10-300) |
| `--secrets-cache-max-size` | `1000` (range 1-10000) |
| `--workspace-store-uri` | backend store URI |
| `--enable-workspaces` / `--disable-workspaces` | `False` |

- Most options have `MLFLOW_*` env equivalents (`MLFLOW_HOST`, `MLFLOW_PORT`, `MLFLOW_BACKEND_STORE_URI`, ...).
- Example commands (Tracking Server page):
  - `mlflow server --backend-store-uri postgresql://username:password@host:port/database`
  - `mlflow server --host 0.0.0.0 --port 8885 --artifacts-destination s3://my-bucket` (proxied artifacts)
  - `mlflow server --no-serve-artifacts --default-artifact-root s3://my-bucket` (clients write to S3 directly)
  - `mlflow server --artifacts-only ...` (artifact-only instance; tracking endpoints return errors)
  - `mlflow server --uvicorn-opts "--timeout-keep-alive=120"` (long uploads)
- Proxied artifacts: the server holds the cloud credentials, so users get "assumed role of access to all artifacts" the server can reach. Without proxying, each client needs its own storage credentials.
- The Tracking Server page recommends a reverse proxy (NGINX or Apache httpd) or a VPN for TLS and auth.
- Static prefix (MLflow 3 migration guide): since 3.12, `--static-prefix` / `MLFLOW_STATIC_PREFIX` also applies to REST `/api/` routes, and later to `/v1/traces`, Job, Gateway and Assistant APIs. Clients and proxies must include the prefix.
- Upgrades (Upgrade page): stop server, upgrade package, run `mlflow db upgrade <backend-store-url>` (Alembic), restart. "Always take a backup of the database before running the migration." No live upgrade; use a rolling upgrade behind a load balancer. Server supports SDKs up to one major version older; newer SDK features may need a newer server.
- 3.17.0 and 3.18.0 notes require stopping all writers before `mlflow db upgrade`; "Mixed-version rolling upgrades are not supported" (3.17.0).
- `mlflow db` subcommands in the CLI index: `upgrade`, `delete-trace-rollups`, `migrate-to-default-workspace`, `move-resources`, `prepopulate-trace-analytics`.
- Deleted runs keep their data until `mlflow gc`. `mlflow gc` options: `--older-than` (`#d#h#m#s`), `--backend-store-uri`, `--run-ids`, `--experiment-ids`, `--logged-model-ids`, `--jobs`, `--job-ids`, `--tracking-uri`, `--artifacts-destination`, `--workspace`, `--all-workspaces`.
- Connection pool env vars: `MLFLOW_SQLALCHEMYSTORE_POOL_SIZE`, `MLFLOW_SQLALCHEMYSTORE_POOL_RECYCLE`, `MLFLOW_SQLALCHEMYSTORE_MAX_OVERFLOW`. MySQL TLS: `MLFLOW_MYSQL_SSL_CA`, `MLFLOW_MYSQL_SSL_CERT`, `MLFLOW_MYSQL_SSL_KEY`.
- Param value length: max raised from 500 to 8k (Sept 2023), "capped internally at 6000".
- Trace rollups (3.17+): `MLFLOW_SQL_TRACE_ROLLUPS_ENABLED` (default `false`), `MLFLOW_TRACE_ROLLUPS_SCHEDULE` (`0 2 * * *` UTC), `MLFLOW_TRACE_ROLLUPS_MAX_PARTITIONS_PER_RUN` (1000), `MLFLOW_TRACE_ROLLUPS_MAX_WORKERS` (4).
- **File store status:** 3.13.0 notes: local file paths for tracking/registry "raise an error by default. Set `MLFLOW_ALLOW_FILE_STORE=true`". Env reference: `MLFLOW_ALLOW_FILE_STORE` default `False`. Migrate with `mlflow migrate-filestore --source /path/to/mlruns --target sqlite:///path/to/mlflow.db` (needs MLflow 3.10+; target must be SQLite and empty; artifacts and trace span files are not moved; IDs and timestamps are kept).

**Official URLs read.**
- https://mlflow.org/docs/latest/self-hosting/
- https://mlflow.org/docs/latest/self-hosting/architecture/overview/
- https://mlflow.org/docs/latest/self-hosting/architecture/tracking-server/
- https://mlflow.org/docs/latest/self-hosting/architecture/backend-store/
- https://mlflow.org/docs/latest/self-hosting/migration/
- https://mlflow.org/docs/latest/self-hosting/migrate-from-file-store/
- https://mlflow.org/docs/latest/api_reference/cli.html
- https://mlflow.org/docs/latest/ml/mlflow-3/

**Gaps / UNVERIFIED.**
- Conflict: the Architecture overview and the Tracking overview still say the default is a local `mlruns` directory. The Self-Hosting overview, Backend Store page, CLI reference and 3.7.0 notes say SQLite. Teach SQLite.
- Conflict on file store status: Backend Store page says "TO BE DEPRECATED SOON" and maintenance mode; Search Traces page says "deprecated as of MLflow 3.6.0"; 3.13.0 notes say it now errors unless opted in. Teach the 3.13 behaviour.
- `mlflow ui` does not appear anywhere in the CLI reference command index. Current docs start the UI with `mlflow server`. Whether `mlflow ui` still exists as a command is UNVERIFIED.
- No MySQL server example command was found on a fetched page.

### 3b. Artifact stores (S3, MinIO, RustFS, others)

**Plain explanation.** Artifacts can live on local disk or in object storage. For S3-compatible storage such as MinIO or RustFS you point MLflow at a custom endpoint URL. The server can proxy uploads and downloads, or hand out short-lived signed URLs so big files skip the server.

**Documented facts.**
- Supported URIs (Artifact Store page): `s3://<bucket>/<path>` (plus S3-compatible: MinIO, DigitalOcean Spaces, Hugging Face Storage Buckets), `wasbs://<container>@<account>.blob.core.windows.net/<path>`, `gs://<bucket>/<path>`, `b2://<bucket>@<endpoint-host>/<path>`, `ftp://`, `sftp://` (needs `pysftp`), NFS (plain path, same on server and client), `hdfs:`.
- S3 env vars: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `MLFLOW_S3_ENDPOINT_URL` (custom endpoint such as MinIO), `MLFLOW_S3_IGNORE_TLS` or `AWS_CA_BUNDLE` (not both), `MLFLOW_S3_UPLOAD_EXTRA_ARGS` (JSON, e.g. KMS), `MLFLOW_S3_EXPECTED_BUCKET_OWNER`.
- Azure: `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_STORAGE_ACCESS_KEY`, fallback `DefaultAzureCredential`. GCS: `MLFLOW_GCS_UPLOAD_CHUNK_SIZE`, `MLFLOW_GCS_DOWNLOAD_CHUNK_SIZE`.
- Multipart: `MLFLOW_MULTIPART_UPLOAD_MINIMUM_FILE_SIZE` (default 500 MB), `MLFLOW_MULTIPART_UPLOAD_CHUNK_SIZE` (default 100 MB), `MLFLOW_ENABLE_PROXY_MULTIPART_UPLOAD` (server hands out presigned part URLs for S3/GCS).
- Presigned-only mode: `--artifacts-presigned-only` or `MLFLOW_ARTIFACTS_PRESIGNED_ONLY=true`; proxied byte endpoints return 403; S3-compatible only. Direct presigned downloads in the UI need 3.15.0+ and Amazon S3. `MLFLOW_PRESIGNED_DOWNLOAD_URL_TTL_SECONDS` default 300. "anyone with the URL can fetch the artifact until it expires."
- Proxied mode warning: "all users who have access to the Tracking Server in this mode will have access to artifacts."
- MLflow 3 artifact layout (migration guide): model artifacts moved from `experiments/<exp>/<run>/artifacts/` to `experiments/<exp>/models/<model_id>/artifacts/`.
- **Docker Compose** (repo `docker-compose/` folder, README read on GitHub): MLflow + PostgreSQL + **RustFS** (S3-compatible). `.env.dev.example` sets `MLFLOW_BACKEND_STORE_URI=postgresql://...@postgres:5432/mlflow`, `MLFLOW_ARTIFACTS_DESTINATION=s3://mlflow`, `MLFLOW_S3_ENDPOINT_URL=http://storage:9000`, `AWS_ACCESS_KEY_ID=s3admin`, `MLFLOW_HOST=0.0.0.0`, `MLFLOW_PORT=5000`. Start: `cp .env.dev.example .env` then `docker compose up -d`.

**Official URLs read.**
- https://mlflow.org/docs/latest/self-hosting/architecture/artifact-store/
- https://mlflow.org/docs/latest/genai/getting-started/connect-environment/
- https://github.com/mlflow/mlflow/blob/master/docker-compose/README.md (raw)
- https://github.com/mlflow/mlflow/blob/master/docker-compose/.env.dev.example (raw)

**Gaps / UNVERIFIED.**
- Conflict: the "Set Up MLflow Server" page says the compose stack uses MinIO; the Self-Hosting overview and the repo README say RustFS. The repo is the source of truth: RustFS.
- The Artifact Store page does not explain the `mlflow-artifacts:/` URI scheme; only the CLI default mentions it.
- A worked MinIO-specific example (bucket creation, endpoint) was not found on a fetched docs page.

### 3c. Kubernetes (Helm) and cloud

**Plain explanation.** Since 3.13 there is an official Helm chart for running the tracking server on Kubernetes. The docs say SQLite and local files are not fit for teams; use PostgreSQL and object storage.

**Documented facts.**
- Chart: `oci://ghcr.io/mlflow/charts/mlflow`, source `github.com/mlflow/mlflow/tree/master/charts`. Needs Kubernetes 1.23+, Helm 3.8+.
- Install: `helm install mlflow oci://ghcr.io/mlflow/charts/mlflow --version <version> --namespace mlflow --create-namespace`.
- Chart `X.Y.Z` uses image `ghcr.io/mlflow/mlflow:vX.Y.Z-full`.
- Values: `mlflow.backendStoreUri` or `mlflow.backendStoreUriFrom.secretKeyRef` (Secret recommended); `mlflow.artifactsDestination`; `server.value_options.app_name: "basic-auth"` plus `MLFLOW_FLASK_SERVER_SECRET_KEY` from a Secret; `ingress.*`; `server.value_options.allowed_hosts` (else "requests are rejected with HTTP 403"); `tls.enabled`, `tls.secretName`; `server.flag_options` with `enable_workspaces`; `garbageCollection.enabled/schedule/olderThan/allWorkspaces`; `storage.*`; `metrics.enabled`, `serviceMonitor.enabled`.
- Quote: "SQLite and local file storage are not suitable for multi-user or high-concurrency deployments."
- 3.18.0 notes: opt-in CPU/memory autoscaling in the Helm chart.
- Official Docker image page: `ghcr.io/mlflow/mlflow` on GitHub Container Registry.

**Official URLs read.**
- https://mlflow.org/docs/latest/self-hosting/kubernetes-helm/
- https://mlflow.org/docs/latest/ml/docker/

**Gaps / UNVERIFIED.**
- The Docker image page still shows a `v2.0.1` tag example (stale).
- The cloud deployment page (`/self-hosting/deploy-to-cloud/aws/`) was not read.
- Exact autoscaling value names are not documented on the Helm page.

### 3d. Security: network middleware

**Plain explanation.** From 3.5.0 the server has built-in protection against DNS rebinding, cross-site requests and clickjacking. The defaults suit a laptop. If you open the server to a network you must list the allowed host names and web origins.

**Documented facts.**
- Requires the default FastAPI/uvicorn server (3.5.0+); not available with `--gunicorn-opts` or `--waitress-opts`.

| Setting | CLI | Env var | Default |
|---|---|---|---|
| Allowed hosts | `--allowed-hosts` | `MLFLOW_SERVER_ALLOWED_HOSTS` | localhost and private IPs |
| CORS origins | `--cors-allowed-origins` | `MLFLOW_SERVER_CORS_ALLOWED_ORIGINS` | `localhost:*` |
| X-Frame-Options | `--x-frame-options` | `MLFLOW_SERVER_X_FRAME_OPTIONS` | `SAMEORIGIN` (also `DENY`, `NONE`) |
| Disable all | `--disable-security-middleware` | `MLFLOW_SERVER_DISABLE_SECURITY_MIDDLEWARE` | false |

- Wildcards: `*.company.com`, `192.168.*`. IPv4 prefix patterns match IPs only, not hostnames. `"*"` is warned against; CORS `"*"` is "development only".
- Example: `mlflow server --host 0.0.0.0 --allowed-hosts "mlflow.company.com" --cors-allowed-origins "https://app.company.com"`.
- "Invalid Host header" error means you need `--allowed-hosts` (Self-Hosting overview).
- Secure installs page exists (`/self-hosting/security/secure-installs/`) about pinning dependencies with hashes; not read in detail.

**Official URLs read.**
- https://mlflow.org/docs/latest/self-hosting/security/network/

**Gaps / UNVERIFIED.**
- The network page does not cover TLS termination; the Tracking Server page points to a reverse proxy.

### 3e. Authentication, RBAC, SSO, workspaces

**Plain explanation.** Open-source MLflow has a built-in username and password mode. Since 3.13, admins grant access through roles. Each role is a list of "resource, pattern, permission" grants. Workspaces split one server into team areas. Single sign-on needs a community plugin or a reverse proxy.

**Documented facts.**
- Basic auth: `pip install 'mlflow[auth]'`, then `mlflow server --app-name basic-auth`. Auth works only on a remote tracking server.
- "MLflow ships no default admin password." Set `MLFLOW_AUTH_ADMIN_PASSWORD` (or `admin_password` in config) or the server refuses to start. Minimum 12 characters. The old default `password1234` is rejected. Admin username default `admin` (`MLFLOW_AUTH_ADMIN_USERNAME`).
- Set `MLFLOW_FLASK_SERVER_SECRET_KEY` for CSRF; keep it the same across replicas.
- Config file `basic_auth.ini` (override path with `MLFLOW_AUTH_CONFIG_PATH`): `default_permission` (READ), `grant_default_workspace_access`, `database_uri` (default SQLite `basic_auth.db`), `admin_username`, `admin_password`, `authorization_function` (`module:function`).
- Auth DB migration: `python -m mlflow.server.auth db upgrade --url <database_url>`. Uses its own `alembic_version_auth` table.
- Client credentials: `MLFLOW_TRACKING_USERNAME` and `MLFLOW_TRACKING_PASSWORD`, or `~/.mlflow/credentials` (`[mlflow]` section).
- Permission levels: `READ`, `USE`, `EDIT`, `MANAGE`, `NO_PERMISSIONS` (resolver-only), and since 3.17 `DENY`. Admins bypass all checks.
- REST: `2.0/mlflow/users/create`, `.../users/get`, `.../users/update-password`, `.../users/update-admin`, `.../users/delete`; `3.0/mlflow/users/permissions/grant` and `.../revoke`; `3.0/mlflow/auth/check`. UI sign-up at `<tracking_uri>/signup` (admin only).
- Python admin client: `from mlflow.server import get_app_client`; `get_app_client("basic-auth", tracking_uri=...)`; methods `create_user`, `update_user_admin`, `create_role`, `add_role_permission(role_id, resource_type, resource_pattern, permission)`, `assign_role(username, role_id)`, `list_roles`, `grant_user_permission`, `revoke_user_permission`, `get_user_permission`, `list_user_permissions`.
- RBAC (3.13+): role = "a named list of `(resource_type, resource_pattern, permission)` grants", e.g. `experiment:42` or `experiment:*`. Resource types: experiment, registered model, prompt, scorer, AI Gateway resources, workspace, MCP server; sub-resource tiers (3.17+) run, trace, assessment, logged_model, review_queue, registered_model_version, prompt_version, scorer_version, mcp_server_version (only `*` pattern). Built-in roles `admin` = `(workspace, *, MANAGE)` and `user` = `(workspace, *, USE)`, seeded when `MLFLOW_RBAC_SEED_DEFAULT_ROLES` is on (default). `default_permission` "acts as a floor". Admin UI at `/admin` and `/admin/ws?workspace=<name>`.
- 3.13.0 breaking change: legacy per-resource permission tables, endpoints and client methods were removed.
- SSO: community plugin `mlflow-oidc-auth` (`pip install 'mlflow-oidc-auth[full]'`, `mlflow server --app-name oidc-auth`), env `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_REDIRECT_URI`, `OIDC_DISCOVERY_URL`, `OIDC_SCOPE`, `SECRET_KEY`, group vars; or a reverse proxy such as oauth2-proxy. "This plugin is maintained by the community."
- Workspaces: opt-in, "disabled by default". Enable with `--enable-workspaces` or `MLFLOW_ENABLE_WORKSPACES=1`. Need a SQL backend. Scope experiments (with runs, traces, artifacts), registered models, prompts, AI Gateway resources, evaluation datasets. Client: `mlflow.set_workspace("team-a")` or `MLFLOW_WORKSPACE`. Reserved `default` workspace. "Not a hard isolation boundary." OTLP clients send `X-MLFLOW-WORKSPACE` (OTLP ingest page). Released as "Organization Support" in 3.10.0.

**Official URLs read.**
- https://mlflow.org/docs/latest/self-hosting/security/basic-http-auth/
- https://mlflow.org/docs/latest/self-hosting/security/role-based-access-control/
- https://mlflow.org/docs/latest/self-hosting/security/sso/
- https://mlflow.org/docs/latest/self-hosting/workspaces/

**Gaps / UNVERIFIED.**
- The basic-auth page's own examples use a short password that breaks its 12-character rule. Do not copy them.
- Kubernetes auth (`/self-hosting/security/kubernetes/`) and custom auth (`/self-hosting/security/custom/`) pages were not read.
- The exact `resource_type` strings for gateway resources are not given.

---

## 4. Models (MLmodel, flavors, pyfunc, signatures, custom models, dependencies, LoggedModel)

**Plain explanation.** An MLflow Model is a folder with a file called `MLmodel` that describes it. A flavor is one way to load the model, such as scikit-learn. Almost every model also has the `python_function` (pyfunc) flavor, so any tool can call `predict` the same way. A signature says what inputs and outputs the model expects. You can wrap your own logic in a `PythonModel`, or save it as a plain Python file ("models from code") instead of a pickle. MLflow records the Python packages the model needs. In MLflow 3, every logged model gets its own `model_id` and you no longer need a run to log one.

**Documented facts.**
- Folder layout from `mlflow.sklearn.save_model(...)`: `MLmodel`, `model.pkl`, `conda.yaml`, `python_env.yaml`, `requirements.txt`, optional `input_example.json`, `serving_input_example.json`, `environment_variables.txt`; metadata also copied to a `metadata/` subfolder.
- `MLmodel` fields documented: `flavors`, `time_created`, `run_id`, `signature`, `input_example`, `databricks_runtime`, `mlflow_version`. Example has `flavors: sklearn: {pickled_model: model.pkl}` and `python_function: {loader_module: mlflow.sklearn}`.
- Built-in flavors: `python_function`, `crate` (R), `h2o`, `keras`, `pytorch`, `sklearn`, `spark`, `tensorflow`, `onnx`, `xgboost`, `lightgbm`, `catboost`, `spaCy`, `statsmodels`, `prophet`, `pmdarima`, `johnsnowlabs`, `transformers`, `sentence_transformers`. GenAI flavors listed separately: LangChain (and LangGraph), LlamaIndex, DSPy; `mlflow.openai.log_model()` is "deprecated" (GenAI Packaging page).
- Loading: flavor loaders return native objects; `mlflow.pyfunc.load_model(uri)` returns a generic predictor (does not install dependencies); `predict_stream` for streaming models.
- MLflow 3 logging: `log_model(..., name="model")` replaces `artifact_path`; no `start_run()` needed; returns `ModelInfo` with `model_uri` and `model_id`.
- URIs: `models:/<model_id>` (MLflow 3), `models:/<name>/<version>`, `models:/<name>@<alias>`, `runs:/<run_id>/<path>` (migration guide: "will be removed in future").
- `mlflow.create_external_model()` (MLflow 3+) creates a model entry without packaged artifacts (Registry overview; details not read).
- **Signatures**: column-based `ColSpec("double", "sepal_length")` (optional with `required=False`) or tensor-based `TensorSpec(np.dtype(np.float32), (-1, 28, 28, 1))`. Params: `ParamSchema([ParamSpec("stop_words", "string", [".", "!"], (-1,))])` (scalars or 1-D only). `infer_signature(X, preds[, params])`. An `input_example` auto-generates the signature and produces `input_example.json` plus `serving_input_example.json`. Types: string, long, integer, double, float, boolean, datetime, binary; Array (2.10+), Object, Map, AnyType (2.19+). Safe casts int→long, int→double, float→double; long→double and string→int are rejected. Extra input fields are ignored; unknown params warn. `mlflow.models.set_signature(model_uri, signature)` updates a logged model; registered versions are immutable.
- **Custom PythonModel**: implement `predict` (required), optional `predict_stream`, `load_context`. From 2.20.0 the `context` argument can be dropped and **type hints** drive the signature and validation; inputs must be `list[...]`; Pydantic models allowed. Function-based models with `@pyfunc` from `mlflow.pyfunc.utils`. Type-hinted models are queried with `{"inputs": [...]}`.
- **Models from code** (2.12.2+): write the model in a `.py` file ending with `set_model(obj)`; log with `mlflow.pyfunc.log_model(python_model="basic.py", name=..., input_example=...)`; helper modules via `code_paths=[...]`. The script runs at logging time. "Don't hardcode secrets"; if logged, delete the run, run `mlflow gc`, rotate the key.
- **Dependencies**: saved as `requirements.txt`, `python_env.yaml`, `conda.yaml`. `extra_pip_requirements` adds, `pip_requirements` replaces (warned as "dangerous"). `MLFLOW_LOCK_MODEL_DEPENDENCIES=true` (2.16.0+, needs `uv`) pins transitive deps. Experimental uv support reads `uv.lock`/`pyproject.toml` (uv 0.6.10+); params `uv_project_path`, `uv_groups`, `uv_extras`; toggles `MLFLOW_UV_AUTO_DETECT`, `MLFLOW_LOG_UV_FILES`. `infer_code_paths=True` (2.13.0+). `code_paths=["src"]` keeps import paths.
- Pre-deploy check: `mlflow.models.predict(model_uri=..., input_data=..., env_manager="uv")` (2.10.0+) builds a fresh env and predicts; CLI `mlflow models predict -m ... -i input.csv -o output.csv`; fix with `pip_requirements_override=[...]`, persist with `mlflow.models.update_model_requirements(model_uri=..., operation="add", requirement_list=[...])` or CLI `mlflow models update-pip-requirements`.
- **Pickle-free formats and model-code safety** (Pickle-Free page, 3.18.0): pickle "can execute arbitrary code during deserialization". Options: sklearn `serialization_format="skops"` (`skops_trusted_types`), PyTorch `serialization_format="pt2"` (needs `input_example`, torch 2.4+), LightGBM `skops` (sklearn API only), DSPy `use_dspy_model_save=True`, LangChain/custom via models-from-code. `MLFLOW_ALLOW_MODEL_CODE_EXECUTION` (3.18.0, default `true`; `false` refuses PyFunc, pickle, code-path and models-from-code models). `MLFLOW_ALLOW_PICKLE_DESERIALIZATION` is deprecated. Pickle-free will become the default in an unspecified future release.
- **GenAI model interfaces**: `mlflow.pyfunc.ResponsesAgent` (subclass of `PythonModel`) is the recommended interface. ChatModel page banner: "Starting in MLflow 3.0.0, we recommend ResponsesAgent instead of ChatModel." ResponsesAgent page: "We recommend ResponsesAgent instead of ChatModel and ChatAgent." Types in `mlflow.types.responses`: `ResponsesAgentRequest`, `ResponsesAgentResponse`, `ResponsesAgentStreamEvent`. Helpers: `create_text_output_item`, `create_function_call_item`, `create_function_call_output_item`, `create_reasoning_item`, `create_text_delta`, MCP approval items. Logged via models-from-code; MLflow adds `{"task": "agent/v1/responses"}` metadata. Needs `pydantic>=2`. "Ensure your model is compatible with OpenAI Responses API". ChatModel needs MLflow 2.17.0+ and uses `ChatMessage`, `ChatParams`, `ChatCompletionResponse`.

**Official URLs read.**
- https://mlflow.org/docs/latest/ml/model/
- https://mlflow.org/docs/latest/ml/model/signatures/
- https://mlflow.org/docs/latest/ml/model/python_model/
- https://mlflow.org/docs/latest/ml/model/models-from-code/
- https://mlflow.org/docs/latest/ml/model/dependencies/
- https://mlflow.org/docs/latest/ml/tracking/pickle-free-models/
- https://mlflow.org/docs/latest/ml/mlflow-3/
- https://mlflow.org/docs/latest/genai/flavors/
- https://mlflow.org/docs/latest/genai/flavors/responses-agent-intro/
- https://mlflow.org/docs/latest/genai/flavors/chat-model-intro/

**Gaps / UNVERIFIED.**
- `MLmodel` fields `artifact_path`, `model_uuid`, `model_id`, `utc_time_created`, `saved_input_example_info` are not on the fetched page. A real MLmodel file from 3.18 should be inspected for the lesson.
- `PythonModelContext`, the `artifacts=` dict, and `model_config` / `mlflow.models.ModelConfig` were not on fetched pages.
- `mlflow.pyfunc.get_model_dependencies` and `MLFLOW_REQUIREMENTS_INFERENCE_TIMEOUT` not confirmed.
- Whether ChatAgent is formally deprecated is not stated; docs only "recommend" ResponsesAgent.
- A dedicated LoggedModel concept page was not found in the current docs (3.1.0 notes link `/genai/data-model/logged-model`, not fetched).

---

## 5. Model Registry

**Plain explanation.** The registry is a shared catalog of models. A registered model has a name and numbered versions. An alias, like `@champion`, is a movable pointer to one version, so serving code can stay the same while you swap the model underneath. Tags hold labels such as "validated". The old "stages" (Staging, Production) are deprecated. To move a model between environments, copy the version into another registered model.

**Documented facts.**
- Register: `mlflow.<flavor>.log_model(..., registered_model_name="name")` (creates a new version if the name exists), `mlflow.register_model(model_uri, name)`, `MlflowClient().create_registered_model(name)`, `MlflowClient().create_model_version(name, source, run_id)`. UI: "Register Model" button.
- Versions start at 1. Registered versions are immutable (Signatures page).
- Aliases: `client.set_registered_model_alias(name, alias, version)`, `client.get_model_version_by_alias(name, alias)`, `client.delete_registered_model_alias(name, alias)`. Load with `models:/<name>@<alias>`.
- Tags: `set_registered_model_tag`, `delete_registered_model_tag`, `set_model_version_tag(name, version, key, value)`, `delete_model_version_tag`.
- Other: `rename_registered_model`, `update_model_version(name, version, description=...)`, `search_registered_models()`, `search_model_versions("name='<model>'")`, `delete_model_version`, `delete_registered_model` ("irrevocable").
- **Stages**: `transition_model_version_stage(name, version, stage)` with Staging, Production, Archived, None; URI `models:/<name>/<Stage>`. Workflow page: "Model Stages are deprecated and will be removed in a future major release." Deprecated since 2.9.0. Migration helper shown: `assign_alias_to_stage()` using `get_latest_versions(..., stages=[...])`.
- Copy across environments: `client.copy_model_version(src_model_uri="models:/regression-model-staging@candidate", dst_name=...)`; UI "Promote model" button. Recommended pattern: one registered model per environment (e.g. `dev.ml_team.revenue_forecasting`, `staging...`, `prod...`), protect with auth, point production at an alias. Mature teams promote code through CI/CD instead of models.
- Other registries: `mlflow.set_registry_uri("databricks-uc")` (Unity Catalog; signature required); `"uc:<url>"` for OSS Unity Catalog with `MLFLOW_UC_OSS_TOKEN`.
- Version note: 2.21.0+ clients with servers older than 2.21.0 "may return inconsistent search results".
- Webhooks (section 12) fire on registry events such as `model_version_alias.created`.
- 3.18.0 breaking change: `models:/` downloads no longer add `registered_model_meta`.

**Official URLs read.**
- https://mlflow.org/docs/latest/ml/model-registry/
- https://mlflow.org/docs/latest/ml/model-registry/workflow/

**Gaps / UNVERIFIED.**
- Conflict: the Registry overview and the ML overview still describe stage transitions without a deprecation note. The Workflow page is explicit that stages are deprecated. Teach aliases.
- Whether `mlflow.register_model("models:/<model_id>", name)` is the preferred MLflow 3 form is not shown (the workflow page uses `runs:/`). UNVERIFIED.
- The registry tutorial page (`/ml/model-registry/tutorial/`) was not read.

---

## 6. Serving and deployment (models serve, Docker, Kubernetes, deployments, AI Gateway)

### 6a. Local serving and Docker

**Plain explanation.** `mlflow models serve` starts a small web server for any pyfunc model. You send JSON to `/invocations` and get predictions back. `mlflow models build-docker` puts the same server and model into a container image. MLServer was an optional alternative server, but it was removed in 3.13.

**Documented facts.**
- `mlflow models serve` options (CLI reference): `-m/--model-uri` (required), `-p/--port` (5000, `MLFLOW_PORT`), `-h/--host` (`127.0.0.1`), `-t/--timeout` (60 s, `MLFLOW_SCORING_SERVER_REQUEST_TIMEOUT`), `-w/--workers` (1 uvicorn worker, `MLFLOW_MODELS_WORKERS`), `--env-manager` (`local`, `virtualenv`, `uv`, `conda`; default `virtualenv`), `--no-conda`, `--install-mlflow`.
- The scoring server uses FastAPI (Deploy Locally page).
- Endpoints: `/invocations` (POST), `/ping` and `/health` (health), `/version` (MLflow version).
- Content types: `application/json` or `application/csv`. Parquet input was added to the scoring server in 3.10.0 (release notes).
- JSON request keys: `{"dataframe_split": df.to_dict(orient="split")}`, `{"dataframe_records": df.to_dict(orient="records")}` (not recommended; column order not guaranteed), `{"instances": [...]}`, `{"inputs": [...]}`, optional `"params": {...}` (needs params in the signature). Chat-style models also accept a raw OpenAI-like body `{"messages": [...], "temperature": 0.0}` without `model`. Binary must be base64; datetimes ISO 8601.
- Response example (3.12.0 KServe tutorial): `{"predictions": [-0.034...]}`.
- `mlflow models build-docker`: `-m`, `-n/--name`, `--env-manager` (default `virtualenv`), `--mlflow-home`, `--install-java`, `--install-mlflow`. If `-m` is omitted, mount a model at `/opt/ml/model`. `mlflow models generate-dockerfile -d <dir>` writes a Dockerfile instead.
- Other `mlflow models` subcommands: `predict`, `prepare-env`, `update-pip-requirements`.
- **MLServer**: 3.13.0 notes: "No longer a pyfunc serving backend. `enable_mlserver` is removed, and `mlflow models serve` always uses the built-in scoring server." The 3.12.0 tutorial said it "is deprecated and will be removed in MLflow 3.13". `--enable-mlserver` is absent from the current CLI reference.
- Targets listed on the Deployment overview: Local, Amazon SageMaker (`mlflow sagemaker`), Azure ML (`azureml-mlflow`), Databricks Model Serving, Modal (`mlflow-modal-deploy` plugin), community plugins (Ray Serve, Redis AI, TorchServe, OCI).
- `mlflow deployments` subcommands: `create` (`--name`, `-t/--target`, `-m`, `-f`, `-C/--config`, `--endpoint`), `create-endpoint`, `predict` (`-I` input, `-O` output), `list`, `run-local`, `delete`, `delete-endpoint`, `explain`, `get`, `get-endpoint`, `help`, `list-endpoints`, `update`, `update-endpoint`.
- **Kubernetes/KServe tutorial: removed from latest docs.** `/docs/latest/ml/deployment/deploy-model-to-kubernetes/` and `/tutorial/` now redirect to `/docs/latest/self-hosting#kubernetes` (checked with curl). The tutorial still exists in the 3.12.0 docs and redirects from 3.13.0 onward. 3.12.0 content (historic): build with `mlflow models build-docker -m runs:/<id>/model -n <user>/mlflow-wine-classifier --enable-mlserver`; InferenceService `apiVersion: "serving.kserve.io/v1beta1"`, `kind: "InferenceService"`, container `containerPort: 8080`, env `PROTOCOL=v2`; or `spec.predictor.model.modelFormat.name: mlflow`, `protocolVersion: v2`, `storageUri: <remote URI>` ("KServe cannot resolve `runs:/` or `models:/` URIs"); request to `/v2/models/<name>/infer` with V2 `inputs` (`name`, `shape`, `datatype: "FP32"`, `data`).
- GenAI Agent Server (needs 3.6.0+ per example): a FastAPI server that hosts a `ResponsesAgent`-style agent at `/invocations`; `@invoke()` and `@stream` decorators; `AgentServer("ResponsesAgent")`; run with `python3 start_server.py --reload --workers 4 --port 8000`; request body `{"input": [{"role": "user", "content": "..."}], "stream": true}`.

**Official URLs read.**
- https://mlflow.org/docs/latest/ml/deployment/
- https://mlflow.org/docs/latest/ml/deployment/deploy-model-locally/
- https://mlflow.org/docs/latest/api_reference/cli.html
- https://mlflow.org/docs/latest/ml/deployment/deploy-model-to-kubernetes/ (redirect, curl)
- https://mlflow.org/docs/3.12.0/ml/deployment/deploy-model-to-kubernetes/tutorial/ (archived version)
- https://mlflow.org/docs/latest/genai/serving/agent-server/

**Gaps / UNVERIFIED.**
- There is no current official Kubernetes model-serving tutorial. A lesson that deploys a served model to Kubernetes would rely on the 3.12.0 page (with MLServer removed) or on general KServe docs. Whether KServe's `mlflow` model format still works with images built without MLServer is UNVERIFIED.
- The container port of images from `build-docker` is 8080 only in the 3.12.0 MLServer example; for the default server it is UNVERIFIED.
- The Docker CLI options `--base-image` were not found.
- The SageMaker and Modal pages were not read.

### 6b. AI Gateway

**Plain explanation.** The MLflow AI Gateway is a single front door for LLM providers. You store provider API keys once on the server. You create named endpoints, and apps call the endpoint instead of the provider. It can split traffic, fall back to a second model, track usage and cost, set budgets, and run guardrails. Since 3.x it is built into `mlflow server` and managed in the UI. The old YAML-file gateway still exists but is called "legacy".

**Documented facts.**
- Name: "MLflow AI Gateway".
- Install `pip install 'mlflow[genai]'`; start `mlflow server --port 5000`; the gateway is part of the tracking server. Needs a SQL backend and the FastAPI server.
- UI: Settings → **LLM Connections** (provider + API key), then **Endpoints** → Create Endpoint (name, provider, model, connection). Endpoint page at `http://localhost:5000/#/gateway`.
- Providers: "100+" via the picker; "LiteLLM" opens the LiteLLM catalog (needs LiteLLM installed). The 3.15.0 notes add a `sap-ai-core:/` provider.
- Call it:
  - `POST http://localhost:5000/gateway/<endpoint-name>/mlflow/invocations` with `{"messages": [...]}`.
  - OpenAI SDK: `OpenAI(base_url="http://localhost:5000/gateway/mlflow/v1", api_key="")`, `model="<endpoint-name>"`.
  - Raw passthrough proxy (3.13.0): `/gateway/proxy/{endpoint_name}/{path}`.
- Traffic split: weights 1-100% that must "sum to exactly 100%". Fallbacks tried "sequentially from top to bottom" on errors or rate limits.
- Guardrails: per endpoint; types Safety (default post-LLM), PII Detection (default pre-LLM), Custom. An LLM judge on a separate gateway endpoint answers yes/no. Actions Block (HTTP 400, `INVALID_PARAMETER_VALUE`) or Sanitize. Post-LLM guardrails do not run on streaming responses.
- Secrets: API keys "are encrypted before being stored". Passphrase via `MLFLOW_CRYPTO_KEK_PASSPHRASE` and `MLFLOW_CRYPTO_KEK_VERSION`; without it a built-in default passphrase is used (OK only "for development or single-user deployments"). Rotate with `mlflow crypto rotate-kek --new-passphrase "..."` while the server is stopped.
- `MLFLOW_GATEWAY_API_BASE_ALLOW_PRIVATE_IPS=true` only if every user who can create connections is trusted with your private network.
- Budgets (`budget_policy.exceeded` webhook event), usage tracking page (3.10.0), coding-agent onboarding for Claude Code, Codex, Gemini CLI (3.13.0).
- Legacy gateway: CLI still has `mlflow gateway start --config-path <file>` (`--host` 127.0.0.1, `--port` 5000, `--workers`; env `MLFLOW_GATEWAY_CONFIG`). Env reference calls it "the legacy YAML-config gateway (`mlflow gateway start`)". MLflow 3 migration guide: `routes` and `route_type` config keys removed; "The deployment server and `start-server` CLI were removed".

**Official URLs read.**
- https://mlflow.org/docs/latest/genai/governance/ai-gateway/
- https://mlflow.org/docs/latest/genai/governance/ai-gateway/quickstart/
- https://mlflow.org/docs/latest/genai/governance/ai-gateway/endpoints/create-and-manage/
- https://mlflow.org/docs/latest/genai/governance/ai-gateway/api-keys/create-and-manage/
- https://mlflow.org/docs/latest/genai/governance/ai-gateway/api-keys/key-rotation/
- https://mlflow.org/docs/latest/genai/governance/ai-gateway/traffic-routing-fallbacks/
- https://mlflow.org/docs/latest/genai/governance/ai-gateway/guardrails/

**Gaps / UNVERIFIED.**
- No full provider list or endpoint-type list (chat, embeddings) on fetched pages.
- Rate limiting config not found.
- A search result claimed the gateway "does not support Windows" (3.6.0rc0 page). Not confirmed on a current page. UNVERIFIED, but matters for a Windows-based course.
- Usage tracking, budgets, benchmarks and coding-agents pages were not read.

---

## 7. GenAI tracing

**Plain explanation.** A trace records one request through your app, step by step. Each step is a span with inputs, outputs, timing and a type such as "retriever" or "tool". One line, such as `mlflow.openai.autolog()`, traces a library for you. For your own code you add `@mlflow.trace` or a `with mlflow.start_span()` block. Traces follow OpenTelemetry, so you can send them to MLflow from any language, or send MLflow traces on to other tools. In production you use a small package called `mlflow-tracing`, async logging, and sampling.

**Documented facts.**
- Quickstart: `pip install --upgrade mlflow openai>=1.0.0`; `uvx mlflow server` or `mlflow server`; `mlflow.set_tracking_uri("http://localhost:5000")`; `mlflow.set_experiment("My Application")`; `mlflow.openai.autolog()`; then call OpenAI; view the experiment's **Traces** tab.
- Autolog names confirmed on fetched pages: `mlflow.openai.autolog()`, `mlflow.anthropic.autolog()` (async since 2.21.0; disable with `autolog(disable=True)`), `mlflow.langchain.autolog()` (also covers **LangGraph**; `run_tracer_inline=True` for async with manual spans).
- Integrations page lists 79 entries (75 unique): Python agent frameworks (LangChain, LangGraph, OpenAI Agent, DSPy, PydanticAI, Google ADK, Claude Agent SDK, Microsoft Agent Framework, CrewAI, LlamaIndex, AutoGen, Strands, LiveKit Agents, Agno, Bedrock AgentCore, Smolagents, Semantic Kernel, Haystack, Pipecat and more), TypeScript (LangChain, LangGraph, Vercel AI SDK, Mastra, VoltAgent, Claude Agent SDK, Cloudflare Agents, Flue), Java (Spring AI, Quarkus LangChain4j), coding agents (Claude Code, Codex CLI, Gemini CLI, OpenCode, OpenHands, Qwen Code, ...), 19 model providers (OpenAI, Anthropic, Gemini, Bedrock, LiteLLM, Mistral, Ollama, Groq, DeepSeek, ...), gateways (MLflow AI Gateway, LiteLLM Proxy, Vercel AI Gateway, OpenRouter, Portkey, Helicone, Kong, ...).
- Claude Code: `mlflow autolog claude` installs the MLflow Claude plugin and writes `.claude/settings.json` (CLI reference); since 3.13 it no longer installs a Python hook.
- Combining: autolog plus `@mlflow.trace(span_type=SpanType.CHAIN)` yields one combined trace. Disable all tracing with `mlflow.tracing.disable()`; re-enable with `mlflow.tracing.enable()`.
- Manual API: `@mlflow.trace(name=, span_type=, attributes=, output_reducer=)`; wrap a function: `mlflow.trace(math.pow)`; `with mlflow.start_span(name="my_span") as span:` then `span.set_inputs({...})`, `span.set_outputs(...)`, `span.set_attributes({...})`; `mlflow.get_current_active_span()`; `mlflow.update_current_trace(tags=..., request_preview=..., response_preview=..., session_id=..., user=..., client_request_id=...)`; span links via `links=[Link(...)]` or `span.add_link(...)`. Generators: span ends when the iterator is exhausted. Threads: copy context with `contextvars.copy_context()` and `executor.submit(ctx.run, ...)`; asyncio copies context automatically.
- Span types (Span concept page, raw HTML): `CHAT_MODEL`, `CHAIN`, `AGENT`, `TOOL`, `EMBEDDING`, `RETRIEVER`, `PARSER`, `RERANKER`, `MEMORY`, `WORKFLOW`, `TASK`, `GUARDRAIL`, `EVALUATOR`, `UNKNOWN` (default). Custom strings allowed. RETRIEVER output should be a list of documents with `page_content`, optional `metadata` (`doc_uri`, `chunk_id`), optional `id`.
- Span fields: `span_id`, `trace_id`, `parent_id`, `name`, `start_time_ns`, `end_time_ns`, `status` (OK, UNSET, ERROR), `inputs`, `outputs`, `attributes`, `events`, `links`.
- Trace = `TraceInfo` + `TraceData`. TraceInfo: `trace_id`, `trace_location`, `request_time` (ms), `execution_duration` (ms), `state` (`OK`, `ERROR`, `IN_PROGRESS`, `STATE_UNSPECIFIED`), `request_preview`, `response_preview`, `client_request_id`, `trace_metadata` (immutable), `tags` (mutable). Storage: TraceInfo row in `trace_info`; each span a JSON row in `spans` (3.3.0+); attachments in artifact storage via `mlflow-attachment://`.
- Sessions and users: `session_id` and `user` params on `update_current_trace()` and `with mlflow.tracing.context(session_id=..., user=...)` since 3.11.0; older versions set metadata keys `mlflow.trace.session` / `mlflow.trace.user`. 3.18.0: `session_id` can be a list.
- `mlflow.search_traces(filter_string=..., order_by=["timestamp_ms DESC"], return_type="list")` (list since 2.21.1; default pandas); also `model_id=` (Version Tracking pages). Filter fields: `trace.status`, `trace.timestamp_ms`, `trace.execution_time_ms`, `trace.end_time_ms`, `trace.name`, `trace.client_request_id`, `trace.run_id`, `tag.<key>`, `metadata.<key>` (backticks for dots), `span.name`, `span.type`, `feedback.<name>`, `expectation.<name>`, `prompt` (`"name/version"`), `trace.text` (SQL store only). Operators include `LIKE`, `ILIKE`, `RLIKE`. `MlflowClient().search_traces(experiment_ids=..., max_results=, page_token=)` paginates with `.token`.
- **OTLP ingestion** (3.6.0+): MLflow server exposes `/v1/traces`; header `x-mlflow-experiment-id` (and `X-MLFLOW-WORKSPACE` with workspaces). "MLflow Server supports only the OTLP/HTTP endpoint"; gRPC not supported. Needs a SQL backend. Compression `gzip`/`deflate` via `OTEL_EXPORTER_OTLP_TRACES_COMPRESSION` (3.7.0+). Env example: `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:5000/v1/traces`, `OTEL_EXPORTER_OTLP_TRACES_HEADERS=x-mlflow-experiment-id=123`.
- **OTLP export**: `pip install opentelemetry-exporter-otlp`; set `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` "before starting any trace"; then traces go only to the collector unless `MLFLOW_TRACE_ENABLE_OTLP_DUAL_EXPORT=true`. `MLFLOW_ENABLE_OTEL_GENAI_SEMCONV=true` converts attributes to `gen_ai.*`. Metrics export: histogram `mlflow.trace.span.duration` (ms) via `OTEL_EXPORTER_OTLP_METRICS_ENDPOINT` / `_PROTOCOL`. Backends with guides: Datadog, New Relic, SigNoz, Splunk, Grafana, Jaeger, Dynatrace, Lightstep, Middleware, Dash0.
- **Production tracing**: use `pip install mlflow-tracing` ("95% smaller", about 5 MB vs about 1000 MB); "Do not install the full `mlflow` package together with the `mlflow-tracing` package." It excludes the server/UI, runs, model logging, evaluation, registry. Use PostgreSQL/MySQL behind the server. Async logging is on by default for OSS: `MLFLOW_ENABLE_ASYNC_TRACE_LOGGING`, `MLFLOW_ASYNC_TRACE_LOGGING_MAX_WORKERS` (10), `MLFLOW_ASYNC_TRACE_LOGGING_MAX_QUEUE_SIZE` (1000; full queue drops traces), `MLFLOW_ASYNC_TRACE_LOGGING_RETRY_TIMEOUT` (500 s). Sampling: `MLFLOW_TRACE_SAMPLING_RATIO` (default 1.0, per trace) and `@mlflow.trace(sampling_ratio_override=0.1)` on root spans. `MLFLOW_USE_BATCH_SPAN_PROCESSOR` default `True`.
- Other tracing features listed: PII masking, multimodal attachments, distributed tracing (context propagation), cost tracking (3.10.0), span log levels (3.13.0), trace retention and archival to object storage (3.13.0).

**Official URLs read.**
- https://mlflow.org/docs/latest/genai/tracing/
- https://mlflow.org/docs/latest/genai/tracing/quickstart/
- https://mlflow.org/docs/latest/genai/tracing/integrations/
- https://mlflow.org/docs/latest/genai/tracing/integrations/listing/langgraph/
- https://mlflow.org/docs/latest/genai/tracing/integrations/listing/anthropic/
- https://mlflow.org/docs/latest/genai/tracing/app-instrumentation/automatic/
- https://mlflow.org/docs/latest/genai/tracing/app-instrumentation/manual-tracing/
- https://mlflow.org/docs/latest/genai/concepts/trace/
- https://mlflow.org/docs/latest/genai/concepts/span/
- https://mlflow.org/docs/latest/genai/tracing/track-users-sessions/
- https://mlflow.org/docs/latest/genai/tracing/search-traces/
- https://mlflow.org/docs/latest/genai/tracing/opentelemetry/
- https://mlflow.org/docs/latest/genai/tracing/opentelemetry/ingest/
- https://mlflow.org/docs/latest/genai/tracing/opentelemetry/export/
- https://mlflow.org/docs/latest/genai/tracing/prod-tracing/
- https://mlflow.org/docs/latest/genai/tracing/lightweight-sdk/

**Gaps / UNVERIFIED.**
- `LLM` is not in the built-in span type table, but the manual tracing page uses `SpanType.LLM` and the search page uses `span.type = 'LLM'`. Treat `LLM` as valid but check the API reference.
- `span.add_event`, `span.set_status`, `mlflow.start_span_no_context`, `mlflow.get_last_active_trace_id` were not on fetched pages.
- `mlflow.autolog()` (generic) as a GenAI tracing switch is mentioned only on the Anthropic page (as a way to disable).
- The `mlflow-tracing` version number and its release cadence were not found. The lightweight SDK page shows a © 2025 notice and may be stale.
- Trace archival config format (`--trace-archival-config` YAML) not read.
- The masking, distributed tracing and multimodal pages were not read.

---

## 8. GenAI evaluation and monitoring

**Plain explanation.** You test a GenAI app by running it on a set of example inputs and scoring each answer. Scorers can be LLM judges (a model grades the answer) or plain Python checks. MLflow ships many ready-made judges and lets you write your own with `make_judge` or `@scorer`. Each score is stored as "feedback" on the trace. Humans can add feedback too. Test cases can live in a managed evaluation dataset. You can compare two evaluation runs with statistics, and in production you can let judges score live traffic automatically. The old `mlflow.evaluate` for LLMs is deprecated; `mlflow.models.evaluate` is still the API for classic ML.

**Documented facts.**
- Call: `mlflow.genai.evaluate(data=eval_dataset, predict_fn=qa_predict_fn, scorers=[...])`. Data = list of dicts, pandas or Spark DataFrame, or an MLflow evaluation dataset. Record shape: `{"inputs": {"question": ...}, "expectations": {"expected_response": ...}}`; optional pre-computed `outputs` or `trace`. The `inputs` keys "must match the parameter name of the `predict_fn` function". 3.18.0 adds an experimental `quality_criteria` parameter.
- Imports: `from mlflow.genai.scorers import Correctness, Guidelines, RelevanceToQuery, ...`; `from mlflow.genai import scorer` (also `mlflow.genai.scorers.scorer`).
- Judge model: `<provider>:/<model-name>`, e.g. `Correctness(model="anthropic:/claude-sonnet-4-20250514")`, `"gemini:/gemini-2.5-flash"`, `"openai:/gpt-5-mini"`. Default judge is OpenAI `gpt-4o-mini` (Quickstart, Custom Judges page). Global default via `MLFLOW_GENAI_JUDGE_DEFAULT_MODEL`.
- Built-in judges (Predefined page):
  - Response quality: `RelevanceToQuery`, `Correctness` (needs ground truth), `Completeness` (exp.), `Fluency`, `Safety`, `Equivalence`, `Summarization`, `Guidelines`, `ExpectationsGuidelines`.
  - RAG (need traces): `RetrievalRelevance`, `RetrievalGroundedness`, `RetrievalSufficiency` (needs ground truth).
  - Tool calls (need traces, exp.): `ToolCallCorrectness`, `ToolCallEfficiency`.
  - Multi-turn, session-level (exp.; need `mlflow.trace.session`; pre-collected traces only): `ConversationCompleteness`, `ConversationalGuidelines`, `ConversationalRoleAdherence`, `ConversationalSafety`, `ConversationalToolCallEfficiency`, `KnowledgeRetention`, `UserFrustration`.
  - Page says `Safety` and `RetrievalRelevance` "are currently only available in Databricks managed MLflow".
- `make_judge` (3.4.0+): `from mlflow.genai.judges import make_judge`; args `name`, `instructions`, `feedback_value_type` (e.g. `Literal["correct", "incorrect"]`), `model`. Only template variables `{{ inputs }}`, `{{ outputs }}`, `{{ expectations }}`, `{{ trace }}`, `{{ conversation }}`; custom variables error. `{{ trace }}` judges explore the trace with MCP tools and must set `model`. Older `custom_prompt_judge` is deprecated. Judge Builder UI needs 3.9.0+. Structured outputs in `make_judge` since 3.7.0. TypeSafe judge models `model="typesafe:/jev-latest"` (3.17.0).
- Judge alignment with human feedback: `judge.align()`; default optimizer is MemAlign since 3.13.0 (release notes). Uses DSPy per the Scorers overview.
- Code-based scorers: `@scorer` function with keyword args `inputs`, `outputs`, `expectations`, `trace`. Return `"yes"`/`"no"`, bool, int/float, `Feedback`, or `list[Feedback]` (distinct names). `Scorer` subclass is a Pydantic model with `name` and `__call__`. Raised exceptions become Feedback with `value=None` and the error. `Feedback` fields: `name`, `value`, `rationale`, `source=AssessmentSource(source_type=..., source_id=...)` (`HUMAN`, `CODE`, `LLM_JUDGE`), `metadata`, `error`.
- Scorer registry: `list_scorers`, `get_scorer(name=...)`, `judge.register(name=...)`. CLI: `mlflow scorers list` (`--builtin/-b`), `mlflow scorers register-llm-judge`.
- Evaluation datasets: need a SQL-backed tracking server ("FileStore is not supported"). `create_dataset(name=..., experiment_id=["0"], tags={...})`, `dataset.merge_records(records | DataFrame | traces)`, `get_dataset(name=...)`, `dataset.to_df()`, `set_dataset_tags(...)`. Build from production: `mlflow.search_traces(...)`, `mlflow.log_expectation(trace_id=..., name=..., value=...)`, `merge_records(traces)`. `ConversationSimulator(test_cases=dataset)` for multi-turn scenarios (`goal`, `persona`, `context`). 3.17.0 links aggregate logged-model metrics to the managed dataset.
- Human feedback (3.2.0+): `mlflow.log_feedback(trace_id=..., name=..., value=..., rationale=..., source=AssessmentSource(source_type=AssessmentSourceType.HUMAN, source_id="expert@company.com"))`; `mlflow.get_assessment`, `mlflow.update_assessment`, `mlflow.delete_assessment`, `mlflow.override_feedback`. UI lets reviewers add and edit feedback on traces. CLI `mlflow traces log-feedback` / `log-expectation`. End-user feedback pattern: store `client_request_id`, look up the trace, then `log_feedback` (Production tracing page).
- Compare runs: `mlflow.genai.compare_evaluations(candidate_run_id=..., baseline_run_id=..., confidence_level=0.95, greater_is_better={...}, log_results=False)` returns `ComparisonResult` with `summary()`, `assert_improved(scorers=[...], alpha=0.05)` (raises `AssertionError`; for CI gates), `paired_rows`. Rows pair by `mlflow.eval.requestId` tag then input hash; fewer than 6 pairs gives `insufficient_pairs`. Quote: "experimental in MLflow 3.18.0".
- Automatic evaluation (production monitoring): `judge.register(name=...)` then `.start(sampling_config=ScorerSamplingConfig(sample_rate=0.5))`; `get_scorer(name=...).update(...)` / `.stop()`. UI: experiment **Judges** tab → "+ New LLM judge". Needs a running server, tracing on, and an AI Gateway endpoint for the judge. Only LLM judges, except `@scorer` functions in experimental job containers (3.18). Judges only see traces up to one hour old when enabled. Trace eligible 5 minutes after start; session complete after 5 idle minutes. Failures are not retried.
- Classic evaluation: `mlflow.models.evaluate(model, data, targets=, model_type="classifier"|"regressor", predictions=, evaluator_config=, extra_metrics=[make_metric(...)], custom_artifacts=)` is current for non-LLM work ("Classic ML Evaluation System"). Default metrics: classifier accuracy, precision, recall, F1, ROC-AUC, PR-AUC, log loss, Brier; regressor MAE, MSE, RMSE, R², adjusted R², MAPE. Validation: `mlflow.validate_evaluation_results(candidate_result=..., validation_thresholds={...: MetricThreshold(threshold=..., greater_is_better=...)})` (2.18.0+) raises `ModelValidationFailedException`. SHAP explainer off by default (`log_explainer`).
- Legacy LLM evaluation: "The mlflow.evaluate API has been deprecated as of MLflow 3.0.0" and "will likely be removed in MLflow 3.7.0 or a few releases after that." Mapping: `answer_correctness`, `faithfulness`, `relevance` → built-in judges or `make_judge`; `make_genai_metric` → `make_judge`; `toxicity`, ROUGE, `exact_match` → `@scorer`; `latency`, `token_count` → traces.

**Official URLs read.**
- https://mlflow.org/docs/latest/genai/eval-monitor/
- https://mlflow.org/docs/latest/genai/eval-monitor/quickstart/
- https://mlflow.org/docs/latest/genai/eval-monitor/scorers/
- https://mlflow.org/docs/latest/genai/eval-monitor/scorers/llm-judge/predefined/
- https://mlflow.org/docs/latest/genai/eval-monitor/scorers/llm-judge/custom-judges/
- https://mlflow.org/docs/latest/genai/eval-monitor/scorers/custom/
- https://mlflow.org/docs/latest/genai/datasets/
- https://mlflow.org/docs/latest/genai/assessments/feedback/
- https://mlflow.org/docs/latest/genai/eval-monitor/automatic-evaluations/
- https://mlflow.org/docs/latest/genai/eval-monitor/comparing-evaluation-runs/
- https://mlflow.org/docs/latest/genai/eval-monitor/legacy-llm-evaluation/
- https://mlflow.org/docs/latest/ml/evaluation/

**Gaps / UNVERIFIED.**
- Conflict: Quickstart uses `expectations.expected_response` for `Correctness`; the Predefined page says `Correctness` needs `expected_facts`. Check which keys the 3.18 scorer accepts.
- Conflict: `Safety` is "only available in Databricks managed MLflow" per the Predefined page, yet the Agent Server and Prompt Optimization pages use `Safety` in OSS examples. Test before teaching.
- `genai.evaluate(model_id=...)` linking an eval run to a LoggedModel was not shown on a fetched page.
- Whether `mlflow.models.evaluate` itself has a deprecation timeline is not stated (only the old `mlflow.evaluate` for LLMs).
- Review queues / labeling sessions in OSS were not described on fetched pages (only a nav link and the `review_queue` RBAC tier).
- The `ScorerSamplingConfig(filter_string=...)` argument was not shown in code on the Automatic Evaluation page (the Production tracing page does show it).
- Third-party scorers (DeepEval, RAGAS, Phoenix) not read; 3.18.0 notes mention `DeepEvalScorer`.

---

## 9. Prompt Registry and prompt optimization

**Plain explanation.** The Prompt Registry stores prompt templates with versions, like Git for prompts. Each version is frozen once saved. Aliases such as `production` point to a version, so you can roll forward or back without a code change. Your app loads the prompt by URI and fills in the variables. MLflow can link prompts to the models and traces that used them. It can also try to improve a prompt for you with an optimizer.

**Documented facts.**
- Register: `mlflow.genai.register_prompt(name=..., template=..., commit_message=..., tags={...}, model_config={...} | PromptModelConfig)`. Same name = new version.
- Templates: text with double braces `{{ num_sentences }}`; chat prompts as a list of `{"role", "content"}` dicts; Jinja2 detected when `{% %}` is used (sandboxed by default, `use_jinja_sandbox=False` to disable). `to_single_brace_format()` for LangChain/LlamaIndex.
- Load: `mlflow.genai.load_prompt("prompts:/summarization-prompt/2")`, `"prompts:/summarization-prompt@production"`, `"prompts:/summarization-prompt@latest"` (`@latest` is reserved), or bare name for latest. Fill with `prompt.format(...)`.
- "prompt versions are immutable once created"; `model_config` is the exception (mutable via `set_prompt_model_config` / `delete_prompt_model_config`). `PromptModelConfig` fields include `model_name`, `temperature`, `max_tokens`, `top_p`, `top_k`, `stop_sequences`, `extra_params`. `response_format` is a `PromptVersion` property (Pydantic class or dict).
- Aliases: `mlflow.genai.set_prompt_alias("summarization-prompt", alias="production", version=2)`; `delete_prompt_alias` appears in the cache-invalidation list.
- Search: `mlflow.genai.search_prompts(filter_string="task='summarization'")`; `MlflowClient().search_prompts(max_results=, page_token=)`.
- Tags: `set_prompt_tag`, `get_prompt_tags`, `delete_prompt_tag`, `set_prompt_version_tag`, `delete_prompt_version_tag`. Delete a version: `client.delete_prompt_version()`.
- Cache: version loads cached forever by default; alias loads 60 s. Override with `cache_ttl_seconds=` or `MLFLOW_ALIAS_PROMPT_CACHE_TTL_SECONDS`, `MLFLOW_VERSION_PROMPT_CACHE_TTL_SECONDS`.
- Linking: `mlflow.langchain.log_model(chain, name="model", prompts=["prompts:/summarization-prompt/2"])` (LLM/agent flavors only). Models-from-code that call `load_prompt` link automatically. Prompts are linked to experiments when loaded or registered (3.7.0 notes). Trace search supports `prompt = "name/version"`. Prompt webhooks exist (section 12). Workspaces and RBAC cover prompts.
- Optimization: `mlflow.genai.optimize_prompts(predict_fn=..., train_data=..., prompt_uris=["prompts:/qa/1"], optimizer=GepaPromptOptimizer(reflection_model="openai:/gpt-5", max_metric_calls=300), scorers=[...], aggregation=...)` (needs 3.5.0+). Optimizers: `GepaPromptOptimizer`, `MetaPromptOptimizer` (`reflection_model`, `guidelines`; zero-shot without data), `BasePromptOptimizer` for custom. Returns `PromptOptimizationResult` (`optimized_prompts`, `initial_eval_score`, `final_eval_score`).
- `optimize_prompt` (singular, added in 3.0) was removed: "The optimize_prompt() function has been removed in MLflow 3.5.0." `OptimizerConfig` deprecated since 3.5.0 (search result, see gaps).
- Playground UI loads registered prompts with their model config.

**Official URLs read.**
- https://mlflow.org/docs/latest/genai/prompt-registry/
- https://mlflow.org/docs/latest/genai/prompt-registry/manage-prompt-lifecycles-with-aliases/
- https://mlflow.org/docs/latest/genai/prompt-registry/log-with-model/
- https://mlflow.org/docs/latest/genai/prompt-registry/optimize-prompts/
- https://mlflow.org/docs/latest/api_reference/_modules/mlflow/genai/optimize.html

**Gaps / UNVERIFIED.**
- Whether `optimize_prompts` registers a new prompt version automatically is not stated.
- Required extra packages for GEPA (e.g. `gepa`, `dspy`) not stated on the page.
- `OptimizerConfig` deprecation came from a search summary, not a fetched page. UNVERIFIED.
- Backend requirement for the Prompt Registry is not stated on the overview (prompts are stored as registered models per the file-store migration page, so a DB backend is implied).

---

## 10. App and version tracking for GenAI apps

**Plain explanation.** In MLflow 3 a "version" of an agent is a LoggedModel. You set an active model by name, and every trace after that is linked to it. You can also make versions from Git: each branch, commit and dirty state becomes a version automatically. Then you can search traces and compare evaluation runs per version.

**Documented facts.**
- `mlflow.set_active_model(name="langchain_model")` (also usable as a context manager); `mlflow.get_active_model_id()`; `mlflow.search_traces(model_id=active_model_id)`.
- Git-based versions (3.4+, experimental, not in Databricks Git Folders): `context = mlflow.genai.enable_git_model_versioning()` (or `with ...:`); `context.info.branch`, `.commit`, `.dirty`; `context.active_model.model_id`. Each unique (branch, commit, dirty) creates or reuses a LoggedModel. Uncommitted changes stored as a diff (`mlflow.git.diff` tag). Inspect with `mlflow.get_logged_model(model_id=...)` and tags starting with `mlflow.git`.
- Agent Server example calls `setup_mlflow_git_based_version_tracking()`.
- UI tabs named: Prompts, Models (shows `model_id`), Traces, Experiments/evaluation runs.
- MLflow 3 launch notes: LoggedModel is "a first-class citizen, moving beyond the traditional run-centric approach", grouping traces and metrics across environments.
- Classic API on MLflow 3: `mlflow.create_external_model()` (Registry overview).

**Official URLs read.**
- https://mlflow.org/docs/latest/genai/version-tracking/
- https://mlflow.org/docs/latest/genai/version-tracking/quickstart/
- https://mlflow.org/docs/latest/genai/version-tracking/track-application-versions-with-mlflow/
- https://mlflow.org/docs/latest/genai/version-tracking/compare-app-versions/

**Gaps / UNVERIFIED.**
- The Version Tracking overview still compares versions with `mlflow.evaluate` and legacy metrics (`toxicity`, `latency`), which is deprecated for GenAI; its example also uses undefined variables. Do not copy it.
- The Compare App Versions page compares by trace names that its own code does not set. Do not copy it.
- `mlflow.log_model_params` (3.1.0 notes mention "fluent APIs for `LogLoggedModelParams`") and `mlflow.genai.evaluate(model_id=...)` were not confirmed on a fetched page.

---

## 11. MLflow Projects

**Plain explanation.** A Project is a folder with an `MLproject` file that says how to run the code and which environment it needs. `mlflow run` runs it locally, on Databricks, or on Kubernetes. The docs still describe it with no deprecation notice, but it gets little attention in the new docs.

**Documented facts.**
- `MLproject` keys: `name`, `python_env` (e.g. `python_env.yaml`), `conda_env`, `docker_env` (`image`, `volumes`, `environment`), `entry_points` with `parameters` and `command`. Parameter types `string`, `float`, `int`, `path`, `uri`; defaults like `{type: float, default: 0.1}`.
- Environments: virtualenv (recommended), conda, docker, system.
- `mlflow run <uri>` with `-e/--entry-point` (default `main`), `-P/--param-list NAME=VALUE`, `--env-manager` (`local`, `virtualenv`, `uv`, `conda` per CLI reference), `--experiment-name`, `--experiment-id`, `-b/--backend` (`local` default, `databricks`, `kubernetes` "experimental" per CLI), `-c/--backend-config`, `-v/--version`, `-A/--docker-args`, `--run-name`, `--build-image`, `--storage-dir`. Git URIs with `#subdirectory`.
- Python: `mlflow.projects.run(uri, entry_point=, parameters=, backend=, backend_config=, synchronous=)`.
- The MLflow 3 migration guide suggests Projects as a replacement for removed MLflow Recipes.
- `mlflow-tracing` docs list "Projects, and Recipes" among things not in the lightweight SDK.

**Official URLs read.**
- https://mlflow.org/docs/latest/ml/projects/
- https://mlflow.org/docs/latest/api_reference/cli.html

**Gaps / UNVERIFIED.**
- The Projects page does not mention `uv`, while the CLI reference lists `uv` as an `--env-manager` choice.
- No stated plan to deprecate Projects; also no sign of recent investment. UNVERIFIED either way.

---

## 12. Other current features (brief)

**Plain explanation.** MLflow now has several "agent platform" features. Most are new and marked experimental. They are worth one short lesson or a sidebar, not a deep dive.

**Documented facts.**
- **MLflow MCP server** (3.5.1+, experimental): lets coding assistants query MLflow traces. `pip install 'mlflow[mcp]>=3.5.1'`; run `mlflow mcp run` (e.g. `uv run --with "mlflow[mcp]>=3.5.1" mlflow mcp run`); configure with `MLFLOW_TRACKING_URI` in the client's MCP config (`.vscode/mcp.json` "servers", `.cursor/mcp.json` or `.mcp.json` "mcpServers", or `claude mcp add mlflow-mcp -e MLFLOW_TRACKING_URI=...`). Tools: `search_traces`, `get_trace`, `delete_traces`, `set_trace_tag`, `delete_trace_tag`, `log_feedback`, `log_expectation`, `get_assessment`, `update_assessment`, `delete_assessment`. `MLFLOW_MCP_TOOLS` = `genai` (default), `ml`, `all`, or a list.
- **MCP Registry** (3.15.0+, experimental): catalog of MCP servers with semver versions, aliases, tool snapshots; `mlflow.genai.register_mcp_server()`, `register_mcp_server_from_url()`, `search_mcp_servers()`, `create_mcp_access_endpoint()`.
- **Skill Registry** (3.18.0, experimental): versioned agent skills (`SKILL.md`); CLI `mlflow skills register --source ./code-review`, `mlflow skills search`, `mlflow skills pull skills:/code-review/1 --destination ...`, plus alias/tag commands; Python `mlflow.genai.register_skill()`, `search_skills()`.
- **MLflow AI Assistant** (Beta): in-UI assistant powered by Claude Code, Codex CLI, Ollama, or an AI Gateway endpoint. Runs on the server machine; remote use needs `MLFLOW_ENABLE_REMOTE_ASSISTANT=true`. CLI has `mlflow assistant --configure` and `mlflow agent setup`. Privacy note: data goes to the chosen model provider unless Ollama is used.
- **Automatic Issue Detection** (3.18.0): Issues tab groups recurring trace failures; can be scheduled daily/weekly; needs Linux/macOS server, SQL backend, background jobs, and a model or gateway endpoint. API `mlflow.genai.create_issue()`, `search_issues()`, `update_issue()`.
- **Job containers** (3.18+, experimental): run `@scorer` code for online evaluation in Docker containers with no network. Env: `MLFLOW_SERVER_ENABLE_CUSTOM_SCORERS=true`, `MLFLOW_SERVER_JOB_EXECUTION_ENGINE=executor`, `MLFLOW_JOB_CUSTOM_SCORER_EXECUTOR_BACKEND=docker`, optional `MLFLOW_JOB_IMAGE`. Single replica, non-root, DB backend. `MLFLOW_SERVER_ENABLE_JOB_EXECUTION` default `True`.
- **Webhooks** (experimental, SQL backend, OSS only): events `registered_model.created`, `model_version.created`, `model_version_tag.set/deleted`, `model_version_alias.created/deleted`, prompt events (`prompt.created`, `prompt_version.created`, `prompt_alias.created`, ...), `budget_policy.exceeded`. `client.create_webhook(name=, url=, events=[...], description=, secret=)`, `client.test_webhook(id, event=...)`. Signature header `X-MLflow-Signature: v1,<base64>` (HMAC-SHA256 over `delivery_id.timestamp.payload`), plus `X-MLflow-Delivery-Id`, `X-MLflow-Timestamp`. HTTPS only and private IPs blocked by default (`MLFLOW_WEBHOOK_ALLOW_PRIVATE_IPS`). Secrets encrypted with `MLFLOW_WEBHOOK_SECRET_ENCRYPTION_KEY`. Admin-only when auth is on.
- **Demo**: `mlflow demo` / `uvx mlflow demo` (3.10.0).
- **CLI index** (current): `agent`, `ai-commands`, `artifacts`, `assistant`, `autolog`, `crypto`, `datasets`, `db`, `demo`, `deployments`, `doctor` (`--mask-envs`), `experiments`, `gateway`, `gc`, `mcp`, `migrate-filestore`, `models`, `run`, `runs`, `sagemaker`, `scorers`, `server`, `skills`, `traces`.
- **TypeScript SDK**: separate releases (`ts/v0.2.0`); tracing integrations for TS frameworks.

**Official URLs read.**
- https://mlflow.org/docs/latest/genai/mcp/
- https://mlflow.org/docs/latest/genai/mcp-registry/
- https://mlflow.org/docs/latest/genai/skill-registry/
- https://mlflow.org/docs/latest/genai/getting-started/try-assistant/
- https://mlflow.org/docs/latest/genai/eval-monitor/ai-insights/detect-issues/
- https://mlflow.org/docs/latest/self-hosting/job-containers/
- https://mlflow.org/docs/latest/self-hosting/webhooks/

**Gaps / UNVERIFIED.**
- Webhooks minimum version not stated (3.5.0 notes add prompt registry support to webhooks, so they existed before 3.5.0).
- Assistant and issue detection minimum versions not stated on their pages (release notes place assistant engines in 3.13 and issue detection in 3.18).
- The TypeScript SDK docs were not read.

---

## 13. Proposed lesson order

Thirteen lessons. Each lists the sections above that back it. Lessons 1-8 are the classic MLOps core; 9-13 are the GenAI/LLMOps half. Pin `mlflow==3.18.0` in all lesson code.

1. **What MLflow is, and your first server.** Install, `mlflow server` with the SQLite default, the UI, `uvx mlflow demo`, the two doc trees, OSS vs managed. (Sections 0, 1, 3a.)
2. **Tracking experiments and runs.** Params, metrics with steps, tags, artifacts, nested runs, autolog, system metrics, async logging. (Section 2.)
3. **Finding the best run.** `search_runs` filter syntax, datasets with `mlflow.data` and `log_input`, comparing runs. (Section 2.)
4. **What an MLflow model is.** MLmodel file, flavors, pyfunc, signatures and input examples, MLflow 3 `name=` and `model_id`, checkpoints linked to metrics, `search_logged_models`. (Sections 2, 4.)
5. **Custom models and their dependencies.** `PythonModel` with type hints, models-from-code, `requirements.txt`/uv, `mlflow.models.predict` env check, pickle risk and `MLFLOW_ALLOW_MODEL_CODE_EXECUTION`. (Section 4.)
6. **The Model Registry.** Versions, aliases (`@champion`), tags, why stages are deprecated, promoting across environments with `copy_model_version`, registry webhooks. (Sections 5, 12.)
7. **Serving a model.** `mlflow models serve`, `/invocations` payload formats, `/ping`, `build-docker`, a note that MLServer and the KServe tutorial are gone, `mlflow deployments`. (Section 6a.)
8. **A team tracking server.** PostgreSQL + S3-compatible storage (the official Docker Compose with RustFS, or MinIO via `MLFLOW_S3_ENDPOINT_URL`), proxied vs direct artifacts, `mlflow db upgrade`, `mlflow gc`, file-store migration, Helm chart. (Sections 3a, 3b, 3c.)
9. **Securing the server.** Allowed hosts and CORS, basic auth with a strong admin password, RBAC roles, workspaces, SSO options, reverse proxy for TLS. (Sections 3d, 3e.)
10. **Tracing an LLM app.** `mlflow.openai.autolog()` / `anthropic` / `langchain` (LangGraph), `@mlflow.trace`, `start_span`, span types, sessions and users, `search_traces`. (Section 7.)
11. **Tracing in production and OpenTelemetry.** `mlflow-tracing`, async queue settings, sampling, OTLP ingest at `/v1/traces`, export and dual export, PII masking pointer. (Section 7.)
12. **Evaluating GenAI apps.** `mlflow.genai.evaluate`, built-in judges, `make_judge`, `@scorer`, evaluation datasets, human feedback, `compare_evaluations` as a CI gate; contrast with `mlflow.models.evaluate` for classic ML. (Section 8.)
13. **Prompts, versions and GenAI operations.** Prompt Registry with aliases, `optimize_prompts`, `set_active_model` and Git versioning, AI Gateway (endpoints, fallbacks, guardrails, key encryption), automatic evaluation and issue detection, the MCP server. (Sections 6b, 8, 9, 10, 12.)

Optional extra: **MLflow Projects** (section 11) as a short appendix, not a core lesson.

---

## 14. Version and deprecation notes

**What changed from 2.x to 3.x (MLflow 3 migration guide and release notes).**
- LoggedModel is a first-class entity with `model_id`. `log_model` no longer needs a run. `artifact_path` → `name`. New URI `models:/<model_id>`. Model artifacts moved out of run artifacts to `experiments/<exp>/models/<model_id>/artifacts/`; the run Artifacts tab no longer shows models.
- `runs:/<run_id>/model` URIs: deprecated, "will be removed in future".
- Removed in 3.0: MLflow Recipes; flavors `fastai`, `mleap`, `gluon`; `diviner` and `promptflow` (removed in 3.7.0); AI Gateway `routes`/`route_type` keys; the deployment server and `start-server` CLI; `run_info.run_uuid` (use `run_id`); git tags `mlflow.gitBranchName`, `mlflow.gitRepoURL`; TF autolog `every_n_iter`; `example_no_conversion`, `code_path`, PyTorch `requirements_file`, Transformers `inference_config`; `ModelInfo.signature_dict`; evaluation `baseline_model` and `custom_metrics`; `MLFLOW_GCS_DEFAULT_TIMEOUT`. `higher_is_better` → `greater_is_better`. Explainer logging off by default.
- `mlflow.evaluate` for LLMs: deprecated since 3.0.0; use `mlflow.genai.evaluate`. `mlflow.models.evaluate` remains the classic API.
- ChatModel / ChatAgent: not called deprecated, but "Starting in MLflow 3.0.0, we recommend ResponsesAgent instead of ChatModel."
- `mlflow.openai.log_model()`: called "deprecated" on the GenAI Packaging page.
- Upgrade client and server together. 3.x reads 2.x data, not the reverse. Stay on 2.x with `pip install 'mlflow<3'`.

**Changes inside the 3.x line that lessons must respect.**
- 3.5.0: FastAPI/uvicorn server with security middleware (`--allowed-hosts`, `--cors-allowed-origins`, `--x-frame-options`). `optimize_prompt` removed; use `optimize_prompts`. Prompt webhooks.
- 3.6.0: OTLP ingestion at `/v1/traces`. File store called deprecated in the Search Traces page.
- 3.7.0: **SQLite is the default backend** (`sqlite:///mlflow.db`).
- 3.10.0: Workspaces, `mlflow migrate-filestore`, demo experiment.
- 3.11.0: `session_id` and `user` arguments for traces.
- 3.12: `--static-prefix` also applies to REST and other API routes.
- 3.13.0: RBAC replaces per-resource permissions (old APIs removed); **MLServer removed** (`--enable-mlserver` gone); **file store raises an error unless `MLFLOW_ALLOW_FILE_STORE=true`**; official Helm chart; `judge.align()` default optimizer is MemAlign; `mlflow autolog claude` uses a Claude plugin. The Kubernetes/KServe model-deployment tutorial is gone from the docs from this version.
- 3.15.0: MCP Registry; presigned direct artifact transfer.
- 3.17.0: DENY and sub-resource RBAC tiers; trace rollups; coordinated DB upgrade with writers stopped.
- 3.18.0: `MLFLOW_ALLOW_MODEL_CODE_EXECUTION` added; `MLFLOW_ALLOW_PICKLE_DESERIALIZATION` deprecated; pickle-free formats to become default later; `compare_evaluations`, Skill Registry, online code scorers in job containers (all experimental); `models:/` downloads drop `registered_model_meta`; CVE-2026-53995 path traversal fix in FileStore trace handling.

**Long-standing deprecations.**
- Model Registry **stages**: deprecated since 2.9.0, "will be removed in a future major release". Use aliases.
- `mlflow gateway start --config-path` YAML gateway: labelled "legacy" in the env var reference but still in the CLI reference.
- `custom_prompt_judge`: deprecated in favor of `make_judge`.

**Doc inconsistencies found (do not copy these into lessons without checking).**
- Default backend shown as `mlruns` on the Architecture overview and Tracking overview (stale) vs SQLite elsewhere.
- File store described three different ways (to be deprecated / deprecated in 3.6 / errors by default in 3.13).
- Stages described without deprecation on the ML overview and Registry overview.
- Docker Compose storage named MinIO on one page, RustFS on others and in the repo.
- `Correctness` expectation key (`expected_response` vs `expected_facts`).
- `Safety` / `RetrievalRelevance` called Databricks-only but used in OSS examples.
- Version Tracking overview and Compare App Versions pages have code that will not run as written.
- Basic auth examples use a password shorter than the documented 12-character minimum.
- Docker image page shows an old `v2.0.1` tag.
- `SpanType.LLM` used in examples but missing from the span type table.

---

## 15. Consolidated gaps (not confirmed on a fetched official page)

1. Whether `mlflow ui` still exists (absent from the CLI reference index).
2. A current official Kubernetes model-serving tutorial (the old KServe one was removed at 3.13 and relied on MLServer).
3. Container port and runtime behaviour of `build-docker` images without MLServer.
4. Full `mlflow.autolog()` argument defaults; `search_runs` `output_format` and `max_results` default.
5. Python `MlflowClient` logging signatures; `log_dict`/`log_figure`/`log_image`/`log_table`/`log_text` signatures.
6. Full `MLmodel` field list for 3.18 (`model_id`, `artifact_path`, `utc_time_created`, ...).
7. `PythonModelContext`, `artifacts=` and `ModelConfig` details.
8. AI Gateway full provider list, endpoint types, rate limits, and Windows support.
9. `mlflow-tracing` package version and size claim currency.
10. `span.add_event`, `span.set_status`, `start_span_no_context`, `get_last_active_trace_id`.
11. `genai.evaluate(model_id=...)` and `log_model_params` for LoggedModels.
12. Whether `optimize_prompts` registers a new prompt version; GEPA package requirements.
13. Review queues / labeling sessions in open source.
14. Minimum versions for webhooks, AI Assistant, issue detection, workspaces (from docs pages; release notes give approximate versions).
15. Release notes for 3.4, 3.6, 3.8, 3.9, 3.11, 3.12, 3.14, 3.16 were not read; changes in those versions may be missing above.
