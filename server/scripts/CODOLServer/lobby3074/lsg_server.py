# -*- coding: utf-8 -*-
"""CODOL lobby (lsg) server on 127.0.0.2:3074, plain TCP.

Implements the frame protocol from CODOL_LOBBY_WORKING_20261002.md section 3.
The key material is read from secrets.txt, which the in-process observer writes
after reading game memory (the server process itself cannot read the game).

Frame layout (client -> server, 0x85):
    u32 total | AB | 85 | u32 seq | iv[16] | cipher | hmac8[8]
    hmac8 = HMAC-SHA1(hmac_out, frame[:-8])[:8]
    plain = AES-128-CBC-decrypt(aes_out, iv, cipher)
          = u32 declared | 0x86 | service | 0x03 | task | payload

Reply (server -> client, same shell):
    plain = u32 len | 0x01 | TLV
    TLV   = tag10+u64 replyId | tag8+u32 status | tag3+u8 task | tag8+u32 nobj
    seq echoes the request seq; replyId is an independent counter from 1.
"""
import argparse
import json
import os
import socket
import struct
import threading
import time

from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA1


# ---------------------------------------------------------------------------
# hmac key recovery
# ---------------------------------------------------------------------------
# The observer snapshots 40 bytes at [sub+0x60C].  Those bytes are two 20-byte
# HMAC keys stored XOR-obfuscated: hmac_out is blob[0:20], hmac_in is
# blob[20:40], and each is recovered with dst[i] = TABLE[IDX[i]] ^ src[i]
# (the codec at 0xBA0420; the project already implements it in
# lobby_plain_probe.py as codec_0420).
_T0420_TABLE = bytes([
    0x41, 0x13, 0x09, 0xAE, 0x3F, 0xA3, 0xBC, 0xF3, 0x18, 0x72,
    0xEA, 0xBC, 0x09, 0x32, 0x11, 0xCC, 0x12, 0x42, 0x54, 0xF4,
])
_T0420_IDX = bytes([
    0x07, 0x11, 0x0E, 0x10, 0x09, 0x13, 0x0D, 0x00, 0x02, 0x03,
    0x04, 0x08, 0x01, 0x0A, 0x0B, 0x05, 0x12, 0x06, 0x0C, 0x0F,
])


def codec_0420(src):
    """dst[i] = TABLE[IDX[i]] ^ src[i] for 20 bytes; symmetric."""
    if len(src) < 20:
        raise ValueError("codec_0420 needs 20 bytes")
    return bytes(_T0420_TABLE[_T0420_IDX[i]] ^ src[i] for i in range(20))


# ----------------------------------------------------------------------------
# logging
# ----------------------------------------------------------------------------
class Log(object):
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.fh = open(path, "a", encoding="utf-8") if path else None

    def __call__(self, msg):
        line = "%.3f %s" % (time.time(), msg)
        with self.lock:
            print(line, flush=True)
            if self.fh:
                self.fh.write(line + "\n")
                self.fh.flush()


def hexs(b, n=None):
    if n is not None:
        b = b[:n]
    return " ".join("%02X" % x for x in b)


# ----------------------------------------------------------------------------
# secrets (written by the observer)
# ----------------------------------------------------------------------------
class Secrets(object):
    """Reads secrets.txt produced by the in-process observer.

    Expected format (one key=value per line, hex values):
        svc=0x........
        sub=0x........
        challenge=<16 hex chars = 8 bytes>
        aes_out=<32 hex = 16 bytes>
        aes_in=<32 hex = 16 bytes>
        hmac_out=<40 hex = 20 bytes>
        hmac_in=<40 hex = 20 bytes>
    """

    def __init__(self, path, log):
        self.path = path
        self.log = log
        self.lock = threading.Lock()
        self.data = {}
        self.mtime = 0

    def load(self):
        try:
            st = os.stat(self.path)
        except OSError:
            return False
        with self.lock:
            # Always reload: the observer writes continuously (2 Hz) and the
            # client re-derives keys on every reconnect.  A stale cache here
            # causes HMAC verification failures on the second connection.
            try:
                txt = open(self.path, encoding="utf-8").read()
            except OSError:
                return False
            d = {}
            for line in txt.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v = v.strip()
                if v.startswith("0x"):
                    v = v[2:]
                try:
                    d[k.strip()] = bytes.fromhex(v)
                except ValueError:
                    pass
            self.data = d
            self.mtime = st.st_mtime
            self.log("[secrets] loaded %d field(s): %s"
                     % (len(d), ",".join(sorted(d))))
            return True

    def get(self, k):
        with self.lock:
            return self.data.get(k)

    def hmac_keys(self):
        """Return (hmac_out, hmac_in) recovered from the 40-byte blob.

        Accepts either an explicit hmac_out/hmac_in pair (if a future observer
        exports them directly) or the raw blob, which is what this observer
        writes."""
        with self.lock:
            ho = self.data.get("hmac_out")
            hi = self.data.get("hmac_in")
            blob = self.data.get("blob")
        if ho and hi:
            return ho, hi
        if blob and len(blob) >= 40:
            return codec_0420(blob[0:20]), codec_0420(blob[20:40])
        return None, None


# ----------------------------------------------------------------------------
# frame codec
# ----------------------------------------------------------------------------
TAG_REPLYID = 0x10
TAG_STATUS = 0x08
TAG_TASK = 0x03
TAG_NOBJ = 0x08


def hmac8(key, data):
    h = HMAC.new(key, digestmod=SHA1)
    h.update(data)
    return h.digest()[:8]


def aes128cbc_dec(key, iv, ct):
    return AES.new(key, AES.MODE_CBC, iv).decrypt(ct)


def aes128cbc_enc(key, iv, pt):
    pad = 16 - (len(pt) % 16)
    pt = pt + bytes([pad]) * pad
    return AES.new(key, AES.MODE_CBC, iv).encrypt(pt)


def parse_client_85(buf):
    """Return dict or None. buf = full frame bytes."""
    if len(buf) < 4 + 1 + 1 + 4 + 16 + 8:
        return None
    total = struct.unpack_from("<I", buf, 0)[0]
    if buf[5] != 0x85:
        return None
    seq = struct.unpack_from("<I", buf, 6)[0]
    iv = buf[10:26]
    cipher = buf[26:len(buf) - 8]
    tag = buf[len(buf) - 8:]
    return {"total": total, "seq": seq, "iv": iv, "cipher": cipher,
            "tag": tag, "raw": buf}


def parse_inner_plain(plain):
    """decrypt result -> dict."""
    if len(plain) < 8:
        return None
    declared = struct.unpack_from("<I", plain, 0)[0]
    if plain[4] != 0x86:
        return None
    service = plain[5]
    if plain[6] != 0x03:
        return None
    task = plain[7]
    payload = plain[8:8 + max(0, declared - 3)]
    return {"declared": declared, "service": service, "task": task,
            "payload": payload}


def build_reply(seq, reply_id, task, status, objects=None):
    """Build the server->client 0x85 reply plaintext (before AES)."""
    tlv = b""
    tlv += bytes([TAG_REPLYID]) + struct.pack("<Q", reply_id)
    tlv += bytes([TAG_STATUS]) + struct.pack("<I", status)
    tlv += bytes([TAG_TASK]) + bytes([task])
    nobj = len(objects) if objects else 0
    tlv += bytes([TAG_NOBJ]) + struct.pack("<I", nobj)
    if objects:
        tlv += bytes([TAG_NOBJ]) + struct.pack("<I", nobj)
        for o in objects:
            tlv += o
    body = b"\x01" + tlv
    return struct.pack("<I", len(body)) + body


def wrap_85(seq, iv, plain, key, hmac_key):
    ct = aes128cbc_enc(key, iv, plain)
    body = struct.pack("<I", seq) + iv + ct
    frame = b"\x00\x85" + body
    frame = struct.pack("<I", len(frame) + 8) + frame
    tag = hmac8(hmac_key, frame)
    return frame + tag


def obj_file(data):
    """File-type data object: tag 0x13 + tag 0x08 + u32 len + raw bytes."""
    return (bytes([0x13]) + bytes([0x08]) + struct.pack("<I", len(data)) + data)


def obj_currency(kind, amount):
    """Currency object per doc section 5: 03 <currency> 08 <u32>."""
    return bytes([0x03, kind, 0x08]) + struct.pack("<I", amount)


# ----------------------------------------------------------------------------
# locally authored payload data
# ----------------------------------------------------------------------------
USER_NAME = "CODOL-LOCAL-0001"
CP_BALANCE = 985699
GP_BALANCE = 883599
PLAYER_ID = 11355988700816506746


def _pattern(n, start=0x20):
    return bytes((start + (i % 0x40)) & 0xFF for i in range(n))


PUBLISHER_INFOS = [
    # Ten synthetic publisher .info files.  The client asks for ten; each is
    # a small opaque config blob it stores and later reads by name.
    _pattern(0x100, 0x20),
    _pattern(0x0C0, 0x30),
    _pattern(0x080, 0x40),
    _pattern(0x060, 0x50),
    _pattern(0x040, 0x60),
    _pattern(0x030, 0x70),
    _pattern(0x028, 0x80),
    _pattern(0x020, 0x90),
    _pattern(0x018, 0xA0),
    _pattern(0x010, 0xB0),
]


def _profile_public():
    """Synthetic public player profile (the client renders what it finds)."""
    body = bytearray()
    body += struct.pack("<I", 0x2BC)            # result code 700
    body += USER_NAME.encode("ascii")
    body += b"\x00" * (0x40 - len(USER_NAME))
    body += struct.pack("<Q", PLAYER_ID)
    body += struct.pack("<I", CP_BALANCE)       # CP
    body += struct.pack("<I", GP_BALANCE)       # GP
    body += b"\x00" * 0x100
    return bytes(body)


def _profile_secure():
    body = bytearray()
    body += struct.pack("<I", 0x2BC)
    body += struct.pack("<Q", PLAYER_ID)
    body += struct.pack("<I", CP_BALANCE)
    body += struct.pack("<I", GP_BALANCE)
    body += b"\x00" * 0x200
    return bytes(body)


def _user_file():
    return USER_NAME.encode("ascii") + b"\x00" * 0x20


# ----------------------------------------------------------------------------
# handshake
# ----------------------------------------------------------------------------
def handle_hello_28(frame):
    """Client's initial 28-byte hello."""
    parts = struct.unpack_from("<IIIII", frame, 0)
    nonce = frame[20:28]
    return {"fields": parts, "nonce": nonce}


def build_0x81(magic, nonce8):
    """u32 22 | 00 | 81 | u32 magic | 8B random | 8B = hello[20:28]"""
    body = struct.pack("<I", magic) + os.urandom(8) + nonce8
    f = b"\x00\x81" + body
    return struct.pack("<I", len(f)) + f


def build_0x83(challenge8):
    f = b"\x00\x83" + challenge8
    return struct.pack("<I", len(f)) + f


# ----------------------------------------------------------------------------
# server
# ----------------------------------------------------------------------------
class LobbyServer(object):
    def __init__(self, bind, port, log, secrets):
        self.bind = bind
        self.port = port
        self.log = log
        self.secrets = secrets
        self.reply_id = 1
        self.pending = []
        self.armed = False
        # The 0x83 challenge must be the 8 bytes the CLIENT derived and stored
        # at [req+0x5FC].  It cannot be inferred from the 0x82 frame tail --
        # measured: the frame carried "03869a921d8c6feb" while the live 5FC
        # held "e1909d7027ed89bb".  The observer exports the live value to this
        # file, so read it here.
        self.echo_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "logs", "Z7_3074", "echo.txt")

    def read_echo(self):
        """Return the 8-byte challenge hex from the observer, or None."""
        try:
            txt = open(self.echo_file, encoding="utf-8").read().strip()
        except OSError:
            return None
        if len(txt) != 16:
            return None
        try:
            bytes.fromhex(txt)
        except ValueError:
            return None
        return txt

    def serve(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.bind, self.port))
        srv.listen(8)
        self.log("=== lsg listening on %s:%d ===" % (self.bind, self.port))
        while True:
            c, a = srv.accept()
            self.log("=== lobby connection from %s:%d ===" % a)
            t = threading.Thread(target=self.session, args=(c, a), daemon=True)
            t.start()

    def session(self, c, a):
        c.settimeout(1.0)
        state = {"hello": False, "sent81": False, "sent83": False, "last_ka": 0.0}
        buf = b""
        while True:
            try:
                d = c.recv(65536)
            except socket.timeout:
                self.drain_pending(c)
                now = time.time()
                if now - state.get("last_ka", 0) >= 5.0:
                    state["last_ka"] = now
                    try:
                        c.sendall(b"\x00\x00\x00\x00")
                    except OSError:
                        pass
                continue
            except OSError as e:
                self.log("recv error: %s" % e)
                break
            if not d:
                self.log("client closed")
                break
            buf += d

            # 28-byte hello
            if not state["hello"] and len(buf) >= 28 and buf[0:4] == b"\xc8\x00\x00\x00":
                h = handle_hello_28(buf[:28])
                buf = buf[28:]
                state["hello"] = True
                self.log("<- client hello fields=%s nonce=%s"
                         % (h["fields"], hexs(h["nonce"])))
                c.sendall(build_0x81(0xDC, h["nonce"]))
                state["sent81"] = True
                self.log("-> 0x81 magic=0xDC")
                continue

            # subsequent frames: u32 len + body
            while len(buf) >= 4:
                ln = struct.unpack_from("<I", buf, 0)[0]
                if ln == 0 or ln > 1 << 20:
                    self.log("!! bad frame len %d, dropping buffer" % ln)
                    buf = b""
                    break
                if len(buf) < ln + 4:
                    break
                frame = buf[:ln + 4]
                buf = buf[ln + 4:]
                self.on_frame(c, frame, state)

    def on_frame(self, c, frame, state):
        if len(frame) < 6:
            return
        op = frame[5]
        if op == 0x82:
            self.log("<- 0x82 stage1 len=%d" % len(frame))
            # The challenge echoed in 0x83 must equal the value the client
            # stored at [req+0x5FC].  Waiting briefly lets the observer publish
            # it (it writes echo.txt right after the same transition).
            ch = None
            for _ in range(20):
                hx = self.read_echo()
                if hx:
                    ch = bytes.fromhex(hx)
                    self.log("   echo.txt -> challenge=%s" % hx)
                    break
                time.sleep(0.01)
            if ch is None:
                ch = os.urandom(8)
                self.log("   !! echo.txt unavailable -> random challenge "
                         "(client will reject 0x83)")
            c.sendall(build_0x83(ch))
            state["sent83"] = True
            self.log("-> 0x83 challenge=%s" % hexs(ch))
        elif op == 0x85:
            self.on_85(c, frame)
        elif op == 0x00 or op == 0x86:
            pass
        else:
            self.log("<- opcode 0x%02X len=%d  %s" % (op, len(frame), hexs(frame, 32)))

    def on_85(self, c, frame):
        fr = parse_client_85(frame)
        if fr is None:
            self.log("!! malformed 0x85")
            return
        if not self.secrets.load():
            self.pending.append(frame)
            self.log("<- 0x85 seq=%d (secrets not ready, queued; n=%d)"
                     % (fr["seq"], len(self.pending)))
            return
        self.decrypt_and_reply(c, fr)

    def drain_pending(self, c):
        if not self.pending or not self.secrets.load():
            return
        q = self.pending
        self.pending = []
        self.log("draining %d queued 0x85 frame(s)" % len(q))
        for raw in q:
            fr = parse_client_85(raw)
            if fr:
                self.decrypt_and_reply(c, fr)

    def decrypt_and_reply(self, c, fr):
        aes_out = self.secrets.get("aes_out")
        hmac_out, _hmac_in = self.secrets.hmac_keys()
        if not aes_out or not hmac_out:
            self.log("!! secrets incomplete (aes_out/hmac_out missing)")
            return
        calc = hmac8(hmac_out, fr["raw"][:-8])
        ok = (calc == fr["tag"])
        if not ok:
            # The client may have just reconnected with fresh keys.  The
            # observer writes secrets at 2 Hz, so wait briefly and retry.
            for _ in range(10):
                time.sleep(0.2)
                self.secrets.load()
                aes_out2 = self.secrets.get("aes_out")
                hmac_out2, _ = self.secrets.hmac_keys()
                if aes_out2 and hmac_out2:
                    calc2 = hmac8(hmac_out2, fr["raw"][:-8])
                    if calc2 == fr["tag"]:
                        ok = True
                        aes_out = aes_out2
                        hmac_out = hmac_out2
                        self.log("   hmac retry OK after secrets refresh")
                        break
        try:
            plain = aes128cbc_dec(aes_out, fr["iv"], fr["cipher"])
        except Exception as e:
            self.log("!! decrypt error: %s" % e)
            return
        inner = parse_inner_plain(plain)
        if inner is None:
            self.log("<- 0x85 seq=%d hmac=%s plain(no inner) %s"
                     % (fr["seq"], "OK" if ok else "BAD", hexs(plain, 24)))
            return
        self.log("<- 0x85 seq=%d hmac=%s service=%d task=%d payload=%dB"
                 % (fr["seq"], "OK" if ok else "BAD", inner["service"],
                    inner["task"], len(inner["payload"])))

        # First reply in a session: arm the 0x87 gate first.
        # 0xBA3600 (the 0x89 handler) requires [req+0x644] == 1, which is
        # only set by a successful 0xBA3590 (0x87) arm.  Without the arm,
        # the client drops our replies.
        if not self.armed:
            # The client's 0xBA3710 parser expects a full-size frame
            # (the wire length field must match what the parser reads).
            # frame_len=382 gives inner_len=352 bytes of AES plaintext.
            frame_len = 382
            inner = bytes([0x87, 0x01])
            inner_len = frame_len - 2 - 4 - 16 - 8  # type+opcode+seq+iv+hmac
            plaintext = inner + b"\x00" * (inner_len - len(inner))
            iv = os.urandom(16)
            ct = aes128cbc_enc(aes_out, iv, plaintext)
            body = struct.pack("<I", 0) + iv + ct  # seq=0 for server-initiated
            frame_wo_tag = struct.pack("<I", frame_len) + b"\x00\x85" + body
            tag = hmac8(hmac_out, frame_wo_tag)
            arm_out = frame_wo_tag + tag
            c.sendall(arm_out)
            self.armed = True
            self.push_config(c)
            self.log("-> 0x85 arm (0x87) frame_len=%d total=%d"
                     % (frame_len, len(arm_out)))
        objs = self.handle_task(inner)
        if objs is None:
            self.log("   no reply sent (handler returned None)")
            return
        rid = self.reply_id
        self.reply_id += 1
        # Build TLV reply (first byte 0x01 -> 0xBA3B36 else path -> 0xB9BBC0)
        rep = build_reply(fr["seq"], rid, inner["task"], 0, objs)
        # Pad to 382-byte frame so client parser sees expected size
        frame_len = 382
        inner_len = frame_len - 2 - 4 - 16 - 8
        plaintext = rep + b"\x00" * (inner_len - len(rep))
        iv = os.urandom(16)
        ct = aes128cbc_enc(aes_out, iv, plaintext)
        body = struct.pack("<I", fr["seq"]) + iv + ct
        frame_wo_tag = struct.pack("<I", frame_len) + b"\x00\x85" + body
        tag = hmac8(hmac_out, frame_wo_tag)
        out = frame_wo_tag + tag
        c.sendall(out)
        self.log("-> 0x85 reply seq=%d replyId=%d TLV nobj=%d frame=%d"
                 % (fr["seq"], rid, len(objs) if objs else 0, len(out)))

    def send_arm(self, c):
        """Send a server->client 0x85 frame containing the 0x87 arm inner."""
        self.secrets.load()
        aes_out = self.secrets.get("aes_out")
        hmac_out, _ = self.secrets.hmac_keys()
        if not aes_out or not hmac_out:
            self.log("   !! arm: secrets not ready")
            return
        inner = bytes([0x87, 0x01])
        rep = struct.pack("<I", len(inner)) + inner
        out = wrap_85(0, os.urandom(16), rep, aes_out, hmac_out)
        c.sendall(out)
        self.log("-> 0x85 arm (0x87) len=%d" % len(out))


    def build_task_inner(self, service, task, payload=b""):
        """Build inner plaintext for a server->client task push.
        Format: u32 declared | 0x86 | service | 0x03 | task | payload"""
        declared = 3 + len(payload)
        inner = struct.pack("<I", declared) + bytes([0x86, service, 0x03, task]) + payload
        return inner

    def push_frame(self, c, seq, service, task, payload=b""):
        """Send a server->client 0x85 task push frame."""
        self.secrets.load()
        aes_out = self.secrets.get("aes_out")
        hmac_out, _ = self.secrets.hmac_keys()
        if not aes_out or not hmac_out:
            self.log("   !! push: secrets not ready")
            return
        inner = self.build_task_inner(service, task, payload)
        fl = 382
        inner_len = fl - 2 - 4 - 16 - 8
        if len(inner) > inner_len:
            inner_len = ((len(inner) + 15) // 16) * 16
        plaintext = inner + b"\x00" * (inner_len - len(inner))
        iv = os.urandom(16)
        ct = aes128cbc_enc(aes_out, iv, plaintext)
        body = struct.pack("<I", seq) + iv + ct
        frame_wo_tag = struct.pack("<I", fl) + b"\x00\x85" + body
        tag = hmac8(hmac_out, frame_wo_tag)
        frame = frame_wo_tag + tag
        c.sendall(frame)
        self.log("-> 0x85 push seq=%d svc=%d task=%d len=%d" % (seq, service, task, len(frame)))

    def push_config(self, c):
        """Push all configuration data after 0x83 handshake."""
        self.secrets.load()
        seq = 100  # start from a high seq to avoid collision with client seq
        # 10/21 x10: publisher .info files
        for i, info_data in enumerate(PUBLISHER_INFOS):
            payload = bytes([0x13, 0x08]) + struct.pack("<I", len(info_data)) + info_data
            self.push_frame(c, seq, 10, 21, payload)
            seq += 1
        # 10/12: user file
        user_data = USER_NAME.encode("ascii") + b"\x00" * 16
        payload = bytes([0x13, 0x08]) + struct.pack("<I", len(user_data)) + user_data
        self.push_frame(c, seq, 10, 12, payload)
        seq += 1
        # 8/1: public profile
        prof = _profile_public()
        payload = bytes([0x13, 0x08]) + struct.pack("<I", len(prof)) + prof
        self.push_frame(c, seq, 8, 1, payload)
        seq += 1
        # 8/2: secure profile
        prof2 = _profile_secure()
        payload = bytes([0x13, 0x08]) + struct.pack("<I", len(prof2)) + prof2
        self.push_frame(c, seq, 8, 2, payload)
        seq += 1
        # 80/130: CP balance
        cp_data = bytes([0x03, 0x01, 0x08]) + struct.pack("<I", CP_BALANCE)
        self.push_frame(c, seq, 80, 130, cp_data)
        seq += 1
        # 93/1: GP balance
        gp_data = bytes([0x03, 0x02, 0x08]) + struct.pack("<I", GP_BALANCE)
        self.push_frame(c, seq, 93, 1, gp_data)
        seq += 1
        self.log("-> pushed %d config frames" % (seq - 100))

    def handle_task(self, inner):
        """Task dispatch. Returns a list of data objects (or empty)."""
        svc, task, pl = inner["service"], inner["task"], inner["payload"]
        self.log("   task %d/%d payload %dB %s" % (svc, task, len(pl), hexs(pl)))
        # File-type objects in the request are tag0x13 + tag0x08 + u32 len +
        # data (doc section 3).  Parse them so the log shows what is asked for.
        off = 0
        want = []
        while off + 6 <= len(pl):
            if pl[off] == 0x13 and pl[off + 1] == 0x08:
                n = struct.unpack_from("<I", pl, off + 2)[0]
                want.append((off, n))
                off += 6 + n
            else:
                off += 1
        if want:
            self.log("     file-objects requested: %s"
                     % ", ".join("len=%d" % n for _, n in want))
        return self.dispatch(svc, task, pl)

    def dispatch(self, svc, task, pl):
        """Return the data objects for (svc, task).

        Mirrors the coverage table in the working reference (doc section 5):
        publisher/user/profile/currency tasks carry real objects, everything
        else answers empty, which the client accepts.
        """
        key = (svc, task)
        if key == (10, 21):
            # Ten publisher config files.
            self.log("     10/21 -> %d publisher .info objects" %
                     len(PUBLISHER_INFOS))
            return [obj_file(d) for d in PUBLISHER_INFOS]
        if key == (10, 12):
            self.log("     10/12 -> user file")
            return [obj_file(_user_file())]
        if key == (8, 1):
            self.log("     8/1  -> public profile (%d bytes)"
                     % len(_profile_public()))
            return [obj_file(_profile_public())]
        if key == (8, 2):
            self.log("     8/2  -> secure profile (%d bytes)"
                     % len(_profile_secure()))
            return [obj_file(_profile_secure())]
        if key == (80, 130):
            self.log("     80/130 -> CP balance")
            return [obj_currency(0x01, CP_BALANCE)]
        if key == (93, 1):
            self.log("     93/1  -> GP balance")
            return [obj_currency(0x02, GP_BALANCE)]
        if key == (71, 4):
            self.log("     71/4  -> identity objects")
            return [
                obj_file(b"\x00" * 16),
                obj_file(USER_NAME.encode("ascii")),
                obj_file(_pattern(0x80, 0x20)),
                obj_file(b"\x00" * 0x80),
            ]


            return self.handlers[key](self, pl)
        self.log("     -> empty object list (unhandled task)")
        return []

    handlers = {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bind", default="127.0.0.2")
    ap.add_argument("--port", type=int, default=3074)
    ap.add_argument("--secrets", default=r"D:\z7tmp\secrets.txt")
    ap.add_argument("--log", default="")
    a = ap.parse_args()
    log = Log(a.log)
    secrets = Secrets(a.secrets, log)
    LobbyServer(a.bind, a.port, log, secrets).serve()


if __name__ == "__main__":
    main()
