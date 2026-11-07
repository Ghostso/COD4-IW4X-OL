# -*- coding: utf-8 -*-
"""把 motion-trace 里 idx84 那段（武器/弹药表）解成结构。一次性分析工具。

不参与运行时；只用来把"实录位流"翻译成我方 _build_motion_snapshot 末尾
那段 guns 循环该照抄的形状。
"""
import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("sd", os.path.join(ROOT, "snapshot_diff.py"))
sd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sd)

TRACE = r"F:\桌面\ol\新建文件夹\reference\playerstate-motion-trace.json"
d = json.load(open(TRACE, encoding="utf-8"))
seq = sd.decode_index_sequence(d["reads"])
start = [p for f, p in seq if f == 84][0]
b = d["reads"][start:]

print("metadata: clips=%s reserve=%s owned=%s"
      % (d.get("clips"), d.get("reserve"), d.get("owned")))
print()


def show(lo, hi, desc):
    vals = ["%d:%d" % (b[k]["bits"], b[k]["value"]) for k in range(lo, hi)]
    print("  [%3d..%3d] %-46s %s" % (lo, hi - 1, desc, " ".join(vals)))


print("=== idx84 结构（按读数下标）===")
show(0, 10, "9 个 4bit 块 = 15x9 + 1 个 0  (site 672094)")
show(10, 20, "10 个 1bit = 1,1,0,0,0,0,0,0,0,0")
show(20, 22, "1bit=1 + 17bit=5        -> clips 计数 = 5")
show(22, 25, "slot0: 1bit=1, 4bit=0, 11bit=1157")
show(25, 27, "slot0: 1bit=1, 9bit=35          <- clip=35")
show(27, 28, "slot0: 1bit=0                   <- 项结束")
show(28, 31, "slot1: 1bit=1, 4bit=1, 11bit=1158")
show(31, 33, "slot1: 1bit=1, 9bit=15          <- clip=15")
show(33, 34, "slot1: 1bit=0                   <- 项结束")
show(34, 35, "1bit=0                          <- clips 列表结束")
show(35, 36, "1bit=1")
show(36, 37, "1bit=1                          <- owned 列表开始")
print("  (owned 项：1bit=1 + 1bit=1 + 11bit=weapon + 5x1bit + 12bit)")
show(37, 45, "owned0")
show(45, 53, "owned1")
show(53, 61, "owned2")
show(61, 76, "owned 剩余空槽 (15 项上限)")
show(76, 77, "1bit=1                          <- reserve 列表开始")
print("  (reserve 项：4bit=slot + 11bit=ammoKey + 12bit=reserve)")
show(77, 80, "res0: 4bit=0, 11bit=1112, 12bit=108")
show(80, 83, "res1: 4bit=1, 11bit=646, 12bit=45")
show(83, 84, "1bit=0                          <- reserve 结束")
show(84, 97, "尾部 13 个 1bit=0")
