# 《Kisak Black》中文总结

原文：[LWSS, Kisak Black, 2026-05-10](https://lwss.github.io/Kisak-Black/)<br>
相关项目：[SwagSoftware/KisakBlack](https://github.com/SwagSoftware/KisakBlack)

## 从 COD4 支线走向完整 BO1 反编译

文章先交代 KisakCOD 发布后的几条支线：作者根据 Xbox 360 PDB/MAP 补 COD4 单人模式和 actor AI，修复内置 GSC 调试器，尝试 `useFastFile = 0` 的原始资产加载，又追查了多人模式的 CSM 阴影。阴影问题最后不是图形算法错误，而是 `R_SetVisData()` 中一个 TLS 数据赋值 typo。

作者在这些工作中越来越频繁地用 BO1 PDB 校正 COD4，发现 BO1 不只是“更多可参考的函数”，而是一个包含大量 Treyarch 技术演进的完整系统。于是原本的参考支线变成了新项目：KisakBlack 从空工程开始完整反编译《使命召唤：黑色行动》。

![RawPDB 生成源码树](images/rawpdb.png)

## 第二次流程改进

KisakCOD 早期依赖 MAP、Notepad++ 和手工整理，机械成本很高。KisakBlack 改造 RawPDB，直接从 PDB 路径生成源码树、空 `.cpp` 和每个编译单元的函数清单，再让 IDA 脚本批量填入函数和关联头文件。整个代码库按多轮 pass 推进：

1. 先在 headers 中补类型；
2. 再逐个 `.cpp` 修 IntelliSense；
3. 用 `Ctrl-F7` 做单文件编译；
4. 最后集中处理链接错误。

这比第一次更自动化，但作者也承认总耗时未必更短。BO1 本身更大、更偏 C++，生成阶段仍有改进空间。这是一个很实际的结论：自动化需要用端到端周期衡量，而不是只看某一步少按了多少次键。

## BO1 特有的难点

- 编译器会把 float 当作 32-bit integer 装载和存储，并用 XOR 实现负号或 `fabs()`，Hex-Rays 输出需要批量清理，也需要人工识别漏网模式。
- 16-byte aligned class 放在栈上会让函数 frame 错 12 字节，需要在 Stack View 修正 frame，并删除对齐产生的开头 junk code。
- Treyarch 代码比 COD4 更偏 C++，复杂虚继承和 vftable 中的轻微错误会在很晚才暴露。
- BO1 相比 COD4 多了 DemonWare、玻璃、火焰、车辆、IK、Treyarch physics、XAudio、job system、实例化脚本、DDL 和大规模 `live` 集成，代码量和模块耦合显著增加。

作者逐渐把 DemonWare 从游戏主体中剥离，因为目标是恢复游戏本身，而不是复刻已经失效的线上服务；不过由于类型已深入代码，WIP 目录仍保留为兼容边界。这种“逻辑责任先分开，物理代码稍后清理”的处理对 ol-mod 很有参考价值。

## 从 dedicated server 恢复 client

KisakBlack 以 BO1 server executable 为基础。那个时代的 dedicated server 基本仍是 MP binary，只是 `dedicated` dvar 和一些被常量分支屏蔽的 client 路径不同，因此 graphics 和关卡加载代码仍在。作者通过 patch 常量分支、修数据库和移除等待 master server stats 的 DemonWare 检查，让菜单和 ClientState/signon 继续前进。

测试地图选了 `mp_mountain`。它开局就有玻璃破碎，迫使团队较早修复 networked glass snapshot。基于 v1.0 的反编译还缺后续地图脚本需要的 built-ins，因此又从 retail MP 逆向补入，但明确标注其中许多尚未被调用和验证。

## 图形与物理调试

首次进图是纯白画面且只有 5 FPS。Tracy 指向 Dx9 `Present`，作者依次试过 apitrace、Intel Graphics Monitor 和 PIX。最终通过给 `d3d9` 加载 symbols，在真正的 `CreateQuery` callee 上断点，定位到为 Nvidia INTZ 扩展加入的 `nvapi`。移除它并修 shader 后画面恢复。

物理则卡在 Treyarch 的 GJK 实现。作者先验证 broad phase 产生的碰撞 pair 正确，再聚焦 `phys_gjk_info::collide()`、`gjk()`、continuous collision 的 `gjk_ray_cast()` 和末尾 pushout。这个顺序很重要：先证实上游输入，再把范围缩到最可能的数学实现，而不是在整套 physics 中盲改。

## AI 调试带来的变化

作者此前对 AI 很保留，会把 AI 改过的内容标成 `aislop`，因为它不像 Hex-Rays 那样由确定性算法产生。后来他使用 Claude Code、IDA MCP 和大上下文模型，先要求逐函数对照 IDA/ASM，再扩大到逐文件和带入口提示的任务。约一天半后，AI 找到了 GJK 中的几个小型数学错误，碰撞开始工作。

作者给出的评价并不神化 AI：

- typo 和小错误的查找非常快；
- 复杂任务需要持续引导，推进速度取决于问题性质；
- 最明显的收益是并行，人可以在 AI 查一组文件时继续做另一组运行测试；
- 任务范围是逐步放大的，最初始终以 IDA/ASM 对照约束正确性。

这与 ol-mod 当前的协作方向高度一致。Agent 最有价值的角色不是生成大量“看起来像引擎”的代码，而是在可靠工具、权威二进制和可重复运行证据之间持续缩小问题范围，并把重复操作自动化。

## 对 ol-mod 的直接启发

1. **从 server 形态恢复 client/gameplay 时，应先确认被常量屏蔽但仍保留的路径。** 这对理解 BO1/KisakBlack 的 server world 结构很有用，但 CODOL 是否相同仍需自己的 xref 和运行证据。
2. **测试地图会主动选择后续工作。** `mp_mountain` 的玻璃让 snapshot 问题提前出现。ol-mod 在恢复 initial snapshot 时也应选择能暴露基线、entity delta 和 playerstate 的最小场景，而不是只选最容易暂时进图的场景。
3. **先验证上游，再调复杂算法。** broad phase 已正确才继续 GJK，类似地，ol-mod 应先锁定 gamestate、ack 和 baseline 输入，再解释客户端 snapshot parser 的后续失败。
4. **工具链要迭代，但必须衡量完整周期。** RawPDB + IDA 批量生成减少了手工整理，却未保证总项目更快。新工具应记录准备、等待、捕获、分析和清理各阶段耗时，避免只优化表面动作。
5. **AI 需要证据护栏和渐进授权。** 从逐函数 ASM 校验到逐文件任务，是比“一次让 Agent 重写整个系统”更可靠的扩展路径。

## 文末的引擎史假说

附录根据 Kelly Slater 源码、COD3 MAP 和一份 Spider-Man 3 的 GCC 预处理源码，提出 Treyarch 可能长期存在两条技术线：原 Treyarch 的所谓 NGL/Nyarlathotep 系统，以及从 COD:UO、后来吸收 IW3 的 COD 分支，最终在 BO1 前后合流。作者明确把这部分写成外部观察者的推测。

这段材料对寻找物理代码亲缘关系很有价值，尤其是 BO1 `phys_player_collision_mode = 1` 与 Spider-Man physics 的相似性；但它不能直接证明 CODOL 的继承关系，使用时应继续标成线索而非既定事实。
