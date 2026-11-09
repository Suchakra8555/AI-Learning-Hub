---
title: Context, memory, and the session log
summary: The model remembers nothing. The harness decides what it sees, and keeps a record of everything.
time: 15 min
---

Here is a surprising fact for newcomers: **a model has no memory between calls.** Each request starts blank. When a chat seems to remember your earlier message, that is because the harness sent the earlier messages again.

So "memory" is something the harness builds. The pieces:

| Kind | What it is | Lives where |
|---|---|---|
| **Context** | The text sent to the model right now | Rebuilt for every request |
| **History** | Everything said and done in this session | The session log |
| **Long-term memory** | Facts that should last across sessions | Files or a database, loaded when needed |

## The context window is a budget

The **context window** is the most text a model can read in one request. Every instruction, every past message, every tool result counts against it.

A long agent session fills it. Many tool results are large (whole files, long command output). Soon the history does not fit. The harness has to choose what to keep.

Common strategies:

- **Truncate tool output.** Keep the first and last part of long results.
- **Drop old, low-value items.** Old file listings rarely matter later.
- **Summarize.** Ask a model to write a short summary of the old part, then replace the old part with it. This is often called **compaction**.
- **Move facts out.** Save notes to a file ("decisions so far") and load only what is relevant.
- **Delegate.** Hand a big sub-task to a sub-agent that returns just a short result.

Each choice trades detail for room. Summaries lose things. That is why the **log** matters.

## The session log: the source of truth

A **session log** is a record of every event, written in order and never edited. Mini harness writes `session.jsonl`, one JSON object per line:

```json
{"t": 1793593355.42, "kind": "user", "text": "Read my notes and save a one-line summary."}
{"t": 1793593355.43, "kind": "tool_call", "tool": "list_files", "args": {}, "step": 1}
{"t": 1793593355.43, "kind": "tool_result", "tool": "list_files", "text": "notes.txt\nsummary.txt"}
```

Run the mini harness, then open the file and read it top to bottom. You can tell the whole story of the job.

### Why append-only

**Append-only** means you only ever add lines to the end, never change or delete old ones. It gives you:

- **Debugging.** You can replay exactly what happened.
- **Audit.** Who approved what, when.
- **Recovery.** If the process crashes, you resume from the log.
- **Trust.** Nobody can quietly rewrite history.

DeepSeek Harness's architecture doc puts this firmly: the log is "the source of model context", and the model's history is *derived* from it (the doc names a function `deriveMessages()` that does this). Its rule is memorable: **"Model-visible means logged."** Everything the model saw is in the log, so every request can be reconstructed afterwards.

The mini harness does the same in miniature:

```python
def messages_from_log():
    """The model's memory is rebuilt from the log."""
    msgs = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e["kind"] in ("user", "assistant", "tool_result"):
            msgs.append(e)
    return msgs
```

Notice the filter. Some log events are for people (like `stopped`) and are not sent to the model. The log holds more than the context does. Context is a *view* of the log.

:::say
The log is what happened. The context is what the model is told about it. Keep them separate and you can always rebuild one from the other.
:::

## What belongs in the log

| Event | Why |
|---|---|
| User messages | The task |
| Model messages | What it said |
| Tool requests and results | What it did |
| Approvals and denials | Who allowed what |
| Failed or retried model calls | Debugging; DeepSeek Harness keeps these as separate `assistant/attempt` events that do not go back into the model's history |
| Limits hit | Why it stopped |
| Settings and versions | Which model, which prompt |

## Log formats change, so plan for it

DeepSeek Harness's docs say its session files are versioned: `session.jsonl` for the first format and `session.vN.jsonl` after that, with older generations never renamed or deleted, and upgrades done one version step at a time. The takeaway applies to your own logs: **put a format version in from the start.** You will change the shape of events later, and you will want to read the old ones.

## Privacy

Logs capture everything, including secrets that appeared in files or command output, and personal data. Decide early:

- Who can read logs.
- How long they live.
- What to scrub (keys, tokens, passwords) before writing.

:::warn
The same append-only property that makes logs trustworthy makes mistakes permanent. If a secret goes in, you cannot just edit the line. Scrub before you write.
:::

:::try
Run `python mini_harness.py`. Then write a few lines of Python that read `session.jsonl` and print only the tool names the agent used, in order. That is the start of a trace viewer.
:::

:::check Why can a harness rebuild the model's context from the log?
Because the log holds every event in order. The context is a selected, trimmed view of it, so the harness can recreate it whenever it needs to.
:::

:::check Compaction saves space. What does it cost?
Detail. A summary leaves things out, so the full record should stay in the log in case you need it.
:::
