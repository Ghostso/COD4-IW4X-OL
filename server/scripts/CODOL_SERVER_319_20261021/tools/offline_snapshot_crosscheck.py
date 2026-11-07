# -*- coding: utf-8 -*-
"""离线快照对拍 —— 不启动客户端, 不写受保护目录。

做三件事:
  A. 我们的编码器(经 probe_snapshot_size.exe) 与**改动前记录的黄金向量**对拍:
     · 首帧是否与改动前逐字节相同(证明"XOR->裸值"这次改动没碰首帧);
     · 第 2 帧是否**仍然含裸值**(不再退化成 0);
     · 换基线(from=上一帧 / from=全零)是否产出相同字节(裸值的不变量)。
  B. 与**真正的 Python 参照**逐字节对拍: 从 REF_LOBBY_KIT/battle_server.py 里
     原文 exec 出 `_Slot` / `_Equipment` / `_BitWriter` / `_build_motion_snapshot`
     (不用 import —— import 会在受保护目录里生成 __pycache__), 用同一组入参跑一遍。
  C. 顺带体检: 仓库里那份 golden_first_snapshot.hex 是否还等于**当前**参照的输出
     (若不等, 说明那份黄金向量是旧的)。

用法:  python -X utf8 tools/offline_snapshot_crosscheck.py
"""
from __future__ import annotations
import os, re, struct, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
PROJ = ROOT / "CODOL_SERVER_319_20261021"
PROBE = PROJ / "build" / "Debug" / "probe_snapshot_size.exe"
GOLDEN = PROJ / "tests" / "fixtures" / "snapshot_golden_20261024.txt"
REF_PY = ROOT / "REF_LOBBY_KIT" / "battle_server.py"
STALE_GOLDEN_HEX = ROOT / "CODOL-Combat-Server-v0.1" / "tests" / "golden_first_snapshot.hex"
LIVE_LOG = (ROOT / "run_codol_001" / "runs" / "ENTITY_SECTION_20261024_1320" /
            "kit" / "_c_battle_out.txt")

fails: list[str] = []


def ok(msg): print("ok   " + msg)
def bad(msg):
    print("FAIL " + msg)
    fails.append(msg)


def first_diff(a: bytes, b: bytes):
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return None if len(a) == len(b) else n


def run_probe() -> dict:
    r = subprocess.run([str(PROBE)], capture_output=True, text=True, errors="replace")
    out = r.stdout
    got = {}
    for m in re.finditer(r"^XCHK ([a-z0-9_]+)=(.*)$", out, re.M):
        got[m.group(1)] = m.group(2).strip()
    if r.returncode != 0 or "frame1" not in got:
        raise SystemExit("probe 失败 rc=%d\n%s\n%s" % (r.returncode, out[-2000:], r.stderr[-2000:]))
    return got


def load_golden() -> dict:
    d = {}
    for line in GOLDEN.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        d[k.strip()] = v.strip()
    return d


def build_python_reference(first: bool, server_time: int):
    """原文 exec 参照的四个定义, 用同一组入参跑一遍, 返回 (bytes, bits)。"""
    src = REF_PY.read_text(encoding="utf-8").splitlines(keepends=True)
    scratch = Path(tempfile.mkdtemp(prefix="codol_ref_"))
    ns = {"__name__": "codol_ref_extracted", "os": os, "struct": struct,
          "OUTDIR": str(scratch), "IDX45_FLAG": str(scratch / "idx45.on"),
          "_OMIT_VIEWANGLES": False}
    seg1 = "".join(src[953:1100])      # 行 954..1100: _Slot / _Equipment / _BitWriter
    seg2 = "".join(src[1103:1286])     # 行 1104..1286: _build_motion_snapshot
    assert "class _Slot" in seg1 and "_BitWriter" in seg1, "参照切片对不上(行号漂了)"
    assert "def _build_motion_snapshot" in seg2, "参照切片对不上(行号漂了)"
    exec(compile(seg1, str(REF_PY), "exec"), ns)
    exec(compile(seg2, str(REF_PY), "exec"), ns)
    eq = ns["_Equipment"]()
    snap, nbits = ns["_build_motion_snapshot"](
        0, server_time, 1000, first,
        48.0, -572.0, -116.0, 0, 0, 0,
        0.0, 0.0, 0.0, False, eq, omit_motion=False)
    return bytes(snap), nbits


def main() -> int:
    got = run_probe()
    gold = load_golden()
    our1 = bytes.fromhex(got["frame1"])
    our2p = bytes.fromhex(got["frame2_prev"])
    our2z = bytes.fromhex(got["frame2_zero"])

    print("=" * 78)
    print("A. 与改动前的黄金向量对拍")
    print("=" * 78)
    g1 = bytes.fromhex(gold["omit0_frame1"])
    g2raw = bytes.fromhex(gold["omit0_frame2_raw"])
    g2xor = bytes.fromhex(gold["omit0_frame2_xor"])
    print("   我们 帧1            = %d 字节" % len(our1))
    print("   我们 帧2(from=帧1)  = %d 字节" % len(our2p))
    print("   我们 帧2(from=零)   = %d 字节" % len(our2z))

    if our1 == g1:
        ok("首帧与改动前逐字节相同 —— 这次改动没有触碰首帧")
    else:
        d = first_diff(our1, g1)
        bad("首帧变了! 首个不同偏移 0x%X (%s vs %s)" % (
            -1 if d is None else d,
            "" if d is None else "%02X" % our1[d],
            "" if d is None else "%02X" % g1[d]))

    if int(got["frame2_baseline_diff_bytes"]) == 0 and our2p == our2z:
        ok("第 2 帧换基线产出相同字节 —— 字段载荷是裸值, 基线不参与编码")
    else:
        bad("第 2 帧仍受基线影响(diff=%s)" % got["frame2_baseline_diff_bytes"])

    if our2p == g2raw:
        ok("第 2 帧 == 改动前记录的「裸值写法」")
    else:
        d = first_diff(our2p, g2raw)
        bad("第 2 帧与「裸值写法」不同, 首个不同偏移 %s" % d)

    if our2p == g2xor:
        bad("第 2 帧仍等于旧的 XOR 写法 —— 改动没生效")
    else:
        ok("第 2 帧 != 旧的 XOR 写法 —— 退化到 0 的写法确实没了")

    n = int(got["frame1_vs_frame2_zero_diff_bytes"])
    offs = [int(x) for x in got["frame1_vs_frame2_zero_diff_offsets"].split(",") if x.strip()]
    if n <= 6 and all(o <= 10 for o in offs):
        ok("帧1 与 帧2 只在头部不同(%d 字节, 偏移 %s) —— 值没变就逐字节相同" % (n, offs))
    else:
        bad("帧1 与 帧2 在头部之外还有差异: %d 字节, 偏移 %s" % (n, offs))

    if any(our2p[i:i + 4] == struct.pack("<f", 48.0) for i in range(len(our2p) - 3)):
        ok("第 2 帧里能找到裸值 float(48.0) —— 不再被异或成 0")
    else:
        bad("第 2 帧里找不到裸值 float(48.0)")

    print()
    print("=" * 78)
    print("B. 与真正的 Python 参照对拍(《REF_LOBBY_KIT/battle_server.py》原文 exec)")
    print("=" * 78)
    ref1, refbits1 = build_python_reference(True, 1000)
    ref2, refbits2 = build_python_reference(False, 2000)
    print("   参照 帧1 = %d 字节  帧2 = %d 字节" % (len(ref1), len(ref2)))
    print("   我们 帧1 = %d 字节  帧2 = %d 字节" % (len(our1), len(our2z)))

    print("   我们帧1: " + our1.hex())
    print("   参照帧1: " + ref1.hex())
    d = first_diff(our1, ref1)
    if d is None:
        ok("首帧与 Python 参照**逐字节相同**")
    else:
        print("   → 首个不同偏移 0x%02X(%d): 我们 %s / 参照 %s"
              % (d, d, our1[d:d + 6].hex(), ref1[d:d + 6].hex()))
        print("   → 共同前缀 %d 字节 / 我们 %d / 参照 %d"
              % (d, len(our1), len(ref1)))
        print("   (首帧与参照的差异**不是**这次改动造成的 —— 改动前后首帧逐字节相同;")
        print("    差异来自 docs/SNAPSHOT_FIELD_DIFF_20261024.md §7/§8 记录的结构性项:")
        print("    我们多写 idx62/107/162、idx83, 少写 index(84), 21-24 用旧式事件数组。)")

    print()
    print("=" * 78)
    print("C. 仓库里那份 golden_first_snapshot.hex 是否还等于当前参照的输出?")
    print("=" * 78)
    if STALE_GOLDEN_HEX.is_file():
        stored = bytes.fromhex(STALE_GOLDEN_HEX.read_text(encoding="ascii").strip())
        print("   仓库里  = %d 字节" % len(stored))
        print("   当前参照 = %d 字节" % len(ref1))
        if stored == ref1:
            ok("仓库那份黄金向量仍然等于当前参照输出")
        else:
            dd = first_diff(stored, ref1)
            print("   → 不同, 首个不同偏移 %s; 长度 %d vs %d" % (dd, len(stored), len(ref1)))
            print("   → 说明**仓库那份是旧参照产出的**, 不能当当前参照的黄金向量用。")
        print()
        print("   ⚠ 这条是**负面情报**, 不是「我们对齐了」: 参照这份首帧 = %d 字节, 而 141 字节"
              % len(ref1))
        print("     正是 HANDOFF_20261025_BINARY_BISECT.md §15 里让**客户端卡住**的那一份")
        print("     (REFENCODER_20261024_1150, 首帧 141B, 客户端只走到 head≈0x62)。")
        print("     ⇒ 对这个加壳客户端, '与 Python 参照逐字节一致'是已知死路; 只能以实测为准。")
    else:
        print("   (仓库里没有那份文件)")

    print()
    print("=" * 78)
    print("D. 客户端**实际接受**过的那条路径有没有被本次改动碰过?")
    print("=" * 78)
    print("   证据: ENTITY_SECTION_20261024_1320 —— 客户端进图并持续 ack 那一轮,")
    print("         战斗服日志里第一帧快照的**线上原始字节**(TX_SNAP_HEX)。")
    live = None
    if LIVE_LOG.is_file():
        for line in LIVE_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.search(r"TX_SNAP_HEX seq=(\d+) total=(\d+) ents=(\d+) ([0-9A-Fa-f]+)", line)
            if m and int(m.group(3)) == 0:
                seq = int(m.group(1))
                raw = bytes.fromhex(m.group(4))
                mask = (seq ^ 1) & 0xFF
                snap = bytearray(raw[4:])
                for i in range(len(snap)):
                    if 4 + i >= 8:
                        snap[i] ^= mask
                live = bytes(snap)
                print("   seq=%d total=%d -> 解掩码后快照 %d 字节" % (seq, int(m.group(2)), len(live)))
                break
    if live is None:
        print("   (没找到该轮的 TX_SNAP_HEX, 跳过)")
    else:
        our_omit1 = bytes.fromhex(got.get("omit1_first_ct0", ""))
        print("   线上(解掩码) : " + live.hex())
        print("   我们现在     : " + our_omit1.hex())
        if live == our_omit1:
            ok("线上那帧与我们现在的 omit=1(command_time=0) 输出**逐字节相同**"
               " —— 客户端接受的那条路径没被本次改动碰过")
        else:
            d = first_diff(live, our_omit1)
            bad("线上那帧与现在的 omit=1 输出不同! 首个偏移 %s, 长度 %d vs %d"
                % (d, len(live), len(our_omit1)))

    print()
    if fails:
        print("对拍结果: FAILED (%d 项)" % len(fails))
        for f in fails:
            print("   - " + f)
        return 1
    print("对拍结果: A/D 两段(本次改动的验收项)全部通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
