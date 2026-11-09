---
title: Scaling and load
summary: How several LiveKit nodes share work through Redis, how rooms are placed and drained, what the published benchmarks say, how to load-test your own server with lk perf, and how to size and scale the agent servers that do the heavy work.
time: 25 min
---

One node handles your pilot. Then sales signs a customer with 300 calls at once, and you have to answer two questions before the launch: how many calls fit on one node, and what happens when you add a second? This lesson covers how LiveKit spreads rooms across nodes, how to measure a node yourself, and how to size the agent servers, which for a voice agent usually run out of CPU long before the SFU does.

## Distributed mode

Set `redis.address` and the server switches to **distributed mode**. Redis holds room data and acts as a message bus, and each node reports its load there, so every node can see the whole cluster ([distributed](https://docs.livekit.io/transport/self-hosting/distributed)). The lab confirmed it: with a `redis` block, the server runs distributed even on one machine.

Three rules follow:

- A room lives on one node. The node that gets the create request picks an available node to host it. A self-hosted room tops out at about 3,000 participants ([self-hosting overview](https://docs.livekit.io/transport/self-hosting)). A voice call has two or three, so for you the limit is rooms per node, not people per room.
- Signaling is proxied. A client's WebSocket can land on any node. That node bridges messages to the node that hosts the room. This is why any node can answer any API call.
- Nodes drain on shutdown. On `SIGTERM`, `SIGINT` or `SIGQUIT` with participants connected, a node keeps its rooms running and accepts new participants into them, but refuses new rooms. It exits when the last participant leaves. That is why the Helm chart waits up to 5 hours.

For several data centers, the **region-aware node selector** picks a node for a new room. Geo DNS sends the user to the nearest load balancer. LiveKit then picks at random among nodes in the closest region whose load is below `sysload_limit`:

```yaml
node_selector:
  kind: regionaware
  sysload_limit: 0.5
  regions:
    - name: us-west-2
      lat: 37.64046607830567
      lon: -120.88026233189062
    - name: us-east
      lat: 40.68914362140307
      lon: -74.04445748616385
```

<figure>
<svg viewBox="0 0 880 350" role="img" aria-labelledby="t-sc-multi d-sc-multi">
  <title id="t-sc-multi">Multi-node LiveKit with Redis and region-aware routing</title>
  <desc id="d-sc-multi">Geo DNS sends a user to the load balancer in the nearest region, us-west-2 or us-east. Each region has two LiveKit nodes. In us-west-2, node A is below sysload_limit and gets the new room, while node B is over the limit and is skipped. All four nodes report their load to one shared Redis, which also carries messages between nodes.</desc>
  <defs><marker id="sc-ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path class="ah" d="M0 0 L10 5 L0 10 z"/></marker></defs>
  <g font-size="14" text-anchor="middle">
    <rect class="box" x="340" y="16" width="200" height="50" rx="10"/><text x="440" y="38">Geo or latency DNS</text><text x="440" y="56" font-size="12" class="small">nearest load balancer</text>
    <rect class="box" x="30" y="130" width="130" height="50" rx="10"/><text x="95" y="160">LB us-west-2</text>
    <rect class="box hot" x="200" y="100" width="200" height="56" rx="10"/><text x="300" y="124">Node A</text><text x="300" y="144" font-size="12" class="small">load 0.31, gets the room</text>
    <rect class="box" x="200" y="176" width="200" height="56" rx="10"/><text x="300" y="200">Node B</text><text x="300" y="220" font-size="12" class="small">load 0.62, skipped</text>
    <rect class="box" x="480" y="130" width="130" height="50" rx="10"/><text x="545" y="160">LB us-east</text>
    <rect class="box" x="650" y="100" width="200" height="56" rx="10"/><text x="750" y="124">Node C</text><text x="750" y="144" font-size="12" class="small">its own rooms</text>
    <rect class="box" x="650" y="176" width="200" height="56" rx="10"/><text x="750" y="200">Node D</text><text x="750" y="220" font-size="12" class="small">its own rooms</text>
    <rect class="box" x="320" y="280" width="240" height="56" rx="10"/><text x="440" y="304">Redis</text><text x="440" y="324" font-size="12" class="small">node stats, rooms, message bus</text>
  </g>
  <path class="arrow" stroke-dasharray="4 6" d="M440 76 V262"/>
  <path class="arrow" d="M380 66 L120 126" marker-end="url(#sc-ah)"/>
  <path class="arrow" d="M500 66 L545 126" marker-end="url(#sc-ah)"/>
  <path class="arrow" d="M160 150 L196 132" marker-end="url(#sc-ah)"/>
  <path class="arrow" d="M610 150 L646 132" marker-end="url(#sc-ah)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M300 232 L380 276" marker-end="url(#sc-ah)"/>
  <path class="arrow" stroke-dasharray="5 5" d="M750 232 L520 276" marker-end="url(#sc-ah)"/>
  <g font-size="12" class="small" text-anchor="middle">
    <text x="95" y="100">us-west-2</text><text x="545" y="100">us-east</text>
    <text x="190" y="270">load reports</text><text x="690" y="270">load reports</text>
  </g>
</svg>
<figcaption>With sysload_limit 0.5, node B is skipped. The new room goes to node A and stays there for its whole life.</figcaption>
</figure>

## What the benchmarks say

LiveKit ran its benchmarks on a 16-core `c2-standard-16` on Google Cloud, with one room per test ([benchmarks](https://docs.livekit.io/transport/self-hosting/benchmark)):

| Use case | Pubs | Subs | Bytes/s in/out | CPU |
| --- | --- | --- | --- | --- |
| Large audio room | 10 | 3000 | 7.3 kBps / 23 MBps | 80% |
| Large meeting (720p video) | 150 | 150 | 50 MBps / 93 MBps | 85% |
| Livestreaming (720p video) | 1 | 3000 | 233 kBps / 531 MBps | 92% |

The audio test used an average bitrate of 3 kbps. The command printed under that table says `--subscribers 1000`, not 3000, so one of the two is out of date. These are big single rooms. Thousands of two-person calls are a different load, so test your own shape.

## Load-test your own server

`code/livekit/load_test.sh`:

```bash
ulimit -n 65535 2>/dev/null || true      # the docs ask for this on the machine running the test
lk perf load-test --room load-test --audio-publishers 5 --subscribers 40 --duration 20s
```

Real output, `out/load_test.txt`, with the 200 per-track rows and most subscriber rows cut:

```text
Using url, api-key, api-secret from environment
Starting load test with 5 audio publishers, 40 subscribers, room: load-test
publishing audio track - aqzdg_pub_0
...
Finished connecting to room, waiting 20s
...
Subscriber summaries:
┌────────┬─────────┬────────────────────────┬─────────────────┬───────┐
│ Tester │ Tracks  │ Bitrate                │ Total Pkt. Loss │ Error │
├────────┼─────────┼────────────────────────┼─────────────────┼───────┤
│ Sub 10 │ 5/5     │ 101.8kbps              │ 0 (0%)          │ -     │
...
│ Total  │ 200/200 │ 3.5mbps (87.3kbps avg) │ 0 (0%)          │ 0     │
└────────┴─────────┴────────────────────────┴─────────────────┴───────┘
```

And `out/load_stats.txt`, from `docker stats` during the test:

```text
lab-livekit-1 cpu=88.01% mem=169.6MiB / 15.31GiB
```

All 200 subscriptions (40 × 5) came up. Each subscriber got about 100 kbps, around 20 kbps per track in the per-track rows, with no loss. The server used 88% of **one** core, since `docker stats` counts per core and the machine has 12, and 170 MiB of memory.

That result understates what a real node can do. The load generator ran on the same machine and competed with the server for CPU. The lab's `rtc` range is 50000 to 50200, and each participant uses two ports, so the lab config can't hold much more than 100 participants whatever the CPU. And the docs ask you to run the tester on a machine with plenty of CPU and bandwidth, or on several machines. For a real number, put the server alone on the instance type you will deploy and drive it from elsewhere.

`lk perf agent-load-test --rooms 20 --agent-name <name> --duration 10m` tests the other side. It opens rooms, dispatches your agent, and plays the agent's speech back to it ([load testing](https://docs.livekit.io/reference/developer-tools/livekit-cli/perf)). Cloud caps `load-test` at 50 of each participant type. Your own server has no cap.

## Sizing agent servers

For a voice agent, the agent servers usually hit their limit first. The docs suggest 4 cores and 8 GB per agent server, good for 10 to 25 jobs. In LiveKit's own test, 30 agents running Silero VAD on one 4-core, 8 GB machine peaked at about 3.8 cores and 2.8 GB ([self-hosted deployments](https://docs.livekit.io/deploy/custom/deployments)).

- Availability: an agent server stops taking jobs when `load_fnc` (CPU by default) passes `load_threshold`. In the installed `livekit-agents` 1.8.11, that is 0.7 in production and infinite in dev mode. Autoscale lower, at 0.5, so new servers are up before old ones refuse work.
- Dispatch: the server hands each job to one agent server, round-robin. If that server doesn't accept in time, the job goes to another.
- Rollout: on `SIGTERM` an agent server takes no new jobs and lets running ones finish. Give it a grace period of 10 minutes or more. The package's own `drain_timeout` default is 3600 s.
- Crashes: a crashed job doesn't affect the others, but if the agent server process crashes, all of its jobs die with it.
- Health: the server answers 200 on `/` of port 8081 in production when it is connected, and 503 when it isn't ([health check](https://docs.livekit.io/agents/server/options#health-check-endpoint)).
- Warm processes: `num_idle_processes` keeps processes loaded and ready. The docs give the Python default as `math.ceil(cpu_count)`, and on the 12-core lab machine the installed package showed 12.

:::note Self-hosted vs Cloud
Cloud runs a global mesh, so a room isn't bound to one node, and it hosts and autoscales agents for you. Self-hosted, a room lives on one node, you scale nodes through Redis, and you run agent servers in your own Docker or Kubernetes with the autoscaling rules above.
:::

:::tip CLI
`lk perf load-test --room <room> --audio-publishers <n> --subscribers <n> --duration 5m` (alias `lk load-test`), and `lk perf agent-load-test --rooms <n> --agent-name <name> --echo-speech-delay 2s --duration 10m` ([load testing](https://docs.livekit.io/reference/developer-tools/livekit-cli/perf)).
:::

:::try
Run `load_test.sh` with `--subscribers 120` and watch `docker stats lab-livekit-1`. Before you run it, use the port range in `lab/livekit.yaml` to predict whether every subscriber will connect. Then widen `port_range_end`, restart the server, and run it again.
:::

:::warn Scaling up is easy, scaling down cuts calls
A node or agent server that is killed before it drains drops every call on it. Set the grace period longer than your longest call: up to 5 hours for LiveKit pods, 10 minutes or more for agent servers. Also stretch your autoscaler's scale-down window, because voice load falls slowly.
:::

:::note What we did not test
The lab is one node, so we didn't see rooms placed across nodes, signal proxying, the region-aware selector or draining with live calls. We didn't run `agent-load-test`, and the load generator shared the machine with the server. The benchmark table is from the docs, not ours.
:::

:::say
Rooms are placed on one node each and the cluster coordinates through Redis, so you scale by adding nodes and agent servers, measure with lk perf on real hardware, and drain before you remove anything.
:::

:::check Your nodes average 30% CPU, but one hot node is at 95% and its calls sound bad. Why didn't LiveKit move them?
A room stays on the node it was placed on. Load only affects where new rooms go, through `sysload_limit`. Existing calls stay until they end, so add capacity before nodes get hot.
:::

:::check Your agent servers use the default `load_threshold`. At what CPU level should the autoscaler add servers?
Below 0.7, for example at 0.5 as the docs suggest. By the time a server reaches 0.7 it already refuses jobs, so new capacity has to be starting before then.
:::
