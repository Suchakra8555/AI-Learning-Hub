---
title: A shared server and how to lock it
summary: Backend store versus artifact store, the mlflow server flags and their defaults, upgrading the database, and the security settings added in 3.5 to 3.17. Read from the docs, not run.
time: 20 min
---

:::warn Not run
We ran MLflow only against local SQLite. Everything on this page about PostgreSQL, S3, authentication and Helm comes from MLflow's docs and the 3.18 CLI help. Test it before you rely on it.
:::

A laptop file does not work for a team. A **tracking server** is one process everyone logs to ([docs](https://mlflow.org/docs/latest/self-hosting/)).

## Two stores

| Store | Holds | Typical choice |
| --- | --- | --- |
| **Backend store** | Experiments, runs, params, metrics, registry entries | PostgreSQL or MySQL (SQLite for one user) |
| **Artifact store** | Model files, plots, datasets | S3, or an S3-compatible store such as MinIO or RustFS; or a folder |

Keep them apart. The database stays small and fast. The artifacts can be gigabytes.

## The command

```bash
mlflow server \
  --backend-store-uri postgresql://user:pass@db:5432/mlflow \
  --artifacts-destination s3://my-bucket/mlflow \
  --host 0.0.0.0 --port 5000
```

Defaults from the docs: 4 workers, `--artifacts-destination ./mlartifacts`. By default the server **proxies** artifact transfers, so clients need no S3 keys. `--no-serve-artifacts` makes clients talk to the store directly. `--artifacts-only` runs a server that handles files and nothing else.

For an S3-compatible store that is not AWS, set `MLFLOW_S3_ENDPOINT_URL`. The official Docker Compose setup uses RustFS; one docs page still says MinIO.

## Upgrades and cleanup

- `mlflow db upgrade <uri>` migrates the database after you upgrade MLflow. Back it up first. From 3.17 the docs say to stop writers during the upgrade.
- Deleting a run only marks it deleted. `mlflow gc` removes deleted runs for good.
- `mlflow migrate-filestore` moves an old `mlruns` folder into SQLite.
- 3.13 added an official Helm chart for Kubernetes.

## Locking it down

A server open on a network with no login lets anyone read your runs and, with artifact serving, write files. Since 3.5.0 the server has security middleware:

- `--allowed-hosts` lists the `Host` headers it accepts.
- `--cors-allowed-origins` lists browsers allowed to call it.
- `--x-frame-options` controls embedding.

Authentication is separate. Start with `--app-name basic-auth`. Points from the docs:

- There is no default admin password. Passwords need at least 12 characters. The docs' own examples use shorter ones, so do not copy them.
- Since 3.13, access is given through **roles**, not per-resource permissions, and the old permission APIs are gone. 3.17 adds explicit DENY.
- Single sign-on needs a community plugin or a reverse proxy in front.
- Use TLS through a reverse proxy.

Workspaces (3.10) split one server into separate areas for different teams.

## AI Gateway keys

If you use the built-in AI Gateway, provider keys are stored encrypted with `MLFLOW_CRYPTO_KEK_PASSPHRASE`. If you do not set it, a built-in default passphrase is used, so set your own.

:::check A teammate runs `mlflow server --host 0.0.0.0` on a shared VM with no other flags. What is wrong?
It listens on the network with no authentication, no TLS, and default host and CORS rules. Anyone who can reach the port can read and change runs.
:::
