# -*- coding: utf-8 -*-
"""BA-06 大厅实体全量注册表.

不按文件偏移, 而按"大厅实体"提取:
  A. 所有 lobby/room/dw/profile/matchmaking 相关 RTTI 类
  B. 所有服务名 / 任务名 字面量
  C. 所有 (service, task) 组合线索
  D. 所有 AS_* ActionScript 方法名
  E. 所有 UiCpp* 类与其 vtable
输出关键实体的 VA, 供后续逐篇论文使用.
"""
import json
import os
import re
import struct

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "DATA")
BASE = 0x400000
IMG_EXE = r"E:\codol_re\client_image_20261027.bin"
IMG_BASE = r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"


def load(path):
    return open(path, "rb").read()


def strings(buf, minlen=4):
    for m in re.finditer(rb"[ -~]{%d,}" % minlen, buf):
        yield m.start(), m.group().decode("latin1")


def rtti(buf):
    out = []
    for m in re.finditer(rb"\.\?A[VU][\x20-\x7E\x80-\xFF]{1,200}\x00", buf):
        td_off = m.start() - 8
        if td_off < 0:
            continue
        out.append((td_off, m.group()[:-1].decode("latin1")))
    return out


KEY = re.compile(
    r"lobby|Lobby|LOBBY|room|Room|ROOM|dw[A-Z]|Dw[A-Z]|match|Match|MATCH|"
    r"session|Session|playlist|Playlist|profile|Profile|party|Party|"
    r"clan|Clan|friend|Friend|presence|Presence|queue|Queue|"
    r"service|Service|Service|task|Task|Task|"
    r"onboard|Onboard|tutorial|Tutorial|challenge|Challenge|"
    r"loadout|Loadout|stencil|Stencil|"
    r"demon|Demon|DW|atom|Atom|"
    r"GameStart|StartGame|SetRoomData|CreateRoom|JoinRoom|FindSessions|"
    r"ReadQueued|Ready|Kick|Leave|Vote|Ban|"
    r"UiCpp|FSG|fsg")

report = {}


def analyze(tag, buf, is_dll):
    print("=" * 78)
    print("[%s] size=%d (0x%X)  %s" % (tag, len(buf), len(buf),
                                      "DLL" if is_dll else "EXE"))
    print("=" * 78)
    rd = {}

    # --- RTTI 分类
    ts = rtti(buf)
    print("RTTI TypeDescriptor: %d" % len(ts))
    groups = {}
    for off, nm in ts:
        # 类名 = 去掉 .?AV / .?AU 前缀 与 @@ 后缀
        m = re.match(r"\.\?A[VU](.+?)@@", nm)
        cls = m.group(1) if m else nm
        groups.setdefault(cls, []).append(off)
    print("  去重类名: %d" % len(groups))

    # 大厅相关类
    lob = sorted([c for c in groups if KEY.search(c)])
    print("  大厅相关类: %d" % len(lob))
    for c in lob[:400]:
        print("    %-60s td=0x%08X" % (c, groups[c][0]))
    rd["lobby_classes"] = {c: [o for o in groups[c]] for c in lob}
    rd["rtti_total"] = len(ts)
    rd["classes_total"] = len(groups)

    # --- 服务/任务名字面量
    print()
    svc = set()
    task = set()
    other = set()
    for off, s in strings(buf, 4):
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{2,40}", s):
            if s.endswith("Service") or s.startswith("Service"):
                svc.add(s)
            if "services/" in s:
                svc.add(s)
    print("Service-ish strings: %d" % len(svc))
    for s in sorted(svc):
        print("    %s" % s)
    rd["service_strings"] = sorted(svc)

    print()
    print("Demonware 风格标识 (bd*/dw*/atom*):")
    dws = set()
    for off, s in strings(buf, 3):
        if re.match(r"^(bd|dw|DW|atom|Atom)[A-Z]", s):
            dws.add(s)
    print("  %d 个" % len(dws))
    for s in sorted(dws)[:300]:
        print("    %s" % s)
    rd["dw_strings"] = sorted(dws)

    report[tag] = rd
    return buf


exe = load(IMG_EXE)
analyze("EXE", exe, False)
print()
dll = load(IMG_BASE)
analyze("Base.dll", dll, True)

os.makedirs(OUT, exist_ok=True)
json.dump(report, open(os.path.join(OUT, "ba06_lobby_inventory.json"), "w",
                       encoding="utf-8"), indent=1, default=str)
print("\nwrote DATA/ba06_lobby_inventory.json")
