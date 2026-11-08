---
title: Secrets, recordings, and privacy
summary: A voice platform holds other people's API keys and records other people's voices. How our platform keeps keys in one place, refuses unsafe config, and where its privacy defaults still fail open.
time: 20 min
---

A customer pastes their ElevenLabs key into your console. Next week a support engineer greps the logs for a call id and finds that key printed in full inside a nested error payload. The same week, the config service blips during a deploy, and every call in that minute gets recorded, including calls for an assistant whose owner turned recording off.

A voice platform holds two kinds of sensitive data: **credentials**, meaning customers' API keys for STT, LLM, TTS and carriers, and **conversation data**, meaning recordings and transcripts of real people talking. This lesson covers both.

## One service decrypts

Customer keys are stored encrypted in the credential service's own Postgres database. It uses **Fernet** from the Python `cryptography` package. Fernet is symmetric encryption with a built-in integrity check. Its docs say a message encrypted with it "cannot be manipulated or read without the key", and that it uses AES-128 in CBC mode with an HMAC-SHA256 check ([cryptography: Fernet](https://cryptography.io/en/latest/fernet/)).

The rule the platform follows: **the credential service is the only service that decrypts.** Everyone else holds an id.

- The console shows a masked hint, like eight stars and the last four characters.
- Exactly one route returns plaintext, and it lives under `/internal`, behind the shared internal key. The gateway refuses any public path with an `internal` segment.
- Each read of a secret writes a row to an access log table, so you can answer "who fetched this key, and when".
- The agent worker fetches the STT, LLM and TTS keys **per call**, all three at once, for that call only.

<figure>
<svg viewBox="0 0 900 270" role="img" aria-labelledby="t-sec d-sec">
  <title id="t-sec">How secrets flow through the platform</title>
  <desc id="d-sec">Top row: AWS Secrets Manager holds one platform secret. A bootstrap step in each container loads it into the environment and then execs the service. Bottom row: the credentials database holds only ciphertext. The credential service, the only decryptor, uses the encryption key from its environment. The agent worker fetches plaintext keys per call over an internal route and passes them to the STT, LLM and TTS providers.</desc>
  <defs><marker id="ah-sec" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="15" text-anchor="middle">
    <rect class="box" x="16" y="30" width="180" height="60" rx="10"/><text x="106" y="56">Secrets Manager</text>
    <rect class="box" x="246" y="30" width="180" height="60" rx="10"/><text x="336" y="56">Bootstrap</text>
    <rect class="box" x="476" y="30" width="180" height="60" rx="10"/><text x="566" y="56">Every service</text>
    <rect class="box" x="16" y="170" width="180" height="60" rx="10"/><text x="106" y="196">Credentials DB</text>
    <rect class="box hot" x="246" y="170" width="180" height="60" rx="10"/><text x="336" y="196">Credential service</text>
    <rect class="box" x="476" y="170" width="180" height="60" rx="10"/><text x="566" y="196">Agent worker</text>
    <rect class="box" x="706" y="170" width="180" height="60" rx="10"/><text x="796" y="196">STT, LLM, TTS</text>
  </g>
  <g font-size="13" class="small" text-anchor="middle">
    <text x="106" y="76">one platform secret</text>
    <text x="336" y="76">load, check, exec</text>
    <text x="566" y="76">env vars, PID 1</text>
    <text x="106" y="216">ciphertext only</text>
    <text x="336" y="216">the only decryptor</text>
    <text x="566" y="216">fetches per call</text>
    <text x="796" y="216">customer's keys</text>
  </g>
  <path class="arrow" d="M196 60 H242" marker-end="url(#ah-sec)"/>
  <path class="arrow" d="M426 60 H472" marker-end="url(#ah-sec)"/>
  <path class="arrow" d="M196 200 H242" marker-end="url(#ah-sec)"/>
  <path class="arrow" d="M426 200 H472" marker-end="url(#ah-sec)"/>
  <path class="arrow" d="M656 200 H702" marker-end="url(#ah-sec)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M336 90 V166" marker-end="url(#ah-sec)"/>
  <text x="346" y="133" font-size="13" class="small">encryption key</text>
  <text x="449" y="254" font-size="13" class="small" text-anchor="middle">Internal route, shared key</text>
</svg>
<figcaption>Platform secrets come in once at boot. Customer keys stay encrypted at rest and are decrypted only by the credential service, one call at a time.</figcaption>
</figure>

## Loading secrets at boot, and refusing bad ones

The platform's own secrets (the JWT signing key, the internal service key, the Fernet key, LiveKit's API key and secret) live in one AWS Secrets Manager secret ([Secrets Manager](https://docs.aws.amazon.com/secretsmanager/latest/userguide/intro.html)). Every container starts with a small **bootstrap** step. It loads that secret into environment variables, works out the service's database URL, checks the config, and then calls `exec` to replace itself with the real server.

For local dev, each of those settings has a hard-coded fallback so the stack boots with no setup. In production that is a disaster: a dev JWT key that is in the repo means anyone can forge a login. So when the environment says production, bootstrap refuses to start if any of them is missing or still equals its dev value. It prints the names of the bad keys, never the values, and exits.

Someone notices a boot crash within minutes. A service running on a known key can go unnoticed for months.

## The limits of log redaction

The logging setup has a processor that replaces values for keys like `password`, `token`, `api_key` and `authorization` with a placeholder. It checks only the **top level** of each log event, by exact key name. `log.info("x", api_key=k)` is redacted. `log.error("x", request={"headers": {"Authorization": k}})` is printed in full.

A fresh recursive version, run here:

```python
SECRET_KEYS = {"password", "secret", "token", "api_key", "authorization"}

def redact(value):
    if isinstance(value, dict):
        return {k: "***" if k.lower() in SECRET_KEYS else redact(v)
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value

print(redact({"call_id": "c1", "provider": {"name": "x", "api_key": "sk-123"},
              "headers": [{"Authorization": "Bearer abc"}]}))
```

```text
{'call_id': 'c1', 'provider': {'name': 'x', 'api_key': '***'}, 'headers': [{'Authorization': '***'}]}
```

Even this misses a key embedded in a URL or an exception message. Treat redaction as a safety net, and keep secrets out of log calls in the first place.

## Recording consent and failing safe

**Fail closed** means that when a check cannot be done, you pick the answer that does the least harm. For recording, that answer is "don't record". A fresh sketch:

```python
def should_record(fetch_config) -> bool:
    try:
        cfg = fetch_config()
    except Exception:
        return False                      # can't tell: don't record
    return cfg.get("recording_enabled") is True   # missing field: don't record

def down(): raise TimeoutError
print(should_record(down), should_record(lambda: {}), should_record(lambda: {"recording_enabled": True}))
```

```text
False False True
```

Config down, field missing, and explicitly on. Only the last one records.

:::warn Gotcha from the platform
The recording service does the opposite. If the assistant config call fails, it records. If the response has no recognizable recording field, it records. Its own docstring flags this as a choice to revisit. Assistants also have a `recording_consent_required` flag, which you can set in the console. It is stored, copied into assistant versions, and returned by the config API, and no service ever checks it. A customer who ticks that box gets no disclosure played and no change in behavior.
:::

## Transcripts, retention, and PII

The agent publishes every partial transcript as an event, and the recording service stores partials as well as finals. One sentence can become a dozen rows. Each org has a retention policy, 90 days by default. The retention sweep deletes the recording object from S3 and its database row. It never touches transcripts. So "delete after 90 days" is true for audio and false for text.

That matters because transcripts are where **PII** (personally identifiable information) piles up: names, addresses, card numbers read aloud, health details. Text is easier to search, copy, and leak than audio. If you keep only one thing, keep the final transcript, redact it, and delete it on the same clock as the audio.

:::try
Add `"cookie"` to `SECRET_KEYS` in the snippet, then log a dict with a `Set-Cookie` header nested two levels down. Predict whether it is redacted. (The check is an exact match on the lower-cased key.) What would you change so that partial matches like `x-api-key` are caught too?
:::

:::note What we did not test
We read the credential service, bootstrap, logging, config, and recording code. We did not run the credential service, fetch a real secret, or record a call. The two snippets above are ours and were run here. We did not check the platform's logs for leaked keys.
:::

:::say
Decrypt in one place, refuse to boot on dev secrets, redact recursively but log less, and when you can't tell whether to record, don't.
:::

:::check Why does bootstrap print the names of bad settings but not their values?
The values are secrets. A boot failure log goes to the same place as every other log, so printing them would leak the thing the check exists to protect.
:::

:::check Recording defaults to ON when the config service is down. Name two ways that hurts.
Calls for assistants with recording off get recorded anyway, which can break the customer's promise to callers or the law where they operate. And because the consent flag is never checked, no disclosure is played on those calls either.
:::

Next: [Testing what you can't call](lesson:voice-prod/testing-what-you-cant-call)
