"""Be the phone company: place a SIP call into self-hosted LiveKit, with no provider.

Run:  python sip_call.py           (lab + sip profile + echo agent running, sip_setup.sh done)

We send a SIP INVITE with an SDP offer for PCMU (G.711 mu-law, 8 kHz) to the
LiveKit SIP service, answer its 200 OK with an ACK, stream 20 ms RTP packets of
a tone, and listen for the echo agent sending our tone back as RTP. That is the
whole inbound phone path: SIP for signaling, RTP for audio.
"""
import math
import random
import re
import socket
import struct
import sys
import time

sys.path.insert(0, "../voice-prod")
from mulaw import DECODE, encode_sample   # G.711 codec from the voice-prod track

SIP_SERVER = (socket.gethostbyname(socket.gethostname()), 5060)  # the SIP service listens on the host IP
ME, CALLER, CALLEE = "127.0.0.1", "+15550001111", "+15105550100"
tag, call_id, branch = (f"{random.getrandbits(32):x}" for _ in range(3))

sip = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sip.bind((ME, 0))
rtp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rtp.bind((ME, 0))
sip_port, rtp_port = sip.getsockname()[1], rtp.getsockname()[1]

sdp = (f"v=0\r\no=- 1 1 IN IP4 {ME}\r\ns=-\r\nc=IN IP4 {ME}\r\nt=0 0\r\n"
       f"m=audio {rtp_port} RTP/AVP 0 101\r\na=rtpmap:0 PCMU/8000\r\na=rtpmap:101 telephone-event/8000\r\na=sendrecv\r\n")


def request(method, cseq, body="", extra=""):
    return (f"{method} sip:{CALLEE}@{SIP_SERVER[0]} SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {ME}:{sip_port};branch=z9hG4bK{branch}{method[:2]}\r\n"
            f"From: <sip:{CALLER}@{ME}>;tag={tag}\r\nTo: <sip:{CALLEE}@{SIP_SERVER[0]}>{extra}\r\n"
            f"Call-ID: {call_id}\r\nCSeq: {cseq} {method}\r\nContact: <sip:{CALLER}@{ME}:{sip_port}>\r\n"
            f"Max-Forwards: 70\r\nContent-Type: application/sdp\r\nContent-Length: {len(body)}\r\n\r\n{body}").encode()


sip.sendto(request("INVITE", 1, sdp), SIP_SERVER)
t0, to_tag, remote = time.monotonic(), "", None
sip.settimeout(15)
while True:
    msg = sip.recv(65535).decode()
    status = msg.split("\r\n")[0]
    print(f"{time.monotonic() - t0:5.2f}s  <- {status}")
    if " 200 " in status:
        to_tag = re.search(r"^To:.*?(;tag=[^\s;]+)", msg, re.M | re.I).group(1)
        ip = re.search(r"c=IN IP4 (\S+)", msg).group(1)
        port = int(re.search(r"m=audio (\d+)", msg).group(1))
        remote = (ip, port)
        codecs = re.findall(r"a=rtpmap:(\S+ \S+)", msg)
        print(f"        answer SDP: send RTP to {ip}:{port}, codecs {codecs}")
        break
    if int(status.split()[1]) >= 300:
        sys.exit("call failed")
sip.sendto(request("ACK", 1, extra=to_tag).replace(b"Content-Type: application/sdp\r\n", b""), SIP_SERVER)
print(f"{time.monotonic() - t0:5.2f}s  -> ACK (call is up)")

# Stream 1 s of 440 Hz tone, then 4 s of silence, as 20 ms PCMU RTP packets. Listen for the echo.
rtp.settimeout(0.001)
seq, ts, ssrc, heard = random.randint(0, 999), 0, random.getrandbits(32), None
start = time.monotonic()
for i in range(250):  # 5 s: 1 s tone, then silence
    amp = 8000 if i < 50 else 0
    payload = bytes(encode_sample(int(amp * math.sin(2 * math.pi * 440 * (ts + n) / 8000))) for n in range(160))
    rtp.sendto(struct.pack("!BBHII", 0x80, 0, seq & 0xFFFF, ts, ssrc) + payload, remote)
    seq, ts = seq + 1, ts + 160
    try:
        while True:
            pkt = rtp.recv(2048)
            pcm = [DECODE[b] for b in pkt[12:]]
            if pcm and heard is None and math.sqrt(sum(x * x for x in pcm) / len(pcm)) > 1000:
                heard = time.monotonic() - start
                print(f"        <- RTP from LiveKit: payload type {pkt[1] & 0x7F}, {len(pkt) - 12} bytes, loud: our tone came back after {heard:.2f} s")
    except socket.timeout:
        pass
    time.sleep(max(0, start + (i + 1) * 0.02 - time.monotonic()))

sip.sendto(request("BYE", 2, extra=to_tag).replace(b"Content-Type: application/sdp\r\n", b""), SIP_SERVER)
print(f"{time.monotonic() - t0:5.2f}s  -> BYE, <- {sip.recv(65535).decode().splitlines()[0]}")
