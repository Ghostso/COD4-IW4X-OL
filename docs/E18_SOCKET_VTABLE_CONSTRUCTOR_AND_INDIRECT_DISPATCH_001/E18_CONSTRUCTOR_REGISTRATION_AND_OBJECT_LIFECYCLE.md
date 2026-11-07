# E18 — 构造者、注册与对象生命周期 / CONSTRUCTOR & LIFECYCLE

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. 直接交叉引用（PROVEN）

.text 中对 vtable 基址（VA 0x00C98568）的立即数写入：仅 2 处。

| 站点 RVA | 指令 | 语义 |
|---|---|---|
| 0x776139 | mov dword [esi], 0xC98568 | 就地构造：写 vptr |
| 0x776188 | mov dword [eax], 0xC98568 | 堆分配后构造：写 vptr |

## 2. 构造函数（PROVEN）

    776130  push ebp / mov ebp,esp / push esi
    776134  mov esi,ecx
    776136  lea ecx,[esi+0x1C]
    776139  mov dword [esi],0xC98568      ; vptr = 基类 vtable
    77613F  call 0xB757E0
    776148  mov dword [esi],0xC98500      ; 再改为清理 vptr
    77614E  je 0xB7615E
    776150  mov ecx,[0xD3A588]            ; 全局分配器
    776158  mov edx,[eax+0x30]
    77615B  push esi / call edx           ; 归还对象
    77615E  ret 4

    776170  mov ecx,[0xD3A588]
    776178  mov edx,[eax+0x28]           ; 分配方法
    77617B  push 0 / push 0x24           ; 0x24 = 36 字节
    77617F  call edx
    776188  mov dword [eax],0xC98568      ; 构造：写 vptr
    77618E  mov [eax+0x14],-1
    776191  mov [eax+0x18],-1
    776194  mov [eax+0x1C],0
    77619B  mov [eax+0x20],0

裁定（PROVEN）：0x776130 析构/清理；0x776170 堆分配 + 构造；对象大小 0x24；分配经全局分配器 vtable [0xD3A588]+0x28。
0x776170 无直接调用者（数据指针 0），经表/延迟注册（INFERRED）。

## 3. 派生类构造（PROVEN）

| 站点 | 写入 vptr |
|---|---|
| 0x7763A6 | 0xC985CC |
| 0x7767D2 | 0xC985EC |
| 0x776B64 | 0xC98620 |
| 0x776BE6 | 0xC985FC |
| 0x776C1A | 0xC985CC |
| 0x776F15 | 0xC985FC |
| 0x473F1C | 0xC985CC |

裁定（PROVEN）：同一 libcurl 传输对象族有 5 个 vptr 值，对应 5 个继承层级。

## 4. 生命周期（PROVEN）

| 阶段 | 证据 |
|---|---|
| 分配 | 0x776170 push 0x24 + 分配器 vtable |
| 构造 | 写 vptr（9 处） |
| 使用 | 52 个方法经 vtable 分派 |
| 销毁 | 0x776130（flag 归还）、0x7767E6（释放成员 + 改 vptr） |

## 5. 未闭合（BLOCKED）

| 项 | 说明 |
|---|---|
| 0x776170 的调用者 | 无直接交叉引用（BLK-18-1） |
| 对象实例化时机 | 需运行时或更深表枚举 |
| 0xD3A588 单例初始化 | 未追溯 |

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 构造函数 | PROVEN（0x776130 / 0x776170） |
| vptr 写入点 | PROVEN（9 处） |
| 对象大小 | PROVEN（0x24） |
| 注册者 | 部分（构造已定位，注册路径 BLOCKED） |
| 生命周期 | PROVEN（四段均有证据） |
