from __future__ import annotations

"""Throwaway CORE-010 pre-check: verify the static facts before they are baked
into the CORE-010 bootstrap contract. Read-only; no binary modification."""

import hashlib
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXE = ROOT / "COD OL" / "codoMP_client_shipRetail.exe"


class Image:
    def __init__(self, blob: bytes) -> None:
        self.blob = blob
        self.pe = struct.unpack_from("<I", blob, 0x3C)[0]
        assert blob[self.pe : self.pe + 4] == b"PE\0\0"
        coff = self.pe + 4
        (self.machine,) = struct.unpack_from("<H", blob, coff)
        (self.nsections,) = struct.unpack_from("<H", blob, coff + 2)
        (self.opt_size,) = struct.unpack_from("<H", blob, coff + 16)
        self.opt = coff + 20
        (self.magic,) = struct.unpack_from("<H", blob, self.opt)
        (self.entry_rva,) = struct.unpack_from("<I", blob, self.opt + 16)
        (self.image_base,) = struct.unpack_from("<I", blob, self.opt + 28)
        (self.size_of_image,) = struct.unpack_from("<I", blob, self.opt + 56)
        (self.subsystem,) = struct.unpack_from("<H", blob, self.opt + 68)
        self.ddir = self.opt + (96 if self.magic == 0x10B else 112)
        self.sections: list[tuple[str, int, int, int]] = []
        sec = self.opt + self.opt_size
        for i in range(self.nsections):
            off = sec + i * 40
            name = blob[off : off + 8].rstrip(b"\0").decode("latin-1")
            vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", blob, off + 8)
            self.sections.append((name, vaddr, vsize, rawptr, rawsize))

    def rva_to_off(self, rva: int) -> int | None:
        for name, vaddr, vsize, rawptr, rawsize in self.sections:
            if vaddr <= rva < vaddr + max(vsize, rawsize):
                return rawptr + (rva - vaddr)
        return None

    def read_rva(self, rva: int, size: int) -> bytes:
        off = self.rva_to_off(rva)
        assert off is not None, hex(rva)
        return self.blob[off : off + size]

    def directory(self, index: int) -> tuple[int, int]:
        return struct.unpack_from("<II", self.blob, self.ddir + index * 8)


def main() -> int:
    blob = EXE.read_bytes()
    print("size            ", len(blob))
    print("sha256          ", hashlib.sha256(blob).hexdigest().upper())
    img = Image(blob)
    print("machine         ", hex(img.machine), "sections", img.nsections, "magic", hex(img.magic))
    print("subsystem       ", img.subsystem)
    print("imagebase       ", hex(img.image_base), "entry_rva", hex(img.entry_rva))
    print("entry bytes     ", img.read_rva(img.entry_rva, 8).hex(" ").upper())
    for name, vaddr, vsize, rawptr, rawsize in img.sections:
        print(f"  section {name:<8} va={vaddr:#010x} vsize={vsize:#010x} raw={rawsize:#010x}")

    # IAT slot value
    slot_va = img.image_base + 0x0E5DC665
    print("slot va         ", hex(slot_va))
    off = img.rva_to_off(0x0E5DC665)
    print("slot value      ", hex(struct.unpack_from("<I", blob, off)[0]))

    # imports
    imp_rva, imp_size = img.directory(1)
    print("import dir      ", hex(imp_rva), imp_size)
    count = 0
    cur = imp_rva
    names = []
    while True:
        off = img.rva_to_off(cur)
        desc = blob[off : off + 20]
        if len(desc) < 20 or desc == b"\0" * 20:
            break
        (orig,) = struct.unpack_from("<I", desc)
        (name_rva,) = struct.unpack_from("<I", desc, 12)
        (first,) = struct.unpack_from("<I", desc, 16)
        noff = img.rva_to_off(name_rva)
        end = blob.index(b"\0", noff)
        names.append((blob[noff:end].decode("latin-1"), hex(orig), hex(first)))
        count += 1
        cur += 20
    print("import descs    ", count, names)

    # relocations: does any reloc target the IAT slot VA?
    rel_rva, rel_size = img.directory(5)
    hits = 0
    total = 0
    if rel_rva:
        cur = rel_rva
        end = rel_rva + rel_size
        while cur < end:
            off = img.rva_to_off(cur)
            page, blocksize = struct.unpack_from("<II", blob, off)
            if blocksize == 0:
                break
            n = (blocksize - 8) // 2
            for i in range(n):
                (entry,) = struct.unpack_from("<H", blob, off + 8 + i * 2)
                total += 1
                va = img.image_base + page + (entry & 0x0FFF)
                if va == slot_va:
                    hits += 1
            cur += blocksize
    print("relocs          ", total, "slot reloc hits", hits)

    # absolute operand scan for the tracked globals
    patterns = {
        "0x0849413B": bytes.fromhex("3B414908"),
        "0x0849B500": bytes.fromhex("00B54908"),
        "0x0849B501": bytes.fromhex("01B54908"),
        "0x08189FEC": bytes.fromhex("EC9F1808"),
        "0x0196928C": bytes.fromhex("8C929601"),
        "0x01969290": bytes.fromhex("90929601"),
        "0x00CA827C": bytes.fromhex("7C82CA00"),
    }
    for label, pat in patterns.items():
        idx = []
        start = 0
        while True:
            p = blob.find(pat, start)
            if p < 0:
                break
            idx.append(p - 4)  # file offset of the operand start
            start = p + 1
        print(f"operand {label}: {len(idx)} sites at file offsets", [hex(i) for i in idx])

    # fall-through zero span after the Entry call
    eoff = img.rva_to_off(img.entry_rva)
    span = 0
    while blob[eoff + 6 + span] == 0 and span < 0x4000:
        span += 1
    print("zero span after entry", span)

    # ASCII presence of the gate tokens and axis strings
    for token in [b"-src=tgp", b"-qa", b"-q", b"WIN_NO_TCLS", b"stun1-tub.codol.qq.com", b"iips.dll"]:
        print("token", token, blob.find(token))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())