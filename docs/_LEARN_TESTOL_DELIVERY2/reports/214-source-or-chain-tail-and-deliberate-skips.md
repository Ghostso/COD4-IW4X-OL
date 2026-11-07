# 214 · OR 链的收尾、`stage=function_prefixes`、五个"故意不校验"

## 一、范围

本报告学习 `EngineBindings.cpp` 3914–4113 行。

## 二、OR 链的剩余项（本组 30+ 项）

### 2.1 按功能分组

**D. 动画脚本链**（11 项）

```text
BGAnimScriptEvent / BGFindAnims / BGAnimParseAnimScript / BGLoadAnimTrees
ScrCreateObject / ScrPrecacheAnimTrees / BGFindAnimTrees
BGFinalizePlayerAnims / MantleCreateAnims / HunkAllocXAnim
```

**E. 武器注册表**（6 项）

```text
WeaponLookup / WeaponResolver / AttachmentLookup
WeaponRegistryReset / WeaponRegistryInitialize / ZoneLoaded
```

**F. 角色与 configstring**（6 项）

```text
CharacterCurrentItemsCopy / CurrentCharacterGet / CharacterSlotGet
CharacterRecordFillDefaults / CharacterRecordToSelectionNames
ConfigStringGet
```

**总计（含前组）：约 60 项**。

## 三、那三处"故意不校验"

### 3.1 `WeaponSlotReadStaged` —— **没有 1649370 地址**

```cpp
// CODDIFF(client_loadout_capture): WeaponSlotReadStaged is NOT guarded
// here, because no 1649370 address for it has been established -- the only
// one in this tree is CodolWeaponResolve.py's 0x1945B0, and that file
// targets codoMP_client_shipRetail.exe.
```

**"这个树里唯一的那个是 `CodolWeaponResolve.py` 的 `0x1945B0`，而那个文件针对的是 `codoMP_client_shipRetail.exe`。"**

**注意**：`codoMP_client_shipRetail.exe` **就是本 build 的客户端**（§183 的 SHA256 注释里点名）。

**所以"那个文件针对的是 X"不是理由** —— 而是"那个文件里的地址可能对应别的版本"。

**这个理由本身需要更精确**，但从 §`sv_gamestate` 的记录看，`0x1945B0` 确实是 3.3.3.3 的（§185 里"`weaponSlotReadStaged_` 唯一已知地址是 3.3.3.3 的 `0x1945B0`"）。

### 3.2 `CurrentCharacterGet` —— **TODO 已自行解决**

这是最有价值的一段：

```text
CurrentCharacterGet IS guarded now, and the TODO that used to sit here
is RESOLVED ON ITS OWN TERMS.

它说："currentCharacterIndex" 在 0x00DCAB98 且有 65 个函数引用它，
所以字符串本身挑不出那个访问器 —— 退出条件是【对它函数体形状的匹配】，
而不是又一次字符串命中。

sub_6B87C0 就是那个函数体，十三条指令：
    mov eax, dword_E567C0 / cmp eax, -1 / jnz ret
    push 0 / push offset "currentCharacterIndex" / call sub_512120
    mov dword_E567C0, eax / test eax,eax / jns ret / xor eax,eax / mov back
—— 一个把负数钳到零的缓存查找，正是 0x0068A0E0 的形状，
而 dword_E567C0 除它自己的两次存储外没有任何东西写。
那 65 个字符串引用是【消费者】。
```

### 3.3 那十三条指令的完整解读

```asm
mov  eax, dword_E567C0              ; 读缓存
cmp  eax, -1
jnz  ret                            ; 缓存命中 → 直接返回
push 0
push offset "currentCharacterIndex"
call sub_512120                     ; 按名字查
mov  dword_E567C0, eax              ; 写缓存
test eax, eax
jns  ret                            ; 非负 → 返回
xor  eax, eax                       ; 负数 → 归零
mov  [缓存], eax                    ; 把零也写进缓存
ret:
```

**这是一个"缓存 + 钳制负数"的访问器** —— 而 `0x0068A0E0` 有同样的形状。

**"那 65 个字符串引用是消费者"** —— 因此**函数体匹配才是判据**，字符串匹配不行。

### 3.4 那条"从来没真的没确立过"

```text
It was also never really unestablished: CodolMatchFlow.py's 1649370 block
carries CURRENT_CHARACTER_GET_RVA = 0x2B87C0 and calls it every run.
```

**与 §185 里那段"`no address is established on 1649370` 对这一个【是错的】，而【地址整个时间都在这个仓库里】"完全对应** —— 同一个事实在两处被记录，说明它是本项目的一个反复教训。

### 3.5 `CharacterSelectionResolve` —— **OLfinal 上按设计不存在**

```cpp
// CODDIFF(character_customization): CharacterSelectionResolve is
// absent by design on OLfinal -- §16a. Not guarded, not bound.
```

**"按设计不存在"** —— 而 §213 里 `worldCharacterModelResolve_` 是同一族。

### 3.6 三处的类型对照

| 名称 | 状态 | 理由 |
|---|---|---|
| `WeaponSlotReadStaged` | 不校验 | 无本 build 地址 |
| `CurrentCharacterGet` | **已校验** | TODO 已解决（函数体匹配） |
| `CharacterSelectionResolve` | 不校验 | **按设计不存在** |
| `worldCharacterModelResolve` | **绑为 nullptr** | 同上 |

## 四、`stage=function_prefixes`：那 60 项失败时的唯一日志

```cpp
if (!std::equal(...) || ... 60 项 ...)
{
    OlMod::RuntimeLog::write(
        OlMod::RuntimeLog::Channel::GameServer,
        "engine binding validation failed stage=function_prefixes");
    return false;
}
```

**注意：日志里没有 "message binding" 字样** —— 而是 `stage=function_prefixes`。

**所以 §213 里我推测的"message binding prefix mismatch"是错的** —— 实际的日志是：

```text
"engine binding validation failed stage=function_prefixes"
```

**这意味着 60 项里任何一个失败，日志完全相同**。

### 4.1 与前两组的对照

```text
native entity 组  → "native entity binding prefix mismatch function=SV_Trace"
player DObj 组    → "player DObj binding prefix mismatch function=BG_PlayerAnimation"
function_prefixes → "engine binding validation failed stage=function_prefixes"
```

**前两组能定位到函数名，第三组不能** —— 这是 §213 指出的不一致的**准确形态**。

**而 `stage=` 这个前缀说明 bind() 是分阶段的**，所以"哪一阶段"是可报告的，但"阶段内哪一项"不是。

## 五、40+ 个指针的赋值块

```cpp
dbFindXAssetHeader_ = (DBFindXAssetHeader)(module_ + DBFindXAssetHeaderRva);
dbIsXAssetDefault_  = (DBIsXAssetDefault)(module_ + DBIsXAssetDefaultRva);
dbLinkXAssetEntry_  = (DBLinkXAssetEntry)(module_ + DBLinkXAssetEntryRva);
msgInit_ = module_ + MsgInitRva;
...
```

### 5.1 两种类型

```text
有 typedef 的 → reinterpret_cast<Typed>(...)
无 typedef 的 → 裸 module_ + Rva（存为 void*）
```

**这正是 §190 里那句"保留函数用自定义寄存器 ABI 的保持 `void*`，只能通过各自受守卫的适配器调用"**的实现。

### 5.2 三处**显式置 null**

```cpp
worldCharacterModelResolve_ = nullptr;   // §16a
```

**而注释就在赋值上方**：

```cpp
// CODDIFF(character_customization): left null on OLfinal. §16a.
```

**"显式置 null 而不是不赋值"** —— 因为 `bind()` 可能被再次调用（重绑），而**不赋值会留下上一次的值**。

### 5.3 `trace_` 的 typedef

```cpp
trace_ = reinterpret_cast<Trace>(module_ + TraceRva);
```

**`Trace` 是 §183 里那个六参数 typedef** —— 所以它是普通 cdecl，可以直接类型化。

**而 `worldTrace_` 是 `void*`** —— 因为它是自定义 ABI。

**同一个文件里，`Trace` 类型化而 `WorldTrace` 不** —— 这正说明"能否类型化取决于 ABI"。

## 六、完整赋值清单（本组 70+ 项）

### 6.1 类型化的（10 个）

```text
dbFindXAssetHeader_   DBFindXAssetHeader
dbIsXAssetDefault_    DBIsXAssetDefault
dbLinkXAssetEntry_    DBLinkXAssetEntry
ccsInitialize_        CCSInitialize
trace_                Trace
bgGetPlayerEyePosition_ BGGetPlayerEyePosition
serverGameEntitiesPointer_  void**
serverGameEntityCount_      uint32*
mantleAnims_                void**
```

### 6.2 `void*` 的（60+ 个）

```text
msgInit_ / msgWriteBits_ / msgWriteString_
levelZoneLoad_ / collisionMapLoad_ / collisionWorldLink_
ccsClear_ / ccsGetConstantString_
worldTrace_ / transformedBrushModelTrace_ / transformedCapsuleTrace_
calcTraceExtents_ / pointTraceToEntities_
dobjGeomTracelinePartBits_ / dobjContentsTracelinePartBits_
dobjTraceline_ / dobjContentsTraceline_ / pointTraceStaticModels_ / dobjCalcSkel_
gEntities_ / svLinkEntity_ / svUnlinkEntity_ / svTrace_
bulletEndpos_ / viewMovement*(4) / weaponMovement*(5) / setWeaponMovementAngles_
anglesToQuaternion_ / angleVectors_ / matrixMultiply_ / axisToAngles_
pmoveSingle_ / pmSetPitchValues_ / playerStateToEntityState_
bgAnimScriptEvent_ / bgFindAnims_ / bgAnimParseAnimScript_ / bgLoadAnimTrees_
scrCreateObject_ / scrPrecacheAnimTrees_ / bgFindAnimTrees_ / bgFinalizePlayerAnims_
nativeLerpFrameAccessorInitialize_ / bgPlayerAnimation_ / bgUpdatePlayerDObj_
mantleCreateAnims_ / hunkAllocXAnim_ / xanimFreeInfo_
```

**约 55 个 void\*** —— 占绝大多数。

## 七、关键结论

1. **60 项 OR 链失败时的日志是 `stage=function_prefixes`**，不带任何函数名。
2. **三处"故意不校验"各有理由**：无地址 / 按设计不存在 / TODO 已解决。
3. **`CurrentCharacterGet` 的 TODO 通过"函数体十三条指令匹配"解决**，而不是又一次字符串命中。
4. **那 65 个字符串引用是消费者，不是定义**。
5. **同一文件里 `Trace` 类型化而 `WorldTrace` 不** —— 能否类型化取决于 ABI。
6. **`worldCharacterModelResolve_ = nullptr` 是显式的**，因为 `bind()` 可能重绑。

## 八、未闭合点

- `WeaponSlotReadStaged` 的理由表述（"那个文件针对 shipRetail.exe"）与本 build 客户端同名这一点存在张力，需核对。
- `EngineBindings.cpp` 4113 行之后未读取。
