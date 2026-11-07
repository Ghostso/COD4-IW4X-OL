# 准备按钮点不动：根因闭链（2026-10-28 第二十一轮）

## 一、推翻之前的判断

此前我判断「`AS_SetReadyState` 类无 COL/vtable ⇒ 该功能没实现」。
**这个判断不完整。**

真相是：房间 UI **不是** `UiCpp*View` 那套 Scaleform 回调，
而是走 `dwRoomMatch` 自己的事件系统。

## 二、关键证据

### 1. 全游戏只有 8 个类有 `Init`

```
UiCppChallengesView          (挑战)
UiCppItemListView            (物品列表)
UiCppMatchSelectView         (匹配选择)
UiCppNewItems                (新物品)
UiCppOnboarding              (新手引导)
UiCppSuggestedLoadoutView    (推荐配装)
UiCppView                    (基类)
dwRoomMatch                  ★ 房间界面的后端在这里
```

没有 `UiCppRoomView` —— 房间界面不走 UiCpp 那套。

### 2. `dwRoomMatch::Init` 里定义了什么

```
符号: ??Init@dwRoomMatch@@SAXXZ@
      （static void dwRoomMatch::Init(void)）

其内部唯一类型:
      .?AVMyEventHandler@?5??Init@dwRoomMatch@@SAXXZ@
      （dwRoomMatch::Init 内的局部类 MyEventHandler）
```

`?5?` 是 MSVC 的函数局部类型编号。

## 三、与既有结论的交叉验证

项目记忆 `codol-myhandler-never-created-root-cause` 早已记录：

```
dwRoomMatch::Init 的 MyEventHandler 实例数 = 0
  ⇒ 建房回调 0x63B500 永不触发
  ⇒ 整条链断
```

**本次从符号层独立确认了这条链**：`MyEventHandler` 确实
是 `dwRoomMatch::Init` 的局部类，只有当 `Init` 被调用且执行到
实例化那一行时，它才会存在。

## 四、这解释了用户的全部观察

| 观察 | 解释 |
|---|---|
| 准备按钮点下去没反应 | 没有 `MyEventHandler` 处理事件 |
| 本地"已准备"状态也不变 | 事件根本没被消费 |
| 不发任何网络上行 | 同上 |
| 房间能建、有 11/4 上行 | 那是另一条路径（客户端自动初始化） |

## 五、所以「大厅没修完」这个猜测方向是对的

`dwRoomMatch::Init` 没被调用 ⇒ 说明它的调用条件未满足。
调用条件很可能与大厅下发的某种数据有关。

这正是用户提出的假设：**大厅功能缺损 → 某个前置数据缺失 → Init 不执行**。

## 六、下一步：找 `dwRoomMatch::Init` 的调用点

需要确认：
1. 谁调用 `dwRoomMatch::Init()`
2. 调用条件是什么
3. 条件依赖哪条大厅应答

入口：搜 `??Init@dwRoomMatch@@SAXXZ@` 符号地址的引用，
或搜调用该函数的代码。

## 七、工具

```
tools/（本轮多为内联 python 检索）
关键检索式:
    ??Init@<类名>@@            —— 列出所有 Init
    .?A[VU]Xxx@?N??Init@Y@@    —— 找函数局部类型
```
