p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.75 ★★★★★★ 终局矛盾：静态推演与事实不符，且两侧均已核准（第十三轮终章）

**(a) 静态推演（每一步都已用顺序反汇编核准）**

```text
0xBA39E7  mov esi, [ebp - 0x390]   ; esi = 旧游标（唯一赋值）
          （到 0xBA3A5D 之间 esi 未被任何指令改写）
0xC73C10  （被调用者）push esi / ... / pop esi   ; 正确保存，不破坏 esi

0xBA3A07  mov ecx, [ebp - 0x3A4]
0xBA3A18  mov [ebp - 0x390], ecx   ; 游标 = ecx
0xBA3A42  push ecx                 ; arg3 = ecx = 游标
0xBA3A45  call 0xB783C0            ; *arg4 = arg3 + arg6 = 游标 + 4
0xBA3A51  mov eax, [ebp - 0x3A4]   ; eax = 游标 + 4
0xBA3A5D  cmp eax, esi             ; (游标+4) vs 游标  ⇒ 恒大于
0xBA3A5F  ja  0xBA3A65             ; ⇒ 恒跳转 ⇒ al = 0 ⇒ cl = 0
```

**(b) ⇒ 推演结论：该路径恒失败**

```text
cl = 0 ⇒ 0xBA3AE6 cmp cl,0x87 不成立 ⇒ arm 永不进入
      ⇒ [obj+0x644] 恒 0 ⇒ c8 停在 2 ⇒ ~90 s 弹窗
```

**(c) 但这与事实矛盾**

```text
事实一：客户端的 5ec（收包计数）在增长 ⇒ 它能正常处理入站 0x85。
事实二：§5.27.52 的 NOP 实验证明 arm 确实从未执行。
两者同时成立 ⇒ 客户端处理 0x85 时【不经过这条 cl=0 的路径】，
                 或者 cl 最终不为 0（另有赋值）。
```

**(d) 因此这个矛盾本身是精确的结论**

```text
不是"我没读懂"，而是：
  按 0xBA3710 的线性读法，0xBA3A5D 的 ja 恒成立、cl 恒 0；
  但客户端实际能处理入站帧。
⇒ 说明该函数存在【我尚未发现的控制流转移】：
   · 可能 0xBA3A65 出口在某个条件下会重新走到 0xBA3A72..0xBA3A91（另一次读取）
   · 可能 [ebp-0x389] 在 0xBA3A67 清零后、0xBA3AE6 之前还有别的写入
   · 可能 0xBA3AE6 的 cl 来源不是 0xBA3AE0（我看错了）
```

**(e) 结论：静态分析在此已达到可靠性边界**

```text
十三轮累计：
  已确证（可靠、可复用）：
    帧尾 MAC、接收 AES 密钥、帧结构、provider 布局与 vtable、
    0x85 入站处理器入口（0xBA3710，唯一调用者 0xBA46C2）、
    0xB783C0 参数语义、644 全部写入点、arm 入口条件
  未闭合：
    cl 的实际取值 —— 静态推演给出"恒 0"，与事实矛盾，
    说明该函数内还有未发现的控制流

判断：继续纯静态推演的有效性已经很低。
     下一步需要运行时观测（读 [ebp-0x38a] 或 [ebp-0x389]），
     而这需要一个在探针侧、不依赖观察器采样循环的手段。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
