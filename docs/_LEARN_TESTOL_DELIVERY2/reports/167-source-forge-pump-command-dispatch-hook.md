# 167 · Forge 链的泵、上传钩子的尾跳、命令分派钩子（节流大小是目标属性）

## 一、范围

本报告学习 **2 处实现**：

- `ClientRenderFrameHook.cpp` 280–470 行
- `ClientCommandTrace.cpp` 前 100 行

## 二、模型发布：360 字节从定长数组转到 vector

```cpp
ref.name = model.name;
ref.header.assign(model.header.begin(), model.header.end());   // array<byte,360> → vector
ref.boneNames / parentList / quaternions / translations
ref.partClassification / baseMatrices
ref.materials = model.materials;
if (!model.resources.empty()) ref.resource = model.resources.front();
```

注释：

> bundle 把 360 字节作为定长数组携带；ref 要 vector，**而尺寸检查属于 `SV_BuildForgeXModel`**。

即：这里**不做尺寸校验**，只做类型转换——校验在构建器里统一做。

`ref.resource = model.resources.front()` —— **只用第一个**，与之前报告里 `lodInfo[0].name` 只认一个 loose resource 一致。

两个解析器都是**只读表遍历**：

```cpp
SV_ForgeStringTableResolver(hostBase())
SV_ForgeMaterialTableResolver(hostBase())
```

## 三、`pumpChain`：每帧一步，让卡顿在阶段里可见

```cpp
std::unique_lock lock(ChainMutex, std::try_to_lock);
if (!lock.owns_lock() || !Chain.active) return;

if (phase == Images) {
    if (PendingCount != 0) return;         // 等图片队列排空
    phase = Materials; return;
}
if (phase == Materials) {
    if (materials.empty()) { phase = Models; return; }
    name = materials.front(); materials.erase(begin());
    ok = publishOneMaterial(...);
    note("material " + name, ok, error);
    return;                                 // 一帧一个
}
if (phase == Models) { 同上 }
```

注释：

> **每帧一步，所以一次停滞在阶段里可见。**

这是设计选择：**不追求快，追求"卡住时能看出卡在哪一步"**。而 `Chain.steps` 是完整的步骤日志（`ForgeChainStep{what, ok, detail}`）。

`try_to_lock` 与上传队列同一纪律：**队列线程永远不能卡住一帧**。

## 四、`pumpImageUploads`：两级快速路径

```cpp
if (PendingCount.load(relaxed) == 0) {
    pumpChain();      // 图片做完了，材质和模型可以开始
    return;
}

Job job;
{
    std::unique_lock lock(QueueMutex, std::try_to_lock);
    if (!lock.owns_lock() || Pending.empty()) return;
    job = std::move(Pending.front());
    Pending.erase(Pending.begin());
    PendingCount.store(Pending.size(), relaxed);
}
if (!job.image) return;

ForgeImageUploadRecord record; record.name = job.image->name;
record.status = uploadOne(job, record);

{ std::lock_guard lock(QueueMutex); Records.push_back(record); Retained.push_back(std::move(job.image)); }
```

### 4.1 为什么每帧只做一张

> **每帧一张。**一张 512×512 DXT5 链是 **349,552 字节**穿过 `LockRect` 与 `UpdateTexture`；**一帧做六张就是一次卡顿。**

### 4.2 为什么图片排空才开始材质

材质要 `resolveImage()` 找到图片；图片没发布时查找会失败。所以链的阶段顺序**不仅是逻辑依赖，也是时序依赖**。

## 五、`renderFrameHook`：尾跳的完整形态

```asm
pushad
pushfd
call pumpImageUploads
popfd
popad
jmp dword ptr [RenderBegin]
```

注释：

> **按构造透明**：跑泵，然后带着**与调用点留下时完全相同的栈**尾跳到原始函数，**所以它自己的 `retn` 返回 `0x00BE2213`，而调用者的 `add esp, 4` 仍然平衡。这里没有任何东西需要知道 `sub_BE2150` 的签名。**

与 `FrameHook.cpp` 的对比很明确：

| | FrameHook | RenderFrameHook |
|---|---|---|
| 形式 | `call [OriginalComFrame]` 先跑原始 | `jmp [RenderBegin]` 尾跳 |
| 返回 | 自己的 `ret` | 原始函数的 `retn` |
| 需要知道签名 | 否（直接 call 指针） | 否（尾跳） |
| 栈平衡 | 自己负责 | 原始函数负责 |

两者都"不知道签名"，但方式不同：前者借 `call reg` 不关心参数，后者借尾跳把整个返回链交还给原始函数。

## 六、PE 头自检

```cpp
module = GetModuleHandleW(nullptr);
dos = (IMAGE_DOS_HEADER*)module;
if (dos->e_magic != IMAGE_DOS_SIGNATURE) return nullptr;
nt = (IMAGE_NT_HEADERS*)(module + dos->e_lfanew);
if (nt->Signature != IMAGE_NT_SIGNATURE) return nullptr;
imageSize = nt->OptionalHeader.SizeOfImage;
return module;
```

**两级签名校验**（`MZ` 与 `PE\0\0`），然后取 `SizeOfImage`——这是给 `VirtualQuery` 之外的范围检查用的。

## 七、语义推断：后缀 + 变形名

```cpp
semanticForName(name):
    tail = name.substr(size-2)
    "_n" → 5   "_s" → 8   "_c" → 2
    // CoD4 管线把合并贴图改写成 `~<name>_s-...~<hash>`
    name.find("_s-") → 8
    name.find("_n-") → 5
    默认 → 2
```

注释点明了一个真实存在的命名变形：

> CoD4 管线把合并的贴图**改名**成 `~<name>_s-...~<hash>`，**所以后缀没了但角色仍可读**。

这与之前报告里 alpha Barrett 的 17 张图片中有 4 张是 `~…&…` 变形名是同一现象。

**注意这个方法与 `semanticFor(sampler)` 是不同的**：前者按**文件名后缀**，后者按**sampler 名**。两条路径都存在，各有各的适用场景。

## 八、`ClientCommandTrace`：窃取大小是**目标**的属性

### 8.1 六字节不是五字节

```text
RVA 0x214C00   55 8b ec 83 ec 08  53 56 57  8b f8  a1 ...
                push ebp / mov ebp,esp / sub esp,8 / push ebx / push esi / push edi
                mov edi, eax          ← EAX 在入口是序列号
```

注释：

> **六字节，不是五字节。**前三条指令占 1 + 2 + 3 字节，所以**五字节窃取会把 `sub esp, 8` 切成两半，客户端会在第一条命令上就死掉**。
>
> **`FrameHook` 的 `HookSize = 5` 正确只是因为 `Com_Frame` 的序言恰好落在五字节边界上**（`55 8b ec 56 57`）。
>
> **尺寸是目标的属性，不是钩子的属性。**

这是本组最重要的一条方法论：**每个钩子站点必须单独确认窃取长度**，不能沿用别处的常数。

### 8.2 命令文本不是参数

```text
base = dword_331C0C8 ^ 0xD362501F        (RVA 0x2F1C0C8，混淆指针)
cmd  = base + 524628 + ((seq & 0x1FF) << 10)
```

注释：

> 命令文本**不是参数**。`sub_614C00` 从一个 **512 槽环**里把它读出来。
>
> **512 槽 × 1024 字节。`(seq & 0x1FF)` 是镜像自己陈述环大小的地方，独立于最初确立它的线格式测量。**

即：**512 这个数字在客户端代码里就能读到**（`& 0x1FF`），不必只依赖线测量。这与之前报告里"`reliableAcknowledge & 1FFh` 的掩码是 512"是同一条事实的第二个证据源。

### 8.3 混淆指针

```cpp
constexpr std::size_t CommandRingBaseRva = 0x2F1C0C8;
constexpr std::uint32_t CommandRingBaseKey = 0xD362501F;
```

与 `ClientBatteryLookup` 的 `cg = table[sel] ^ 0xFBB2C97A` 是同一种模式——**同一个小节里两个不同的 XOR 键**。

### 8.4 `readable()`：五层检查

```cpp
if (!address) return false;
VirtualQuery → info
if (info.State != MEM_COMMIT) return false;
if (info.Protect & (PAGE_NOACCESS | PAGE_GUARD)) return false;
start = info.BaseAddress; end = start + info.RegionSize;
return address + bytes <= end;
```

**五个维度**：非空、查询成功、已提交、非 NOACCESS/GUARD、**不跨区域边界**。

最后一条最容易被忽略：`VirtualQuery` 只告诉你**这个地址所在区域**的大小，**如果请求的字节数超过该区域剩余部分，就跨到了另一个可能不同的区域**。

注释：

> 一个尚未建立的环指针是空或垃圾，**而一个在它观察的分派内部 fault 的追踪比没有追踪更糟**。

### 8.5 三个原子计数

```cpp
std::atomic<std::uint64_t> Recorded{};
std::atomic<std::uint64_t> Unreadable{};
std::atomic<bool> Recording{};
```

`Unreadable` 与 `Recorded` 分开——**"读到"与"读不出"各自计数**，所以"追踪没输出"与"追踪输出全空"是可区分的。

## 九、关键结论

1. **窃取长度是目标的属性**：同一个项目里 `Com_Frame` 是 5、`sub_614C00` 是 6，因为序言指令边界不同。**不能跨站点复用常数。**
2. **每帧一步让停滞在阶段里可见**——这是"可诊断性优先于吞吐"的选择。
3. **尾跳与 `call reg` 都"不知道签名"，但机制不同**：前者把返回链交还原始函数，后者借间接 call。
4. **`readable()` 必须检查跨区域边界**，`VirtualQuery` 只报告当前区域。
5. **"读不出"要单独计数**，否则追踪失效与追踪无内容无法区分。
6. **文件名的语义推断有两条路径**（后缀 与 `~..._s-` 变形），因为管线会改名。

## 十、未闭合点

- Forge 链的 `queueForgeChain` 前置解析不在本次读取范围。
- `ClientCommandTrace.cpp` 100 行之后的钩子安装与记录逻辑未在本组。
