---
title: Guardrails: checks around the model
summary: A good prompt lowers the chance of a bad answer. Guardrails catch the ones that still happen.
time: 12 min
---

Your bank chatbot is told to be helpful. A user asks which stocks to buy. The model answers with enthusiasm. The bank is not allowed to give that advice.

Prompting alone cannot promise the model will behave. A **guardrail** is a check that sits outside the model and runs on every request or reply. It does not rely on the model's good manners.

## Where checks go

```text
user input -> [input check] -> model -> [output check] -> user
```

- **Input checks** look at what comes in. Examples: block attempts to override your rules, strip personal data, refuse out-of-scope topics.
- **Output checks** look at what goes out. Examples: block advice you may not give, hide card numbers, confirm that the reply has the JSON shape you need.

## Kinds of rule

| Kind | Example |
|---|---|
| Legal and compliance | No investment advice. Add the required disclaimer. |
| Data protection | Never print an email address or card number. |
| Brand | Keep the tone you want, avoid banned phrases. |
| Safety | Refuse harmful requests. |
| Accuracy | Require citations, or say "I don't know" when sources are missing. |

## How to build them

1. **Simple rules.** A regular expression for card numbers, a list of banned topics, a length cap. Fast, cheap, predictable. They miss rewordings.
2. **A second model call.** Ask a model "does this reply give investment advice? yes or no". It catches rewordings but costs a call and can be wrong.
3. **A human.** Send borderline cases to a person.

Layer them. Run the cheap rules first, then the model check on what is left.

## An output check as a prompt

```text
You check replies from a banking assistant.
Reply with exactly one word: PASS or FAIL.
FAIL if the reply recommends a specific investment or promises returns.

Reply to check:
<the draft reply>
```

If the check says FAIL, replace the reply with a fixed safe message.

## Limits

- **Rules only cover what you thought of.** A new kind of misuse passes until you add a rule.
- **Checks can be fooled.** An attacker may phrase a request so the check misses it.
- **False alarms.** Strict rules block good answers. Measure both kinds of error.
- **They are not a replacement for a clear prompt.** Do both.

For agents that can run tools, the same idea shows up as permissions and approval. See [safety and a checklist](lesson:harness/safety-and-checklist). For prompt injection and what to do about it in a RAG app, see [fast, cheap and safe](lesson:rag/fast-cheap-safe).

:::say
Do not ask the model to police itself. Put a check outside it.
:::

:::check Why not just write "never give investment advice" in the prompt?
A prompt is a request, and the model can still slip, or be talked around it. An output check enforces the rule whatever the model does.
:::

## Sources

Based on GeeksforGeeks, [What are AI guardrails](https://www.geeksforgeeks.org/artificial-intelligence/what-are-ai-guardrails/), which loaded fine. The page has no limits section, so the limits above are our own reasoning, not claims from it.
