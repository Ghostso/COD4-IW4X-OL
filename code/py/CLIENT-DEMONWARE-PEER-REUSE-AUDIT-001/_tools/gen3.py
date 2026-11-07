# -*- coding: utf-8 -*-
import os, re, hashlib
root = r"D:\BaiduNetdiskDownload\使命召唤OL\CLIENT-DEMONWARE-PEER-REUSE-AUDIT-001"

p = os.path.join(root, "03_FRAME_AND_STATE_MACHINE_COMPARISON.md")
t = open(p, encoding="utf-8").read()
t = t.replace(
"| +0x1E | 密文 | `0xAAAA9A lea edi,[ebx+0x1E]`，`ebx = (len+0x14) & 0xFFFFFFF0` |",
"| +0x1A | 密文 | 头部顺序写入 len(4)/AB/85/seq(4)/iv(16) 后，偏移自然为 26 = `0x1A` |")
t = t.replace(
"明文长度对齐：`lea ebx,[len+0x14]; and ebx,0xFFFFFFF0`（`0xAAAA84-0xAAAA87`）；参考 `n=(5+len(inner)+15)//16*16`。",
"""明文长度对齐：`lea ebx,[len+0x14]; and ebx,0xFFFFFFF0`（`0xAAAA84-0xAAAA87`），`ebx` 即 16B 对齐后的密文长度；随后 `lea edi,[ebx+0x1E]`、`lea eax,[edi+4]`（`0xAAAA9A-0xAAAA9D`）得到 `len 字段值 = ct+30`、`总帧长 = ct+34`，与 `26 头 + ct + 8 tag` 一致。参考实现 `n=(5+len(inner)+15)//16*16`。""")
t = t.replace(
"| 覆盖范围 | `frame[0 : total-8]`（`0xAAAF58` 起；`0xAAAFBA` 起以 `[0:total-8]` 作 HMAC 输入） | `frame[:-8]` | **一致** |",
"| 覆盖范围 | 除末尾 8B tag 外的整帧：tag 取自 `base+len-8`（`0xAAAF58`-`0xAAAF6C`）；HMAC_Update 长度 = `[edi+0xAC]-4`（`0xAAB07A`），按长度字段口径即 `total-8` | `frame[:-8]` | **一致** |")
open(p,"w",encoding="utf-8").write(t)

p = os.path.join(root, "05_REUSE_VERDICT.md")
t = open(p, encoding="utf-8").read()
t = t.replace(
"两个 codec 的调用者各仅 **2** 处，全部位于密钥派生路径（`0xAAB92C/0xAAB93C` 及另一处）。",
"两个 codec 的调用者各仅 **2** 处：一处位于密钥派生路径（`0xAAB92C` / `0xAAB93C`），另一处位于 0x85 帧路径（发送 `0xAAACE3` / 接收 `0xAAB046`）用于安装帧密钥。即同一 codec 在“会话密钥派生”和“逐帧密钥装载”两处复用。")
open(p,"w",encoding="utf-8").write(t)
print("patched")

# recompute manifest with workspace-relative paths
files = sorted(f for f in os.listdir(root) if f.endswith(".md"))
lines = []
for f in files:
    h = hashlib.sha256(open(os.path.join(root,f),"rb").read()).hexdigest()
    lines.append("%s  %s" % (h, f))
extra = [("_data","func_AAB310.txt"),("_data","recv_frame_parser.txt"),("_data","recv_parser_core.txt"),("_data","dispatcher.txt"),("_data","frame_85_region.txt")]
for d,f in extra:
    fp = os.path.join(root,d,f)
    if os.path.exists(fp):
        h = hashlib.sha256(open(fp,"rb").read()).hexdigest()
        lines.append("%s  %s/%s" % (h, d, f))
open(os.path.join(root,"SHA256SUMS.txt"),"w",encoding="utf-8").write("\n".join(lines)+"\n")
print("\n".join(lines))
