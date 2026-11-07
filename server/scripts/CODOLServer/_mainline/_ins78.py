p = r"CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md"
lines = open(p, encoding="utf-8").read().split("\n")
idx = None
for i, ln in enumerate(lines):
    if ln.startswith("## 6."):
        idx = i
        break
assert idx is not None
block = r"""
#### 5.27.78 ★★★★★★ 我的推演错误已定位：bl 被重算两次，且失败出口已被补丁堵上（第十四轮）

**(a) `0xBA3710` 内 `bl` 被【重新计算两次】**

```text
第一次（0xBA37E9 区）：
  0xBA37E9  test cl, cl        ; cl 来自 call#1/call#2 是否都成功
  0xBA37EB  je  0xBA37F6
  0xBA37ED  cmp ebx, 8
  0xBA37F0  jbe 0xBA37F6
  0xBA37F2  mov bl, 1          ; ★ bl#1
  0xBA37F6  xor bl, bl
  0xBA3840  test bl, bl
  0xBA3842  je  0xBA3867       ; bl#1 == 0 → 失败出口

第二次（0xBA38CC 区）：
  0xBA38A4  mov ecx, [edi+0xB0]
  0xBA38AA  lea ebx, [edi+0xB0]
  0xBA38B6  call 0xB9BBB0
  0xBA38C1  lea esi, [eax-5]
  0xBA38C6  cmp esi, [eax+0x1C]   ; 条件 A
  0xBA38CC  setae cl
  0xBA38D2  cmp edx, eax          ; 条件 B
  0xBA38D4  setbe al
  0xBA38DF  mov bl, 1             ; ★ bl#2（覆盖 bl#1）
  0xBA38E3  xor bl, bl
```

**(b) 第三次判定 + 一个关键事实**

```asm
0xBA3917  test bl, bl               ; bl#2
0xBA3919  je  0xBA3939
0xBA393B  [ebp-0x3A8] = 0x14
0xBA3945  test al, al
0xBA3947  je  0xBA3967
0xBA395A  call 0xC737A0             ; 取 20 字节摘要
0xBA3963  mov bl, 1                 ; ★ bl#3
0xBA3967  xor bl, bl
0xBA3985  test bl, bl               ; bl#3
0xBA3987  je  0xBA3867              ; ★★ 失败出口
0xBA398D  ... 8 字节 XOR 比较 ...
0xBA39D4  je  0xBA39E7              ; 匹配 → 进入 provider 分支
0xBA39D6  xor bl, bl
0xBA39E2  jmp 0xBA3867
```

**(c) ⇒ 我此前的推演错在哪里**

```text
我此前把 0xBA3A2C..0xBA3A5D 那段当作"必然执行的验证链"，
并据此得出"0xBA3A5D 的 ja 恒成立 ⇒ cl 恒 0"。

但实际控制流是：
  · 0xBA3842 之前有一整套判定（bl#1）
  · 0xBA3917/0xBA3985 又各有一次判定（bl#2 / bl#3）
  · 而 0xBA3987 的失败出口【已被 --patch-85-pass 用 6 字节 NOP 掉】
    （§5.27.3 记录的站点补丁之一）

⇒ 所以 bl == 0 时并不会失败退出，而是被补丁放行，
  继续走到 0xBA398D 的 8 字节比较，
  匹配后经 0xBA39D4 je 0xBA39E7 进入 0xBA39E7 分支。
```

**(d) 这解释了全部观测**

```text
· 5ec 增长（1→2→3→4、5→6→7）
  ⇒ 走到了 0xBA384D，即 bl#1 != 0 或失败出口被放行

· 644 恒 0
  ⇒ 即便进入 0xBA39E7 之后的 provider 链，
    0xBA3A5D / 0xBA3A70 的判定仍可能让 cl 停在 0

⇒ 此前"矛盾"的根源：我把【已被补丁修改过的控制流】
  按未打补丁的原代码来推演。
```

**(e) 教训（本轮第五次同类错误）**

```text
推演控制流时，必须把【已生效的站点补丁】一并算进去。
--patch-85-pass 改的 6 处（0xBA39D4/0xBA3A15/0xBA3987/
0xBA3859/0xBA35BF/0xBA3644）会改变分支走向，
而我此前在推演里全部按原代码处理。
```

**(f) 下一步**

```text
按【打了补丁之后】的控制流重新推演 0xBA39E7..0xBA3AE6，
才能得到与 5ec/644 观测一致的解释。
```
"""
lines[idx:idx] = block.split("\n")
open(p, "w", encoding="utf-8").write("\n".join(lines))
print("ok")
