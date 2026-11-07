"""Export every in-match array-element layout reachable through 0xDA9330.

Evidence:
    run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin

The type table has 24 entries (type ids 0..23).  Entries that point at the
same table are aliases.  Every distinct table is 64 records long, retained
verbatim; index 63 may be a sentinel/special value for some layouts.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

BASE = 0x400000
TYPE_TABLE = 0xDA9330
TYPE_COUNT = 24
FIELD_COUNT = 64

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DUMP = ROOT.parent / "run_codol_001" / "runs" / "OMIT_RETEST_20261022" / "mem" / "mem_005.bin"
DEFAULT_OUT = ROOT / "docs" / "INMATCH_ARRAY_ELEMENT_VARIANTS_20261023.md"


def read_dump(path: Path) -> bytes:
    data = path.read_bytes()
    if len(data) <= TYPE_TABLE - BASE:
        raise ValueError(f"dump is too short: {len(data)}")
    return data


def get_bytes(data: bytes, va: int, size: int) -> bytes:
    off = va - BASE
    if off < 0 or off + size > len(data):
        raise ValueError(f"VA 0x{va:08X} outside dump")
    return data[off:off + size]


def get_u32(data: bytes, va: int) -> int:
    return struct.unpack_from("<I", get_bytes(data, va, 4))[0]


def get_i32(data: bytes, va: int) -> int:
    return struct.unpack_from("<i", get_bytes(data, va, 4))[0]


def load_table(data: bytes, address: int, count: int = FIELD_COUNT):
    result = []
    for index in range(count):
        raw = get_bytes(data, address + index * 12, 12)
        offset, bits, hint = struct.unpack("<Iii", raw)
        result.append({"index": index, "offset": offset, "bits": bits, "hint": hint})
    return result


def load_type_map(data: bytes):
    rows = []
    for type_id in range(TYPE_COUNT):
        address = get_u32(data, TYPE_TABLE + type_id * 8)
        max_index = get_i32(data, TYPE_TABLE + type_id * 8 + 4)
        rows.append({"type": type_id, "table": address, "max_index": max_index})
    return rows


def validate_layout(name: str, rows) -> None:
    if len(rows) != FIELD_COUNT:
        raise ValueError(f"{name}: expected {FIELD_COUNT} fields, got {len(rows)}")

    # The first 63 entries are normal netField_t records.  Index 63 is
    # retained verbatim because some layouts store a sentinel/special value.
    prefix = rows[:FIELD_COUNT - 1]
    offsets = [row["offset"] for row in prefix]
    if len(set(offsets)) != len(offsets):
        raise ValueError(f"{name}: duplicate offsets in first 63 entries")
    if max(offsets) > 0x4000:
        raise ValueError(f"{name}: prefix offset out of range")
    for row in prefix:
        bits = row["bits"]
        if bits == 0:
            continue
        if 1 <= bits <= 32:
            continue
        if -128 <= bits <= -1:
            continue
        raise ValueError(f"{name}: invalid bits={bits} at index {row['index']}")


def build_layouts(data: bytes):
    type_map = load_type_map(data)
    if len(type_map) != TYPE_COUNT:
        raise ValueError("bad type table length")

    layouts = []
    by_address = {}
    for row in type_map:
        address = row["table"]
        if address not in by_address:
            entry = {
                "address": address,
                "max_index": row["max_index"],
                "types": [],
                "fields": load_table(data, address, FIELD_COUNT),
            }
            validate_layout(f"0x{address:08X}", entry["fields"])
            by_address[address] = entry
            layouts.append(entry)
        entry = by_address[address]
        entry["types"].append(row["type"])
        if entry["max_index"] != row["max_index"]:
            raise ValueError(f"0x{address:08X}: inconsistent max_index")

    return type_map, layouts


def fmt_signed_hex(value: int) -> str:
    if value < 0:
        return f"-0x{-value:X}"
    return f"0x{value:X}"


def render(data: bytes, dump_path: Path) -> str:
    type_map, layouts = build_layouts(data)
    lines = []
    lines.append("# CODOL 3.19 对局内数组元素布局（全部）")
    lines.append("")
    lines.append(f"> 证据：`{dump_path.as_posix()}`")
    lines.append("> ImageBase：`0x400000`；条目格式：`struct netField_t { uint32 offset; int32 bits; uint32 hint; }`，12 字节。")
    lines.append("> `bits > 0`：无符号位宽；`bits == 0`：浮点 codec；`bits < 0` 且命中 codec 集：专用 codec；其余负数：有符号整数。")
    lines.append("")
    lines.append("## 范围")
    lines.append("")
    lines.append("- `0xDA9330` 是 `{ table_ptr, max_index }[24]` 的数组元素类型表，类型号为 0–23。")
    lines.append("- 每项 `max_index=0x3F`，对应索引 0–63，共 64 项。")
    lines.append("- 按 `table_ptr` 去重后共有 18 张不同布局；同一布局的类型号列在每节标题和别名表中。")
    lines.append("- 第 64 项（`index=63`）按原始三元组保留，不做语义裁剪；某些布局的末项可能是哨兵/特殊值。")
    lines.append("")
    lines.append("## 类型表与别名")
    lines.append("")
    lines.append("| Type | Table | Max | 相同布局的其它类型 |")
    lines.append("|---:|---|---:|---|")
    by_address = {entry["address"]: entry for entry in layouts}
    for row in type_map:
        same = [str(x) for x in by_address[row["table"]]["types"] if x != row["type"]]
        same_text = ", ".join(same) if same else "-"
        lines.append(f"| {row['type']} | `0x{row['table']:08X}` | `0x{row['max_index']:X}` | {same_text} |")
    lines.append("")

    for layout_index, layout in enumerate(layouts):
        address = layout["address"]
        types = layout["types"]
        type_text = ", ".join(str(x) for x in types)
        rows = layout["fields"]
        summary = {
            "zero": sum(1 for row in rows if row["bits"] == 0),
            "positive": sum(1 for row in rows if row["bits"] > 0),
            "negative": sum(1 for row in rows if row["bits"] < 0),
        }
        tail = rows[-1]
        lines.append(f"## Layout {layout_index}  `0x{address:08X}`")
        lines.append("")
        lines.append(f"- Types：`{type_text}`；字段数：`{FIELD_COUNT}`；indexBits：`6`；`max_index=0x{layout['max_index']:X}`。")
        lines.append(f"- Summary：正数位宽 `{summary['positive']}`，零/浮点 `{summary['zero']}`，负数/codec `{summary['negative']}`。")
        lines.append(f"- 末项 `index=63` 原样保留：`offset=0x{tail['offset']:X}`, `bits={tail['bits']}`, `hint={fmt_signed_hex(tail['hint'])}`。")
        lines.append("")
        lines.append("| Index | Offset | Bits | Hint |")
        lines.append("|---:|---|---:|---:|")
        for row in rows:
            lines.append(
                f"| {row['index']} | `0x{row['offset']:03X}` | {row['bits']} | {fmt_signed_hex(row['hint'])} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dump", type=Path, default=DEFAULT_DUMP)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    data = read_dump(args.dump)
    type_map, layouts = build_layouts(data)

    if args.json_out:
        payload = {
            "source": str(args.dump),
            "base": BASE,
            "field_count": FIELD_COUNT,
            "type_table": TYPE_TABLE,
            "type_count": len(type_map),
            "unique_layout_count": len(layouts),
            "types": {
                str(row["type"]): {
                    "table": row["table"],
                    "max_index": row["max_index"],
                }
                for row in type_map
            },
            "layouts": {
                f"0x{entry['address']:08X}": {
                    "address": entry["address"],
                    "max_index": entry["max_index"],
                    "types": entry["types"],
                    "fields": entry["fields"],
                }
                for entry in layouts
            },
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.check:
        print(f"OK: {len(type_map)} type entries -> {len(layouts)} unique layouts x {FIELD_COUNT} fields")
        return 0

    rendered = render(data, args.dump)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
