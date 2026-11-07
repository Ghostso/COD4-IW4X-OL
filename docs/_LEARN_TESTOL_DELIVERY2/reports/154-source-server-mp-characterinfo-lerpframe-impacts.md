# 154 · characterInfo 大小与 lerp 帧、client impacts 实现

## 一、范围

本报告完整学习 **2 个文件**：

- `sv_native_characterinfo_mp.hpp`（前 80 行，本 build 与 3.3.3.3 的逐字段差异）
- `sv_client_impacts_mp.cpp`（前 40 行）

`server_mp` 进度推进到 **145/154**。

## 二、characterInfo 是 0x450，不是 0x3B8

### 2.1 证据不是"某处常量"，是结构自己的步长

> 两个 build 都**直接声明自己的大小**，作为每客户端 characterInfo 数组的步长：3.3.3.3 在 `0x518136` 的 `imul edi, edi, 0x3B8`（就在动画投影前几条指令），本 build 在 `0x53DE19` 和 `0x53DE34` 的 `imul ecx, ecx, 0x450`，同一位置。**这个乘法在 3.3.3.3 上出现 342 次、在这里 496 次**，所以它是结构真实大小而不是局部常量。

### 2.2 后果

> 这驱动 ol-mod 自己的每实体存储步长**以及**它交给 `BG_UpdatePlayerDObj` 和 `BG_PlayerAnimation` 的缓冲区，**两者都通过它写入**——所以在 0x3B8 时本服务器交给引擎的缓冲区**比引擎认为自己拥有的少 152 字节**。§34b 的 playerState 短缺是同一个缺陷在另一个结构上。

## 三、lerp 帧偏移：三条路线都漏了，答案就在已在调用的函数里

### 3.1 正偏移

```text
SvNativeCharacterInfoLegsLerpFrameOffset  = 0x17C   (3.3.3.3 是 0x160)
SvNativeCharacterInfoTorsoLerpFrameOffset = 0x1BC   (3.3.3.3 是 0x1A0)
SvNativeLerpFrameSize                     = 0x40
```

两者都移动了**同样的 +0x1C**，且仍恰好相隔 `SvNativeLerpFrameSize`：

> 这正是使它成为**一次重定位而不是两个猜测**的原因。

证据（`BG_PlayerAnimation sub_40A960`，characterInfo 在 EDI）：

```text
40A981  lea esi,[edi+17Ch]                 -> sub_408E70   clear
40A992  lea esi,[edi+1BCh]                 -> sub_408E70   clear
40A9D7  lea esi,[edi+17Ch]  ecx=[edi+258h] -> sub_408A70   run, LEGS
40A9F8  lea esi,[edi+1BCh]  ecx=[edi+25Ch] -> sub_408A70   run, TORSO
```

`sub_408E70` 从另一侧确认帧自身的形状：

> 它读 `frame+0x10` 的动画号并 `& 0x3FF`，并把 `+0x10`、`+0x14`、`+0x18` 重置为 150。

### 3.2 为什么什么都没抓到

这是本组最有价值的一段方法论述：

> ol-mod 把混淆访问器对安装在 `characterInfo + 本偏移`，而 `SV_AreNativeLerpFrameAccessorsValid` 再解码**ol-mod 自己写在同一个地方**的东西——所以**一个错误偏移是完美自洽的，守卫会通过**。引擎 meanwhile 在 0x1C 字节更远处跑它的 lerp 帧，那里从未安装过任何访问器。§35j 精确预言了这个失效模式却找不到那个值；**答案在一个本服务器已经在调用的函数里**。

### 3.3 帧内部的三个偏移，一次读取全定

`sub_408A70`（同一个"run"函数）对这对指针做**两次、双向**解码：

```text
408deb  (dword_E60B3C ^ *(frame+28) ^ (frame+32))(source, frame+36)
408b9a  (dword_E60B40 ^ (frame+28) ^ *(frame+32))(frame+36, dest)
408c1c  (dword_E60B3C ^ (frame+32) ^ *(frame+28))  -- 再 SET，被提升
```

`28 = 0x1C`、`32 = 0x20`，所以：

```text
SET 指针存在 +0x1C，以 +0x20 的地址为键
GET 指针存在 +0x20，以 +0x1C 的地址为键
```

> 正是 `SV_DecodeNativeLerpFrameAccessors` 执行的那个**交叉**，也正是 §43e 的规则。两个 cookie 是 `dword_E60B3C` 与 `dword_E60B40`，即 `NativeLerpFrameSetKeyRva` 与 `NativeLerpFrameGetKeyRva` 未变。

**第三个偏移从同样的行里掉出来**：

> 两个访问器都拿 `frame + 36` 作为读/写的缓冲区，所以**受保护值在 +0x24**。关于它的宽度或角色什么都没有假设。

### 3.4 帧头其余部分，从同一函数的另一侧确认

```text
+0x10  动画号（与 a5 比较并 & 0x3FF）
+0x14  anim-def 指针（其 +0x50 是标志字，+0x44 是时长）
+0x34  lerp 速率（该函数钳到 0.1..4.0）
+0x38  与全局帧时间比较的时间戳
```

> 这解释了帧到 +0x3C 为止的全部，留下 `SvNativeLerpFrameSize = 0x40` **没有无法解释的字节**。

这种"每个字节都被解释"的标准值得记住：不是"够用"，而是**没有剩余未知**。

## 四、client impacts 实现

```cpp
SV_BuildClientImpactBatch(sourceEntityNum, touchEntityNums, linkedEntities)
```

前置拒绝：

- `sourceEntityNum > MaximumServerCollisionEntityNum (2045)`；
- `touchEntityNums.size() > 32`。

`linkedEntities` 逐个校验：

- 必须 `SV_IsCollisionEntityValid`；
- **实体号不可重复**（用 `array<bool, 2046>` 记录已见）。

任一不符即整批返回 nullopt。

输出 `SvClientImpactBatch` 记录 `sourceEntityNum / inputTouchCount / impactCount / targetEntityNums[32] / unresolvedEntityCount`——**把"输入有多少个 touch"与"解析出多少个"分开记**，这样"touch 了但没解析出来"是可见的而不是静默丢弃。

参考实现：

> BO1 `ClientImpacts 0x005F6810`、Ghosts `0x1401149D0`、BO2 `ClientImpacts/G_TouchEnts 0x005B06E0/0x005B05E0` 消费有界的 Pmove touch 列表，**按首次出现顺序**，通知两个实体，然后调用两个可用的 touch 处理器。
>
> `CODDIFF(client_impacts)`：CODOL **没有保留的服务端实现**；这个源计划解析 generation-safe 的 ol-mod 所有者，把玻璃 touch 加具体原生处理器留作 `TODO(CODOL)`。

## 五、关键结论

1. **结构大小要从它自己的步长乘法读**，而不是某处常量——`imul reg,reg,imm` 出现几百次就是证据。
2. **错误的偏移可以是完美自洽的**：当守卫验证的是"自己刚写进去的东西"时，它永远通过。要验证的是**引擎在哪里读**，不是"我写的地方读得回来"。
3. **一次反汇编可以同时定多个常量**：`sub_408A70` 一次给出交叉键、两个 cookie 和 +0x24。
4. **"每个字节都被解释"是结构理解到位的标志**，不是"够用就行"。
5. **输入数与解析数必须分别记**，否则"touch 了但没解析"会静默消失。

## 六、未闭合点

- characterInfo 除了已确认偏移之外的**其余部分仍是不透明**，本头文件不声称重建完整布局。
- 玻璃 touch 与具体原生处理器是 `TODO(CODOL)`。
- `SV_AreNativeLerpFrameAccessorsValid` 的自洽性缺陷（自证式验证）已记录但未改。
