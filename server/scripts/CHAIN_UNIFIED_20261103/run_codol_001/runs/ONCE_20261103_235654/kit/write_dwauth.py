# -*- coding: utf-8 -*-
"""按【三方已验证可用】的格式写游戏目录下的 dwauth.ini。

三方来源: E:\\codol\\dist\\CODOL-Portable\\Data\\runtime\\Run-Session.ps1 第 167 行
    $auth = "formal-zone-lsg.codol.qq.com 3074`r`n
             formal-zone-auth.codol.qq.com 3074`r`n
             0x03EA`r`n"

要点(与我方旧版完全不同):
  1. 主机名用【域名】而不是 IP;
  2. 端口是【3074】(明文/主通道), 不是 443;
  3. 末行多一个魔数【0x03EA】;
  4. CRLF 行尾, 末尾保留一个 CRLF。

旧版(错误)内容长这样, 别再用:
    127.0.0.1
    0
    127.0.0.1
    443
    0
    0
    0

用法:
  python write_dwauth.py                 # 写到默认游戏目录
  python write_dwauth.py --root "E:\使命召唤OL\使命召唤OL"
  python write_dwauth.py --show          # 只读现在的内容, 不写
"""
import argparse
import os
import shutil
import sys

DEFAULT_ROOT = r"E:\使命召唤OL\使命召唤OL"

CONTENT = ("formal-zone-lsg.codol.qq.com 3074\r\n"
           "formal-zone-auth.codol.qq.com 3074\r\n"
           "0x03EA\r\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT, help="游戏根目录(含 codoMP_client_shipRetail.exe)")
    ap.add_argument("--show", action="store_true", help="只打印当前内容, 不写")
    ap.add_argument("--no-backup", action="store_true")
    a = ap.parse_args()

    dst = os.path.join(a.root, "dwauth.ini")
    want = CONTENT.encode("ascii")

    if os.path.exists(dst):
        cur = open(dst, "rb").read()
        print("[*] 当前 %s (%d 字节):" % (dst, len(cur)))
        print("    " + repr(cur))
    else:
        cur = None
        print("[*] %s 不存在(将新建)" % dst)

    if a.show:
        return 0

    if cur == want:
        print("[=] 已经是正确内容, 无需修改")
        return 0

    if cur is not None and not a.no_backup:
        bak = dst + ".orig"
        if not os.path.exists(bak):
            shutil.copy2(dst, bak)
            print("[*] 已备份 -> %s" % bak)

    open(dst, "wb").write(want)
    print("[+] 已写入正确格式 (%d 字节), CRLF 行尾:" % len(want))
    for ln in CONTENT.split("\r\n"):
        if ln:
            print("      %s" % ln)
    # 回读校验
    back = open(dst, "rb").read()
    if back != want:
        print("[!] 回读不一致!")
        return 1
    print("[+] 回读校验 OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
