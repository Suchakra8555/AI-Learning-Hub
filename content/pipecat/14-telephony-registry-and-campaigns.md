---
title: Telephony: a registry, a spec and a campaign engine
summary: Dograh supports nine phone integrations with one provider interface. Adding a carrier touches its own folder plus two lines. This lesson shows the spec, the concurrency slots and how campaigns dial.
time: 25 min
---

A voice platform lives or dies on phone integrations. Each carrier has its own call API, webhook format, audio format and number provisioning. Dograh handles nine (`ari`, `cloudonix`, `exotel`, `plivo`, `telnyx`, `twilio`, `vobiz`, `vonage`, `whatsapp`) without `if provider == "twilio"` scattered through the call path.

## The provider interface

`api/services/telephony/base.py:130` defines `TelephonyProvider(ABC)`. A provider must implement, among others: `initiate_call`, `get_call_status`, `verify_webhook_signature`, `get_webhook_response`, `parse_status_callback`, `handle_websocket`, `can_handle_webhook`, `parse_inbound_webhook`, `start_inbound_stream`, `transfer_call`, `supports_transfers` and `get_call_cost`. A few are optional: `configure_inbound`, `list_provider_phone_numbers`, `select_trunk`.

On top of that is a **`ProviderSpec`**, a frozen dataclass in `registry.py` (lines 246 to 373). It holds everything the rest of the system needs to know about a provider *without importing it*:

| Field | Meaning |
|---|---|
| `name`, `provider_cls` | The id and the class |
| `config_loader`, `config_request_cls` | How to read and validate saved credentials |
| `transport_factory` | An async function that builds the Pipecat transport |
| `transport_sample_rate` | 8,000 for most carriers |
| `ui_metadata` | Field labels and types, so the UI draws the config form with no per-carrier React |
| `account_id_credential_field` | For inbound routing by account |
| `supports_outbound`, `requires_caller_id`, `requires_e164_destinations` | Capability flags |
| `connectivity` | `"api"` or `"sip"` |
| `trunk_settings_cls`, `apply_trunk_on_save`, `remove_trunk_on_delete` | SIP trunk hooks |

Registration happens at import time with `register(SPEC)`. Provider routes are mounted by importing `providers.<name>.routes` and treating a missing module as "no routes".

## Adding a provider

`api/services/telephony/providers/AGENTS.md` says a new carrier touches exactly two lines outside its own folder:

1. Create `providers/<name>/` with `__init__.py` (builds and registers the `ProviderSpec`), `config.py`, `provider.py`, `transport.py`, and optionally `serializers.py`, `routes.py` and `strategies.py`.
2. Add `<name>` to the import list in `providers/__init__.py`.
3. Add its request class to a `Union` in `api/schemas/telephony_config.py`.

Editing `factory.py`, `audio_config.py`, `run_pipeline.py` or `routes/telephony.py` is called "a smell" in that file. The pipeline code never branches on a carrier name (`run_pipeline.py:363`). It looks up the spec and calls its `transport_factory`.

A transport factory is short. For Twilio (`providers/twilio/transport.py:92`) it builds a `TwilioFrameSerializer` with the transfer and hang-up strategies, wraps it in a `FastAPIWebsocketTransport`, and passes the ambient-noise mixer. That is the serializer pattern from [lesson 6](lesson:pipecat/transports-and-phone-audio).

## Concurrency

`services/call_concurrency/` gives each organization **slots**. `acquire_org_slot(org, source, timeout)` runs before a call starts, and returns an error (HTTP 429) at the limit. The default is 10 concurrent calls per organization (`constants.py:214`), overridable. Slots live in Redis, so they work across API processes. The signaling code and the carrier code both bind a slot to a run and release it on any exit path.

## Campaigns

A **campaign** dials a list of contacts with one agent. The pieces (`services/campaign/`):

- **Orchestrator** (a singleton process): listens to Redis events, schedules batches, marks campaigns complete.
- **Dispatcher**: enforces rate and concurrency limits, then asks the carrier to dial.
- **Retries**: redial on busy, no answer or voicemail, with settings per campaign.
- **Circuit breaker** (`circuit_breaker.py`): a Redis Lua script counts recent failures. After 20 recent failures (`MAX_RECENT_FAILURES`) a campaign pauses, so a broken carrier credential does not burn through a contact list.
- **Sources**: CSV or Google Sheets, synced by an ARQ job.
- **Traffic splits**: send a share of calls to different versions of the workflow, for A/B tests.

The changelog says a recent refactor of the dispatcher aimed at "higher concurrency" (v1.47.0). We did not read the dispatcher's internals.

## Asterisk

Asterisk is an open-source phone system. Companies that run their own PBX use it. Dograh's `ari_manager.py` (1,800 lines, a standalone process) listens for Asterisk's Stasis events over ARI, its control API, and connects Asterisk's `chan_websocket` external media to the endpoint `/ws/ari` with the subprotocol `media`. It is behind `ENABLE_ARI_STASIS`. We did not read its internals. The Pipecat side is the Asterisk serializer from the previous lessons.

## Security notes worth learning from

- Media WebSockets can require an **HMAC token** in the URL path (`TELEPHONY_WS_TOKEN_SECRET`, `ws_auth.py`). The code says in a `TODO(security)` that the token is stateless and replayable, and enforcement is off by default. That is honest and a real gap. See the [socket auth lesson](lesson:voice-prod/who-is-on-this-socket) for why it matters.
- Inbound webhooks check carrier signatures (`verify_webhook_signature`). Behind nginx that needs `FORWARDED_ALLOW_IPS="*"`, or the signed URL no longer matches. The compose file explains it.

:::try
Read `providers/twilio/__init__.py` in the Dograh repo. It is the smallest complete example. List the fields of its `ProviderSpec`, then write down which of them a SIP-only carrier would set differently.
:::

:::check Why is ProviderSpec a separate object from the provider class?
The rest of the system needs to know a provider's capabilities, sample rate and form fields without importing or instantiating the class. A frozen spec registered at import time answers that cheaply.
:::

:::check What problem does the campaign circuit breaker solve?
A bad carrier credential or outage makes every dial fail. Without it, a campaign would burn through its whole contact list. After 20 recent failures it pauses and waits for a human.
:::
