---
title: Everything is a plugin
summary: The design idea behind DeepSeek Harness, and why it makes a harness easier to change.
time: 15 min
---

Most software has a core and add-ons. The core is sacred and the add-ons are optional. DeepSeek Harness flips that. Its README calls the design **everything-is-a-plugin**, and its architecture doc says it directly:

> Every part of the product is a plugin, including the model adapter, the tool registry, the session log, and the agent loop itself, so each is replaceable from configuration.

The key phrase is "including the agent loop itself". There is no special, untouchable core. A plugin sits next to other plugins, and you choose which ones to run.

(This lesson explains the idea in plain words. Details of DeepSeek Harness come from its own docs, linked in the next lesson. It is a developer preview, so check them for anything exact.)

## Why anyone would want this

Think about what changes between users of a harness:

| One team wants | Another team wants |
|---|---|
| A web page UI | A command-line tool with no UI |
| Claude as the model | Another model, or a local one |
| Strict approvals on every command | Approvals only on writes |
| Logs in files | Logs sent to a company system |
| A special tool for their ticket system | None of that |

A harness with a fixed core forces everyone into one shape, or into forking the code. A harness where everything is a plugin lets each team **compose** its own from parts.

:::say
Instead of one program with settings, you get a set of parts and a recipe.
:::

## The three words you need

**Plugin.** A piece of code that adds something: a tool, a model adapter, a UI. It is loaded when the harness starts and unloaded when it stops.

**Service.** A capability one plugin offers to others, under a known name. For example, a "tools" service that other plugins can register tools into. DeepSeek Harness describes a **seam** as three parts: a definition of the interface, a provider that implements it, and a consumer that uses it. The point is that a consumer asks for "the tools service" and does not care which plugin supplies it.

**Profile.** A named recipe saying which plugins to run and how they are set up. Different profiles give different products from the same parts.

## What DeepSeek Harness's profiles look like

Its docs list shipped profile templates: `web`, `headless`, `sdk`, `sdk-minimal`, and `acp`. In plain terms:

| Profile | What you get |
|---|---|
| `web` | A browser UI on your machine |
| `headless` | Run one job from the command line, print the result, exit |
| `sdk` and `sdk-minimal` | A program talks to the harness over a pipe, using JSON messages (JSON-RPC) |
| `acp` | A pipe-based server for editor and tool integrations |

Same parts underneath, different recipe on top. The docs also say a profile is stored in the Harness's home folder, and profiles are built from **bundles**, groups of plugins and their settings that ship together. One shipped bundle, `dsh-base`, holds the common pieces: model adapters, tools, saving data, the sandbox and approval policy, settings, credentials, and telemetry.

## Plugins clean up after themselves

A harness that loads and unloads parts on the fly has a hard problem: leftovers. If a plugin registers a tool and is then removed, the tool must go too, or the model will try to call something that no longer exists.

DeepSeek Harness's framework, called **Cordis**, handles this by making registrations **reversible**: things you add through the plugin's context are removed when the plugin unloads. Per its docs, that includes event listeners, tools, and timers. For outside resources you write your own cleanup. The docs' example does this with a function that returns an undo step:

```ts
ctx.effect(() => {
  const timer = setInterval(/* ... */)
  return () => clearInterval(timer)   // runs when the plugin unloads
})
```

You can take this idea anywhere: **anything a plugin starts, the harness should be able to stop.**

## Events: how plugins talk without knowing each other

Plugins coordinate through named **events**. In the previous lesson you saw hook points like "before a tool runs". With a plugin design, those are events that any plugin may listen to.

The practical effect: a safety plugin can listen to "before a tool runs" and block dangerous calls, and no other plugin needs to know it exists. You add the safety by adding a plugin, and remove it the same way.

## Trade-offs, honestly

| Strength | Cost |
|---|---|
| Swap or add parts without forking | More concepts to learn first |
| Teams build their own product from shared parts | Harder to trace a behavior to one place |
| A bug in one plugin is contained | Plugin versions must stay compatible |
| Tests can replace one part | Plugins with wide access mean more trust placed in plugin authors |

That last point is serious. DeepSeek Harness's SAFETY file warns that it can "load third-party plugins", and that plugins deserve review. A plugin runs code inside the harness. Install them like you install any software dependency: from authors you trust, after a look at the code.

## Using the idea in your own system

You do not need Cordis to benefit. In your own harness, even a small one:

1. Put tools in a **registry** (a dictionary, like `TOOLS` in the mini harness), not hard-coded `if` statements.
2. Put the model call behind one function (`model.next(...)`), so models can be swapped.
3. Put permission checks in one place, so there is one door to guard.
4. Write events to a log through one function, so the log has one shape.
5. Keep settings in a file, not in code.

Each of these is a small plugin point. You get most of the benefit at about 5 percent of the machinery.

:::check What does "even the agent loop is a plugin" allow?
Replacing the loop itself from configuration, for example to try a different strategy, without changing the rest of the system.
:::

:::check What is a profile?
A named recipe that says which plugins to run and how they are configured. Different profiles make different products from the same parts.
:::

:::check Why is a plugin system also a security question?
A plugin runs code inside the harness, with whatever access the harness has. Untrusted plugins are untrusted code.
:::
