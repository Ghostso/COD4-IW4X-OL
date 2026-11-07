# 恢复 CODOL 的原生鼠标输入

2026-08-12

CODOL 在现代高回报率鼠标上的视角手感并不稳定。1000 Hz 下快速转向容易出现突然加速甚至大幅掉头，降到 500 Hz 后现象会明显减轻，但鼠标启停仍有轻微阻塞感。局内还存在服务端快照修正视角的可能，因此这次工作的目标不是用一个补丁解释所有镜头问题，而是先把客户端本地输入链中已经能够确认的旧式采样方式替换掉。

## 先弄清 S1x 到底修了什么

S1x 在 `patches.cpp` 中把一个调用点 NOP，并在主线程 scheduler 中循环调用 `SetThreadExecutionState(ES_DISPLAY_REQUIRED)`。仅凭源码旁的 `Fix mouse lag` 注释，曾经很容易把被 NOP 的调用误认为 `Sleep(1)`；对 AW 可执行文件核对后，实际被移除的正是窗口消息过程中的 `SetThreadExecutionState` 调用。

两段代码必须放在一起理解：S1x 没有简单删除系统执行状态维护，而是把它从“随窗口消息调用”迁移成“每个主帧调用一次”。这能避免高频输入消息把与鼠标采样无关的 Win32 调用塞进消息处理热路径，同时继续防止系统在游戏运行时关闭显示器。

CODOL 存在同构结构。`MainWndProc 0x00643FE0` 在 `0x00644000` 调用 `SetThreadExecutionState`，因此可以采用同样的所有权迁移。不过该修改只有在客户端帧 hook 已成功安装时才成立，否则直接 NOP 会丢掉原有行为。当前实现会校验 CODOL PE build、调用点字节和 IAT target；任一条件不满足就拒绝修改。

## CODOL 的旧鼠标采样链

反汇编确认 CODOL 并不是直接使用 `WM_MOUSEMOVE` 的 16-bit 坐标差。它的实际链路是：

```text
IN_RecenterMouse 0x0063DCB0
  -> GetCursorPos
  -> 与上一帧光标位置求差
  -> IN_ClampMouseMove 0x0063DE00
  -> IN_MouseMove 0x0063DE70
  -> CL_MouseEvent 0x0045EE80
  -> SetCursorPos 回到窗口中心
```

因此，“高 DPI 导致 `WM_MOUSEMOVE lParam` 溢出”并不适用于这份 CODOL EXE。更值得处理的是 `GetCursorPos`、每帧差分和光标回中的旧式采样方式：它会把输入精度、窗口消息时序、帧率以及系统光标状态耦合在一起，也无法自然消费现代鼠标在一帧内产生的多笔相对移动。

## 用 IW8 的设计约束实现方向

IW8 的 Xbox One PDB 展示了更新一代 COD 输入链的职责划分。`IN_OnMouseMovedEvent` 接收系统提供的相对 `MouseDelta`，在锁内累加到共享状态；`IN_MouseMove` 每帧一次性取走并清零累计值，随后仍进入原有 `CL_Input_MouseEvent`。事件频率和游戏帧率由此解耦，下游的灵敏度、按键状态、usercmd 和视角逻辑仍由引擎拥有。

当前 CODOL 实现沿用了这个结构，而没有重写整套输入系统：

- 注册 `WM_INPUT`，通过 `GetRawInputData` 获取鼠标硬件相对计数；
- 窗口事件侧加锁累计，客户端帧侧在唯一的 `CL_MouseEvent` 边界取走；
- 保留 CODOL 原有 `CL_MouseEvent` 及其下游灵敏度、输入状态和 usercmd 生成；
- 每个客户端 `Com_Frame` 调用一次 `SetThreadExecutionState(ES_DISPLAY_REQUIRED)`；
- 不设置 `RIDEV_NOLEGACY`，避免破坏现有窗口、按键和 UI 消息；
- 某帧没有 Raw Input 时回退原有 `GetCursorPos` 差分，以兼容远程桌面等不稳定提供 `WM_INPUT` 的环境。

Raw Input 默认启用。需要比较旧链或排查兼容性时，可以在启动前设置：

```text
CODOL_RAW_MOUSE_INPUT=0
```

## 已确认边界与后续验证

当前构建和测试已经覆盖 patch 字节校验、开关行为、输入累计和消费边界，部署版本也默认启用新路径。但“编译通过”和“鼠标手感完全恢复”不是一回事，仍需在相同灵敏度下对比 500 Hz 与 1000 Hz，重点观察快速连续转向、瞬间启停、冲刺转向和远程桌面回退。

旧 `SetCursorPos` 回中目前仍保留，因为 CODOL 的 UI 捕获、窗口焦点和旧路径 fallback 还依赖它；实机证明确实不再需要后才能继续缩减。DPI awareness、引擎内部 filter/accel，以及服务端快照造成的视角校正也仍是独立问题，不能因为 Raw Input 接入成功就提前宣称解决。

这次恢复最重要的结果不是增加一个“鼠标修复”特判，而是重新划清了输入所有权：系统事件负责无损累计硬件相对移动，游戏帧负责消费，CODOL 原有下游继续负责把输入变成可预测、可同步的玩家命令。
