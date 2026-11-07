# Duty of Kisak：Kisak 的使命

> 原文：[Duty of Kisak](https://lwss.github.io/Duty-Of-Kisak/)，LWSS，2025-06-25。<br>
> 本文是非官方中文直译。代码、链接、图片和视频顺序按原文保留；作者的口语、玩笑和观点不代表本项目立场。

我们反编译了 COD4。

## 背景

这篇博文是对 *SwagSoftware* 最新发布项目 [KisakCOD](https://github.com/SwagSoftware/KisakCOD) 的一次背景故事大放送。

## SwagSoftware 的动机，以及什么是“Kisak”？

KisakCOD 是 *SwagSoftware* 的第三个游戏项目。

第一个项目是 [Kisak-Strike](https://github.com/SwagSoftware/Kisak-Strike)，第二个则是后来意外走红的 [kisak-thug](https://github.com/SwagSoftware/kisak-thug)。

做 *Kisak-Strike* 的目标，只是想要一个好用、可修改的 CSGO，让爱好者可以进去研究并玩得开心。它是一个 100% 开源的项目，可以移植到任何平台，也能永远保存在互联网上。这个项目很酷，我认为它确实达成了这些目标。甚至有人把它移植到了冷门的 [e2k](https://en.wikipedia.org/wiki/Elbrus_2000) 架构上（那是你我根本不可能买到的东西）。

Kisak-thug 的目标则是拿到 [THUG 源码](https://github.com/thug1src/thug)，把它移植到 Win32。（它原本只支持 Xbox、PS2 和 GC。）

Kisak-Strike 和 kisak-thug 都使用了各自游戏泄漏的部分源码，并做了额外修改，让它们在现代环境里更容易运行，同时尽量尊重原作。直接把受版权保护的源码放到 GitHub 上，在道德上正确吗？Valve 对 modder 相当友好，看起来他们默许了这件事。THUG 在我 fork 之前也已经放在 GitHub 上超过十年了。*（KisakCOD 与这一段无关。）*

***Kisak*** 是我们关于开源的神话图腾。这个神秘存在宣称所有软件都应该是 GPL。他要求最虔诚的追随者运行 Gentoo，并强制亲自编译所有程序。我们务实地朝 Windows 来了一次朝圣，但并没有完全背弃他的教诲。

```text
“新硬件会出现，范式会改变，但软件永存。” -- Kisak（2045）
```

## COD4 与其他 COD 不一样

KisakCOD 是我做过的第一个游戏反编译项目。我大概十年前就想做它了。（这是我最喜欢的游戏之一，我在 Xbox 上玩了无数个小时。）

COD4 诞生在一个游戏会附带 mod 工具和 dedicated server build 的年代。

Mod 是游戏明确内建的功能。[COD4 的 GSC 脚本以带注释的原始形式发布](https://github.com/volkv/CoD4-Default-GSC-Scripts)，游戏里还有开发者专用 profile。

![COD4 mod 界面](../images/cod4modsui.png)

![COD4 开发者 profile](../images/cod4devprofiles.webp)

```text
Star Wars Galactic Warfare：一个曾经很流行、把 COD4 变成星球大战的 mod
```

![Star Wars Galactic Warfare](../images/codstarwars.jpg)

直到今天，仍然有人在制作非常出色的 COD4 mod。

```text
COD4 Rooftops：爱好者制作的一部现代 COD4 战役
```

[https://www.youtube.com/watch?v=row5eYSdvMA&t=780s](https://www.youtube.com/watch?v=row5eYSdvMA&t=780s)

![COD4 Rooftops](../images/cod4rooftops.jpg)

不过我最喜欢的还得是 COD4 ProMod。十多年前，我甚至还随便开过一个没多少人的 ProMod 服务器。

ProMod 基本就是对原版 COD4 的玩法做了一些调整。它很快、很硬核，对新人来说可能极难上手（我自己也不算厉害）。

它大概是多人 FPS 能带给你的最大乐趣。

真正的亮点是 IW3 引擎的流畅度：它可以稳定锁在 125、250 或 333 FPS。

不同的 FPS 上限会对世界物理产生不同影响。333 大概是最不平衡的，因为你能跳得非常高；250 更常用一些。

COD4 地图配上 ProMod 的高速玩法之后格外出彩。由于地图建模方式的缘故，里面有大量独特的跳跃、弹跳和可抵达点位。

既然 COD4 ProMod 已经这么好玩，想象一下开源 COD4 能有多少可能性。

```text
暴论：IW3 比 Source Engine 更好（至少比 CSGO 的好）。我觉得 CSGO 开发者自己都会同意。
```

## 游戏开发的黄金时代（你错过了！！）

![Metroid 游戏画面演进](../images/metroids.png)
![Doom 游戏画面演进](../images/dooms.png)

在十年甚至更短的时间里，电子游戏从 16-bit sprite 发展到了带实时光照、骨骼动画和顶点动画的完整 3D 场景。

在这个“黄金时代”的中段，Quake 1 于 1996 年发布，源码则在 1999 年公开。如果你不想使用 GPL，也可以花大约 125,000 美元从 id Software 购买授权。

几乎任何人都能学习这些新的 3D 技术，并成为行业开拓者。Mod 和地图制作非常流行；只要你做得好，就很容易在 id Software、Raven 或类似公司找到工作。

如果你当时就在这个圈子里，就相当于从一楼起步，随后一切以自然的速度逐渐变复杂。如果你从那时开始关注游戏开发，就能像追 Dota 2 patch notes 一样，亲眼见证各种技术的自然演进。

而且不管一些人怎么想，当年的游戏开发者都猛得很。

程序员极其敏锐，凭直觉就知道什么时候该用高级数据结构（例如各种自平衡二叉搜索树）。位运算、ASCII、x86 opcode 和 cache line 对他们来说都很自然。他们没有 Google 或 Stack Overflow；需要帮助时，只能去联系真正的专家。

美术人员来自一个真的要用纸笔绘画的背景。他们得花钱购买这些消耗品来训练技能，而且教他们的是技艺更高的古典艺术家。

作家写的是要在纸面上提供“AAA”体验的书。早期电子游戏的情节发人深省，也很有意思。（《幽灵行动 1》几乎预言了如今的乌克兰冲突。）

***如今……事情不一样了……***

大多数传奇游戏工作室都让自己的老师退休了，却没有把知识传下去。许多工作室只剩下名字还活着。（我不点名，也不是在暗示 IW；从 MobyGames 的制作人员记录来看，COD4 团队的传承仍然相当扎实。）

自研引擎极其罕见，而且需要巨额资金。

模型、纹理、动画等工作被外包给第三世界的承包商（看看 Starfield 的 credits）。AI 此刻也正在被整合进来，进一步削弱手艺本身。

FPS 优化成了事后才考虑的东西。

程序员被不懂技术的商科管理者“管理”，关进一个盒子里。他们从 sprint 里领任务，而不是自我驱动，直接去做明显合理的事情。

（我还能继续列，但你应该已经明白了。）

***现在的大多数游戏开发都很糟，但它并非一直如此。***

幸运的是，我们仍然可以以尊重原作的方式重访 COD4 这样的老游戏，并在今天继续享受它们。通过深入游戏引擎，我们也能在某种程度上[模仿那个黄金时代，亲自活一遍](https://www.youtube.com/watch?v=j1D7k_qqJts)。

# KisakCOD：制作过程

好了，下面来谈谈这次反编译究竟是怎样完成的。

#### 前期规划：资料多得惊人

公开网络上可以找到几十份 COD 游戏的调试信息（`.PDB`）。

![COD 调试版本列表](../images/codbuilds.png)

仅《使命召唤 4》至少就有：

- 2 份 Win32 PDB（v1.0 和 v1.1）；
- 6 份 Xbox 360 PDB/MAP（其中一份对应零售版 v1.0）；
- 带 ELF symbols 的 Macintosh 版本。

后来，我们也开始用《黑色行动 1》和《黑色行动 2》的 Win32 PDB 做交叉核对。

别忘了，COD4 基于 COD2，COD2 基于 COD，而 COD 又基于 id Tech 3。因此，我用 [Jedi Academy](https://github.com/grayj/Jedi-Academy) 作为许多基础框架的参考。（这款游戏在 2000 年代早期由 Raven/Activision 真正以 GPL 发布。）

这个项目的想法在我脑中放了很久，直到有人给了我一份 v1.0 PC PDB，我才决定正式动手。此前 Xbox 版本因为 PowerPC 架构而工作量过大，v1.1 PDB 又太难找到。

这个 build 不仅带 asserts，连局部变量名也有，所以根本不需要犹豫。

![带局部变量名的 COD4 IDA 视图](../images/cod4randomida.png)

```text
Blops1 和 Blops2 的 build 也有这些东西。我很惊讶居然还没人完整反编译那两款游戏。
```

这时我找了两位很优秀的程序员伙伴加入。我们大约在 2025 年 3 月 4 日开工：

- Avail
- *“Destructive Interface”*

#### 阶段 0：摸索流程（第 1 至 7 天）

我还没蠢到直接拿 Jedi Academy 源码来改，所以我们从零开始。（每天的 commit 可以让你逐步看到这个过程。）

第一件事，是根据 assert 暴露的相对路径，尽量把文件结构搭出来。

![assert 中的 COD4 源文件路径](../images/cod4assertpaths.png)

当时这些都只是空文件，而且清单并不完整。许多 `.cpp` 没有 assert，`.h` 通常更是完全没有。

做了几天研发后，我意识到 Xbox 版本（我使用零售版 v1.0）有一份 `.map` 文件，里面写明了每个函数属于哪个 `.cpp`。

Xbox 版本与 PC 版本相当接近，因此大多数地方都非常有用。`gfx_d3d/` 的对应关系稍差一些，但也没糟到哪里去。

```text
这就是 .map 文件的样子。每个 .obj 都对应一个同名 .cpp 文件。
```

![COD4 MAP 文件](../images/cod4mapfileex.png)

我先手工反编译了一些内容，了解实际工作是什么感觉；到了第 7 天，我写了一个 IDAPython 脚本，用来批量反编译函数。

![COD4 IDAPython 脚本](../images/cod4idapyth.png)

### 阶段 1：填入函数（约第 7 至 32 天）

流程大致如下：

1. 选一个想要填充的 `.cpp` 文件（也可以通过 `.map` 找到缺失文件）。
2. 在 Notepad++ 中对 `file.obj` 执行“查找全部”。

![从 MAP 筛选编译单元函数](../images/cod4maprpuning.png)

手工移除所有看起来奇怪或不属于这里的函数（D3D、Swizzle 等），再把剩余文本复制到一个新的空文件中。

3. 对文本执行 demangle，并用正则表达式（`!\b[a-zA-Z_][a-zA-Z0-9_]*\s*\(`）只提取函数名，把结果放进 `targetfuncs.txt`。

![targetfuncs.txt](../images/targetfuncs.png)

4. 运行 IDAPython 脚本（它会自动寻找 `targetfuncs.txt`），脚本会导出 `decompout.txt` 和 `decompheaderglob.txt` 两个文件。
5. 把 `decompout.txt` 的内容粘贴进 `.cpp`，把 `decompheaderglob.txt` 放进对应的 `.h` 或共享 `.h`（视情况而定）。
6. 现在你已经找到了这个 `.cpp` 的全部函数，不过它们仍然需要手工修复、补类型和全局变量。之后也可能发现遗漏的函数，需要再补。玩得开心！

如果你想问为什么没有进一步自动化，原因基本是可能遇到的特殊情况太多。这个脚本已经让事情容易了很多，也自动完成了相当多的工作。这里最大的头痛点，大概是无法让 IDA 的反编译数据库自动更新。如果你修改了全局变量的类型，就得在函数里按两次 F5 才能更新。我们没找到自动完成它的方法，`Ctrl-F5` 也不行。

### 阶段 2：修复已经填入的函数（约第 32 至 55 天）

所有文件填满之后，就可以很方便地按 A 到 Z 的顺序消除 IntelliSense 错误。

工程只是一个简单的 `.sln`，文件直接拖进去。这样很方便，也足够好用。

完成一个文件后，可以右键点击 [`.cpp`](https://youtu.be/qWTAC0zO_-U) 文件，再点“Compile”测试编译。

![Visual Studio 单文件编译](../images/cod4compileindivid.png)

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/compilin.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

我们遇到了许多 IDA 问题：不小心按下 `\` 导致 cast 显示被关闭；即使按 `Ctrl-F5`，反编译也不更新；明明有 PDB，函数 prototype 仍然错误，等等。

这需要大量人工修正。

也是在这个阶段，我们开始发现哪些地方必须做定制处理。

#### ODE 物理

COD4 使用 [Open Dynamics Engine](https://github.com/thomasmarsh/ODE) 处理物理。

我放入了大约 2004 年的 0.5.0 tag，匹配程度相当不错。

不过，这个库里存在大量修改。原始开发者完全不怕直接钻进第三方库，按自己的需求优化代码。

“*Destructive Interface*”负责了这一块，把代码与反编译结果对得相当接近。后续调试时，这里还需要更多工作……

#### Bink 和 Miles

COD4 使用 Bink（过场动画）和 Miles Sound System（整个音频栈）。

它们都是 RAD Game Tools 制作的专有库。

我给 RAD 发了邮件，询问能否得到这些版本的库：

![给 RAD Game Tools 的邮件](../images/rademail.png)

但他们似乎太忙，没能回复，所以这条路没有结果。

Bink SDK 很容易找到，Miles 则少见得多。版本必须大致正确，否则所有代码都得重写，最终结果很可能也不再相同。

搜索数小时后，最接近的结果在这里：[https://github.com/rocketprogrammer/disney-miles](https://github.com/rocketprogrammer/disney-miles)

它基本完美匹配，但后来出现了链接错误。我怀疑 `.lib` 和 `.h` 之间有少量差异。

继续搜索后，我找到了 2008 年 10 月发布的 Miles 7.2e 完整安装包。音频代码需要做少量改写，但总体没问题。

至于 EQ filter，[Dogecore](https://github.com/HappyDOGE) 必须 patch `milesEq.flt` 才能让它工作。这看起来是 COD4 的自定义版本，每次 filter pass 有三个 band value。

### 阶段 3：调试与清理（第 55 天至今）

这一阶段花的时间最长，而且仍在继续。

从这里开始，每日 commit 停了下来，工作变成了不定期修复各种问题。

##### 黑屏、数据库错误，以及禁用 Bink

最开始启动时只会黑屏，原因是一些 Pixel Shader 变量没有默认值（哎呀）。

因为这是 MP binary，我们禁用了 Bink。过场动画原本只显示纯绿色，不过声音是正常的。

数据库简直是一场噩梦，也就是所谓的“fastfiles”。据我理解，它们叫“fastfiles”，是因为文件会被整个吞进内存，然后把磁盘上设为 `-1` 或 `-2` 的指针在加载时修正。这也使它们依赖特定架构。

这里有好几处没有正确解引用……

![可疑的 fastfile 指针处理](../images/sketchy.png)

修完之后，游戏能进入主菜单了，但*很多*东西仍然是坏的。

<video width="750" height="600" controls muted>
  <source src="https://lwss.github.io/videos/cod4kootise.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

修复后，菜单终于可以工作。

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/cod4menufirstload.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

![损坏的 COD4 logo](../images/cod4logobusted.png)

我们开始启用 ASAN 构建游戏。在 Visual Studio 里它直接就能用，非常有帮助。

##### 招募人手

大部分摧残心灵的苦工完成后，我觉得可以招些朋友来一起调试游戏了。

我和 [R1Delta](https://github.com/r1delta/r1delta) 团队里不少人是朋友。他们刚完成 Titanfall 1 Server Mod，时机正好。

来自 R1D 的成员：

- [Dogecore](https://github.com/HappyDOGE)
- [Mr Steyk](https://github.com/mrsteyk)（一位老牌 Apex hacker）
- Wanderer（R1D 创始人兼 CSGO 传奇）
- [bt](https://github.com/eepycats)（Steam Client 专家，可能比 Valve 还懂 Steam）

我们还决定通过共同朋友找一些 COD 专家，回答关于游戏的问题。我们当时都算不上 COD 专家，所以他们的意见非常有价值。

来自 COD 社区的成员：

- [xoxor4d](https://github.com/xoxor4d)（COD4 专家，也为几乎所有其他游戏制作过 RTX 版本）
- [xensik](https://github.com/xensik)（COD 专家，制作过高级 GSC 工具等项目）
- [voron00](https://github.com/voron00)（COD2 专家，已经反编译过一个 COD2 自定义 dedicated server）
- [nta](https://github.com/nta)（老牌 COD modder，也是我的前老板 =P）

（还有其他一些人……Koutsie？）

##### GSC 脚本

脚本系统的反编译完全坏了。这里说的是游戏脚本，不是 UI 脚本。（COD4 有两套。）

Avail 找到了 [voron00](https://github.com/voron00) 的[这个 COD2 server 项目](https://github.com/voron00/CoD2rev_Server)。经过深入核对，它与 COD4 有 90% 相似。

我们邀请他加入项目，并用他的一些代码替换了我们的版本。

替换后仍然有些问题，不过 Dogecore、Mr Steyk 和我最终让它工作了（主要是 Dogecore）。

这里还发生了一次 IDA 背叛事件……

我的 IDA：

![我的 IDA 反编译结果](../images/idawrong1.webp)

DOGECORE 的 IDA：

![Dogecore 的 IDA 反编译结果](../images/idawrong2.webp)

（注意 `0x200000000LL`。）我们使用的是同一份 IDA database 和同一个版本……

这原本应该是一种厉害的优化，同时执行 `value.type = 2` 和 `value.u.intValue = name`，但它并不能工作，因为 `VariableValue` 实际长这样：

```cpp
struct VariableValue
{
    VariableUnion u; // 4-byte union type
    int type;
}
```

那不是唯一的问题，但很有意思……

##### ^6==BOGDANOFF GAMING== 24/7 mp_bog, bots, !skins

不知道为什么，我们选择 `mp_bog` 作为固定测试地图。说实话，这地图真的很烂，抱歉。不过它确实承载了许多[怀旧回忆](https://www.youtube.com/watch?v=a-4KTZlPqok)。

下面是 5 月 30 日第一次载入 bog。当时一选队伍就会崩溃；镜头移动一会儿后，static model cache 也会崩溃。

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/firstloadbog.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

你可能还注意到，一些 xmodel 是黑色的。这个光照错误大概花了一周才找到。

Xoxor 通过禁用 skinning 和 static model cache，成功走得更远了一些。

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/xoxorFirstLoad.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

##### 幽灵枪（很酷）

修复了几个 bug、终于能加入队伍后，还留下一个不会崩溃的问题：枪悬浮在 viewmodel 外面……

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/ghostguns2.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/ghostgun.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

讽刺的是，开启 `r_fullbright` 后模型反而出现了。（先忽略瞄具，那是另一个后来修掉的 bug。）

![fullbright 下的 MP5](../images/mp5fullbright.webp)

Mr Steyk [修好了它](https://github.com/SwagSoftware/KisakCOD/commit/ce5437b165f2356845de63c24e5967662820ccd2)：问题是 IDA 丢失了 cast。

![模型矩阵 cast 修复](../images/modelmatrix.png)

瞄具 bug 基本是我在回移一些 Blops1 PDB 代码时[亲手引入的](https://github.com/SwagSoftware/KisakCOD/commit/dd72fb16099ed170fc41d3dd8b76455e0384dbd2)。

Blops1 PDB 中被内联的函数更少，还有一些很不错的 matrix 函数，能和 Xbox COD4 PDB 对上。

##### “Destructive Interface”修复物理

物理系统刚开始的表现大致是：“游戏卡死，然后 Visual Studio 强行跳到最前面。”

后来，我们通过细致匹配函数修复了它，不过物体会向下掉进其他东西里。

修复的一部分涉及 ODE LCP solver 中一个很细微的变化：

![ODE physics 变化](../images/physicschange.webp)

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/physicsgrug.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

solver 必须重做；许多内存分配改成 object pool；ODE trimesh 被大幅删改；大多数 vtable 被移除；又接上了大量额外碰撞代码（`Phys_`）。

“Destructive Interface”[也修好了 ragdoll](https://github.com/SwagSoftware/KisakCOD/commit/f5b373b1cfa9ca7bd425d24d9b87eb915f311010)。

![失控的 ragdoll](../images/ragdollsfubar.webp)

除了 matrix 的一些问题，我还多写了一个分号（哎呀）。

![多余分号](../images/semicolongrief.png)

“Destructive Interface”还修了一个很棘手的 bug：一个返回 `bool` 的函数被 cast 成了返回 `int` 的函数。

![bool/int 函数签名错误](../images/image.webp)

`bool` 只使用 EAX 的低 8 位，`int` 则使用整个寄存器。函数返回 false 时只把 EAX 低 8 位清零，caller 却读取了整个 EAX。

##### 黑色光照

为了找出黑色光照 bug 到底在哪里，我们折腾了很久。最终，我的一次清理 commit 改变了问题表现，于是通过在本地做局部 revert 找到了相关区域。

结果问题在 lightgrid 系统里。这里有几千行代码要翻，不过我会把函数单独放出来，让你这个读者看看能不能找到 bug。

![lightgrid 函数上半部分](../images/lightgrid2.webp)
![lightgrid 函数下半部分](../images/lightgrid1.webp)

##### LightGrid 真的修好了吗？？

“修好” lightgrid 后，我遇到了一些 viewmodel 变成 RGB 色块的区域。

<video width="900" height="600" controls muted>
  <source src="https://lwss.github.io/videos/lightgridRBG.mp4" type="video/mp4">
  你的浏览器不支持 video 标签。
</video>

我试着在这一带随缘搜索更多 bug，但一无所获。

研究后发现，这居然是***原版 COD4 的预期行为***。有一个 dvar 就叫 `r_showMissingLightGrid`。

更多信息：[https://wiki.zeroy.com/index.php?title=Call_of_Duty_4:_Gridfile](https://wiki.zeroy.com/index.php?title=Call_of_Duty_4:_Gridfile)

我简直不敢相信，于是启动零售版 COD4 并设置了这个命令。

![零售版 COD4 的 missing lightgrid](../images/retailCOD4.webp)

果然，这完全正常，而且原版在一模一样的位置也会变成 RGB。

之后光照又显得太蓝，不过很快就发现只是解析 BSP 中 float convar 时出了问题。

##### 首次公开发布前的最后清理

公开发布前，我们做了几件事来处理剩余的大问题：

- 拆出一个“DEDICATED”server build。（实际上只是 `com_dedicated 2`。我们本来想做 Linux dedicated server，但把项目一分为二变得很难看，所以回退了。以后还会再做。）
- 添加 Steam API Auth，取代 CD Key Auth。（这给服务器管理员提供了封禁手段，也能抑制盗版。）
- 其他清理工作（以及写这篇博客）。

##### 还没有完成

仍有大量 IDA 反编译代码需要清理，才能让代码库看起来更好、运行得也更好。

[清理一个函数的例子](https://github.com/SwagSoftware/KisakCOD/commit/cc6db5f7897c7f2b5d2f3a2f968ab4b4ee72df7a)

Assert 应该放进 `iassert` macro，而不是硬编码；没用的变量应该删除；`v123` 风格的变量应该消失；逻辑可以简化；`// [esp+440h] [ebp-25ECh] BYREF` 这种 stack comment 也应该删除。

很可能还有不少 bug 在等着被发现和修复。

这些可以用比较放松的节奏慢慢处理。等准备好之后，我们可以开分支，尝试更多实验性的东西。

## KisakCOD：首次发布时的状态

KisakCOD 目前看起来基本能按预期工作，只有几个不影响游戏的已知问题：

- 出生时显示的队伍图标偶尔会变成白色方块；
- stencil shadow 不工作；
- `sv_wwwDownloads` 仍是 stub，因为 libWWW 太老，而且找不到相关 boilerplate code（应该换成 CURL）；
- 切换 profile 时，控制设置有时会损坏。

除此以外……我暂时想不到别的了……

当然，仍然有不少不理想的行为，也有大量可以扩展的空间。

## 如果 COD4 真能官方 GPL 发布就好了……

![希望 Microsoft GPL 发布 COD4](../images/microsoftglazing.jpg)

如果 Microsoft（也是 GitHub 的所有者）能正式批准 COD4 的官方 GPL 发布，那就太好了。

这会是一次很不错的公关行动。你也知道，Doom 3 并不会和 Doom 2016 之后的作品形成竞争。

只是提供一点思路……

## SwagSoftware 继续前进

*SwagSoftware* 一直在寻找下一个项目。

你有什么有趣的东西吗？

我们目前正在寻找以下复古游戏的 symbols 或源码：

- Ghost Recon 1
- Far Cry Instincts
- Syphon Filter
- COD4 mod tools
- James Bond id Tech games
- Need for Speed: Most Wanted（已知 PC PDB 存在）
- Need for Speed: Carbon
- 第五至第七世代游戏主机上的任何东西
