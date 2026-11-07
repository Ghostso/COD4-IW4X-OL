# IIPS 组件篡改取证报告

日期：2026-09-25
结论等级：**已证实（Authenticode 签名判定 + 逐字节 diff，非推测）**

---

## 0. 一句话结论

`COD OL\IIPS\iips.dll` **确实被修改过**，但**不是腾讯在停服时改的**，
而是 **2026-09-21 本机被替换成了工程自己手搓的代理/打桩版本**，
且替换时把**原版 Authenticode 签名整体照搬**过来，导致签名状态变为 `HashMismatch`。

腾讯原版仍然完整存在于本机：`工具\EX035_DIR\IIPS\iips.dll`（签名 **Valid**）。

---

## 1. 判据：Authenticode 签名状态

签名是唯一可靠的"内容是否等于腾讯签发时"的判据。**签名 Valid 无法伪造**，
因为摘要覆盖整个 PE 镜像（除证书区本身）。若把 A 的签名贴到 B 上，结果必然是
`HashMismatch`。

| 文件 | SHA256(前 8) | 大小 | 签名状态 |
|---|---|---|---|
| `工具\EX035_DIR\IIPS\iips.dll` | `72DDB9D1` | 347704 | **Valid** |
| `COD OL\IIPS\iips.dll`（当前生效） | `E2367C48` | 347704 | **HashMismatch** |
| `工具\EB1_SANDBOX\IIPS\iips.dll` | `2ED47824` | 380928 | NotSigned |
| `restore003\sandbox_B\IIPS\iips.dll` | `032FAC66` | 352256 | NotSigned |

其余 IIPS 组件均为 **Valid**（未被改动）：

```
IIPSHostApp.exe      Valid
IIPSHost.dll         Valid
iips_policymsg.dll   Valid
codoMP_client_shipRetail.exe  Valid
```

=> 被改的**只有 `iips.dll` 一个文件**。

---

## 2. 决定性证据：签名被"照搬"

两个文件的证书区**逐字节相同**：

```
cert blob @ file offset 0x53000, size 0x1E38
sha256(ORIG cert)    = 696fc2815bae9720b32827709452d38483a2d14e2aa54f2b3df530cbb2f37447
sha256(CURRENT cert) = 696fc2815bae9720b32827709452d38483a2d14e2aa54f2b3df530cbb2f37447
identical = True
```

即：被改版**保留了原版签名**。正因如此它才显示 `HashMismatch` 而不是
`NotSigned`——签名存在，但摘要对不上被改过的内容。这是"事后篡改"的指纹。

---

## 3. 时间与扩散：25 份被改版 vs 8 份原版

```
sha256 72DDB9D1... (Valid)        : 8 份，mtime 全部 = 2026-09-10 00:07:33（解包时间）
sha256 E2367C48... (HashMismatch) : 25 份，mtime 全部 = 2026-09-21 20:52:32
```

- 原版时间戳 = 整包解包时间 9/10，与目录内其它 250+ 个文件完全一致。
- 被改版时间戳 = 9/21 20:52，**远晚于解包、且远晚于 2024 年停服**。
- 被改版已扩散进 25 个沙箱/运行目录。

=> 修改行为发生在**本机工程期间**，不是停服日。

---

## 4. 篡改内容：精确位置（347704 字节中 849 字节被改，97 段）

PE 结构未变（段表、目录表、导入表、导出名、导出函数体全部一致），
改动集中在三处：

### 4.1 `.text` RVA 0x1000 —— 函数被替换为打桩

```
原版：c7 01 18 3d 03 10   ff 25 98 32 03 10
      mov dword ptr [ecx], 0x10033D18 ; jmp dword ptr [0x10033298]
      （std::exception 派生类析构 thunk；0x10033298 = IAT 槽
        -> MSVCR80.dll ??1exception@std@@UAE@XZ）

被改：b8 78 56 34 12   c3   c3
      mov eax, 0x12345678 ; ret ; ret
```

`mov eax, 0x12345678; ret` 是**人工打桩**的典型特征（返回魔数常量）。

### 4.2 `.rdata` RVA 0x33000 —— IAT 区被覆盖

该区正是 PE 数据目录 `IAT (index 12) rva=00033000 size=000004AC`。

```
原版前 0x30 字节：2af90300 16f90300 42f90300 ...   （合法 IAT 槽，指向 ILT）
被改前 0x30 字节：4765745265736f757263654d616e61676572494900...
                  = ASCII "GetResourceManagerII\0ReleaseResourceManagerII\0"
```

**IAT 区被 ASCII 字符串 + 一张手写的导出目录覆盖。**
（磁盘上的 IAT 只是 ILT 副本、加载时会被改写，所以这本身不致命；
但它证明该文件是**手工构造的替换品**，而非腾讯产物。）

### 4.3 `.data` RVA 0x42000 起 —— 全局指针表成片清零

```
原版：dc3c0310 b2bd0210 10350310 ...   （指向 .text/.rdata 的函数/对象指针）
被改：00000000 00000000 00000000 ...
```

成片清零的全局槽 + 连续 128 字节的函数指针数组被抹平，
这是 IIPS 运行时状态（单例、vtable 指针、初始化标志）所在区域。

---

## 5. 与成因的对应：为什么这解释 `[100]`

工程早先文档已经写明该路线的性质：

```
ICH029_COMPAT_SURFACE.md :
  IMPLEMENTATION: DLL proxy (replace iips.dll with local implementation)

_ebo1_mkproxy.py 文件头 :
  "a COPY of iips.dll with an embedded, position-relocatable Local RM object
   so GetResourceManagerII/GetResourceManager return a valid RM from the very
   first call"

RESTORE_LOCALRM_006_DECISION.md :
  原版导出 GetResourceManagerII -> new 0x410 对象 / 48 槽 vtable
```

=> 当前生效的 `iips.dll` 是**用桩替换 IIPS 实现的代理版**。
IIPS 管道、共享内存、HostPid 握手全部不复存在，于是：

```
ResourceManagerII::Initialize() -> 失败 -> WIN_IIPS_INIT_ERROR (8189FEC)
-> UI 抛 [100] 无法连接大厅服务
```

这解释了 `IIPS_ROOT_CAUSE.md` 观测到的现象：
`IIPSHostApp` 起得来但**不创建管道、不写 HostPid**——
因为调用方早已被换成桩，根本没有真实 IIPS 初始化序列。

---

## 6. 纠正工程内的一条错误基线

以下文档把**被改版**当成了"原始"：

```
RESTORE_LOCALRM_005_DECISION.md  : ORIGINAL_IIPS_INTEGRITY = BYTE_IDENTICAL
RESTORE_LOCALRM_006_DECISION.md  : SHA256 E2367C48...347704 bytes
                                   "mtime unchanged (2026-09-21 20:52:32)"
```

`E2367C48` 的签名是 `HashMismatch`，**不可能是腾讯原版**。
这些文档写于替换之后，把"当时磁盘上的文件"误当成了原始基线。

真原始 = `72DDB9D1...`（签名 Valid，mtime 2026-09-10 00:07:33）。

---

## 7. 原版副本位置（可立即回退）

```
工具\EX035_DIR\IIPS\iips.dll              347704  sha 72DDB9D1  Valid  2026-09-10 00:07:33
工具\EX053_BASELINE\IIPS\iips.dll         347704  sha 72DDB9D1  Valid  2026-09-10 00:07:33
工具\EX053_IFS2_PATH_A\IIPS\iips.dll      347704  sha 72DDB9D1  Valid
工具\EX053_IFS2_PATH_A\EX035_DIR\IIPS\iips.dll  同上
工具\EX053_IFS2_PATH_B\IIPS\iips.dll      347704  sha 72DDB9D1  Valid
工具\EX053_IFS2_PATH_B\EX035_DIR\IIPS\iips.dll  同上
工具\EX053_IFS2_PATH_C\IIPS\iips.dll      347704  sha 72DDB9D1  Valid
工具\EX053_IFS2_PATH_C\EX035_DIR\IIPS\iips.dll  同上
```

另有完整原始 IIPS 目录快照（含全部 ini）：
`工具\EX035_DIR\IIPS\`（32 个文件，时间戳全为 2026-09-10）。

### 配置差异（同时被改的）

```
工具\EX035_DIR\iips.ini  (46 B, 原版) : enable_iips=1 / iips_url="http://10.231.2.181/"
COD OL\iips.ini          (17 B, 现版) : enable_iips=0
```

`10.231.2.181` 是腾讯内网地址，现已不可达；把它指向本地可自建策略服务。

---

## 8. 建议的下一步（按优先级）

1. **回退 `iips.dll` 到 `72DDB9D1`（签名 Valid）**，并归档当前被改版以便 A/B。
2. 恢复 `iips.ini` 为 `enable_iips=1`，`iips_url` 指向本地（如 `http://127.0.0.1:PORT/`）。
3. 观察 `IIPSHostApp` 是否开始创建命名管道并写入 `IIPS\HostPid`。
   - 若开始写 HostPid => IIPS 层修复成功，游戏将推进到 TQoS/GDP 网络层。
   - 若仍失败 => 检查 `IIPSPolicySvrInfo\Address=udp://ctrl.iips.qq.com:8000` 是否需本地应答。
4. 只有走到第 3 步之后，`gdp_server.py` 的大厅协议才有机会被触达。

## 9. 本轮工具

```
CODOLServer\_mainline\_s3_iips_forensic.py   签名/哈希/逐字节 diff 取证（可复跑）
```
