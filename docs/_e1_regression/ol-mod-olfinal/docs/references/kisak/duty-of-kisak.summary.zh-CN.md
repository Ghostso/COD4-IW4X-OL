# 《Duty of Kisak》中文总结

原文：[LWSS, Duty of Kisak, 2025-06-25](https://lwss.github.io/Duty-Of-Kisak/)<br>
相关项目：[SwagSoftware/KisakCOD](https://github.com/SwagSoftware/KisakCOD)

## 文章讲了什么

LWSS 用这篇文章回顾了 KisakCOD 从 2025 年 3 月启动到首次公开发布的过程。项目目标不是做一个挂在原版二进制旁边的兼容层，而是把《使命召唤 4》的 Win32 多人游戏重新整理成可以独立编译、调试和长期维护的源码工程。作者也花了相当篇幅解释自己为什么认为旧游戏值得被开放、保存和继续改造。

![KisakCOD 的函数与局部变量信息来源](images/cod4randomida.png)

## 最关键的方法

KisakCOD 的起点不是“找到一份相近源码然后改成 COD4”。团队从空工程开始，组合了多种互补证据：

- COD4 v1.0/v1.1 Win32 PDB；
- 多份 Xbox 360 PDB 和 MAP，其中 MAP 能把函数归回对应的 `.obj`/`.cpp`；
- Macintosh ELF symbols；
- COD2、Jedi Academy 等祖先或近缘源码；
- BO1/BO2 PDB，用于交叉核对被内联或类型更清楚的函数；
- COD4 原版运行行为和后续调试结果。

这套做法的重要之处，在于每种资料只解决自己擅长的问题。PDB 给出符号、类型和局部变量，assert 暴露源文件路径，MAP 恢复编译单元归属，近缘源码提供结构，而最终正确性仍要靠编译和运行验证。

## 三个阶段

**阶段 0：建立流程（第 1 至 7 天）**

团队先用 assert 中的相对路径搭出空目录，再从 Xbox MAP 恢复函数到源文件的归属。手工试做一段后，作者在第 7 天写了 IDAPython 脚本，开始批量导出指定函数的伪代码和头文件声明。

**阶段 1：填满函数（约第 7 至 32 天）**

工作流仍然是半自动的：选择 `.cpp`，从 MAP 找函数，清理不属于该文件的条目，demangle 后生成 `targetfuncs.txt`，再由脚本输出 `decompout.txt` 和 `decompheaderglob.txt`。作者没有继续追求全自动，是因为边缘情况很多，而且 IDA 类型修改后的反编译刷新本身不稳定。工具负责批量劳动，人负责边界判断。

**阶段 2 与 3：修类型、编译、调试（约第 32 天以后）**

文件填充完成后，团队按顺序消除 IntelliSense 和单文件编译错误，最后进入持续时间最长的运行调试。此时真正困难的并不是“还有多少函数没导出”，而是错误类型、丢失 cast、ABI 细节、第三方库改造和海量小型转写错误会以完全不同的画面、物理或脚本故障表现出来。

## 几个典型案例

- COD4 深度改造过 ODE。团队不能直接替换一个相近版本，而要把 solver、对象池、trimesh、vtable 和额外 `Phys_` 碰撞代码逐项对回反编译结果。
- Bink 和 Miles 是闭源依赖。找到“差不多”的 SDK 不够，头文件和 `.lib` 的微小版本差异也会造成链接问题，最终使用 Miles 7.2e 并补了 COD4 自定义 EQ filter。
- fastfile 加载依赖磁盘中的 `-1/-2` 指针标记和加载时 fixup，错误解引用会导致黑屏或数据库错误。
- 同一个 IDA 数据库和版本仍可能给不同人生成不同伪代码。`VariableValue` 的联合体与 `type` 被错误合并写入，是伪代码不能取代汇编核验的直接例子。
- 枪械飘离 viewmodel 来自丢失的 cast；瞄具错误来自移植 BO1 PDB 代码时引入的问题；`bool` 返回值被声明成 `int` 则暴露了 x86 EAX 低 8 位和全寄存器读取的 ABI 差异。
- 黑色光照最终通过清理提交改变行为、局部回退来定位；另一个 RGB viewmodel 现象经原版复测后被证明是 `r_showMissingLightGrid` 的正常行为，而不是反编译 bug。

## 对 ol-mod 最有价值的启发

1. **参考资料应形成证据组合，而不是单一答案。** KisakCOD 也同时使用 COD4 PC、Xbox、Mac、BO1、BO2 和祖先源码，但不会把任一近缘实现当成最终真相。这与 ol-mod 以 CODOL xref、wire bytes 和运行证据裁决参考实现的原则一致。
2. **先恢复编译单元与责任边界，再批量搬函数。** MAP 的价值不只在函数名，而在恢复代码原本属于哪个模块。对 CODOL 来说，继续分清 backend control plane、player persistence 和 authoritative game server 比堆积反编译片段更重要。
3. **自动化最适合消灭重复劳动，不适合替代高不确定判断。** 作者把函数导出工具化，却保留人工清理和类型核验。ol-mod 的 Frida watcher、自然匹配编排和后续 IDA/trace 工具也应沿用这个边界。
4. **能显示画面不代表系统已经正确。** 菜单能开、地图能载入、模型能出现之后，仍可能有脚本、物理、光照和 ABI 深层错误。对 ol-mod 而言，客户端离开加载页也不能自动等价于 server world、snapshots 和生命周期已经恢复。
5. **对照原版可以证伪“看起来像 bug”的判断。** RGB lightgrid 的案例尤其重要：异常外观必须与零售版、配置和触发条件复测，不能只凭直觉修掉。

## 作者最后的判断

首次发布时，KisakCOD 已基本可玩，但仍有 stencil shadow、profile 切换、下载功能和大量反编译代码清理工作。作者把“公开发布”视为可继续改进的基线，而不是宣称一切已经完成；后续实验应在稳定分支之外展开。这种诚实标注完成边界的做法，比单纯追求一次成功画面更值得借鉴。
