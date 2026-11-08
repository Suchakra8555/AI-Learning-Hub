---
title: The lk CLI
summary: Install lk, learn the order in which it picks a server and credentials, save your server as a project, and tour the commands that work self-hosted, with real output from the lab and the Cloud-only commands marked.
time: 20 min
---

You saved your staging server with `lk project add --default`. You run `lk room delete demo`, and the room on staging is still there. The command went somewhere else, because a `LIVEKIT_URL` left in your shell beat the default project. `lk` is the fastest way to poke at a LiveKit server, but only once you know which server it is talking to. This lesson covers that first, then the commands.

The lab uses **`lk` v2.19.3** against livekit-server v1.13.11.

## Install

From the [CLI setup guide](https://docs.livekit.io/reference/developer-tools/livekit-cli/#setup):

```bash
brew install livekit-cli                       # macOS
curl -sSL https://get.livekit.io/cli | bash    # Linux
winget install LiveKit.LiveKitCLI              # Windows
```

There are also prebuilt binaries on the [GitHub releases page](https://github.com/livekit/livekit-cli/releases/latest). On the lab, the GitHub download failed, so we copied the `lk` binary out of the `livekit/livekit-cli:v2.19.3` Docker image instead. Any of these routes gives you the same single binary. `lk --version` prints `lk version 2.19.3`.

## What lk does when you run a command

`lk` is a client of the server API. For a command like `lk room list`, it signs a short-lived **JWT** (a signed JSON token) with your API secret, on your machine. Then it sends an HTTP POST to a **Twirp** endpoint. Twirp is an RPC framework where each method is a URL and the body is JSON ([room service API](https://docs.livekit.io/reference/other/roomservice-api/)). The server checks the signature with the same secret.

`lk token create` stops after the first step: it signs and prints a token, and no server is involved ([rooms reference](https://docs.livekit.io/reference/developer-tools/livekit-cli/rooms/#token-commands)).

<figure>
<svg viewBox="0 0 860 310" role="img" aria-labelledby="cli-t cli-d">
  <title id="cli-t">How lk picks credentials and calls the server</title>
  <desc id="cli-d">Five credential sources in priority order feed lk: the project or subdomain flag, flags or LIVEKIT environment variables, the dev flag, livekit.toml, and the default project. lk signs a JWT locally with the API secret, then sends an HTTP POST with a Bearer token to a Twirp endpoint on livekit-server port 7880, which checks the signature and returns JSON.</desc>
  <defs><marker id="cli-ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <text x="16" y="26" font-size="13" font-weight="700">Credentials: first match wins</text>
  <g font-size="13">
    <rect class="box" x="16" y="40" width="214" height="34" rx="8"/><text x="28" y="62">1  --project / --subdomain</text>
    <rect class="box hot" x="16" y="82" width="214" height="34" rx="8"/><text x="28" y="104">2  flags or LIVEKIT_* env</text>
    <rect class="box" x="16" y="124" width="214" height="34" rx="8"/><text x="28" y="146">3  --dev (devkey / secret)</text>
    <rect class="box" x="16" y="166" width="214" height="34" rx="8"/><text x="28" y="188">4  livekit.toml in this dir</text>
    <rect class="box" x="16" y="208" width="214" height="34" rx="8"/><text x="28" y="230">5  default project</text>
  </g>
  <g font-size="14" text-anchor="middle">
    <rect class="box hot" x="280" y="100" width="120" height="70" rx="10"/><text x="340" y="130">lk</text><text x="340" y="152" font-size="12" class="small">v2.19.3</text>
    <rect class="box" x="660" y="100" width="184" height="70" rx="10"/><text x="752" y="128">livekit-server</text><text x="752" y="150" font-size="12" class="small">:7880, checks signature</text>
    <rect class="box" x="250" y="236" width="300" height="56" rx="10"/><text x="400" y="259">JWT signed locally with the secret</text><text x="400" y="279" font-size="12" class="small">token create stops here: no server call</text>
  </g>
  <path class="arrow" d="M230 135 H276" marker-end="url(#cli-ah)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M340 170 V232" marker-start="url(#cli-ah)" marker-end="url(#cli-ah)"/>
  <path class="arrow" d="M400 124 H656" marker-end="url(#cli-ah)"/>
  <path class="arrow" d="M660 152 H404" marker-end="url(#cli-ah)"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="528" y="100">POST /twirp/livekit.RoomService/…</text>
    <text x="528" y="116">Authorization: Bearer &lt;JWT&gt;</text>
    <text x="528" y="172">JSON response</text>
  </g>
</svg>
<figcaption>Every server command signs a token locally and makes one HTTP call. The only network hop is the Twirp POST.</figcaption>
</figure>

## Which server, which key

The [rooms reference](https://docs.livekit.io/reference/developer-tools/livekit-cli/rooms/#credentials) gives the order. The CLI uses the first source it finds:

1. `--project NAME` or `--subdomain SUBDOMAIN`, which pick a saved project.
2. `--url`, `--api-key`, `--api-secret`, or the `LIVEKIT_URL`, `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` env vars.
3. `--dev`, which uses `devkey` and `secret` for a dev-mode server.
4. The project named in a `livekit.toml` in the current directory.
5. Your default project.

We checked this on the lab. `cli_tour.sh` saves the lab as the default project, but it has also sourced `lab.env`, which sets the three env vars. Every later command prints "Using url, api-key, api-secret from environment", so the env vars won (rule 2 beats rule 5). With the same saved project, `lk room list --dev` printed "Using dev credentials" and the lab answered with a 401, because it doesn't know the dev key.

A **project** in `lk` is just a name plus a URL, key and secret, stored in your local CLI config. `lk project` never creates anything on a server ([project management](https://docs.livekit.io/reference/developer-tools/livekit-cli/projects/)). The commands are `lk project add`, `list`, `set-default` and `remove`. The first project you add becomes the default.

## The tour, on the lab

`code/livekit/cli_tour.sh` runs the commands below against the lab. The key lines:

```bash
source "$(dirname "$0")/lab.env"
step() { printf '\n$ %s\n' "$*"; "$@"; }

step lk project add lab --url http://127.0.0.1:7880 --api-key "$LIVEKIT_API_KEY" --api-secret "$LIVEKIT_API_SECRET" --default
step lk token create --join --room demo --identity alice --valid-for 1h
step lk room create --empty-timeout 120 --departure-timeout 10 demo
step lk room list --curl

lk room join --identity bot --publish-demo demo >/tmp/lk-join.log 2>&1 &
sleep 4
step lk room participants list demo
step lk room send-data --room demo --topic chat '{"message":"hello from the cli"}'
step lk room participants update --room demo --permissions '{"can_publish": false, "can_subscribe": true}' bot
step lk room delete demo
```

Real output, trimmed. The full `enabledCodecs` list was PCMU, PCMA, opus, red, VP8, H264, VP9, AV1, H265 and rtx:

```text
$ lk project add lab --url http://127.0.0.1:7880 --api-key lab-key --api-secret lab-secret-... --default
Saved CLI config to [.../.livekit/cli-config.yaml]
│ * lab │            │ http://127.0.0.1:7880 │ lab-key │

$ lk token create --join --room demo --identity alice --valid-for 1h
Using url, api-key, api-secret from environment
valid for (mins): 60
Token grants:
{
  "identity": "alice",
  "name": "alice",
  "video": {
    "roomJoin": true,
    "room": "demo"
  }
}
...
$ lk room create --empty-timeout 120 --departure-timeout 10 demo
Using url, api-key, api-secret from environment
setting empty timeout: 120
setting departure timeout: 10
{
  "sid":  "RM_QNCfxnLMwUta",
  ...

$ lk room list --curl
Using url, api-key, api-secret from environment
curl -X POST \
	-H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \
	-H 'X-Livekit-Request-Id: fcd17f33-e2c0-4b55-adab-46519b697608' \
	-H 'Content-Type: application/json' \
	--data '{}' \
	http://127.0.0.1:7880/twirp/livekit.RoomService/ListRooms
│ RM_QNCfxnLMwUta │ demo │ 0            │ 0          │

$ lk room participants list demo
bot (ACTIVE)	 tracks: 1

$ lk room send-data --room demo --topic chat {"message":"hello from the cli"}
successfully sent data to room demo

$ lk room participants update --room demo --permissions {"can_publish": false, "can_subscribe": true} bot
updating participant...
{
  "room":  "demo",
  "identity":  "bot",
  "permission":  {
    "canSubscribe":  true,
    "canPublishData":  true
  }
}
participant updated.

$ lk room delete demo
deleted room demo
```

Some things to read in it:

- `--valid-for 1h` shows up as "valid for (mins): 60". The default lifetime is 5 minutes.
- `--curl` prints the exact request. Decode the middle part of that Bearer token and you get `{"iss":"lab-key","exp":1794151650,"nbf":1794130050,...,"video":{"roomList":true}}`. The CLI gave itself only the `roomList` grant, valid for 6 hours.
- `canPublish` is missing from the updated permission. It is false, and false fields are left out of the JSON.
- Name flags such as `--room` and `--identity` accept **templates**: `%t` becomes a UTC timestamp, `%x` random hex and `%U` the current user, so `--room "test-%t"` makes a fresh room each run ([rooms reference](https://docs.livekit.io/reference/developer-tools/livekit-cli/rooms/#credentials)).
- `lab.env` sets `LK_NO_SKILLS_PROMPT=1`. Without it, `lk` prints a tip banner that clutters scripted output.

## Every command group

From `lk --help` on v2.19.3 and the [CLI reference](https://docs.livekit.io/reference/developer-tools/livekit-cli/):

| Command | What it does | Self-hosted? |
|---|---|---|
| `lk project` | Save, list, pick and remove servers | Yes |
| `lk cloud` | Sign in to LiveKit Cloud and import a project | No |
| `lk app` | Create a frontend app from a template, with credentials filled in | Yes (not tested) |
| `lk token` | Sign access tokens | Yes |
| `lk room` | Create, list, update, delete, join, `mute-track`, `update-subscriptions`, `send-data` | Yes |
| `lk room participants` | `list`, `get`, `update`, `remove` | Yes |
| `lk room participants move` / `forward` | Move or forward a participant to another room | No: the server API returns "not implemented" self-hosted |
| `lk dispatch` | Send an agent to a room, list and delete dispatches | Yes |
| `lk egress` | Start, list, stop recordings and streams | Yes, with the egress service running |
| `lk ingress` | Create RTMP, WHIP and URL inputs | Yes, with the ingress service running |
| `lk sip` | Trunks, dispatch rules, SIP participants | Yes, with the SIP service running |
| `lk number` | LiveKit Phone Numbers | No: use a SIP trunk from any provider |
| `lk perf` | `load-test` and `agent-load-test` | Yes |
| `lk agent init` / `dev` / `start` / `console` | Scaffold and run an agent locally | Yes |
| `lk agent debugger` | Drive a local agent turn by turn | Yes in text mode. `--audio` uses LiveKit Inference TTS, billed to a Cloud project |
| `lk agent simulate` | Judged simulations | No |
| `lk agent create`, `deploy`, `promote`, `status`, `update`, `restart`, `rollback`, `logs`, `delete`, `versions`, `list`, `secrets`, `update-secrets`, `private-link`, `config`, `dockerfile` | Managed agent hosting | No: run agent servers yourself in Docker or Kubernetes |
| `lk docs`, `lk skills` | Search the docs, install coding-agent skills | Yes, no server needed |

`lk --help` groups the hosting commands under "AGENT DEPLOYMENT (LIVEKIT CLOUD)". `lk agent dockerfile` only writes a `Dockerfile` and `.dockerignore`, so you may find it useful self-hosted, but we didn't try it.

:::note Self-hosted vs Cloud
Everything that touches rooms, tokens, dispatch, egress, ingress, SIP and load tests works against your own server. The Cloud-only commands are `lk cloud`, `lk number`, `lk agent simulate`, `lk agent debugger --audio`, participant `move`/`forward`, and the whole agent deployment group. The self-hosted replacement for `lk agent create`/`deploy` is your own container image and orchestrator, covered in the production lessons.
:::

:::tip CLI
`lk project add <name> --url <url> --api-key <key> --api-secret <secret> --default`, `lk project list`, `lk project set-default <name>`, `lk token create --join --room <room> --identity <id> --valid-for 1h`, `lk room list --curl`, `lk room join --identity bot --publish-demo <room>`. Add `--project <name>` to any command when you mean a specific server.
:::

:::try
Run `source code/livekit/lab.env`, then `lk room list`, and note the "from environment" line. Run `unset LIVEKIT_URL LIVEKIT_API_KEY LIVEKIT_API_SECRET` and run it again. Which source did it use the second time? Then run `lk token create --join --room "t-%t" --identity me --valid-for 2m --json` and paste the token into a JWT decoder to find `exp`.
:::

:::warn Env vars beat your default project
`LIVEKIT_URL` and friends rank above the default project, and they tend to linger in shells, `.env` files and CI. A destructive command such as `lk room delete` then hits whatever server they name. Watch for the "Using url, api-key, api-secret from environment" line, or pass `--project <name>` in scripts so the target is explicit.
:::

:::note What we did not test
We didn't install `lk` with brew, the curl script or winget. We didn't try `livekit.toml` or `--subdomain` resolution, `lk app`, `lk agent dockerfile`, or any Cloud-only command. The `--dev` check was a single `lk room list --dev` against the lab.
:::

:::say
`lk` signs a token locally and makes one Twirp POST per command, so the only thing to get right is which URL and key it picked, and env vars win over your default project.
:::

:::check You set a default project, but `lk room list` prints "Using url, api-key, api-secret from environment". Why, and how do you force the project?
The `LIVEKIT_*` env vars rank above the default project. Pass `--project <name>`, which ranks first, or unset the env vars.
:::

:::check Does `lk token create` need the server to be running?
No. It signs the JWT locally with the API secret. The server only checks the signature later, when a client connects or calls the API with that token.
:::

Next: [Rooms, participants and tracks](lesson:livekit/rooms-participants-tracks)
