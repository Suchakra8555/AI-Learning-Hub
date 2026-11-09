---
title: Your first API call
summary: Send one message to a model from Python using only the standard library, and see what goes over the wire.
time: 15 min
---

An **API** is a way for one program to ask another program to do something. Here, your script sends text to the model provider's server, and the server sends the model's reply back. It is an ordinary web request.

## The whole call

This is `code/foundations/llm.py`, the helper used in this course:

```python
def ask(prompt, system=None, max_tokens=400):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    body = {"model": os.environ.get("LLM_MODEL", "claude-sonnet-5-5"), "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]}
    if system:
        body["system"] = system
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["content"][0]["text"]
```

Read it line by line:

- `messages` is the conversation. One message from the `user` is enough to start.
- `system` is an optional instruction that sets the model's role and rules.
- `max_tokens` caps the length of the reply. It is also a cost guard.
- The key goes in a header. Never put it in your code or a Git repository.
- Without a key, `ask` returns `None`, so the scripts still run and show what they would send.

## Run it

```bash
export ANTHROPIC_API_KEY=your-key      # Windows PowerShell: $env:ANTHROPIC_API_KEY="your-key"
python first_call.py "Explain a hash map in one sentence."
```

:::note What was and was not tested
This repo's scripts were run without a key, so the no-key path is tested. A live call was not run here. Check the [provider's API reference](https://docs.anthropic.com/en/api/messages) if the request shape has changed.
:::

## Things that go wrong

| Symptom | Likely cause |
|---|---|
| `HTTP Error 401` | Wrong or missing key |
| `HTTP Error 429` | Too many requests. Wait and retry. |
| Reply cut off mid-sentence | `max_tokens` too small |
| Timeout | Long prompt or busy server. Retry once, then fail clearly. |

:::try
Call it twice with the same question. Do you get the same words? Then add "Answer in five words." and compare. You have just seen why prompts matter.
:::
