---
title: LangSmith Engine, Insights, and Chat, tools that find problems
summary: What each one does, which ones propose fixes, what they cost, and why you still review every change.
time: 15 min
---

You asked about LangChain's engine that finds and fixes issues. The docs describe three separate features. Only one proposes fixes. There is no product called "auto-fix".

## LangSmith Engine

The docs call it "the LangSmith agent for agent engineering". It reads production traces, finds recurring problems, ranks them by severity, diagnoses them, and can propose a fix as a pull request (or GitLab merge request) for agents built with Deep Agents, LangChain or LangGraph ([Engine](https://docs.langchain.com/langsmith/engine.md), [issues](https://docs.langchain.com/langsmith/engine-issues.md)).

Key facts from the pages:

- **It never merges a pull request itself.**
- It attaches new matching traces to open issues, reopens issues that return, and can turn failing traces into dataset examples for offline evals.
- Issue states: `open`, `fixing`, `watching`, `completed`, `ignored`.
- **Fix validation** builds a preview deployment from the PR, replays up to five traces against it, and retries up to three times. It is labeled **private beta**, Cloud only. "Inconclusive" means no trustworthy evidence, not "fixed" ([fix validation](https://docs.langchain.com/langsmith/engine-fix-validation.md)).
- Cost: billed in LangChain Standard Units, $1 USD each, with a default limit of 750 per month until an admin changes it. Plan availability is not stated on the page.

## Insights

Insights groups traces into categories to show usage patterns and failure modes, with an executive summary. It **reports and does not fix**. It needs a Plus or Enterprise plan. The page's cost estimate is about $1 to $2 per 1,000 threads with OpenAI models and $3 to $4 with current Anthropic models. Run it from the UI, the SDK, or the CLI, on up to 1,000 traces per report ([Insights](https://docs.langchain.com/langsmith/insights.md)).

## LangSmith Chat (formerly Polly)

An assistant inside LangSmith where you ask questions about traces, prompts and evals. When asked, it can edit prompts in the Playground, create datasets from runs, and write evaluator code. The page does not say it fixes problems on its own ([Chat](https://docs.langchain.com/langsmith/chat.md)).

| Feature | Finds problems | Proposes fixes | Acts without you |
|---|---|---|---|
| Engine | Yes | Yes, as a PR | No |
| Insights | Yes | No | No |
| Chat | When you ask | Edits when you ask | No |

## The rule that does not change

A PR from Engine is a proposal. Review it like any other, and run your own [test set](lesson:evals/why-test-an-agent) on it. Preview deployments inherit the baseline's secrets, so keep that in mind.

We did not run Engine. It needs a LangSmith organization and traced production runs.

:::check Engine opens a pull request and fix validation says "inconclusive". Is the bug fixed?
No. Inconclusive means the check had no trustworthy evidence either way. Test the change yourself before merging.
:::
