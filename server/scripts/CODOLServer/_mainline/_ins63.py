p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.63 ⚠️ 再更正：0xBA46C2 的 ebx/edi 来源（第十二轮收官）

**(a) `0xBA4430`（大厅分发器）内的实参准备**

```asm
0xBA44AD  mov ecx, [esi + 0xB0]     ; esi = 连接对象
0xBA44B3  call 0xB9BBB0             ; ★ 返回一个【数值】，不是指针
0xBA44B8  mov edi, [esi + 0xAC]     ; edi = obj+0xAC（另一个数值）
0xBA44BE  mov ebx, eax              ; ebx = 0xB9BBB0 的返回值
0xBA44C4  lea ecx, [ebp - 0x14]
0xBA44CB  push edi
0xBA44CC  push ebx
0xBA44D8  call 0xB765A0             ; 解析帧头
```

而 `0xB9BBB0` 的语义（§5.27.33 已分析）：

```asm
0xB9BBB0  mov eax, [ecx + 0x1C]
0xB9BBB3  test eax, eax
0xB9BBB5  jne ok
0xB9BBB7  ret                        ; 0 直接返回
0xB9BBB8  sub eax, [ecx + 0x24]
0xB9BBBB  add eax, 0x1F
0xB9BBBE  ret
```

⇒ **返回值是 `[ctx+0x1C] - [ctx+0x24] + 0x1F`，是一个数值（长度/偏移量）。**

**(b) ⇒ 因此 §5.27.60(c) 的"arg1 = 源基址、arg3 = 另一缓冲"结论需撤回**

```text
外层传入 0xBA3710 的：
  arg1 = ebx = 0xB9BBB0(...) 的返回值（数值）
  arg3 = edi = [obj+0xAC]     （数值）

而 0xBA3710 内部把 arg1 存进 esi、arg3 存进 ebx，
后续把它们当作【缓冲区指针与边界】使用（0xB783C0 的 arg1/arg2）。

⇒ "两个不同缓冲"的说法没有依据：
  当时依据的是 POST83_SAMPLE 的 b0/b4 两个地址，
  但那是 [obj+0xB0] 与 [obj+0xB4] 的采样，
  与 0xBA46C2 传入的 ebx/edi 不是同一组值。
```

**(c) 当前准确状态**

```text
已确证（有直接反汇编依据）：
  · 0xB783C0 的参数语义（arg1 源基址 / arg3 源偏移 / arg5 目标 / arg6 长度）
  · 0x85 入站处理器 = 0xBA3710，唯一调用者 = 0xBA46C2（在 0xBA4430 内）
  · 0xBA46C2 的调用用 push ebx / push edi / push [ebp-8] / push [ebp+0xC] / push esi
  · 0xBA3A91 读取 cl 时 arg1 = ebx（该函数内 = 其 arg3）
  · 0xBA35E9 打 NOP 后 644 仍为 0（§5.27.52）

已撤回：
  · §5.27.60(c) "两个不同源缓冲"
  · §5.27.61(e) 甲（改 0xBA3A90）—— 已实验证否（破坏启动）
  · §5.27.54 / §5.27.57(e) 关于"参数错位"的定位

未确定：
  · cl 为何不等于 0x87 —— 需要运行时观测 [ebp-0x38a]
```

**(d) 教训（本轮第三次同类）**

```text
纯静态反汇编在寄存器语义上极易出错：
  同名寄存器在不同函数、不同阶段含义不同；
  返回值是"数值"还是"指针"必须逐个确认；
  跨来源的数据（观察器采样的 [obj+0xB0]/[obj+0xB4]）不能
  直接等同于另一处代码的局部变量。
⇒ 在给出"根因"级结论前，应先用一次可观测实验验证。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
