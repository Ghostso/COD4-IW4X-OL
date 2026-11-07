# 准备按钮为什么点不动：AS_* 类无实现（2026-10-28 第二十轮）

## 一、核心发现

对全部 1560 个文件（dll/exe/ff/ifs）做全树扫描：

```
COD OL\codoMP_client_shipRetail.exe    AS_SetReadyState, AS_GetReadyState,
                                       AS_IsRoomHost, AS_StartMatch, AS_VoteMap
（其余 1559 个文件：零命中）
```

**只有主 EXE 里有这些名字，没有任何 DLL / ff / ifs 携带。**

## 二、EXE 内 RTTI 链解析失败

用文件偏移（不是内存 VA）重做完整解析：

| 类 | 文件偏移 | RTTI 名 VA | COL | vtable |
|---|---|---|---|---|
| AS_SetReadyState | 0x762C98 | 0xE76C98 | **无** | **无** |
| AS_GetReadyState | 0x762C78 | 0xE76C78 | **无** | **无** |
| AS_IsRoomHost | 0x762C5C | 0xE76C5C | **无** | **无** |
| AS_StartMatch | 0x762CE0 | 0xE76CE0 | **无** | **无** |
| AS_VoteMap | 0x762A20 | 0xE76A20 | **无** | **无** |
| AS_ChangeTeam | 0x762B60 | 0xE76B60 | **无** | **无** |

搜索 `TD → COL`（`TD` 地址的 dword 引用）：**0 处**
搜索 `COL → vtable`：无法进行（无 COL）

## 三、这意味着什么

MSVC 的 RTTI 结构：

```
TypeDescriptor  (.?AVXxx@@ 名字串 + 前 16 字节头)
CompleteObjectLocator  (pTD 指向 TypeDescriptor)
vtable[-1]  = COL
```

**有名字、无 COL、无 vtable** 只会在以下情况发生：

1. 类被声明但**从未实例化**，编译器保留了名字串但没生成 COL
2. 类被 `#ifdef` 排除，但字符串常量仍留在只读数据
3. 类定义在源码里，但目标文件没被链接进最终产物

三种情况都指向同一结论：**当前这个客户端构建里，
房间 UI 的 `AS_*` 后端回调没有实现（或没有链接）。**

## 四、与用户现象的吻合

用户观察：**准备按钮按下去完全没有反应，连本地"已准备"状态都不变。**

若 Flash（Scaleform）里的按钮调用 `SetReadyState`，
而 C++ 侧没有注册对应处理器：
- 调用会失败或被静默忽略
- 本地 UI 状态不会更新
- 不会发出任何网络请求

这与「无反应、无状态变化、无上行」**三点完全吻合**。

## 五、但有一个反证需要考虑

10-28 的实机里，客户端**确实发出了** `11/4 setRoomData` 批次
（63B/21B/16B/245B），说明房间系统有部分工作。

那些不是按钮触发的，而是客户端自动发的（建房后初始化）。

⇒ 客户端**有房间逻辑**，只是**按钮这条特定路径**不通。

## 六、当前最可信的判断

**`AS_SetReadyState` 这个 Scaleform 回调在当前构建里没有实现。**

这不是服务端能修的问题——它属于客户端缺失功能。
除非：
- 找到另一种能触发"准备"的途径（例如控制台命令）
- 或者接受 BOT 房间模式在此构建下不可用

## 七、可以立刻验证的两件事

1. **查客户端是否有 `room.match.*` 类控制台命令**（项目记忆提到过
   "room.match.* 是控制台命令不是自动路径"）。若存在，
   可以绕过按钮直接触发准备。
2. **确认 10-26 那 8 轮成功是否进过房间界面** ——
   若是 PvE 剧情入口，那它从未使用过这个按钮，
   不能作为"房间可用"的证据。

## 八、工具

```
tools/sweep_as_names.py                            全树扫描（★ 本轮关键）
CODOLServer/_mainline/resolve_as_from_exe.py       EXE 内 RTTI 链解析
CODOLServer/_mainline/dump_dynamic_api_table.py    运行时 AS_* 名表
```
