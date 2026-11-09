---
title: Tools and permissions
summary: How a model asks for actions, and how a harness decides which ones to allow.
time: 18 min
---

A **tool** is a function the model may ask the harness to run. The model never runs anything. It writes a request, like "please call `read_file` with name `notes.txt`", and the harness decides what happens.

That split is the most important safety fact in agent design: **the model proposes, the harness disposes.**

## What a tool looks like

Each tool has four parts:

| Part | Example | Who it is for |
|---|---|---|
| Name | `read_file` | Both |
| Description | "Read a file. args: name" | The model, so it knows when to use it |
| Input shape | `{"name": string}` | The harness checks arguments against it |
| The code | `read_file(args)` | The harness runs it |

In the mini harness:

```python
TOOLS = {
    "list_files": {"fn": list_files, "needs_approval": False, "doc": "List files in the workspace."},
    "read_file":  {"fn": read_file,  "needs_approval": False, "doc": "Read a file. args: name"},
    "write_file": {"fn": write_file, "needs_approval": True,  "doc": "Write a file. args: name, content"},
}
```

The descriptions get sent to the model on every request. That makes them a kind of prompt. A vague description leads to tools used wrongly. Write them as if explaining the tool to a new coworker.

## Good tool design

- **Small and clear.** `read_file` and `write_file` beat one giant `do_file_stuff`.
- **Precise input.** Reject unknown or missing arguments.
- **Helpful errors.** "File not found. Files here: a.txt, b.txt" lets the model recover.
- **Bounded output.** Cap result size.
- **Few tools.** Every extra tool is more for the model to misuse. Ten good tools beat fifty overlapping ones.

## Permissions: three outcomes

When the model asks for a tool, the harness should have exactly three possible answers:

| Answer | Use for | Example |
|---|---|---|
| **Allow** | Safe, read-only actions | List files, read a file |
| **Ask** | Actions that change things or cost money | Write a file, send an email, run a command |
| **Deny** | Actions that should never happen | Anything outside the workspace |

This is the same pattern as access control in any system: default to the least power, and grant more on purpose.

The mini harness implements all three. Run it and answer `y`, then run again and answer `n`:

```bash
cd code/harness
python mini_harness.py
```

Look for three behaviors:

1. `list_files` and `read_file` ran with no question.
2. `write_file` stopped and asked you.
3. `read_file` on `../mini_harness.py` was refused: it points outside the workspace.

## A sandbox is a box around the tools

A **sandbox** limits what a tool can reach even if the model asks for something bad. Think of it as the walls, with permissions as the doors.

Layers, from weakest to strongest:

1. **Path checks in your code.** What the mini harness does (`_safe_path`). Easy, but you must get every tool right.
2. **A limited folder.** The agent works in a copy of the project, not your whole disk.
3. **A limited user account.** Without rights to anything sensitive.
4. **A container or virtual machine.** Cut off from your real machine, network, and credentials.

Use the stronger layers when the agent can run commands. A command tool can do anything the account running it can do.

DeepSeek Harness says its sandbox backend sits behind `ctx.sandbox`, and that code which spawns processes should "wrap argv" (the command and its arguments) through it. In its own safety file it warns plainly that **sandboxing and approvals do not guarantee isolation**. Treat that as true of every harness.

## Approvals that people can bear

Approvals have a hidden cost. If every action asks, people click "yes" without reading, and the check becomes a ritual. Good designs:

- Allow read-only actions without asking.
- Ask for risky ones, and **show what will happen** in plain words ("Write 16 characters to summary.txt") and not just a tool name.
- Let people approve a *kind* of action for the session ("allow reads in /docs").
- Never offer "approve everything" without a visible warning.

## The path check, line by line

```python
def _safe_path(name):
    p = (WORKSPACE / name).resolve()
    if WORKSPACE.resolve() not in p.parents and p != WORKSPACE.resolve():
        raise PermissionError(f"path outside workspace: {name}")
    return p
```

`resolve()` turns `workspace/../mini_harness.py` into its real location first. That is the key step. Checking the text of the name ("does it start with workspace?") is a classic mistake that `..` defeats.

:::warn Dangerous tools
A tool that runs shell commands, sends messages, spends money, or touches production is not a normal tool. Give it its own approval rule, its own log lines, and its own limits. Think about what happens if the model is tricked into calling it (see the safety lesson).
:::

:::try
Add a tool called `delete_file` to `mini_harness.py` with `needs_approval: True`. Make sure it uses `_safe_path`. Then edit `ScriptedModel.plan` to ask for it. What is the smallest change that makes it safe by default?
:::

:::check Why is "the model proposes, the harness disposes" a useful rule?
The model's output is only text until the harness acts on it. All control, checks, and limits live in the harness, where you can test them, instead of in a prompt that a model might ignore.
:::

:::check Why call resolve() before checking a path?
It turns tricks like `../` into the real final path. Without it, a name that looks safe can point outside the workspace.
:::
