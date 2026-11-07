"""Independently parse the TDR schema embedded in the client EXE.

Verifies the claim "GDPOpenProtocol.tdr is inside the client and is plaintext"
by locating its magic 0x000B02D6 in the on-disk image and dumping the
surrounding string table. This is DATA-section evidence only.
"""
import struct
import sys

import pefile

sys.stdout.reconfigure(encoding="utf-8")

EXE = "COD OL/codoMP_client_shipRetail.exe"
TDR = "COD OL/GDPOpenProtocol.tdr"
MAGIC = 0x000B02D6


def main():
    import hashlib

    if __import__("os").path.exists(TDR):
        blob = open(TDR, "rb").read()
        print("standalone TDR: %s" % TDR)
        print("size: %d" % len(blob))
        print("sha256: %s" % hashlib.sha256(blob).hexdigest())
        print("first 32 bytes: %s" % blob[:32].hex())
        for key in (
            b"GDP_Open_Protocol",
            b"GDPPkgHead",
            b"GDP_CODOL_COMMAND",
            b"TGDPCODOLCmd",
            b"GDP_CF_NOTIFY_GAMESERVERPORTINFO",
            b"GDP_CF_REQ_ENTERSERVER",
            b"GDP_CMD_TDR_HELLO",
            b"GDP_PROTOCOL_VERSION",
        ):
            print(
                "   %-38s offset %s"
                % (
                    key.decode("latin-1"),
                    hex(blob.find(key)) if blob.find(key) >= 0 else "NONE",
                )
            )
        print()

    pe = pefile.PE(EXE, fast_load=True)
    pe.parse_data_directories()
    image_base = pe.OPTIONAL_HEADER.ImageBase

    hits = []
    for section in pe.sections:
        raw = section.get_data()
        name = section.Name.rstrip(b"\x00").decode("latin-1")
        needle = struct.pack("<I", MAGIC)
        idx = 0
        while True:
            idx = raw.find(needle, idx)
            if idx < 0:
                break
            hits.append((name, image_base + section.VirtualAddress + idx))
            idx += 1

    print("magic 0x%08X hits: %d" % (MAGIC, len(hits)))
    for name, va in hits:
        print("   section=%-8s VA=0x%08X" % (name, va))

    # The embedded .tdr is a data blob; locate its containing section and read
    # a bounded window so we can confirm the schema name pool is present.
    for name, va in hits:
        rva = va - image_base
        blob = pe.get_data(rva, 0x60000)
        print()
        print("---- window at 0x%08X (section %s), %d bytes ----" % (va, name, len(blob)))
        for key in (
            b"GDP_Open_Protocol",
            b"GDPPkgHead",
            b"GDP_CODOL_COMMAND",
            b"TGDPCODOLCmd",
            b"GDP_CF_NOTIFY_GAMESERVERPORTINFO",
            b"GDP_CF_REQ_ENTERSERVER",
            b"GDP_CMD_TDR_HELLO",
            b"GDP_PROTOCOL_VERSION",
        ):
            idx = blob.find(key)
            print(
                "   %-38s %s"
                % (
                    key.decode("latin-1"),
                    "VA 0x%08X" % (va + idx) if idx >= 0 else "not in window",
                )
            )


if __name__ == "__main__":
    main()
