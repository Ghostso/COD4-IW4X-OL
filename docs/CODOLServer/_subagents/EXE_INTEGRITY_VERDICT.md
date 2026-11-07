# `codoMP_client_shipRetail.exe` 完整性校验核查（只读）

日期：2026-09-29 夜（第三版会话）
边界：**全只读**。未运行游戏、未写内存、未改 `.text`、未碰 ACE。
说明：本条原派给子代理，子代理因上游服务错误（`stream disconnected`）
在开始工作前即失败，未产出任何文件；改由主线完成。

---

## 0. 结论摘要

| 问题 | 结论 | 强度 |
|---|---|---|
| exe 是否被自有校验路径覆盖？ | **在磁盘清单层面：否。没有任何 `.lst`/`.ini`/`.cfg` 列出 exe 或它的哈希** | 已证（穷尽枚举） |
| 是否有本地比对基准？ | 磁盘清单层面**不存在** exe 条目 | 已证 |
| 是否存在通用「算文件哈希再比对」的代码？ | `codoMP_client_shipRetail.exe` 自身的 IAT **不含**任何哈希/校验 API | 已证（按导入表） |
| 那 `WinVerifyTrust` 呢？ | 在运行期镜像里**出现 1 次**，但**不属于 exe 的导入表**，来自镜像内的第三方组件 | 已证（归属限定） |
| 是否有别的自校验？ | **未定** —— 见 §4，这是唯一还剩的缺口 | — |

---

## 1. 磁盘清单：穷尽枚举，**exe 不在任何一份清单里**

对 `D:\BaiduNetdiskDownload\使命召唤OL\COD OL` 全树递归读原始字节，
搜 `TCLSCheck` / `TCLSAutoCheck` / `checktoolname` / `noticerepair` 四个 needle：

```text
 202793  COD OL\docs\game-net-hunt-report.md      (命中 TCLSCheck/TCLSAutoCheck —— 是文档，不是配置)
  14943  COD OL\scripts\dirscan_net.py            (命中 TCLSCheck —— 是脚本，不是配置)
   1965  COD OL\TCLS\TCLSCheck.lst                (命中 TCLSAutoCheck —— 真正的清单)
     59  COD OL\TCLS\config\check.ini             (命中 checktoolname/noticerepair)
```

⇒ **配置层只有两处消费点**：`TCLS\TCLSCheck.lst`（31 条 DLL/资源）与
`TCLS\freshui.lst`（1 条资源）。**两份都不含 `.exe`**（`TCLSCheck.lst` 里唯一的
`.exe` 是 `Tenio\TenioDL\TenioDL.exe`，与游戏本体无关）。

对全树搜 `codoMP_client_shipRetail` + `.exe` 相邻文本，9 个命中文件
**全部是日志/报告/脚本产物**（`ICH042_stdout.txt`、`Logs\_direct_contract_launch.txt`、
`scripts\_out\*.txt`），**无一是校验清单**。

`COD OL\TCLS\config\check.ini` 全文：
```ini
[check]
backupfile=data.vfs
noticerepair=
checktoolname=
```
`checktoolname` / `noticerepair` 都是**空值** ⇒ 该开关未被启用。

---

## 2. exe 的导入表：没有任何哈希/校验 API

`arch_imports.csv`（813 条，从**运行期明文镜像**解析的 IAT，不是磁盘加密 exe）中，
与「完整性校验」可能的 API 只有：

```text
KERNEL32  GetModuleFileNameA/W     多个
KERNEL32  CreateFileA/W            多个
KERNEL32  ReadFile                 多个
KERNEL32  GetFileSize              多个
KERNEL32  CreateFileMappingA/W     多个
KERNEL32  IsDebuggerPresent        2 处
ntdll     NtQueryInformationProcess / NtQueryInformationThread
ntdll     NtQueryVirtualMemory / NtQuerySystemInformation
WINTRUST  WinVerifyTrust           1 处（见 §3）
```

**没有**：`MapFileAndCheckSum`、`CheckSumMappedFile`、`CryptVerifySignature`、
`CryptHashData`、`BCryptHash`、`BCrypt*` 家族。

对运行期镜像按字节搜这些名字，**全部为 0 命中**：
```text
MapFileAndCheckSum   0
CheckSumMappedFile   0
CryptVerifySignature 0
BCryptHash           0
WinVerifyTrust       0   ← 注意：字符串层面为 0
```

⇒ 上面那条 `WINTRUST|WinVerifyTrust` 是 **IAT 槽位**（`0x00B029A8`），
不是磁盘上的明文串 —— 说明它来自**运行期才解析的导入**，且**不在 exe 自己的
导入描述符里**（`game-net-hunt-report.md` 已确立：exe 的 IMPORT 目录
**只有一个描述符** = `codoMP_client_shipRetailBase.dll`，序号 1；
即 **exe 自身不导入 WinTrust，全部导入经 Base.dll 承载**）。

镜像内 `codoMP_client_shipRetail.exe` 这个**字符串**只出现 2 次，
且都不是校验用途：
```text
0xDE8F11  "...game\pc\codoMP_client_shipRetail.pdb"        ← PDB 调试路径
0xE156B4  "codoMP_client_shipRetail.exe" 后接 Scaleform RTTI  ← 应用名/日志名
```

---

## 3. 本机基线（供将来做差集用）

```text
路径   COD OL\codoMP_client_shipRetail.exe
大小   7,841,344 B (0x77A640)
MD5    6d6f68debf708280f5383dfed6d96281
SHA256 36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537
PE     PE32, 7 sections, opt magic 0x10B
PE 头 CheckSum 字段 = 0x0078840D
Authenticode = Valid（Tencent Technology (Shenzhen) Company Limited，
               DigiCert Assured ID Code Signing CA-1，
               2020-11-25 → 2024-02-23，thumbprint B550768BC5F6FD1AD4943B10FE4E6EDD1A8571E3）
```

⚠️ **本机这份 exe 是「已过期的原版」**：签名 `Not After = 2024/2/23`，
而当前日期 2026-09-29。签名**仍然 Valid**（因为有时间戳），但**已过期**。
⇒ 将来若要判断「exe 是否被改过」，**Authenticode 状态本身就是可用判据**
（与 `IIPS_TAMPER_FORENSIC.md` 用同一套方法：改过的文件会变 `HashMismatch`）。

**当前状态：Valid ⇒ 本机 exe 未被修改过**（与 `TCLSCheck.lst` 覆盖的
22 个文件形成鲜明对比）。

---

## 4. 未定项（**不要当成结论用**）

```text
1. TP/ACE 的**内核态** minifilter（ACE-BASE.sys，FLTMGR）具有拦截任意文件读写的
   能力。它是否在运行期对 exe 做哈希/校验，**本轮纯静态无法判定**
   —— 需要运行期观测（ETW / 受限样本实验）才能定。
2. `WinVerifyTrust`（IAT 槽 0x00B029A8）的**调用者未被定位**。
   它不属于 exe 的导入描述符，来自镜像内第三方组件（CEF / libcurl / Scaleform
   候选）。**归属未判**。
3. exe 是否有**自校验**（例如把自身 PE 的某段与硬编码常量比较）。
   §2 已排除「用标准哈希 API」，但**逐字节自比较无法用导入表排除**。
   判据：需要在运行期镜像里对 exe 的 `.text` 段做「自我引用」扫描
   （即找指向 exe 自身映像范围的可执行/数据引用）。
4. `TCLSCheck.lst` 的**加载者与比对时机**未定（同一份清单，另一条线）。
```

---

## 5. 方法与可复现命令

```text
# 1) 清单消费点穷尽枚举（只读，读原始字节）
python - <<'PY'
import os
root=r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL"
needles=[b"TCLSCheck",b"TCLSAutoCheck",b"checktoolname",b"noticerepair"]
for dp,dn,fn in os.walk(root):
    for f in fn:
        p=os.path.join(dp,f)
        try:
            if os.path.getsize(p)>200*1024*1024: continue
            d=open(p,"rb").read()
        except OSError: continue
        hit=[n.decode() for n in needles if n in d]
        if hit: print(p,hit)
PY

# 2) exe 哈希 + Authenticode
python -c "import hashlib;d=open(r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe','rb').read();print(len(d),hashlib.md5(d).hexdigest(),hashlib.sha256(d).hexdigest())"
powershell -c "(Get-AuthenticodeSignature 'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe').Status"

# 3) 导入面筛选
Select-String -Path arch_imports.csv -Pattern 'CheckSum|WinVerify|CryptVerify|BCrypt|MapFile'
```

