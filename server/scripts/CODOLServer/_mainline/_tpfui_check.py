tests = [
 r"TPFUI\IIPSRes\back\边玩边下\边玩边下底.png",
 r"TPFUI\IIPSRes\back\按钮\关闭_3_正常.png",
 r"TPFUI\IIPSRes\back\进度条\黄色进度条_中.png",
 r"TPFUI\IIPSRes\Localization\Chinese\back\边玩边下\边玩边下底.png",
]
import os
for t in tests:
    print("%-60s exists=%s" % (t, os.path.isfile(t)))
print()
print("=== TPFUI 目录树 ===")
for dp,dn,fn in os.walk("TPFUI"):
    print("  DIR", dp, "files=%d"%len(fn))
    if dp.count(os.sep) > 3: dn[:] = []
