# -*- coding: utf-8 -*-
"""准备"翻一遍商城页 -> 抓内存"的采集流程。

目的（2026-10-07）：
  1. 补齐还没找回的 11 个 SKU（48/73/1011/1981/15827/19405/19621/
     31173/31374/31819/41314）—— 这些多半只在**打开对应商城页之后**
     才被客户端解密到内存；
  2. 顺带为**目录页 80/70** 收集线索（客户端解析出 SKUObj 后，
     record/字段序列会留在内存里）。

做的事（都是**开关文件**，可一键回滚）：
  * memlinear.on              -- 打开线性内存转储
  * memlinear_after.txt       -- 转储延迟秒数（默认 150）
  * memlinear_outdir.txt      -- 输出目录名（默认带时间戳，绝不覆盖 mem_linear）
  * callsign-scan.on          -- 顺带抓称号表

用法：
  1) 先按主手册起服务 + 拉起游戏（run_all.py）
  2) 游戏进大厅后，运行本脚本
  3) 脚本会打印转储倒计时；这段时间里**把商城各页签都翻一遍**
     （商店/军火箱/仓库/特价），并停留在最后一页别动，等转储完成
  4) 完成后：
     python -X utf8 _extract_sku_table_v2.py <新目录>

回滚：删掉 memlinear.on / callsign-scan.on 即可（其余两个是参数文件，
      不打开开关时完全无副作用）。
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
FLAG_MEM = os.path.join(ROOT, "memlinear.on")
AFTER = os.path.join(ROOT, "memlinear_after.txt")
OUTDIR = os.path.join(ROOT, "memlinear_outdir.txt")
CALLSIGN = os.path.join(ROOT, "callsign-scan.on")

# 转储前留给用户翻页的秒数。nt10 的计时从注入完成开始，
# 所以这里给足时间（默认 150s）让你进大厅 + 翻商城。
BROWSE_SECONDS = 150


def touch(p):
    with open(p, "w"):
        pass


def main():
    name = "mem_linear_" + time.strftime("%Y%m%d_%H%M%S")
    with open(AFTER, "w", encoding="ascii") as f:
        f.write("%d\n" % BROWSE_SECONDS)
    with open(OUTDIR, "w", encoding="ascii") as f:
        f.write(name + "\n")
    touch(FLAG_MEM)
    touch(CALLSIGN)

    out = os.path.join(ROOT, name)
    print("=" * 66)
    print("已打开采集开关：")
    print("  memlinear.on          = 开")
    print("  callsign-scan.on      = 开（顺带抓称号表）")
    print("  memlinear_after.txt   = %d 秒" % BROWSE_SECONDS)
    print("  memlinear_outdir.txt  = %s" % name)
    print("-" * 66)
    print("现在请：进大厅 -> 把商城各页签都翻一遍（商店/军火箱/仓库/特价）")
    print("         -> 停在最后一页别动，等约 %d 秒让转储完成。" % BROWSE_SECONDS)
    print("转储输出目录: %s" % out)
    print("-" * 66)
    print("转发储完成后跑：")
    print('  python -X utf8 _extract_sku_table_v2.py "%s"' % out)
    print("=" * 66)
    print("注意：本脚本只写开关文件，不碰 mem_linear（旧转储保留）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
