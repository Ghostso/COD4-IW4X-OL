# 180 · 重新键控：复制一个缓冲区会让指针解引用失效

## 一、范围

本报告学习 **2 处实现**：

- `PlayerDataDef.cpp` 319–334 行（**该文件完整读完，334 行**）
- `NativeEntityStateBindings.cpp` 120–199 行（**该文件完整读完，199 行**）

## 二、`resolve` 的收尾

```cpp
if (stop == std::string_view::npos)
    break;
at = stop + 1;
}

resolved.index = index;
return resolved;
```

`resolve` 与 `byteOffsetOf` 的组合就是"路径 → 表索引 → 字节偏移"两步：

```cpp
byteOffsetOf(path) = resolve(path) → byteOffset(index) → offsetTable[index]
```

## 三、本组最重要的一条：`auto candidate = original` 会毁掉指针

### 3.1 症状与根因

```cpp
// RE-KEY THE COPY BEFORE THE ENGINE DECODES A POINTER OUT OF IT.
// `auto playerCandidate = playerState;` above relocated the buffer, and CODOL's
// function pointers are keyed on the slot's own ADDRESS -- so without this the
// converter's `xor ecx, ds:0x00E60B78 / call ecx` at 0x0041144C jumps to a
// different wild address on every command.
//
// Measured: 0x00198A90, 0x00DAF2AC, 0x0041144C, plus privileged-instruction
// faults from executing what it hit.
```

**四个实测的野地址**，其中 `0x0041144C` 是**它自己**——即那次 `call ecx` 跳回了它自己所在的地址，然后执行到特权指令。

### 3.2 机制

CODOL 的**函数指针用"槽位地址"作为键**：存储的值是 `f ^ key(address)`（或类似的地址相关编码）。所以：

```text
原缓冲区在地址 A → 指针编码为 encode(f, A)
复制到地址 B   → 解码时用 B → f' = decode(encoded, B) ≠ f
```

**复制使所有地址键控的指针失效**，而失效的结果不是崩溃而是**跳到随机地址**。

### 3.3 必须的三步顺序

```text
1. rebindNativePlayerStateAccessors(playerCandidate)   ← 重新键控
2. writeNativeProtectedPlayerStateFlags(...)           ← 写受保护值
3. invokePlayerStateToEntityState(...)                 ← 调用原生
```

注释：

> **这一对重新有效了，所以它后面的受保护值才可以写。顺序重要：setter 是【通过这一对】解码的，所以必须先重新键控。**

即：**键控 → 才能写 → 才能调用**。

## 四、被"退役"而非"遗忘"的尺寸假设

```cpp
// The size hypothesis this replaced is RETIRED, not forgotten: with a kilobyte of
// slack on each buffer the engine wrote through ps+72 of 15292 and es+226 of 280.
// Neither struct is too small, so entityState_s 0x118 and playerState_s 0x3BBC
// both stand.
```

这是"用实验排除一个假设"的范例：

1. 假设是"缓冲区太小"；
2. 实验是**给每个缓冲区多留 1 KiB**；
3. 观测是引擎写到 `ps+72`（共 15292 = 0x3BBC）与 `es+226`（共 280 = 0x118）；
4. 结论：**两个结构都不小**，所以尺寸假设**退役**（不是"我们忘了"，是"被测过并否定"）。

这直接支撑了之前报告里 `0x3BBC` 与 `0x118` 两个尺寸。

## 五、`otherFlags` 被编码覆盖的后果链

```cpp
// The engine's SET accessor replaced ps+0x10 with its encoded form, and that is
// the dword ol-mod reads otherFlags from. Leaving it there made the server's own
// otherFlags a different random number every frame -- which the snapshot frame
// validator then refused (`playerstate domain refused otherFlags=...`),
// so no snapshot ever reached the client.
```

**四步因果**：

```text
引擎 SET 访问器把 ps+0x10 换成编码形式
  → ol-mod 从那里读 otherFlags，读到的是编码后的随机数
  → 快照帧校验器拒绝（playerstate domain refused otherFlags=...）
  → 【没有任何快照到达客户端】
```

所以修法是：

```cpp
captureNativeProtectedPlayerStateFlags(playerCandidate, plaintextProtectedFlags);
```

**在调用后立刻把明文取回来**，因为调用本身把它覆盖了。

### 5.1 三个捕获/恢复点

```text
installServerAnimConditionStorage(previousAnimConditionBase)   调用前
rebindNativePlayerStateAccessors(playerCandidate)              调用前（因复制）
writeNativeProtectedPlayerStateFlags(...)                      调用前
invokePlayerStateToEntityState(...)                            调用
captureNativeProtectedPlayerStateFlags(...)                    调用后
restoreServerAnimConditionStorage(previousAnimConditionBase)   调用后
```

**三前两后**，每一个都有明确的理由。

## 六、失败诊断的"快照式"去重

```cpp
if (!completed || !animConditionBaseRestored || !entityProjection) {
    static std::string reported;
    details = "completed=X animConditionRestored=Y projection=Z";
    if (reported != details) { reported = details; log("playerstate->entitystate refused " + details); }
    return false;
}
```

**按"三元组是否变化"去重**，而不是按时间或按计数。这样：

- 同一种失败只记一次；
- 换成另一种组合会立刻再记一次。

`static std::string reported` 是**函数级静态** —— 与前面 `reportedByEntityState` 按地址分桶不同，这里是**全局一份**，因为失败组合的种类本来就少。

## 七、成功路径的两步发布

```cpp
playerState = std::move(playerCandidate);
entityState = std::move(entityCandidate);
projection = *entityProjection;
```

注释：

> **entityState 的 origin 字是用它们的字段地址加密的**。`SvNativeEntityState` 的赋值**把这些字从临时原生调用缓冲区重定位到这个持久所有者**。

即：`SvNativeEntityState::operator=` **不只是 memcpy** —— 它把地址键控的 origin 字重新键控到新地址。这与 `SvNativeEntityState` 头文件里那四个自定义赋值运算符对应。

## 八、`originKeys` 的五个 RVA

```cpp
for (index = 0; index < originKeys.values.size(); ++index)
    originKeys.values[index] = *(const uint32_t*)(module_ + EntityOriginKeyRvas[index]);
```

即：**每次投影前从镜像里现读密钥**，而不是缓存。因为密钥本身可能在运行时被改写（自我保护）。

## 九、关键结论

1. **复制一个地址键控的缓冲区会让所有指针失效**，而失效表现为跳到随机地址而非崩溃。
2. **必须先重新键控，再写受保护值，再调用**——顺序不可交换。
3. **"退役"一个假设要留证据**：多留 1 KiB 后引擎仍只写到本尺寸，所以尺寸不是问题。
4. **引擎的 SET 访问器会覆盖明文**，必须调用后立刻取回，否则 `otherFlags` 变成随机数并被快照校验器拒绝。
5. **`SvNativeEntityState::operator=` 会重定位加密字**，不是普通拷贝。
6. **失败诊断按"组合是否变化"去重**，因为组合种类少而出现频繁。

## 十、未闭合点

- `rebindNativePlayerStateAccessors` / `writeNativeProtectedPlayerStateFlags` / `captureNativeProtectedPlayerStateFlags` / `installServerAnimConditionStorage` / `restoreServerAnimConditionStorage` 五个函数的实现不在本文件。
- `EntityOriginKeyRvas` 五个地址来自 `EngineBindings`，未在本组核对。
- `NativeWeaponBindings.cpp` 的 `playerState` 偏移仍未与本 build 对齐（文件在自己注释里指出）。
