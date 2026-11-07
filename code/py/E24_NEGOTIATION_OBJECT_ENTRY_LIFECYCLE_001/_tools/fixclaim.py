from pathlib import Path
base=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001")

p=base/"E24_EXECUTIVE_SUMMARY.md"; t=p.read_text(encoding="utf-8")
old="- `this+0x14` 的 16 字节是**构造期预设的常量密钥表**，两处调用传入的 `arg1` 是**不同的临时缓冲**，但校验后均与同一份密钥比较。"
new="- `0xACE180` 的被比较字段是 `(this+0xC)+4`（即 `this+0x10`）的长度值与常量 `0x10`；写入目标是 `(this+0xC)+8`（即 `this+0x14`）的 16 字节块。`arg1` 与 `arg2/arg3` 是**不同的临时缓冲**（arg1 为 `[ebp-0x50]` 的 16 字节块）。"
assert old in t; t=t.replace(old,new); p.write_text(t,encoding="utf-8"); print("fixed exec")

p=base/"E24_A87D50_BUFFER_DATAFLOW.md"; t=p.read_text(encoding="utf-8")
old="""- `0xB4FF60` 是 `memcpy`（`rep movsd` + 尾字节分支，见实测反汇编）。
- **比较对象**：`this+0x10` 处的长度字段与常量 `0x10`。
- **写入**：把 arg1 的 0x10 字节拷入 `this+0x14`。
- **失败**：返回 `0x10`。

**裁定**：该检查实际是"**16 字节定长拷入 + 长度守卫**"，不是摘要比对。可写为 PROVEN。"""
new="""- `0xB4FF60` 是 `memcpy`（`rep movsd` + 尾字节分支，见实测反汇编）。
- **比较对象**：`(this+0xC)+4` = `this+0x10` 处的 dword 与常量 `0x10`。
- **写入**：把 arg1 的 0x10 字节拷入 `(this+0xC)+8` = `this+0x14`。
- **失败**：返回 `0x10`。

**裁定**：该检查实际是"**16 字节定长拷入 + 长度守卫**"，不是摘要比对。可写为 PROVEN。

> 未闭合：`this+0x10` 处长度值 `0x10` 的**最初写入点**未定位（构造器 `0x687BA0` 在 `0x687BC4..0x687BDC` 之间以 `push 0x10; call 0xA888A0` 建立基类子对象，但其 `ecx` 与 `this+0xC` 的偏移关系尚未逐指令确认）。该项标 BLOCKED，不影响本节结论。"""
assert old in t; t=t.replace(old,new); p.write_text(t,encoding="utf-8"); print("fixed dataflow")

import hashlib
reps=sorted(base.glob("E24_*.md"), key=lambda x:x.name)
lines=["%s  %s"%(hashlib.sha256(x.read_bytes()).hexdigest(),x.name) for x in reps]
(base/"SHA256SUMS.txt").write_text("\n".join(lines)+"\n",encoding="ascii")
man={}
for ln in (base/"SHA256SUMS.txt").read_text(encoding="ascii").splitlines():
    if ln.strip():
        h,n=ln.split("  ",1); man[n]=h
cur={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in base.glob("E24_*.md")}
print("manifest OK:",len(man)==8 and set(man)==set(cur) and all(man[n]==cur[n] for n in man))
