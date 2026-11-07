# CODOL 复活项目 —— 总报告（2026-10-02）

本报告**只写可从原始数据重算的事实**，并明确区分
`[已测量]` / `[已证伪]` / `[未知]`。此前手册中反复改口的推断不再引用。

数据来源：
* 运行日志 `run_codol_001\runs\IFS1_*\aboprobe.stdout`（1027 轮）
* 静态分析 `SUBAGENT_VM_ISA.md`（2026-09-25，capstone + PE 节表）
* 运行期镜像 `CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin`

---

## 一、语料规模

| 项 | 值 |
|---|---|
| 总运行轮数 | **1027** |
| 有效轮（life ≥ 60 s） | **459** |

---

## 二、第一档五步的真实状态

| 步骤 | 状态 | 证据（在有效轮中的出现率） |
|---|---|---|
| ① 0x81 握手 | **闭合** | `LOBBY_READY_ONLY` 274/459 |
| ② 0x82 / +0x5FC | **闭合** | `LOBBY_5E8_READY` 279/459 |
| ③ 0x83 回显 | **闭合** | `LOBBY_ECHO_READY` 267/459 |
| ④ 0x85 帧 / AES-CBC / HMAC | **闭合** | `POST83_SAMPLE` 239/459 |
| ④' 接收侧解密可用 | **闭合** | `SET_P608_DECODED` 134/459，`LOBBY_SESSION_READY` 141/459 |
| ⑤ 进大厅 | **未闭合** | 459 个有效轮中 **无一例**进入大厅界面 |

关键副产物：**`644` 曾能达到非 0**

```
20260924 :  0/17      20260929 : 29/65   ← 曾经常态可用
20260925 :  0/ 6      20260930 :  0/74
20260927 :  0/13      20261001 : 10/81
20260928 : 36/104     20261002 :  0/99   ← 今天完全为 0
```

`[已测量]` 9-28/9-29 期间 35–45% 的有效轮里 `644` 变成过非 0。
今天 0/99。**这是我们自己工具链改动造成的**，不是游戏行为变化。

---

## 三、启动失败的真实分类（1027 轮）

| 退出码 | 数量 | 含义 |
|---|---|---|
| `0xFFFFFFFF` | **487** | 主要噪声源。9–14 s 退出，无弹窗，**原因未确定** |
| `0x00000000` | 27 | 正常退出（含 1 例带 `警告码`） |
| `terminated` | 17 | 探针超时收尾 |
| `0xC0000005` | 14 | 访问违规（假 DLL 实验造成，已还原） |
| `0xC0000409` | 9 | `__fastfail`（删 ACE 实验造成，已还原） |
| `0xE06D7363` | 2 | C++ 异常 |

`[已测量]` **`0xFFFFFFFF` 是最大的单一问题**：487 轮，占全部运行 47%。
它**与补丁、与 ACE、与 IIPS 均无关**（关掉 IIPS 后仍照常出现）。

---

## 四、已证伪的假设（不要重试）

| 假设 | 否证方式 | 结果 |
|---|---|---|
| ACE 阻止跨进程读内存 | 有效轮 460 次成功读、零 denied | **不成立** |
| `.text` 补丁被完整性校验干掉 | 13 处补丁 `ok=True`，游戏活满 110 s | **不成立** |
| 静态镜像因重定位失真 | 6 站点静态==运行时逐字节 | **不成立** |
| 需要 IAT 解密 / 重定向修复 | 补丁打在绝对地址且生效 | **不适用** |
| 删掉 ACE 游戏能跑 | 2.9–3.1 s `__fastfail` | **不成立** |
| 假 DLL 返回 0 能蒙混 | 2.0 s `0xC0000005` | **不成立** |
| 假 DLL 返回合法对象能满足 | 弹空提示，握手全不走 | **不成立** |
| `iipsinit` 窗口是闸门 | 关掉 IIPS 后仍死于 8.2 s | **不成立** |
| `PicFace` 缺失是原因 | 该轮活满 110 s 却无 PicFace | **不成立** |
| `0x638/0x63C` 的 token 是根因 | token=0 后门仍不开 | **不成立** |
| 已到达"逆向边界" | 每次声称后被新数据推翻 | **不成立** |

---

## 五、ACE 的真实结构（静态取证，`SUBAGENT_VM_ISA.md`）

### 5.0 先记一条最重要的发现：`644` 是我们自己弄坏的

`[已测量]` 按日期统计「有效轮中 `644` 曾变成非 0」的比例：

```
20260924 :  0/17        20260929 : 29/65   ← 45% 可用
20260925 :  0/ 6        20260930 :  0/74
20260927 :  0/13        20261001 : 10/81
20260928 : 36/104       20261002 :  0/99   ← 今天完全为 0
```

**两处工具链回归（都是自己造成的）：**

1. **驱动丢参数** —— `_e57a5c_experiment.py` 重写后不再传 `-PokeLobby644`，
   观察器从 09-30 起再没收到过它。
2. **观察器写错值** —— `AboProbe.cs` 里写成 `BitConverter.GetBytes((uint)0)`，
   本该写 `1`，且自述文字也写成 `target=0`。

修复后实测：

```
68.275  POKE_LOBBY_644   before=0 after=1   ← 写入成功
68.292  CODEC_TRANSITION c8=4  5e8=0 ...    ← 17 ms 后状态机复位
```

**⇒ 写入成功，但 17 ms 内被复位。这是唯一"修复后仍失败"的具体现象。**

**这条发现的代价**：因为从未回溯历史，我在 09-30 之后花了 18 个小节
去研究"为什么 644 恒为 0"，而它本可以在第一天用一个日期统计查出来。

| 结论 | 强度 |
|---|---|
| `.tvm0` 与所谓"引擎代码区"**0 字节重叠** | HIGH |
| 引擎窗口磁盘**非零** | HIGH |
| `.tls` 磁盘↔运行时是**非固定 XOR** 变换 | HIGH |
| 运行时引擎窗口**无绝对写指令** | HIGH |
| `.tvm0` 是高熵数据块，**不是典型 x86** | HIGH |
| **`.tvm0` 存在 VM dispatch loop** | **未证实** |
| 内嵌 OpenSSL 0.9.8zg / 1.1.0k，含完整 AES 表 | HIGH |
| AES key-expansion 候选 RVA `0x32090E/0x320A48/0x320BAE` | MEDIUM-HIGH |
| AES key 装载调用者 | **UNKNOWN** |

`[重要纠正]` 我在 2026-10-02 多次声称"ACE 核心是 VMProtect 虚拟字节码、
需要逆向虚拟机"。**这与既有静态取证不一致**：`.tvm0` 的 VM 性质
**从未被证实**，其头部字节反汇编为 `cli; pop ebx; inc edx`，不是合法入口。

**⇒ "必须逆向 VMProtect" 这一前提目前没有证据支撑。**

---

## 六、ACE 模块加载的实测

| 模块 | 是否被游戏加载 |
|---|---|
| `VSDDrvDll.dll` | 是（~1.7 s），导出 `CreateVSDIDrvObj` / `ReleaseVSDIDrvObj` |
| `ACE-DRV32.dll` | 是（~2.5 s），导出 `CreateObject` |
| `ace-ats32.dll` | 是（~5.1 s），导出 `Init` / `DllEntry2` / `GetObject1` / `GetObject2` / `CreateObject` |
| `tersafe.dll` / `policyprobe.dll` / `TenRpcs.dll` / `TenProxy.dll` | 是（依赖 `TCLS\` 存在） |

补上缺失的 `TCLS\`（172 文件）后：ACE 栈从 0/5 → 5/5，
`警告码(3;1045;19002)` 消失。

`[已测量]` `CreateVSDIDrvObj` 入口 `e9` 跳转，目标落在 `.vmp1`，
该区 4 KB 内 **256/256 不同字节值** = 高熵（加密）。

`[未知]` 运行时该目标是否解密为代码：探针在 t=1.5 s 读到**全零**，
之后无更新（重扫机制未生效或被跳过）。**这一测量尚未完成。**

---

## 七、0x87 门的完整链条（字节级验证）

```
0xBA3A18  89 8D 70FCFFFF   mov  [ebp-0x390], ecx
0xBA3A2A  74 39            je   0xBA3A65          ← 唯一出口（NOP 后 d4 0→1，4/4）
0xBA3A45  e8 7649fdff      call 0xBA37C0          ; 读 1 字节
0xBA3A4F  74 14            je   0xBA3A65
0xBA3A5F  77 04            ja   0xBA3A65
0xBA3A78  6a 01            push 1                 ; count=1
0xBA3A7A  8d 8d 76fcffff   lea  ecx,[ebp-0x38A]   ; dest
0xBA3A91  e8 2a49fdff      call 0xBA37C0          ; 再读 1 字节
0xBA3A9D  8a 95 76fcffff   mov  dl,[ebp-0x38A]    ; ← 内层类型字节
0xBA3AA3  88 95 77fcffff   mov  [ebp-0x389], dl
0xBA3AE0  8a 8d 77fcffff   mov  cl,[ebp-0x389]
0xBA3AE6  80 f9 87         cmp  cl, 0x87          ← ARM 门
0xBA3AE9  75 23            jne  0xBA3B0E
0xBA3AEB  81 bf 40060000 dc000000  cmp [edi+0x640], 0xDC
0xBA3AF5  72 3f            jb   0xBA3B36
0xBA3B02  e8 89faffff      call 0xBA3590          ; ARM（唯一写 644=1 处）
0xBA3B0E  80 f9 89         cmp  cl, 0x89
0xBA3B11  75 23            jne  0xBA3B36
0xBA3B2A  e8 d1faffff      call 0xBA3590          ; ARM（0x89）
0xBA3B36  8b bd 4cfcffff   mov  edi,[ebp-0x3B4]   ; 通用路径
```

`[已测量]`
* `[edi+0x640]` 在帧到达时 == **220 == 0xDC** → 第二道门 **PASS**
* `0xBA3590` 在整个镜像中**只被 `0xBA3B02` / `0xBA3B2A` 调用**
* 强制 `0xBA3AE9` 的 `jne` 为 `jmp` → 流程**消失**（d4=0、POST83 仅 1 次）
* `obj+0x5E0` 现可承载**真实内层字节**（修 `bl`→`dl` 后实测 `0x1C/0x39/0x78/0xB2/0xDC/0xF0`），**每轮不同、均非 0x87**

`[未知]` 内层读取的**源**。`0xBA46BD` 推入的 EDI 是**函数入口残留**
（0x85 分支从 `0xBA454E` 跳入，跳过 `0xBA45A5` / `0xBA4610` 两处 EDI 装载）。

---

## 八、已建立的可复现工具

### 8.0 操作手册（照抄即可）

**每次开工前必做：**

```powershell
# 1. 确认提权代理存活（需返回 debug_privilege: true）
python -X utf8 CODOLServer\_mainline\agent_client.py ping

# 2. 清理残留（含 ≥20 s 等待端口释放）
python -X utf8 CODOLServer\_mainline\_z7_cleanup.py 20
```

**标准一轮：**

```powershell
python -X utf8 CODOLServer\_mainline\_multiround.py --tag XX --need 1 `
  --patch-85-pass --patch-delay 42 --serve-delay 30 `
  --follow-85 --follow-85-rule receive --follow-85-cbc `
  --reply-85-cbc --reply-85-seqs 1,2,3,4 --reply-85-arm-first
```

**改观察器后必须重编译：**

```powershell
cd restore_iips_contract_001\observer2
dotnet publish -c Release -o out
```

**环境坑：**

| 现象 | 处理 |
|---|---|
| `life < 30 s` | 启动抖动，判为不可用，重跑 |
| 失败率升高 | 有残留进程，先清理 |
| PowerShell 长内联命令被拦 | 写成 `.py` 文件再跑 |
| `wmic` 对提权进程返回空 | 用端口 50508 识别代理，**不要**用命令行 |
| 清理脚本杀到自己 | 已修（排除自身与父进程） |

| 工具 | 路径 | 用途 |
|---|---|---|
| 观察器 | `restore_iips_contract_001\observer2\AboProbe.cs` | 进程内读写、事件记录 |
| 多轮驱动 | `CODOLServer\_mainline\_multiround.py` | 自动清理 + 多轮重试 |
| 主实验 | `CODOLServer\_mainline\_e57a5c_experiment.py` | 全部实验开关 |
| 本地大厅探针 | `CODOLServer\lobby_server\lobby_plain_probe.py` | 服务端应答 |
| 提权代理 | PID 17624，端口 50508 | 以管理员身份执行 |
| 清理脚本 | `CODOLServer\_mainline\_z7_cleanup.py` | 杀残留、查端口 |

关键开关：
```
--patch-85-pass      12 处 .text 补丁
--patch-delay 42     补丁时机（<40 s 会崩）
--serve-delay 30     探针延迟，把帧处理从 38.9 s 推到 ~69 s
--poke-lobby-644     恢复 9-28/9-29 的 644 写入（今天才接回）
--token              0x81 帧的 u64 令牌
```

---

## 九、当前唯一可信的下一步

`[已测量]` 修复 `644` 写入值后（`BitConverter.GetBytes((uint)1)`）：

```
68.275  POKE_LOBBY_644   before=0 after=1   ← 写入成功
68.292  CODEC_TRANSITION c8=4  5e8=0 ...    ← 17 ms 后状态机复位
```

**写入成功但 17 ms 内被复位。** 这是唯一一个"修复后仍然失败"的具体现象，
也是唯一有确定抓手的问题。

---

## 十、必须记住的三条纪律

1. **先测再断。** 本项目的多次反复，根因都是"基于错位读数推因果"。
   指令级结论必须给逐字节位置 + `E8` 目标合法性交叉校验。
2. **回溯历史。** `644` 的可用性统计只需一次脚本，却能省掉 18 个小节。
   任何"某状态恒为 X"的断言，必须先按日期统计。
3. **区分三种强度。** `[已测量]`（可重算）/ `[已证伪]`（有否证实验）/
   `[未知]`（无证据）。不得把 `[未知]` 写成结论。
