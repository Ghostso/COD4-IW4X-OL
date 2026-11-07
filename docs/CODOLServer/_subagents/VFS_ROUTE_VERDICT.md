# VFS 路线判定：**否证**。引擎不通过任何 VFS 读资源

日期：2026-09-30（第三版会话）
边界：**全只读**。未运行游戏、未写内存、未改 `.text`、未碰 ACE。

---

## 0. 结论（一句话）

**「用 VFS 挂载点喂资源、绕过签名」这条路走不通。**
游戏引擎读 `.ff` 用的是**它自己的 `IffFileSystem` 层 + 直接 Win32 文件 API**，
**完全不碰** `IIPSVFS.dll` / `Tenio\VFS.dll`。

强度：**已证**（三重独立证据，见 §1–§3）。

---

## 1. 决定性证据：引擎镜像里根本没有 VFS 的符号

对运行期明文镜像（`image_best.bin`，base 0x400000）按字节穷尽搜索：

```text
ICreateVFileSys      0     ICreateFileSysMgr    0
ICreateGeneralFileSys 0    ICreateFileMapper    0
ICreateBufferCache   0     ICreateHandleAlloc   0
ICreateCoderRWFilter 0     ICreateZlibRWFilter  0
IIPSVFS.dll          0     VFS.dll              0
CreateVFS            0     SequenceVFS          0     ReleaseVFS   0
[VFS_TRACE]_mount path %s %s     0
[vfs]Create vfs Sys Suceess!     0
```

⇒ 游戏主体**从不** `LoadLibrary("IIPSVFS.dll")`、也不 `GetProcAddress` 它的任何导出。
*（`_mount` 有 8 个字节命中，但全是 `_mountains` 的子串假阳性 —— 已逐一核对。）*

---

## 2. 引擎自己的文件系统层是 `IffFileSystem`

`0x483DB0` 读 `.ff` 头部时，先 `call 0x484B70` 初始化，而 `0x484B70` 里出现：

```asm
00484BC1  push 0xDB6154          ; "mp_playlists"
00484BC7  call 0x774710          ; 路径拼接
00484B8C  mov [0x1CD1788], 0x1C51780   ; 结构指针
00484BAA  call 0x484760
```

`0x483DB0` 随后与两个魔数比较：

```asm
00483DF4  cmp edx, [ecx + 0xDB5EE0]   ; 0xDB5EE0 = "IWff0100"
00483E14  cmp edx, [ecx + 0xDB5EEC]   ; 0xDB5EEC = "IWffu100"
00483E3B  cmp eax, 0x1CD              ; 0x1CD 版本号
00483E4A / 00483E55  push 0xDB5F08 "283 %s %d %d" / 0xDB5F18 "284 %s %d %d"
```

⇒ 这是**引擎自带的 `IffFileSystem`**（`IWff` 家族），**与腾讯那套 VFS 无关**。

---

## 3. `.ff` 的实际打开路径是 `CreateFile` + `CreateFileMapping`

`0x49ED40`（把 zone 名变 `"%s.ff"` 的那个函数）内部：

```asm
0049ED5A  push 0xDB617C          ; "%s.ff"
0049ED71  call 0x774900          ; sprintf 路径
0049ED7B  call 0x77B3B0          ; 路径规范化（内部 push "mp_" @0xDDA690 / "_load" @0xDB6578）
0049ED94  call 0x776FA0          ; ← 打开文件
```

`0x776FA0` 解析后**是纯 Win32**：

```asm
00776F73  lea ecx, [ebp-0x108]              ; 路径
00776F79  call dword ptr [0xCA8208]         ; CreateFileW/A
          （6 个 push：0x80000000 访问、1 共享、3 OPEN_EXISTING、
                       0x60000000 标志、0、0 模板）
```

另有 `0x776F00` 是**同一函数的父级**（`0x776FA0` 在它内部被调用），
同样走 `CreateFile` + `CreateFileMapping` 系列。

⇒ 路径 = **`sprintf("%s.ff")` → 规范化 → `CreateFile`**。
**中间没有任何 VFS 接口调用。**

---

## 4. 这套 VFS 是给谁用的：只有腾讯自己的工具链

`IIPSVFS.dll` 里的 PDB 路径自证来源：
```text
f:\code\iips_proj\QQSpeedVFS\Output\Release\PDB\TenKart.pdb
"[vfs] QQSpeed"
```
（`QQSpeed` = 腾讯《QQ飞车》，`TenKart` = 其内部代号）

⇒ 它是**腾讯游戏通用的资源加密层**，被 `IIPS*` / `Cross\` / `TPHelper\` 用，
**不被 IW 引擎用**。盘上的 `.vfs` 文件（`Cross\Res.vfs` 等）全部属于
腾讯平台侧，不属于游戏侧。

---

## 5. 这条否证**没有**关闭的东西

```text
· VFS 路线仅对「腾讯平台侧的 UI 资源」成立（例如 TPFUI 的 PNG），
  对「引擎的 zone/.ff 加载」不成立。
· 与第一档 ⑤ 的因果关系：**无关**。⑤ 卡在 gate=0（见 HANDOFF §15），
  不是卡在资源读取方式。
```

## 6. 附带确认（对 §15 的补充证据）

`0x49ED40` 里对 zone 名做了两类前缀测试，字符串在案：

```text
0xDB656C  "patch"
0xDB6574  "ez_"
```

再加上 `0x49E410` 里的 `patch_*` 家族（`patch_common_marketplace_lite` 等），
⇒ **`patch_` 前缀的 zone 名是引擎真实会去构造的**，
不是归档扫描出来的噪声。但盘上任何 `.ifs` 里都没有对应 `.ff`
（`RESOURCE_MOUNT_AUDIT_20260929.md` 已证）。

---

## 7. 可复现命令

```text
# 1) 引擎镜像里搜 VFS 符号（全部应为 0）
python -c "
p=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin'
d=open(p,'rb').read()
for n in (b'ICreateVFileSys',b'IIPSVFS.dll',b'CreateVFS',b'[VFS_TRACE]_mount path %s %s'):
    print(n, d.count(n))
"

# 2) 反汇编 zone 打开路径
python CODOLServer/_mainline/_dis_va.py 0x49ED40:0x49EE20
python CODOLServer/_mainline/_dis_va.py 0x776FA0:0x777000     # -> call [0xCA8208] = CreateFile
python CODOLServer/_mainline/_dis_va.py 0x483DB0:0x483EE0     # -> cmp "IWff0100" / "IWffu100"

# 3) 字符串常量
python CODOLServer/_mainline/_str_at.py 0xDB5EE0 0xDB5EEC 0xDB5F08 0xDB617C 0xDDA690
```

