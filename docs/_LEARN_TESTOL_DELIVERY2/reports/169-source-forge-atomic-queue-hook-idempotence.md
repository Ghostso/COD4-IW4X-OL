# 169 · Forge 链的原子入队、钩子的幂等与"故意不卸载"

## 一、范围

本报告学习 **2 处实现**：

- `ClientRenderFrameHook.cpp` 640–780 行
- `ClientCommandTrace.cpp` 279–413 行

## 二、`queueForgeChain` 的"先全建，再入队"

```text
1. 收集 materials（去重）与 images（去重）
   某个 model 命名的 material 不在 bundle 里 → 整体拒绝，错误信息带 model 名与 material 名
2. 对每张 image：
      file = root / "main" / "images" / (name + ".iwi")
      打不开 / 读不出 → 整体拒绝
      semanticFor(texture.semantic) 从引用它的 material 反查
      SV_BuildForgeGfxImageFromIwi → 失败则整体拒绝
3. 全部成功后才写 Chain 状态
4. 最后一次循环逐张 queueForgeImageUpload(link=true)
```

### 2.1 为什么 `semantic` 要约两次

`semanticFor` 有两个重载：按 **sampler 名**（`normalMap`→5）与按**文件名后缀**（`_n`→5）。

这里用的是**反查**：

```cpp
imageRequest.semantic = 2;                       // 默认 colorMap
for (每个 material) for (每个 texture)
    if (texture.image == imageName)
        imageRequest.semantic = semanticFor(texture.semantic);
```

即：**从"哪个 material 用了我这张图"反推语义**，而不是自己猜文件名。默认 2 是最保守的回退。

## 三、图像的构建与链的启动是**两个阶段**

```cpp
// 全部构建在 built 里
std::vector<std::unique_ptr<SvForgeGfxImage>> built;
for (...) built.push_back(...);

// 全部成功后才启动链
{ std::lock_guard lock(ChainMutex); Chain.phase = Images; Chain.active = true; ... }

// 最后才入队
for (auto &image : built) queueForgeImageUpload(std::move(image), true);
```

注释：

> **在排队任何东西之前构建每一张图**，所以一张坏的会拒绝整个请求，**而不是让客户端处于半发布状态**。

这与之前 `SV_LoadForgeBundle` 的"闭集验证"是同一纪律，只是层次不同：**bundle 那层拒绝形状错误，这一层拒绝文件缺失**。

### 3.1 但入队失败只返回 false 不清理

```cpp
if (!queueForgeImageUpload(std::move(image), true))
{
    error = "the render-frame hook refused image " + name;
    return false;
}
```

此时 Chain 已经 active、部分图片已入队。**注释说"不该半发布"，但这一段确实可以半发布** —— 唯一的触发条件是钩子被中途卸载，而 `Installed` 一旦置 true 就不会清。这是一个理论上的不一致，实际不可达。

## 四、`queueForgeImageDirectory`：目录批量模式

```text
is_directory 检查 → 失败 "not a directory"
遍历 directory_iterator，只挑 .iwi（扩展名 tolower）
排序（sort）           ← 让结果稳定
report.found = files.size()
对每个：打不开 → failures 记录 "cannot open"，【继续】而不是中止
```

与 `queueForgeChain` 的关键差别：**这里是批量工具，单个失败继续；链是事务，单个失败全拒**。

## 五、重建时的幂等：**不重复打补丁**

```cpp
// ALREADY INSTALLED IS NOT AN ERROR. Re-running the diagnostic should start a new file
// against the hook that is already there, not patch the prologue a second time -- the
// second patch would copy the JMP as its own "original" and the client would recurse
// into itself on the next command.
if (Trampoline)
{
    Recording.store(true);
    return true;
}
```

这是本组最重要的一段：**二次打补丁会把 `E9 <rel32>` 当作"原始序言"复制进 trampoline**，于是 trampoline 跳回钩子，钩子跳到 trampoline——**自递归，在第一条命令上崩**。

注意顺序：**先开文件、写表头、重置计数，再判断是否已安装**。所以重跑会得到**新文件**，而钩子保持原样。

## 六、`_fsopen` + `_SH_DENYWR` 而不是 `fopen`

```text
CRT 的 fopen 直接拒绝共享：
    实测，客户端持有文件时 PowerShell 与 python 都打不开，
    所以追踪只在客户端停止录制后才可读 ——
    对"看着十分钟 demo 跑过去"无用，而如果客户端崩溃就更无用，而那正是值得追踪的事情之一。
```

`_SH_DENYWR` = 允许别人**读**、只拒绝别人**写**。所以外部工具能实时跟读。

## 七、序言校验：把崩溃变成一行日志

```cpp
static constexpr std::uint8_t Expected[StolenBytes] = { 0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x08 };
if (!std::equal(begin(Expected), end(Expected), target))
{
    std::fprintf(Output,
        "0,0,?,,REFUSED,0,\"prologue at RVA 0x%zX is not 55 8B EC 83 EC 08 -- "
        "this build moved sub_614C00; nothing was patched\"\n", ClientCommandDispatchRva);
    std::fflush(Output);
    return false;
}
```

注释：

> **拒绝一个不是测量过的那个序言。**如果一个构建移动了这个函数，**给现在那里的东西打六字节补丁就是客户端毫无解释地死掉的方式**。检查只花一次比较，**把一次崩溃变成一行日志**。

**注意拒绝信息写进了 CSV 本身**（`verb=?`、`dispatch=REFUSED`），所以看追踪文件的人直接看到原因，不需要另找日志。

## 八、六字节窃取的填充

```cpp
target[0] = 0xE9;
*(int32*)(target + 1) = &dispatchHook - (target + 5);
target[5] = 0x90;                        // 第六个被偷字节，填充
```

`E9` + 4 字节 rel32 = **5 字节**，第 6 字节是 `NOP`。

这是与 `FrameHook.cpp`（5 字节全用）和 `DisconnectWitness.cpp`（10 字节用 5 + 5 NOP）**不同的第三种配比**：**5 + 1**。

`VirtualProtect` 恢复在 `FlushInstructionCache` **之前** —— 与 `FrameHook.cpp` 的顺序相反（那里是先 flush 再恢复）。两者都对，因为 flush 不需要页可写。

## 九、卸载**故意**不做

```cpp
void stopClientCommandTrace()
{
    // THE HOOK IS LEFT IN PLACE ON PURPOSE. Unpatching means writing six bytes back into a
    // function another thread may be executing at that instant, for no gain -- the hook
    // costs a predictable branch and a flag test once every few hundred milliseconds. Only
    // the RECORDING stops.
    Recording.store(false);
    ...
}
```

理由有三层：

1. **还原意味着往另一个线程可能正在执行的函数里写六个字节** —— 有撕裂风险；
2. **没有收益**：钩子成本是一次可预测分支 + 每几百毫秒一次标志测试；
3. 所以**只停录制**。

`record()` 的第一行就是 `if (!Recording.load(relaxed)) return;`，所以停录后钩子几乎零成本。

## 十、状态字符串

```text
"client command trace: not installed"
"client command trace: RECORDING|stopped, N command(s) written, M unreadable, -> <path>"
```

**`Recorded` 与 `Unreadable` 并列**——正如之前报告指出的，"读到"与"读不出"必须都能看到。

## 十一、关键结论

1. **事务式入队**：先全部构建成功，再启动链，最后才入队。
2. **幂等必须是"不重复打补丁"**，否则 trampoline 会把跳转指令当成原始字节，形成自递归。
3. **`_SH_DENYWR` 而不是 `fopen`**，否则外部工具在客户端运行时读不到。
4. **序言不符时把原因写进输出文件本身**，让看文件的人直接看到。
5. **窃取长度的填充有三种配比**（5、5+5、5+1），取决于目标指令边界。
6. **卸载钩子比保留更危险**——只停录制。

## 十二、未闭合点

- `queueForgeChain` 入队阶段的失败不清理已入队项（理论不一致，实际不可达）。
- playerstate 镜像与 fps 探针的实现仍未在本组读取。
