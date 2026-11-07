# 186 · 三个键地址不是连续的、两次"地址正确但不是那个"

## 一、范围

本报告学习 `EngineBindings.hpp` 1136–1375 行。

## 二、`EntityOriginKeyRvas`：三个键**不是**连续的三 dword

### 2.1 反汇编证据

```text
BG_PlayerToEntity_SetTrajectory 0x0041167A：
    mov ecx, ds:0x00E51A84 / not ecx / xor ecx, [ebp-10h]   ; origin[0]
    lea eax, [esi+18h] / xor ecx, eax / mov [eax], ecx      ; ^ 【它自己的地址】
    mov edx, ds:0x00E51B1C / not edx / xor edx, [ebp-0Ch]   ; origin[1]
    mov ecx, ds:0x00E51B20 / not ecx / xor ecx, [ebp-08h]   ; origin[2]
```

**这同时确认了三件事**：

1. `OriginOffsets {0x18, 0x1C, 0x20}` —— 与已有的偏移表一致；
2. **解码公式 `encoded ^ fieldAddress ^ ~key`** —— `not ecx` 就是 `~key`；
3. **只有键的【地址】是错的**（旧值）。

### 2.2 三个键的实际布局

```cpp
static constexpr std::array<std::size_t, 3> EntityOriginKeyRvas{
    0xA51A84, 0xA51B1C, 0xA51B20,
};
```

第一个键距另两个 **0x98 = 152 字节**。

注释：

> **第一个键坐在离另两个 0x98 字节远的地方，所以旧的"三个连续 dword"从来不是这个 build 的布局。任何假设"三个一排"的移植——包括读一个然后加 4——【三次中有两次】落到错误的全局上。**

**"三次中有两次"** 是精确的：0xA51A84+4 与 0xA51A84+8 都是错的，只有第三个（如果按 `base+8` 算）可能碰巧对——但实际三个都在不同位置。

### 2.3 `not` 与 `xor` 的组合

```text
encoded ^ fieldAddress ^ ~key
```

反汇编里是 `not ecx`（`~key`）然后 `xor` 两次（一次与数据、一次与字段地址）。**顺序无关**因为是 XOR 与 NOT 的组合。

## 三、`CharacterItemDecodeKeyRva`：两个地址的镜像值相同

### 3.1 旧值

```text
0xA57A70  —— 是这个 build 上真实的运行时 key，但【不是】解码角色物品记录的那个。
```

注释：

> 它是这个块里**唯一一个旁边没有推导的地址**——§51k 最温和的形式：**一个未记录的常量夹在两个有记录的常量之间**。

### 3.2 新值的证据

```text
sub_619E90 在 0x619f20 结束于
    ROL32(dword_E4DD90 ^ *(dword*)entry ^ *(dword*)(entry + 8), 8)
它的唯一调用者在另外四处（0x618c8e, 0x618cb2, 0x618e5a, 0x619161）
重复同样的三方 XOR 对 dword_E4DD90
dword_E4DD90 是 VA 0xE4DD90 ⇒ RVA 0xA4DD90
```

**五处独立使用**（一处加四处）⇒ 是这个键。

### 3.3 那句最关键的观察

> **两个地址都无法从它们的镜像值区分**：**两者都读 `0xFFFFFFFF`，因为两者都是运行时初始化的**。**只有调用点能区分**，这就是为什么规则是"对着一个调用点确认"。

即：**静态扫描键的地址是无效的**，因为它们在被初始化前都是同一个哨兵。

## 四、`SessionMember*` 的七个常量与两次步长

```text
SessionMemberCountRva            0x7EE13A4
SessionMemberItemHandlesRva      0xC511424
SessionMemberStride              160
SessionMemberCapacity            18
SessionMemberItemHandleCount     12
```

### 4.1 两个地址互相印证

> 计数在 `0x82E13A4` 比 `RoomSingletonRva` 的 `0x82E13FC` **低 0x58 字节**，`sub_618A00` 按计数循环而 `sub_620700` 读单例，而 `sub_620B90` 用 `v0 <= 0x11` 清 roster —— **十八，即 `MaximumSessionMembers`**。

**三条独立证据**指向 18。

### 4.2 源步长 4 与目标步长 12

```text
sub_619E90 以步长 4 走 SOURCE、以步长 12 走 DESTINATION
    （0x619efd 的 `add edi,4` / `add ebx,0Ch`）
```

结论：

> **所以源是十二个【普通】dword —— item handle，160 字节成员记录的 48 字节。**
> **携带混淆的是 12 字节的【目标】记录，而引擎自己在 `sub_810B20` 里施加它。**

**即：源是明文，目标是密文。** 这与之前报告里"`record+20` 是 KEY 字段"是同一族。

## 五、`bind()` 与 `valid()` 的分工

```cpp
[[nodiscard]] bool bind();
[[nodiscard]] bool valid() const;
[[nodiscard]] bool clientLoadoutBindingsAvailable() const;
```

注释：

> `client_loadout_capture` 的辅助在 OLfinal 上**未绑定**，所以它们的存在**单独报告而不是折进 `valid()`**——它们的缺席**降级一条客户端路径，不意味着引擎未绑定**。

**这是"可选绑定的失败不应伪装成引擎不可用"**。

## 六、`nativeConfigString` 返回原生指针

```cpp
// The raw native accessor. Returns CODOL's own pointer, which may be
// into either the parsed gamestate table or the constant-configstring
// chunks depending on the index's class.
[[nodiscard]] const char *nativeConfigString(std::uint32_t index) const;
```

**返回的是原生指针，不是拷贝** —— 所以调用方必须知道它可能指向两种不同的存储。

## 七、`findXAsset` 包装了 `allowDefault` 的区别

```cpp
// DB_FindXAssetHeader with the allowDefault distinction this build's
// two-parameter version cannot express on its own.
[[nodiscard]] XAssetHeader findXAsset(
    std::uint32_t type, const char *name, bool allowDefault) const;
```

与前面 §9 呼应：**两参数版本无法表达这个区别**，所以需要一个包装。

而 `findXAsset()` **还要单独问 `DB_IsXAssetDefault`**，因为 `allowDefault=false` 只抑制未命中路径。

## 八、`reportSessionMemberItemHandles()` 的"测量而非健康检查"

```cpp
// OLMOD(section-48-input-probe): what the room roster actually holds, as one log
// line. This is a MEASUREMENT and not a health check, so it reports on every call
// including the empty case -- "count=0" and "unreadable" are different answers and
// silence would be neither. Section 44a: a reporter that cannot fire reads as
// innocence.
```

**"一个无法触发的报告器读起来像清白"** —— 这是本项目反复出现的原则（"读到"与"读不出"必须都可见）。

## 九、`profileSlotProbeEnabled()` 默认关的理由

```cpp
// Every caller of currentCharacterGet_ and characterSlotGet_ must pass this
// first. It is not defensive style -- see the CODIFF on CharacterSlotGetRva.
// OLMOD_PROBE_PROFILE_SLOTS=1. Off by default: the native profile call's
// safety on the bridge thread is not established.
```

**"在桥线程上的安全性未确立"** —— 所以默认关，且**每一个调用者都必须先过这个门**。

## 十、`reportClientCharacterInfo()` 读的那一面

```cpp
// What the CLIENT will hand BG_UpdatePlayerDObj for each clientNum: whether
// its characterInfo is valid and what base model it resolved. The one
// instrument that reads the side an invisible player actually fails on.
```

**"读的是隐形玩家真正失败的那一侧"** —— 这是一个诊断设计原则：**站在失败的一侧读，不要在成功的一侧读**。

## 十一、`characterPresentationResolverAvailable()`

```cpp
// Whether the character-model resolver exists on this build at all.
// On OLfinal it does not ... so "resolve failed" and "there is nothing here
// to resolve with" are different answers and the caller has to be able to
// tell them apart.
```

**"解析失败"与"没有东西可以解析"是不同答案**——又一次同一个原则。

## 十二、`installAlphaWeaponPorts()` 的三类

```text
两个实测后代
八个显式兼容别名
一个转换后的 Barrett
```

注释：

> 普通别名**克隆它们的源模型表**；**Barrett 在它的转换模型族驻留之后发布精确的四行 alpha 表**。

即：**15 个 port 分三类，处理方式各不相同**。

## 十三、三个 audit 都是只读且 opt-in

```text
auditAlphaWeaponModelPointers()   OLMOD_ALPHA_WEAPON_MODEL_AUDIT=1
auditXModelSurfaces()             OLMOD_XMODEL_SURFACE_AUDIT=1
auditAlphaBarrettAssetTemplates() client bridge `alpha-barrett-templates`
```

第三个的注释：

> 它写出精确的 104 字节 Material 与 52 字节 GfxImage 头、texture 行，以及保留的 16 字节 image load definition 到运行时日志旁。**它从不链接或改动资产。**

**三条都是"只读 + 环境变量门控"**，而第三条还是**从控制口触发**而不是环境变量。

## 十四、关键结论

1. **三个键不连续**（0x98 差距），"读一个加 4"三次里错两次。
2. **解码公式 `encoded ^ fieldAddress ^ ~key`** 从反汇编直接读出。
3. **两个候选键的镜像值都是 `0xFFFFFFFF`** ⇒ 静态扫描无效，只能对着调用点确认。
4. **源明文、目标密文**（步长 4 vs 12），引擎自己施加混淆。
5. **可选绑定的失败不折进 `valid()`**。
6. **"一个无法触发的报告器读起来像清白"**；"读不到"与"读到空"必须都可见。
7. **站在失败的一侧读**（clientInfo 而不是解析结果）。

## 十五、未闭合点

- `resolveSessionCharacterPresentation` 在 OLfinal 上没有解析器（需回退路径）。
- `EngineBindings.hpp` 1375 行之后未读取。
