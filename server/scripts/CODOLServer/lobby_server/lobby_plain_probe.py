#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plain-TCP lobby channel probe.

The client's lobby channel (built by 0x007F3800, connected by 0x00C73900 via
the Tenio connector) is NOT TLS: when it landed on the HTTPS probe server the
server logged "WRONG_VERSION_NUMBER".  This listener accepts the raw socket,
hex-dumps everything the client sends, and can send canned replies so the
0x00BA41D0 state machine can be observed.

Usage:
  python -X utf8 lobby_plain_probe.py --bind 127.0.0.1 --port 8445 \
      --log logs/lobby_plain.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import struct
import sys
import threading
import time


def log(path: str, obj: dict) -> None:
    obj["ts"] = time.time()
    line = json.dumps(obj, ensure_ascii=False)
    print(line, flush=True)
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def hexdump(b: bytes) -> str:
    return " ".join("%02x" % x for x in b)


def build_frame(opcode: int, body: bytes, frame_len: int = 200,
                frame_type: int = 0x00) -> bytes:
    """Build a server->client lobby frame.

    Wire layout (confirmed by image_best disassembly of 0xBA20A0 / 0xBA4440):
        u32 frame_len | u8 type | u8 opcode | body...
    The dispatcher reads the opcode at reader-buffer offset 30, which maps to
    body[1] of the frame (i.e. the byte after the type byte).  Both 0x81 and
    0x83 reply frames from earlier runs used exactly this layout, e.g.
        c8 00 00 00 | 00 | 81 | d2 00 00 00 | <u64> | ...
    """
    payload = bytes([frame_type, opcode]) + body
    if frame_len > len(payload):
        payload += b"\x00" * (frame_len - len(payload))
    return struct.pack("<I", frame_len) + payload


def build_0x81(magic: int = 0xD2, token: int = 0x1122334455667788,
               tail: bytes = b"\x00" * 8, frame_len: int = 200) -> bytes:
    """opcode 0x81: u32 magic in [0xD2,0xDC], u64 token, 8 bytes."""
    return build_frame(0x81, struct.pack("<I", magic) + struct.pack("<Q", token)
                       + tail, frame_len=frame_len)


def build_0x83(echo8: bytes, frame_len: int = 200) -> bytes:
    """opcode 0x83: the 8 bytes the client must see echoed back."""
    return build_frame(0x83, echo8, frame_len=frame_len)


def build_0x84(value: int, frame_len: int = 200) -> bytes:
    """opcode 0x84: single u32; dispatcher then calls 0x7F9350."""
    return build_frame(0x84, struct.pack("<I", value & 0xFFFFFFFF),
                       frame_len=frame_len)


def build_0x89(frame_len: int = 200) -> bytes:
    """opcode 0x89 (handshake step 4).

    0xBA3BA0 only routes 0x89 to 0xBA3600 when [req+0x640] >= 0xDC, and
    0xBA3600 requires [req+0x644] == 1.  That is exactly the client state
    after a successful 0x83, so 0x89 is the frame that advances
    644: 1 -> 2 and 5E8: 3 -> 0.
    """
    return build_frame(0x89, b"\x00" * 4, frame_len=frame_len)


def build_0xC8_magic(frame_len: int = 200) -> bytes:
    """The 28-byte 0xC8 frame the client itself emits for 0x88.

    Shape taken from the very first bytes the client sends on the lobby
    socket (and from 0xBA3010's emit path):
        u32 0xC8 | u32 0xC8 | u32 0xD2 | u32 0xDC |
        u32 0x08 | u16 ? | u32 0xD4B1C7E9 | 8 bytes
    """
    return (struct.pack("<I", 0xC8) + struct.pack("<I", 0xC8)
            + struct.pack("<I", 0xD2) + struct.pack("<I", 0xDC)
            + struct.pack("<I", 0x08) + struct.pack("<H", 0)
            + struct.pack("<I", 0xD4B1C7E9) + b"\x00" * 8)


def build_0x85(v1: int, sixteen: bytes = b"\x00" * 16,
               frame_len: int = 200) -> bytes:
    """opcode 0x85: u32 + 16 bytes.

    The handler (0xBA3710) additionally XOR-compares an 8-byte field against
    a table-driven decode (0xBA02A0).  We send zeros first and let the
    observer dump the live comparison buffer, so the required value is read
    from memory instead of being guessed.
    """
    if len(sixteen) != 16:
        raise ValueError("sixteen must be exactly 16 bytes")
    return build_frame(0x85, struct.pack("<I", v1 & 0xFFFFFFFF) + sixteen,
                       frame_len=frame_len)


# 0xBA02A0 table-driven XOR codec (constants read from the image).
_T02A0_TABLE = bytes([
    0x80, 0x22, 0xDE, 0xAA, 0x0B, 0x1C, 0x21, 0xF4, 0x00, 0xFF,
    0xEE, 0x37, 0x27, 0x92, 0x10, 0xCE, 0xAA, 0xF4, 0x3C, 0x21,
])
_T02A0_IDX = bytes([
    0x13, 0x12, 0x09, 0x04, 0x11, 0x01, 0x0A, 0x08, 0x0D, 0x02,
    # index 13 is 0x10: at 0xBA02C2 the routine stores edx (=0x10) into
    # [ebp-0x34] which is IDX[13].  The previous table dropped it, leaving
    # only 19 entries; with `% len(IDX)` every index >= 13 then shifted and
    # the last 6 output bytes were wrong (verified byte-for-byte against the
    # disassembly of 0xBA02A0).
    0x0F, 0x03, 0x0C, 0x10, 0x05, 0x07, 0x00, 0x0E, 0x06, 0x0B,
])


def codec_02a0(src: bytes) -> bytes:
    """Encode/decode with 0xBA02A0: dst[i] = TABLE[IDX[i]] ^ src[i].

    The routine walks 4 groups of 5 bytes (0x14 stride per iteration) and is
    its own inverse, so the same call both produces the value the 0x85 handler
    compares against and can recover its input.
    """
    out = bytearray()
    for group in range(4):
        base = group * 5
        for i in range(5):
            k = _T02A0_IDX[(base + i) % len(_T02A0_IDX)]
            out.append(_T02A0_TABLE[k] ^ src[(base + i) % len(src)])
    return bytes(out)


# 0xBA0420 table-driven XOR codec: the SEND-side twin of 0xBA02A0.
#
# Verified byte-for-byte against the disassembly:
#   table = 41 13 09 ae 3f a3 bc f3 18 72 ea bc 09 32 11 cc 12 42 54 f4
#   idx   = 07 11 0e 10 09 13 0d 00 02 03 04 08 01 0a 0b 05 12 06 0c 0f
#
# Two details that made every earlier HMAC attempt miss:
#   * the source base is object+0x60C, NOT object+0x60D.  The disassembly does
#     `add eax,0x60D` and then reads `[eax-1]`, so the real first byte is 0x60C.
#   * nothing here is truncated: all 20 output bytes become the SHA1 key.
_T0420_TABLE = bytes([
    0x41, 0x13, 0x09, 0xAE, 0x3F, 0xA3, 0xBC, 0xF3, 0x18, 0x72,
    0xEA, 0xBC, 0x09, 0x32, 0x11, 0xCC, 0x12, 0x42, 0x54, 0xF4,
])
_T0420_IDX = bytes([
    0x07, 0x11, 0x0E, 0x10, 0x09, 0x13, 0x0D, 0x00, 0x02, 0x03,
    0x04, 0x08, 0x01, 0x0A, 0x0B, 0x05, 0x12, 0x06, 0x0C, 0x0F,
])


def codec_0420(src: bytes) -> bytes:
    """Encode/decode with 0xBA0420: dst[i] = TABLE[IDX[i]] ^ src[i]."""
    if len(src) < 20:
        raise ValueError("codec_0420 needs at least 20 source bytes")
    return bytes(_T0420_TABLE[_T0420_IDX[i]] ^ src[i] for i in range(20))


def key_0420_from_connection_object(obj: bytes) -> bytes:
    """SHA1 key used by the client's own outgoing 0x85, from a connection dump."""
    if len(obj) < 0x620:
        raise ValueError("connection object dump is shorter than 0x620 bytes")
    return codec_0420(obj[0x60C:0x620])


def sign_0x85(frame_without_tag: bytes, key: bytes) -> bytes:
    """The client's outgoing-0x85 MAC: HMAC-SHA1(key, whole frame)[:8].

    Derivation (see HANDOFF_20260930_REVERSE_MANUAL.md §5.3 / §5.8):

        0xBA2D90  call 0xBA0420       ; key2 = codec(obj+0x60C) -> 20B
        0xBA2DA1  call 0xC73800       ; HMAC-SHA1 init(key2, 20)
        0xBA2DED  call 0xC73760       ; update(message = edi, len = [ebp-0x384]-8)
        0xBA2E20  call 0xC737A0       ; final -> only the first 8 bytes are kept

    where `edi` spans from the start of the frame's length field to the byte
    before the tag, i.e. `len - 8`.  Confirmed by a byte-exact hit on an
    unmodified client frame:

        key2 = 383b40b2feef5335c7f5bf6dd21c2199fda0364d
        tag  = c12506059d1063c6
    """
    import hashlib
    import hmac

    return hmac.new(key, frame_without_tag, hashlib.sha1).digest()[:8]


# ---------------------------------------------------------------- 会话密钥
# 口径来自 F: 盘那份「已验证能进大厅」的实现(2026-10-05 用本仓库自己的
# 抓包离线复核通过):
#   provider 对象 +0x9C 存的是 AES-128 key schedule, 其前 16 字节就是 AES 密钥;
#   provider 对象 +0x14 是同类中间量, codec_02a0(obj+0x620)[4:20] 都不是密钥。
#   实测: 用 [+0x9C] 前 16 字节解开的客户端 0x85 明文 = 09 00 00 00 86 47 03 09 …
#   (u32 declared | 0x86 | service=0x47 | ver=3 | task=9), 完全符合 DW 任务帧。
_HK_W1 = (2919830337, 4089226047, 3169481240, 3423678985, 4099162642)
_HK_I1 = (7, 17, 14, 16, 9, 19, 13, 0, 2, 3, 4, 8, 1, 10, 11, 5, 18, 6, 12, 15)
_HK_W2 = (2866684544, 4095810571, 938409728, 3457192487, 557642922)
_HK_I2 = (19, 18, 9, 4, 17, 1, 10, 8, 13, 2, 15, 3, 12, 16, 5, 7, 0, 14, 6, 11)


def decode_key(src: bytes, start: int, words, indices) -> bytes:
    """照抄参考实现的 DecodeKey: out[j] = src[start+j] ^ 展开(words)[indices[j]]。"""
    tab = b"".join(struct.pack("<I", w) for w in words)
    return bytes(src[start + j] ^ tab[indices[j]] for j in range(len(indices)))


def read_secrets(path: str) -> dict:
    """读观察器写的 secrets.txt: aes_out/aes_in 直接给, hmac_* 由 40B blob 还原。"""
    d = {}
    if not path:
        return d
    # secrets.txt 要等四个字段同时有效才落盘（实测比客户端第一个任务晚 ~34s），
    # 旁边的 provider_keys.txt 是 4 Hz 高频出口 —— 两个都读，谁先到用谁。
    paths = [path]
    try:
        sibling = os.path.join(os.path.dirname(path), "provider_keys.txt")
        if sibling not in paths:
            paths.append(sibling)
    except Exception:  # noqa: BLE001
        pass
    for p in paths:
        if not os.path.exists(p):
            continue
        try:
            fh = open(p, encoding="utf-8")
        except OSError:
            continue
        with fh:
            for ln in fh:
                ln = ln.strip()
                if not ln:
                    continue
                # 观察器写的是 `key=value`; nt10 写的是 `key value` —— 两种都收。
                if "=" in ln:
                    k, v = ln.split("=", 1)
                elif " " in ln:
                    k, v = ln.split(None, 1)
                else:
                    continue
                v = v.strip()
                if not v:
                    continue
                try:
                    val = bytes.fromhex(v)
                except ValueError:
                    continue
                # 非零值优先：provider_keys.txt 的 aes_in 可能是空/全零
                if val and val != bytes(len(val)):
                    d[k] = val
                else:
                    d.setdefault(k, val)
    blob = d.get("blob")
    if blob and len(blob) >= 40:
        d.setdefault("hmac_out", decode_key(blob, 0, _HK_W1, _HK_I1))
        d.setdefault("hmac_in", decode_key(blob, 20, _HK_W2, _HK_I2))
    # 本 build 实测 p608(+0x9C) 常为 0(接收侧 provider 尚未建立), 而 p604(+0x9C)
    # 是有效密钥。缺 aes_in 时先按同一把密钥回发: 若客户端收发同键则直接可用,
    # 若不同键则这条应答会被丢弃, 但 rx_task 日志仍能记下它要什么。
    for src, dst in (("aes_out", "aes_in"), ("hmac_out", "hmac_in")):
        cur = d.get(dst)
        if d.get(src) and (not cur or cur == bytes(len(cur))):
            d[dst] = d[src]
    return d


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def serialize_file_data(data: bytes) -> bytes:
    """照抄三方 SerializeFileData: tag 0x13 + tag 0x08 + u32 长度 + 原始字节。"""
    return bytes([19, 8]) + struct.pack("<I", len(data)) + data


def _requested_name(plain: bytes):
    """从 10/21、10/12 的请求明文里取文件名。
    实测形态: 10 00 10 <文件名字符串> 00 00"""
    import re as _re
    m = _re.search(rb"[0-9A-Za-z_\-\.]{3,}\.(?:info|json|dat|txt|cfg|result)",
                   plain or b"")
    return m.group(0).decode("ascii", "replace") if m else None


def _read_account() -> dict:
    d = {"Name": "Player", "Level": 70, "Experience": 11056700,
         "Prestige": 4, "CodPoints": 999999, "Gold": 999999}
    try:
        with open(os.path.join(DATA_DIR, "player-account.json"),
                  encoding="utf-8") as f:
            d.update(json.load(f))
    except Exception:
        pass
    return d


def _balance_object(currency: int):
    """照抄 MarketplaceStore.BalanceObject: 03 <currency> 08 <u32 值>。"""
    a = _read_account()
    v = int(a.get("CodPoints", 0)) if currency == 1 else int(a.get("Gold", 0))
    return bytes([3, currency & 0xFF, 8]) + struct.pack("<I", v & 0xFFFFFFFF)


def reply_objects(service: int, task: int, plain: bytes):
    """按 (service, task) 准备应答对象(照抄 F: 盘已验证实现的分派表)。

    参考实现成功的那轮里, 客户端在 71/4、71/10 之后会连发 10/21(发行方配置 x N)、
    8/1、8/2(档案)、80/70 等真实业务任务; 一律回空对象会让它卡在
    EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE。返回 (objects, 说明)。
    """
    if service == 10 and task == 21:                     # 发行方配置
        nm = _requested_name(plain)
        if not nm:
            return [], "名字没解析出来"
        p = os.path.join(DATA_DIR, "publisher_files", os.path.basename(nm))
        if not os.path.exists(p):
            return [], "缺 %s" % nm
        d = open(p, "rb").read()
        return [serialize_file_data(d)], "publisher %s (%d 字节)" % (nm, len(d))
    if service == 10 and task == 12:                     # 用户文件
        nm = _requested_name(plain)
        if not nm:
            return [], "名字没解析出来"
        p = os.path.join(DATA_DIR, "user_files", os.path.basename(nm))
        if not os.path.exists(p):
            return [], "缺 %s" % nm
        d = open(p, "rb").read()
        return [serialize_file_data(d)], "user_file %s (%d 字节)" % (nm, len(d))
    if service == 8 and task in (1, 2):                  # 档案 public / secure
        fn = "public.result" if task == 1 else "secure.result"
        p = os.path.join(DATA_DIR, "player_profiles", fn)
        if not os.path.exists(p):
            return [], "缺 %s" % fn
        d = open(p, "rb").read()
        return [d], "profile %s (%d 字节)" % (fn, len(d))
    if (service == 80 and task == 130) or (service == 93 and task == 1):
        cur = 1 if service == 80 else 2
        return [_balance_object(cur)], "balance currency=%d" % cur
    return [], ""


def decrypt_client_task(frame: bytes, aes_out: bytes, hmac_out: bytes = b""):
    """解一条客户端 0x85。明文 = u32 declared | 0x86 | service | ver | task | payload。"""
    import hashlib
    import hmac as _hmac

    if len(frame) < 34 or len(aes_out) != 16:
        return None
    if frame[4] != 0xAB or frame[5] != 0x85:
        return None
    total = struct.unpack_from("<I", frame, 0)[0]
    body = frame[:4 + total]
    seq = struct.unpack_from("<I", body, 6)[0]
    iv, ct, tag = body[10:26], body[26:-8], body[-8:]
    if not ct or len(ct) % 16:
        return None
    from Crypto.Cipher import AES
    pt = AES.new(aes_out, AES.MODE_CBC, iv).decrypt(ct)
    declared = struct.unpack_from("<I", pt, 0)[0]
    ok = True
    if hmac_out:
        ok = (_hmac.new(hmac_out, body[:-8], hashlib.sha1).digest()[:8] == tag)
    return {
        "seq": seq, "total": total, "hmac_ok": ok, "plain": pt,
        "declared": declared,
        "marker": pt[4] if len(pt) > 4 else 0,
        "service": pt[5] if len(pt) > 5 else 0,
        "ver": pt[6] if len(pt) > 6 else 0,
        "task": pt[7] if len(pt) > 7 else 0,
        "payload": pt[8:8 + max(0, declared - 3)] if declared >= 3 else b"",
    }


def build_task_reply(aes_in: bytes, hmac_in: bytes, seq_out: int, task: int,
                     reply_id: int, status: int = 0, objects=()) -> bytes:
    """DW 任务应答(照抄参考实现 BuildTaskReplyObjects)。

    明文: u32 inner_len | 0x01 | tag10+u64 replyId | tag8+u32 status
          | tag3+u8 task | tag8+u32 对象数 [| tag8+u32 对象数 | 各对象原始字节]
    出站 seq 由调用方维护, 必须**每帧 +1**(不能复用请求 seq)。
    """
    import hashlib
    import hmac as _hmac

    from Crypto.Cipher import AES

    inner = bytearray()
    inner += bytes([10]) + struct.pack("<Q", reply_id)
    inner += bytes([8]) + struct.pack("<I", status)
    inner += bytes([3, task & 0xFF])
    inner += bytes([8]) + struct.pack("<I", len(objects))
    if objects:
        inner += bytes([8]) + struct.pack("<I", len(objects))
        for o in objects:
            inner += o
    n = (5 + len(inner) + 15) // 16 * 16
    plain = bytearray(n)
    struct.pack_into("<I", plain, 0, len(inner))
    plain[4] = 0x01
    plain[5:5 + len(inner)] = inner
    iv = os.urandom(16)
    enc = AES.new(aes_in, AES.MODE_CBC, iv).encrypt(bytes(plain))
    fr = bytearray(26 + len(enc) + 8)
    struct.pack_into("<I", fr, 0, len(fr) - 4)
    fr[4] = 0xAB
    fr[5] = 0x85
    struct.pack_into("<I", fr, 6, seq_out)
    fr[10:26] = iv
    fr[26:26 + len(enc)] = enc
    fr[-8:] = _hmac.new(hmac_in, bytes(fr[:-8]), hashlib.sha1).digest()[:8]
    return bytes(fr)


def build_0x89_inner(inner: int = 1) -> bytes:
    """Inner 0x89 message: the 0x85 handler reads it via 0xBA0FF0.

    0xBA3600 (the 0x89 arm) requires [req+0x644] == 1, which is exactly the
    state the client is in after a successful 0x83 - unlike 0x87, which
    requires 644 == 0 and would fail immediately.
    """
    return build_frame(0x89, struct.pack("<I", inner & 0xFFFFFFFF),
                       frame_len=0x20)


def build_inner16_89() -> bytes:
    """16-byte inner block: u32 len | 0x89 | valid 0xBA0FF0 body | pad."""
    body = bytes([1, 1, 0]) + struct.pack("<H", 0) + struct.pack("<I", 0)
    msg = struct.pack("<I", 1 + len(body)) + bytes([0x89]) + body
    if len(msg) > 16:
        raise ValueError("inner message does not fit in 16 bytes")
    return msg + b"\x00" * (16 - len(msg))


def build_0x85_checksum(v1: int, inner16: bytes, src20: bytes,
                        frame_len: int = 200) -> bytes:
    """Build a server->client 0x85 with a tag made by the verified 0xBA0420 rule.

    The tag is HMAC-SHA1(codec_0420(src20), frame_without_tag)[:8], which is the
    rule the client itself uses on its own outgoing 0x85 (byte-exact hit, see
    HANDOFF_20260930_REVERSE_MANUAL.md §5.8).

    NOTE: whether the client's *receive* path validates an inbound 0x85 with the
    same rule is still unproven.  0xBA3710 uses 0xBA02A0(obj+0x620) as the key
    and hashes `[obj+0xB0]` with length `[obj+0xAC]-4`, so an inbound frame may
    need a different key source.  Keep both builders available and compare.
    """
    if len(inner16) != 16:
        raise ValueError("inner16 must be 16 bytes")
    if len(src20) != 20:
        raise ValueError("src20 must be 20 bytes")
    body = struct.pack("<I", v1 & 0xFFFFFFFF) + inner16
    payload_prefix = bytes([0x00, 0x85]) + body
    pad_len = frame_len - len(payload_prefix) - 8
    if pad_len < 0:
        raise ValueError("frame_len too small for 0x85 + 8-byte tag")
    frame_without_tag = (
        struct.pack("<I", frame_len) + payload_prefix + b"\x00" * pad_len
    )
    tag = sign_0x85(frame_without_tag, codec_0420(src20))
    return frame_without_tag + tag


def build_0x85_receive_side(v1: int, inner16: bytes, src20: bytes,
                            frame_len: int = 200) -> bytes:
    """Server->client 0x85 signed with the RECEIVE-side rule (0xBA02A0 key).

    Kept separate on purpose: which side of the key/table pair the client's
    inbound validator expects is still an open question (§8.2).
    """
    if len(inner16) != 16:
        raise ValueError("inner16 must be 16 bytes")
    if len(src20) != 20:
        raise ValueError("src20 must be 20 bytes")
    body = struct.pack("<I", v1 & 0xFFFFFFFF) + inner16
    payload_prefix = bytes([0x00, 0x85]) + body
    pad_len = frame_len - len(payload_prefix) - 8
    if pad_len < 0:
        raise ValueError("frame_len too small for 0x85 + 8-byte tag")
    frame_without_tag = (
        struct.pack("<I", frame_len) + payload_prefix + b"\x00" * pad_len
    )
    tag = sign_0x85(frame_without_tag, codec_02a0(src20))
    return frame_without_tag + tag


def build_inner_87() -> bytes:
    """Build the stream fragment consumed by the 0x87 arm dispatcher.

    0xBA3A2C reads the cursor value, which is then used as the source offset
    for the opcode read. The arm consumes one more byte and requires value 1.
    """
    return struct.pack("<I", 4) + bytes([0x87, 0x01])


def build_inner_89(flag32: bytes = b"\x00" * 32,
                   payload: bytes = b"",
                   value: int = 0,
                   subtype: int = 1) -> bytes:
    """Build a stream fragment for 0xBA3600 (0x89) -> 0xBA0FF0.

    Reconstructed field by field from 0xBA0FF0:
      u32  cursor   source offset of the opcode (4 for this envelope)
      u8   opcode   == 0x89
      u8   ver      == 1                       (0xBA1057)
      u8   subtype  in {1,2}                   (0xBA1097)
      u8   flag     0 here                     (0xBA10CA)
      32B  field    compared with req+0x648    (0xBA1130 / 0xBA1171)
      u16  len      <= 0x400                   (0xBA11D9)
      u8[] payload                             (0xBA11FE)
      u32  value    -> float/1000 -> +0xAE0    (0xBA121A-0xBA1270)
    """
    if len(flag32) != 32:
        raise ValueError("flag32 must be 32 bytes")
    if len(payload) > 0x400:
        raise ValueError("payload too long")
    # 0xBA0FF0 has two distinct layouts:
    #   subtype == 2 -> ver, subtype, flag, flag32(32B), len(2B), payload, value(4B)
    #                   and flag32 is compared with [req+0x648]
    #   subtype == 1, flag == 0 -> ver, subtype, flag, len(2B), payload, value(4B)
    #                   (0xBA1286: cmp al,1; test cl,cl; je 0xBA11AE)
    # The earlier builder always inserted flag32, which shifted the length
    # field for the subtype==1 path and made 0xBA0FF0 fail.
    if subtype == 1:
        # 0xBA10CA..0xBA10D6: if flag(C) != 0 then subtype must be 2;
        # 0xBA1286: with subtype==1, test flag; je 0xBA11AE; flag!=0 -> fail.
        # So subtype==1 requires flag == 0 and takes the short path at 0xBA11AE.
        body = (bytes([0x01, 0x01, 0x00]) +
                struct.pack("<H", len(payload)) + payload +
                struct.pack("<I", value & 0xFFFFFFFF))
    else:
        body = (bytes([0x01, subtype & 0xFF, 0x00]) + flag32 +
                struct.pack("<H", len(payload)) + payload +
                struct.pack("<I", value & 0xFFFFFFFF))
    return struct.pack("<I", 4) + bytes([0x89]) + body


def build_0x85_server_cbc(v1: int, src20: bytes,
                          frame_len: int = 386,
                          iv: bytes = b"\x00" * 16,
                          aes_key: bytes = b"",
                          inner: bytes = b"",
                          zero_keys: bool = False,
                          len_field: int = -1,
                          pad_after_tag: int = 0) -> bytes:
    """Server->client 0x85 with the inner message AES-CBC encrypted.

    The inner dispatcher (0xBA3AE6 / 0xBA3B0E) reads the cursor DWORD, then
    branches on the plaintext byte at that source offset. The outer opcode
    stays 0x85.

    pad_after_tag appends N bytes AFTER the 8-byte tag. The client splits
    frames by the length field, so the extra bytes are not consumed here;
    the point is to make the client's own recorded frame size
    ([obj+0xAC]) larger than the length field, which is what the
    0xBA3AC2 check `frame_len + cursor <= obj+0xAC` needs.
    """
    from Crypto.Cipher import AES

    if len(src20) != 20:
        raise ValueError("src20 must be 20 bytes")
    if len(iv) != 16:
        raise ValueError("iv must be 16 bytes")
    key20 = codec_02a0(src20)
    # The 16-byte AES key is NOT key20[:0x10]: the observer dump shows the live
    # p608.key equals codec_02A0(src620)[4:20] byte for byte, e.g.
    #   codec_02A0(bac753082cab680bb05ef0d48f1993addd7ddd1d)
    #     = 9bfbac03 d889860b22803e7ea8b38f595d6dfc2a
    #   p608.key =          d889860b22803e7ea8b38f595d6dfc2a
    # Using [0:16] (the old manual value) shifts the key by 4 bytes and makes
    # every inbound frame fail the 0xBA3A15 provider check.
    if zero_keys:
        # With --force-p608-zero-key the client's RECEIVE side uses an all-zero
        # AES key, and its HMAC key is likewise zero.  Using the derived key
        # here (the previous behaviour) guaranteed a mismatch.
        key = bytes(16)
        hmac_key = bytes(20)
    else:
        key = aes_key if len(aes_key) == 16 else key20[4:20]
        hmac_key = key20
    inner_len = frame_len - 2 - 4 - 16 - 8
    if inner_len <= 5 or inner_len % 16 != 0:
        raise ValueError("frame_len cannot hold a CBC inner block")
    if len(inner) > inner_len:
        raise ValueError("inner message does not fit in frame")
    plaintext = inner + b"\x00" * (inner_len - len(inner))
    ciphertext = AES.new(key, AES.MODE_CBC, iv).encrypt(plaintext)
    body = struct.pack("<I", v1 & 0xFFFFFFFF) + iv + ciphertext
    # The client's 0xBA3AC2 check is:  frame_len_field + cursor <= obj+0xAC.
    # Our own frame_len (382) makes that fail, so the arm never runs.  Allow
    # the wire length field to differ from the actual frame size.
    wire_len = frame_len if len_field < 0 else (len_field & 0xFFFFFFFF)
    frame_without_tag = struct.pack("<I", wire_len) + bytes([0x00, 0x85]) + body
    tag = sign_0x85(frame_without_tag, hmac_key)
    return frame_without_tag + tag + (b"\x00" * max(0, pad_after_tag))


def serve_handshake(conn: socket.socket, peer, path: str,
                    magic: int, token: int, echo_source: str,
                    ready_file: str = "", ready_timeout: float = 45.0,
                    echo_file: str = "", follow_84: bool = False,
                    follow_84_value: int = 0, follow_85: bool = False,
                    follow_85_v1: int = 0, key_file: str = "",
                    follow_85_rule: str = "send",
                    follow_85_cbc: bool = False,
                    follow_85_aes_key: str = "",
                    follow_85_aes_key_file: str = "",
                    follow_85_rand_iv: bool = False,
                    follow_85_delay: float = 0.0,
                    follow_85_wait_flag: str = "",
                    reply_85_cbc: bool = False,
                    reply_85_aes_key: str = "",
                    reply_85_aes_key_file: str = "",
                    reply_85_zero_keys: bool = False,
                    reply_85_len_field: int = -1,
                    reply_85_pad_after_tag: int = 0,
                    reply_85_rand_iv: bool = False,
                    reply_85_seqs: str = "1",
                    reply_85_arm_first: bool = False,
                    frame_len: int = 200, split_83_84: bool = False,
                    keepalive4: bytes = b"",
                    keepalive4_every: float = 0.0,
                    hold_after_83: float = 0.0,
                    serve_delay: float = 0.0,
                    seq_after_83: str = "",
                    seq_after_81: str = "",
                    pre81_drain: float = 0.0,
                    echo_85: bool = False,
                    echo_85_rule: str = "send",
                    echo_85_inner89: bool = False,
                    echo_85_keep_type: bool = False,
                    session_file: str = "",
                    reply_85_task: bool = False,
                    secrets_file: str = "",
                    wait_keys_max: float = 0.0,
                    use_out_keys: bool = False) -> None:
    """Drive the 0x81 -> client 0x82 -> 0x83 handshake.

    The 8 bytes that 0x83 must echo are generated by the *client's own* send
    path (0xBA1EF2 -> 0xBA13D0, stored at [req+0x5FC] by 0xBA1F3C, then written
    into the outgoing frame).  The server therefore cannot invent them; it must
    read them out of the frame the client sends back (0x82, 153 bytes,
    starting 95 00 00 00 ab 82 ...).

    When ready_file is set, the observer is forcing [req+0x5E8] 1 -> 2 and we
    must not send 0x81 before that write lands.  Run 20260928_231932 proved the
    race is real: the 0x81 frame was already inside the reader buffer at the
    moment the state byte flipped, and the handler ran against the stale
    sub-state (C8 went 1 -> 4 with 5E8 reset to 0).
    """
    if serve_delay > 0:
        # Delay the whole handshake so the client's per-frame processing
        # happens AFTER the observer's patches.  Measured: a patch written
        # before ~40 s makes the process exit at ~50 s, so the two events
        # must be ordered patch-first / frame-processing-second.
        log(path, {"event": "serve_delay_start", "peer": list(peer),
                   "seconds": serve_delay})
        time.sleep(serve_delay)
        log(path, {"event": "serve_delay_done", "peer": list(peer)})
    conn.settimeout(20.0)
    log(path, {"event": "accept", "peer": list(peer), "mode": "handshake"})
    total = bytearray()
    sent_81 = False
    sent_83 = False
    frame81 = b""
    echo_key = None

    def read_echo_file(timeout: float) -> bytes:
        """Wait for the observer to publish [req+0x5FC] as hex.

        The 8 bytes 0x83 must echo are NOT the ones carried in the client's
        0x82 frame: the client re-derives/rewrites [req+0x5FC] afterwards
        (run 20260929_072119: frame tail was 03 86 9a 92 1d 8c 6f eb while
        [req+0x5FC] read 0x3AF232D6 afterwards).  Only the observer can read
        the live comparison buffer, so it writes it out and we consume it.
        """
        if not echo_file:
            return b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if os.path.exists(echo_file):
                    raw = open(echo_file, encoding="ascii").read().strip()
                    if raw:
                        return bytes.fromhex(raw)
            except OSError:
                pass
            # Keep the observer->probe handoff tight: the client can re-write
            # [req+0x644] within a few ms, so a 20 ms poll loses the window.
            time.sleep(0.001)
        return b""

    def read_key_file(path_name: str, timeout: float) -> bytes:
        if not path_name:
            return b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if os.path.exists(path_name):
                    raw = open(path_name, encoding="ascii").read().strip()
                    if raw:
                        data = bytes.fromhex(raw)
                        # 20B for the two MAC key sources, 16B for the
                        # server-side session block used by --echo-85-session-file.
                        if len(data) in (16, 20):
                            return data
            except OSError:
                pass
            time.sleep(0.01)
        return b""

    try:
        while True:
            try:
                chunk = conn.recv(65536)
            except socket.timeout:
                log(path, {"event": "recv_timeout", "peer": list(peer),
                           "total": len(total), "sent81": sent_81,
                           "sent83": sent_83})
                continue
            if not chunk:
                break
            total += chunk
            log(path, {"event": "recv", "peer": list(peer), "len": len(chunk),
                       "hex": hexdump(chunk[:2048]), "total": len(total)})

            if not sent_81:
                # The client's first message on the wire begins with
                # "c8 00 00 00" (u32 200) but only 28 bytes arrive before the
                # server answers.  Drain for a while (without replying) to see
                # whether the client streams the remaining 172 bytes on its
                # own - i.e. whether that u32 really is a frame length.
                if pre81_drain > 0:
                    log(path, {"event": "pre81_drain_start",
                               "peer": list(peer), "seconds": pre81_drain,
                               "total": len(total)})
                    drain_end = time.time() + pre81_drain
                    conn.settimeout(0.25)
                    while time.time() < drain_end:
                        try:
                            more = conn.recv(65536)
                        except socket.timeout:
                            continue
                        except OSError as exc:
                            log(path, {"event": "pre81_drain_error",
                                       "peer": list(peer),
                                       "error": str(exc)})
                            break
                        if not more:
                            log(path, {"event": "pre81_drain_eof",
                                       "peer": list(peer)})
                            break
                        total += more
                        log(path, {"event": "pre81_drain_recv",
                                   "peer": list(peer), "len": len(more),
                                   "hex": hexdump(more[:256]),
                                   "total": len(total)})
                    log(path, {"event": "pre81_drain_done",
                               "peer": list(peer), "total": len(total),
                               "full_hex": hexdump(bytes(total)[:512])})
                    conn.settimeout(20.0)
                if ready_file:
                    deadline = time.time() + ready_timeout
                    while time.time() < deadline:
                        if os.path.exists(ready_file):
                            log(path, {"event": "ready_seen",
                                       "peer": list(peer),
                                       "file": ready_file})
                            break
                        time.sleep(0.05)
                    else:
                        log(path, {"event": "ready_timeout",
                                   "peer": list(peer),
                                   "file": ready_file,
                                   "waited": ready_timeout})
                        break
                frame81 = build_0x81(magic=magic, token=token,
                                     frame_len=frame_len)
                pre_blob = b""
                for step in [s.strip().lower()
                             for s in seq_after_81.split(",") if s.strip()]:
                    if step in ("89", "0x89"):
                        pre_blob += build_0x89(frame_len=frame_len)
                    elif step in ("84", "0x84"):
                        pre_blob += build_0x84(0, frame_len=frame_len)
                    elif step in ("c8", "0xc8"):
                        pre_blob += build_0xC8_magic()
                    else:
                        log(path, {"event": "seq81_unknown",
                                   "peer": list(peer), "step": step})
                try:
                    # The client's first-frame gate (0xBA3853) only accepts a
                    # frame while [req+0x5EC] is still 0.  0x83 success writes
                    # 0x5EC=1, so any 0x89/0x87 meant to advance [req+0x644]
                    # must ride along with 0x81 - not after 0x83.
                    conn.sendall(frame81 + pre_blob)
                except OSError as exc:
                    log(path, {"event": "send_error", "peer": list(peer),
                               "stage": "0x81", "error": str(exc)})
                    break
                sent_81 = True
                log(path, {"event": "sent_81", "peer": list(peer),
                           "len": len(frame81), "hex": hexdump(frame81[:64]),
                           "magic": magic, "token": "%016x" % token,
                           "pre_len": len(pre_blob),
                           "pre": hexdump(pre_blob[:64])})
                continue

            if not sent_83:
                # Preferred source: the observer's live [req+0x5FC] snapshot.
                live8 = read_echo_file(3.0)
                if live8:
                    log(path, {"event": "echo_from_observer",
                               "peer": list(peer),
                               "echo8": hexdump(live8)})
                # Locate the client's 0x82 frame: u32 len | type | 0x82 | body.
                #
                # Two independent historical 0x82 frames (ok_20260928_214622,
                # tk_20260928_215148) are byte-identical over offsets 0..143
                # (95 00 00 00 | ab | 82 | ...), differ over 144..151 and then
                # carry one varying trailer byte at 152.  That is exactly the
                # structure produced by the client's own send path
                # (0xBA1EF2 -> 0xBA13D0(..., 0xD5A4E8, 0x0A, 8B, ...), stored
                # to [req+0x5FC] at 0xBA1F3C and written into the frame).
                #
                # So the value 0x83 must echo is the 8 bytes immediately
                # BEFORE the final byte of the frame - not the first 8 body
                # bytes, and not the 28-byte handshake frame's d2/dc fields.
                echo8 = b""
                echo_off = -1
                blob = bytes(total)
                for i in range(0, max(0, len(blob) - 10)):
                    flen = struct.unpack_from("<I", blob, i)[0]
                    if flen < 12 or flen > 4096 or i + 4 + flen > len(blob):
                        continue
                    if blob[i + 5] != 0x82:
                        continue
                    frame = blob[i:i + 4 + flen]
                    echo_off = len(frame) - 9
                    echo8 = frame[echo_off:echo_off + 8]
                    log(path, {"event": "found_82", "peer": list(peer),
                               "frame_off": i, "frame_len": flen,
                               "frame_tail_hex": hexdump(frame[-12:]),
                               "echo8": hexdump(echo8)})
                    break
                if echo_source == "last8":
                    echo8 = bytes(total)[-8:]
                    echo_off = len(total) - 8
                if live8:
                    echo8 = live8
                    echo_off = -2
                if not echo8:
                    log(path, {"event": "no_credential", "peer": list(peer),
                               "total": len(total)})
                    break
                # ★ 2026-10-05: 客户端在构建/发出 0x82 时就已经派生好会话密钥,
                # 但观察器主循环在 post83 阶段一次迭代要 17~40 s, 密钥文件会
                # 晚于客户端第一个任务(seq=1, 在 0x83 后 ~1 ms 到达)才落盘。
                # 这里在发 0x83 之前等一等, 让 seq=1 也能被立刻应答。
                if reply_85_task and secrets_file:
                    wait_deadline = time.time() + max(0.0, wait_keys_max)
                    waited = 0.0
                    while time.time() < wait_deadline:
                        _sec = read_secrets(secrets_file)
                        if _sec.get("aes_out"):
                            log(path, {
                                "event": "keys_ready_before_83",
                                "peer": list(peer),
                                "waited": round(waited, 2),
                                "aes_out": _sec["aes_out"].hex(),
                            })
                            break
                        time.sleep(0.25)
                        waited = time.time() - (wait_deadline - wait_keys_max)
                    else:
                        log(path, {
                            "event": "keys_wait_timeout",
                            "peer": list(peer),
                            "seconds": wait_keys_max,
                        })
                frame83 = build_0x83(echo8, frame_len=frame_len)
                extra = b""
                extra_name = ""
                if follow_84:
                    if not split_83_84:
                        extra = build_0x84(follow_84_value,
                                           frame_len=frame_len)
                        extra_name = "0x84"

                # The client tears the lobby socket down ~45 ms after a
                # successful 0x83, so any follow-up frame MUST share the same
                # TCP segment (run 20260929_123835 proved a 30 ms gap loses the
                # race: the 0x89 went out at +63 ms, 18 ms after the RST).
                seq_payloads = []
                for step in [s.strip().lower() for s in seq_after_83.split(",")
                             if s.strip()]:
                    if step in ("84", "0x84"):
                        seq_payloads.append(
                            (step, build_0x84(0, frame_len=frame_len)))
                    elif step in ("84echo", "0x84echo"):
                        seq_payloads.append(
                            (step, build_frame(0x84, echo8,
                                               frame_len=frame_len)))
                    elif step in ("89", "0x89"):
                        seq_payloads.append(
                            (step, build_0x89(frame_len=frame_len)))
                    elif step in ("c8", "0xc8"):
                        seq_payloads.append((step, build_0xC8_magic()))
                    else:
                        log(path, {"event": "seq_unknown",
                                   "peer": list(peer), "step": step})
                seq_blob = b"".join(p for _, p in seq_payloads)
                try:
                    conn.sendall(frame83 + extra + seq_blob)
                except OSError as exc:
                    log(path, {"event": "send_error", "peer": list(peer),
                               "stage": "0x83+" + (extra_name or "only"),
                               "error": str(exc)})
                    break
                sent_83 = True
                log(path, {"event": "sent_83", "peer": list(peer),
                           "len": len(frame83), "hex": hexdump(frame83[:64]),
                           "echo_off": echo_off, "echo8": hexdump(echo8)})
                if extra:
                    log(path, {"event": "sent_" + extra_name[2:],
                               "peer": list(peer), "len": len(extra),
                               "hex": hexdump(extra[:64]),
                               "combined": True})
                if keepalive4:
                    time.sleep(0.005)
                    try:
                        conn.sendall(keepalive4)
                        log(path, {"event": "sent_keepalive4",
                                   "peer": list(peer),
                                   "len": len(keepalive4),
                                   "hex": hexdump(keepalive4)})
                    except OSError as exc:
                        log(path, {"event": "send_error",
                                   "peer": list(peer),
                                   "stage": "keepalive4",
                                   "error": str(exc)})
                        break
                # Periodic variant of the same 4-byte keepalive.  The client
                # accepts one 00 00 00 00 right after 0x83 without resetting,
                # so the open question is whether repeating it can cover the
                # ~50 s window in which the lobby otherwise declares loss.
                #
                # This must run on its own timer: the client is silent for most
                # of that window, so a send hooked onto recv would never fire.
                stop_keepalive4 = threading.Event()
                if keepalive4 and keepalive4_every > 0:
                    def keepalive4_loop():
                        while not stop_keepalive4.wait(keepalive4_every):
                            try:
                                conn.sendall(keepalive4)
                                log(path, {"event": "sent_keepalive4_repeat",
                                           "peer": list(peer),
                                           "len": len(keepalive4),
                                           "hex": hexdump(keepalive4),
                                           "sent": time.time()})
                            except OSError as exc:
                                log(path, {"event": "send_error",
                                           "peer": list(peer),
                                           "stage": "keepalive4_repeat",
                                           "error": str(exc)})
                                return
                    threading.Thread(target=keepalive4_loop,
                                     daemon=True).start()
                if follow_84 and split_83_84:
                    # Send 0x84 as a separate frame after a short pause so the
                    # dispatcher has already consumed [req+0x644] for 0x83.
                    time.sleep(0.02)
                    f84 = build_0x84(follow_84_value, frame_len=frame_len)
                    try:
                        conn.sendall(f84)
                        log(path, {"event": "sent_84", "peer": list(peer),
                                   "len": len(f84),
                                   "hex": hexdump(f84[:64]),
                                   "split": True})
                    except OSError as exc:
                        log(path, {"event": "send_error", "peer": list(peer),
                                   "stage": "0x84split", "error": str(exc)})
                        break
                if follow_85:
                    # The client does not reach the lobby protocol until about
                    # T+38 s (c8: 1->2 at 38.6 s, 5e8: 0->3 at 38.69 s).
                    # Sending 0x85 at ~T+0.17 s makes the client reject it and
                    # immediately fire seq=1/2/3 error reports.  Waiting here
                    # also guarantees the observer has already published the
                    # current obj+0x620, so rx.txt is no longer stale.
                    if follow_85_wait_flag:
                        # Wait for the observer to publish the AC edge
                        # ([obj+0xAC] 0 -> 382).  The 0x85 reader at 0xBA3A91
                        # uses that length; sending outside the window makes it
                        # read with length 0 and the dispatch byte is never 0x87.
                        log(path, {"event": "follow_85_wait_flag_start",
                                   "peer": list(peer),
                                   "flag": follow_85_wait_flag})
                        deadline_f = time.time() + 120.0
                        while time.time() < deadline_f:
                            if read_key_file(follow_85_wait_flag, 0.0):
                                break
                            time.sleep(0.01)
                        log(path, {"event": "follow_85_wait_flag_done",
                                   "peer": list(peer),
                                   "found": bool(read_key_file(
                                       follow_85_wait_flag, 0.0))})
                    if follow_85_delay > 0:
                        log(path, {"event": "follow_85_delay_start",
                                   "peer": list(peer),
                                   "seconds": follow_85_delay})
                        deadline85 = time.time() + follow_85_delay
                        while time.time() < deadline85:
                            time.sleep(0.05)
                        log(path, {"event": "follow_85_delay_done",
                                   "peer": list(peer)})
                    src20 = read_key_file(key_file, 0.5)
                    if src20:
                        # Which rule to use is selected by --follow-85-rule:
                        #   send    (default) key = codec_0420(obj+0x60C)
                        #   receive           key = codec_02a0(obj+0x620)
                        # The send rule is the byte-exact verified one; the
                        # receive rule is the untested hypothesis.  The key
                        # file MUST match the rule (tx-file for send, key-file
                        # for receive) or the tag will be wrong on purpose.
                        if follow_85_cbc:
                            if follow_85_aes_key_file:
                                aes_key = read_key_file(
                                    follow_85_aes_key_file, 1.0)
                            else:
                                aes_key = (bytes.fromhex(follow_85_aes_key)
                                           if follow_85_aes_key else b"")
                            extra = build_0x85_server_cbc(
                                follow_85_v1, src20, frame_len=382,
                                aes_key=aes_key, inner=build_inner_87(),
                                iv=os.urandom(16) if follow_85_rand_iv
                                else b"\x00" * 16)
                            extra_2 = build_0x85_server_cbc(
                                follow_85_v1 + 1, src20, frame_len=382,
                                aes_key=aes_key, inner=build_inner_89(),
                                iv=os.urandom(16) if follow_85_rand_iv
                                else b"\x00" * 16)
                            extra = extra + extra_2
                            rule = "receive/codec_02a0+aes-cbc+hmac_sha1"
                            key_used = codec_02a0(src20)
                        elif "send" == follow_85_rule:
                            extra = build_0x85_checksum(
                                follow_85_v1, build_inner16_89(), src20,
                                frame_len=frame_len)
                            rule = "send/codec_0420+hmac_sha1"
                            key_used = codec_0420(src20)
                        else:
                            extra = build_0x85_receive_side(
                                follow_85_v1, build_inner16_89(), src20,
                                frame_len=frame_len)
                            rule = "receive/codec_02a0+hmac_sha1"
                            key_used = codec_02a0(src20)
                        log(path, {"event": "85_tag", "peer": list(peer),
                                   "src20": hexdump(src20),
                                   "key": hexdump(key_used),
                                   "tag": hexdump(extra[-8:]),
                                   "rule": rule})
                    else:
                        extra = build_0x85(follow_85_v1, frame_len=frame_len)
                    try:
                        conn.sendall(extra)
                        log(path, {"event": "sent_85", "peer": list(peer),
                                   "len": len(extra),
                                   "hex": hexdump(extra[:64]),
                                   "keyed": bool(src20)})
                    except Exception as exc:
                        log(path, {"event": "send_error", "peer": list(peer),
                                   "stage": "0x85",
                                   "error": "%s: %s" % (type(exc).__name__,
                                                        exc)})
                        break
                # Hypothesis under test (run 20260929_1156+): the client resets
                # [req+0xC8] to 4 about 31 ms after a successful 0x83 because
                # the probe closes the socket, so 0xC739E0 returns a hard error
                # instead of -2 ("no data yet, keep waiting").  Holding the
                # connection open keeps the read pending and should let the
                # 0xBA34D0 wait loop stay alive.
                if hold_after_83 > 0:
                    log(path, {"event": "hold_after_83", "peer": list(peer),
                               "seconds": hold_after_83})
                    deadline = time.time() + hold_after_83
                    # Persistent across recv() iterations: the 0x87 arm only
                    # needs to succeed once, after which every reply carries
                    # the 0x89 business message.
                    armed = False
                    # reply_85_task: 出站 seq 现改为回显请求 seq(与参考实现一致),
                    # 不再用独立递增计数器。
                    # 观察器主循环在 post83 阶段很慢(17~40s/轮), 密钥文件可能
                    # 晚到。把当轮还解不出的帧缓存下来, 拿到密钥后补答。
                    pending_frames = []
                    while time.time() < deadline:
                        remaining = deadline - time.time()
                        if remaining <= 0:
                            break
                        try:
                            conn.settimeout(min(1.0, remaining))
                            more = conn.recv(65536)
                        except socket.timeout:
                            continue
                        except OSError as exc:
                            log(path, {"event": "hold_recv_error",
                                       "peer": list(peer), "error": str(exc)})
                            break
                        if not more:
                            log(path, {"event": "hold_peer_closed",
                                       "peer": list(peer)})
                            break
                        total += more
                        log(path, {"event": "hold_recv", "peer": list(peer),
                                   "len": len(more),
                                   "hex": hexdump(more[:512]),
                                   "total": len(total)})
                        # Echo experiment: the client sends 0x85 frames and
                        # expects a matching reply (its [req+0x5EC] recv
                        # counter only advances when the seq matches).  The
                        # exact checksum needs the bignum provider behind
                        # 0xC77E90, so instead of reimplementing it we send
                        # the client's own frame straight back: the seq is
                        # then correct by construction.
                        if echo_85:
                            off_e = 0
                            while off_e + 6 <= len(more):
                                f_len = int.from_bytes(more[off_e:off_e + 4],
                                                       "little")
                                if f_len < 6 or off_e + 4 + f_len > len(more):
                                    break
                                f_op = more[off_e + 5]
                                if f_op == 0x85:
                                    frame = more[off_e:off_e + 4 + f_len]
                                    # Direction matters: a client->server frame
                                    # carries type 0xAB, a server->client frame
                                    # carries type 0x00.  Echoing the frame
                                    # verbatim (the earlier experiment) sent the
                                    # wrong type AND kept the client's own tag,
                                    # so it could never be accepted.
                                    reply = bytearray(frame)
                                    if not echo_85_keep_type:
                                        reply[4] = 0x00
                                    if echo_85_inner89:
                                        # Keep the client's outer frame/seq (so
                                        # the 0x5EC gate passes), but replace its
                                        # 16-byte request block with the expected
                                        # 0x89 inner message and re-sign below.
                                        reply[10:26] = build_inner16_89()
                                    if session_file:
                                        # Fill the 16-byte block with the
                                        # client's own server-side session value
                                        # ([obj+0x608]+0x14).  For a server->client
                                        # frame this is the value the client
                                        # expects to see echoed back, unlike its
                                        # own request block.
                                        # The observer publishes this file a few
                                        # ms after 5E8 flips; wait briefly so we
                                        # never substitute an all-zero value.
                                        sess = b""
                                        # The session value can appear well
                                        # after the first client 0x85; the
                                        # client's own retry window is ~47 s,
                                        # so 20 s is safe.
                                        deadline = time.time() + 20.0
                                        while time.time() < deadline:
                                            cand = read_key_file(session_file, 0.05)
                                            if len(cand) == 16 and cand != b"\x00" * 16:
                                                sess = cand
                                                break
                                            time.sleep(0.01)
                                        if len(sess) == 16:
                                            reply[10:26] = sess
                                            log(path, {
                                                "event": "echo_85_session",
                                                "peer": list(peer),
                                                "session16": hexdump(sess),
                                            })
                                    if echo_key is None:
                                        raw_key = read_key_file(key_file, 0.5)
                                        if raw_key:
                                            echo_key = (
                                                codec_0420(raw_key)
                                                if echo_85_rule == "send"
                                                else codec_02a0(raw_key))
                                            log(path, {
                                                "event": "echo_85_key",
                                                "peer": list(peer),
                                                "src20": hexdump(raw_key),
                                                "key": hexdump(echo_key),
                                                "rule": echo_85_rule,
                                            })
                                    if echo_key is not None:
                                        reply[-8:] = sign_0x85(
                                            bytes(reply[:-8]), echo_key)
                                    if echo_key is None:
                                        log(path, {
                                            "event": "echo_85_no_key",
                                            "peer": list(peer),
                                            "seq": more[off_e + 6]
                                                   if off_e + 7 <= len(more)
                                                   else None,
                                            "rule": echo_85_rule,
                                            "key_file": key_file,
                                        })
                                        off_e += 4 + f_len
                                        continue
                                    try:
                                        conn.sendall(bytes(reply))
                                        log(path, {
                                            "event": "echo_85",
                                            "peer": list(peer),
                                            "seq": more[off_e + 6]
                                                   if off_e + 7 <= len(more)
                                                   else None,
                                            "len": len(reply),
                                            "rule": echo_85_rule,
                                            "rewrapped": True,
                                            "inner89": echo_85_inner89,
                                            "keep_type": echo_85_keep_type,
                                            "keyed": echo_key is not None,
                                            "tail8": hexdump(reply[-8:]),
                                            "hex": hexdump(reply[:64]),
                                        })
                                    except OSError as exc:
                                        log(path, {
                                            "event": "echo_85_error",
                                            "peer": list(peer),
                                            "error": str(exc)})
                                        break
                        elif reply_85_task:
                            # ★ F: 盘已验证路径: 解客户端 DW 任务帧, 按
                            #   `u32 len | 01 | TLV` 回任务应答。
                            sec = read_secrets(secrets_file)
                            off_t = 0
                            while off_t + 10 <= len(more):
                                f_len = int.from_bytes(more[off_t:off_t + 4],
                                                       "little")
                                if (f_len < 10 or
                                        off_t + 4 + f_len > len(more)):
                                    break
                                if more[off_t + 5] == 0x85:
                                    frame = more[off_t:off_t + 4 + f_len]
                                    d = None
                                    if sec.get("aes_out"):
                                        try:
                                            d = decrypt_client_task(
                                                frame, sec["aes_out"],
                                                sec.get("hmac_out", b""))
                                        except Exception:  # noqa: BLE001
                                            d = None
                                    log(path, {
                                        "event": "rx_task",
                                        "peer": list(peer),
                                        "seq": int.from_bytes(frame[6:10],
                                                              "little"),
                                        "hmac_ok": bool(d and d["hmac_ok"]),
                                        "marker": d["marker"] if d else None,
                                        "service": d["service"] if d else None,
                                        "task": d["task"] if d else None,
                                        "declared": d["declared"] if d else None,
                                        # 128->512: 71/3 UserWarning 与 71/7
                                        # ComError 的 Address Fail 位置在
                                        # payload 中段, 48 字节根本看不到。
                                        "payload_head": (hexdump(
                                            d["payload"][:512]) if d else ""),
                                        "payload_text": (d["payload"][:512]
                                                         .decode("utf-8",
                                                                 "replace")
                                                         if d else ""),
                                        "have_aes_out": bool(
                                            sec.get("aes_out")),
                                        "have_aes_in": bool(sec.get("aes_in")),
                                    })
                                    if d and sec.get("aes_in"):
                                        if use_out_keys:
                                            rk_aes = sec.get("aes_out")
                                            rk_hmac = sec.get("hmac_out", b"")
                                        else:
                                            rk_aes = sec.get("aes_in")
                                            rk_hmac = sec.get("hmac_in", b"")
                                        # ★ 照抄 F: 盘已验证实现: 应答的 seq **回显
                                        # 请求 seq**, reply_id 才用独立计数器。
                                        # 参考日志里 seq 与 replyId 在 1:1 时相同,
                                        # 但语义上前者是回显、后者是自增。
                                        objs, note = reply_objects(
                                            d.get("service", 0),
                                            d.get("task", 0),
                                            d.get("payload", b""))
                                        rep = build_task_reply(
                                            rk_aes, rk_hmac,
                                            d["seq"], d["task"], d["seq"],
                                            0, objs)
                                        try:
                                            conn.sendall(rep)
                                            log(path, {
                                                "event": "tx_task_reply",
                                                "peer": list(peer),
                                                "reply_id": d["seq"],
                                                "seq": d["seq"],
                                                "service": d.get("service"),
                                                "task": d["task"],
                                                "objects": len(objs),
                                                "note": note,
                                                "len": len(rep),
                                                "hex": hexdump(rep[:64]),
                                            })
                                        except OSError as exc:
                                            log(path, {
                                                "event": "tx_task_error",
                                                "error": str(exc)})
                                            break
                                    elif not sec.get("aes_out"):
                                        if frame not in pending_frames:
                                            pending_frames.append(frame)
                                off_t += 4 + f_len
                            # 密钥到位后补答积压帧(seq=1 常常在这里才被答上)。
                            if pending_frames and sec.get("aes_out"):
                                for fr in list(pending_frames):
                                    try:
                                        dd = decrypt_client_task(
                                            fr, sec["aes_out"],
                                            sec.get("hmac_out", b""))
                                    except Exception:  # noqa: BLE001
                                        dd = None
                                    if not dd:
                                        continue
                                    pending_frames.remove(fr)
                                    log(path, {
                                        "event": "rx_task_late",
                                        "peer": list(peer),
                                        "seq": dd["seq"],
                                        "service": dd["service"],
                                        "task": dd["task"],
                                        "hmac_ok": dd["hmac_ok"],
                                    })
                                    if not sec.get("aes_in"):
                                        continue
                                    # 与主路径一致: seq 回显, 并按任务分派真实数据。
                                    objs, note = reply_objects(
                                        dd.get("service", 0),
                                        dd.get("task", 0),
                                        dd.get("payload", b""))
                                    rep = build_task_reply(
                                        sec["aes_in"],
                                        sec.get("hmac_in", b""),
                                        dd["seq"], dd["task"], dd["seq"],
                                        0, objs)
                                    try:
                                        conn.sendall(rep)
                                        log(path, {
                                            "event": "tx_task_reply",
                                            "peer": list(peer),
                                            "reply_id": dd["seq"],
                                            "seq": dd["seq"],
                                            "service": dd.get("service"),
                                            "task": dd["task"],
                                            "objects": len(objs),
                                            "note": note,
                                            "len": len(rep),
                                            "late": True,
                                        })
                                    except OSError as exc:
                                        log(path, {
                                            "event": "tx_task_error",
                                            "error": str(exc)})
                                        break
                        elif reply_85_cbc:
                            # Answer every client 0x85 with a server-side CBC
                            # frame carrying the same sequence.
                            off_r = 0
                            while off_r + 10 <= len(more):
                                f_len = int.from_bytes(more[off_r:off_r + 4],
                                                       "little")
                                if (f_len < 10 or
                                        off_r + 4 + f_len > len(more)):
                                    break
                                if more[off_r + 5] == 0x85:
                                    frame = more[off_r:off_r + 4 + f_len]
                                    seq = int.from_bytes(frame[6:10], "little")
                                    allowed = set()
                                    for part in reply_85_seqs.split(","):
                                        part = part.strip()
                                        if part:
                                            try:
                                                allowed.add(int(part, 0))
                                            except ValueError:
                                                pass
                                    if allowed and seq not in allowed:
                                        off_r += 4 + f_len
                                        continue
                                    src20 = read_key_file(key_file, 0.5)
                                    if src20:
                                        rk = (bytes.fromhex(reply_85_aes_key)
                                              if reply_85_aes_key else b"")
                                        if reply_85_aes_key_file:
                                            live = read_key_file(
                                                reply_85_aes_key_file, 0.3)
                                            if len(live) == 16:
                                                rk = live
                                        # 0xBA3600 (the 0x89 handler) requires
                                        # [req+0x644] == 1, which is only set
                                        # by a successful 0xBA3590 (0x87) arm.
                                        # So the first reply must arm, and only
                                        # then may a 0x89 business frame follow.
                                        if reply_85_arm_first and not armed:
                                            inner = build_inner_87()
                                            inner_tag = "87"
                                        else:
                                            inner = build_inner_89()
                                            inner_tag = "89"
                                        reply = build_0x85_server_cbc(
                                            seq, src20, frame_len=382,
                                            len_field=reply_85_len_field,
                                            pad_after_tag=reply_85_pad_after_tag,
                                            aes_key=rk, inner=inner,
                                            iv=(os.urandom(16)
                                                if reply_85_rand_iv
                                                else b"\x00" * 16),
                                            zero_keys=reply_85_zero_keys)
                                        try:
                                            conn.sendall(reply)
                                            if reply_85_arm_first:
                                                armed = True
                                            log(path, {
                                                "event": "reply_85_cbc",
                                                "peer": list(peer),
                                                "seq": seq,
                                                "len": len(reply),
                                                "inner": inner_tag,
                                                "hex": hexdump(reply[:64]),
                                            })
                                        except OSError as exc:
                                            log(path, {
                                                "event": "reply_85_error",
                                                "error": str(exc)})
                                            break
                                off_r += 4 + f_len
                    log(path, {"event": "hold_done", "peer": list(peer),
                               "total": len(total)})
                stop_keepalive4.set()
    except OSError as exc:
        log(path, {"event": "conn_error", "peer": list(peer),
                   "error": str(exc)})
    finally:
        log(path, {"event": "close", "peer": list(peer), "total": len(total),
                   "sent81": sent_81, "sent83": sent_83,
                   "full_hex": hexdump(total[:8192])})
        try:
            conn.close()
        except OSError:
            pass


def serve_conn(conn: socket.socket, peer, path: str, reply: bytes,
               hold: bool = True, repeat_every: float = 0.0) -> None:
    conn.settimeout(20.0)
    log(path, {"event": "accept", "peer": list(peer)})
    total = bytearray()
    next_repeat = time.time() + repeat_every if repeat_every > 0 else 0.0
    try:
        while True:
            if repeat_every > 0 and reply and time.time() >= next_repeat:
                # 0xBA20A0 keeps the session alive only while server frames keep
                # arriving; with a single reply the client drops the lobby ~50 s
                # later with "与大厅服务失去连接".
                try:
                    conn.sendall(reply)
                    log(path, {"event": "repeat_sent", "peer": list(peer),
                               "len": len(reply), "hex": hexdump(reply[:64])})
                except OSError as exc:
                    log(path, {"event": "repeat_error", "peer": list(peer),
                               "error": str(exc)})
                    break
                next_repeat = time.time() + repeat_every
            try:
                chunk = conn.recv(65536)
            except socket.timeout:
                # The client treats a dead lobby channel as fatal a short while
                # later, so keep the socket open across idle periods and just
                # note them.  Closing here produced the "致命错误" dialog.
                log(path, {"event": "recv_timeout", "peer": list(peer),
                           "total": len(total), "holding": hold})
                if not hold:
                    break
                continue
            if not chunk:
                break
            total += chunk
            log(path, {"event": "recv", "peer": list(peer),
                       "len": len(chunk), "hex": hexdump(chunk[:2048]),
                       "total": len(total)})
            if reply:
                try:
                    conn.sendall(reply)
                    log(path, {"event": "sent", "peer": list(peer),
                               "len": len(reply), "hex": hexdump(reply[:512])})
                except OSError as exc:
                    log(path, {"event": "send_error", "peer": list(peer),
                               "error": str(exc)})
    except OSError as exc:
        log(path, {"event": "conn_error", "peer": list(peer),
                   "error": str(exc)})
    finally:
        log(path, {"event": "close", "peer": list(peer), "total": len(total),
                   "full_hex": hexdump(total[:8192])})
        try:
            conn.close()
        except OSError:
            pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bind", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8445)
    ap.add_argument("--log", default="")
    ap.add_argument("--reply-hex", default="",
                    help="hex bytes to send back after each received chunk")
    ap.add_argument("--repeat-every", type=float, default=0.0,
                    help="also re-send the reply every N seconds")
    ap.add_argument("--lobby-handshake", action="store_true",
                    help="drive the 0x81 -> client 0x82 -> 0x83 handshake "
                         "instead of sending a fixed --reply-hex frame")
    ap.add_argument("--magic", type=lambda s: int(s, 0), default=0xD2,
                    help="0x81 magic u32 (must be in [0xD2,0xDC])")
    ap.add_argument("--token", type=lambda s: int(s, 0),
                    default=0x1122334455667788,
                    help="0x81 u64 token")
    ap.add_argument("--echo-source", choices=["frame", "last8"],
                    default="frame",
                    help="where the 0x83 echo is taken from")
    ap.add_argument("--ready-file", default="",
                    help="wait for this file before sending 0x81")
    ap.add_argument("--ready-timeout", type=float, default=45.0,
                    help="seconds to wait for --ready-file")
    ap.add_argument("--echo-file", default="",
                    help="observer-published 8-byte [req+0x5FC] hex")
    ap.add_argument("--follow-84", action="store_true",
                    help="also send opcode 0x84 after a successful 0x83")
    ap.add_argument("--follow-84-value", type=lambda s: int(s, 0), default=0,
                    help="u32 payload for the 0x84 frame")
    ap.add_argument("--follow-85", action="store_true",
                    help="also send opcode 0x85 after a successful 0x83")
    ap.add_argument("--follow-85-cbc", action="store_true",
                    help="with --follow-85: AES-CBC-encrypt the inner 0x87 "
                         "message using the receive-side key "
                         "(codec_02a0(obj+0x620)) and a 386-byte frame")
    ap.add_argument("--follow-85-aes-key", default="",
                    help="with --follow-85-cbc: 16-byte hex AES key taken from "
                         "the live p608 provider object ([p608+0x14])")
    ap.add_argument("--follow-85-aes-key-file", default="",
                    help="with --follow-85-cbc: observer-published p608 key")
    ap.add_argument("--follow-85-rand-iv", action="store_true",
                    help="with --follow-85-cbc: give the two initial 0x85 "
                         "frames a random IV instead of all-zero (the client "
                         "rejects a zero 16-byte block within 1 ms)")
    ap.add_argument("--follow-85-wait-flag", default="",
                    help="with --follow-85: wait until this file exists before "
                         "sending (the observer writes it on the [obj+0xAC] "
                         "0->382 edge)")
    ap.add_argument("--follow-85-delay", type=float, default=0.0,
                    help="with --follow-85: wait this many seconds before "
                         "sending, so the client is already in lobby state")
    ap.add_argument("--reply-85-cbc", action="store_true",
                    help="reply to every inbound client 0x85 with a "
                         "server-side CBC frame carrying the same seq")
    ap.add_argument("--reply-85-aes-key", default="",
                    help="16-byte hex AES key for --reply-85-cbc")
    ap.add_argument("--reply-85-aes-key-file", default="",
                    help="with --reply-85-cbc: file the observer keeps "
                         "rewriting with the LIVE p608 key (+0x14, 16B)")
    ap.add_argument("--reply-85-len-field", type=lambda s: int(s, 0),
                    default=-1,
                    help="override the u32 length field written into reply "
                         "0x85 frames (client checks field + cursor <= "
                         "obj+0xAC, so 382 always fails)")
    ap.add_argument("--reply-85-pad-after-tag", type=lambda s: int(s, 0),
                    default=0,
                    help="with --reply-85-cbc: append N zero bytes AFTER the "
                         "8-byte tag, so the client's own recorded frame size "
                         "exceeds the length field and the 0xBA3AC2 check "
                         "frame_len + cursor <= obj+0xAC can pass")
    ap.add_argument("--reply-85-zero-keys", action="store_true",
                    help="with --reply-85-cbc: build the reply with an "
                         "all-zero AES key and all-zero HMAC key, matching a "
                         "client whose p608 was overwritten by "
                         "--force-p608-zero-key")
    ap.add_argument("--reply-85-rand-iv", action="store_true",
                    help="with --reply-85-cbc: generate a random 16-byte IV "
                         "instead of the all-zero default (the client's own "
                         "frames carry a random-looking IV)")
    ap.add_argument("--reply-85-seqs", default="1",
                    help="comma list of client seq values to answer with "
                         "--reply-85-cbc")
    ap.add_argument("--reply-85-arm-first", action="store_true",
                    help="with --reply-85-cbc: send the 0x87 arm before the "
                         "first 0x89 business reply (required because "
                         "0xBA3600 needs [+0x644]==1)")
    ap.add_argument("--reply-85-task", action="store_true",
                    help="reply to every inbound client 0x85 with the DW "
                         "task envelope (u32 len | 01 | TLV), decrypting the "
                         "request and signing/encrypting the reply with the "
                         "keys from --secrets-file (provider +0x9C)")
    ap.add_argument("--secrets-file", default="",
                    help="observer-written secrets.txt carrying aes_out/"
                         "aes_in (provider +0x9C) and the 40B blob used to "
                         "derive hmac_out/hmac_in")
    ap.add_argument("--wait-keys-max", type=float, default=0.0,
                    help="with --reply-85-task: wait up to N seconds for the "
                         "provider keys to appear before sending 0x83, so the "
                         "client's first task (seq=1) can be answered at once")
    ap.add_argument("--reply-85-out-keys", action="store_true",
                    help="with --reply-85-task: sign+encrypt the reply with the "
                         "verified send-side pair (aes_out/hmac_out) instead of "
                         "aes_in/hmac_in")
    ap.add_argument("--follow-85-v1", type=lambda s: int(s, 0), default=0,
                    help="u32 payload for the 0x85 frame")
    ap.add_argument("--key-file", default="",
                    help="observer-published 20-byte source matching "
                         "--follow-85-rule: tx-file (obj+0x60C) for 'send', "
                         "key-file (obj+0x620) for 'receive'")
    ap.add_argument("--follow-85-rule", choices=["send", "receive"],
                    default="send",
                    help="which verified/hypothesised rule signs the follow-up "
                         "0x85: 'send' uses codec_0420(obj+0x60C) (byte-exact "
                         "against a recorded client frame), 'receive' uses "
                         "codec_02a0(obj+0x620) (untested)")
    ap.add_argument("--frame-len", type=int, default=200,
                    help="u32 frame_len written into every server frame")
    ap.add_argument("--split-83-84", action="store_true",
                    help="send 0x84 as a separate frame after 0x83")
    ap.add_argument("--keepalive4", default="",
                    help="hex bytes sent as a 4-byte packet after 0x83")
    ap.add_argument("--keepalive4-every", type=float, default=0.0,
                    help="repeat --keepalive4 every N seconds after 0x83")
    ap.add_argument("--serve-delay", type=float, default=0.0,
                    help="wait this many seconds after accept before "
                         "driving the handshake (moves the client's frame "
                         "processing later in time)")
    ap.add_argument("--hold-after-83", type=float, default=0.0,
                    help="keep the lobby socket open N seconds after 0x83")
    ap.add_argument("--echo-85", action="store_true",
                    help="echo every 0x85 frame the client sends back to it "
                         "(seq matches by construction; tests whether the "
                         "recv counter just needs a reply)")
    ap.add_argument("--echo-85-rule", choices=["send", "receive"],
                    default="send",
                    help="key used when re-wrapping an echoed 0x85: 'send' "
                         "uses codec_0420(obj+0x60C), 'receive' uses "
                         "codec_02a0(obj+0x620).  Requires --key-file.")
    ap.add_argument("--echo-85-inner89", action="store_true",
                    help="with --echo-85: keep the client's outer frame and "
                         "seq (passes the 0x5EC gate) but replace the 16-byte "
                         "request block with the expected 0x89 inner message, "
                         "then re-sign the 8-byte tag")
    ap.add_argument("--echo-85-keep-type", action="store_true",
                    help="with --echo-85: keep the client's original frame "
                         "type (0xAB) instead of rewriting it to 0x00; test "
                         "only the MAC/key variable in isolation")
    ap.add_argument("--echo-85-session-file", default="",
                    help="with --echo-85: 16-byte hex file holding the "
                         "client's server-side session value "
                         "([obj+0x608]+0x14); its contents replace the 16-byte "
                         "block of the reply")
    ap.add_argument("--seq-after-83", default="",
                    help="comma list of follow-up frames after 0x83: "
                         "84,84echo,89,c8")
    ap.add_argument("--seq-after-81", default="",
                    help="comma list of frames bundled with 0x81 (they are "
                         "seen while [req+0x5EC] is still 0): 89,84,c8")
    ap.add_argument("--pre81-drain", type=float, default=0.0,
                    help="seconds to keep receiving BEFORE answering 0x81, "
                         "to capture the full client first frame")
    a = ap.parse_args()
    reply = bytes.fromhex(a.reply_hex) if a.reply_hex else b""

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((a.bind, a.port))
    srv.listen(16)
    log(a.log, {"event": "listen", "bind": a.bind, "port": a.port,
                "pid": __import__("os").getpid()})
    try:
        while True:
            conn, peer = srv.accept()
            if a.lobby_handshake:
                threading.Thread(target=serve_handshake,
                                 args=(conn, peer, a.log, a.magic, a.token,
                                       a.echo_source, a.ready_file,
                                       a.ready_timeout, a.echo_file,
                                       a.follow_84, a.follow_84_value,
                                       a.follow_85, a.follow_85_v1,
                                       a.key_file, a.follow_85_rule,
                                       a.follow_85_cbc,
                                       a.follow_85_aes_key,
                                       a.follow_85_aes_key_file,
                                       a.follow_85_rand_iv,
                                       a.follow_85_delay,
                                       a.follow_85_wait_flag,
                                       a.reply_85_cbc,
                                       a.reply_85_aes_key,
                                       a.reply_85_aes_key_file,
                                       a.reply_85_zero_keys,
    a.reply_85_len_field,
    a.reply_85_pad_after_tag,
                                       a.reply_85_rand_iv,
                                       a.reply_85_seqs,
                                       a.reply_85_arm_first,
                                       a.frame_len,
                                       a.split_83_84,
                                       bytes.fromhex(a.keepalive4)
                                       if a.keepalive4 else b"",
                                       a.keepalive4_every,
                                       a.hold_after_83,
                                       a.serve_delay,
                                       a.seq_after_83,
                                       a.seq_after_81,
                                       a.pre81_drain,
                                       a.echo_85,
                                       a.echo_85_rule,
                                       a.echo_85_inner89,
                                       a.echo_85_keep_type,
                                       a.echo_85_session_file,
                                       a.reply_85_task,
                                       a.secrets_file,
                                       a.wait_keys_max,
                                       a.reply_85_out_keys),
                                 daemon=True).start()
            else:
                threading.Thread(target=serve_conn,
                                 args=(conn, peer, a.log, reply, True,
                                       a.repeat_every),
                                 daemon=True).start()
    except KeyboardInterrupt:
        pass
    finally:
        srv.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
