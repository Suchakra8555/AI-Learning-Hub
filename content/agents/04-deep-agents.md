---
title: Deep agents, managed deep agents, and OpenWiki
summary: A ready-made harness for long jobs, a hosted version of it, and a tool that writes a wiki so coding agents start informed.
time: 20 min
---

Everything here is from LangChain's own docs. We read the pages. We did not run any of it, since each needs provider keys, and managed deep agents needs a LangSmith account.

## Deep Agents

**Deep Agents** is described as an "agent harness for complex, multi-step work". It sits on top of LangChain and LangGraph and adds ([overview](https://docs.langchain.com/oss/python/deepagents/overview.md)):

- **Planning.** A to-do tool that tracks tasks as pending, in progress, or completed. Off by default from v0.7, so you add it.
- **A virtual file system.** Tools like `ls`, `read_file`, `write_file`, `edit_file`, `glob` and `grep`. A **backend** decides where files really live. A shell tool exists only with sandbox backends.
- **Subagents.** A `task` tool hands a job to a helper that works in its own context and returns one final report. That keeps the main agent's context small.
- Also skills, memory files, history summarizing, and `interrupt_on` for approvals.

Compare with the [Harness track](lesson:harness/what-is-a-harness): this is the same set of ideas, packaged.

### Safety notes from the docs ([backends](https://docs.langchain.com/oss/python/deepagents/backends.md))

- `FilesystemBackend` and `LocalShellBackend` are for local tools and controlled CI, not web servers.
- `FilesystemBackend` has no path limit unless `virtual_mode=True`.
- `LocalShellBackend` runs any command with your permissions.
- Agents can read `.env` files in reachable paths. Keep secrets out of reach.
- `StoreBackend` without a per-user namespace is shared by all users of one assistant.

We could not copy the exact minimal example (the fetch tool did not return it), and the install command was not on the overview page. Use the live page.

## Managed Deep Agents

A LangSmith service. You write a project folder with instructions, tools, skills, and a model. A command-line tool called `mda` uploads it, and LangSmith runs the harness and the runtime for you. The quickstart shows these commands ([quickstart](https://docs.langchain.com/langsmith/python/managed-deep-agents-quickstart.md)):

```bash
uvx --from managed-deepagents mda init research-assistant
uv sync
uv run mda dev
uv run mda deploy
```

Status: the quickstart and runtime pages say **public beta**, on LangSmith Cloud only. Pricing and limits are not on the pages we read. Expect changes. For example, `runtime.channel` is documented as deprecated.

## OpenWiki

A command-line tool, documented on LangChain's docs site, that writes and updates a Markdown wiki about a codebase. Coding agents read the wiki first and open source files only when needed ([overview](https://docs.langchain.com/oss/openwiki/overview.md), [quickstart](https://docs.langchain.com/oss/openwiki/quickstart.md)):

```bash
npm install -g openwiki
openwiki --init
openwiki --update
```

It needs Node.js 22.22.0 or newer. Output goes in an `openwiki/` folder, linked from `AGENTS.md`. The pages name no author or version number.

:::warn
OpenWiki sends your code to a model provider. Check your data rules first. In CI it can open pull requests that change several files, so review them like any other PR, and note it sends anonymous telemetry unless you set `OPENWIKI_TELEMETRY_DISABLED=1` ([automate updates](https://docs.langchain.com/oss/openwiki/automate-updates.md)).
:::

## Finding integrations

LangChain's catalog lists plug-ins by provider and by type: chat models, embeddings, vector stores, document loaders, tools, and more. Most packages are named `langchain-<provider>`. In the vector store index, a blank cell in the comparison table means "not marked", not "no". The loader page warns that community loaders are user-contributed and unverified ([providers](https://docs.langchain.com/oss/python/integrations/providers/overview.md), [vector stores](https://docs.langchain.com/oss/python/integrations/vectorstores/index.md), [loaders](https://docs.langchain.com/oss/python/integrations/document_loaders/index.md)).

## Dig deeper

All the sources, page by page, and what we could not read, are in our [LangChain research notes](lesson:research/langchain).

:::check Why use `virtual_mode=True` with a file backend?
Without it, the backend has no path limit, so an agent could read or write outside the project folder.
:::
