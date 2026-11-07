#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Closed-loop verification for client → server 0x85 (send-side) using the
exact same run-batch data.

Steps implemented
-----------------
1. BA0420 (second codec) – derives the 20-byte HMAC-SHA1 key from
   `obj + 0x60D` using the hard-coded permutation table.
2. Reads the *temporary* source stream that BA2A60 uses (sampled by the
   read-only observer) and reproduces the message pointer / length exactly
   as the original code does:
       B9BB90  ->  B9BBB0  ->  B962E0
3. Feeds the key + message into the same keyed-SHA1 helper chain
   (C73800 / C73760 / C737A0) – here re-implemented with hashlib.
4. Compares **only the last 8 bytes** of the resulting digest with the
   last 8 bytes of the real 0x85 frame captured on the wire.

The script is completely offline – it only needs the three blobs that the
observer records for a single 0x85 emission:

    • connection_object   – the whole connection object (at least +0x60D … +0x630)
    • stream_object       – the stream object that BA2A60 receives in ecx
    • frame_0x85          – the complete 0x85 frame the client actually sent

All three blobs can be dumped with a one-liner in the observer, e.g.:

    observer.dump(obj_ptr, 0x640)          # connection object
    observer.dump(stream_ptr, 0x200)       # stream object (covers +0x0C … +0x40)
    observer.dump(frame_ptr, frame_len)    # 0x85 frame

The script prints "MATCH" / "MISMATCH" and the two 8-byte values for
manual inspection.
"""

import sys
import struct
import hashlib
from pathlib import Path
from typing import Tuple

# ----------------------------------------------------------------------
# 1️⃣  BA0420 – second codec (24‑byte output, we keep the first 20 bytes)
# ----------------------------------------------------------------------
# permutation table extracted from the binary (index order used by BA0420)
_BA0420_INDEX = [
    0x07, 0x11, 0x0E, 0x10, 0x09, 0x13, 0x0D, 0x00,
    0x02, 0x03, 0x04, 0x08, 0x01, 0x0A, 0x0B, 0x05,
    0x12, 0x06, 0x0C, 0x0F
]

# constant table (6 dwords = 24 bytes) – taken from 0xBA044C … 0xBA0468
_BA0420_CONST = bytes.fromhex(
    "90 f5 42 ad e6 21 a4 88 02 89 c9 3b dc 02 ff 39 "
    "ff 77 04 11 0d 62 88 ee"
)  # 24 bytes


def ba0420(source: bytes) -> bytes:
    """
    Re-implementation of BA0420.

    Parameters
    ----------
    source: bytes
        24‑byte region starting at `obj + 0x60D` (exactly 0x18 bytes).
        The function only reads the first 20 bytes (5 dwords) – the
        remaining 4 bytes are never used.

    Returns
    -------
    bytes
        24‑byte buffer; caller should take `[:20]` as the HMAC‑SHA1 key.
    """
    if len(source) < 0x18:
        raise ValueError("source must be at least 0x18 bytes")
    # BA0420 works on 4‑byte words; we treat the source as 5 dwords (20 bytes)
    src_words = struct.unpack("<5I", source[:20])
    const_words = struct.unpack("<6I", _BA0420_CONST)

    out = bytearray(24)
    # The algorithm: for each of the 20 output positions take the
    # corresponding constant word and XOR the source word selected by
    # the permutation table (mod 5 because only 5 source words exist).
    for i, idx in enumerate(_BA0420_INDEX):
        const_word = const_words[i]
        src_word = src_words[idx % 5]
        val = const_word ^ src_word
        struct.pack_into("<I", out, i * 4, val)
    return bytes(out)
# ----------------------------------------------------------------------
# 2️⃣  Stream helper – reproduces B9BB90 / B9BBB0 / B962E0
# ----------------------------------------------------------------------
def stream_message_ptr_and_len(stream: bytes) -> Tuple[int, int]:
    """
    Given the *entire* stream object (at least 0x40 bytes), compute the
    exact message pointer (`edi`) and length (`[ebp-0x384]-8`) that the
    original code uses.

    Offsets (verified from the disassembly):
        +0x0C  – buffer base pointer (relative to stream object)
        +0x1C  – current write offset (absolute)
        +0x20  – buffer size (or end offset)
        +0x24  – window limit set by B9BB90 (min(requested, 0x1F))

    The original sequence:
        B9BB90:  stream[+0x24] = min(requested, 0x1F)
        B9BBB0:  edi = stream[+0x1C] - stream[+0x24] + 0x1F
        B962E0:  validates that the byte at `edi` is 0x1F (header)

    Length used in C73760 is `[ebp-0x384] - 8`.  In the live run the value
    of `[ebp-0x384]` equals `stream[+0x20] - stream[+0x1C] + 0x1F`
    (i.e. remaining bytes in the window including the 0x1F header).
    Therefore `len = (stream[+0x20] - stream[+0x1C] + 0x1F) - 8`.
    """
    if len(stream) < 0x40:
        raise ValueError("stream blob too small (<0x40)")

    # little-endian 32‑bit reads
    buf_base   = struct.unpack_from("<I", stream, 0x0C)[0]
    write_off  = struct.unpack_from("<I", stream, 0x1C)[0]
    buf_end    = struct.unpack_from("<I", stream, 0x20)[0]
    win_limit  = struct.unpack_from("<I", stream, 0x24)[0]  # already min(...,0x1F)

    # message pointer (edi) – absolute address inside the stream buffer
    msg_ptr = write_off - win_limit + 0x1F

    # length fed to C73760  (= [ebp-0x384] - 8)
    remaining = buf_end - write_off + 0x1F
    msg_len   = remaining - 8

    return msg_ptr, msg_len


# ----------------------------------------------------------------------
# 3️⃣  Keyed‑SHA1 (C73800 / C73760 / C737A0) – pure Python
# ----------------------------------------------------------------------
def keyed_sha1(key20: bytes, message: bytes, length: int) -> bytes:
    """
    Mirrors the three calls:
        C73800(ctx, key20, 0x14)
        C73760(ctx, message, length)
        C737A0(ctx, out, 8)   ← we only need the first 8 bytes
    """
    h = hashlib.sha1()
    h.update(key20)          # init with key (HMAC‑like, but the binary does a plain keyed hash)
    h.update(message[:length])
    return h.digest()[:8]    # C737A0 writes only 8 bytes into the frame
# ----------------------------------------------------------------------
# 4️⃣  Main verification routine
# ----------------------------------------------------------------------
def verify(conn_obj_path: Path, stream_obj_path: Path, frame_path: Path) -> bool:
    # 1️⃣ load blobs
    conn_obj = conn_obj_path.read_bytes()
    stream_obj = stream_obj_path.read_bytes()
    frame = frame_path.read_bytes()

    # 2️⃣ derive key from connection object (+0x60D, 0x18 bytes)
    src_for_ba0420 = conn_obj[0x60D:0x60D + 0x18]
    key24 = ba0420(src_for_ba0420)
    key20 = key24[:20]

    # 3️⃣ compute message pointer & length from stream object
    msg_ptr, msg_len = stream_message_ptr_and_len(stream_obj)

    # The message lives *inside* the stream buffer.  The observer gave us the
    # whole stream object, whose buffer starts at `stream_obj + 0x??`.  The
    # original code uses an absolute address (`edi`).  Because we only have a
    # dumped copy, we reconstruct the buffer relative to the stream object:
    #   buffer_base = stream_obj + offset_of_buffer_in_dump
    # The dump we ask the observer to take starts at the stream object
    # itself, so the buffer base relative to the dump is the value read at
    # +0x0C **minus** the stream object address.  Since we don't know the
    # original address, we cheat: the observer also dumps the first 0x40
    # bytes of the *buffer* (as requested in the instructions).  We'll
    # assume the observer saved the buffer immediately after the stream
    # object in the same file – adjust if your dump layout differs.
    #
    # Simpler: ask the observer to dump the *buffer region* separately.
    # For this script we expect a fourth file `stream_buffer.bin` placed
    # next to the stream object dump.
    buffer_path = stream_obj_path.with_name("stream_buffer.bin")
    if not buffer_path.exists():
        raise FileNotFoundError(
            f"Expected stream buffer dump at {buffer_path}. "
            "Ask the observer to dump `stream+0x0C` (size 0x40)."
        )
    stream_buffer = buffer_path.read_bytes()

    # Convert absolute `msg_ptr` to offset inside our buffer dump.
    # The original `buf_base` (stream+0x0C) is the absolute address of the
    # buffer start.  Our dump starts at that address, so:
    buf_base = struct.unpack_from("<I", stream_obj, 0x0C)[0]
    offset_in_buffer = msg_ptr - buf_base
    if offset_in_buffer < 0 or offset_in_buffer + msg_len > len(stream_buffer):
        raise ValueError("Computed message range falls outside dumped buffer")

    message = stream_buffer[offset_in_buffer: offset_in_buffer + msg_len]

    # 4️⃣ compute keyed‑SHA1 (first 8 bytes)
    calc_tag8 = keyed_sha1(key20, message, msg_len)

    # 5️⃣ real tag = last 8 bytes of the captured 0x85 frame
    real_tag8 = frame[-8:]

    print(f"Calculated tag8 : {calc_tag8.hex()}")
    print(f"Captured  tag8 : {real_tag8.hex()}")

    if calc_tag8 == real_tag8:
        print("✅ MATCH – send-side 0x85 verified")
        return True
    else:
        print("❌ MISMATCH")
        return False


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            "Usage: python verify_0x85_send.py "
            "<connection_object.bin> <stream_object.bin> <frame_0x85.bin>"
        )
        sys.exit(1)

    ok = verify(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
    sys.exit(0 if ok else 1)