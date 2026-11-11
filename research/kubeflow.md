# Research notes: Kubeflow (Pipelines, Trainer, Katib, KServe, Hub, and the platform)

Date of research: 2026-11-11. Sources are kubeflow.org, the official Kubeflow sub-sites (trainer.kubeflow.org, sdk.kubeflow.org, spark.kubeflow.org), the official GitHub repos (kubeflow/community-distribution, formerly kubeflow/manifests; kubeflow/pipelines; kubeflow/trainer; kubeflow/katib; kubeflow/hub, formerly kubeflow/model-registry; kubeflow/sdk; kserve/kserve), the KServe docs at kserve.github.io/website, the CNCF site and PyPI. "Read" means the page was fetched and summarized by the fetch tool. Items marked UNVERIFIED were not confirmed on a fetched official page.

Note on method: pages were read through a fetch tool that returns summaries, not raw text. Quotes are short. GitHub release pages show day and month but not the year; years below come from PyPI upload dates or the release tag scheme, and are marked when inferred. Check each page before quoting it in a lesson.

Big changes since most tutorials were written (read these first):
- Kubeflow graduated in the CNCF (announced 2026-08-17).
- The installer repo `kubeflow/manifests` is now `kubeflow/community-distribution`, and the bundle is called the "Kubeflow Community Distribution" (KCD). Releases now use Year.Month tags (26.03, 26.10).
- Model Registry is renamed "Kubeflow Hub" (repo `kubeflow/hub`). The Python package is still `model-registry`.
- Katib is deprecated (deprecation 2026-11-01, archive 2027-11-01). Its replacement is the alpha `OptimizationJob` API in Kubeflow Trainer.
- KServe is listed as a Kubeflow "Ecosystem" project, not a subproject. KServe's own README calls it a CNCF incubating project.
- KFP replaced MinIO with SeaweedFS as the default object store (from KFP 2.15).
- Workspaces (Notebooks v2) is on by default in KCD 26.10.0; Notebooks v1 is off by default and scheduled for removal in 27.03.

---

## K1. What Kubeflow is now: subprojects, distributions, lifecycle map

**Plain explanation.** Kubeflow is a set of open source projects that run AI work on Kubernetes. Each project does one job: notebooks, pipelines, training, tuning, a model registry, Spark. You can install one project on its own, or install many together as a "distribution". The community keeps one free reference bundle, the Kubeflow Community Distribution. Companies sell or support others. Some well-known tools, like KServe and Feast, are not Kubeflow projects. Kubeflow lists them as "ecosystem" projects that work well with it.

**Documented facts.**
- Kubeflow calls itself "_the_ Cloud Native AI platform", made of modular open source projects (introduction page, read).
- Subprojects named on the introduction page: Kubeflow SDK, Spark Operator, Notebooks, Workspaces, Trainer, MCP Server, Katib, Hub, Pipelines, Dashboard, Kale.
- Subprojects are "designed to be usable both independently and as part of the Kubeflow Distribution" (introduction page).
- Ecosystem projects: Feast (feature store), Elyra (JupyterLab UI for KFP), KServe (inference platform), OGX ("vendor-neutral generative AI application server"). The ecosystem page says these are "not governed by the Kubeflow community" and are "developed and supported by their respective maintainers".
- Maturity table on the install page:
  - Graduated: Kubeflow Hub, Notebooks, Pipelines, Spark Operator, Trainer.
  - Incubating: Kale, Kubeflow SDK.
  - Experimental ("Progressing"): Kubeflow MLflow Integration, MCP Server, MCP Spark History Server, Semantic Operator.
  - Deprecated: Katib. "Deprecation is November 1, 2026, and archiving is November 1, 2027."
- Lifecycle map on the architecture page, five stages: "Data Preparation", "Model Development", "Model Training", "Model Optimization", "Model Serving".
  - Data Preparation: Spark Operator ("can be used for data preparation and feature engineering step").
  - Model Development: Notebooks.
  - Model Training: Trainer (distributed training, LLM fine-tuning).
  - Model Optimization: Trainer's OptimizationJob APIs (hyperparameter tuning).
  - Model Serving: no subproject is mapped; Kubeflow Hub "helps prepare models for production serving".
  - Pipelines spans the whole lifecycle. Dashboard exposes the UIs. The SDK gives "unified Pythonic APIs".
- The architecture page also splits the lifecycle into development and production phases (diagram only; no text).
- Kubeflow graduated in the CNCF. CNCF announcement dated "August 17, 2026": "CNCF has graduated Kubeflow, recognizing the open source project as a mature, production-ready platform".
- KServe governance: KServe's README says it is a "Cloud Native Computing Foundation (CNCF) incubating project" and an "important addon component of Kubeflow". The KServe site footer says "a Series of LF Projects, LLC".
- Naming: the 26.03 GitHub release was titled "26.03 Kubeflow AI Reference Platform". The 26.10.0 release and the repo README are titled "Kubeflow Community Distribution". The README body says it helps "install the Kubeflow Platform". The docs use "Kubeflow Community Distribution (KCD)".

**Official URLs read.**
- https://www.kubeflow.org/docs/started/introduction/
- https://www.kubeflow.org/docs/started/architecture/
- https://www.kubeflow.org/docs/components/
- https://www.kubeflow.org/docs/started/installing-kubeflow/
- https://www.kubeflow.org/docs/ecosystem/
- https://www.kubeflow.org/docs/ecosystem/kserve/
- https://www.cncf.io/announcements/2026/08/17/cncf-announces-kubeflows-graduation/
- https://raw.githubusercontent.com/kserve/kserve/master/README.md
- https://kserve.github.io/website/
- https://github.com/kubeflow/community-distribution

**Gaps / UNVERIFIED.**
- KServe's CNCF incubating acceptance date. The CNCF blog URL in search results is dated 2025-11-11 (https://www.cncf.io/blog/2025/11/11/kserve-becomes-a-cncf-incubating-project/); a CNCF slide page says 2025-09-29. Not fetched. UNVERIFIED.
- The Kubeflow docs never say in words that KServe "left" Kubeflow. They only list it as Ecosystem. Search summaries (not official) say KServe began as KFServing under Kubeflow in 2019 and moved to LF AI & Data in 2022. UNVERIFIED.
- The architecture diagrams are images. Their content was not read.
- The CNCF TOC vote date (2026-07-24, from a news site) is UNVERIFIED.

---

## K2. Installation: standalone vs Community Distribution vs vendor distributions; multi-user

**Plain explanation.** There are three ways in. One: install only the project you need, for example just Pipelines, with one or two `kubectl apply -k` commands. Two: install the Community Distribution, which brings everything plus login, user isolation and the dashboard. Three: use a vendor's packaged version. The full bundle is heavy. It wants about 16 GB of RAM and 8 CPU cores. In the full bundle, Istio routes traffic, Dex handles login, oauth2-proxy checks the login on every request, and each user gets a "Profile", which is a Kubernetes namespace with permissions.

**Documented facts.**
- Install options page: subprojects "can be deployed as a standalone services, without the need to install the entire Kubeflow distribution". It recommends the latest stable KCD release for a conservative setup; it names the `v26.03.1` release branch (page not yet updated for 26.10.0 at time of reading).
- Vendor distributions table (community "does not endorse or certify" any): Canonical Charmed Kubeflow (1.11), prokube.ai prokube MLOps (26.03), Microsoft Azure on AKS (26.03), Nutanix (1.10), QBO GPU Cloud (1.10), Red Hat Open Data Hub on OpenShift (26.03).
- Current KCD release: `26.10.0`, published 06 Nov (2026, inferred from tag scheme), marked Latest. Pre-release `26.10.0-rc1` on 03 Nov. Prior: `26.03.1` (15 Jun), `26.03` (22 Mar), and the older 1.11.0 line.
- KCD 26.10.0 bundled versions (release notes and README): Trainer v2.4.0 (JobSet 0.13.0), Notebooks v1.11.1, Workspaces 2.0.0, Dashboard v2.0.1, Katib v0.19.0 (README table), KServe v0.21.0, KServe UI v1.1.0, Pipelines 2.18.0 (with `kfp` and `kfp-kubernetes` 2.18.0), Hub v0.3.18, Spark Operator 2.5.2, Istio 1.31.3, Knative Serving/Eventing v1.24.0, cert-manager 1.21.2, Dex 2.46.1, OAuth2-Proxy 7.15.5.
- Kubernetes: CI covers Kubernetes 1.35 to 1.37.0; full E2E on 1.35 and 1.37 (26.10.0 notes). README says to "consult the release notes" for versions.
- KinD script `tests/install_KinD_create_KinD_cluster_install_kustomize.sh` (read): `KIND_VERSION="v0.33.0"`, node image `kindest/node:v1.37.0@sha256:...`, `KUSTOMIZE_VERSION="v5.8.1"`, kubectl derived from the node image tag (v1.37.0 by default; "kubectl must stay within +/-1 minor of the API server"). Cluster name `kubeflow`. Config: 1 control-plane + 2 worker nodes; API server extra args `service-account-issuer=https://kubernetes.default.svc` and `service-account-signing-key-file=/etc/kubernetes/pki/sa.key`. No port mappings.
- Hardware (README): "16+ GB of RAM recommended." and "8 CPU cores recommended." Minimal: "You can exclude components from the `example/kustomization.yaml` to fit Kubeflow into 4-8 GB of memory and 2-4 CPU cores."
- Resource table (README, "maximum of actual usage and configured requests"):

  | Component | CPU | Memory | PVC |
  |---|---|---|---|
  | Trainer v2.4.0 | 8m | 143Mi | 0GB |
  | Notebooks v1.11.1 | 43m | 806Mi | 0GB |
  | Dashboard v2.0.1 | 10m | 302Mi | 0GB |
  | Katib v0.19.0 | 13m | 476Mi | 10GB |
  | KServe UI v1.1.0 | 6m | 259Mi | 0GB |
  | KServe v0.21.0 | 600m | 1200Mi | 0GB |
  | Pipelines 2.18.0 | 970m | 3552Mi | 35GB |
  | Hub v0.3.18 | 510m | 2112Mi | 20GB |
  | Spark Operator 2.5.2 | 9m | 41Mi | 0GB |
  | Istio 1.31.3 | 750m | 2364Mi | 0GB |
  | Knative v1.24.0 | 1450m | 1038Mi | 0GB |
  | Cert Manager 1.21.2 | 3m | 128Mi | 0GB |
  | Dex 2.46.1 | 3m | 27Mi | 0GB |
  | OAuth2-Proxy 7.15.5 | 3m | 27Mi | 0GB |
  | Total | 4377m | 12316Mi | 65GB |

- Other prerequisites: container runtime `podman` (preferred) or `docker`. Linux inotify limits: `sudo sysctl fs.inotify.max_user_instances=2280` and `sudo sysctl fs.inotify.max_user_watches=1255360`. ARM64 "not fully supported yet".
- After creating the cluster: `kind get kubeconfig --name kubeflow > /tmp/kubeflow-config` and `export KUBECONFIG=/tmp/kubeflow-config`. Optional `regcred` secret for Docker Hub pull limits.
- Single-command install (re-run until it succeeds; README wraps it in a retry loop): `kustomize build example | kubectl apply --server-side --force-conflicts -f -`
- Step-by-step order (README): kubeflow namespace; cert-manager (`./tests/cert_manager_install.sh`); Istio CNI (`./tests/istio-cni_install.sh`); OAuth2-Proxy overlay (option 1 `m2m-dex-only` works on most clusters); Kubeflow Istio resources; multi-tenancy (`./tests/multi_tenancy_install.sh`); Dex (`./tests/dex_install.sh`); Dashboard incl. PodDefaults webhook (`./tests/dashboard_install.sh`); Knative Serving (Eventing optional); KServe + KServe UI in namespace `kserve` (`./tests/kserve_install.sh`); Pipelines (`./tests/pipelines_install.sh`); Katib; Workspaces; Trainer; Spark Operator; user namespace (`export KF_PROFILE=kubeflow-user-example-com` then `./tests/kubeflow_profile_install.sh`).
- Access: `kubectl port-forward svc/istio-ingressgateway -n istio-system 8080:80`, open `http://localhost:8080`. Default login: `user@example.com` / `12341234` (README and dashboard access page).
- Exposing via NodePort/LoadBalancer/Ingress needs HTTPS because web apps use secure cookies. `APP_SECURE_COOKIES=false` allows HTTP but is advised against.
- Changing the password: hash with passlib bcrypt (12 rounds, `2y`), put it in `DEX_USER_PASSWORD` in `common/dex/base/dex-passwords.yaml` before install; after install, `kubectl delete secret dex-passwords -n auth`, recreate it, then `kubectl delete pods --all -n auth`. Username/email in `common/dex/overlays/oauth2-proxy/config-map.yaml` under `staticPasswords`.
- Dex is an OIDC provider with a static test user; add connectors for Azure, GitHub, Google, Keycloak. OAuth2-Proxy is the OIDC client for the Istio ingress gateway and supports machine-to-machine tokens. Authorization uses Kubernetes RBAC and Istio authorization policies. Istio uses Istio CNI (no privileged init containers).
- Upgrade cautions (README): "Never delete the `Profiles` CRD" (it removes every profile namespace). For 26.03.1 to 26.10.0, switch `ml-pipeline-ui` Deployment strategy to `Recreate` first. KServe control plane moves to the `kserve` namespace. Helm charts (1:1 with Kustomize) are new and "experimental".
- Profiles (dashboard docs): `apiVersion: kubeflow.org/v1`, `kind: Profile`, `metadata.name` becomes the namespace name, `spec.owner` (kind `User`, email name), optional `plugins` and `resourceQuotaSpec`. A profile creates: the namespace; owner RoleBinding `namespaceAdmin` to `ClusterRole/kubeflow-admin`; contributor RoleBindings to `kubeflow-edit` or `kubeflow-view`; ServiceAccounts `default-editor` (kubeflow-edit) and `default-viewer` (kubeflow-view); Istio AuthorizationPolicy `ns-owner-access-istio` plus one per contributor. Commands: `kubectl get profiles`, `kubectl describe profile <name>`, `kubectl delete profile <name>` (deletes the namespace). Self-registration off by default; enable with `CD_REGISTRATION_FLOW=true` on the central-dashboard Deployment.

**Official URLs read.**
- https://raw.githubusercontent.com/kubeflow/manifests/master/README.md (resolves to community-distribution)
- https://raw.githubusercontent.com/kubeflow/community-distribution/master/README.md
- https://github.com/kubeflow/manifests/releases (redirects to community-distribution releases)
- https://github.com/kubeflow/community-distribution/releases/tag/26.10.0
- https://raw.githubusercontent.com/kubeflow/community-distribution/master/tests/install_KinD_create_KinD_cluster_install_kustomize.sh
- https://www.kubeflow.org/docs/started/installing-kubeflow/
- https://www.kubeflow.org/docs/components/central-dash/profiles/
- https://www.kubeflow.org/docs/components/central-dash/access/

**Gaps / UNVERIFIED.**
- No kustomize or kubectl minimum version is stated in the README or release notes. Only the KinD script pins kustomize v5.8.1.
- The README does not say which components to drop for the 4-8 GB option.
- The KinD script and `tests/*.sh` are bash. Running them on Windows (WSL2, Git Bash, Docker Desktop) is not documented. The inotify `sysctl` lines are Linux commands. UNVERIFIED for Windows.
- The 26.10.0 notes say "legacy Training Operator was removed (PR #3540)" from the distribution; the PR itself was not read.
- Release years for KCD tags are inferred from the tag scheme.

---

## K3. Kubeflow Pipelines (KFP v2)

### K3.1 Concepts

**Plain explanation.** A pipeline is a recipe of steps. Each step is a "component", which is a small program that runs in its own container. When you use a component inside a pipeline, that use is a "task". Steps pass two kinds of data. "Parameters" are small values like numbers and strings. "Artifacts" are files, like a dataset or a model, stored in object storage. You write the pipeline in Python and "compile" it to a YAML file (the IR YAML). You send that YAML to a KFP server to start a "run". Runs are grouped into "experiments". A "recurring run" starts a new run on a schedule.

**Documented facts.**
- KFP is "a platform for building and deploying portable and scalable machine learning (ML) workflows" (overview).
- A pipeline is a DAG of components; "each component execution maps to one container execution" (overview summary).
- Pipelines compile to IR YAML, a "platform-neutral" definition; it can run on open-source KFP or on Google Vertex AI Pipelines.
- The IR YAML is a serialized `PipelineSpec` protobuf. Header comments: `# PIPELINE DEFINITION`, `# Name:`, `# Description:`, `# Inputs:`, `# Outputs:` (compile page).
- Run: "a single execution of a pipeline". Recurring run: also called a "job" in backend APIs; it "will periodically start a new copy of the run configuration"; it has a max concurrency setting; it can be enabled or disabled in the UI (run concept page).
- Concept pages exist for: Pipeline, Pipeline Root, Component, Graph, Experiment, Run, Step, Output Artifact, IR YAML, ML Metadata.
- "components are actually pipelines" (compile page): a component can be compiled alone.

### K3.2 Authoring components

**Plain explanation.** There are three ways to write a component. A lightweight Python component is a plain function with type hints and `@dsl.component`; KFP copies the function's source into a stock Python image at run time. A containerized Python component is the same function, but KFP builds a Docker image for it with `kfp component build`, so it can import your other files. A container component wraps any image and command you choose, with `@dsl.container_component`.

**Documented facts.**
- Lightweight rules: valid type annotations; "The Python function may not reference any symbols defined outside of its body."; "Imports must also be included in the function body."
- Full `@dsl.component` signature (SDK reference, release-2.18): `component(func=None, *, base_image=None, target_image=None, packages_to_install=None, pip_index_urls=None, output_component_file=None, install_kfp_package=True, kfp_package_path=None, pip_trusted_hosts=None, use_venv=False, additional_funcs=None, embedded_artifact_path=None, task_config_passthroughs=None, artifact_previews=True, artifact_preview_rows=True)`.
- Default base image in SDK source: `_DEFAULT_BASE_IMAGE = 'python:3.11'`. A `FutureWarning` says it "will switch from 'python:3.11' to 'python:3.12' on Oct 1, 2027" and tells you to pass an explicit `base_image`.
- `packages_to_install` installs at task runtime, e.g. `@dsl.component(packages_to_install=['numpy==1.21.6'])`. For production the docs say to prefer containerized components.
- `pip_index_urls`: when set, PyPI is not added automatically; add `'https://pypi.org/simple'` yourself. (KFP 2.18 notes: generated install commands no longer add `--trusted-host` automatically.)
- `additional_funcs` adds helper functions; `embedded_artifact_path` embeds a local file or directory, read through `dsl.EmbeddedInput[T]`.
- Containerized: `@dsl.component(base_image='python:3.11', target_image='gcr.io/my-project/my-component:v1')`. Build: `kfp component build src/ --component-filepattern my_component.py --no-push-image` (or `--push-image`). Needs `pip install kfp[all]` (CLI page).
- Container component:
  ```python
  @dsl.container_component
  def say_hello():
      return dsl.ContainerSpec(image='alpine', command=['echo'], args=['Hello'])
  ```
  Outputs use `dsl.OutputPath(str)`; the container writes the value to that path. Access with `task.outputs['greeting']`. Placeholders `dsl.ConcatPlaceholder([...])` and `dsl.IfPresentPlaceholder(input_name=..., then=[...], else_=[...])` work only inside a container component's `ContainerSpec`.
- Other component kinds listed in the docs: Notebook Python Components (`dsl.notebook_component`), Importer components (`dsl.importer(artifact_uri, artifact_class, reimport=False, metadata=None, download_to_workspace=False)`).

### K3.3 Parameters and artifacts

**Plain explanation.** Use parameters for small values and artifacts for files. For an artifact you write to `.path`; KFP uploads it to the object store for you. Metrics and classification metrics are special artifacts that the KFP UI can draw.

**Documented facts.**
- Parameter types: `str`, `int`, `float`, `bool`, `list`/`typing.List`, `dict`/`typing.Dict`. All parameters are serialized as JSON. Defaults work like normal Python. Multiple outputs: `typing.NamedTuple('outputs', a=int, b=str)`, read with `task.outputs['<key>']`.
- Artifact classes and schema titles: `Artifact` (`system.Artifact`), `Dataset`, `Model`, `Metrics`, `ClassificationMetrics`, `SlicedClassificationMetrics`, `HTML`, `Markdown`. "Artifact is also compatible with all other artifact types."
- Artifact properties: `.name`, `.uri`, `.metadata` (dict), `.path` (local path mapped to `.uri`). "input artifacts should be treated as immutable."
- Traditional syntax (works on open-source KFP): `def my_component(in_artifact: Input[Artifact], out_artifact: Output[Artifact]):`. Output artifacts are passed in; write to `.path`. "You should not return the artifact instance from your component."
- Pythonic syntax (`def train_model(dataset: Dataset) -> Model:` with `dsl.get_uri()`) is "currently supported at runtime only by Vertex Pipelines". The open-source backend does not support it yet. Teach the `Input[...]`/`Output[...]` style.
- Metrics methods (SDK reference): `Metrics.log_metric(metric: str, value: float)`; `ClassificationMetrics.log_confusion_matrix(categories, matrix)`, `log_roc_curve(fpr, tpr, threshold)`, `log_confusion_matrix_cell(...)`, `log_confusion_matrix_row(...)`.
- Lists of artifacts: `List[Artifact]` or `Input[List[Artifact]]`, usually from `dsl.Collected`.
- Pipeline Run Workspaces (KFP 2.15.0+): `dsl.WorkspaceConfig(size=...)` via `pipeline_config`; artifacts live on a PVC; `dsl.WORKSPACE_PATH_PLACEHOLDER` (e.g. `/kfp-workspace`).
- Default pipeline root: "By default `defaultPipelineRoot` is `minio://mlpipeline/v2/artifacts`" (object store page). Bucket name `mlpipeline`.
- KFP 2.18 adds Dataset and Model previews in run details, Pydantic `BaseModel` inputs/outputs, init containers, DRA, and custom task cache keys (release notes).

### K3.4 Pipelines, task settings, control flow, caching

**Plain explanation.** A pipeline is a Python function with `@dsl.pipeline`. Calling a component inside it makes a task. Tasks that pass data run in order; others run in parallel. You can set CPU, memory, GPU, retries, environment variables and caching on each task. You can branch with `dsl.If`, loop with `dsl.ParallelFor`, gather loop results with `dsl.Collected`, and run a clean-up step with `dsl.ExitHandler`. A pipeline can be used as a step inside another pipeline.

**Documented facts.**
- `@dsl.pipeline(func=None, *, name=None, description=None, pipeline_root=None, display_name=None, pipeline_config=None)` (SDK reference).
- Task outputs: `.output` (single unnamed output) or `.outputs['key']`.
- `PipelineTask` methods (SDK reference, release-2.18):
  - `set_cpu_request(cpu)`, `set_cpu_limit(cpu)`, `set_memory_request(memory)`, `set_memory_limit(memory)`
  - `set_accelerator_type(accelerator)`, `set_accelerator_limit(limit)` (`add_node_selector_constraint` is deprecated in favor of `set_accelerator_type`)
  - `set_caching_options(enable_caching: bool, cache_key: str | None = None)`
  - `set_retry(num_retries, backoff_duration=None, backoff_factor=None, backoff_max_duration=None, policy=None)`
  - `set_env_variable(name, value)`, `set_display_name(name)`, `set_container_image(name)`, `set_debug_pause(...)`
  - `after(*tasks)`, `ignore_upstream_failure()`
- Note: the "compose components" page lists `.add_accelerator_type` and says `.ignore_upstream_failure` is "not yet supported by the KFP orchestration backend", while the control-flow page documents `ignore_upstream_failure()` as working. The two pages disagree.
- Special placeholders, e.g. `dsl.PIPELINE_JOB_NAME_PLACEHOLDER`, `dsl.PIPELINE_TASK_ID_PLACEHOLDER`. Not yet supported by the KFP backend: `PIPELINE_JOB_CREATE_TIME_UTC_PLACEHOLDER`, `PIPELINE_JOB_SCHEDULE_TIME_UTC_PLACEHOLDER`, `PIPELINE_ROOT_PLACEHOLDER`.
- Control flow (control-flow page):
  - `with dsl.If(coin_flip_task.output == 'heads'):` ; `dsl.Elif` and `dsl.Else` must be "immediately downstream" of `dsl.If`. "The `dsl.Condition` is deprecated in favor of the functionally identical `dsl.If`."
  - `dsl.OneOf(t1.output, t2.output, t3.output)` merges outputs of mutually exclusive branches; one branch must be `dsl.Else`.
  - `with dsl.ParallelFor(items=[1, 5, 10, 25], parallelism=2) as epochs:` ; "parallelism=0 indicates unconstrained parallelism."
  - `dsl.Collected` gathers loop outputs; nested-loop parameters become nested lists; artifacts become a "_flat_ list".
  - `with dsl.ExitHandler(exit_task=clean_up_task):` ; like `try`/`finally`. Exit task can take a `dsl.PipelineTaskFinalStatus` parameter (fields `state`, `pipeline_job_resource_name`, `pipeline_task_name`, `error_code`, `error_message`).
- Pipelines as components: a `@dsl.pipeline` function can be called inside another pipeline like a component (example `square_and_sum` inside `pythagorean`).
- Caching (caching page): "Caching is enabled by default for all components in KFP." Cached tasks show a green "arrow from cloud" icon.
  - Per task: `task.set_caching_options(False)`.
  - Per run: `enable_caching=` on `client.create_run_from_pipeline_func(...)` overrides all tasks.
  - Compile time: `kfp dsl compile --disable-execution-caching-by-default`, or env var `KFP_DISABLE_EXECUTION_CACHING_BY_DEFAULT=true` (must be set before importing KFP components).
  - KFP 2.18: custom cache keys "replace the automatic input, image, command, argument, and PVC-name contributions"; legacy V1 cache entries with unknown ownership are no longer reused, so some tasks may rerun.

### K3.5 Compile, client, CLI

**Plain explanation.** `Compiler().compile()` turns your Python pipeline into YAML. `kfp.Client` talks to the KFP server: it can upload pipelines, create experiments, and start runs. The `kfp` command-line tool does the same from a terminal.

**Documented facts.**
- `compiler.Compiler().compile(my_pipeline, package_path='pipeline.yaml')`; optional `pipeline_name`, `pipeline_parameters` (dict of defaults), `type_check` (on by default), `kubernetes_manifest_format`, `kubernetes_manifest_options`.
- Kubernetes-native output: with `kubernetes_manifest_format=True` and `KubernetesManifestOptions` (from `kfp.compiler.compiler_utils`; fields `pipeline_name`, `pipeline_display_name`, `pipeline_version_name`, `pipeline_version_display_name`, `namespace`, `include_pipeline_manifest`), the compiler emits `Pipeline` and `PipelineVersion` resources, apiVersion `pipelines.kubeflow.org/v2beta1`, applied with `kubectl apply -f`. Needs KFP 2.14.0+ in native API mode.
- `kfp.Client` constructor params: `host`, `client_id`, `namespace` (default `kubeflow`), `other_client_id`, `other_client_secret`, `existing_token`, `cookies`, `proxy`, `ssl_ca_cert`, `kube_context`, `credentials`, `ui_host`, `verify_ssl`.
- Client methods: `create_experiment(name, description, namespace)`, `get_experiment`, `list_experiments`, `upload_pipeline(pipeline_package_path, pipeline_name, description, namespace)`, `upload_pipeline_version(...)`, `create_run_from_pipeline_func(pipeline_func, arguments, run_name, experiment_name, namespace, pipeline_root, enable_caching, cache_key, service_account, experiment_id)`, `create_run_from_pipeline_package(pipeline_file, arguments, ...)`, `run_pipeline(experiment_id, job_name, pipeline_package_path, params, pipeline_id, version_id, ...)`, `create_recurring_run(experiment_id, job_name, ..., interval_second, cron_expression, max_concurrency, no_catchup, ...)`, `wait_for_run_completion(run_id, timeout, sleep_duration)`, `get_run(run_id)`, `list_runs(...)`. `cron_expression` takes six fields.
- Getting started: `pip install kfp`; `client = Client(host='<MY-KFP-ENDPOINT>')`; `client.create_run_from_pipeline_package('pipeline.yaml', arguments={'recipient': 'World'})`.
- Connecting to standalone KFP from your laptop: `kubectl port-forward --namespace kubeflow svc/ml-pipeline-ui 3000:80` then `kfp.Client(host="http://localhost:3000")`. In-cluster: `kfp.Client(host="http://ml-pipeline-ui:80")` or `http://ml-pipeline-ui.{namespace}`.
- Connecting to full KCD from outside: port-forward `svc/istio-ingressgateway` 8080:80 and use the `KFPClientManager` helper class from the docs, which logs in to Dex and builds `kfp.Client(host=..., cookies=...)` with `api_url="http://localhost:8080/pipeline"`.
- Inside KCD: `kfp.Client()` reads a token from `KF_PIPELINES_SA_TOKEN_PATH` (default `/var/run/secrets/kubeflow/pipelines/token`); provide it with a projected service account token (audience `pipelines.kubeflow.org`, `expirationSeconds: 7200`) or a `PodDefault` selecting label `access-ml-pipeline: "true"`.
- CLI: `kfp [OPTIONS] COMMAND`; `kfp --endpoint http://my_kfp_endpoint.com run list`; resources `run`, `recurring-run`, `pipeline`, `experiment` with actions `create`, `list`, `get`, `delete` (+ `archive`/`unarchive`, `disable`/`enable`, `create-version`, etc.). Compile: `kfp dsl compile --py path/to/pipeline.py --output path/to/output.yaml [--function my_pipeline] [--pipeline-parameters '{"param1": 2.0}']`. Run: `kfp run create --experiment-name "my-experiment" --package-file "./path/to/pipeline.yaml"`.
- UI flow: Pipelines tab, `+ Upload pipeline` (.yaml, .zip, .tar.gz), then Runs tab, `+ Create run`.

### K3.6 Local execution (no cluster)

**Plain explanation.** You can run components and simple pipelines on your own machine with `kfp.local`. The Docker runner starts one container per task and is closest to the real thing. The subprocess runner runs tasks as local Python processes, inside a virtual environment, and only supports lightweight Python components. Branches, loops and exit handlers do not run locally yet.

**Documented facts.**
- `local.init(runner=local.DockerRunner())` or `local.init(runner=local.SubprocessRunner(use_venv=False))`.
- `init()` signature in source: `init(runner, pipeline_root: str = './local_outputs', workspace_root: Optional[str] = None, raise_on_error: bool = True, enable_caching: bool = False, cache_root: Optional[str] = None)`.
- `SubprocessRunner(use_venv: bool = True)`. `DockerRunner(max_concurrent_pip_installs: int = 1, **container_run_args)`; `container_run_args` follow the docker SDK `containers.run` except `image`, `command`, `volumes`.
- DockerRunner is "recommended", supports all component types, mounts the pipeline root so outputs stay on disk. SubprocessRunner "Supports only Lightweight Python Components".
- Supported locally: calling components and pipelines like functions (outputs are real values, e.g. `assert task.output == 3`), sequential and nested pipelines, artifacts.
- Not supported or ignored locally: `dsl.Condition`, `dsl.ParallelFor`, `dsl.ExitHandler`; `.set_retry` and `.set_caching_options` have no effect; resource methods (`.set_memory_limit`, `.set_accelerator_type`) have no effect; cloud auth; Container Components with SubprocessRunner.

### K3.7 kfp-kubernetes extension

**Plain explanation.** Plain KFP code is platform-neutral. When you need Kubernetes-only features, like mounting a secret or a volume, you add the `kfp-kubernetes` package. Its functions take a task and change the pod it will run in.

**Documented facts.**
- Install `pip install kfp[kubernetes]`; import `from kfp import kubernetes`. Version 2.18.0 on PyPI (2026-10-28).
- Functions shown in the package README: `use_secret_as_env(task, secret_name=..., secret_key_to_env={'password': 'SECRET_VAR'})`, `use_secret_as_volume(task, secret_name=..., mount_path=..., optional=True)`, `use_config_map_as_env(...)`, `use_config_map_as_volume(...)`, `CreatePVC(pvc_name_suffix='-my-pvc', access_modes=['ReadWriteOnce'], size='5Gi', storage_class_name='standard')`, `mount_pvc(task, pvc_name=..., mount_path='/data')`, `DeletePVC(pvc_name=...)`, `add_ephemeral_volume(task, volume_name=..., mount_path=..., access_modes=[...], size='5Gi')`, `add_pod_label(...)`, `add_pod_annotation(...)`, `use_field_path_as_env(task, env_name='KFP_RUN_NAME', field_path=...)`, `set_timeout(task, 20)` (activeDeadlineSeconds), `set_image_pull_policy(task, "Always")`, `set_image_pull_secrets(task, ['secret-name'])`, `set_security_context(task, run_as_user=1000, run_as_group=3000)`.
- Node selectors and tolerations are named in the README intro but no example is shown.
- KFP 2.18 adds Kubernetes Dynamic Resource Allocation for components (needs Kubernetes 1.31+ with DRA enabled and a DRA driver).

### K3.8 Backend architecture and install

**Plain explanation.** The KFP server has an API server that stores pipelines and runs in a database and turns each run into an Argo Workflow. Argo runs the pods. A persistence agent watches those workflows and records their state. Output files go to an S3-style object store, which is now SeaweedFS by default instead of MinIO. Run metadata and lineage go to ML Metadata (MLMD). A web UI shows it all.

**Documented facts.**
- Legacy-v1 intro page: the Pipeline Service "calls the Kubernetes API server to create the necessary Kubernetes resources"; the Persistence Agent "watches the Kubernetes resources created by the Pipeline Service" and persists state in the ML Metadata Service; KFP "stores the metadata in a MySQL database" and artifacts in "an artifact store like SeaweedFS" or Cloud Storage; the UI "gathers data from various services".
- Orchestrator: KFP uses Argo Workflows by default with the Argo Emissary executor (README).
- Argo versions: README at tag 2.18.0 lists "Argo Workflows | v3.7, v4.1" and says "Argo Workflows 3.x remains supported for KFP 2.x, but is deprecated" and "will not be supported by Kubeflow Pipelines 3.0." README on master says "Argo 3.x is not supported on this branch" (tested 4.0.13 and 4.1.6). MySQL v8.
- Object store: "the default object store deployment has been changed to SeaweedFS, replacing the previous deployment of MinIO" (as of KFP 2.15). MinIO "remains fully supported"; legacy MinIO manifests "may be subject to removal in future releases". KCD README: every overlay replaces `minio-service` to route S3 traffic to SeaweedFS.
- Object store config: API server env vars `OBJECTSTORECONFIG_HOST`, `_PORT`, `_REGION`, `_SECURE`, `_ACCESSKEY`, `_SECRETACCESSKEY` on the `ml-pipeline` deployment; launcher config in the `kfp-launcher` ConfigMap `providers` field (S3 `endpoint`, `disableSSL`, `region`, `forcePathStyle`, `credentials.secretRef`; or `fromEnv: true`).
- Named deployments/services seen on docs pages: `ml-pipeline` (API server), `ml-pipeline-ui`, `metadata-grpc-service`, `ml-pipeline-ui-artifact`.
- Database: KFP 2.15 had "a major upgrade to the underlying Gorm backend" with an index migration that "does not support rollback functionality". PostgreSQL overlays (`platform-agnostic-postgresql`, `platform-agnostic-multi-user-postgresql`) are for dev/eval only in 2.18 (MLMD concurrency limitation).
- Standalone install, "development flavor (non-production)" (install page, verbatim):
  ```bash
  export PIPELINE_VERSION=2.18.0
  kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref=$PIPELINE_VERSION"
  kubectl wait --for condition=established --timeout=60s crd/applications.app.k8s.io
  kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/env/dev?ref=$PIPELINE_VERSION"
  ```
  The UI: `kubectl port-forward -n kubeflow svc/ml-pipeline-ui 8080:80`, then http://localhost:8080. "about 3 minutes" to deploy.
- Kubernetes-native API mode: same first three lines, then cert-manager (`kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.18.2/cert-manager.yaml`), then `env/cert-manager/platform-agnostic-k8s-native?ref=$PIPELINE_VERSION`. Pipelines are stored as Kubernetes custom resources. Multi-user variant `platform-agnostic-multi-user-k8s-native` needs Istio. Migration script in `tools/k8s-native`.
- `manifests/kustomize/env` directories (GitHub listing): `aws`, `cert-manager`, `dev-kind` (subfolders `base`, `linux`, `macOS`, `postgres`), `dev`, `gcp`, `openshift`, `plain-multi-user`, `plain`, `platform-agnostic-multi-user-postgresql`, `platform-agnostic-multi-user`, `platform-agnostic-postgresql`, `platform-agnostic`.
- Multi-user (KCD only): experiments belong to a namespace; runs run in the user's namespace; "Pipeline definitions are not isolated and are shared across all namespaces"; MLMD artifacts and executions have no isolation. SDK: `kfp.auth.ServiceAccountTokenVolumeCredentials(path=None)`, `client.create_experiment(..., namespace=...)`, `client.set_user_namespace()` writes `$HOME/.config/kfp/context.json`.
- Versions: backend `2.18.0` (GitHub release 28 Oct 2026, marked Latest), SDK tag `sdk-2.18.0` same day. `kfp` 2.18.0 requires Python `>=3.9.0`; extras `all`, `kubernetes`, `notebooks`. Prior: 2.17.3 (22 Oct), 2.17.2 (04 Sep), 2.17.1 (27 Aug), 2.17.0 (09 Jul). 2.18 also adds export/import of experiments, pipelines, runs and schedules between installs, and optional run retention (off by default).
- Version compatibility page: KFP runtime v2.0.* works with SDK v2.0.*; SDK v1.8.* runs on runtime v2 without v2 features. KCD 26.10.0 notes: KFP v1 SDK support "scheduled for removal in 27.03".

**Official URLs read (K3).**
- https://www.kubeflow.org/docs/components/pipelines/overview/
- https://www.kubeflow.org/docs/components/pipelines/concepts/
- https://www.kubeflow.org/docs/components/pipelines/concepts/run/
- https://www.kubeflow.org/docs/components/pipelines/concepts/metadata/
- https://www.kubeflow.org/docs/components/pipelines/getting-started/
- https://www.kubeflow.org/docs/components/pipelines/interfaces/
- https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/
- https://www.kubeflow.org/docs/components/pipelines/user-guides/components/lightweight-python-components/
- https://www.kubeflow.org/docs/components/pipelines/user-guides/components/containerized-python-components/
- https://www.kubeflow.org/docs/components/pipelines/user-guides/components/container-components/
- https://www.kubeflow.org/docs/components/pipelines/user-guides/components/compose-components-into-pipelines/
- https://www.kubeflow.org/docs/components/pipelines/user-guides/data-handling/artifacts/
- https://www.kubeflow.org/docs/components/pipelines/user-guides/data-handling/parameters/
- https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/control-flow/
- https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/caching/
- https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/execute-kfp-pipelines-locally/
- https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/run-a-pipeline/
- https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/compile-a-pipeline/
- https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/platform-specific-features/
- https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/cli/
- https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/connect-api/
- https://www.kubeflow.org/docs/components/pipelines/operator-guides/
- https://www.kubeflow.org/docs/components/pipelines/operator-guides/installation/
- https://www.kubeflow.org/docs/components/pipelines/operator-guides/configure-object-store/
- https://www.kubeflow.org/docs/components/pipelines/operator-guides/server-config/
- https://www.kubeflow.org/docs/components/pipelines/operator-guides/multi-user/
- https://www.kubeflow.org/docs/components/pipelines/reference/version-compatibility/
- https://www.kubeflow.org/docs/components/pipelines/legacy-v1/introduction/
- https://kubeflow-pipelines.readthedocs.io/en/stable/source/dsl.html
- https://kubeflow-pipelines.readthedocs.io/en/stable/source/client.html
- https://raw.githubusercontent.com/kubeflow/pipelines/master/README.md
- https://raw.githubusercontent.com/kubeflow/pipelines/2.18.0/README.md
- https://raw.githubusercontent.com/kubeflow/pipelines/master/docs/sdk/Architecture.md (image only)
- https://raw.githubusercontent.com/kubeflow/pipelines/master/sdk/python/kfp/dsl/component_factory.py
- https://raw.githubusercontent.com/kubeflow/pipelines/master/sdk/python/kfp/local/config.py
- https://raw.githubusercontent.com/kubeflow/pipelines/master/kubernetes_platform/python/README.md
- https://raw.githubusercontent.com/kubeflow/pipelines/master/manifests/kustomize/README.md
- https://github.com/kubeflow/pipelines/tree/master/manifests/kustomize/env
- https://github.com/kubeflow/pipelines/tree/master/manifests/kustomize/env/dev-kind
- https://github.com/kubeflow/pipelines/releases and /releases/tag/2.18.0
- https://pypi.org/pypi/kfp/json ; https://pypi.org/pypi/kfp-kubernetes/json

**Gaps / UNVERIFIED (K3).**
- The current KFP architecture doc is an image. The scheduled workflow controller (ScheduledWorkflow CRD), the v2 driver and launcher pods, and the cache server are not described in any fetched page. UNVERIFIED as described components.
- Doc conflict: the lightweight page says the default base image is `python:3.7`; the containerized page and SDK source say `python:3.11`. Trust the source (`python:3.11`, moving to 3.12 on 2027-10-01).
- `env/dev-kind` overlay: folder exists, purpose and command not documented on the install page. The older `env/platform-agnostic` standalone command is not on the current install page. UNVERIFIED for standalone use.
- KFP standalone CPU/RAM needs are not stated (only the KCD table: 970m CPU, 3552Mi, 35GB PVC for Pipelines in the full multi-user bundle).
- Exact `kfp` 2.18.0 PyPI upload date was truncated; the GitHub release and `kfp-kubernetes` PyPI both show 28 Oct 2026.
- `kfp.kubernetes` function names `add_node_selector` and `add_toleration` (and affinity, empty-dir helpers) are not shown in any fetched page. UNVERIFIED.
- `kfp.local.init` has `enable_caching` in source, but the docs say caching has no effect locally. Not reconciled.
- Which Argo version ships in the KFP 2.18.0 manifests is not stated.
- The KFP 3.0 release date is not stated anywhere read.

---

## K4. Kubeflow Trainer (v2)

**Plain explanation.** Trainer runs training jobs on Kubernetes. You create one object, a `TrainJob`. It points to a "runtime", which is a ready-made template set up by the platform team for a framework such as PyTorch. Under the hood Trainer uses JobSet to start the pods. Data scientists usually do not write YAML. They call `TrainerClient().train()` from Python. The same Python code can run on your laptop (as a local process or in Docker) or on a big cluster. There are also built-in recipes for fine-tuning LLMs with TorchTune.

**Documented facts.**
- Description: "a Kubernetes-native distributed AI platform for scalable large language model (LLM) fine-tuning" and training; "Train models with a single Kubernetes CRD (TrainJob) across any supported framework". Reuses JobSet and LeaderWorkerSet. Has a distributed data cache.
- Frameworks listed: PyTorch, JAX, DeepSpeed, MLX, HuggingFace, Megatron(-LM), XGBoost, TorchTune; user guides also exist for MPI, Flux, PyTorch on AMD ROCm, JAX on TPU.
- Scheduler integrations: Kueue, Slurm Bridge, KAI Scheduler, Coscheduling, Volcano, YuniKorn.
- Personas: AI Practitioners (SDK, TrainJob), Platform Administrators (install, runtimes, policies, schedulers).
- Runtimes: `ClusterTrainingRuntime` (cluster-scoped, any namespace can use it) and `TrainingRuntime` (namespace-scoped). A TrainJob picks one via `runtimeRef` (`apiGroup`, `name`, `kind`).
- Built-in ClusterTrainingRuntimes: CustomTrainer `torch-distributed`, `deepspeed-distributed`, `jax-distributed`, `mlx-distributed`, `xgboost-distributed`; TorchTune BuiltinTrainer `torchtune-llama3.2-1b`, `torchtune-llama3.2-3b`, `torchtune-qwen2.5-1.5b`.
- Runtime YAML: `apiVersion: trainer.kubeflow.org/v1alpha1`, `kind: ClusterTrainingRuntime`, label `trainer.kubeflow.org/framework: torch` (required so the SDK can recognize it), `spec.mlPolicy.numNodes`, `spec.mlPolicy.torch.numProcPerNode: auto`, `spec.template.spec.replicatedJobs[]` (e.g. name `node`, pod label `trainer.kubeflow.org/trainjob-ancestor-step: trainer`). Other labels: `trainer.kubeflow.org/webhook-validation: disabled`, `trainer.kubeflow.org/support: "deprecated"`.
- TrainJob YAML (lifecycle page):
  ```yaml
  apiVersion: trainer.kubeflow.org/v1alpha1
  kind: TrainJob
  metadata:
    name: my-trainjob
  spec:
    activeDeadlineSeconds: 3600
    runtimeRef:
      name: torch-distributed
      kind: ClusterTrainingRuntime
      apiGroup: trainer.kubeflow.org
    trainer:
      image: docker.io/my-training-image:latest
      command: [torchrun, train.py]
  ```
  (indentation reconstructed; the page's indentation was flattened). Other spec fields seen: `suspend`, `trainer.numNodes`, `trainer.resourcesPerNode`, `trainer.resourceClaimsPerNode`, `runtimePatches` (replaces legacy `podTemplateOverrides`), initializers (`dataset-initializer`, `model-initializer`).
- SDK (`pip install -U kubeflow`): `from kubeflow.trainer import TrainerClient, CustomTrainer`. `TrainerClient().list_runtimes()`; `TrainerClient().train(trainer=CustomTrainer(func=train_pytorch, num_nodes=4, resources_per_node={"cpu": 3, "memory": "16Gi", "gpu": 1}))` returns a job name; `get_job(name=...).steps`; `get_job_logs(job_id, follow=True)`; `wait_for_job_status(...)` (SDK README). `CustomTrainer` also takes `packages_to_install`. `TrainJobTemplate` wraps a trainer for reuse.
- CPU works: the PyTorch guide's code picks `("cpu", "gloo")` when CUDA is missing, and a CPU example requests `"cpu": 2` per node.
- Local backends: `LocalProcessBackendConfig()` (Python venv, "Single-node only (no distributed training)", needs Python 3.10+); `ContainerBackendConfig(container_runtime="docker" | "podman" | None)` (auto-detect tries Docker then Podman; each node is a container `<job-name>-node-<n>` on network `<job-name>-net`; sets `RANK`, `WORLD_SIZE`; params `pull_policy="IfNotPresent"`, `auto_remove=True`, `container_host`, `runtime_source`); `KubernetesBackendConfig(namespace=...)` for clusters. "Switching backends changes only the configuration."
- TorchTune BuiltinTrainer: `client.train(runtime="torchtune-llama3.2-1b", initializer=Initializer(model=HuggingFaceModelInitializer(storage_uri="hf://meta-llama/Llama-3.2-1B-Instruct", access_token=...)), trainer=BuiltinTrainer(config=TorchTuneConfig(...)))`. `LoraConfig(lora_rank=8, lora_alpha=16, lora_dropout=0.1)`; LoRA since Trainer v2.1.0 / SDK v0.2.0; multi-node fine-tuning not supported; example needs 2 GPUs; output in `/workspace/output` on an auto-created PVC.
- Install (operator guide): prerequisites Kubernetes 1.31+ and kubectl 1.31+; Kind or Minikube for local testing.
  - Helm: `helm install kubeflow-trainer oci://ghcr.io/kubeflow/charts/kubeflow-trainer --namespace kubeflow-system --create-namespace --version ${VERSION#v}`; `--set runtimes.defaultEnabled=true` to install default runtimes.
  - Kustomize: `kubectl apply --server-side -k "https://github.com/kubeflow/trainer.git/manifests/overlays/manager?ref=${VERSION}"`, then runtimes `.../manifests/overlays/runtimes?ref=${VERSION}`.
  - Verify: `kubectl get pods -n kubeflow-system` shows the JobSet controller manager and the Trainer controller manager.
  - The install page still shows `export VERSION=v2.3.0`; the newest release is v2.4.0.
- Releases: v2.4.0 (GitHub 06 Nov; `kubeflow-trainer-api` 2.4.0 on PyPI 2026-11-06), v2.3.0 (2026-08-07), v2.2 (2026/03), v2.1 (2025/11), v2.0 (2025/07). v2.4.0 adds Workload-Aware Scheduling phase 1, DRA, OptimizationJob (alpha gate), JobSet v0.13.0; breaking: ReplicatedJob names limited to 20 characters, Helm uninstall keeps CRDs.
- Trainer is alpha: README warns "APIs may change".
- Legacy Training Operator v1: kinds PyTorchJob, TFJob, PaddleJob, XGBoostJob, JAXJob, MPIJob. Docs carry an "Old Version" label. Install shown for v1.8.1: `kubectl apply --server-side -k "github.com/kubeflow/training-operator.git/manifests/overlays/standalone?ref=v1.8.1"`. README: v1 code maintained on the `release-1.9` branch. A `v1.9.4` tag was released 18 Aug. KCD 26.10.0 removed the legacy Training Operator from the distribution.
- Migration: `kubeflow.org/v1` PyTorchJob becomes `trainer.kubeflow.org/v1alpha1` TrainJob; Master+Worker replicas become `trainer.numNodes`; container image/command become `trainer.image`/`trainer.command`; add `runtimeRef.name: torch-distributed`. MPIJob (`kubeflow.org/v2beta1`): launcher and worker specs move into the runtime; drop `-np` from `mpirun`.

**Official URLs read.**
- https://www.kubeflow.org/docs/components/trainer/
- https://trainer.kubeflow.org/en/latest/
- https://trainer.kubeflow.org/en/latest/overview/index.html
- https://trainer.kubeflow.org/en/latest/getting-started/index.html
- https://trainer.kubeflow.org/en/latest/operator-guides/installation.html
- https://trainer.kubeflow.org/en/latest/operator-guides/runtime.html
- https://trainer.kubeflow.org/en/latest/operator-guides/runtime-patches.html
- https://trainer.kubeflow.org/en/latest/operator-guides/migration.html
- https://trainer.kubeflow.org/en/latest/user-guides/pytorch.html
- https://trainer.kubeflow.org/en/latest/user-guides/trainjob-lifecycle.html
- https://trainer.kubeflow.org/en/latest/user-guides/builtin-trainer/torchtune.html
- https://trainer.kubeflow.org/en/latest/user-guides/local-execution/overview.html
- https://trainer.kubeflow.org/en/latest/user-guides/local-execution/docker.html
- https://trainer.kubeflow.org/en/latest/legacy-v1/index.html
- https://trainer.kubeflow.org/en/latest/legacy-v1/installation.html
- https://raw.githubusercontent.com/kubeflow/trainer/master/README.md
- https://github.com/kubeflow/trainer/releases and /releases/tag/v2.4.0
- https://pypi.org/pypi/kubeflow-trainer-api/json
- https://sdk.kubeflow.org/en/latest/getting-started/local-development.html

**Gaps / UNVERIFIED.**
- No complete, correctly indented TrainJob YAML with `numNodes` and `resourcesPerNode` together was read. The skeleton above is reconstructed.
- Whether the local backends support GPUs or BuiltinTrainer is not stated.
- Docker backend on Windows: only "start Docker Desktop" is mentioned.
- No explicit v1 deprecation or end-of-life wording on the Trainer docs.
- The `kubeflow` SDK 0.5.0 pins `kubeflow-trainer-api>=2.3.0,<2.4`. Whether SDK 0.5.0 fully supports a Trainer 2.4.0 control plane is not stated.
- JobSet minimum version for the standalone install is not stated (bundled JobSet 0.13.0 in v2.4.0).

---

## K5. Katib (deprecated) and its replacement, Trainer OptimizationJob

**Plain explanation.** Hyperparameter tuning means trying many settings, like learning rate, and keeping the best. Katib does this on Kubernetes. An Experiment says what to tune and what score to chase. Katib asks a search algorithm for a Suggestion, runs a Trial for each set of values, reads the score, and repeats. Katib is now deprecated. The new path is the `OptimizationJob` API inside Kubeflow Trainer, which is alpha and only does random search so far. Teach the ideas with Katib or OptimizationJob, but tell learners about the deprecation.

**Documented facts.**
- Deprecation: "The Katib project is deprecated." Migrate to OptimizationJob in Trainer (alpha feature gate). Deprecation date 2026-11-01, archive 2027-11-01 (install page). Remaining features tracked at kubeflow/trainer#3562.
- Katib is "Kubernetes-native project for automated machine learning (AutoML)": hyperparameter tuning, early stopping, neural architecture search; framework-agnostic.
- Concepts (architecture page): Experiment is "a single tuning run, also called an optimization run"; Suggestion is "a set of hyperparameter values that the hyperparameter tuning process has proposed"; Trial is "one iteration of the hyperparameter tuning process"; Worker is "the process that runs to evaluate a Trial".
- Components: `katib-controller` (manages Experiment, Suggestion, Trial CRDs), `katib-ui`, `katib-db-manager` (gRPC DB API), `katib-mysql`.
- Experiment spec (`apiVersion: kubeflow.org/v1beta1`, `kind: Experiment`): `objective` (`type` maximize/minimize, `goal`, `objectiveMetricName`, `additionalMetricNames`, `metricStrategies` min/max/latest), `algorithm.algorithmName`, `parallelTrialCount` (default 3), `maxTrialCount`, `maxFailedTrialCount`, `parameters` (types `int`, `double`, `categorical`; `feasibleSpace`), `trialTemplate` (`primaryContainerName`, `trialParameters`, `trialSpec`), `earlyStopping`, `metricsCollectorSpec`.
- Algorithm names: `grid` (Optuna), `random` (Hyperopt/Goptuna/Optuna), `bayesianoptimization` (scikit-optimize), `hyperband`, `tpe`, `multivariate-tpe` (Optuna), `cmaes` (Goptuna/Optuna), `sobol` (Goptuna), `pbt` (needs RWX PVC). Overview also lists ENAS and DARTS for NAS.
- Early stopping: only `medianstop`; settings `min_trials_required` (default 3), `start_step` (default 4); works only with `StdOut` or `File` collectors; stopped trials get status `EarlyStopped`.
- Metrics collectors: `StdOut` (default), `File` (default path `/var/log/katib/metrics.log`), `TensorFlowEvent` (`/var/log/katib/tfevent/`), `Custom`, `Push` (training code calls `report_metrics()`). Default regex parses `name=value` lines, e.g. `loss=3.0e-02`.
- Install: prerequisites Kubernetes >= 1.27, kubectl >= 1.27, Python >= 3.7; "must have `StorageClass`" for Katib DB.
  `kubectl apply -k "github.com/kubeflow/katib.git/manifests/v1beta1/installs/katib-standalone?ref=v0.19.0"`. Verify with `kubectl get pods -n kubeflow`.
- Python SDK: `pip install -U kubeflow-katib` (0.19.0, PyPI upload 2025-10-30). Example: `katib_client = katib.KatibClient(namespace="kubeflow")`; `katib_client.tune(name=..., objective=objective, parameters={"a": katib.search.int(min=10, max=20), "b": katib.search.double(min=0.1, max=0.2)}, objective_metric_name="result", max_trial_count=12, resources_per_trial={"cpu": "2"})`; the objective prints `result=...`; `wait_for_experiment_condition(name=name)`; `get_optimal_hyperparameters(name)`.
- Katib releases: v0.19.0 (30 Oct 2025), v0.18.0 (31 Mar), v0.17.0 (15 Jul), v0.16.0 (03 Nov).
- OptimizationJob (Trainer user guide): `apiVersion trainer.kubeflow.org/v1alpha1`, `kind: OptimizationJob`, alpha and "not production-ready"; needs Trainer 2.4+; enable with `--feature-gates=OptimizationJob=true,TrainJobStatus=true` or Helm `manager.config.featureGates.OptimizationJob=true` and `...TrainJobStatus=true`. Spec: `objectives` (one entry, `metric`, `direction` Minimize/Maximize), `searchAlgorithm` (only `random`; `grid` fails with `UnsupportedSearchAlgorithm`), `parameters` (1-100; `uniform`, `logUniform`, `categorical`; `type: Float|Int`), `numTrials` (1-100, default 1), `parallelTrials`, `trainJobTemplate`. Values arrive as `KUBEFLOW_TRAINER_OPT_<name>` env vars. Metrics must be reported to `TrainJob.status.trainerStatus.metrics` (stdout is not scraped), e.g. `from kubeflow.trainer import update_trainjob_status; update_trainjob_status(progress_percent=100, metrics={"validation_loss": loss})`, or automatically by `KubeflowTrainerCallback` in HF Transformers 4.57.0+. Best result in `.status.result`. List trials: `kubectl get trainjobs -l trainer.kubeflow.org/optimization-job=<name>`.
- Kubeflow SDK optimizer: `from kubeflow.optimizer import OptimizerClient, Search, TrialConfig`; `OptimizerClient().optimize(trial_template=TrainJobTemplate(trainer=CustomTrainer(func=train)), search_space={... Search.loguniform(...), Search.choice(...)}, trial_config=TrialConfig(num_trials=10, parallel_trials=2), objectives=[Objective(name="accuracy", type="maximize")])`; `get_best_results(job_name)` returns `.hyperparameters` and `.metrics`. The SDK optimize page says "Kubeflow uses Katib under the hood."

**Official URLs read.**
- https://www.kubeflow.org/docs/components/katib/overview/
- https://www.kubeflow.org/docs/components/katib/installation/
- https://www.kubeflow.org/docs/components/katib/getting-started/
- https://www.kubeflow.org/docs/components/katib/reference/architecture/
- https://www.kubeflow.org/docs/components/katib/user-guides/hp-tuning/configure-experiment/
- https://www.kubeflow.org/docs/components/katib/user-guides/hp-tuning/configure-algorithm/
- https://www.kubeflow.org/docs/components/katib/user-guides/early-stopping/
- https://www.kubeflow.org/docs/components/katib/user-guides/metrics-collector/
- https://github.com/kubeflow/katib/releases
- https://pypi.org/pypi/kubeflow-katib/json
- https://trainer.kubeflow.org/en/latest/user-guides/optimizationjob.html
- https://sdk.kubeflow.org/en/latest/optimize/index.html
- https://raw.githubusercontent.com/kubeflow/sdk/main/README.md

**Gaps / UNVERIFIED.**
- Conflict: Kubeflow SDK docs say the OptimizerClient uses Katib "under the hood", while Katib is deprecated and Trainer has its own OptimizationJob. Which backend SDK 0.5.0 targets by default is not stated. UNVERIFIED.
- Katib UI port-forward command not found on the pages read.
- Katib resource needs standalone: not stated (KCD table: 13m CPU, 476Mi, 10GB PVC).
- ENAS/DARTS algorithm names and settings were not read.

---

## K6. KServe

**Plain explanation.** KServe turns a trained model into a web service on Kubernetes. You write one `InferenceService` object that says the model format (like sklearn or mlflow) and where the files are (a `storageUri`). KServe picks a matching "serving runtime", which is a server image that knows that format, and starts it. It can run in two modes. Standard mode uses plain Kubernetes Deployments and is lighter. Knative mode adds scale-to-zero and canary traffic splits but needs Knative and Istio. For LLMs there is a Hugging Face runtime that uses vLLM and speaks the OpenAI API. Requests to classic models use either the old v1 format (`instances`) or the Open Inference Protocol, also called v2 (`inputs` with name, shape, datatype, data).

**Documented facts.**
- Current version 0.21 (docs selector); GitHub `v0.21.0` marked Latest, 25 Sep; PyPI `kserve` 0.21.0 uploaded 2026-09-25, Python `<3.14,>=3.10`, extras `storage`, `logging`, `ray`, `llm`. Earlier: v0.20.0 (06 Aug).
- Resources (concepts page): InferenceService, InferenceGraph, ServingRuntime (namespace), ClusterServingRuntime (cluster), ClusterStorageContainer, StorageContainer, LocalModelCache, LocalModelNamespaceCache, LocalModelNode, LocalModelNodeGroup. Controllers include KServe Controller Manager, LocalModel controllers, InferenceGraph controller, TrainedModel controller, admission webhooks.
- Deployment modes:
  - Control-plane page: "Standard Deployment Mode" "uses standard Kubernetes resources", "Recommended for LLMs", networking via Gateway API (recommended) or Ingress, autoscaling via HPA or optional KEDA, no scale-to-zero. "Knative Mode" "leverages Knative Serving for event-driven, scale-to-zero capabilities", Istio or Kourier gateway, KPA autoscaler.
  - Admin guide: InferenceService (Standard) for "Full resource control, GPU workloads, production"; InferenceService (Knative/Serverless) for "Scale-to-zero, burst/unpredictable traffic", predictive only; LLMInferenceService for prefix-aware routing and disaggregated serving.
  - KServe README still names "Standard Kubernetes (raw deployment)", "Knative (serverless)" as "the default for InferenceService", and "ModelMesh".
  - Helm value: `--set kserve.controller.deploymentMode=Standard` or `=Knative`; Kustomize standard mode edits the `inferenceservice` ConfigMap to `"defaultDeploymentMode": "Standard"`.
- Install (v0.21): Kubernetes "1.32 or higher" (quickstart). Tools: kubectl, helm, git. kind or minikube recommended locally.
  - Dependencies: Knative mode = cert-manager v1.17.0, Istio 1.27.1, Knative Operator/Serving 1.21.1; Standard mode = cert-manager v1.17.0+ only; LLMIsvc = cert-manager, Gateway API + extension CRDs, Envoy Gateway, Envoy AI Gateway, LWS operator, and an external LB (needed locally on Kind/Minikube). Optional KEDA.
  - Dependency scripts: `curl -fsSL https://github.com/kserve/kserve/releases/download/v0.21.0/kserve-standard-mode-dependency-install.sh | bash` (and `kserve-knative-mode-...`, `llmisvc-...`, `keda-...`).
  - Quick-install scripts named `kserve-standard-mode-full-install-with-manifests.sh`, `kserve-knative-mode-full-install-with-manifests.sh`, `llmisvc-full-install-with-manifests.sh`; repo script `./hack/kserve-install.sh --kserve-version v0.21.0 --type kserve --standard` (or `--knative`, `--kustomize`).
  - Helm: `helm install kserve-crd oci://ghcr.io/kserve/charts/kserve-crd --version v0.21.0 --namespace kserve --create-namespace`, then `helm install kserve-resources oci://ghcr.io/kserve/charts/kserve-resources ... --set kserve.controller.deploymentMode=Standard`. Runtimes: `kubectl apply -k config/runtimes`. Other charts: `kserve-crd-minimal`, `kserve-llmisvc-crd`, `kserve-llmisvc-resources`, `kserve-localmodel-*`, `kserve-runtime-configs`.
- First predictive InferenceService (verbatim):
  ```yaml
  apiVersion: "serving.kserve.io/v1beta1"
  kind: "InferenceService"
  metadata:
    name: "sklearn-iris"
    namespace: kserve-test
  spec:
    predictor:
      model:
        modelFormat:
          name: sklearn
        storageUri: "gs://kfserving-examples/models/sklearn/1.0/model"
        resources:
          requests: {cpu: "100m", memory: "512Mi"}
          limits: {cpu: "1", memory: "1Gi"}
  ```
  (resources condensed). "Do not deploy `InferenceServices` in control plane namespaces". Check: `kubectl get inferenceservices sklearn-iris -n kserve-test`. Port-forward the Istio ingress gateway `8080:80`, then `curl -v -H "Host: ${SERVICE_HOSTNAME}" -H "Content-Type: application/json" "http://${INGRESS_HOST}:${INGRESS_PORT}/v1/models/sklearn-iris:predict" -d @./iris-input.json` with `{"instances": [[6.8, 2.8, 4.8, 1.4], [6.0, 3.4, 4.5, 1.6]]}`; expected `{"predictions": [1, 1]}`.
- Predictive frameworks table: SKLearn, XGBoost, LightGBM, PMML, Paddle, HuggingFace (KServe servers, HTTP v1+v2, gRPC v2); MLFlow (MLServer v1.5.0, HTTP v2 and gRPC v2 only); TensorFlow Serving 2.6.2 (v1); Triton 23.05-py3 (v2); AutoGluon; Custom.
- Built-in runtime files in `config/runtimes`: `kserve-autogluonserver`, `kserve-huggingfaceserver`, `kserve-huggingfaceserver-multinode`, `kserve-lgbserver`, `kserve-llm-omni`, `kserve-llm-sglang`, `kserve-mlserver`, `kserve-openvino`, `kserve-paddleserver`, `kserve-pmmlserver`, `kserve-predictiveserver`, `kserve-sklearnserver`, `kserve-tensorflow-serving`, `kserve-torchserve`, `kserve-tritonserver`, `kserve-vllmserver`, `kserve-xgbserver`.
- `kserve-mlserver` (verbatim fields): `apiVersion: serving.kserve.io/v1alpha1`, `kind: ClusterServingRuntime`, `supportedModelFormats` sklearn 0/1, xgboost 1/2, lightgbm 3/4 (`autoSelect: true`, `priority: 2`), mlflow 1/2 (`autoSelect: true`, `priority: 1`), `protocolVersions: [v2]`.
- Runtime selection (older KServe docs via search, not current page): with no explicit runtime, the controller picks a runtime whose `supportedModelFormats` entry has `autoSelect: true`; higher `priority` wins. UNVERIFIED for 0.21.
- Open Inference Protocol (v2): `POST v2/models/<model_name>[/versions/<v>]/infer`, `GET v2/models/<name>` (metadata), `GET v2/models/<name>/ready`, `GET v2/health/ready`, `GET v2/health/live`, `GET v2`. Request: optional `id`, `parameters`, `inputs[]` each with `name`, `shape`, `datatype`, `data` (flat row-major), optional `outputs[]`. Response: `model_name`, `model_version`, `id`, `outputs[]`. Datatypes: BOOL, UINT8-64, INT8-64, FP16, FP32, FP64, BYTES. Example (HF text classification): `{"inputs": [{"name": "input-0", "shape": [2], "datatype": "BYTES", "data": ["Hello, my dog is cute", "I am feeling sad"]}]}` to `/v2/models/distilbert/infer`.
- Autoscaling (KPA page, Knative mode only): `scaleTarget`, `scaleMetric` (default `concurrency`; also `rps`, `cpu`, `memory`), `containerConcurrency` (hard limit), `minReplicas` (default 1; `0` enables scale-to-zero), annotation `autoscaling.knative.dev/target`. Load test with `hey -z 30s -c 5`.
- Canary (canary example page): "Canary rollout strategy is only supported in serverless deployment mode." Add `canaryTrafficPercent: 10` under `predictor` with a new `storageUri`; `kubectl get isvc` shows PREV/LATEST (90/10). Promote: remove the field and re-apply. Roll back: `canaryTrafficPercent: 0`. Tag routing: annotation `serving.kserve.io/enable-tag-routing: "true"`, hosts prefixed `latest-` and `prev-`. (v0.21.0 release notes mention "canary traffic splitting for RawDeployment HTTPRoutes"; not reflected on the canary page.)
- InferenceGraph: `apiVersion: serving.kserve.io/v1alpha1`, `kind: InferenceGraph`, entry node `root`; `routerType` Sequence, Switch (needs `condition`, GJSON), Ensemble, Splitter (`weight`, sum 100); step target is one of `serviceName`, `serviceUrl`, `nodeName`; `data: $response` passes the previous output.
- LLM serving (Hugging Face runtime): uses vLLM; "If a model is not supported by the vLLM engine, KServe automatically falls back to the standard Hugging Face backend". CPU image chosen automatically when no `nvidia.com/gpu` is requested; CPU env vars `VLLM_CPU_KVCACHE_SPACE`, `VLLM_CPU_OMP_THREADS_BIND`, `OMP_NUM_THREADS`. Endpoints `openai/v1/completions`, `openai/v1/chat/completions`, `openai/v1/embeddings`, `openai/v1/rerank` (prefix changeable with `KSERVE_OPENAI_ROUTE_PREFIX`). Args: `--model_id`, `--model_name`, `--model_dir`, `--backend` (auto, huggingface, vllm), `--max_model_len`, `--dtype` (float16 on GPU, float32 on CPU by default; CPU section recommends bfloat16), `--task`.
- First LLM InferenceService: name `qwen-llm`, `modelFormat: huggingface`, `args: [--model_name=qwen]`, `storageUri: "hf://Qwen/Qwen2.5-0.5B-Instruct"`, requests cpu 1 / 4Gi / 1 GPU, limits cpu 2 / 6Gi / 1 GPU. Optional HF token: secret `hf-secret` key `HF_TOKEN` plus a ClusterStorageContainer `hf-hub`. Call `http://qwen-llm.kserve-test/openai/v1/chat/completions`.
- HF text classification example: `huggingface-distilbert`, `storageUri: "hf://distilbert/distilbert-base-uncased-finetuned-sst-2-english"`, 1 CPU / 2Gi; GPU "optional but recommended". v1: `POST /v1/models/distilbert:predict` with `{"instances": ["Hello, my dog is cute", "I am feeling sad"]}` returns `{"predictions":[1,0]}`.
- LLMInferenceService: "Built on the foundation of llm-d"; apiVersion `serving.kserve.io/v1alpha1` on the overview (v0.21.0 notes mention a sample update to `v1alpha2`); fields `spec.model`, `spec.replicas`, `spec.template`, `spec.worker` (LeaderWorkerSet), `spec.prefill`, `spec.parallelism`, `spec.router` (gateway, route, scheduler). InferenceService serves LLMs "only for basic single-node deployments".
- In Kubeflow: KCD installs KServe v0.21.0 and KServe UI v1.1.0 into the `kserve` namespace; the dashboard shows "KServe Endpoints".

**Official URLs read.**
- https://kserve.github.io/website/
- https://kserve.github.io/website/docs/getting-started/quickstart-guide
- https://kserve.github.io/website/docs/install/overview
- https://kserve.github.io/website/docs/install/kserve-install
- https://kserve.github.io/website/docs/install/dependencies
- https://kserve.github.io/website/docs/admin-guide/overview
- https://kserve.github.io/website/docs/concepts/resources
- https://kserve.github.io/website/docs/concepts/architecture/control-plane
- https://kserve.github.io/website/docs/concepts/architecture/data-plane/v2-protocol
- https://kserve.github.io/website/docs/getting-started/predictive-first-isvc
- https://kserve.github.io/website/docs/getting-started/genai-first-isvc
- https://kserve.github.io/website/docs/model-serving/predictive-inference/frameworks/overview
- https://kserve.github.io/website/docs/model-serving/predictive-inference/frameworks/mlflow
- https://kserve.github.io/website/docs/model-serving/predictive-inference/frameworks/huggingface/overview
- https://kserve.github.io/website/docs/model-serving/predictive-inference/frameworks/huggingface/text-classification
- https://kserve.github.io/website/docs/model-serving/generative-inference/overview
- https://kserve.github.io/website/docs/model-serving/generative-inference/llmisvc/llmisvc-overview
- https://kserve.github.io/website/docs/model-serving/predictive-inference/rollout-strategies/canary-example
- https://kserve.github.io/website/docs/model-serving/predictive-inference/autoscaling/kpa-autoscaler
- https://kserve.github.io/website/docs/model-serving/inferencegraph/overview
- https://raw.githubusercontent.com/kserve/kserve/master/README.md
- https://github.com/kserve/kserve/releases
- https://github.com/kserve/kserve/tree/master/config/runtimes
- https://raw.githubusercontent.com/kserve/kserve/master/config/runtimes/kserve-mlserver.yaml
- https://pypi.org/pypi/kserve/json

**Gaps / UNVERIFIED.**
- The default deployment mode in 0.21 is not stated on the install pages. The README says Knative is default; the control-plane page calls Standard "Recommended for LLMs". Treat "default" as UNVERIFIED.
- Whether "RawDeployment" was officially renamed "Standard" (and the annotation `serving.kserve.io/deploymentMode` values) is not stated on any page read. UNVERIFIED.
- KServe CPU/RAM needs for the control plane on kind are not stated (KCD table: 600m CPU, 1200Mi for KServe alone, plus Knative 1450m/1038Mi and Istio 750m/2364Mi in Knative mode).
- The current ServingRuntime docs page was not found (404); spec fields beyond the `kserve-mlserver` file are UNVERIFIED for 0.21.
- The full v2 JSON body for the MLflow wine example (`mlflow-input.json`) was not read.
- Running the Qwen LLM example on CPU only is implied by the CPU image auto-selection but is not shown as a tested example. UNVERIFIED.
- ModelMesh status in 0.21 is not stated.

---

## K7. Kubeflow Hub (formerly Model Registry)

**Plain explanation.** A model registry is a catalog of your models. For each model it keeps versions, and for each version it keeps where the files are and in what format. It does not store the files themselves. Kubeflow's registry is now part of "Kubeflow Hub", which also has a read-only "Model Catalog" for browsing outside models such as Hugging Face ones. You register a model from Python with `register_model`. KServe can then serve a registered version by using a `model-registry://name/version` storage URI.

**Documented facts.**
- Hub is "the central component in Kubeflow for managing the full lifecycle of ML models". The registry is "a passive repository for metadata and is not meant to be a Control Plane". The catalog is a "read-only discovery service" that "does not store model weights or artifacts".
- Backend: metadata in a relational database; schema "inspired by the Google ML-Metadata project"; an OpenAPI/REST server; Python and Go clients. REST path `api/model_registry/v1alpha3/...`.
- Logical model (repo `docs/logical_model.md`): RegisteredModel (`name`, `owner`, `customProperties`) 1-to-many ModelVersion (`name`, `author`, `customProperties`); ModelVersion has Artifacts; ModelArtifact (`modelFormatName`, `modelFormatVersion`, `storageKey`, `storagePath`, `serviceAccountName`, `uri`, `customProperties`); DocArtifact (e.g. README). Implemented as MLMD Contexts and Artifacts.
- Python client: `pip install model-registry==0.3.18` (PyPI latest 0.3.18, 2026-10-22, Python `>=3.10,<4.0`, extras `boto3`, `hf`, `olot`, `s3`, `signing`). Getting-started page still says Python 3.9+.
  ```python
  registry = ModelRegistry(server_address="http://model-registry-service.kubeflow.svc.cluster.local", port=8080, author="your name", is_secure=False)
  rm = registry.register_model("iris", "gs://kfserving-examples/models/sklearn/1.0/model",
        model_format_name="sklearn", model_format_version="1", version="v1",
        description="Iris scikit-learn model", metadata={"accuracy": 3.14, "license": "BSD 3-Clause License"})
  ```
  (argument values from the page; exact positional layout reconstructed). Retrieve: `get_registered_model("iris")`, `get_model_version("iris", "v1")`, `get_model_artifact("iris", "v1")` (gives `uri`, `model_format_name`, `model_format_version`).
- Kubeflow SDK alternative: `from kubeflow.hub import ModelRegistryClient`; `ModelRegistryClient("https://model-registry.kubeflow.svc.cluster.local", author="Your Name")` with `register_model`, `get_model`, `list_models`, `list_model_versions`; default ports 443 (https) / 8080 (http). Install `pip install 'kubeflow[hub]'`.
- KServe integration (getting-started page): either copy `art.uri` into the InferenceService `storageUri` and add labels `modelregistry/registered-model-id` and `modelregistry/model-version-id`, or use the Custom Storage Initializer with `storageUri: "model-registry://iris/v1"` (format `model-registry://{modelName}/{modelVersion}`), which needs the `options/csi` manifests.
- Install standalone (installation page):
  ```bash
  MODEL_REGISTRY_VERSION=0.3.18
  kubectl apply -n kubeflow -k "https://github.com/kubeflow/hub/manifests/kustomize/overlays/db?ref=v${MODEL_REGISTRY_VERSION}"
  ```
  plus `options/istio` (Istio clusters only) and `options/csi` (for `model-registry://`). Prerequisites: Kubernetes >= 1.27, Kustomize >= 5.0.3. Verify: `kubectl wait --for=condition=available -n kubeflow deployment/model-registry-deployment --timeout=1m`. Port-forward: `kubectl port-forward svc/model-registry-service -n kubeflow 8081:8080`. On KCD, install into your profile namespace with `overlays/db`, `options/istio`, `options/ui/overlays/istio`.
- Releases: v0.3.18 (22 Oct 2026) "Replaced MinIO with SeaweedFS", added an evaluation-metrics artifact type, deprecation headers on alpha catalog APIs. v0.3.9 notes: "Kubeflow Model Registry is now Kubeflow Hub"; images under `ghcr.io/kubeflow/hub/...`.
- UI: reachable from the Central Dashboard; register, view, update, delete models.

**Official URLs read.**
- https://www.kubeflow.org/docs/components/hub/
- https://www.kubeflow.org/docs/components/hub/overview/
- https://www.kubeflow.org/docs/components/hub/getting-started/
- https://www.kubeflow.org/docs/components/hub/installation/
- https://www.kubeflow.org/docs/components/hub/reference/architecture/
- https://raw.githubusercontent.com/kubeflow/hub/main/docs/logical_model.md
- https://github.com/kubeflow/hub/releases
- https://pypi.org/pypi/model-registry/json

**Gaps / UNVERIFIED.**
- Hub maturity: the install page lists Hub as "Graduated", while the Hub installation page calls Model Registry "an opt-in alpha component in KCD 1.9+". Conflicting.
- Getting-started pins `kserve=="0.13"`, far behind KServe 0.21. The KServe Python SDK calls shown may be outdated.
- The DB used by `overlays/db` (MySQL vs PostgreSQL) is not stated on the page.
- Whether `options/csi` works with KServe Standard mode outside KCD is not stated.
- The ServingEnvironment / InferenceService / ServeModel entities in the registry API were not found in the logical model doc. UNVERIFIED.

---

## K8. Notebooks and Workspaces, Central Dashboard, Spark Operator, Feast, the `kubeflow` SDK, Kale, MCP Server

**Plain explanation.** Notebooks give each user a JupyterLab, VS Code or RStudio running inside the cluster. The new version is called Workspaces. The Central Dashboard is the web page that links all the UIs and lets you switch between your namespaces. The Spark Operator runs Apache Spark jobs from a YAML file. Feast is a feature store that lives in the Kubeflow ecosystem. The `kubeflow` Python package is one SDK with clients for Trainer, the optimizer, Spark, the Hub and Pipelines.

**Documented facts.**
- Notebooks (v1): "runs interactive development environments for AI, ML, and Data workloads on Kubernetes"; JupyterLab, RStudio, VS Code (code-server). v1.11.1 in KCD 26.10.0; disabled by default; "scheduled for removal in Kubeflow 27.03". Cleanup removes Notebook, Tensorboard and PVCViewer CRDs.
- Workspaces (Notebooks v2): "the next generation of Kubeflow Notebooks"; CRDs `WorkspaceKind` (admin-curated images, resources, pod config) and `Workspace` (user instance via a wizard). Status Beta, "not yet intended for production use". Components (backend, controller, frontend) install into namespace `kubeflow-workspaces`. StorageClass must be labeled `workspaces.kubeflow.org/can-use=true`. Sample WorkspaceKinds: `kubectl apply --kustomize "github.com/kubeflow/notebooks/workspaces/controller/manifests/kustomize/samples?ref=${KUBEFLOW_WORKSPACE_TAG:-v2.0.0-rc.1}"`. KCD 26.10.0 ships Workspaces 2.0.0 enabled by default.
- Central Dashboard: "an authenticated web interface for Kubeflow and ecosystem components". Menu items when installed: Home, Manage Contributors, Notebooks/TensorBoards/Volumes, Katib Experiments, KServe Endpoints, Pipelines/Experiments/Runs/Recurring Runs/Artifacts/Executions. v2.0.1 in KCD 26.10.0. Also installs the PodDefaults admission webhook.
- Spark Operator: runs Spark apps on Kubernetes; CRDs in group `sparkoperator.k8s.io`: `SparkApplication` (example `v1beta2`), `ScheduledSparkApplication` (cron), `SparkConnect`. Install: `helm repo add spark-operator https://kubeflow.github.io/spark-operator`, `helm repo update`, `helm install spark-operator spark-operator/spark-operator --namespace spark-operator --create-namespace` (options `--set webhook.enable=true`, `--set "spark.jobNamespaces={test-ns}"`). Example: `kubectl apply -f examples/spark-pi.yaml`, `kubectl get sparkapplication spark-pi -o=yaml`. Version 2.5.2 in KCD 26.10.0. Docs site example uses Spark 4.2.1.
- Feast (ecosystem): "open-source feature store"; can run on the same cluster; serves features to models trained in KFP and deployed with KServe; offline store (BigQuery, Snowflake, Redshift), online store (Redis, Datastore, DynamoDB), registry (S3, GCS, SeaweedFS or SQL). The Kubeflow GenAI use-cases page lists Feast (with Milvus) as a vector store for RAG.
- Kubeflow SDK (`pip install -U kubeflow`): latest 0.5.0 (2026-08-10), Python >=3.10, status Incubating. Extras `docker`, `podman`, `hub`, `pipelines`, `spark`. Clients:
  - `from kubeflow.trainer import TrainerClient, CustomTrainer, TrainJobTemplate, ContainerBackendConfig`
  - `from kubeflow.optimizer import OptimizerClient, Search, TrialConfig`
  - `from kubeflow.spark import SparkClient, KubernetesBackendConfig` (`SparkClient(KubernetesBackendConfig(namespace="spark-test")).connect()` returns a Spark session)
  - `from kubeflow.hub import ModelRegistryClient`
  - `from kubeflow.pipelines import PipelinesClient, dsl` ("implemented in the KFP repository and re-exported by the Kubeflow SDK"; `upload_pipeline(hello_pipeline, name="hello-pipeline")`, `run("hello-pipeline", params={...})`, `wait_for_run_status`, `create_experiment`, `get_run`; `client.kfp_client` is the underlying `kfp.Client`).
  - Version support table: Trainer v2.0.0+, Katib v0.19.0+, Model Registry v0.3.0+, Spark Operator v2.5.0+, Pipelines v2.17.0+, Feast planned.
  - Pins in 0.5.0: `kubeflow-trainer-api>=2.3.0,<2.4`, `kubeflow-katib-api>=0.19.0,<0.20`, `model-registry>=0.3.14,<0.4` (hub), `kfp[kubernetes]>=2.17.0,<2.18` (pipelines), `kubeflow-spark-api>=2.4.0,<2.5` and `pyspark-connect==4.2.0` (spark).
  - Docs: https://sdk.kubeflow.org/en/latest/ . Also exposes an MCP server for agents.
- Kale: incubating subproject; docs at https://kale.kubeflow.org/ (page is a stub; purpose not stated on it).
- MCP Server: experimental subproject; docs at https://sdk.kubeflow.org/en/latest/mcp-server/index.html (stub page).

**Official URLs read.**
- https://www.kubeflow.org/docs/components/notebooks/overview/
- https://www.kubeflow.org/docs/components/workspaces/
- https://www.kubeflow.org/docs/components/workspaces/overview/
- https://www.kubeflow.org/docs/components/workspaces/operator-guides/deployment-guide/
- https://www.kubeflow.org/docs/components/central-dash/overview/
- https://www.kubeflow.org/docs/components/spark-operator/
- https://spark.kubeflow.org/
- https://spark.kubeflow.org/en/latest/getting-started/index.html
- https://www.kubeflow.org/docs/ecosystem/feast/introduction/
- https://www.kubeflow.org/docs/genai/ and https://www.kubeflow.org/docs/genai/use-cases/
- https://raw.githubusercontent.com/kubeflow/sdk/main/README.md
- https://sdk.kubeflow.org/en/latest/
- https://sdk.kubeflow.org/en/latest/pipelines/index.html
- https://pypi.org/pypi/kubeflow/json
- https://www.kubeflow.org/docs/components/kale/
- https://www.kubeflow.org/docs/components/mcp-server/

**Gaps / UNVERIFIED.**
- Workspace / WorkspaceKind apiVersion: sample filenames suggest `v1beta1`. UNVERIFIED.
- The Workspaces deployment guide still uses `v2.0.0-rc.1` and KCD 26.03.1; KCD 26.10.0 ships 2.0.0.
- Spark Operator install page states "Kubernetes (v1.16 or later)", which looks stale; operator version and Spark compatibility not stated. Spark Operator 2.5.2 release date not checked.
- Kale's purpose (notebook-to-pipeline) is not confirmed on any page read. UNVERIFIED.
- `kubeflow[pipelines]` 0.5.0 pins `kfp<2.18`, one minor behind the KFP 2.18.0 backend.

---

## K9. MLflow and Kubeflow (only what official docs say)

**Plain explanation.** Kubeflow does not ship MLflow. Two official bridges exist. First, KFP has an MLflow plugin. An admin turns it on, and then every pipeline run shows up as an MLflow run, with each task as a nested run. Components can also log to MLflow directly because KFP can inject the MLflow address as environment variables. Second, KServe can serve a saved MLflow model with `modelFormat: mlflow`, using the MLServer runtime and the v2 protocol. A "Kubeflow MLflow Integration" project is listed as experimental.

**Documented facts.**
- KFP MLflow plugin (operator guide): "enables automatic experiment tracking"; "registers each KFP run with MLflow". Configure `plugins.mlflow` in the API server `config.json`: `endpoint` (e.g. `https://mlflow-service.mlflow.svc.cluster.local:8443`), `timeout` (default "30s"), `tls.insecureSkipVerify` (default false), `tls.caBundlePath`, and `settings`: `authType` (`kubernetes` default, `bearer`, `basic-auth`, `none`), `credentialSecretRef` (secret name fixed: `kfp-mlflow-credentials`), `workspacesEnabled`, `defaultExperimentName` (default `"KFP-Default"`), `experimentDescription`, `kfpBaseURL`, `kfpRunURLPathTemplate`, `mlflowBaseURL`, `mlflowUIPathPrefix`, `injectUserEnvVars`. Then `kubectl rollout restart deployment/ml-pipeline -n kubeflow`. Namespace override via `plugins.mlflow` in the namespace's `kfp-launcher` ConfigMap.
- User side (integration overview): logs scalar metric artifacts and KFP run parameters; `mlflow.autolog()` in components works if env var injection is on. Injected env vars: `MLFLOW_RUN_ID` (nested run for the current task), `MLFLOW_TRACKING_URI`, `MLFLOW_EXPERIMENT_ID`, `MLFLOW_WORKSPACE`, `MLFLOW_TRACKING_AUTH` (`kubernetes` or `kubernetes-namespaced`), `MLFLOW_TRACKING_TOKEN`, `MLFLOW_TRACKING_USERNAME`/`PASSWORD`. Cached tasks still get a new MLflow run. Per-run override: `plugins_input.mlflow` with `experiment_name`, `experiment_id`, `disabled`, only via the REST API (`POST .../apis/v2beta1/runs`), "not supported in the KFP UI" or Python SDK.
- KServe MLflow serving: `modelFormat: name: mlflow`, `protocolVersion: v2`, MLServer runtime (`mlserver_mlflow.MLflowRuntime` locally), example `storageUri: "gs://kfserving-examples/models/mlflow/wine"`, name `mlflow-v2-wine-classifier`, 100m/512Mi requests. Model directory holds `MLmodel`, `model.pkl`, `conda.yaml`, `requirements.txt`. Endpoint `/v2/models/mlflow-v2-wine-classifier/infer`; response output `predict`, shape [1], `FP64`. Training example uses `mlflow.sklearn.log_model(lr, "model", ...)`.
- `kserve-mlserver` ClusterServingRuntime supports `mlflow` versions "1" and "2" (priority 1) on protocol v2 only.
- Kubeflow ecosystem page and KServe-in-Kubeflow page do not mention MLflow.

**Official URLs read.**
- https://www.kubeflow.org/docs/components/pipelines/operator-guides/mlflow-plugin/
- https://www.kubeflow.org/docs/components/pipelines/user-guides/integrations/mlflow/overview/
- https://www.kubeflow.org/docs/components/pipelines/user-guides/integrations/mlflow/run-a-pipeline/
- https://kserve.github.io/website/docs/model-serving/predictive-inference/frameworks/mlflow
- https://raw.githubusercontent.com/kserve/kserve/master/config/runtimes/kserve-mlserver.yaml
- https://www.kubeflow.org/docs/started/installing-kubeflow/ (Experimental "Kubeflow MLflow Integration")

**Gaps / UNVERIFIED.**
- Supported MLflow versions and the plugin's maturity label are not stated.
- Which KFP version first shipped the MLflow plugin is not stated.
- The "Kubeflow MLflow Integration" project has no docs or repo link on the install page; `github.com/kubeflow/mlflow` returned 404. UNVERIFIED what it is.
- The "Pipeline Structure in MLflow" page was not read.
- A KServe `storageUri` pointing at an MLflow registry (`models:/...`) is not documented on any page read. UNVERIFIED; do not teach it.

---

## K10. What fits on a 16 GB / 8-core Windows laptop (Docker + kind)

This section combines documented numbers. The conclusions are my inference, marked as such.

- Documented: full KCD needs "16+ GB of RAM recommended" and "8 CPU cores"; its components total about 12.3 GiB memory and 4.4 cores, plus 65 GB of PVCs. Inference: on a 16 GB Windows laptop, Docker Desktop's VM gets only part of the RAM, so the full bundle is not a good first lab. Treat it as a stretch lab, or trim `example/kustomization.yaml` (the README says 4-8 GB is possible but does not list what to drop).
- Documented: KFP local execution needs no cluster (`kfp.local` with `DockerRunner` or `SubprocessRunner`). Inference: this is the best first lab.
- Documented: Trainer local backends need no cluster (`LocalProcessBackendConfig`, `ContainerBackendConfig` with Docker). CPU-only PyTorch with gloo is shown. TorchTune runtimes need GPUs (example needs 2).
- Documented: standalone KFP (`env/dev`) takes "about 3 minutes" to deploy; KCD shows Pipelines at 970m CPU / 3.5 GiB / 35 GB PVC in the full bundle. Standalone needs are not stated.
- Documented: KServe Standard mode needs only cert-manager; the sklearn-iris example asks for 100m CPU / 512Mi; distilbert asks for 1 CPU / 2Gi with GPU optional. Knative mode adds Istio and Knative (2.2 cores, 3.4 GiB in the KCD table). Inference: use Standard mode on kind for the serving lab; show canary and scale-to-zero only as a Knative stretch lab.
- Documented: Trainer control plane is small (8m CPU, 143Mi). Katib 476Mi + 10 GB PVC. Hub 2.1 GiB + 20 GB PVC.
- Not documented: anything Windows-specific. The KCD scripts are bash and the inotify fix is Linux. UNVERIFIED on Windows; plan to run commands from WSL2 and test before publishing.

---

## Proposed lesson order (12 lessons)

1. **What Kubeflow is in 2026.** Subprojects vs ecosystem vs distributions; lifecycle map; CNCF graduation; Katib deprecation; Hub rename. Backed by K1, K2 (versions), Version notes.
2. **Your first pipeline, no cluster.** `@dsl.component`, `@dsl.pipeline`, parameters, `kfp.local` with `SubprocessRunner` then `DockerRunner`. Backed by K3.1, K3.2, K3.3, K3.6.
3. **Artifacts, metrics and types.** `Input[Dataset]`, `Output[Model]`, `Output[Metrics]`, `ClassificationMetrics`, `dsl.OutputPath`; why the Pythonic artifact style does not work on open-source KFP. Backed by K3.3, K3.2.
4. **A small cluster and standalone KFP.** kind, `kubectl apply -k` with `PIPELINE_VERSION=2.18.0`, `env/dev`, port-forward, `kfp.Client`, compile to IR YAML, upload, run, experiments, recurring runs, CLI. Backed by K3.5, K3.8, K10.
5. **Real pipeline features.** Task resources, retries, env vars, caching on and off, `dsl.If/Elif/Else`, `ParallelFor` + `Collected`, `ExitHandler`, nested pipelines, `kfp-kubernetes` secrets and PVCs, containerized components with `kfp component build`. Backed by K3.4, K3.7, K3.2.
6. **How KFP runs underneath.** API server, Argo Workflows, persistence agent, MLMD, MySQL, SeaweedFS, pipeline root; Kubernetes-native API mode; Argo 3.x to 4.x warning. Backed by K3.8.
7. **Distributed training with Trainer.** TrainJob, ClusterTrainingRuntime, JobSet; `TrainerClient` on local process, then Docker multi-node, then kind with `torch-distributed` on CPU. Backed by K4, K8 (SDK).
8. **Hyperparameter tuning.** Experiment/Trial/Suggestion ideas, algorithms, early stopping (Katib, deprecated); the new `OptimizationJob` and `OptimizerClient`; clear deprecation note. Backed by K5.
9. **Serving with KServe (Standard mode on kind).** InferenceService, modelFormat, storageUri, ServingRuntimes, v1 vs Open Inference Protocol v2 requests, sklearn and distilbert examples. Backed by K6.
10. **Serving LLMs and rollouts.** Hugging Face runtime with vLLM, OpenAI-compatible endpoints, CPU vs GPU, LLMInferenceService overview; Knative stretch: autoscaling, scale-to-zero, `canaryTrafficPercent`, InferenceGraph. Backed by K6.
11. **Model registry and MLflow bridges.** Hub data model, `register_model`, `model-registry://` URI into KServe; KFP MLflow plugin and env vars; serving an MLflow model with `modelFormat: mlflow`. Backed by K7, K9.
12. **The full platform (stretch).** Community Distribution on kind, Dex login, Profiles and namespaces, Istio, oauth2-proxy, Central Dashboard, Workspaces, Spark Operator and Feast at a glance, the unified `kubeflow` SDK, multi-user KFP auth. Backed by K2, K8, K3.8 (multi-user), K10.

---

## Version and deprecation notes

Versions (as of 2026-11-11):

| Item | Version | Date | Source |
|---|---|---|---|
| Kubeflow Community Distribution | 26.10.0 | 06 Nov 2026 (year inferred) | GitHub release |
| Previous KCD | 26.03.1 | 15 Jun 2026 (inferred) | GitHub release |
| KFP backend | 2.18.0 | 28 Oct 2026 | GitHub release; kfp-kubernetes PyPI date |
| `kfp` SDK | 2.18.0 | 28 Oct 2026 (sdk-2.18.0 tag) | PyPI / GitHub |
| `kfp-kubernetes` | 2.18.0 | 2026-10-28 | PyPI |
| Kubeflow Trainer | v2.4.0 | 2026-11-06 | GitHub; `kubeflow-trainer-api` PyPI |
| JobSet (bundled) | 0.13.0 | n/a | Trainer v2.4.0 notes |
| Katib | v0.19.0 | 2025-10-30 | PyPI `kubeflow-katib` |
| Kubeflow Hub / `model-registry` | 0.3.18 | 2026-10-22 | GitHub / PyPI |
| KServe / `kserve` SDK | 0.21.0 | 2026-09-25 | GitHub / PyPI |
| `kubeflow` SDK | 0.5.0 | 2026-08-10 | PyPI |
| Spark Operator | 2.5.2 | not checked | KCD README |
| Workspaces | 2.0.0 | not checked | KCD 26.10.0 notes |
| Notebooks v1 | 1.11.1 | not checked | KCD 26.10.0 notes |
| Dashboard | 2.0.1 | not checked | KCD 26.10.0 notes |
| Istio / Knative / cert-manager / Dex / OAuth2-Proxy (KCD) | 1.31.3 / 1.24.0 / 1.21.2 / 2.46.1 / 7.15.5 | n/a | KCD notes |
| Legacy Training Operator | v1.9.4 tag (18 Aug); docs install v1.8.1 | n/a | GitHub / docs |

Deprecations and moving parts:
- Katib: deprecated 2026-11-01, to be archived 2027-11-01. Replacement: Trainer `OptimizationJob` (alpha, Trainer 2.4+, random search only).
- Training Operator v1 (PyTorchJob, TFJob, MPIJob, ...): legacy; code kept on `release-1.9`; removed from KCD 26.10.0. Migrate to TrainJob.
- Notebooks v1: disabled by default in KCD 26.10.0; "scheduled for removal in Kubeflow 27.03". Workspaces (v2) is Beta but on by default.
- KFP v1 SDK support: "scheduled for removal in 27.03" (KCD notes).
- `dsl.Condition`: deprecated for `dsl.If`. `add_node_selector_constraint`: deprecated for `set_accelerator_type`.
- KFP default base image moves from `python:3.11` to `python:3.12` on 2027-10-01.
- Argo Workflows 3.x: deprecated for KFP 2.x, unsupported in KFP 3.0; upgrade the Argo controller to 4.x first.
- MinIO: replaced by SeaweedFS as KFP's default object store from KFP 2.15 (MinIO still supported; legacy manifests may be removed). Hub v0.3.18 also replaced MinIO with SeaweedFS. KCD 1.10.2 to 1.11.0 upgrade removed MinIO.
- Model Registry renamed Kubeflow Hub (repo `kubeflow/hub`; Python package still `model-registry`).
- `kubeflow/manifests` renamed `kubeflow/community-distribution`; version scheme changed from 1.x to Year.Month (26.03, 26.10; 27.03 planned).
- PostgreSQL for KFP: dev/eval only in 2.18.
- Trainer v2.4.0 breaking: ReplicatedJob names max 20 characters; Helm uninstall keeps CRDs.
- KServe: InferenceService modes now named "Standard" and "Knative" in docs; LLMInferenceService samples moving from `v1alpha1` to `v1alpha2` (v0.21.0 notes).
- SDK version skew: `kubeflow` 0.5.0 pins `kfp<2.18` and `kubeflow-trainer-api<2.4`, one minor behind the newest backends.

---

## Consolidated gaps (UNVERIFIED)

1. KFP v2 backend internals (scheduled workflow controller, driver, launcher, cache) are not described in text on any current official page read.
2. No Windows-specific guidance exists for the KCD KinD script, kfp.local DockerRunner, or Trainer container backend.
3. The KFP `env/dev-kind` overlay's purpose and command are not documented; standalone KFP resource needs are not stated.
4. KServe 0.21 default deployment mode and the official RawDeployment-to-Standard rename are not stated on the install pages.
5. KServe CPU-only run of the Qwen LLM example is not shown as tested.
6. Current KServe ServingRuntime docs page not found; selection rules come from older versions via search.
7. Which backend `OptimizerClient` uses in SDK 0.5.0 (Katib vs Trainer OptimizationJob) is unclear.
8. Hub maturity conflict (Graduated vs "opt-in alpha"); Hub DB type in `overlays/db`.
9. `kfp.kubernetes` node selector and toleration function names not shown.
10. Kale's purpose and the "Kubeflow MLflow Integration" project's repo and scope.
11. KServe's CNCF incubating acceptance date (2025-09-29 vs 2025-11-11).
12. Workspace/WorkspaceKind apiVersion.
13. Release years on GitHub pages are inferred where PyPI did not confirm them (KCD 26.10.0, 26.03.1).
