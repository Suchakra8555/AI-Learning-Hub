---
title: The agent loop
summary: Ask the model, run the tool it picked, show it the result, repeat. Simple to say, full of details that matter.
time: 15 min
---

Every agent runs one loop. Learn it and you can read the source of any harness.

```text
1. Build the message  (instructions + history + tools list)
2. Ask the model
3. Did it ask for a tool?
     yes -> run the tool, add the result to the history, go to 1
     no  -> it gave a final answer, stop
```

That is the entire idea. Here are the same steps as code. This is the middle of `code/harness/mini_harness.py`:

```python
for step in range(1, max_steps + 1):
    action = model.next(messages_from_log(), TOOLS)
    if action["type"] == "final":
        print(action["text"])
        return
    result = run_tool(action["tool"], action["args"])   # with permission checks
    log_event("tool_result", tool=action["tool"], text=result)
print("STOPPED: step limit reached")
```

## Words people use

DeepSeek Harness's architecture doc defines two words worth borrowing, and they are clear:

- A **step** is one model request plus the tools it calls.
- A **turn** is zero or more steps, from your message until the agent stops to wait for you.

So a "turn" is one job from your point of view, and each job may take many "steps".

## The loop's real work is in the edges

The core loop is five lines. The rest of a harness is handling what can go wrong around it.

### 1. It must stop

A model can keep asking for tools forever, or go in circles. Every loop needs limits:

| Limit | Protects against |
|---|---|
| Max steps | Endless loops |
| Max time | Hangs |
| Max cost or tokens | Surprise bills |
| A stop button | You, noticing it going wrong |
| Repeat detection | Same tool call with same arguments five times in a row |

When a limit hits, say so clearly in the log and to the user. A silent stop looks like a bug.

### 2. Tool errors go back to the model

A tool will fail: file not found, network error, bad arguments. Do not crash the loop. Send the error text back as the tool's result. The model can read "ERROR: no such file" and try something else.

```python
try:
    result = spec["fn"](args)
except Exception as e:
    result = f"ERROR: {e}"      # the model sees this and adjusts
```

Run `python mini_harness.py` and watch step 3. The scripted model tries to read a file outside its folder, gets an error, and the loop carries on.

### 3. The model asks for things that do not exist

Models sometimes call a tool by the wrong name or with missing arguments. Check before running, and return a clear error.

### 4. Results can be huge

A tool that returns a 2 MB log will fill the model's memory. Cap results, say "output truncated at 8,000 characters", and let the model ask for a specific part.

### 5. Failed steps still need recording

If a model call fails halfway, you must still leave the history in a valid state. DeepSeek Harness's docs say that failed steps "record missing tool results". A conversation where the model asked for a tool and no result was ever recorded can confuse the next call, so the harness fills the gap.

## Hooks: places to step into the loop

Good harnesses let you add rules at fixed points without editing the loop. Typical points:

- **Before a step**: add extra context, check the budget.
- **Before a tool runs**: check permissions, block or change the call.
- **After a tool runs**: scrub secrets from the output, record metrics.
- **When the model wants to stop**: check that the job is truly done, and if not, send it back.

DeepSeek Harness names events like `tools/pre-execute`, `tools/post-execute`, and `agent/turn-stopping` for this. The idea is the same in any system: named moments where your code can look, change, or veto.

## Single loop versus many

A simple harness has one loop. More advanced ones let an agent start **sub-agents**: separate loops with their own limited tools and their own history, handed a small job. The parent gets only the result. This keeps big, messy work out of the main conversation. It also multiplies cost and complexity, so start with one loop.

:::warn
More loops mean more ways to fail. Teams that start with a multi-agent design often spend months debugging coordination that one good loop would have avoided.
:::

:::try
In `mini_harness.py`, change `max_steps=8` to `max_steps=3` and run it. What does the output say? Then find where the code writes `stopped` to the log.
:::

:::check What are the two possible outcomes of each loop pass?
The model asks for a tool, so the harness runs it and loops. Or the model gives a final answer, so the loop ends.
:::

:::check A tool throws an error. Why send the error to the model instead of stopping?
The model can read the message and try a different approach. Stopping would turn a small, fixable problem into a failure.
:::
