# -*- coding: utf-8 -*-
"""找 C# 参考实现(CodolLocalLobbyServer.cs / MarketplaceStore.cs)。"""
import os
import sys

PROJ = r"D:\BaiduNetdiskDownload\使命召唤OL"
TARGETS = ("CodolLocalLobbyServer.cs", "MarketplaceStore.cs",
           "PlayerProfile.cs", "LocalPlayerAccount.cs")


def main():
    hits = []
    for base, dirs, files in os.walk(PROJ):
        dirs[:] = [d for d in dirs if d not in
                   ("mem_linear", "mem_marketplace", "mem_callsign",
                    "mem_sku", "__pycache__", ".git", "IIPSDownload")]
        for fn in files:
            if fn in TARGETS:
                p = os.path.join(base, fn)
                hits.append((p, os.path.getsize(p)))
    print("找到 %d 个 C# 参考文件:" % len(hits))
    for p, sz in hits:
        print("  %-100s %d" % (p, sz))
    return 0


if __name__ == "__main__":
    sys.exit(main())
