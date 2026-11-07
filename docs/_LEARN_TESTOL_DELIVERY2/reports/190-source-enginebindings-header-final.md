# 190 · `EngineBindings.hpp` 收尾：原子状态、`EngineMsgWriter`、故障见证

## 一、范围

本报告学习 `EngineBindings.hpp` 2152–2205 行（**该文件在本组读取范围内完整，2205 行**）。

## 二、七个 `atomic` 状态变量

```cpp
mutable std::atomic<std::uint32_t> constantConfigStringChecksum_{};
mutable std::atomic<ClientLoadoutResolveFailure> loadoutResolveFailure_{};
mutable std::atomic<ClientCharacterPresentationResolveFailure> characterPresentationResolveFailure_{};
mutable std::atomic<ServerAnimationInitializationStatus> serverAnimationInitializationStatus_{NotInitialized};
mutable std::atomic<AlphaWeaponPortStatus> alphaWeaponPortStatus_{Disabled};
mutable std::atomic<bool> alphaWeaponModelAuditComplete_{};
mutable std::atomic<bool> xmodelSurfaceAuditComplete_{};
mutable std::atomic<std::uint32_t> characterPresentationResolveRecordIndex_{0xFFFFFFFFu};
mutable std::atomic<std::uint32_t> characterPresentationResolveItemId_{};
std::atomic<std::uint32_t> gameThreadId_{};
std::atomic<bool> bindingCommitted_{};
```

### 2.1 为什么是 `atomic` 而不是锁

这些字段的特征是：

- **单写多读**（帧线程写、控制线程/日志读）；
- **无复合操作**（不需要"读-改-写"）；
- **不能阻塞**（帧线程路径）。

`std::atomic<enum>` 无锁读，所以查询状态**绝不需要与帧线程同步**。

### 2.2 `bindingCommitted_` 与 `valid()` 的关系

`valid()` 大概率是 `bindingCommitted_.load(acquire)` —— 而 `bind()` 是那个置真值的函数。

`gameThreadId_` 用 `memory_order_acquire` 读（前面读过），写在 `bind()`。

### 2.3 两个"完成"布尔

```cpp
alphaWeaponModelAuditComplete_
xmodelSurfaceAuditComplete_
```

**审计只该跑一次**，所以用布尔而不是状态枚举——二值是恰当的。

## 三、`modularDependencyCache_`

```cpp
mutable std::map<std::string, std::vector<SvModularWeaponConfigString>>
    modularDependencyCache_;
```

**按名字缓存依赖列表**，所以同一把模块化武器只解析一次依赖。

**用 `std::map` 而不是 `unordered_map`** —— 遍历顺序确定，便于日志复现。

**没有 `mutex`** —— 说明这个缓存只在帧线程上访问。

## 四、`EngineMsgWriter`：`MsgWriter` 的具体实现

```cpp
class EngineMsgWriter final : public MsgWriter
{
public:
    EngineMsgWriter(const EngineBindings &bindings, std::span<std::uint8_t> buffer);

    void MSG_WriteData(std::span<const std::uint8_t> value) override;
    void MSG_WriteBits(std::int32_t value, std::uint32_t bits) override;
    void MSG_WriteString(std::string_view value) override;
    [[nodiscard]] bool overflowed() const override;
    [[nodiscard]] std::span<const std::uint8_t> data() const;

private:
    const EngineBindings &bindings_;
    msg_t message_{};
};
```

### 4.1 关键设计

1. **`final`** —— 不再派生；
2. **构造时接一个外部缓冲**（`span`），**不自己分配**；
3. **`msg_t` 是值成员** —— 与之前 `msg_t` 的 x86 布局断言直接衔接；
4. **`data()` 返回 span** —— 写出后由调用方读取。

### 4.2 与 `MsgWriter` 抽象的关系

`MsgWriter` 是纯虚基类（四个纯虚）。`EngineMsgWriter` 是**唯一的具体实现**，它把三个写操作转发给原生 `MSG_*` 函数。

**这个抽象存在的意义**：让测试可以造一个假 `MsgWriter` 来验证字节，而不必加载客户端。

### 4.3 缓冲由调用方提供

`EngineMsgWriter(bindings, span<uint8_t> buffer)` —— **缓冲所有权不在 writer 里**。

这与 `Appmain` 里的 64 KiB gamestate/snapshot 缓冲对应：**缓冲是长期存在的，writer 是临时的**。

## 五、`armNativeFaultWitness`

```cpp
/// Install the vectored fault witness for this process.
///
/// Costs nothing until a fault happens, which is why it is safe where a hook
/// on the per-frame functions involved is not.
void armNativeFaultWitness(void *module);
```

**"在 fault 发生之前不花任何成本"** —— 这是 VEH 相对钩子的根本优势：

- 钩子：每帧都付代价；
- VEH：只在异常时进入。

而它记录的是 `SV_CurrentNativeStage()`（前面 `NativeStageScope` 设置的那个标签），所以**崩溃日志能说出"当时在调谁"**。

## 六、整个头文件的结构回顾

到这里 `EngineBindings.hpp` 2205 行全部读完。它的组织：

```text
1.  stage 标签与异常详情            (1-80)
2.  四套失败分类法                  (84-168)
3.  颜色选择器置换                  (176-190)
4.  XAssetHeader                    (194-197)
5.  四个投影结构                    (201-298)
6.  审计方法声明                    (300-355)
7.  ABI typedef 与 RVA 表           (356-1200)
8.  RVA 常量（分 12 组）            (461-1200)
9.  公开方法（约 90 个）            (1201-1646)
10. 私有方法与内部类型              (1648-1977)
11. 状态变量（约 130 个）           (1979-2177)
12. EngineMsgWriter                 (2179-2197)
13. armNativeFaultWitness           (2199-2203)
```

### 6.1 这个文件的规模

**2205 行**，其中：

- RVA 常量约 **250 条**；
- 公开方法约 **90 个**；
- 状态变量约 **130 个**；
- 注释占大部分篇幅。

**注释密度是它的核心特征**：几乎每一个常量都带着"这个数是怎么来的、错在哪里、怎么被证实"。

## 七、关键结论

1. **状态用 `atomic` 而非锁**，因为它们是单写多读、无复合操作、不能阻塞的。
2. **`EngineMsgWriter` 是 `MsgWriter` 的唯一实现**，缓冲由调用方持有。
3. **VEH 在 fault 之前零成本**，这是它相对钩子的根本优势。
4. **这个文件的注释密度就是它的价值**——每个常量都带着论证链。

## 八、未闭合点

- `EngineBindings.cpp`（实现）完全未读。
- 519 vs 123 的 animtree 归因结论仍未在任何已读文件中出现。
- `cls.state` 10→0 的成因仍未点名。
