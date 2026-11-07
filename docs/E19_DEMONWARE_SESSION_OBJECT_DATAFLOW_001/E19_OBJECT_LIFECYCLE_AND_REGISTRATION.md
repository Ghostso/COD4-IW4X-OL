# E19 — 对象生命周期与注册 / OBJECT LIFECYCLE

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. 对象字段初始化（PROVEN）

状态 0（`0x6ABE99`）是**接收状态重置**：

    6ABE99  xor edi,edi
    6ABE9B  mov [esi+0xA4],edi        ; used = 0
    6ABEA1  mov byte [esi+0xA8],0     ; 类型码 = 0
    6ABEA8  mov [esi+0xAC],edi        ; 帧长度 = 0
    6ABEAE  mov eax,[esi+0xB0]
    6ABEB8  add eax,4 / push eax / call [0xBAE114]   ; operator delete[]
    6ABED0  mov eax,[ecx] / mov edx,[eax] / push 1 / call edx  ; 对象虚析构
    6ABED8  mov [esi+0xB0],edi        ; 清指针
    6ABEF6..0x6ABF08  对 [esi+0xB4] 同样处理
    6ABF0E  mov [esi+0x9C],1          ; 状态 = 1（读头）
    6ABF1F  call 0x6ABBC0

**裁定（PROVEN）：`[esi+0xB0]`/`[esi+0xB4]` 是 C++ 对象指针（先 `operator delete[]` 再经虚表析构），每次状态重置都会释放重建。**

## 2. 对象创建与注册（BLOCKED）

| 项 | 状态 |
|---|---|
| `0x6ABBC0` 对象的构造函数 | **未定位**（`0x6ABBC0` 是方法，不是构造者） |
| 对象分配点 | BLOCKED |
| 该对象是否注册到全局 | BLOCKED |
| 与 Demonware `bdSessionParams` 类型名的关联 | **INFERRED**（同簇，但无类型名到函数的直接绑定） |

**本轮未在 `.text` 中找到写入 `0x6ABBC0` 所在对象 vptr 或注册全局的指令**（扫描范围：立即数引用 + 数据指针，见 `_data/out_*`）。

## 3. 连接状态字段 +0xC8（PROVEN）

`0x6AA770`（清理）：

    6AA773  mov eax,[esi+0xC8]
    6AA779  cmp eax,1 / jne
    6AA77E  push 0 / call 0x6AA4B0     ; 状态 1 分支
    6AA787  cmp eax,4 / je
    6AA78C  call 0x6AA96E0             ; 其他状态
    6AA791  mov [esi+0xC8],4           ; 置状态 4
    6AA79B  lea ecx,[esi+0xC4]
    6AA7A2  jmp 0xB83B90               ; 传输对象清理

**+0xC8 是连接/会话状态（取值 1、2、4）**，与 +0x9C 的接收状态是不同字段。

## 4. 生命周期阶段（PROVEN / 部分 BLOCKED）

| 阶段 | 证据 | 等级 |
|---|---|---|
| 接收状态重置 | 0x6ABE99（清 +0xA4/+0xA8/+0xAC） | PROVEN |
| 子对象释放重建 | 0x6ABEB8/0x6ABEF6（+0xB0/+0xB4） | PROVEN |
| 传输对象清理 | 0x6AA7A2（jmp 0xB83B90 → +0xC4） | PROVEN |
| 连接状态迁移 | 0x6AA791（+0xC8 = 4） | PROVEN |
| 对象构造/分配 | — | **BLOCKED** |
| 全局注册 | — | **BLOCKED** |

## 5. 与 E-18 的 libcurl 对象对比

| 项 | E-18 libcurl 对象 | E-19 Demonware 会话对象 |
|---|---|---|
| vptr 写入点 | 0x776139 / 0x776188（已定位） | **未定位** |
| 对象大小 | 0x24 | 未定（≥0x109） |
| 分帧 | 无 | **有（4 字节长度前缀）** |
| 状态机 | 无 | **有（4 状态）** |

**注意：两者不共享 vtable，也不是同一对象族。**

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 接收状态字段重置 | PROVEN |
| 子对象生命周期 | PROVEN |
| 连接状态字段 | PROVEN |
| 对象构造者 | **BLOCKED** |
| 全局注册 | **BLOCKED** |
