"""Append section 27 to SESSION_APPEND_20260929_STAGE3_SUCCESS.md."""
import io
import os

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
REPORT = os.path.join(ROOT, "CODOLServer",
                      "SESSION_APPEND_20260929_STAGE3_SUCCESS.md")

TEXT = u"""

## 27. 客户端首帧实为 28 字节定长 —— 「200 字节帧」假设证伪

### 27.1 实验

探针新增 `--pre81-drain N`：收到客户端首帧后**先不回 0x81**，
用短超时持续 recv N 秒，看客户端会不会自己把剩下的字节流上来。

实跑 `IFS1_ELEVATED_20260929_130737`，`--pre81-drain 6`：

```text
pre81_drain_start  total=28
pre81_drain_done   total=28
full_hex = c8 00 00 00 c8 00 00 00 d2 00 00 00 dc 00 00 00
           00 00 08 00 f4 aa ba 8b 6c c7 5f e2
（6 秒内零新增字节）
```

**证伪**：客户端首消息就是 **28 字节定长**，`[0:4]=0xC8` **不是长度**，
客户端不会自行补足到 200 字节。§23.2 的「200 字节首帧」推断作废。

### 27.2 28 字节首帧的可确认结构

```text
偏移  值            说明
0x00  c8 00 00 00   常量 0xC8（不是长度）
0x04  c8 00 00 00   常量 0xC8
0x08  d2 00 00 00   魔数下界 0xD2
0x0C  dc 00 00 00   魔数上界 0xDC
0x10  00 00 08 00   ?
0x14  8 字节随机    每次运行都不同（本次 f4 aa ba 8b 6c c7 5f e2）
```

与 `0xBA3010`（客户端自发的 0xC8 帧）同形，但 `0xBA3010` 的尾 8 字节
取自 `[req+0x5F4]`，且第 5 个 u32 是 `0x08`（不是 `0x00080000`）。
两处差异说明这 28 字节不是由 `0xBA3010` 生成的。

### 27.3 本轮净结论

```text
1. 客户端首帧 = 28 字节定长，不自动续传        （新增，实跑确证）
2. 该首帧 [0:4] 的 0xC8 不是长度字段            （新增，实跑确证）
3. 0x83 成功后客户端不再处理任何入站帧           （§25/§26 两次实验）
4. [req+0x640] = 0x81 magic，必须 0xDC 才开门    （§22 实跑确证）
```

### 27.4 第一档状态

```text
① 0x81                已闭合（魔数必须 0xDC）
② 0x82                已闭合
③ 0x83 校验           已闭合
④ 0x83 -> 下一阶段    未闭合；阻塞 = 0x83 成功后 644 停在 1 且
                        客户端不再收帧，644 无路可走
⑤ 保活/持续           未闭合
```

### 27.5 接手须知（避免重复劳动）

```text
· 探针工具已具备：--magic / --frame-len / --seq-after-81 / --seq-after-83 /
  --pre81-drain / --hold-after-83 / --follow-84 / --follow-85 /
  --keepalive4 / --split-83-84
· 观察器 POST83_SAMPLE 已含 s9c/5e8/644/a8/ac/b8/c0/6d8/buf，
  已 publish 到 restore_iips_contract_001\\observer2\\out
· auto_lobby_loop 的 SUCCESS 判据是假成功，勿据此收工
· 观察器文件参数必须传绝对路径
· 真正缺的是观测：需要 0xBA3420 的调用者（EIP 采样太慢；
  code-cave 属改 .text，超出当前安全边界）
```
"""


def main():
    with io.open(REPORT, "a", encoding="utf-8") as fh:
        fh.write(TEXT)
    print("appended %d chars -> %s" % (len(TEXT), REPORT))


if __name__ == "__main__":
    main()
