# -*- coding: utf-8 -*-
import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E18_SOCKET_VTABLE_CONSTRUCTOR_AND_INDIRECT_DISPATCH_001"
F={}
F["E18_HYPOTHESIS_LEDGER.md"]="""# E18 — 假设台账 / HYPOTHESIS LEDGER

---

### H-E18-01：0x898588/0x898590 是 libcurl 传输对象的 vtable 槽位
- 支持：表 0x898568..0x898634（52 槽）；表后紧跟 i386-pc-win32 / 7.38.0 / smtps / OCSP_* / BIO_ZLIB_*（EV-18-01/02/03）
- 反证：无
- 状态：CONFIRMED_BY_EVIDENCE

### H-E18-02：0x775A50 / 0x775AB0 是 socket 对象的接口方法
- 支持：thiscall，读 this[0x14]=sock；直接 call recv/recvfrom；不解析载荷（EV-18-08/09）
- 反证：无
- 状态：CONFIRMED_BY_EVIDENCE

### H-E18-03：虚表构造者已定位
- 支持：0x776139/0x776188 写 vptr=0xC98568；分配器 0x776170（EV-18-04/05/06）
- 反证：0x776170 无直接调用者（注册路径未定）
- 状态：CONFIRMED_BY_EVIDENCE（构造）/ BLOCKED（注册）

### H-E18-04：两候选属游戏会话路径
- 支持：（无）
- 反证：libcurl 4 根 6 层闭包不含任何游戏解析候选（EV-18-11）
- 状态：REFUTED（限定范围）

### H-E18-05：0xA84CE0 是 Demonware 消息交付点
- 支持：（E-17 表述）
- 反证：实为定长 0x84 字节 rep movsd 结构体赋值 + 写 word 字段（EV-18-10/12）
- 状态：REFUTED

### H-E18-06：Demonware 栈承载游戏会话
- 支持：Demonware 是 COD 官方后端网络库
- 反证：7 层闭包不含游戏解析器（E-17 EV-17-08）
- 状态：BLOCKED（未证，未否证）

### H-E18-07：游戏协议入口仍在 socket 调用点内
- 支持：（E-12..E-17 曾假设）
- 反证：全部 9 个 recv/recvfrom 调用点已归属（E-17 + E-18）
- 状态：REFUTED（限定范围）

## 保留（未被本轮推翻）

| 假设 | 状态 |
|---|---|
| E-15 TLS 栈属 HTTP 更新 | 保留 |
| E-16 0x1B0430 属 ICMP ping | 保留 |
| E-16 0x78772D 是时间戳工具 | 保留 |
| E-17 0x6B4DE0/0x784F60 是 recv 封装 | 保留 |
| E-13 0x3524F0 是环形缓冲写侧 | 保留（发送暂存） |
"""
F["E18_DEPENDENCY_GRAPH.md"]="""# E18 — 依赖图 / DEPENDENCY GRAPH

---

## 1. 网络输入到应用层（当前状态）

    [socket API]
      recv (7) / recvfrom (3) / send (5) / sendto (4)
         0x602441 / 0x6029BE   -> 错误日志        (PROVEN 非游戏)
         0x6052AB              -> TLS 探测/HTTP   (PROVEN 非游戏)
         0x784F7D              -> Demonware recv  (PROVEN 非游戏应用层)
         0x1B0BA1              -> ICMP ping       (PROVEN 非游戏)
         0x6B4E3C              -> Demonware       (PROVEN 非游戏应用层)
         0x775A6C (0x775A50)   -> libcurl recv    (E18: PROVEN 非游戏)
         0x775ADE (0x775AB0)   -> libcurl recvfrom(E18: PROVEN 非游戏)
         0x788133              -> 未闭合          (BLOCKED)

    游戏应用层消息分派器         : 未定位 (BLOCKED)
    实时 Gamestate 0x03 消费者   : 未定位 (BLOCKED)
    Configstring body 0xA2660    : 字段级 PROVEN；实时归属 BLOCKED

## 2. libcurl 对象子图（本轮闭合）

    libcurl 传输对象 (this)
        vptr (this+0)
           vtable 0xC98568 (52 槽)
                 slot 8  0x775A50 -> recv(this[0x14], buf, len, 0)
                 slot 10 0x775AB0 -> recvfrom(..., &this[4], 16)
        构造: 0x776139 / 0x776188 (vptr write)
        分配: 0x776170 (0x24 字节; 经 [0xD3A588]+0x28)
        销毁: 0x776130 (经 [0xD3A588]+0x30)

## 3. Demonware 对象子图（E-17）

    0x783F00
        栈缓冲 [ebp-0x118]
        call 0x6B4DE0 -> recvfrom -> buf
        rep movsd 0x84 字节
        call 0xA84CE0 (定长结构体赋值)

## 4. 未闭合依赖

| 结论 | 未满足依赖 | 后果 |
|---|---|---|
| 游戏入站路径 | 全部 socket 入口已归属非游戏 | BLOCKED |
| Demonware 承载游戏 | 需展开 0x6ABBC0 | BLOCKED |
| 0x776170 注册者 | 无直接交叉引用 | BLOCKED |
"""
for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
