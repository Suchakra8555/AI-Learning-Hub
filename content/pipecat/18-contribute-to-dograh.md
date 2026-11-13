---
title: Contribute to Dograh: setup, rules and where to start
summary: The real contribution rules, the local setup step by step, what CI checks, and ten places a first pull request could go (each marked as our inference).
time: 30 min
---

You asked how to contribute. This lesson is the practical answer, taken from Dograh's own files. The earlier lessons are the preparation. [Lesson 19](lesson:pipecat/your-path-to-contributor) is a study plan.

:::warn Read the current files first
Everything here is from Dograh commit `5dfa84c` (12 November 2026). The project releases every one to three weeks. Before you start, reread `CONTRIBUTING.md`, `docs/contribution/setup.mdx` and the latest `AGENTS.md` files. If they differ from this lesson, trust them.
:::

## The ground rules

From `CONTRIBUTING.md`, the parts that decide whether a pull request is read:

- **Talk first for big things.** "Join our Slack to discuss your plans", "Share early drafts for feedback on complex features". Look for issues tagged `good first issue`.
- **Bug fixes:** search issues first. If none exists, open one with the deployment mode (self-hosted or cloud), impact, steps to reproduce, expected and actual behavior, and logs. Link it in your pull request with a closing keyword such as `Fixes #123`.
- **Telephony provider pull requests** need documentation **and a video** that shows provider setup, configuring it in Dograh, outbound calls, inbound calls, number provisioning and any KYC flow, and error handling (including adding a number the account does not own). Add API doc links in code comments. Extras such as call transfer go in **separate** pull requests.
- **AI provider pull requests** (TTS, STT, LLM, realtime, embeddings): the provider must have been generally available with a stable public API for **at least six months**. You must explain the user need and the benefit over existing providers, and test with a **real account** in Dograh. Mocks are "not evidence". You supply redacted evidence: credential setup, UI configuration, a real workflow run, request and response logs, invalid-credential and network-error behavior, plus the test date, commit SHA and API version. "Pull requests without a convincing provider-value case or complete live Dograh evidence will be rejected without detailed implementation review."
- **Security:** do not use public issues. Report at the repository's private security advisory page (see `SECURITY.md`).
- **License:** BSD 2-Clause. We found no CLA or DCO text in the root files or `.github/`.

Not in `CONTRIBUTING.md`: code style, branch names and commit rules. They are in the files below.

## Commit and pull request conventions

- **Conventional Commit titles.** No document says so, but `.github/workflows/pr-conventional-labeler.yml` parses the title with `^([a-zA-Z]+)(\([^)]*\))?!?:` and labels it `feat`, `fix`, `docs`, `perf`, `refactor` or `chore`. Those labels drive the changelog. Write `fix(tts): handle empty audio`, not `Fixed stuff`.
- Release notes come from Release Please. Do not edit the version by hand.
- The pull request template is one checkbox: you read the contributing guide.
- Push to **your fork's** `origin`. Open the pull request against `dograh-hq/dograh:main`. The reference page says: "Never push directly to `upstream`."

## Set up, step by step

You need Git, Docker and VS Code with the Dev Containers extension (the documented path). The steps from `docs/contribution/setup.mdx`:

1. Fork `dograh-hq/dograh` and clone **your fork**. If you cloned the original, run `bash scripts/setup_fork.sh` once. It fixes `origin`, adds `upstream`, initializes the submodule, makes a Python 3.13 `venv/`, and copies the three `.env` example files.
2. Open the folder in VS Code and choose **Dev Containers: Reopen in Container**. The first build takes several minutes. It starts Postgres, Redis and MinIO, seeds the Python venv, reinstalls Pipecat **editable** from the submodule, writes the env files and runs `npm ci`.
3. In a container terminal: `bash scripts/start_services_dev.sh`. It stops old processes, runs `alembic upgrade head`, starts four services (ARI manager, campaign orchestrator, uvicorn with reload, ARQ worker) and waits for `/api/v1/health`.
4. In a second terminal: `cd ui && npm run dev -- --hostname 0.0.0.0`.
5. Open `http://localhost:3000`.

Useful facts:

- Only the uvicorn app reloads on edit. `arq`, `campaign_orchestrator` and `ari_manager` need a restart.
- The AI agent builder runs in the ARQ worker. "Running Uvicorn alone accepts requests but leaves them queued."
- Debug configs are in `.vscode/launch.json`, with `justMyCode: false`. Breakpoints inside `pipecat/` work because it is installed editable.
- Without a devcontainer, `docker-compose-local.yaml` gives you Postgres, Redis and MinIO, and `scripts/setup_requirements.sh` installs everything with `uv`.
- Dograh's docs offer a setup skill for Claude Code and Codex that runs these steps for you.

## Commands you will use

| Task | Command |
|---|---|
| API tests | `source venv/bin/activate && set -a && source api/.env.test && set +a && python -m pytest api/tests/...` |
| Format | `./scripts/format.sh` (ruff on `api`, ruff on `pipecat`, eslint fix on `ui`) |
| Lint | `./scripts/lint.sh` (`mypy api`, `ruff check`, `ruff format --check`) |
| UI tests | `cd ui && npm test` (vitest) |
| New API route used by the UI | run the backend, then `cd ui && npm run generate-client` |
| Docs OpenAPI | `python -m scripts.dump_docs_openapi` with `api/.env` loaded |
| Migration | `./scripts/makemigrate.sh "description"` then `./scripts/migrate.sh` |

Each `.sh` has a `.ps1` twin. `scripts/AGENTS.md` says: "When you edit one, edit the other in the same change."

Backend rules from `api/AGENTS.md`: routes do HTTP only, database code lives in `db/` clients, multi-step logic in `services/`, every organization-scoped query must pass `organization_id`, and multi-worker state changes go through `WorkerSyncManager`.

## What CI checks

| Workflow | When | What |
|---|---|---|
| `api-tests.yml` | PR touching `api/`, the submodule or `scripts/` | Postgres + Redis, Python 3.13, Node 22 (a test shells out to Node), `pytest tests/ -xvs` |
| `pre-pr-drift-check.yml` | PR touching api, ui, pipecat | Runs `format.sh` and fails if files change; same for the UI lint fix; regenerates `docs/api-reference/openapi.json` and fails on drift |
| `pr-conventional-labeler.yml` | PR title edits | Labels by title type |
| `release-automation.yml`, `docker-image.yml`, `release-deployment.yml` | on main and releases | Release Please, container images, Vercel deploy |

**What CI does not run:** the UI's vitest suite (72 test files), `tsc`, `next build`, and `scripts/lint.sh` (mypy). Run them yourself. A pull request that fixes this is a good first contribution.

## Ten places to start

These are **our inferences** from reading, with evidence. Check each is still open and ask in Slack before you start a big one.

| # | Idea | Size | Evidence |
|---|---|---|---|
| 1 | Run UI tests, `tsc` and `next build` in CI | small | `ui/package.json` has `"test": "vitest run"`; no workflow runs it |
| 2 | Fix docs drift: `wait_for_user_response` is documented but stripped; the QA docs link points to getting-started | small | `docs/developer/workflow-schema.mdx`, `api/tests/test_dto.py:136`, `ui/src/constants/documentation.ts` |
| 3 | A contributor page for "change Pipecat and Dograh together" | small | `docs/contribution/` has two pages and no such guide |
| 4 | Tests for `CustomEdge.tsx` geometry, `AddNodePanel` limits, `MentionTextarea`, `PropertyInput` | medium | `components/flow/` tests cover only four components |
| 5 | A path overlay on the graph after a call | medium | The run page lists transitions but draws no overlay (we looked) |
| 6 | Cycle rules for graphs | medium, design first | `workflow_graph.py:334` TODO |
| 7 | An evals README, and a CI smoke test for `evals/stt` | small | no `evals/README.md`; the visualizer's README is the create-next-app boilerplate |
| 8 | A provider integration (TTS, STT or telephony) | large, with strict evidence | changelog shows steady contributor-led additions |
| 9 | Tidy housekeeping: unused `zundo`, Node version mismatch, `setup_pipecat.sh` shorter than `setup_requirements.sh` | small | `ui/package.json`, `.nvmrc` vs workflows |
| 10 | Telephony socket token replay | larger, security-sensitive | `routes/telephony.py:649`. Contact maintainers privately first |

A good first pull request is number 1, 2 or 7. They teach you the CI loop with little risk.

## Changing the Pipecat fork

If your change belongs in Pipecat (for example, a bug in a serializer), the path is not in the public docs. From the merge skill and CI configuration, we infer it works like this: the change goes into `dograh-hq/pipecat` first, then a Dograh pull request bumps the submodule pointer. A contributor without write access to the fork needs a maintainer. **Ask first.** Also check whether the bug exists upstream. A fix that upstream Pipecat accepts is better for everyone and removes a patch Dograh must carry ([lesson 16](lesson:pipecat/living-with-a-fork)).

:::try
Fork Dograh. Run the three commands `./scripts/format.sh`, `./scripts/lint.sh` and `cd ui && npm test` on a clean checkout. Note which fail on `main`. That list is your first issue report, if it is not already one.
:::

:::check Your pull request adds a new TTS provider and includes unit tests with mocks. Why may it be rejected without review?
CONTRIBUTING requires evidence from a real account and a real Dograh workflow run, plus request logs and error behavior. Mocks "are not evidence that the Dograh integration works". The provider must also have been generally available for six months.
:::

:::check Your PR title is "Fixed stuff". What happens?
The labeler workflow finds no conventional type, so the PR gets no changelog label. Use `fix(scope): what changed` so Release Please can file it.
:::
