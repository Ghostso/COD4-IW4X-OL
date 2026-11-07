# 165 · Bullet_Endpos 从 7 参数到 10 参数、渲染帧上传实现

## 一、范围

本报告学习 **2 处实现**：

- `NativeWeaponBindings.cpp` 120–259 行
- `ClientRenderFrameHook.cpp` 前 100 行

## 二、`AngleVectors` 的行取反

```cpp
if (completed)
    for (std::size_t component{3}; component != 6; ++component)
        axis[component] = -axis[component];
```

只有 **3..5（第二行）** 取反——这正是"Quake 的 `AnglesToAxis` = `AngleVectors` 且第二行取反"的落地。第一行（forward）与第三行（up）原样。

## 三、`Bullet_Endpos`：本 build 多读了三个 float，且都插在中间

### 3.1 两个 ABI

```text
3.3.3.3  Bullet_Endpos 0x0055AEB0
         EDI=muzzleTrace, ESI=end
         栈上七项：seed, spread, dir, forward, right, up, maxRange

1649370  sub_592230 读【十】项
         EDI 与 ESI 未变 —— 仍然是 fld [edi] → fstp [esi]
```

### 3.2 逐槽对照

```text
[ebp+08] uint32* randomSeed     未变
[ebp+0C] float   spread         未变槽
[ebp+10] float   spread         ← 新，第二个锥半径
[ebp+14] float*  direction      原为 [ebp+10]
[ebp+18] float   randomMinimum  ← 新
[ebp+1C] float   randomMaximum  ← 新
[ebp+20] float*  forward        原为 [ebp+14]
[ebp+24] float*  right          原为 [ebp+18]
[ebp+28] float*  up             原为 [ebp+1C]
[ebp+2C] float   maxRange       原为 [ebp+20]
```

### 3.3 沿用七参数的实际后果

> **沿用七参数形式让被调用者从调用者自己的帧里读 forward、right、up 和 maxRange，并把三个未初始化的 dword 当 float 读。**

即：不崩，但取到的是**栈上残留的指针/垃圾**——`SV_IsWeaponFireBasisValid` 之所以存在，正是为了在结局处抓这类。

### 3.4 四个新值的语义（从 `sub_592230` 与 `0x595DF0` 恢复）

```text
[0x0C,0x10]  径向角界
[0x18,0x1C]  方位角界
普通子弹调用传 [0, spread] 与 [0, 360]
helper 按 lo + (hi-lo)*random 取
```

### 3.5 那两个"看起来该相等却必须不同"的值

```cpp
const float spreadMinimum = 0.0f;    // 径向下界
const float randomMinimum = 0.0f;    // 方位下界
const float randomMaximum = 360.0f;  // 方位上界
```

注释警告：

> `flt_E57A74` 在同一个调用点是 **360.0f**。**一个 90 度的上限会把每一发权威子弹限制在一个象限里。**

以及：

> 普通子弹 `CG_FireWeapon 0x595DF0` 传 `radiusAngleMinDeg=0`、`radiusAngleMaxDeg=spread`。`sub_592230` 在那些半径之间**线性采样**。**把 spread 传给两个值会把整个圆盘塌到外缘，让腰射避开准星中心。**

即：径向是 `[0, spread]`（圆盘），不是 `[spread, spread]`（圆环）。

### 3.6 栈的压入顺序与清理

```asm
push edi
push esi
push maxRange
push up
push right
push forward
push randomMaximum
push randomMinimum
push direction
push spread          ← [ebp+0C]
push spreadMinimum   ← [ebp+10]
push randomSeed
mov edi, muzzleTrace
mov esi, end
call function
add esp, 40          ; 10 个参数 × 4 字节
pop esi
pop edi
```

注意 **`push edi` / `push esi` 在压参数之前**，`pop esi` / `pop edi` 在 `add esp,40` 之后——所以 `add esp,40` 正好清掉十个参数，不碰保存的 EDI/ESI。

`spread` 与 `spreadMinimum` 的压栈顺序：**先 push spread（高地址），后 push spreadMinimum（低地址）** ⇒ `spreadMinimum` 落在 `[ebp+10]`、`spread` 落在 `[ebp+0C]`。**压栈顺序与偏移是反的**，这是调用者必须逐项核对的地方。

### 3.7 两个常量位相同

> `DEG2RAD`（`0x00DE7FA0`）与 LCG 缩放 `1/32768`（`0x00DE7BD8`）都与 3.3.3.3 的**逐位相同**。

即：这两个根本不用移植。

### 3.8 事务：结果先拷进副本

```cpp
result.randomSeed = request.randomSeed;   // 先拷种子
callBulletEndpos(..., &result.randomSeed, ...);
```

注释：

> 在一个**拷贝的** seed/result 上操作，这样一次 fault 不能发布部分源终点。

因为函数**改 `randomSeed`**（LCG 推进），先拷进去再让原生函数推进它，失败时 `result` 整体作废。

## 四、`getPlayerEyePosition` 的两道前置

```cpp
eFlags & TurretViewFlags (0x0C00)  != 0  → 拒绝
linkEntity != UnlinkedEntityNum (2047)   → 拒绝
```

注释：

> `-1` 的 `linkedEntityContext` **只在未链接玩家路径上有效**。
>
> `TODO(CODOL)`：在接受视角锁定或已链接玩家状态之前，加入服务端拥有的 tag/link 实体解析。

即：炮位视角和挂到实体上的玩家都不能走这条路径。

## 五、渲染帧上传：MSVC 的 `__try` 约束

### 5.1 那条编译约束

```cpp
// The two engine calls, each isolated in a function with NO object that
// needs unwinding. MSVC refuses __try in a function that has one, and
// `record.detail = "..."` alone is enough to create one.
[[nodiscard]] bool guardedUpload(void *const header) noexcept
{
    __try { Upload(header, header); return true; }
    __except (EXCEPTION_EXECUTE_HANDLER) { return false; }
}
```

这是 MSVC 的一条硬规则：**函数里有需要析构的对象（C++ 异常展开）就不能用 `__try`**。而 `std::string` 的赋值就足以产生一个需要 unwinding 的对象。

所以两个原生调用被**提取成独立的最小函数**，参数是裸指针，返回 `bool`。

### 5.2 `Upload(header, header)` —— 两个参数是同一个

```cpp
using ImageUploadFn = void(__cdecl*)(void*, void*);
```

注释：

> `sub_BE7470, __cdecl (void** loadDefSlot, GfxImage*)`。**`Load_GfxImage` 把 image 传给两者**，因为 load-def 指针到达时在 `image+0`。

即：调用方传入槽位地址，而槽位就是 image 本身。

### 5.3 `rendererAcceptsUploads` 的两级空检查

```cpp
if (LoadForRendererDvar == nullptr) return false;
dvar = *LoadForRendererDvar;
if (dvar == nullptr) return false;
return dvar[3] != 0x0;
```

对照反汇编：

```text
mov ecx, dword_E899CC
cmp dword ptr [ecx+0Ch], 0
jz
```

`dvar[3]` 就是 `+0x0C`。**这里是 `uint32_t*` 索引 3，与 `[ecx+0Ch]` 一致**。

### 5.4 队列的三个容器

```cpp
std::mutex QueueMutex;
std::vector<Job> Pending;
std::vector<std::unique_ptr<SvForgeGfxImage>> Retained;   // 已发布，永不释放
std::vector<ForgeImageUploadRecord> Records;
std::atomic<std::size_t> PendingCount{0};                 // 每帧无锁读
```

注释：

> 每帧**不加锁**读，所以空闲成本是一次 relaxed load。

即：热路径用原子计数做快速路径，只有真的有待上传时才拿锁。

### 5.5 四个函数指针

```cpp
RenderBegin   sub_BE2150  __cdecl (void*)            一个栈参数，调用者清理
Upload        sub_BE7470  __cdecl (void**, void*)
FiberSlot     sub_67C080  __cdecl ()
Link          DB_LinkXAssetEntry __cdecl (uint32, void**)
```

`Link` 的第二个参数是 `void**`（槽位地址），返回值是条目指针——与之前报告里 `SV_PublishForgeXAnim` 的调用形状一致。

### 5.6 原字节校验

```cpp
constexpr std::array<std::uint8_t, 5> OriginalCall{ 0xE8, 0x3D, 0xFF, 0xFF, 0xFF };
```

与头文件里 `00BE220E E8 3D FF FF FF call sub_BE2150` 逐字节一致。

## 六、关键结论

1. **参数个数变化会以"读到调用者栈上的垃圾"的方式表现**，不崩不报——只有结局校验能抓。
2. **压栈顺序与 `[ebp+xx]` 偏移是反的**，多参数自定义 ABI 必须逐项核对。
3. **圆盘 vs 圆环只差一个下界**：`[0, spread]` 与 `[spread, spread]` 的差别是"腰射能不能打准星中心"。
4. **MSVC 的 `__try` 与需要析构的对象互斥**，所以受保护的调用必须提取成最小函数。
5. **热路径用原子计数做无锁快速路径**，只有真有事才拿锁。
6. **同一个函数传两次同一个指针**不是笔误，而是"load-def 到达时在 image+0"这一事实的直接表达。

## 七、未闭合点

- `getPlayerEyePosition` 的 tag/link 实体解析是 `TODO(CODOL)`。
- `NativeWeaponBindings.cpp` 的三个 `playerState` 偏移未与本 build 对齐。
- 渲染帧上传的 DLL 版本仍未运行过（只有 Frida 版本被证实）。
