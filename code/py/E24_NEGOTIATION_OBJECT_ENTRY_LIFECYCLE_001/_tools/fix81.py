from pathlib import Path
base=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001")
for fn in ["E24_HANDSHAKE_OPCODE_DIRECTION_MATRIX.md"]:
    p=base/fn; t=p.read_text(encoding="utf-8")
    t=t.replace("`0x6AB655`（`mov byte ptr [ebp-0x171], 0x81`，在 `0x6AB310` 内组装应答）","`0x6AB66D`（`mov byte ptr [ebp-0x171], 0x81`，在 `0x6AB310` 内组装应答）")
    p.write_text(t,encoding="utf-8"); print("fixed",fn)
