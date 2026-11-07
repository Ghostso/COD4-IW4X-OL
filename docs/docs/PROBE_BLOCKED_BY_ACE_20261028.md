# 探针失败的真正原因：ACE 拦截 ReadProcessMemory（2026-10-28 第七轮）

## 一、纠正上一轮的错误结论

`PROBE_FAILED_VA_DRIFT_20261028.md` 里我判断"`0x00DE07A4` 读不到是因为
地址漂移（ASLR / 解壳布局不同）"。**这个结论是错的。**

本轮实测：

```
EXE ImageBase      = 0x00400000
DllCharacteristics = 0x8100   (无 DYNAMIC_BASE，**ASLR 关闭**)
0x00DE07A4 的 RVA  = 0x9E07A4，落在 .tp3 节，**在文件内有初值**
文件内容           = 00 0a 7f 00 ...  即 0x007F0A00（dwLobbyEventHandler 首虚函数）
```

vtable 是静态存在于文件里的，地址不会漂移。

## 二、真实原因：`ReadProcessMemory` 一律 err=5

在同一活进程（pid 18056）上的一次性诊断：

```
OpenProcess(0x0410)        -> handle=0x128 成功
VirtualQueryEx(0xDE0000)   -> 成功 (protect=0x2, type=MEM_IMAGE)
Module32FirstW             -> FAILED, err=5 (ACCESS_DENIED)
ReadProcessMemory(0x400000)-> FAILED, err=5
ReadProcessMemory(0xDE07A4)-> FAILED, err=5
```

进一步验证不是权限/句柄问题：

```
QUERY_INFO|VM_READ   handle=0x11C  read=0  err=5
ALL_ACCESS           handle=0x11C  read=0  err=5     ← 即使全权限也读不了
VM_READ only         handle=0x11C  read=0  err=5
```

**拿到 `PROCESS_ALL_ACCESS` 仍然 err=5 ⇒ 不是 Windows 权限边界，是 ACE 在内核层拦截。**

这与既有记忆 `codol-ace-blocks-debug-and-read` 完全一致：

- cdb 附加被 ACE-GAME 拒绝（0xC0000022）
- 后开句柄 / t+15.5s 早期句柄的 ReadProcessMemory 都 err=5

## 三、因此被否掉的两条路

| 方案 | 状态 |
|---|---|
| 活进程内存扫描 / 定点轮询 | **不可行**（RPM err=5） |
| 硬件写断点（DebugActiveProcess） | **不可行**（ACE 拒绝调试附加） |

## 四、仍然可行的取证路径

既有记忆里已经验证过的那条：**抢早期句柄 + 立刻全量转储**
（`dump_early.py`，t+15.39s 拿到句柄、snap_003 读到 1630MB / 0 失败块）。
ACE 的保护是在客户端初始化完成后才生效，早期窗口内 RPM 可用。

⇒ 要想抓 `dwLobbyEventHandler+0x18` 写入后的值，只能：
1. 在早期窗口内多次全量转储（间隔采样），
2. 事后在转储里按 vtable `0x00DE07A4` 找实例，
3. 比较相邻快照里 `+0x18`/`+0x1c` 的变化。

已知窗口：t+23.8s 成功 / t+32.2s 失败。而 `createRoom` 发生在
客户端启动后约 **80~100 秒**（实测 21:59:30 / 22:06:04，客户端约 21:59:0x 启动）。

⇒ **窗口和事件时间不重叠**。这是本轮暴露的真正障碍：
roomId 写入房间对象发生在 ACE 保护生效之后，无法在早期窗口内捕获。

## 五、本轮实机结果

`ONCE_20261028_220445`：客户端启动、`createRoom` 成功、`11/4` 上行正常、
战斗服 **0 收包**。探针在阶段 0（vtable 自检）就失败退出。

## 六、下一步的可行选项

1. **给 dump_early 加"延后窗口"**：测试 ACE 保护是否有时段空档（如切场景、
   回大厅时短暂解除）。需要实测。
2. **放弃运行时取证**，改从纯静态推进：在转储（早期）里把房间对象的
   完整结构解出来，推断 `+0x18` 由哪个字段赋值。
3. **改换信道**：既然 `0x6371F0` 走不通，检查是否存在别的、
   不需要 roomId 路由的房间消息通道。

## 七、工具

```
CODOLServer/_mainline/diag_live_full.py     活进程一次性全诊断（★ 本轮关键）
CODOLServer/_mainline/_acc_test.py          三种访问权限实测
CODOLServer/_mainline/probe_room_identity_rva.py   RVA 版探针（已证明不可用）
```
