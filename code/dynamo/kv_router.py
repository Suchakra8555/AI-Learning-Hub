"""Three ways to pick a worker, on fake chat traffic. Run: python kv_router.py

Three workers each keep a cache of prompt blocks (16 tokens per block). A request is a list of
block ids. A worker can skip prefill for the blocks at the start of the prompt that it already holds.
Each request is one turn of a chat. Chats belong to a few families that share a long system prompt,
and each later turn repeats the whole chat so far, then adds a little more.

Policies:
  round-robin    next worker in turn, ignores caches
  overlap only   the worker with the longest cached prefix
  overlap - load the worker with the most overlap, minus the blocks it is already busy with

The last one is a simplified form of the cost in Dynamo's router docs: cost = uncached prefill blocks
+ blocks in flight on that worker. The prompt length is the same for every worker, so the lowest cost
is the same worker as the highest (overlap minus load).
shortcut: time is whole ticks, one request arrives per tick, and a request holds its blocks for a
number of ticks that depends on how much prefill it needed. Real engines are far messier.
shortcut: the cache is a plain LRU of blocks, and a cached block is just a label, not tensors.
This is our toy, not Dynamo's code, and the numbers say nothing about real speed.
"""
import random
from collections import OrderedDict

BLOCK = 16  # tokens per block
WORKERS = 3
CACHE_BLOCKS = 220  # per worker: room for about two chats' worth of history
REQUESTS = 200
FAMILIES = 4
CHATS_PER_FAMILY = 3
SYSTEM_BLOCKS = 24  # shared system prompt per family: 384 tokens
TURN_BLOCKS = 6  # each turn adds about this much to the chat
random.seed(5)


def make_requests():
    """200 requests. Each is a tuple of block ids: system prompt, chat so far, new turn."""
    turns = {}  # (family, chat) -> number of turns already taken
    out = []
    for _ in range(REQUESTS):
        fam, chat = random.randrange(FAMILIES), random.randrange(CHATS_PER_FAMILY)
        n = turns.get((fam, chat), 0)
        turns[(fam, chat)] = n + 1
        system = [("sys", fam, i) for i in range(SYSTEM_BLOCKS)]
        history = [("chat", fam, chat, i) for i in range((n + 1) * TURN_BLOCKS)]
        out.append(tuple(system + history))
    return out


class Worker:
    def __init__(self):
        self.cache = OrderedDict()  # block id -> True, oldest first
        self.active = []  # [finish_tick, blocks] for requests in flight

    def overlap(self, blocks):
        """Number of blocks at the start of the prompt that are cached here."""
        n = 0
        for b in blocks:
            if b not in self.cache:
                break
            n += 1
        return n

    def load(self, now):
        self.active = [a for a in self.active if a[0] > now]
        return sum(a[1] for a in self.active)

    def store(self, blocks):
        for b in blocks:
            self.cache[b] = True
            self.cache.move_to_end(b)
        while len(self.cache) > CACHE_BLOCKS:
            self.cache.popitem(last=False)  # evict the least recently used block


def run(policy):
    workers = [Worker() for _ in range(WORKERS)]
    hits = total = peak = 0
    counts = [0] * WORKERS
    for now, blocks in enumerate(make_requests()):
        loads = [w.load(now) for w in workers]
        overlaps = [w.overlap(blocks) for w in workers]
        if policy == "round-robin":
            pick = now % WORKERS
        elif policy == "overlap only":
            pick = max(range(WORKERS), key=lambda i: (overlaps[i], -i))
        else:  # overlap - load
            pick = max(range(WORKERS), key=lambda i: (overlaps[i] - loads[i], -i))
        w = workers[pick]
        new = len(blocks) - overlaps[pick]
        hits += overlaps[pick]
        total += len(blocks)
        counts[pick] += 1
        w.active.append([now + 2 + new // 4, len(blocks)])  # more prefill, longer in flight
        w.store(blocks)
        peak = max(peak, max(x.load(now) for x in workers))
    return hits, total, peak, counts


print(f"{REQUESTS} requests, {WORKERS} workers, {FAMILIES} chat families, cache {CACHE_BLOCKS} blocks each")
print("peak in flight = most blocks being worked on at once by the busiest worker")
print(f"{'policy':15} {'cache hit':>9} {'recomputed tokens':>18} {'peak in flight':>14}  requests per worker")
for policy in ["round-robin", "overlap only", "overlap - load"]:
    hits, total, peak, counts = run(policy)
    print(f"{policy:15} {hits / total:9.0%} {(total - hits) * BLOCK:18,} {peak:14}  {counts}")
