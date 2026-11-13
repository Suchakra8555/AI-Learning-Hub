---
title: Living with a fork: how Dograh stays close to Pipecat
summary: Dograh keeps its Pipecat fork alive with tag merges, a written merge procedure and tests on its own wrappers. You learn the two layers that can break, the invisible conflicts, and the rules that keep history safe.
time: 20 min
---

Forking a fast-moving framework is easy on day one and expensive on day 300. Pipecat released 1.15 on 28 October 2026 and 1.16 on 11 November. Dograh's way of coping is worth studying, because it is written down.

## The written procedure

Dograh ships a skill file for coding agents at `.agents/skills/merge-pipecat-upstream/SKILL.md`. It is the best document about the fork, and it is meant to be read by people too. Key points, quoted or closely paraphrased:

- The `pipecat/` folder is a Git submodule of `dograh-hq/pipecat`. The Dograh repo pins one commit of it. Upstream is usually not configured as a remote.
- Customization lives in **two layers**, and both must be audited on every merge:
  1. **In-fork changes**: Dograh-owned modules (`services/dograh/`, the extra serializers, `call_strategies.py`) plus patches to upstream files (aggregators, transports, turn tracking).
  2. **`api/`-side wrappers**: subclasses in the Dograh repo (`api/services/pipecat/`, `api/services/telephony/providers/*/`, `api/services/workflow/pipecat_engine*.py`) that "override upstream hooks and reach into private state (`self._session`, `self._bot_is_responding`, ...). These break **silently** on upstream refactors, with no merge conflict and no import error."
- Work on a branch `merge-vX.Y` in the fork and `bump-pipecat-X.Y` in the Dograh repo.
- **Never rebase fork `main`.** "Old dograh-repo commits reference its commits via submodule pointers; history must stay append-only."
- Recon *before* merging: diff the new tag against the fork, classify each patched file as **keep ours** (upstream did not touch the logic), **take theirs** (upstream fixed the same problem) or **rework** (both changed, port the intent).
- Read the upstream changelog for the range. It names breaking changes the diff hides.

## The invisible conflict

The skill describes a failure that no tool catches:

> Some **take theirs** verdicts are invisible in the diff: upstream sometimes rejects a fork patch and fixes the same bug its own way. Nothing conflicts, so the merge keeps both, two mechanisms for one problem, where whichever trips first silences the other, with no marker and no failing test to show for it.

Their precedent: at v1.8.1 the fork's patch to bound the output-transport drain (#5217) was closed upstream in favor of #5424. After the merge, the fork's 5-second bound fired before upstream's 10-second one, so the hang stayed fixed but upstream's error report was lost. The detection method is manual: list your closed-unmerged PRs to upstream and read the close comment on each. We saw the same pattern in the code: commit `3d0d24bfa` is "drop the drain bound superseded by upstream's write timeout".

A leftover `changelog/<pr>.md` file is the same signal from the other side. If upstream merged that PR, it consumed the note, so the fork's copy is dead weight.

## What breaks on upgrade

From our reading of Dograh's side:

- `DograhPipelineWorker` overrides private methods (`_cancel`, `_setup_within_timeout`, `_cleanup`). Its docstring says to keep the lifecycle tests when upgrading Pipecat.
- `PipecatEngine` calls `llm._update_settings(...)` and `llm._context`.
- The fork's own history shows follow-ups after most merges: "Fix Dograh services for Pipecat 1.5 contracts", "adapt Dograh services to Pipecat 1.8 contracts", "Use upstream MCP 2 client contracts", "Restore upstream LLMContext tool updates".
- Pipecat deprecates names steadily. In the fork's own checkout, `PipelineTask`, `PipelineRunner` and `UninterruptibleFrame` are already flagged deprecated, so any code written against them has a removal date (2.0.0 for the first two).

## Habits to copy

1. **Tests on the seams.** The fork has 24 new test files, including `test_fork_serializer_contracts.py` and `test_llm_transition_deferral.py`. The skill says to validate with `python -c "import api.app"` and the fork's Dograh tests after every merge.
2. **Lifecycle tests for any private override.** If you must override a private method, write a test that fails loudly when the method changes.
3. **Small, titled commits and changelog notes** per fix, so a future merge can classify them.
4. **Try upstream first.** The fork takes upstream's fixes early and files its own PRs (the skill tells you how to list them).
5. **Know your lag.** Dograh trails upstream by one to five days on the versions it merges, and skips some versions. Pick a policy and write it down.

:::warn What we did not find
No contributor-facing page explains how to change Pipecat and Dograh together. `docs/contribution/` has only a setup page and a reference page. The skill file and the CI trigger (`api-tests.yml` runs on submodule pointer changes too) are the nearest thing. If you want to change the fork itself, ask in Dograh's Slack first. See [lesson 18](lesson:pipecat/contribute-to-dograh).
:::

:::try
Read `SKILL.md` end to end. Then pick one patched file from [lesson 15](lesson:pipecat/what-dograh-changed) and write the three-way verdict (keep, take theirs, rework) you would give it against the v1.16.0 tag. Check upstream's `git log v1.15.0..v1.16.0 -- <path>` to justify it.
:::

:::check What is an invisible conflict, and how do you find one?
Upstream fixed a bug its own way after rejecting your patch. The merge applies both with no conflict, and one silences the other. You find it by listing your closed-unmerged upstream PRs and reading each close comment.
:::

:::check Why does Dograh forbid rebasing the fork's main branch?
The Dograh repo records fork commits by hash in its submodule pointer. Rebasing rewrites those hashes, and old Dograh commits would point to commits that no longer exist.
:::
