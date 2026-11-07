"""Direct xref scan over a decrypted 32-bit runtime image.

This reports only concrete instruction-level references:
  * direct call/jmp target
  * immediate operand (push/mov/cmp/etc) equal to a target VA

No semantic inference is made here; results feed evidence cards in the report.
"""
import json
import sys

import capstone

sys.stdout.reconfigure(encoding="utf-8")

BASE = 0x400000
CODE_START = 0x401000
CODE_END = 0xCA8000

TARGETS = {
    "AUTH_0xB991A0": 0xB991A0,
    "AUTH_0xB983F0": 0xB983F0,
    "AUTH_parser_0xBA9BC0": 0xBA9BC0,
    "AUTH_parser_0xB9A470": 0xB9A470,
    "AUTH_result_0xB983B0": 0xB983B0,
    "AUTH_http_0xB99090": 0xB99090,
    "AUTH_tls_0xB9A100": 0xB9A100,
    "DW_state_get_0x7F25B0": 0x7F25B0,
    "DW_state_pump_0x7F26C0": 0x7F26C0,
    "DW_account_0x7F28F0": 0x7F28F0,
    "DW_lobby_0x7F3800": 0x7F3800,
    "DW_connect_0x7F2B90": 0x7F2B90,
    "DW_dns_0x7F34E0": 0x7F34E0,
    "DW_dns_worker_0x7F3600": 0x7F3600,
    "DW_cfg_0x7E98F0": 0x7E98F0,
    "AUTH_str_0xD5A228": 0xD5A228,
    "AUTH_url_0xD5A2CC": 0xD5A2CC,
    "AUTH_host_0x81A76A8": 0x81A76A8,
    "AUTH_port_0x81A9EC4": 0x81A9EC4,
    "AUTH_field1_0x81A7F34": 0x81A7F34,
    "AUTH_hex5_0x81A9EB8": 0x81A9EB8,
    "TICKET_name_0xD5A0E8": 0xD5A0E8,
    "TICKET_size_0xD5A0FC": 0xD5A0FC,
    "IV_SEED_0xD5A114": 0xD5A114,
    "STATE_DW_DNS_ERROR_0xDE08D8": 0xDE08D8,
    "STATE_DW_DNS_COMPLETE_0xDE08E8": 0xDE08E8,
    "STATE_DW_ACCOUNT_ERROR_0xDE08F8": 0xDE08F8,
    "STATE_DW_ACCOUNT_LOGIN_COMPLETE_0xDE090C": 0xDE090C,
    "STATE_DW_LOBBY_ERROR_0xDE0928": 0xDE0928,
    "STATE_DW_LOBBY_CONNECTED_0xDE0938": 0xDE0938,
}


def main():
    path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else "分析/02_runtime_xrefs.json"
    blob = open(path, "rb").read()
    code = blob[CODE_START - BASE:CODE_END - BASE]

    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    md.skipdata = True
    hits = {name: [] for name in TARGETS}

    count = 0
    for ins in md.disasm(code, CODE_START):
        count += 1
        for name, target in TARGETS.items():
            matched = False
            kind = None
            try:
                ops = ins.operands
            except capstone.CsError:
                ops = []
            try:
                is_control = ins.group(capstone.CS_GRP_CALL) or ins.group(
                    capstone.CS_GRP_JUMP
                )
            except capstone.CsError:
                is_control = False
            if ops and ops[0].type == capstone.x86.X86_OP_IMM:
                if ops[0].imm & 0xFFFFFFFF == target and is_control:
                    matched = True
                    kind = "control"
            for op in ops[1:] if is_control else ops:
                if op.type == capstone.x86.X86_OP_IMM:
                    if op.imm & 0xFFFFFFFF == target:
                        matched = True
                        kind = kind or "immediate"
            if matched:
                hits[name].append(
                    {
                        "from": ins.address,
                        "kind": kind,
                        "text": "%s %s" % (ins.mnemonic, ins.op_str),
                    }
                )

    print("instructions disassembled: %d" % count)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "image": path,
                "base": hex(BASE),
                "code_range": [hex(CODE_START), hex(CODE_END)],
                "targets": {name: hex(va) for name, va in TARGETS.items()},
                "hits": hits,
            },
            fh,
            indent=2,
            ensure_ascii=False,
        )

    for name in TARGETS:
        rows = hits[name]
        print("%-36s 0x%08X refs=%d" % (name, TARGETS[name], len(rows)))
        for row in rows[:12]:
            print(
                "    from 0x%08X %-9s %s"
                % (row["from"], row["kind"], row["text"])
            )
        if len(rows) > 12:
            print("    ...")
    print("written:", out)


if __name__ == "__main__":
    main()
