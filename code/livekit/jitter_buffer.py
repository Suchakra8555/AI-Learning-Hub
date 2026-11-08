"""Why every WebRTC receiver keeps a small jitter buffer.

Run:  python jitter_buffer.py

Packets carry 20 ms of audio each and leave every 20 ms. The network delays
each one by a different amount and drops a few. A buffer of depth D holds
audio for D ms before playing it. Too small: gaps. Too big: added delay.
"""
import random

FRAME_MS, N = 20, 500


def network(seed):
    rnd = random.Random(seed)
    arrivals = {}
    for seq in range(N):
        if rnd.random() < 0.02:                     # 2% loss
            continue
        delay = 40 + rnd.expovariate(1 / 15)        # 40 ms base + a long tail
        arrivals[seq] = seq * FRAME_MS + delay
    return arrivals


def play(arrivals, depth_ms):
    late = lost = 0
    for seq in range(N):
        deadline = seq * FRAME_MS + 40 + depth_ms   # when this frame must play
        if seq not in arrivals:
            lost += 1                               # concealment (PLC) fills it
        elif arrivals[seq] > deadline:
            late += 1                               # arrived after its slot: useless
    return late, lost


if __name__ == "__main__":
    arr = network(seed=7)
    reordered = sum(1 for s in range(1, N) if s in arr and s - 1 in arr and arr[s] < arr[s - 1])
    print(f"{N} packets, {N - len(arr)} lost, {reordered} arrived before the one sent ahead of them\n")
    print("buffer  added delay  late frames  gaps to conceal")
    for depth in (0, 10, 20, 40, 60, 100):
        late, lost = play(arr, depth)
        print(f"{depth:>4} ms  {depth:>8} ms  {late:>11}  {late + lost:>15}")
    # shortcut: fixed depth. Real stacks (e.g. NetEq in libwebrtc) grow and shrink it as jitter changes.
