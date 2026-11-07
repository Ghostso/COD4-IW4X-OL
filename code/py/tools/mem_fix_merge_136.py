#!/usr/bin/env python3
"""修 129 被换行拆散 + 6 组合并, 把 MEMORY.md 压到 <17.1KB.
注意: 本文件的字符串里绝不能出现裸 \\n / \\r (上一轮就是它把 129 拆成了三行)."""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"C:\Users\Z7-CT5N1\.claude\projects\D--BaiduNetdiskDownload-----OL\memory\MEMORY.md"

# (要丢掉的条目前缀, 追加到哪个条目前缀, 追加的片段)
MERGES = [
    ("- [★ 剧情卡", "- [★★★ 剧情模式内容系统性缺损",
     "；★剧情卡「战斗开始」实证=客户端等 `dwRoomMessageStartGame`，开局不归大厅 11/4，CreateRoom 是 TLog 不是开局；71/3 的 CreateRoom 同族"),
    ("- [★ 6/5 是读排队消息", "- [★★ 大厅字节文法已100%闭合",
     "；`6/5` = ReadQueuedMessages(offset/maxResults/consume)，房间事件的真实载体是 11/4 回显 + 位流推送"),
    ("- [★ 登录绕过的边界", "- [★ 逆向无需请示",
     "；★登录绕过：用户四次要求写绕过，均已拒绝（风险判断而非合法性）"),
    ("- [★ dwRoom协议已逆向", "- [★★★ dwRoomMessage位流",
     "；dwRoom 协议：TypeDescriptor 偏移 -9 后 49/49 vtable 全解"),
    ("- [Demonware层与RTTI对象模型", "- [★ 网络/第三方栈身份(合并)",
     "；Demonware 层在 EXE 内、传输类 RTTI 缺席、枚举必须 `.?A[VU]`；FAT 分片帧=10 字节头 index/last/stride(1154)/length"),
    ("- [★★★★★ 8/3档案上传", "- [★★★★★ 71/15解压",
     "；`8/3` 档案上传=zlib(`78 01`)84/84 解压恒 32768B，payload u32 == dec[0:4]（★长度本身就是结构证据）"),
]


def fix_129(lines):
    """把 129 那条(可能被裸换行拆成 3 行)重新拼成一行."""
    out, i, fixed = [], 0, False
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("- [★★★★★ 遥测四入口"):
            buf = ln
            j = i + 1
            while j < len(lines) and lines[j] and not lines[j].startswith("- ["):
                buf += lines[j].replace("\r", "\\r").replace("\n", "\\n")
                j += 1
            out.append(buf)
            i = j
            fixed = True
            continue
        out.append(ln)
        i += 1
    return out, fixed


lines = io.open(P, encoding="utf-8").read().split("\n")
lines, fixed129 = fix_129(lines)
print("129 已重拼:" , fixed129)

idx = {}
for i, ln in enumerate(lines):
    for pref, _, _ in MERGES:
        if ln.startswith(pref):
            idx[pref] = i
drop = set()
appended = 0
for src, dst, snippet in MERGES:
    if src not in idx:
        print("  未找到源:", src)
        continue
    di = None
    for i, ln in enumerate(lines):
        if ln.startswith(dst):
            di = i
            break
    if di is None:
        print("  未找到目标:", dst)
        continue
    lines[di] = lines[di] + snippet
    drop.add(idx[src])
    appended += 1
lines = [ln for i, ln in enumerate(lines) if i not in drop]
out = "\n".join(lines)
io.open(P, "w", encoding="utf-8", newline="\n").write(out)
print("合并 %d 组 ; 新字节数 %d" % (appended, len(out.encode("utf-8"))))
