---
title: One interface, many carriers
summary: Every carrier and every AI provider speaks a slightly different dialect. Learn where to put the seam so adding one is a new file, and how a parity check catches what the type checker can't.
time: 20 min
---

The first carrier works. A customer asks for a second. You copy the WebSocket handler, change the JSON field names, and ship. By the third carrier you have three handlers that each fix barge-in a little differently, and a bug fixed in one is still live in the other two.

The fix is to decide which parts differ per carrier and which don't. Then put an interface on the line between them.

## What actually differs

Here are three carriers the platform supports, as their docs and our code describe them:

| | Twilio | Vobiz | Ozonetel |
|---|---|---|---|
| Audio on the wire | base64 µ-law, 8 kHz | base64 µ-law, 8 kHz | PCM16 as a JSON list of ints, 8 kHz |
| Frame size | 20 ms | 20 ms | 10 ms (80 samples) |
| Stream id on every reply | yes | yes | yes, plus a fresh sequence id per packet |
| Clear buffered audio | `clear` | `clearAudio` | `clearBuffer` command |
| End of call | sends `stop` | **never sends `stop`**, the socket just closes | sends `stop` |
| Webhook signing | signed | signed only if the URL carries credentials | not signed |

Sources: [Twilio Media Streams](https://www.twilio.com/docs/voice/media-streams/websocket-messages), [Vobiz stream events](https://www.vobiz.ai/docs/xml/stream/stream-events). Ozonetel's details come from its streaming SDK docs as our code records them. Ozonetel also sends one 16 kHz calibration packet first, which you must skip.

Everything else is the same for all three: the ticket check, joining the LiveKit room, barge-in timing, hang-up handling, logging. That's most of the code.

## Two seams with different lifetimes

The platform splits each carrier into two interfaces because they live for different lengths of time.

The **stream protocol** lives for one WebSocket. It turns each wire message into one of five neutral events (start, caller audio, keypad digit, playback mark, stop) and turns one outgoing PCM16 frame into a wire message. It also says what message clears the carrier's buffer and how to hang up. It declares its sample rate and frame length, and the frame size in bytes follows from those. It holds state, since Twilio wants the stream id from `start` echoed on every message.

The **provider control** has no state and handles the REST side: verify a webhook, place an outbound call, hang up, map the carrier's call-status names to ours, and write the XML that tells the carrier to open a stream.

The media session, room bridge and routers only see these two interfaces. Adding a carrier means one new module and one line in each of two registry dicts keyed by carrier name. An unknown name gets a 400 error that names the carrier.

## A small version you can run

The platform uses abstract base classes. Python's **`typing.Protocol`** gets the same seam without inheritance: any class with the right methods fits, and a type checker verifies it ([Python docs](https://docs.python.org/3/library/typing.html#typing.Protocol)). This is our own toy, not platform code:

```python
import base64
from typing import Protocol

class Carrier(Protocol):
    frame_ms: int
    def parse(self, msg: dict) -> bytes: ...      # wire message -> audio bytes
    def clear(self) -> dict | None: ...           # barge-in command, if any

class JsonMulaw:                                  # base64 mu-law, 20 ms frames
    frame_ms = 20
    def parse(self, msg): return base64.b64decode(msg["payload"])
    def clear(self): return {"event": "clear"}

class IntArrayPcm:                                # PCM16 as a list of ints, 10 ms
    frame_ms = 10
    def parse(self, msg): return b"".join(s.to_bytes(2, "little", signed=True) for s in msg["samples"])
    def clear(self): return None

REGISTRY: dict[str, type[Carrier]] = {"json-mulaw": JsonMulaw, "int-array": IntArrayPcm}

samples = {"json-mulaw": {"payload": base64.b64encode(bytes(160)).decode()},
           "int-array": {"samples": [0] * 80}}
for name, cls in REGISTRY.items():
    c = cls()
    out_bytes = 8000 * c.frame_ms // 1000 * 2    # PCM16 bytes per outgoing frame
    print(f"{name:10} in={len(c.parse(samples[name]))}B  frame_out={out_bytes}B  clear={c.clear()}")
```

Save it as a file and run it with `python3`. It feeds each carrier one sample message:

```text
json-mulaw in=160B  frame_out=320B  clear={'event': 'clear'}
int-array  in=160B  frame_out=160B  clear=None
```

Both take in 160 bytes. Those are µ-law bytes in one case and PCM16 bytes in the other, which is why `parse` should always return PCM16 in a real system. The outgoing frame differs too. So the chunker from [lesson 2](lesson:voice-prod/phone-audio-is-different) must ask the carrier for its frame size and never assume 20 ms.

## The same seam for AI providers

The agent side has the same problem with STT, LLM and TTS vendors. The platform keeps a **provider catalog** in the assistant config service, listing what a customer may pick and with which settings. A **provider registry** in the agent worker maps each catalog key to a function that builds the matching LiveKit plugin. The catalog uses one word for each setting across vendors (`voice`, `language`, `model`). Each builder renames it to whatever the plugin wants, such as `voice_id` or `speaker`.

Two lists that must agree will drift apart. So a **parity check** script runs three tests and exits non-zero on any mismatch, which makes it a CI step:

1. Every catalog key has a registry builder, and the other way around.
2. Every keyword argument a builder passes is accepted by the installed plugin's `__init__`. It swaps the plugin class for a stub that records its kwargs, then binds those against the real signature with `inspect.signature(...).bind_partial`. Nothing touches the network.
3. For each STT model, the catalog's turn-taking capabilities match what the registry reports.

:::warn Gotcha from the platform
Vobiz never sends `stop`. A handler written against Twilio waits for `stop` to end the call, and on Vobiz it waits forever, or until the 15 s idle timeout. The platform treats a closed socket as a hang-up for every carrier. Two other details are still marked "verify on a live call" in the code: the exact shape of Vobiz's extra headers and Ozonetel's outbound API reply. Both are parsed loosely until someone checks.
:::

:::try
Add a third class to the toy, `JsonPcm16k`, for a made-up carrier that sends base64 PCM16 at 16 kHz in 20 ms frames. What should `frame_out` be? (Hint: the toy hard-codes 8000.) Then decide what the bridge would have to do that it never does today.
:::

:::note What we did not test
We ran the toy above with Python 3.10. We did not run the platform's parity script, which needs the agent worker's installed plugins. The carrier quirks come from the carriers' public docs and the platform's code. We did not place live calls on Ozonetel.
:::

:::say
Put everything that differs per carrier behind one small interface, and add a script that fails the build when two lists that must match stop matching.
:::

:::check Why does the platform split each carrier into a stream protocol and a provider control?
They live for different lengths of time. The stream protocol holds state for one WebSocket, like the stream id. The provider control is stateless and handles webhooks and REST calls before and after the socket exists.
:::

:::check A catalog key has no registry builder. When does the customer find out?
Without the parity check, only when a real call starts and the agent raises an error. The config service accepts the assistant, because the key is in its catalog. The parity check moves that failure to CI.
:::

Next: [Who is on this socket?](lesson:voice-prod/who-is-on-this-socket)
