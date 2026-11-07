# E18 — 依赖图 / DEPENDENCY GRAPH

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
