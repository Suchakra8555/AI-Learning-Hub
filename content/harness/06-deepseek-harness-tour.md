---
title: A guided tour of DeepSeek Harness
summary: What it is, how to run it, how to read its settings, and how to write your first plugin. Based only on its own docs.
time: 25 min
---

This lesson walks through DeepSeek Harness (`dsh`) using its own documentation. We read its README, architecture doc, CLI README, safety file, and the "develop" tutorial. Anything we could not confirm there is marked, so you know what to check yourself.

:::warn Before you start: it is a developer preview
The README says it is in developer preview and warns "THERE WILL BE COMPATIBILITY-BREAKING CHANGES." The SAFETY file says it "has not undergone a security audit and must not be treated as secure or production-ready." It can run model-generated code and commands, load third-party plugins, and reach the network, processes, credentials, and files. Use a disposable folder, container, or virtual machine, and keep backups. Do not point it at anything you cannot afford to lose.
:::

**Official sources:** the repo at [github.com/deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) and the docs site its README names, [deepseek-harness.github.io/deepseek-harness](https://deepseek-harness.github.io/deepseek-harness/). Exact commands and file names can change between releases. When something here disagrees with those, they win.

## What it is

From the README: DeepSeek Harness is "an open-source agent harness developed by DeepSeek AI", under the MIT license, "built on an everything-is-a-plugin architecture and powered by Cordis". Cordis is a separate open-source framework ([github.com/cordiverse/cordis](https://github.com/cordiverse/cordis)) that handles plugins, services, and events.

It needs Node.js.

## Map it to what you already know

Every part you learned in this track has a home in it.

| Idea from this track | Where it shows up in DeepSeek Harness (per its docs) |
|---|---|
| The loop | A default loop driver, reached through `ctx.agentLoop`; the agent interface is `ctx.agents` |
| Steps and turns | A **step** is one model request plus the tools it calls; a **turn** is zero or more steps |
| Tools | A scoped tool registry with guarded execution, `ctx.tools` |
| Model adapters | Registered on `ctx.llm` |
| Prompt building | `ctx.systemPrompt` assembles prompt sections and tool schemas |
| Permissions and sandbox | Approval policy and sandbox in the `dsh-base` bundle; process confinement through `ctx.sandbox` |
| The session log | Append-only events in `ctx.sessions`; model history is derived from it |
| Hooks | Events such as `agent/pre-step`, `tools/pre-execute`, `tools/post-execute`, `agent/turn-stopping` |
| Sub-agents | Mentioned as "subagent providers"; an experimental agent teams feature, `ctx.agentTeams` |
| UI | Built by driving `ctx.agents` and rendering from `session/event` |

(`ctx` is short for "context": the object a plugin receives that gives it access to services. You will see it in the plugin example below.)

## Run it

The README's quick start:

```bash
npx @deepseek-ai/dsh web
```

That starts a web interface at `http://127.0.0.1:3080` and opens your browser. Add `--no-open` to skip opening it. In the web UI you enter your model's API key under Settings, then Models, according to the user guide. You also add a workspace folder, since a fresh UI has none selected. The guide says the UI asks before operations that need approval under the active permission policy.

To run from source:

```bash
git clone https://github.com/deepseek-ai/deepseek-harness.git
cd deepseek-harness
pnpm install
pnpm run build
pnpm dsh web
```

`pnpm run build` prepares the built files. `pnpm dsh web` uses them without rebuilding. For development, `pnpm run dev:web` builds, serves, and rebuilds as you edit.

*Not stated in the pages we read:* Windows-specific steps, the minimum Node.js version, and the list of supported model providers. The docs name a providers page for the last one. Check it before you plan around a particular model.

## The command line

From the CLI README:

| Command | What it does |
|---|---|
| `dsh web` | Start the web profile |
| `dsh --profile headless "job"` | Run one job in a saved session, print the final answer, and exit |
| `dsh --profile sdk` | A JSON-RPC server over stdio, for programs to drive |
| `dsh --profile sdk-minimal` | The same, with a minimal agent setup |
| `dsh --profile acp` | An ACP server over stdio |
| `dsh plugin --profile <name> <pnpm args>` | Manage a profile's plugins; it forwards to pnpm in the profile folder |
| `dsh --profile web --dump-config` | Print the composed configuration |

Two flags are worth remembering for learning: `--dump-config` shows what the harness decided to load, and `--dump-config-schema` prints the rules for valid settings as JSON Schema. The first unknown word on the command line starts the app's own arguments, so `dsh --profile headless "run the tests"` passes your sentence to the app.

*Not found in the pages we read:* a full table of flags, and any resume flag. Run `dsh --help`.

## How its settings are layered

This is the most "harness engineering" part. Settings are not one file. They stack. Per the CLI README, they apply in this order:

1. Each **bundle's** settings, in the order the profile lists its bundles.
2. The profile's own `cordis.patch.yml`.
3. A `cordis.patch.yml` in your Harness home folder (the `DSH_HOME` setting).
4. Any `--patch` files you pass on the command line.

Each layer is applied on top of the ones before it. The settings are YAML **patches**: from its architecture doc, a patch "targets a row by id and replaces its whole config, or inserts new rows." So you can change one plugin's settings, or add a new plugin, without copying the whole setup.

:::note One inconsistency
The tutorial passes an overlay called `cordis.yml` using `--patch`, while the architecture and CLI docs use `cordis.patch.yml` for the profile and home layers. We could not confirm from the pages we read whether `--patch` accepts any file name. Follow the tutorial, and check the CLI reference if it fails.
:::

## Your first plugin

The develop tutorial builds the smallest possible plugin. It is only a few lines.

```ts
// scratch-plugin/src/my-plugin.ts
import type { Context } from '@deepseek-ai/cordis'

export const name = 'hello-plugin'

export function apply(ctx: Context) {
  // Required dependencies are ready before apply runs.
  console.log('[hello-plugin] plugin loaded!')
}
```

Two parts to know:

- `name` identifies the plugin.
- `apply(ctx)` runs when the plugin loads. `ctx` is the doorway to everything else.

You tell the harness to load it with a small YAML overlay:

```yaml
# scratch-plugin/cordis.yml
insert:
  - id: hello
    name: '/absolute/path/to/deepseek-harness/scratch-plugin/src/my-plugin.ts'
```

The docs stress that the plugin path **must be absolute**. Then start it with the overlay:

```bash
pnpm dsh web --patch ./scratch-plugin/cordis.yml
```

If it works, the terminal prints `[hello-plugin] plugin loaded!`.

### Making a plugin wait for a service

If your plugin needs another service, say the tools service, declare it:

```ts
export const inject = ['tools']
```

The framework then waits until `tools` is ready before calling `apply`. The docs describe the same idea in object form (`export default { name, inject, apply(ctx) {...} }`) and class form (for a plugin that *provides* a service).

### Registering a tool

The docs show that tools are added with `ctx.tools.register(...)`. The full tool format lives in a separate page (`docs/user/develop/basic/tool.md`) that we did not read, and the tutorial we did read has only a placeholder. So we will not guess the format. Open that page when you are ready to write a real tool.

## Where to go in the official docs next

The pages the docs name but we have not covered:

- Model providers (`docs/user/guide/providers.md`)
- The Python SDK guide (`docs/user/guide/python-sdk.md`)
- Public deployments (`docs/user/guide/public-deployments.md`)
- Tool writing and configuration (`docs/user/develop/basic/tool.md` and `config.md`)
- A primer on Cordis (`docs/cordis-primer.md`)
- Agent lifecycle and tool execution pipeline pages
- The research paper the README cites: [arxiv.org/abs/2608.25512](https://arxiv.org/abs/2608.25512)

## How to treat it as a learning tool

- Read the **architecture doc** after this lesson. You now know the vocabulary.
- Run it in a throwaway folder or container and look at the **session log** it writes.
- Use `--dump-config` to see how a profile becomes a list of plugins.
- Write the hello plugin, then add a listener on a hook such as `tools/pre-execute` that prints every tool call. You will have built an audit log with 10 lines.
- Do **not** use it for anything where a mistake is costly until its authors say it is ready.

:::check Name the four layers of settings, from first to last applied.
Bundle settings, the profile's `cordis.patch.yml`, the home folder's `cordis.patch.yml`, then any `--patch` files. Each layer is applied on top of the earlier ones.
:::

:::check Why does the tutorial say the plugin path must be absolute?
The docs state it as a requirement. We did not find the reason in the pages we read. A likely one is that the path is read by the harness, not by your shell, so "relative to what?" has no clear answer. Treat that as a guess and always use absolute paths.
:::

:::check What is `--dump-config` good for?
Seeing exactly which plugins and settings the harness composed from all its layers, so you can debug "why is this plugin loaded?" without guessing.
:::
