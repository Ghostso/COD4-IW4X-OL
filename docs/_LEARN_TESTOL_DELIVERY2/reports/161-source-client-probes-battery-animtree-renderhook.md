# 161 · 客户端侧探针与钩子：电池查号、animtree、渲染帧上传

## 一、范围

本报告完整学习 **3 个头文件**：

- `ClientBatteryLookup.hpp`（21 行）
- `ClientAnimtreeHook.hpp`（48 行）
- `ClientRenderFrameHook.hpp`（199 行）

## 二、`cg` 指针是 XOR 混淆的，不是 `table[localClientNum]`

```cpp
selector = read(base + 0x7EC3B58)
if (selector >= 64 || !encoded) return {};
encoded  = read(base + 0x181D188 + selector*4)
cg       = encoded ^ 0xFBB2C97A
```

注释：

> `cg` 是 `table[selector] XOR FBB2C97A`，**不是 `table[localClientNum]`**。活体客户端用 selector 5 和 3。**64 项边界是保守的读取守卫，不是恢复出来的原生数组声明。**

这正是"地址混淆"在客户端侧的实例——与 `BG_EvaluateTrajectory` 的 `0x410EA0`（接受地址混淆 base）是同一套机制。

### 2.1 后续四个校验

```cpp
commandTime = read(cg)            // 必须非零
pmType      = read(cg+4)          // 必须 == 0
health      = read(cg+0x1A4)      // 必须非零
client      = read(cg+0x158)      // 必须 < 18
```

注释指出一个陷阱：

> `+0x1A4`（420）是复制的 health `stats[0]`。**`+20C` 是服务端 Pmove 的影子，在两个活客户端里都保持为零。**

即：**同名字段有两份，只有一份是活的**。用 `+0x20C` 会永远读到 0。

`client < 18` 与之前报告里 18 个客户端槽完全一致。

## 三、animtree 钩子：为什么必须是钩子而不是探针

### 3.1 那段"找的是已不存在的状态"

> §12.139 确立：名字→资产的查表**只在它发生的那一刻可观察**。`sub_40B210` 在地图加载时解析六个 animtree 名字，把返回的指针存进 `ctx58 + 0x17E784` 的六项表，**然后这些记账就被释放了**——被 intern 的字符串引用计数降到零，它的注册链表被回收。**从 §12.135 起的每一个事后探针都在寻找已不存在的状态。**

### 3.2 它回答什么问题

> 我们的第 3 列解析到 **519 项**的描述符，而零售的解析到 **123 项**（§12.124），**而这一个差异解释了 T-pose、冻结动画和表面上的坏出生点**（§12.122、§12.133）。钩子按每次解析记录：**被要求的名字、返回的指针、以及该指针处的条目数**。对我们的比赛跑一次、对 demo 跑一次，两份日志并排，**差异是被归因出来的而不是推断出来的**。

### 3.3 站点是五字节 call 重定向

```text
0040B288  8B 11        mov  edx,[ecx]      名字指针
0040B28A  52           push edx
0040B28B  E8 60 FA 33 00  call sub_74ACF0   ← 被替换的五字节
0040B290  83 C4 04     add  esp,4          CALLER 清理，cdecl
0040B293  89 06        mov  [esi],eax      存进六项表
```

注释：

> **一个五字节 call 重定向。**钩子用同样的参数调原始函数并无改动地返回它的结果，所以**语义上是透明的**；唯一效果是一行日志。**原始字节在任何写入之前都被校验，与 `installClientProcessPatches` 完全一样，不匹配就拒绝而不是打补丁。**

`AnimtreeHookResult` 六态，其中 `UnexpectedBytes` 与 `ProtectionFailed` 分开——字节不符与内存保护改不动是两回事。

## 四、渲染帧钩子：为什么不能在 `Com_Frame` 里做 D3D

### 4.1 实测证据

```text
device BehaviorFlags  0x42   FPU_PRESERVE | HARDWARE_VERTEXPROCESSING
                             —— 没有 D3DCREATE_MULTITHREADED
thread 16016  Com_Frame      0x4FEA20       923 次 / 5 s
thread 43208  sub_BE21F0     0xBE21F0       923 次 / 5 s
              且每一次 BeginScene、Clear 和 SetRenderTarget
```

> 2026-09-09 实测。**两者精确同步，一个渲染帧对应一个 Com_Frame，但在不同线程上。**没有 `D3DCREATE_MULTITHREADED`，设备上的每一次调用都必须来自创建它的那个线程，**所以从 Com_Frame 回调驱动的上传是在跨线程调设备。**

### 4.2 站点

```text
00BE220B  50              push eax
00BE220C  8B D8           mov  ebx,eax
00BE220E  E8 3D FF FF FF  call sub_BE2150   ← 被替换的五字节
00BE2213  83 C4 04        add  esp,4         CALLER 清理，cdecl
```

`sub_BE2150` 是调 `BeginScene` 的那个，所以钩子在 **BeginScene 之前**运行——**这正是纹理上传应该在的位置**。

### 4.3 尾跳让它与调用约定无关

> 替换体跑完泵之后**尾跳到 `sub_BE2150`，栈保持不变**，所以原始函数自己的 `retn` 直接返回到调用点。**这使钩子与调用约定无关——它永远不需要知道 `sub_BE2150` 接受几个参数。**

### 4.4 fiber 上下文

> `sub_BE7470` 开头是 `sub_67C170(1, sub_BE0900)`，一次 **fiber 切换**而不是线程跳转。**当调用者已经在上下文 1 上时它立即返回**，否则让出直到 `sub_BE0900` 为真。
>
> 从渲染帧测，`sub_67C080()`（`sub_67C170` 用的同一个槽位计算）返回 **1**，而 `sub_BE0900` 是 `sub_67CCE0() || sub_67C080() == 1`，所以**在那个位置谓词已经满足**。**泵仍然读槽位并在不是 1 时拒绝，因为猜错的失效方式是 `Error("1190")`。**

### 4.5 已被证实的整条链

> 2026-09-09，正是这个序列——暂存 blob、在渲染帧回调里调 `sub_BE7470`、然后 `DB_LinkXAssetEntry(10)`——**把七张 PPSh 图片发布进了一个活客户端**：
>
> - `image+0` 从 load-def 指针变成一个真实的 `IDirect3DTexture9`，其 vtable（`0x6c6f1438`）**与每一张随包图片携带的逐字节相同**；
> - load def 搬迁到 `+0x2C`；
> - category 从 3 变成 **11**（暂存路径加的 +8）；
> - 全部 52 个 header 字节通过链接存活；
> - XAsset 条目表之后能找到每一个名字。
>
> 那次跑是通过 Frida（`tools/runtime/CodolForgeImageProbe.py`）驱动的，因为不需要重编译；**本代码是 DLL 里的同一序列，它本身还没有被跑过。**

最后一句很重要：**证据来自 Frida 版本，DLL 版本尚未运行**。

### 4.6 状态机

```text
Queued / WrongFiberSlot / RendererClosed / UploadFaulted
NoTexture / LinkFaulted / LinkRefused / Published
```

`WrongFiberSlot` 对应 4.4 的槽位检查；`RendererClosed` 对应 `LoadForerRendererDvarRva` 处 `*(dvar+12)` 为零；`NoTexture` 是"`sub_BE7470` 返回了但 `image+0` 仍为空"。

### 4.7 队列语义

> 图像被**移动**并在进程生命周期内保持存活：引擎复制 52 字节 header 但保留内部的指针，**所以存储永远不能被释放**。
>
> **钩子未安装时返回 false**——向一个永远不会跑的钩子入队是**静默挂起，不是延迟**。

### 4.8 为什么必须从进程内发布

> 从注入线程发布可行，且已按资产类型逐个证实，**但它不能存活**：**一次 zone 切换会移除 Material、GfxImage 和 XAnimParts 条目，并把 XModel 改写成缺失模型的默认值，而一个已经存在的名字不能通过链接重新指向。**所以每一次从外部跑都在和下一次地图加载赛跑。
>
> **从这里发布没有这个问题**，因为它可以发生在**客户端即将运行的 zone 之后**——渲染帧钩子是每帧第一个跑的东西，而它跑的时候，地图自己的资产已经加载完了。

### 4.9 顺序由阶段强制

> 图片必须在材质能绑它们之前存在，材质必须在模型能命名它们之前存在。泵**每帧做一张图片**，然后材质，然后模型。

`ForgeChainPhase`：`Idle / Images / Materials / Models / Done / Failed`。

### 4.10 前置失败不留半发布

> 读 bundle、暂存所请求模型需要的每一张图片，并排队三个阶段。**如果 bundle 无法读取或请求没有命名任何可发布的东西，返回 false 并设置 `error`——那种情况下什么都不入队，所以一个坏请求不能让客户端处于半发布状态。**

### 4.11 目录模式的语义取自文件名后缀

```text
_c  colour    2
_n  normal    5
_s  specular  8
```

> 这是随包 `MaterialTextureDef` 携带的，也是 PPSh 自己的材质对这六个名字的期望。

### 4.12 四个 RVA

```text
RenderFrameCallSiteRva  = 0x7E220E   (0x00BE220E)
RenderFrameTargetRva    = 0x7E2150   (0x00BE2150)
ImageUploadRva          = 0x7E7470   (0x00BE7470)
FiberSlotRva            = 0x27C080   (0x0067C080)
LoadForRendererDvarRva  = 0xA899CC   (0x00E899CC)
```

最后一条注释：**`sub_BE7470` 除非 `*(dvar+12)` 非零否则什么都不做。**

## 五、关键结论

1. **`cg` 是 XOR 混淆的**，选择子来自 `base+0x7EC3B58` 且活体只用 5 和 3；64 是守卫不是声明。
2. **同名字段有两份**：`+0x1A4` 是活的 health，`+0x20C` 是服务端 Pmove 影子恒零。
3. **只在发生时可观察的东西必须用钩子**；事后探针只能找到已释放的状态。
4. **五字节 call 重定向 + 原字节校验 + 不匹配就拒绝**是本项目所有钩子的统一纪律。
5. **尾跳让钩子与调用约定无关**——这是不依赖 `sub_BE2150` 参数个数的关键。
6. **跨线程调 D3D 是硬约束**（无 `D3DCREATE_MULTITHREADED`），所以上传必须挂渲染帧而不是 `Com_Frame`。
7. **从进程外发布不能存活**：zone 切换会抹掉 Material/GfxImage/XAnimParts，且已存在的名字不能重新指向。

## 六、未闭合点

- DLL 版本的渲染帧上传**尚未运行**（只有 Frida 版本被证实）。
- `sub_67C080` 的槽位计算在非渲染线程上的行为未测。
- 材质与模型两个阶段的具体实现不在本头文件。
