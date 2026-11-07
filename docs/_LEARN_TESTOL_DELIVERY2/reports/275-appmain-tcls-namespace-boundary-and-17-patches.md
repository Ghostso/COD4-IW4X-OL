# 275 · **TCLS 的命名空间边界**、十四个补丁的清单、`com_maxfps` 的 320 天花板

## 一、范围

本报告学习 `Appmain.cpp` 1040–1260 行。

## 二、**十四个补丁/钩子的完整清单**

```text
① installClientProcessPatches()                 CODOL_CLIENT_EXECUTION_STATE_PATCH
② installClientLoopFxNullGuardPatch()           （在 ① 的分支里，无条件）
③ installForceRecordValidatorPatch()            CODOL_FORCE_RECORD_VALIDATOR=1
④ installClientEntityEventWeaponGuardPatch()
⑤ installClientEntityEventRangeGuardPatch()
⑥ installClientAmmoLookupWeaponGuardPatch()
⑦ installClientWeaponInventoryGuardPatch()
⑧ installClientUiOperatorResolverGuardPatch()
⑨ installClientBatteryDisplayPatch()            （返回局部变量，不入全局槽）
⑩ installClientRawInputPatch()                  CODOL_RAW_MOUSE_INPUT
⑪ installDisconnectWitness()                    OLMOD_DISCONNECT_WITNESS=1
⑫ publishTclsMapping()                          
⑬ installUnlockAllPatch()                       OLMOD_UNLOCK_ALL=1
⑭ installPlaintextConfigPatch()                 OLMOD_PLAINTEXT_CONFIG=1
⑮ installMaxFpsCeilingPatch()                   OLMOD_MAXFPS_CEILING=<n>
⑯ installClientAnimtreeHook()                   CODOL_ANIMTREE_RESOLVE_HOOK=1
⑰ installClientRenderFrameHook()                CODOL_IMAGE_UPLOAD_HOOK=1
```

**⇒ **十七个**（我数十七）。**

### 2.1 而 ①–⑨ 在**同一个 `if (!ClientProcessPatchAttempted)` 块里**

**⇒ 所以它们共享一个"只尝试一次"的门。**

**⇒ 而 ⑩–⑰ 在**块外**，各自有自己的门。**

### 2.2 而 ⑨ 用局部变量

```cpp
const auto batteryDisplayPatch = CodolGameServer::installClientBatteryDisplayPatch();
logGameServer(std::string("client battery HUD divisor patch ") +
    CodolGameServer::clientProcessPatchResultName(batteryDisplayPatch));
```

**⇒ 没有全局槽** —— 与其他八个不同。

**⇒ 所以它的结果不被后续代码使用。**

### 2.3 而 ② 的**无条件**

```cpp
ClientLoopFxPatch = CodolGameServer::installClientLoopFxNullGuardPatch();
logGameServer(...);
```

**⇒ 在 `else` 分支里，无条件执行。**

**⇒ 所以它不受任何环境变量控制。**

## 三、`CODOL_FORCE_RECORD_VALIDATOR` 的中文注释

```php
// ★★★ 2026-10-07 04:5x -- 探针：把候选记录校验器 `sub_806F20`(RVA 0x406F20) 改成
// `mov al,1; ret 4`，让客户端自己的成功路径跑起来（等效于 frida 强制，但无需注入：
// 本机客户端虚拟空间 ~1998 MB，frida attach 40+ 次全失败）。
// 依据与边界见 `ClientProcessPatches.cpp` 实现处注释；只在 CODOL_FORCE_RECORD_VALIDATOR=1 时生效。
```

### 3.1 五个信息

```text
0x406F20              sub_806F20 的 RVA
`mov al,1; ret 4`     两个字节 + ret 4 ⇒ 强制返回 true 且清 4 字节栈
~1998 MB              本机客户端虚拟空间
frida attach 40+ 次全失败
只在 CODOL_FORCE_RECORD_VALIDATOR=1 时生效
```

### 3.2 **"frida attach 40+ 次全失败"**

**⇒ 一个非常具体的失败记录。**

**⇒ 而理由是"本机客户端虚拟空间 ~1998 MB"** —— 接近 2 GB。

**⇒ 32 位进程的上限约 2 GB（或 3 GB with LAA）** ⇒ **所以 frida 需要的空间不存在。**

**⇒ 这解释了为什么本项目**只能**用内存补丁而不是动态注入。**

**⇒ 与记忆里"frida attach 40+ 次全失败"一致。**

### 3.3 而 `ret 4` 意味着**函数是 `__stdcall`**

**⇒ `mov al,1` 返回 true，`ret 4` 清一个参数。**

## 四、**TCLS 的命名空间边界**（本组最重要的一段）

### 4.1 那段完整论证

```php
// PUBLISH THE TCLS MAPPING FROM IN HERE, and say whether it was needed.
//
// TenProxy opens TCLS_SHAREDMEMEMORY<pid> during this process's own startup and dies
// at [100] if it cannot. SampleLauncher creates that name from ANOTHER process, which
// works on Windows and was measured NOT to under Wine: the mapping existed twice over
// and TenProxy still got Error code = 2. A name that exists and cannot be opened from
// the target process is a namespace boundary, and publishing harder from outside does
// not cross one.
//
// This runs in the client, ~30 s before TenProxy asked on the failing machine, so it
// cannot lose on timing either. And it reports ALREADY VISIBLE when the cross-process
// mapping was reachable, which is the measurement nothing else could take.
```

### 4.2 五层

```text
1. TenProxy 在本进程启动时打开 `TCLS_SHAREDMEMEMORY<pid>`，打不开就死在 `[100]`
2. SampleLauncher 从【另一个进程】创建那个名字 ⇒ 在 Windows 上有效，在 Wine 上【实测无效】
3. 现象：映射存在了【两次】，而 TenProxy 仍得到 `Error code = 2`
4. ⇒ 【一个存在但从目标进程无法打开的名字是一个命名空间边界，而从外面"更用力地发布"不跨过它】
5. ⇒ 所以从【客户端内部】发布
```

### 4.3 这是整个项目里最精确的一段 Wine 记录

**两个观测**：

```text
mapping existed twice over      （映射存在了两次）
TenProxy still got Error code = 2  （仍然 ERR_FILE_NOT_FOUND）
```

**⇒ 所以"存在但打不开"⇒ 不同命名空间。**

**⇒ 与记忆里"TCLS_SHAREDMEMEMORY<pid> 是全流程的钥匙"**相关**。**

**⇒ 而这个发现是"钥匙存在但拿不到"。**

### 4.4 而"在失败机器上早 ~30 秒"

**⇒ 所以时间不是问题（客户端的发布早于 TenProxy 的请求）。**

**⇒ 这排除了"时序竞争"这个假设。**

### 4.5 而 `ALREADY VISIBLE` 是**唯一能做的测量**

```php
// And it reports ALREADY VISIBLE when the cross-process
// mapping was reachable, which is the measurement nothing else could take.
```

**⇒ 所以 `TclsMappingResult` 有一个 `AlreadyVisible` 值。**

**⇒ 它回答"跨进程映射是否可达"** —— 而这正是那个问题的答案。

**✓ 一个精确的诊断设计。**

### 4.6 与 §265 的"命名空间"类比

**§265**："客户端 centity 数组在专用服为空 ⇒ 实体半边死"

**§275**："TCLS 映射存在但不同命名空间 ⇒ TenProxy 打不开"

**⇒ 两个都是"你以为在同一个空间里，但不是"。**

## 五、`OLMOD_UNLOCK_ALL` 的**六种结果**

```php
// OWN EVERY ITEM. Off unless OLMOD_UNLOCK_ALL=1, and it says which of the six
// outcomes it got -- "UNEXPECTED BYTES" is the one that matters, because it means
// this is not the build the predicate was read from and NOTHING was written.
const auto unlockAll = installUnlockAllPatch();
if (unlockAll != UnlockAllPatchResult::NotRequested)
    logGameServer("unlock-all patch " + unlockAllPatchResultName(unlockAll));
```

### 5.1 六种结果，而 `UNEXPECTED BYTES` 最重要

**⇒ "这意味着这不是谓词被读取的那个 build，而**什么都没写**。"**

**⇒ 与记忆里"`UnexpectedBytes` message names address/expectation/consequence"一致** ✓

**⇒ 这也是 §247 里 `reportUnlockAllCoverage` 的前置。**

### 5.2 而在 `installClientInputPatches` 里调用

**⇒ 与 §239 的 `OLMOD_UNLOCK_ALL` 的 `call_once` 在 `readProfileWeaponClasses` 里是**两个不同的触发器**。**

**⚠ 两处都可能触发 `reportUnlockAllCoverage`？**

**⇒ 需要确认 `installUnlockAllPatch` 与 `reportUnlockAllCoverage` 的关系。**

**⇒ 待读 `ClientProcessPatches.cpp`。**

## 六、`OLMOD_PLAINTEXT_CONFIG` 的**两次一个字节跳转**

```php
// READABLE players/config_mp.cfg. Off unless OLMOD_PLAINTEXT_CONFIG=1. The game
// already writes that file as text and re-encrypts it in a second pass, so this
// skips the second pass and the matching decrypt on load -- two one-byte jumps.
```

### 6.1 三层

```text
1. 游戏已经把那个文件写成文本，然后在【第二遍】重新加密
2. ⇒ 跳过第二遍
3. ⇒ 并跳过加载时的解密
4. = 【两个一字节跳转】
```

**⇒ 与记忆里"`config_mp.cfg` 是加密的别指望"**矛盾**？**

**⚠ 记忆里**：`config_mp.cfg` 是加密的别指望

**⇒ 而这里说"游戏已经把它写成文本然后第二遍加密" ⇒ **所以加密是我们可以在写入时跳过的一个后处理**。**

**⇒ 而记忆说的是"读现有文件"那条路。

**⇒ 修法不同**：读不可行，而**不让它加密**可行。**

**⇒ 这是一处重要的补充** —— 记忆里的结论需要更新为"加密是第二遍，可以跳过"。

## 七、`OLMOD_MAXFPS_CEILING` 的**320 天花板**

```php
// RAISE com_maxfps' REGISTERED MAX. Off unless OLMOD_MAXFPS_CEILING=<n>. Only the
// dvar's upper BOUND moves; its default stays 200, so this changes nothing until
// somebody sets the dvar. Above ~320 the client outruns the server's per-frame
// usercmd queue -- see the ceiling note in the header.
```

### 7.1 三层

```text
1. 只移动 dvar 的【上界】，默认值仍是 200
2. ⇒ 直到有人设置那个 dvar 才有效果
3. 而【>~320 客户端会跑过服务端每帧 usercmd 队列】
```

### 7.2 而"每帧 usercmd 队列"

**⇒ 与记忆里"usercmd per-packet capacity 32"、"`PendingUserCmdCapacity = 32`"**相关**。**

**⇒ 320 fps ⇒ 每服务端帧（假设 20 Hz = 50 ms）16 个 usercmd。**

**⇒ 而 32 是上限 ⇒ 所以 320 fps 是"32 / 50ms × 1000 = 640"？**

**⇒ 算一下**：

```text
20 Hz 服务端帧 = 50 ms
320 fps 客户端 = 每 50 ms 16 个新 usercmd
而队列容量 32 ⇒ 2 帧的余量
```

**⇒ 而注释说"~320"是**拐点**。**

**⇒ 所以 320 对应 16/frame 而容量 32 ⇒ 有 2 倍余量？**

**⚠ 可能实际的容量或帧率不同。**

**⇒ 这是一处需要核对的具体数值。**

### 7.3 与 §263/§264 的帧率数字

```text
§263  63 ms 帧     ≈ 16 Hz
§264  权威 20 Hz   = 50 ms
记忆   默认 100 ms  = 10 Hz
§275  ~320 fps 拐点
```

**⇒ 四个数字。**

## 八、`CODOL_ANIMTREE_RESOLVE_HOOK` 的"不随包启用"

```php
// 12.140: the animtree resolve hook. Opt-in via CODOL_ANIMTREE_RESOLVE_HOOK=1
// -- it rewrites a call inside the client's own map-load path, so it does not
// ship enabled.
```

**⇒ 理由**："它重写客户端自己地图加载路径里的一个调用 ⇒ 不随包启用。"

**⇒ 与记忆里"animtree 四个钩子"、"六个钩子独立安装"相关。**

## 九、`CODOL_IMAGE_UPLOAD_HOOK` 的**四层理由**

```php
// THE RENDER-FRAME HOOK. Opt-in via CODOL_IMAGE_UPLOAD_HOOK=1. It exists
// because a GfxImage cannot be published by linking alone: image+0 is an
// IDirect3DTexture9 that sub_BE7470 has to create, the device carries no
// D3DCREATE_MULTITHREADED, and its thread is NOT the one running Com_Frame.
// See ClientRenderFrameHook.hpp for the measurement.
```

### 9.1 四层

```text
1. GfxImage 不能只靠 linking 发布
2. `image+0` 是一个 `IDirect3DTexture9`，必须由 `sub_BE7470` 创建
3. 设备【没有】`D3DCREATE_MULTITHREADED`
4. 而它的线程【不是】跑 `Com_Frame` 的那个
```

**⇒ 与记忆里"render frame hook (no D3DCREATE_MULTITHREADED, so upload must be on render thread)"一致** ✓

**⇒ 所以必须在渲染线程上传。**

### 9.2 而 §247 的 `GfxImageInitializeRva = 0x7E7470`

**⇒ `0x7E7470 + 0x400000 = 0xBE7470` ⇒ 就是这里的 `sub_BE7470`** ✓

**⇒ 第三次交叉确认。**

## 十、`CODOL_FORGE_BUNDLE` 的三段**顺序链**

```php
// CODOL_FORGE_BUNDLE names a CodolForge staging bundle.json and
// publishes the WHOLE chain from in here - images, then the materials
// that name them, then the models that name those. That ordering is
// the point: publishing from an injected thread cannot survive a zone
// transition, and this runs on the far side of one.
```

### 10.1 三层

```text
1. 三段的顺序：images → 命名它们的 materials → 命名那些的 models
2. 【顺序就是要点】
3. 因为从注入的线程发布【不能挺过一次 zone 转换】，而这里跑在转换的【另一侧】
```

**⇒ 与 §247/§248 的"发布顺序是严格依赖链"一致** ✓

### 10.2 而默认 clone 源是 `mc/mtl_t6_wpn_pda`

```php
request.cloneSource = (cloneSize > 0 && cloneSize < clone.size())
    ? std::string(clone.data())
    : std::string("mc/mtl_t6_wpn_pda");
```

**⇒ `mc/mtl_t6_wpn_pda`** —— 一个 T6（Black Ops 2）的武器 PDA 材质。

**⇒ 与 §248 的默认回退 `mc/mtl_weapon_m16` 不同。**

## 十一、两个路径变量的**同样的边界检查**

```php
const auto bundleSize = GetEnvironmentVariableA("CODOL_FORGE_BUNDLE", bundle.data(), 512);
if (bundleSize > 0 && bundleSize < bundle.size()) { ... }

const auto size = GetEnvironmentVariableA("CODOL_FORGE_IMAGE_DIR", directory.data(), 512);
if (size > 0 && size < directory.size()) { ... }
```

### 11.1 两项

```text
> 0                 非空
< buffer.size()     未截断
```

**⇒ 与 §247 的 `barrettMetadataEnabled`（`> 0 && < 32768`）同一模式** ✓

**⇒ 这是本文件里**正确**的环境变量处理方式**（对比 §274 的五字符否定与 §271 的 `strtol`）。

### 11.2 而 `bundle` 与 `directory` 都是 **512**

**⇒ 所以路径上限 511 字符。**

**⇒ 与 `MAX_PATH`（260）不同 —— 所以支持长路径？**

**⚠ Win32 API 通常限制 260 除非用 `\\?\` 前缀。**

**⇒ 512 是**库函数**的余量而不是 API 限制。**

## 十二、`dobjLocationalProbeEnabled` 回到 `size == 1 && '1'`

```php
return size == 1 && value[0] == '1';
```

**⇒ 与 §274 的五字符否定**不同**（这是同一文件里的**第六种**解析）。**

## 十三、关键结论

1. **十七个补丁/钩子**，①–⑨ 共享一个 `ClientProcessPatchAttempted` 门，⑩–⑰ 各自有门。
2. **`CODOL_FORCE_RECORD_VALIDATOR` 把 `0x406F20` 改成 `mov al,1; ret 4`**。
3. **"frida attach 40+ 次全失败"因为虚拟空间 ~1998 MB** —— 这解释了为什么只能内存补丁。
4. **TCLS 的命名空间边界**：映射存在两次而 TenProxy 仍得 `Error code = 2` ⇒ **"从外面更用力地发布"不跨过命名空间边界**。
5. **`ALREADY VISIBLE` 是唯一能做的测量**。
6. **`UNLOCK_ALL` 的六种结果而 `UNEXPECTED BYTES` 最重要**（意味着 build 不对，什么都没写）。
7. **`config_mp.cfg` 的加密是第二遍** —— 跳过它 + 跳过解密 = 两个一字节跳转。**这与记忆里"加密别指望"是需要合并补充的两面。**
8. **`com_maxfps` 的 ~320 拐点**与 usercmd 队列容量相关。
9. **`sub_BE7470` = `0x7E7470` + `0x400000`** —— 第三次交叉确认。
10. **forge 的三段顺序是要点**，因为注入线程的发布挺不过 zone 转换。
11. **`GetEnvironmentVariableA` 的 `> 0 && < size` 是正确模式**（对比五字符否定）。
12. **本文件里第六种环境变量解析**（`size == 1 && '1'`）。

## 十四、未闭合点

- `installUnlockAllPatch` 与 §239 的 `reportUnlockAllCoverage` 的关系。
- `~320 fps` 与 `usercmd` 队列容量的精确关系。
- `TclsMappingResult` 的完整枚举。
- `Appmain.cpp` 1260 行之后未读取。
