p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
s = open(p, encoding="utf-8").read()
old = """## 12. 一句话交接

```text
层一已经全线打通，明文资料在 _cleanout\\ff_layer1\\。
现在的两个缺口（层二解密 + 大厅 ⑤）都收敛到同一件事：
  让引擎真正加载一个 zone。

而在那之前，最短的一步是：
  用同一轮的 obj+0x60C 与真实 0x85 帧，
  把 BA0420 + B9BBB0 + keyed-SHA1 + length-8 这条发送侧链
  逐字节复刻出来 —— 剩余缺口是 [ebp+0xC]/[ebp-0x384] 的真实值
  与 message 指针对齐。
```"""
new = """## 12. 一句话交接

> 更精简的版本见同目录 `HANDOFF_20261002_TLDR.md`。

```text
层一已经全线打通，明文资料在 _cleanout\\ff_layer1\\。

大厅第一档：
  ①②③④ 全部闭合（密码学部分各经 3 次独立验证，见 §5.27.18 / §5.27.29）
  ⑤ 未闭合，卡点已精确定位：

    客户端解我们的 0x85 后，内层流首字节不是 0x87
      （provider 输出写到 [ebp-0x50]，而内层读取器 0xB783C0
        的数据源参数里没有它 —— 见 §5.27.53 / §5.27.54）

    结果：0x87 arm 分支从不进入 => [obj+0x644] 恒为 0
          => c8 停在 2 => ~90 s 弹"与大厅服务失去连接"

  §5.27.52 的决定性实验：给 0xBA35E9（arm 失败出口）打 NOP
  后补丁确认生效（ok7=True），但 644 仍为 0
  => 证明 0xBA3590 根本没被调用。

下一步只有一件事：
  确认 0xBA39E7..0xBA3A2C 之间是否存在"把 provider 输出
  送入内层流"的拷贝。
    · 有 => 卡点即在该拷贝的条件
    · 无 => 0x85 内层消息不走这次 provider 调用，
            而是走更早的路径（0xBA1477 那套 + 0xC73800 摘要）
```

> **本节已于 2026-10-02 更新。** 原文说"发送侧链未复刻"，
> 该部分已在 §5.27.18 用三轮数据逐字节验证完毕。"""
assert old in s, "anchor not found"
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(s)
print("updated section 12")
