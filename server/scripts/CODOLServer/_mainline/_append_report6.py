import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\CONFIRMED_RESULTS_20260928.md"
s = open(p, encoding="utf-8", errors="replace").read()
add = """

---

## 25. 收帧后客户端会用 5 位写入器重建回帧

### 25.1 `0xBA20A0` 的写回路径（新增反汇编结论）

```asm
00BA218F  push 4                      ; 参数：字段字节数
00BA2191  lea ecx,[ebp-0x18] ; push   ; &值
00BA2195  lea edx,[ebp-0x14] ; push   ; &位偏移
00BA2199  push 0                      ; 起始位偏移
00BA219D  mov eax,[esi+0xac]          ; eax = 帧长度（来自 u32 长度字段）
00BA21A3  push 5                      ; 参数：位宽
00BA21A5  push edi                    ; edi = 建立 [req+0xB0] 时得到的缓冲指针
00BA21B0  call 0xB78350               ; 写 5 位字段(值 = 帧长度)

00BA21BC  mov al, byte [esi+0xa8]     ; 帧类型字节
00BA21CF  mov eax,[ebp-0x14]          ; 上一次写出的位偏移
00BA21D3  push 5                      ; 位宽
00BA21D5  push edi
00BA21D6  call 0xB78350               ; 再写一个 5 位字段(值 = 类型字节)
```

即客户端在**收到并解析一帧之后**，会用位写入器 `0xB78350` 重建一条
「5 位长度 + 5 位类型」的记录，再经 `0xBA12E0` 构造成对象写入
`[req+0xB4]`，并把位读取器装到 `[req+0xB0]`：

```asm
00BA2175  mov ecx,[esi+0xb0]
00BA217B  lea edx,[ebx+5]     ; ebx = 帧头长度(类型 1/2 -> 9，其它 -> 1)
00BA217F  call 0xB9BB90       ; 设置最小帧门限
00BA218A  call 0xB9BBB0
00BA219B  mov edi, eax        ; edi = 可用长度
00BA21E4  mov ecx,[esi+0xb0]
00BA21E5  call 0xB9BB90       ; 再次设置门限(参数 ebx)
00BA21EA  push 0x18 / call 0xB74220
00BA222C  call 0xBA12E0       ; 用该缓冲构造结果对象
00BA2268  mov [esi+0xb4], edi ; 结果对象
00BA227F  mov [esi+0x9c], 3   ; 进入 sub-state 3
```

### 25.2 字段编码已确定的两个 5 位槽

```text
位偏移  0 : 5 位，值 = 帧长度（客户端首帧为 200）
位偏移 40 : 5 位，值 = 帧类型字节（客户端首帧为 0xC8）
```

两者之间 40 位（=5 字节）是客户端首帧里的
`c8 00 00 00 d2`（200, 210 的小端首字节）。这说明首帧的 4 个 u32
里，至少第 2 个（210）本身就是 5 位字段的容器。

### 25.3 由此得到的客户端首帧位级解读

```text
u32 长度        = 200            ; 帧总长
byte[4] 类型    = 0xC8 (=200)    ; 非 1/2 -> 帧头 1 字节
位偏移 0..39    : 5 位长度字段 + 5 位类型字段（共 40 位 = 5 字节）
                  即 byte[5..9] = c8 00 00 00 d2
位偏移 40 起    : 0x00080000 标志位 + 8 字节随机数
```

### 25.4 本轮未能闭合的点

```text
1) 0x00080000 标志位的语义（是能力位、下载标志还是版本位）
2) 末 8 字节随机数是否需要在服务端应答中原样回显（实测换成固定常量
   52 71 ca 53 2a c1 28 de 仍被接受，说明不是强校验项）
3) sub-state 3 之后客户端在等什么帧，导致约 50 秒后判定失去连接
```

### 25.5 结论：黑盒试探已到边界，下一步需要断点

已排除的组合（全部实测）：

```text
类型字节 = 2                       -> 立即断连
一次性多发多帧 (3 x 204B)          -> 握手第 3 阶段失败
周期重发同一帧 (--repeat-every)    -> 握手第 3 阶段失败
负载不镜像首帧 24 字节结构          -> uA50 从 3 掉回 0
负载镜像首帧结构                    -> uA50=4，50 秒后失去连接
```

剩下的字段语义无法再用「换字节看反应」推进，因为客户端对错误内容
的反馈只有「坚持 N 秒后断连」这一种。**下一步应在 `0x00BA20A0` 的
成功分支（0x00BA21B8 之后）与 `0x00BA0FF0` 加断点**，直接读出：

```text
[req+0xB4] 对象的字段值
[req+0xB0] 位读取器的游标与剩余量
[req+0xB8]/[req+0xBC] 发送队列的内容
```

据此才能反推服务端应答所需的字段值，而不是继续猜。

### 25.6 归档

```text
CODOLServer/archive/CONFIRMED_20260928_2215   472 文件，校验 472/472
```
"""
s = s.rstrip() + add
open(p, "w", encoding="utf-8", newline="\n").write(s + "\n")
print("appended", len(add))
