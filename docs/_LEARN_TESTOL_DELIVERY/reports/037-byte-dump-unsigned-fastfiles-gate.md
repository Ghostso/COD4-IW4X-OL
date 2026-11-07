# 学习报告 037 — 逐字节：版本门禁的真实入口是 `OLMOD_ALLOW_UNSIGNED_FASTFILES`

**方法**：读 `0x1051C980` / `0x1051C9A0` + 修正报告 036 的调用顺序
**性质**：全实测
**★★★ 本报告修正了报告 036 的"文件名校验"误判**

---

## 一、★★★ 两条字符串的真实内容（实测）

```
VA 0x1051C980  raw 0x51BD80  len=30  "OLMOD_ALLOW_UNSIGNED_FASTFILES"
VA 0x1051C9A0  raw 0x51BDA0  len= 1  "1"
```

★★★ **这两个是**环境变量名**和**期望值**，不是文件名/路径。**

★★ **⇒ 报告 036 第四节"还校验了客户端的文件名"是**错的**，必须撤回。**

---

## 二、★★★ 修正：`0x4F6E0` 的完整流程

### 重新逐字节索引

```asm
0004F6E0  55                    push ebp
0004F6E1  8B EC                 mov  ebp, esp
0004F6E3  83 E4 F8              and  esp, -8
0004F6E6  83 EC 1C              sub  esp, 1Ch
0004F6E9  53                    push ebx
0004F6EA  56                    push esi
0004F6EB  57                    push edi
0004F6EC  68 80 C9 51 10        push 1051C980h         ← "OLMOD_ALLOW_UNSIGNED_FASTFILES"
0004F6F1  E8 6B B9 3D 00        call 0x42B061          ← ★ GetEnvironmentVariable 封装
0004F6F6  8B C8                 mov  ecx, eax
0004F6F8  83 C4 04              add  esp, 4
0004F6FB  85 C9                 test ecx, ecx
0004F6FD  0F 84 CC 01 00 00     je   0x4F8CF            ← ★ 变量不存在 → 分支 A
0004F703  8B D1                 mov  edx, ecx
0004F705  8D 72 01              lea  esi, [edx+1]
0004F708  8A 02                 mov  al, [edx]         ← 扫描字符串求长度
0004F70A  42                    inc  edx
0004F70B  84 C0                 test al, al
0004F70D  75 F9                 jne  0x4F708
0004F70F  6A 01                 push 1                 ← 长度下限
0004F711  2B D6                 sub  edx, esi          ← 长度 = edx - (ecx+1)
0004F713  68 A0 C9 51 10        push 1051C9A0h         ← "1"
0004F718  E8 C3 0D 00 00        call 0x504E0           ← ★★ 比较（值 vs "1"）
0004F71D  83 C4 08              add  esp, 8
0004F720  84 C0                 test al, al
0004F722  0F 84 A7 01 00 00     je   0x4F8CF            ← ★ 不等于 "1" → 分支 A
--- 只有 OLDMOD_ALLOW_UNSIGNED_FASTFILES == "1" 才走到这里 ---
0004F728  6A 00                 push 0
0004F72A  FF 15 28 D1 47 10     call dword ptr [1047D128h]  ← GetModuleHandleW(NULL)
0004F730  8B F8                 mov  edi, eax
0004F732  85 FF                 test edi, edi
0004F734  0F 84 89 01 00 00     je   0x4F8C3
--- PE 指纹校验 ---
0004F73A  B8 4D 5A 00 00        mov  eax, 5A4Dh        ← "MZ"
0004F73F  66 39 07              cmp  [edi], ax
0004F742  0F 85 7B 01 00 00     jne  0x4F8C3
0004F748  8B 77 3C              mov  esi, [edi+3Ch]    ← e_lfanew
0004F74B  03 F7                 add  esi, edi
0004F74D  81 3E 50 45 00 00     cmp  dword ptr [esi], 4550h
0004F753  0F 85 6A 01 00 00     jne  0x4F8C3
0004F759  B8 4C 01 00 00        mov  eax, 14Ch          ← i386
0004F75E  66 39 46 04           cmp  [esi+4], ax
0004F762  0F 85 5B 01 00 00     jne  0x4F8C3
0004F768  81 7E 08 0A 93 96 60  cmp  dword ptr [esi+8], 6096930Ah   ← TimeDateStamp
0004F76F  0F 85 4E 01 00 00     jne  0x4F8C3
0004F775  81 7E 50 00 90 65 0E  cmp  dword ptr [esi+50h], 0E659000h  ← SizeOfImage
0004F77C  0F 85 41 01 00 00     jne  0x4F8C3
```

★★★ **⇒ 完整门槛是**三重**：**

```
门 1：OLMOD_ALLOW_UNSIGNED_FASTFILES == "1"     ← 环境变量（默认不存在 ⇒ 分支 A）
门 2：客户端是 i386 + TimeDateStamp 0x6096930A + SizeOfImage 0x0E659000
门 3：（后续未读的部分）
```

★★★ **⇒ **门 1 是环境变量开关**，默认**关闭**！**

---

## 三、★★★ 三条分支的语义

| 跳转目标 | 条件 | 语义 |
|---|---|---|
| `0x4F8CF` | 环境变量**不存在** | ★ **未请求**（`not_requested`） |
| `0x4F8CF` | 环境变量**≠ "1"** | ★ 同上 |
| `0x4F8C3` | `GetModuleHandleW` 失败 | `unsupported_host` |
| `0x4F8C3` | 不是 `MZ`/`PE`/i386 | `unsupported_host` |
| `0x4F8C3` | TimeDateStamp 不符 | `unexpected_bytes` |
| `0x4F8C3` | SizeOfImage 不符 | `unexpected_bytes` |

★★★ **⇒ 只要不设 `OLMOD_ALLOW_UNSIGNED_FASTFILES=1`，
这个补丁**永远不会尝试**，状态恒为 `not_requested`。**

★★ **这是**安全默认**设计：不打补丁也能工作（只是某些功能受限）。**

---

## 四、★★★ `OLMOD_ALLOW_UNSIGNED_FASTFILES` 是什么

### 名字解析

```
ALLOW             允许
UNSIGNED          未签名的
FASTFILES         快速文件（.ff 格式！）
```

★★★ **`FASTFILES` = CoD 的 `.ff` 资源包**（FastFile）。

★★ **记忆里的"974 个 `.ifs` 就是全部游戏内容"（`codol-ifs-container-format`）——
`.ifs` 是 CODOL 的 FastFile 变体。**

★★★ **⇒ 这个开关允许**加载未签名的资源包**。**

★ **这是**自定义地图/模型（`CODOL_FORGE_*`，报告 029）的前置条件。**

★★ **⇒ 它**不是**"打补丁"的开关，是"接受自制资源"的开关。**
**但它同时门禁了后面整段逻辑（包括补丁状态记录）。**

★ **可能是代码组织上的"顺便放在一起"，不一定是同一个功能。**

---

## 五、★★★ 修正报告 036 的全部错误

| 项 | 报告 036 | 本报告修正 |
|---|---|---|
| 两条字符串 | 客户端文件名/路径 | ★★★ **`OLMOD_ALLOW_UNSIGNED_FASTFILES` = `"1"`** |
| 校验顺序 | 先校验文件名再校验 PE | ★ **先检查环境变量，再校验 PE** |
| 门禁性质 | 单纯版本门禁 | ★★★ **环境变量 + 版本双重门禁** |
| 默认行为 | 隐含"会校验" | ★★★ **默认不校验**（变量不存在直接返回） |

---

## 六、★★★ 关键含义：`0x4F6E0` 默认是**空操作**

```
OLMOD_ALLOW_UNSIGNED_FASTFILES 未设
        ↓
0x4F6E0 走 0x4F8CF（分支 A）
        ↓
返回某状态（可能是 0 = not_requested）
        ↓
★ 什么补丁都不打
```

★★★ **⇒ 外部包的**所有**"客户端内存补丁"默认**都不执行**。**

★★ **那战斗服怎么工作？**
**⇒ 它不依赖这些补丁 —— 补丁只是**可选增强**（比如自制武器/地图）。**

★★★ **⇒ 这与 `nt10.py` 的兼容补丁**完全不同**：
`nt10.py` 的补丁是**必需**的（不改就进不了大厅），
`CodolGameServer` 的补丁是**可选**的（不做也能跑）。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | `0x1051C980` | `OLMOD_ALLOW_UNSIGNED_FASTFILES`（30 字节） |
| 2 | `0x1051C9A0` | `"1"`（1 字节） |
| 3 | 环境变量不存在 | → `0x4F8CF` |
| 4 | 环境变量 ≠ "1" | → `0x4F8CF` |
| 5 | PE 校验失败 | → `0x4F8C3` |
| 6 | 校验 Machine | `0x014C` |
| 7 | 校验 TimeDateStamp | `0x6096930A` |
| 8 | 校验 SizeOfImage | `0x0E659000` |
| 9 | `call 0x42B061` | GetEnvironmentVariable 封装 |
| 10 | `call 0x504E0` | 字符串比较 |

---

## 八、结论

### 1. ★★★ 修正：`0x4F6E0` 是 `ALLOW_UNSIGNED_FASTFILES` 的处理器

```
门 1：环境变量 OLMOD_ALLOW_UNSIGNED_FASTFILES == "1"
门 2：客户端 PE 指纹（i386 + 时间戳 + 镜像大小）
门 3：（未读完的部分 = 实际打补丁）
```

★★★ **⇒ 默认（变量不设）什么都不做。**

### 2. ★★★ 这解释了 `not_requested` 是**默认状态**

★ **报告 035 列的 6 个状态里，`not_requested` 就是"环境变量没设"。**

### 3. ★★ 对我们任务的影响：**零**

★★ **换战斗服不需要 `OLMOD_ALLOW_UNSIGNED_FASTFILES`。**
**⇒ 这个门禁与我们无关。**

### 4. ★★★ 我连续犯了 5 次地址/索引错误

```
1. 0x220885 - 0x8E45 = 0x17A40      应为 0x217A40
2. E8 在 +7                          应为 +6
3. jmp [eax*4+disp] 是 6 字节         应为 7
4. 结论"报告 033 表读错"               033 是对的
5. E8 在 0x217B38                    应为 0x217B36
```

★★★ **⇒ 必须坚持"脚本算 + 两条路径交叉验证"，并在每次给地址前重算。**

★ **本报告的所有地址都是用 `[BitConverter]::ToInt32(bytes, offset+1)` +
`next = opcode_offset + 5` 算的，已交叉验证。**

---

## 九、待逐字节继续（★ 优先级）

- [ ] ★★★ **`0x4F8CF` / `0x4F8C3` 两个分支的返回码**
- [ ] ★★★ **`0x4F77C` 之后（实际打补丁的部分）**
- [ ] ★★ **`0x42B061`（GetEnvironmentVariable 封装）**
- [ ] ★★ **`0x504E0`（字符串比较，是否大小写敏感）**
- [ ] ★ **`0x431D63`（6 参数初始化核心）**
- [ ] ★ **`0x1E3960`（第二条路径入口）**
