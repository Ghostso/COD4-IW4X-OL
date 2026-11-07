"""Endpoint / protocol archaeology from the on-disk (unencrypted) image.

Scope discipline: the .tp3 code section is encrypted on disk, so this tool
only reports DATA-section evidence (strings, HTTP header names, JSON keys,
format templates) and the raw 4-byte pointer references to them. Any code
claim requires a decrypted runtime image and is explicitly NOT made here.
"""
import os
import struct
import sys

import pefile

sys.stdout.reconfigure(encoding="utf-8")

EXE = "COD OL/codoMP_client_shipRetail.exe"
OUT = "分析/01_string_anchors.csv"

ANCHORS = [
    # --- config / ini ---
    b"dwauth.ini",
    b"stun.ini",
    b"buildconfig.ini",
    b"iips.ini",
    b"enable_iips=%d",
    b"iips_url=%s",
    b"cacert.pem",
    # --- endpoints / URL templates ---
    b"https://%s:%d/auth/",
    b"https://%s/",
    b"%s://%s:%d/%s/title/%d/queue/%d/member/%llu",
    b"%s://%s:%d/%s/title/%d/queue/%d",
    b"https",
    b"v1.0",
    b"CODOL/1.0",
    # --- dw ticket / auth protocol ---
    b"lsg_server_ticket",
    b"lsg_server_ticket_size",
    b"iv_seed",
    b"DW-Ticket-Seed",
    b"DW-Client-Ticket",
    b"DW-Client-Ticket-Size",
    b"DW-Server-Ticket",
    b"DW-Server-Ticket-Size",
    b"auth_task",
    b"ciphertext",
    b"server_ticket",
    b"client_ticket",
    # --- json response fields ---
    b"extended_data",
    b"license_id",
    b"user_id",
    b"time_to_live",
    b"cd_key",
    b"application/json",
    b"Content-Type",
    b"Transfer-Encoding",
    # --- state names ---
    b"dwLogonStart",
    b"DW_DNS_ERROR",
    b"DW_DNS_COMPLETE",
    b"DW_ACCOUNT_ERROR",
    b"DW_ACCOUNT_LOGIN_COMPLETE",
    b"DW_LOBBY_ERROR",
    b"DW_LOBBY_CONNECTED",
    b"DW_LOGON_ERROR",
    b"DWLOGON_REGISTERCODOID_COMPLETE",
    # --- lobby / blaze ---
    b"bdLobbyErrorCode",
    b"BD_LOBBY_PROTOCOL_VERSION_FAILURE",
    b"BD_LOBBY_INTERNAL_FAILURE",
    b"BD_MAX_ERROR_CODE",
    b"Unknown bdLobbyErrorCode",
    # --- services named ---
    b"ied-tqos.qq.com",
    b"cod4master.activision.com",
    b"stun.eu.demonware.net",
    b"stun.us.demonware.net",
    b"stun.jp.demonware.net",
    b"stun.au.demonware.net",
    b"codol.qq.com",
    # --- http verbs / api ---
    b"matchmaking",
    b"pooledstorage",
    b"messaging",
    b"profiles",
    b"storage",
    b"teams_list",
    b"createteam",
]


def find_ascii(blob, needle):
    hits, start = [], 0
    while True:
        idx = blob.find(needle, start)
        if idx < 0:
            return hits
        hits.append(idx)
        start = idx + 1


def main():
    pe = pefile.PE(EXE, fast_load=True)
    pe.parse_data_directories()
    image_base = pe.OPTIONAL_HEADER.ImageBase

    rows = []
    for anchor in ANCHORS:
        wide = anchor.decode("latin-1").encode("utf-16-le")
        for section in pe.sections:
            raw = section.get_data()
            sec = section.Name.rstrip(b"\x00").decode("latin-1")
            for kind, needle in (("ascii", anchor), ("utf16", wide)):
                for idx in find_ascii(raw, needle):
                    va = image_base + section.VirtualAddress + idx
                    ptr = struct.pack("<I", va)
                    # count 4-byte references anywhere in the file
                    refs = []
                    for s2 in pe.sections:
                        raw2 = s2.get_data()
                        s2name = s2.Name.rstrip(b"\x00").decode("latin-1")
                        for r in find_ascii(raw2, ptr):
                            refs.append(
                                (s2name, image_base + s2.VirtualAddress + r)
                            )
                    rows.append(
                        {
                            "anchor": anchor.decode("latin-1"),
                            "encoding": kind,
                            "section": sec,
                            "va": va,
                            "refs": refs,
                        }
                    )

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("anchor|encoding|section|va|ref_count|refs\n")
        for row in rows:
            fh.write(
                "%s|%s|%s|0x%08X|%d|%s\n"
                % (
                    row["anchor"].replace("|", "\\|"),
                    row["encoding"],
                    row["section"],
                    row["va"],
                    len(row["refs"]),
                    ";".join(
                        "%s@0x%08X" % (s, v) for s, v in row["refs"][:12]
                    ),
                )
            )

    for row in rows:
        print(
            "%-46s %-5s %-8s VA=0x%08X refs=%d %s"
            % (
                row["anchor"],
                row["encoding"],
                row["section"],
                row["va"],
                len(row["refs"]),
                ["%s@0x%08X" % (s, v) for s, v in row["refs"][:4]],
            )
        )
    print()
    print("total anchors recorded: %d -> %s" % (len(rows), OUT))


if __name__ == "__main__":
    main()
