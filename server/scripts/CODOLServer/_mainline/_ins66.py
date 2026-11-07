p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.66 ⚠️ ac_ready 标志方案实施并失败（相位差未消除）（第十三轮）

**(a) 实施内容**

```text
观察器：新增 --ac-ready-flag，在 [conn+0xAC] 变化且非 0 时写该文件
        （并记 AC_READY 事件）。
探针：新增 --follow-85-wait-flag，等到该文件出现后再发 0x85。
包装脚本：capture_elevated_network.ps1 与 elevated_ifs1_observer.ps1
          均已加 -AcReadyFlag 透传（两处转发点）。
```

**(b) 实测（IFS1_ELEVATED_20261002_021838）**

```text
观察器：38.890  AC_READY  ac=200  t=38.868    ← 只触发 1 次
探针：  1790878757.720  follow_85_wait_flag_start
       此后一直等待，从未发出 sent_85

⇒ 探针等不到标志，整轮卡在等待；
  644 全程 = 0；90.9 s 仍弹窗。
```

**(c) 两个问题**

```text
甲. 路径不一致：驱动给观察器传的是 p608_ac_ready.flag（相对当前目录），
    而探针等的是 CODOLServer\logs\p608_ac_ready.flag。
    ⇒ 已修正为同一个绝对路径。
乙. 时机依旧错位：AC_READY 在观察器 t = 38.868 才首次触发，
    而探针的 accept 发生在观察器 t ≈ 0.2 s 附近；
    观察器的采样循环本身要 38 s 才开始（与 §5.27.43 同因）。
```

**(d) ⇒ 结论**

```text
"等待标志"方案与"等待固定秒数"方案受同一个限制：
观察器的【采样循环】在 t≈38 s 才开始，
而探针的握手在 t≈0.2 s 完成。

这不是"门槛值设错"，而是：
  · 探针必须先完成 0x81/0x82/0x83 才会走到发 0x85 的那一步；
  · 而客户端要到 t≈38 s 才把 c8/5e8 推到 2/3，
    观察器的很多采样点也在此之后才激活。
⇒ 两边的时间原点不同，且探针不可能"等 38 s 再握手"
  （服务端的 ready 超时只有 150 s，但客户端的连接在此之前就已建立）。
```

**(e) 本轮的净结论**

```text
· 代码级路线：已证实不可用（5 次尝试均崩溃，§5.27.64d）
· 数据级路线（等标志）：受同样相位差限制（本节）
· 两者都指向同一件事：
    需要一个【在探针侧、与观察器无关】的观测/干预手段，
    或让观察器把采样门槛与探针的握手严格同步（需要改观察器主循环结构）。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
