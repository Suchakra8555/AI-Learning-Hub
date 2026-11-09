---
title: Structured output, getting data back and not prose
summary: Programs need JSON, not paragraphs. Ask for a shape, check the reply, and retry once when it is wrong.
time: 15 min
---

When code reads the model's reply, free text is a problem. "Sure! Here is the result:" breaks `json.loads`. The fix has two halves: ask clearly, then **never trust the reply until you have checked it**.

## Ask

```python
PROMPT = ('Read the message and answer ONLY with JSON like '
          '{"topic": "returns" | "shipping" | "other", "urgent": true | false}.\nMessage: ')
```

## Check

`code/foundations/structured_output.py` rejects anything that is not exactly the shape we asked for:

```python
def parse(text):
    try:
        data = json.loads(text.strip().removeprefix("```json").removesuffix("```").strip())
    except json.JSONDecodeError:
        raise ValueError("not JSON")
    if data.get("topic") not in TOPICS or not isinstance(data.get("urgent"), bool):
        raise ValueError(f"wrong fields: {data}")
    return data
```

It runs three bad replies through the check. Real output:

```text
rejected: Sure! Here you go -> not JSON
rejected: {"topic": "billing", "urgent": false} -> wrong fields: {'topic': 'billing', 'urgent': False}
rejected: {"topic": "other"} -> wrong fields: {'topic': 'other'}
checks passed
```

## Retry once

If the check fails, send the prompt again with the reason added. One retry fixes most slips. If it fails twice, raise an error. Do not loop forever, and do not guess.

:::note
Many providers also offer a built-in "JSON mode" or "structured output" feature that forces valid JSON. Use it when you have it, and still check the values yourself. Look up your provider's current docs, as the names change.
:::

:::warn
A reply that is valid JSON can still be wrong. `{"urgent": false}` for an angry customer parses fine. Checking the shape is the first test, not the last. [Evals](lesson:rag/measure-quality) test the content.
:::

:::check Why validate the reply when you asked for JSON in the prompt?
A prompt is a request, not a guarantee. The model can add words, miss a field, or use a value you did not allow.
:::
