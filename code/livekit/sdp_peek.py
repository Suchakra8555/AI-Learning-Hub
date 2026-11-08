"""Read an SDP offer the way a WebRTC stack does.

Run:  python sdp_peek.py

SDP is plain text, one "type=value" per line. This is a trimmed audio-only offer
of the kind a browser sends. The IP addresses are documentation ranges.
"""
OFFER = """\
v=0
o=- 4611731400430051336 2 IN IP4 127.0.0.1
s=-
t=0 0
a=group:BUNDLE 0
m=audio 9 UDP/TLS/RTP/SAVPF 111 0
c=IN IP4 0.0.0.0
a=mid:0
a=ice-ufrag:EsAw
a=ice-pwd:P2uYro0UCOQ4zxjKXaWCBui1
a=fingerprint:sha-256 D2:FA:0E:C3:22:59:5E:14:95:69:92:3D:13:B4:84:24:2C:C2:A2:C0:3E:FD:34:8E:5E:EA:6F:AF:52:CE:E6:0F
a=setup:actpass
a=sendrecv
a=rtcp-mux
a=rtpmap:111 opus/48000/2
a=fmtp:111 minptime=10;useinbandfec=1
a=rtpmap:0 PCMU/8000
a=candidate:1 1 udp 2122260223 192.168.1.20 54400 typ host
a=candidate:2 1 udp 1686052607 203.0.113.7 54400 typ srflx raddr 192.168.1.20 rport 54400
a=candidate:3 1 udp 41885439 198.51.100.9 3478 typ relay raddr 203.0.113.7 rport 54400
"""


def peek(sdp):
    codecs, cands, info = {}, [], {}
    for line in sdp.splitlines():
        kind, _, value = line.partition("=")
        if kind == "m":
            media, _port, proto, *pts = value.split()
            info["media"], info["proto"], info["payload order"] = media, proto, pts
        elif value.startswith("rtpmap:"):
            pt, name = value[7:].split(" ", 1)
            codecs[pt] = name
        elif value.startswith("fmtp:"):
            pt, params = value[5:].split(" ", 1)
            codecs[pt] += f"  ({params})"
        elif value.startswith("candidate:"):
            f = value.split()
            cands.append((f[7], f[4], f[5], int(f[3])))  # type, ip, port, priority
        elif value.startswith(("fingerprint:", "setup:", "ice-ufrag:")):
            k, _, v = value.partition(":")
            info[k] = v[:23] + "..." if len(v) > 26 else v
    return info, codecs, cands


if __name__ == "__main__":
    info, codecs, cands = peek(OFFER)
    for k, v in info.items():
        print(f"{k:14} {v}")
    print("\ncodecs, in order of preference:")
    for pt in info["payload order"]:
        print(f"  {pt:>3} -> {codecs[pt]}")
    print("\nICE candidates, highest priority first:")
    for typ, ip, port, prio in sorted(cands, key=lambda c: -c[3]):
        print(f"  {typ:6} {ip}:{port:<6} priority {prio}")
