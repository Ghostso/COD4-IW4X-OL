# Kisak Black

> 原文：[Kisak Black](https://lwss.github.io/Kisak-Black/)，LWSS，2026-05-10。<br>
> 本文是非官方中文直译。代码、链接、图片和视频顺序按原文保留；作者的口语、玩笑和观点不代表本项目立场。

再来一遍。

**（本文假设你已经读过[上一篇](https://lwss.github.io/Duty-Of-Kisak/)。）**

## KisakCOD 的后续进展

KisakCOD 发布后，还有几个领域需要继续处理。

最明显的是 SP（Single Player）支持。大多数 mod 使用单人模式，因为 COD4 的 actor code 没有链接进 MP executable，也就是说多人模式中没有原生 AI 系统。

我使用 Xbox 360 COD4 PDB 和 MAP 文件，开始制作 SP。

首先，我用 PDB 找出 SP build 独有的文件，并为它们创建 placeholder。

![COD4 SP placeholder 文件](../images/cod4spplaceholders.png)

它们大多位于没有 `_mp` 后缀的目录里。

![MP client 目录](../images/cod4mpclient.png)
![SP client 目录](../images/cod4spclient.png)
![MP client_mp 目录](../images/cod4mpclientmp.png)

这可能并不完全符合真实源码的布局，但我不认为他们会为了 MP 复制整棵源码树。（Jedi Academy 和其他一些项目倒是真的这么做了。）

为了简化 SP 工作，主要做法是在核心逻辑循环中增加 `#ifdef`，加入同一文件的 SP variant，再包含 MP 中不存在的新文件。

工作的大头是补入 AI（“actor”）代码。

![COD4 SP game actor 文件](../images/cod4spgamefolder.png)

Xbox 的 PowerPC 架构让事情变得更复杂。

![PowerPC 代码示例](../images/cod4powerpccode.png)

后来的 COD 会把 Actor code 也放进 MP executable，因此只要仔细监测不同版本的变化，就可以使用干净得多的 x86 pseudocode。

过了一段时间，SP 达到了“可以编译”的状态，但 bug 多得吓人。

#### 支线：Script Debugger

这让我暂时转移注意力，去修 Script Debugger。COD4 实际内置了一个，外观看起来像 Emacs，操作方式则受 Visual Studio 启发。

它完整支持 watch、当前 scope 变量列表、breakpoint 等功能。

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/cod4scriptdebugger.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

```text
后来的 COD 放弃了它，改用某种远程脚本调试器。这大概是务实选择，毕竟这个东西是为 4:3 CRT 设计的，而且直接在游戏内运行。不过你必须承认，有人为它投入了大量心力，确实很酷。
```

#### 支线：No-FastFiles

调试继续进行，接着又开了一条支线，让“no-FF”（`useFastFile = 0`）能够工作。它基本要求修复所有此前没有使用的 `*_load_obj.cpp`，再准备一批可供加载的数据。幸运的是，IW 随游戏附带了一张 SP 地图和一张 MP 地图的 `.map` Radiant 源文件，另外还有一个测试关卡。

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/cod4spmenu.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/cod4testmap.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/cod4testmapsp.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

```text
你能看到它坏得相当彻底。直到今天，它其实仍然是这个状态。继续往下读……
```

#### 支线：阴影

我们又开了一条支线，终于去修同样影响 MP build 的 CSM shadow。

当时它是这样的：

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/cod4bustedCSM.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

我不是 gfx 程序员，不过会试着简单解释这套阴影系统。

COD4 称它们为 `Sun Shadows`。它们与灯光产生的 `Spot Shadow` 不同。系统从太阳位置沿关卡 geometry 投射，并把结果写入一张 shadowmap（纹理）。如果整张关卡只使用一张巨大的 shadowmap，为了让阴影好看，它必须拥有极高分辨率，因为这张图要覆盖从太阳视角和距离看到的整个区域。高分辨率会很卡，所以游戏改用两张图，分别覆盖近处和远处 partition。（也就是 Cascading Shadow Map 的思路。）

复杂之处在于，它必须与 Quake 的 PVS（Potential Visible Set）系统结合，而且还要多线程运行，`r_smp_workers` 会轮流处理它。

核对完全部逻辑后，结果发现这是一个数据问题。

长话短说，bug 是 `R_SetVisData()` 中的 typo，错误设置了 TLS data。

![R_SetVisData 修复](../images/cod4setvisdata.png)

（修好之后）

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/cod4workingCSM_TODAY.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

## 终极支线

我发现自己越来越频繁地使用 BLOPS PDB，修正 COD4 SP 反编译中做得草率或错误的地方。

我也注意到，除了 actor code 以外，许多领域都有很有品位的更新。

*最终，我决定干脆把整个《黑色行动》都反编译出来。*

主要原因是这样更容易理解和比较代码；如果以后 fork 一个超级 COD 混合引擎，它也会是一箱很好用的零件。

于是，《黑色行动》反编译开始了。*一个崭新、令人兴奋而又截然不同的故事就此开始。*

#### 《黑色行动》

就个人而言，我最喜欢 COD4。但别误解，这就像说《护戒使者》比《王者归来》更好。我当年真的参加了 BLOPS 的午夜首发，它也是我玩过的最后一部 COD。

有人可能以为，直接拿 COD4 代码“更新”到 BLOPS 标准就行。但在实践中，这是个糟透了的主意：struct 或函数中任何一点微小错误都可能造成重大 bug。

我们把《黑色行动》反编译当成一个全新的游戏，一切从零开始。

#### 其他反编译尝试

这里简单提一下，过去也有人尝试反编译 BLOPS，但据我所知，没有一个真正完成。

一个是 [OpenBO1](https://github.com/AmIKnowYou/OpenBO1)，它基于 hook 运行，把尚未实现的调用转发给旁边的官方 binary。项目看起来大约四年前停止了。

另一个是 [OpenT5（Rust）](https://github.com/paleauraaaa/OpenT5)：它不仅想反编译 BLOPS，还想同时用 Rust 重写。这一个没有走多远。

还有一个也叫“*OpenT5*”，现在已经不在 GitHub 上，但它是过去最好的尝试。乍一看似乎极不完整，仔细检查后却能发现作者非常用心。根据修过的代码位置和被禁用的系统，我猜他们做到了载入菜单，然后就收工了。我要称赞这群人，因为有几个地方，他们清理得比当时的我更好，我也借鉴了他们的实现，尤其 gfx 部分做得不错。

## 反编译开始

首先，我想改进第一次使用的流程。KCOD 在这个阶段太依赖人工，而使用 `.map` 文件其实没有必要。

我 fork 了 [RawPDB](https://github.com/MolecularMatters/raw_pdb)，做了一些简单修改，直接根据 PDB 中的路径创建 source tree。

![RawPDB 输出](../images/rawpdb.png)

它会创建一个空 `.cpp`，以及一个 `.txt`，列出据称属于这个 `.cpp` 的函数。

之后，我让 IDA 脚本解析每个 `.txt`，填充 `.cpp`，并为它创建相关 header。

```text
这里并不完全准确，因为 COD 不总是给每个 .cpp 配一个 .h。有时整个目录会共用 header_local.h 和 header_public.h。和许多其他问题一样，想改的话以后可以修。
```

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/idadecompingblops.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

我的 IDA 脚本还会在运行时用简单的文本查找替换，粗暴修掉几种已知坏模式。

生成阶段仍有很大的改进空间。

这一次，我决定分更多轮来做。对整个代码库，大致是：

- 第一轮只进入 headers，添加类型；
- 然后逐个 `.cpp` 修 IntelliSense 错误；
- 再用 `Ctrl-F7` 尝试编译每个 `.cpp`；
- 最后一轮集中修 link error。

当初的想法是，做过一些修正后，可以只对尚未触碰的文件局部重新生成。但老实说，整个过程感觉反而花了更久。

当然，这也可能只是因为 BLOPS 本身比 COD4 难反编译得多。

## BLOPS 独有的挑战

BLOPS 有很多 COD4 没有的东西。我会试着列出来……

#### 混合的 int/float load 与 store

BLOPS 的编译器有一种优化：float 有时会被当成 int，存进 32-bit register，看起来像这样：

![float DWORD load](../images/fltdword.png)

Float constant 通常也会被当作 DWORD。

![float constant](../images/fltconst.png)

出现取负或 `fabs()` 时，它会把 float 当作 int，并对它执行 XOR。

![混合 float/int 操作](../images/floatmix1.png)

很多模式当然可以自动搜索和删除，但当你手工重做函数，或搜索替换没抓到它时，仍然必须亲自处理。

#### 栈没有对齐

有些 class 明确要求 16-byte alignment，又被分配在 stack 上，于是一些函数的 frame 会坏掉。

![错位的 stack frame](../images/img_1.png)

Stack 通常会错 12 bytes。最快的修法，是进入 Stack View，在顶部删除 12 bytes。（如果底部的 arg space 不够，记得补上更多空间。）

Hex-Rays 和 disassembly 并不真正“同步”；Hex-Rays 只把 frame 当成提示，所以这样改是可行的。你只需要删掉函数开头因为 alignment 产生的一些 junk code。

#### 更多 C++ 多态

COD4 大部分是 C，只带一些 C++ 点缀；Treyarch 更喜欢写 C++，大量代码使用了很复杂的虚继承，任何微小错误都可能引发 bug。

真实例子见：[https://github.com/SwagSoftware/KisakBlack/commit/eac4762c4ebcb686e0a15fb8d596efea48fefba2](https://github.com/SwagSoftware/KisakBlack/commit/eac4762c4ebcb686e0a15fb8d596efea48fefba2)

即使非常仔细地沿着 vftable 核对，我仍然犯过几处错误，直到后来才修好。

#### 大得多的代码量

BLOPS 的技术比 COD4 多得多。它不仅晚发布三年，而且 MW2 在 2009 年完成后，他们也能随意吸收其中的技术。由于我是从 COD4 走向 BLOPS，并不确切知道每项技术在何时加入、由谁制作，但可以列出 BLOPS 的一些新增内容：

- DemonWare（也就是今天业内所谓的“Game Coordinator”）；
- 会移动的 foliage/object；
- 风；
- Glass System（来自 MW2）；
- Flame System；
- 新的 Treyarch 自研物理引擎（来自 Spider-Man）；
- 效果更多的新 XAudio engine；
- 载具；
- IK System；
- 脚本系统大改，现在按 instance 运行，client 60 Hz、server 20 Hz；
- 线程与图形系统大改，加入 TL job system；
- Treyarch 一个叫“monkey”的 backdoor，会向“zookeeper”报告；
- `nvapi`（KisakBlack 目前禁用；原本用于 Nvidia 厂商特有的 D3D9 INTZ extension）；
- DynEntity server support；
- 大量 `live` 集成（连接 DemonWare，可理解为 Online、好友列表、成长、匹配等）；
- DDL（Data Definition Language，用于序列化玩家 stats、match stats、profile data 等）。

还有许多系统也发生了大量变化。再强调一次：这是 COD4 之后三年的完整开发成果，而且是在整个游戏行业的巅峰时期，由当时最优秀的一批 AAA 开发者完成。

#### DemonWare

反编译 BLOPS 时，我还必须同时移除 DemonWare。最初我把 DemonWare 当作游戏的一部分一起反编译，但很快就受够了这种毫无意义的工作。

它不是一个好库。我的 Steam 版《黑色行动》根本不能运行；为了测试时启动离线地图，我不得不安装 Plutonium。

有趣的是，一位 DemonWare 开发者在 2011 年做过[一场演讲](https://www.erlang-factory.com/upload/presentations/395/ErlangandFirst-PersonShooters.pdf)，谈他在 BLOPS 等游戏上的工作。

![真实的 Black Ops 服务器](../images/blopsrealservers.png)

```text
这是真实的《黑色行动》服务器照片。（居然是桌面电脑！）
```

演讲里，他基本一直在感叹他们的 C++ 代码不停崩溃，以及改用 *Erlang*（一种冷门的 VM 语言）对他们来说有多么神奇。

这个库只是后来接到游戏上，为它提供类似 Halo 的在线功能。我并不真正把它视为游戏的一部分，尽管它当年确实完成了自己的任务。

由于相关类型已经深入嵌入《黑色行动》，WIP 的 `/DemonWare` 目录暂时保留，但基本不再使用。

#### Treyarch Library（TL）

Treyarch 决定让引擎真正变成“自己的”（*我尊重这一点*），加入了大量内部代码。最让人头痛的毫无疑问是 Physics system，Jobs system 也有些混乱。

## 调试开始

经历艰苦的反编译后，终于该开始调试和修 bug 了。

从技术上说，这次反编译以《黑色行动》的 server executable 为基础，所以第一项任务是把它重新变回 client。在那个时代的 COD 中，dedicated server 基本就是 MP binary，只不过设置了 `dedicated` dvar。Graphics code 等内容仍然都在，因为 server 需要加载与 client 相同的关卡文件；我猜专门把这些代码从 dedicated server 中切掉，反而会带来不必要的混乱。

某些代码存在 dedicated-specific branch，但 client code 并没有被 compiler 优化掉，只是在 ASM 中通过常量 `1` 强行跳过。

![dedicated 常量分支](../images/blopsdeditest.png)

在 byte-patch 成 `0` 之前，Hex-Rays 不会显示这些路径。其中一些可以做 signature 搜索，其他只能靠试错找到。

搜索 `b9 01 00 00 00 85 c9 75` 的结果有 74 个；后者可以改成另一种 jump。

![dedicated 分支位置](../images/isdedispots.png)

修好数据库后，游戏大概能加载到这里：

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/blackopsliteral.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

```text
确实很像 BLACK ops
```

又修了一些 bug 后，菜单可以工作，我也终于能开始处理真正的核心问题：让游戏加载进去。

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/menuworkingnetfubar.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

移除更多邪恶、撒旦式、亵渎神明的 DemonWare 检查（等待 master server 下发 stats）后，结果发现我的 `svCompressedBuf` 旁边有一个 [bug](https://github.com/SwagSoftware/KisakBlack/commit/7bf2921b001dfda3ba8f9ad3e6ac3402468bb53e)，它用于 `SV_SendMessageToClient()`。

现在到了 client/server 协商 ClientState 的部分。（也就是 SignonStates。我以前在 Dota 里卡住这些状态，做过各种缺德事。）

这一次我选 `mp_mountain` 当测试地图。它是我最喜欢的地图之一，而且 BLOPS 里不知为什么没有 `mp_bog`。

`mp_mountain` 有很多玻璃，甚至有些会在 server 启动时自动破碎。这迫使我立刻去修联网同步的 glass snapshot code。

这次反编译基于 BLOPS v1.0，因此还需要加入几个 script built-in，关卡脚本才能加载。它们是通过逆向 retail MP game 补回来的，其中大部分目前尚未测试，也还没有被调用。

之后轮到 Physics engine。这个系统是一次巨大的苦差事，光是重构到能加载进游戏，大概就花了两周。

下面是当时的视频：

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/physicswhace.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

```text
我们至今不知道“whace”是什么，有人知道吗？它的用法类似 AABB。
```

修复音频需要对 XAudio 的 `CXAPOBase` 继承做一点修改，[见这里](https://github.com/SwagSoftware/KisakBlack/commit/69402e3a7a7aa203ab4cc3968dde14675a4ceab3)。

继续修 bug 后，终于可以进入游戏，尽管一切都坏得惨不忍睹。

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/whiteops.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

```text
Call of Duty: White Ops
```

画面纯白，而且只有 5 FPS。

我把 Tracy 接进 PIX stubs（同时又补了一些 stub）。结果发现 Dx9 `Present` 耗时极长，该上图形调试工具了。

我已经受够 apitrace（*也就是 vogl！*）。它很慢，而且必须从头模拟每个调用。之前给 KSGO 接 UI 时，我在 Linux 上就开始使用它了。

针对 32-bit Dx9 的选择不多。我试了 Intel Graphics Monitor，但发现只要尝试 capture frame，它就会崩溃。（看起来是个普遍现象。）

于是我转向 PIX。此前有人遇到 KCOD 问题时，我曾试过一次，但当时它会报一些奇怪错误，而 apitrace 可以正常运行。

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/blopsPIX.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

```text
遇到错误时，PIX UI 用起来有点烦，但总体是个好工具，也是 Dx9 最好的工具。它甚至符合“克隆正确性”：当年的《黑色行动》开发者用的就是它。
```

一开始，PIX 因某个使用无效参数的 `CreateQuery()` 调用而报错，但很难得到更多信息。BLOPS 确实会在几个地方调用 `CreateQuery`，却都不是崩溃的位置。

最终，我把 `d3d9` 加载进 IDA，找到 `CreateQuery` 的名称；在 MSVC 调试时加载 `d3d9` symbols，并在真正的 `CreateQuery` callee 上设置 breakpoint。

结果问题来自 `nvapi` 库内部。引入它只是为了一个 Nvidia 厂商特有的小型 INTZ extension。（反编译时本来很容易跳过它，但为了忠实还原，我还是加了进来；而且 `nvapi` 库本身也不容易找到，感谢 Dogecore。）

![nvapi CreateQuery 调用](../images/img.png)

移除这个库，再做一些 [shader 修复](https://github.com/SwagSoftware/KisakBlack/commit/ba3e02b3167f8ff0140e8156053bf79e1bb0afcf) 后，Graphics 基本正常了。

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/loadinfirst.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

仍然有很多东西是坏的，最明显的是 physics 依然有问题，导致角色完全无法移动。

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/loadinfirstalt.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

```text
因为物理错误而被钉在原地
```

所以又该继续调试物理了。

这一次，我专门努力学习了 GJK 的各种细节。结果发现，[美国陆军竟然有一本讲解 GJK 来龙去脉的官方手册](https://apps.dtic.mil/sti/pdfs/ADA622925.pdf)。

下面分享一些基础知识。

Treyarch Physics engine 包含这些 Collision Geometry 类型：

![碰撞 geometry 类型](../images/colgeom.png)

每一种都是 convex shape。玩家碰撞体是一个有 12 个面（前 6、后 6）的 `GJK_POLYGON_CYLINDER`。这些 shape 都是实现 `phys_gjk_geom` interface 的 class。

GJK 用来判断两个 shape 是否发生碰撞。代码主要位于 `phys_gjk.cpp` 的 `phys_gjk_info::collide()`。

它有两个 variant：`phys_gjk_info::gjk_ray_cast()` 和 `phys_gjk_info::gjk()`。`ray_cast` 版本执行 continuous collision，简单说就是不仅判断两个 shape 是否碰撞，还要找出它们在一帧中的哪个时刻碰撞（0.0 到 1.0）。（如果我没记错的话。我试过禁用它，结果上楼梯变得很困难。）

调用其中一个函数后，`collide()` 底部还有一个 loop。这是 pushout code，用来计算两个 shape 相互嵌入了多深，以及应该怎样把它们分开。

我靠着一些非常基础的理解在这里折腾，算是部分修好了一点。

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/shotgunphysics2.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

现在勉强能移动，但碰撞糟透了。

我检查了物理系统的其他区域，确认它们是否正常，因为当时还不敢肯定问题依旧出在 GJK。

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/broadphase.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

```text
这个测试看起来可能很蠢，但它验证了 broad phase 是否把正确的 pair 交给 collision。结果确实是正确的。
```

#### AI 调试

我决定认输，让 AI 来看看这个问题，找出我到底做错了什么。

过去我多少有些反 AI，不过也会在浏览器里用它回答一些问题，或清理我懒得处理的简单函数片段。通常只要代码被 AI 改过，我会标成 `aislop`，因为我认为那不是完美工作。你可以随便批评 Hex-Rays 生成的垃圾，但至少它来自确定性算法。

然而，我身边似乎有一半朋友都成了 AI 专家，而我仍是 AI 文盲。

我订阅了 Claude Max、Claude Code，又把 [IDA MCP](https://github.com/mrexodia/ida-pro-mcp) 配给 Opus 4.7 1M（后来是 4.6）。

折腾大约一天半后，我让它找到了问题所在：果然只是 GJK 里几个小型数学错误。

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/collworking.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

```text
碰撞已经工作，但你能看到还有许多其他东西是坏的。
```

最开始，我要求 AI 一次只处理一个函数，并逐项对照 IDA（ASM）检查逻辑。然后扩大到一次一个文件，最终才变成直接给它任务，并告诉它应该从哪些文件或函数开始。

查 typo 和小错误时，它快得惊人，也很有效（非高峰时段尤其如此）。

面对更复杂的任务，它需要一些指导，但根据问题类型，也能慢慢推进。

有了 AI，我意识到自己可以省下大量调试时间，于是就这么做了。

指导 AI 的间隙，我还能并行处理其他工作。AI 钻进一组文件查 bug、准备回来报告时，我会在游戏里跳下悬崖或把自己炸飞，再去修其他区域的问题。

这部分没有留下太多视频，因为进展突然快了很多。不过这里有个很有意思的 bug，原因是我把一个 `fabs()` 写错了。

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/axelinrussia.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

```text
（这个踮脚动画本来只应该在非常陡的斜坡上播放。）
```

搭好 dedicated server 后，还出现了另一个有意思的 bug。

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/dedibug2.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

它的解法其实很简单。

![dedicated server 位置修复](../images/workingdedi.webp)

```text
现在正常了。用于 position offset 的地图中心点错了。
```

---

到这里，你基本已经追上当前进度。这只是对一路走到今天的简要总结。

## 结论

总之，我现在把仓库公开了。也许它对你有用，或至少能让你觉得有趣。项目并不完美；只要有人感兴趣，就总能继续改进。

文章底部还有一段附加内容，写给可能感兴趣的人。

（记得把老游戏的稀有源码和 symbols 发给我们。）

## （附加）一个完全由外行讲述的 Treyarch 引擎史

*（写作过程中没有接触任何现任或前 Treyarch 员工。我觉得自己有能力和他们成为朋友，但还没试过。）*

首先，我想澄清一些围绕“NGL”引擎的信息。

如果你搜索 Treyarch 游戏，很快就会看到“NGL”引擎的说法。

![NGL 引擎说法](../images/nglclaim.png)

[YouTube 视频](https://www.youtube.com/watch?v=QPFnZYsI2yc)

所谓“NGL”引擎其实已经通过 [Kelly Slater](https://github.com/historicalsource/kelly-slaters-pro-surfer/) 的源码公开在 GitHub 上。

![Kelly Slater 源码仓库](../images/kellyrepo.png)

现在进入 `NGL` 目录……

![Kelly Slater 的 NGL 目录](../images/kellynglfolder.png)

你会发现，它只是平台相关的 Graphics code。NVL（N... Video Library）和 NSL（N... Sound Library）也是如此。

浏览代码时，你会发现许多带 `ngl` 的函数和类型，但它们全都以某种方式与 graphics 有关。

看看这里：

![needed by NGL 注释](../images/neededbyngl.png)

如果 `NGL` 真是整个引擎的名字，就不会在注释中以这种方式被引用。想象一下，在 id Tech 或 Unreal 自己的代码库里，把这里的 NGL 换成 `idtech` 或 `unreal`，完全说不通。

所以，`NGL` 一定是个假名字……

继续搜索后，我终于找到了引擎真正的名称。

![Nyarlathotep 字符串](../images/Nyar.png)

如你所见，这套引擎叫 **Nyarlathotep**。它来自一个 [H. P. Lovecraft 典故](https://lovecraft.fandom.com/wiki/Nyarlathotep)。

虽然“Graphics Laboratory”多少暗示了 NGL 确实成立，而且开发者也用“N”缩写 NVL/NSL；但我拒绝接受那些上下文中的 N 就代表 NGL，所以我正式宣布它叫 Nyarlathotep engine。

说完这件事，再来看它基于 id Tech 3 的说法。

![NGL 与 id Tech 3 说法](../images/nglai.png)

只要扫一眼 Kelly 仓库，就能看出它显然不基于 id Tech 3，甚至都不是 C 写的。

**不过**，查看 COD3（PS3）的 `.map` 文件后，我能确认 COD3 **确实**基于 id Tech 3。

![COD3 MAP 文件](../images/cod3map.png)

进一步研究后，我提出下面这个假说：

- 2004 年，Treyarch 内部一个新分支拿到了 *Call of Duty: United Offensive* 源码。（COD:UO 由 Activision 旗下 Gray Matter Studios 制作。）
- 这个新分支，也就是 Treyarch（COD），专注 COD 开发，并在 2005 年发布 *Call of Duty 2: Big Red One*（比 IW 的 COD2 晚七天）。
- 同一时期，Treyarch（OG）在制作 Ultimate Spider-Man（2005）和 Spider-Man 3（2007）等其他游戏。
- IW 的 COD4 原本应该是 COD3，但 IW 做得太久，于是 Treyarch（COD）偷走“3”这个数字，在 2006 年发布了 COD3。
- COD4 于 2007 年发布并大获成功。Treyarch（COD）决定使用它的引擎，开始制作 World at War。
- Treyarch（OG）在 2007 年发布 Spider-Man 3，并开始使用自家技术与 COD4 的混合体制作 Quantum of Solace。
- WAW 和 QOS 都在 2008 年发布。
- 两支团队合并，开始制作《黑色行动》。

Treyarch（OG）= Nyarlathotep engine。

Treyarch（COD）= Treyarch COD engine，源自 COD:UO，后来又衍生自 IW3。

我认为这大体准确，但在不同时间点，两者之间肯定存在一些模糊地带，例如 COD3 之后。

在 BLOPS 反编译后期，有人发现 [Spider-Man 3 源码](https://archive.org/details/spiderman3-code)曾以 GCC 后处理状态上传到 PS3 devnet。文件名是 `broken.ii`，看起来像是有人调试时顺手上传了一大段代码。

![Spider-Man 3 预处理源码](../images/spiderman3_src.png)

所有内容都经过处理，烘成了一个文件，也没有注释，但它确实是这个游戏真实而不完整的源码，非常酷。

![Spider-Man 3 与 BLOPS 物理代码对比](../images/sm3vsblops.webp)

当 `phys_player_collision_mode = 1 (DEFAULT)` 时，BLOPS 使用同一套 Spider-Man physics code 处理全部碰撞（当然做过更新和修改）。

![Kelly Slater rigid body 代码](../images/KELLYRIGIDBODY.png)

Kelly 在这里差异已经很大，但仍能看到一些相同思路。
