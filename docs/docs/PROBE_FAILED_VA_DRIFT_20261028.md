# 实机探针失败记录（2026-10-28 第六轮）

## 本轮做了什么

按计划在客户端运行期扫描 `dwLobbyEventHandler` 实例（vtable `0x00DE07A4`），
定点轮询其 `+0x18`/`+0x1c`（路由键槽位），期望抓到客户端解出的 key。

工具：`CODOLServer/_mainline/probe_room_identity.py`（新建，只读 RPM，不下断点）

## 结果：完全失败

```
采样 510 条，全部 {"t": ..., "instances": []}
```

诊断（`diag_vtable_presence.py`，在同一个 pid 11432 上跑）：

```
1. 读 0x00DE07A4  -> FAILED（读不到）
2. 区域统计: MEM_PRIVATE 1439 区/804MB, MEM_MAPPED 1153 区/149MB,
             MEM_IMAGE 1543 区/677MB
3. 不限类型扫 2000 个区找 0x00DE07A4 -> 命中 0 处
```

**连 vtable 本身都不在 `0x00DE07A4` 这个地址上。**

## 这意味着什么

`0x00DE07A4` 是 `MEMDUMP_20261027_v4` **那一次特定运行**里的地址。
换一个进程，这个地址就失效了 —— EXE 有 ASLR，或解壳后布局不同。

⇒ 所有基于**绝对 VA** 的结论都需要按模块基址换算 RVA，不能直接沿用。
这影响的不只是本轮的探针，也包括之前从转储里读到的所有运行时地址。

## 已确认仍然可靠的部分

这些是**文件/节内偏移**或**跨快照稳定**的，不受本轮失败影响：

| 结论 | 依据 | 为何仍可靠 |
|---|---|---|
| 路由键 = roomId 高低 32 | snap_003/snap_004 两次快照一致 | 表内容本身，非地址 |
| 表项 `0x11223344`/`0x55667788` | 同上 | 值 |
| handler = `0x006371F0` | 同上 | 代码段地址，随 EXE 基址变化但 RVA 固定 |
| 信封必须满足 `obj+8`/`obj+0xc` == roomId | `0x7E79C0` 反汇编 | 代码逻辑 |

## 下一步必须做的修正

1. **所有运行时 VA 改用 RVA**。先确定 EXE 基址，把
   `0x00DE07A4` → `RVA = 0x00DE07A4 - EXE_base`，再在新进程里
   `EXE_base_new + RVA` 重算。
2. 探针改为：先枚举模块找到 EXE 基址，再按 RVA 定位 vtable。
3. 若 EXE 是固定基址（无 ASLR），则说明是解壳时机问题
   —— 探针启动太早（客户端刚起来 6 秒），`.tvm0` 还没解密完。
   本轮的 200 秒采样窗覆盖了建房（21:59:30），所以**更可能是地址问题**。

## 本轮实机其它结果

- 客户端正常运行到 22:02:21（约 4 分钟）
- `createRoom` 成功，`11/4` 上行 7 次
- 战斗服收发 **0 包**（与之前一致）

## 工具

```
CODOLServer/_mainline/probe_room_identity.py   实例定位 + 定点轮询（本轮新建，地址假设错误）
CODOLServer/_mainline/diag_vtable_presence.py  诊断 vtable 是否可读、区域统计
CODOLServer/_mainline/diag_module_base.py      模块基址 / RVA 换算（新建，未跑到）
```
