---
title: Who is on this socket?
summary: Anyone can open a WebSocket to a public URL. Learn how the platform tells a real carrier call from a stranger, with one-time tickets, keys in the webhook URL, and a shared key for internal calls.
time: 20 min
---

The media bridge listens on a public URL. A carrier connects, sends a `start` message, and streams a caller's audio. A stranger can connect to the same URL and send a `start` message too. If the bridge believes it, the stranger is in a room with your agent, running up your STT and LLM bill. A WebSocket has no login form. You need some other way to know who is on the other end.

The platform answers three separate questions:

| Question | Answer used |
|---|---|
| Is this webhook really from the carrier? | A secret key in the webhook URL, or the carrier's signature |
| Is this socket the call we set up a moment ago? | A one-time ticket |
| Is this HTTP call from one of our own services? | A shared internal key, which the gateway never lets through |

## One-time tickets

A **one-time ticket** is a random token that works once and only for a short time. It ties a socket to a call the platform already knows about.

<figure>
<svg viewBox="0 0 760 450" role="img" aria-labelledby="t-ticket d-ticket">
  <title id="t-ticket">How a stream ticket is issued and redeemed</title>
  <desc id="d-ticket">The carrier sends a webhook. The bridge stores a ticket in Redis with a time limit and returns stream instructions holding it. The carrier opens a WebSocket and sends start with the ticket. The bridge runs GETDEL in Redis. If call data comes back the bridge joins the room. If nothing comes back it closes the socket with code 1008.</desc>
  <defs><marker id="ah-ticket" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="15" text-anchor="middle">
    <rect class="box" x="40" y="16" width="140" height="44" rx="10"/><text x="110" y="43">Carrier</text>
    <rect class="box hot" x="310" y="16" width="140" height="44" rx="10"/><text x="380" y="43">Media bridge</text>
    <rect class="box" x="580" y="16" width="140" height="44" rx="10"/><text x="650" y="43">Redis</text>
  </g>
  <path class="arrow" stroke-dasharray="4 4" d="M110 60 V420"/>
  <path class="arrow" stroke-dasharray="4 4" d="M380 60 V350"/>
  <path class="arrow" stroke-dasharray="4 4" d="M650 60 V420"/>
  <g font-size="13" text-anchor="middle">
    <text x="245" y="94">1. webhook: call coming (key in URL)</text>
    <text x="515" y="134">2. SET ticket, expires in 60 s</text>
    <text x="245" y="174">3. stream instructions + ticket</text>
    <text x="245" y="214">4. open WebSocket</text>
    <text x="245" y="254">5. start message + ticket</text>
    <text x="515" y="294">6. GETDEL ticket</text>
    <text x="515" y="334">7. call data, or nil</text>
  </g>
  <path class="arrow" d="M110 102 H374" marker-end="url(#ah-ticket)"/>
  <path class="arrow" d="M380 142 H644" marker-end="url(#ah-ticket)"/>
  <path class="arrow" d="M380 182 H116" marker-end="url(#ah-ticket)"/>
  <path class="arrow" d="M110 222 H374" marker-end="url(#ah-ticket)"/>
  <path class="arrow" d="M110 262 H374" marker-end="url(#ah-ticket)"/>
  <path class="arrow" d="M380 302 H644" marker-end="url(#ah-ticket)"/>
  <path class="arrow" d="M650 342 H386" marker-end="url(#ah-ticket)"/>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="220" y="370" width="150" height="44" rx="10"/><text x="295" y="397">valid: join room</text>
    <rect class="box hot" x="390" y="370" width="150" height="44" rx="10"/><text x="465" y="397">bad: close 1008</text>
  </g>
</svg>
<figcaption>The ticket travels out in the carrier's stream instructions and comes back in the socket's first message. GETDEL makes sure it only works once.</figcaption>
</figure>

When a carrier webhook arrives, the bridge looks up the number, creates a queued Call row, and stores a ticket in Redis with a time limit: 60 s for inbound calls and 180 s for outbound calls, since an outbound call has to ring first. The ticket goes into the stream XML the bridge sends back. When the carrier opens the socket, its `start` message carries the ticket back.

The bridge redeems it with Redis **GETDEL**, which returns a key's value and deletes the key in one command ([Redis docs](https://redis.io/docs/latest/commands/getdel/), available since Redis 6.2). Read and delete happen together, so a captured ticket can't be replayed. If two sockets race with the same ticket, only one gets the data.

The bridge checks more than "is the ticket there". The ticket must belong to the same carrier as the socket's route. For outbound calls, the carrier's call id must match too. All of this happens before anything touches LiveKit. If the `start` message doesn't arrive within 10 s, or the ticket fails any check, the bridge closes the socket with code **1008**. RFC 6455 defines 1008 as an endpoint "terminating the connection because it has received a message that violates its policy" ([RFC 6455, section 7.4.1](https://www.rfc-editor.org/rfc/rfc6455.html#section-7.4.1)).

## A key in the webhook URL

Not every carrier signs every webhook. So the platform puts a secret in the webhook URL path. It is derived with **HMAC** from the account's carrier auth token. HMAC is a keyed hash: only someone holding the key can produce the right output. On each webhook the bridge derives the value again and compares. If the auth token is rotated, the URL changes with it.

URLs end up in access logs, so a log filter replaces the key with `[REDACTED]`. The compare uses `hmac.compare_digest` instead of `==`.

A plain string compare stops at the first wrong character. A guess with more correct leading characters takes slightly longer to reject. Someone who can measure that difference can find the secret one character at a time. This is a **timing attack**. Python's docs say `compare_digest` avoids "content-based short circuiting behaviour, making it appropriate for cryptography" ([hmac docs](https://docs.python.org/3/library/hmac.html#hmac.compare_digest)).

## The code

`code/voice-prod/stream_ticket.py` uses a dict in place of Redis and counts the steps a plain compare takes:

```python
def redeem(ticket):
    entry = store.pop(ticket, None)          # GETDEL: read and delete in one step
    if entry is None or time.monotonic() > entry[1]:
        return None
    return entry[0]

def check_url_token(org_id, given):
    return hmac.compare_digest(url_token(org_id), given)
```

```text
first use : call-42
replay    : None -> close socket with 1008 (policy violation)
expired   : None
url token ok : True | wrong org: False
guess with  0 right chars: plain compare did  1 steps
guess with  8 right chars: plain compare did  9 steps
guess with 24 right chars: plain compare did 25 steps
```

The step count grows with every right character, and an attacker who can time it learns how many leading characters are right.

:::try
Change `store.pop(ticket, None)` to `store.get(ticket)` and run it again. Predict the `replay` line first. (The "close socket with 1008" text is hard-coded in the print, so read only the value before it.)
:::

## Service to service: the shared internal key

Services call each other over HTTP on `/internal/*` routes. Each request carries one shared key in a header. The API gateway, the only public entry point, enforces two rules. It drops that header from every client request, so a browser can't forge it. It also refuses any path with a segment called `internal`, and any `.`, `..` or empty segment that could be rewritten into one.

That works, but one key for every service has costs. If any one service leaks the key, every internal route is open. Logs can't tell which service called. Rotating it means restarting everything at once.

:::warn Gotcha from the platform
The webhook keys use `compare_digest`, but the internal key is checked with plain `!=`. Over a network the timing difference is small and noisy, but the fix is one line, so there's no reason to leave it.
:::

## LiveKit webhooks

LiveKit tells call orchestration when a room starts, a participant joins, a track is published, and the room finishes. LiveKit's docs say these requests carry "an `Authorization` header containing a signed JWT token", and that "the token includes a sha256 hash of the payload" ([LiveKit webhooks](https://docs.livekit.io/home/server/webhooks/)). The server SDK's webhook receiver checks both, so it needs the raw body before any JSON parsing. The platform verifies with the LiveKit API key and secret and returns 401 on failure.

On a self-hosted server, webhooks only fire when the server config has a `webhook` section. When the platform's config lacked it, no Call row was ever created, and the agent exited with "no call row for room".

:::note What we did not test
We read the bridge, gateway and webhook code. We did not attack a live socket, measure a timing leak over a real network, or confirm how each carrier passes the ticket back on a live call. The script shows the step count, not a measured time.
:::

## The rule

Every door into the system needs its own proof: a ticket for sockets, a signature or URL key for webhooks, a header key for internal calls. Make tickets single-use and short-lived. Compare every secret with `compare_digest`.

:::say
A WebSocket has no login, so the first message has to prove it belongs to a call you set up, and only once.
:::

:::check Why GETDEL and not GET followed by DEL?
Two separate commands leave a gap. Two sockets with the same ticket could both GET it before either DELs it. GETDEL reads and deletes in one step, so only one can win.
:::

:::check The gateway strips the internal-key header. Why does it also refuse paths with an `internal` segment?
Defense in depth. If a service ever trusted the path alone, or the header check had a bug, the public gateway still would never forward a request to an internal route.
:::

Next: [Never block the audio loop](lesson:voice-prod/never-block-the-audio-loop)
