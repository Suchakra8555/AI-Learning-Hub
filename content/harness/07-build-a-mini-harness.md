---
title: Build and extend a mini harness
summary: Read the 120-line harness in this repo, then grow it with five exercises that each teach one real harness idea.
time: 45 min
---

You have met the parts. Now put your hands on them. `code/harness/mini_harness.py` is a complete, tiny harness. It runs with no installs and no API key, because a scripted stand-in plays the model.

```bash
cd code/harness
python mini_harness.py
```

We ran it as part of building this course. The output on a first run, answering `y` to the approval question:

```text
TASK: Read my notes and save a one-line summary.

step 1: model asks for list_files({})
        result: notes.txt
step 2: model asks for read_file({"name": "notes.txt"})
        result: Meeting moved to Friday. Bring the Q3 numbers.
step 3: model asks for read_file({"name": "../mini_harness.py"})
        result: ERROR: path outside workspace: ../mini_harness.py
step 4: model asks for write_file({"name": "summary.txt", "content": "Notes were read."})
  APPROVE write_file({"name": "summary.txt", "content": "Notes were read."})? [y/N]
        result: wrote 16 characters to summary.txt

DONE after 5 steps: I read notes.txt and wrote a summary.
```

## Read it in this order

The file has numbered sections that match the lessons.

| Section | What to look for | Lesson |
|---|---|---|
| 1. TOOLS | A dictionary. Each tool has a function and a flag for approval. | [3](lesson:harness/tools-and-permissions) |
| 2. POLICY | `ask_human`. A real harness would show a button. | [3](lesson:harness/tools-and-permissions) |
| 3. THE LOOP | `run()`. The `for` loop with a step limit. | [2](lesson:harness/the-agent-loop) |
| 4. THE LOG | `log_event` writes. `messages_from_log` rebuilds the model's memory. | [4](lesson:harness/context-memory-and-the-log) |
| 5. LIMITS | `max_steps`. | [2](lesson:harness/the-agent-loop) |

Notice what is **missing**, because those gaps are your exercises: it has no hooks, no secret scrubbing, no repeat detection, only a pretend model, and no way to add tools without editing the file.

## Exercise 1: add a tool, safely

Add `delete_file`. It must:

- use `_safe_path`,
- need approval,
- return a clear message if the file does not exist.

Then change `ScriptedModel.plan` to ask for it, and run once approving and once denying.

*What you learn:* a new tool is three decisions: what it does, whether it asks, and what it says when it fails.

## Exercise 2: stop a loop that is going in circles

Make the harness stop if the model makes the **same tool call with the same arguments three times in a row**. Write a `stopped` event with reason `repeat`.

Hint: keep a short list of recent `(tool, args)` pairs inside `run()`.

*What you learn:* step limits catch long loops. Repeat detection catches short ones early and saves money.

## Exercise 3: hide secrets before they reach the log

Create `workspace/config.txt` containing a line like `API_KEY=abc123`. When the agent reads it, the log must not hold `abc123`.

Write `scrub(text)` that replaces anything after `KEY=`, `TOKEN=`, or `PASSWORD=` with `[hidden]`, and call it inside `log_event` for `tool_result`.

*What you learn:* the log is permanent and the model sees what is in it, so scrubbing happens before writing, not after.

:::warn
Your scrubber will miss things. Real secrets have many shapes. That is the lesson: scrubbing lowers risk, and it does not remove it. Keep secrets out of the workspace in the first place.
:::

## Exercise 4: add hooks

Add two lists of functions, `before_tool` and `after_tool`. The loop calls each before and after running a tool. A before-hook can return `"deny"` to block.

Write two hooks:

1. A `before_tool` hook that denies any `write_file` whose name ends in `.py`.
2. An `after_tool` hook that prints how long the tool took.

*What you learn:* this is the heart of the plugin idea ([lesson 5](lesson:harness/everything-is-a-plugin)). Your safety rule is now separate code that you can add or remove without touching the loop.

## Exercise 5: replace the pretend model with a real one

`ScriptedModel` has one method, `next(messages, tools)`, that returns either a tool call or a final answer. Write a class with the same method that calls a real model.

You will need to:

1. Describe each tool to the model with a name, a description, and the shape of its arguments. Your `doc` strings are a start, and the API also wants a proper input schema.
2. Send the conversation so far, rebuilt from the log.
3. Read the reply. Most model APIs return either text, or a request to use a tool with arguments.
4. Return `{"type": "final", ...}` for text and `{"type": "tool_call", ...}` for a tool request.
5. Send tool results back in the format the API expects. Many APIs require each result to be tied to the id of the request it answers, so store that id in your `tool_call` log events.

Read your model provider's tool-use guide for the exact message shapes. We do not reproduce them here, because they are specific to each provider and change over time, and we would rather send you to the source than hand you code we have not run against a live key.

*What you learn:* how little the harness has to know about the model. If your harness stays unchanged when the model is swapped, you designed the boundary well.

## A note on what comes next

If you finish these, you have written the core of every agent harness: a registry of tools, a policy gate, a loop with limits, an event log, hooks, and a pluggable model. Everything else in a serious harness (sandboxes in containers, subagents, summaries of old context, web UIs) is a deeper version of one of these.

:::check Which exercise taught the idea behind "everything is a plugin"?
Exercise 4. Hooks let you add a rule as a separate piece of code that the loop calls at fixed points, without editing the loop.
:::

:::check Why must scrubbing happen before the log write?
The log is append-only and also feeds the model's memory. Once a secret is written, it stays and can be sent onward.
:::
