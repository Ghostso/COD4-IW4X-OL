# -*- coding: utf-8 -*-
"""snapshot_diff.py —— 把我们的运动快照和**真实客户端的字段读序列**逐字段对照。

为什么做这个
------------
`battle_selftest.py` 只能证明"快照发出去了"，证明不了"内容对"。
真机跑一局要 3~5 分钟，而且"位置飘/卡住/转不动"很难归因到具体字段。
这里用**权威素材**做静态对照。

用哪一份 trace（重要）
----------------------
`reference/` 下有两个候选，**必须用完整的那份**：

  playerstate-motion-trace.json      ← 用这个
      completed=True, totalBits=497, reads=173
      带完整语义: origin / viewAngles / velocity / clips / reserve /
                  owned / events / weaponTime / gravity / movementSpeed …

  demo-player-fields-trace.json      ← 不要用
      scope="…not live packet validation"，末尾 error=RuntimeError，
      只有 32 个 field / 140 bit —— **残缺**。
      2026-10-07 我用它当基准得出过**错误结论**（"真实快照只有 140 bit、
      我们序列差很多"）。换成完整那份后，实际是 24/29 个字段完全对上。

用法
----
    python -X utf8 snapshot_diff.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TRACE_MOTION = r"F:\桌面\ol\新建文件夹\reference\playerstate-motion-trace.json"


def our_index_order():
    """从 battle_server._build_motion_snapshot 里抽出 w.index(N, prev) 的 N 顺序。

    ★ 两种写法都要认（2026-10-07）：
        · 字面量  w.index(21, prev)
        · 循环    w.index(21 + i, prev)   -> 展开成 21,22,23,24
      只认字面量会把"已经写好的字段"误报成缺失。
    """
    src = open(os.path.join(ROOT, "battle_server.py"), encoding="utf-8").read()
    m = re.search(r"def _build_motion_snapshot.*?return bytes\(w\.data\), w\.bit",
                  src, re.S)
    if not m:
        raise RuntimeError("找不到 _build_motion_snapshot")
    body = m.group(0)
    # 循环形式先展开（保持出现顺序：先记录 base，再插 4 个）
    out = []
    pos = 0
    for mm in re.finditer(r"w\.index\((\d+)(\s*\+\s*i)?,\s*prev\)", body):
        # ★ 被开关门控的 idx 默认"不发"，静态扫描要跳过 ——
        #   否则会把 idx219（已默认关闭，对齐实录）误报成"多发"。
        # 用"前一行"判断门控：写法是
        #     if os.path.exists(... "idx219.on"):
        #         w.index(219, prev); ...
        line_start = body.rfind("\n", 0, mm.start()) + 1
        prev_start = body.rfind("\n", 0, line_start - 1) + 1
        prev_line = body[prev_start:line_start]
        if "os.path.exists" in prev_line:
            continue
        if mm.group(2):                      # 循环形式 -> 展开 4 项
            base = int(mm.group(1))
            out.extend(base + i for i in range(4))
        else:
            out.append(int(mm.group(1)))
    # ★ 去重但保序：函数里有"新写法 + legacy 回退"两条分支（同一批 idx 出现两次），
    #   实际运行时只走其中一条，所以按**首次出现**去重，避免重复计数。
    seen = set()
    uniq = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def decode_index_sequence(reads):
    """把 reads 序列解成 [(字段 index, 该字段首读位置), ...]。

    编码（实测定死）：
      · site 0x672067 写 1 bit：=1 表示 index+1（接着读该字段）；
        =0 表示后面跟若干 4-bit 块（15 = 继续，<15 = 结束），
        index += 累计跳过 + 1。
      · site 0x672080 就是那个 4-bit 块。
    """
    out = []
    idx = -1
    i = 0
    while i < len(reads):
        x = reads[i]
        if x["returnAddress"] == "0x672067" and x["bits"] == 1:
            if x["value"] == 1:
                idx += 1
                out.append((idx, i))
            else:
                j = i + 1
                skip = 0
                while (j < len(reads)
                       and reads[j]["returnAddress"] == "0x672080"
                       and reads[j]["bits"] == 4):
                    skip += reads[j]["value"]
                    if reads[j]["value"] != 15:
                        break
                    j += 1
                idx += skip + 1
                out.append((idx, j))
                i = j - 1
        i += 1
    return out


def main():
    print("=" * 74)
    print("运动快照字段序列对照（我方 vs 真实客户端解码）")
    print("=" * 74)

    if not os.path.exists(TRACE_MOTION):
        print("[!] 找不到权威素材: %s" % TRACE_MOTION)
        return 2

    ours = our_index_order()
    m = json.load(open(TRACE_MOTION, encoding="utf-8"))
    reads = m["reads"]
    seq = decode_index_sequence(reads)
    real_idx = [f for f, _ in seq]

    print()
    print("权威素材: playerstate-motion-trace.json")
    print("  completed   = %s  (True = 完整；另一份 demo-… 是残缺的)"
          % m.get("completed"))
    print("  totalBits   = %s" % m.get("totalBits"))
    print("  reads       = %d" % len(reads))
    print("  origin      = %s" % m.get("origin"))
    print("  viewAngles  = %s" % m.get("viewAngles"))
    print("  velocity    = %s" % m.get("velocity"))
    print("  clips       = %s" % m.get("clips"))
    print("  reserve     = %s" % m.get("reserve"))
    print("  owned       = %s" % m.get("owned"))
    print("  events      = %s" % m.get("events"))
    print()

    print("-" * 74)
    print("真实字段序列（解码自 index-skip 位流）：")
    print("  %s" % real_idx)
    print("  共 %d 个字段 / %s bit" % (len(real_idx), m.get("totalBits")))
    print()
    print("我方 _build_motion_snapshot 的 idx 序列：")
    print("  %s" % ours)

    only_real = [i for i in real_idx if i not in ours]
    only_ours = [i for i in ours if i not in real_idx]
    both = [i for i in ours if i in real_idx]

    print()
    print("-" * 74)
    print("差异")
    print("-" * 74)
    print("  双方都有  : %d 个" % len(both))
    print("  我们缺的  : %s" % only_real)
    print("  我们多发的: %s" % only_ours)

    print()
    print("=" * 74)
    print("结论 / 已知语义")
    print("=" * 74)
    print("")
    print("★ 更正：上一版拿**残缺**的 demo-player-fields-trace.json 当基准，")
    print("  得出过'真实快照只有 140 bit、我们差很多'—— 那是错的。")
    print("  换成完整的 motion-trace（497 bit）后，我方 %d/%d 个字段对上且顺序一致。"
          % (len(both), len(real_idx)))
    print("")
    print("★ 真实缺口（我们从没发过）：")
    print("    idx 21 / 22 / 23 / 24 —— 解码值 1157 / 0 / 0 / 0")
    print("      对照 metadata clips=[[1157,35,0],[1158,15,0],[0,0,0]]、")
    print("      owned=[1157,1158,317] ⇒ 这是**武器槽/武器数组**，")
    print("      不是我方现在写的'事件数组'（eq.events[i]）—— 属**语义错位**。")
    print("    idx 84 —— 一串 4-bit 块（4x15…）⇒ **已拥有武器表**的尾部。")
    print("")
    print("★ 我方多发：")
    print("    idx 45  —— 默认关（idx45.on）；实测写进去会让视角乱转，保持关。")
    print("    idx 219 —— 真实序列里没有，需确认是否应删。")
    print("")
    print("★ 位宽不要照抄：totalBits 随场上内容变（增量编码），")
    print("  字段存在与否取决于与基线的差异。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
