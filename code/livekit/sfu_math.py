"""Mesh vs MCU vs SFU: who sends, who receives, who decodes.

Run:  python sfu_math.py

Assume every participant publishes one audio stream at 32 kbit/s (a typical
Opus voice rate). Count streams on the busiest client and on the server.
"""
KBPS = 32


def mesh(n):   # everyone sends to everyone
    return dict(client_up=(n - 1) * KBPS, client_down=(n - 1) * KBPS, server_in=0, server_out=0, decodes=0)


def mcu(n):    # server decodes all, mixes one stream per person, re-encodes
    return dict(client_up=KBPS, client_down=KBPS, server_in=n * KBPS, server_out=n * KBPS, decodes=n)


def sfu(n):    # server forwards packets untouched
    return dict(client_up=KBPS, client_down=(n - 1) * KBPS, server_in=n * KBPS, server_out=n * (n - 1) * KBPS, decodes=0)


if __name__ == "__main__":
    print(f"{'n':>3} {'topology':8} {'client up':>10} {'client down':>12} {'server out':>11} {'server decodes':>15}")
    for n in (2, 3, 10):
        for name, f in (("mesh", mesh), ("MCU", mcu), ("SFU", sfu)):
            r = f(n)
            print(f"{n:>3} {name:8} {r['client_up']:>7} kb {r['client_down']:>9} kb {r['server_out']:>8} kb {r['decodes']:>15}")
        print()
    print("A voice-agent call is n=2: caller + agent. The SFU just forwards; the agent does its own decoding.")
    # shortcut: ignores video, simulcast, and the encode cost on each client.
