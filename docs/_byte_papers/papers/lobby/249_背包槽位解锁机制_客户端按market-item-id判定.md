# 249 · 大厅黑箱扫荡：背包槽位解锁机制定案 —— 客户端按 **market item id** 判定（4/5 号背包根因闭合）

> 卷次：249（第八轮·字节级扫荡）
> 承接：`248`（遗留「客户端按什么键判第 N 个背包」）/`132`（AS 对象族谱）
> 方法：RTTI → COL → vtable → 实现函数 → 全局 → 初始化 → 拥有列表查找，全链机器指令

---

## §0 结论

**★★★★★ 客户端按「该槽位对应的 market item id 是否出现在已拥有列表里」判定背包是否解锁。**

- **4 号背包** 对应 market item **60027**
- **5 号背包** 对应 market item **60028**

**服务端把 SKU 241/242 都授予成 item 121** ⇒ 客户端查 60027/60028 **永远查不到** ⇒ **4/5 号背包永不解锁**。**248 卷的遗留问题闭合。**

| # | 证据 | 强度 |
|---|---|---|
| ① | `WL_GetMarketItemIdForLoadoutIndex` impl `0x7D7470`：index3→`[0x84ABB38]`、index4→`[0x84ABB3C]` | ★★★★★ |
| ② | 两全局**在 dump 里 = 60027 / 60028** | ★★★★★ |
| ③ | 初始化函数 `0x80A4C0`：从配置名 `"loadout4enable"`/`"loadout5enable"` 取值解码 | ★★★★★ |
| ④ | `WL_GetIsLoadoutSlotUnlocked` impl `0x7DBB60`：取 item id → `0x5E3760` 查拥有列表 | ★★★★★ |
| ⑤ | 库存与目录里**都没有** 60027/60028 | ★★★★★ |

---

## §1 RTTI 全表（Loadout 族）

| RTTI 名 | 地址 |
|---|---|
| `WL_GetMarketItemIdForLoadoutIndex` | `0xE6C3C8` |
| **`WL_GetIsLoadoutSlotUnlocked`** | `0xE6C3F8` |
| `WL_GetMaxNumLoadouts` | `0xE6C424` |
| **`WL_GetIsBadgeSlotUnlocked`** | `0xE6C3A8` ★ |
| `AS_IsLoadoutUnlocked` | `0xE6BDFC` |
| `WL_GetUnlockedMPLoadoutNum` | `0xE76EBC` |
| `WL_GetIsLoadoutSlotUnlocked`（vtable） | `0xDC8A6C` |

★ `WL_GetIsBadgeSlotUnlocked` 存在 ⇒ **徽章槽位是同一套机制**（248 卷 Q3 的新线索，本卷未展开）。

---

## §2 ★★★★★ `WL_GetMarketItemIdForLoadoutIndex`（impl `0x7D7470`）

```asm
0x7D7470  push ebp / mov ebp,esp
0x7D7473  mov ecx, [ebp + 8]          ; loadout 对象
0x7D7476  mov eax, [ecx + 0x10]
0x7D7479  mov eax, [eax + 0x10]       ; ★ loadout 索引
0x7D747E  cmp eax, 3
0x7D7481  jne 0x7D748B
0x7D7483  mov edi, [0x84ABB38]        ; ★ index 3 → item id A
0x7D7489  jmp 0x7D749C
0x7D748B  xor edx, edx
0x7D748D  cmp eax, 4
0x7D7490  setne dl
0x7D7493  lea edi, [edx - 1]          ; (eax==4) ? -1 : 0
0x7D7496  and edi, [0x84ABB3C]        ; ★ index 4 → item id B；其它 → 0
0x7D749C  ... 写入返回对象 [esi+0x10]
```

**⇒ 只有 index **3** 和 **4** 有 item id；0/1/2 返回 0。**

### 2.1 两个全局的取值

```
[0x84ABB38] = 0xEA7B = 60027      ← 4 号背包
[0x84ABB3C] = 0xEA7C = 60028      ← 5 号背包
[0x84ABB40] = 0xEB38 = 60216
```

---

## §3 ★★★★ 初始化：从配置名解码而来（`0x80A4C0`）

```asm
0x80A4C0  push 0xDE6CCC               ; "loadout4enable"
0x80A4C5  call 0x660B00               ; 按名查配置（154 个调用者的通用查表器）
0x80A4CD  test eax,eax / je 0x80A4E7
0x80A4D1  mov  cx, word ptr [eax]     ; 取 16 位
0x80A4D4  xor  cx, word ptr [0xE5737C] ; ★ 种子 0xA2A5
0x80A4DB  xor  cx, ax                  ; ★ 再异或指针低 16 位
0x80A4DE  rol  cx, 4                   ; ★ 循环左移 4
0x80A4E2  movzx eax, cx
0x80A4E9  push 0xDE6CDC               ; "loadout5enable"
0x80A4EE  mov  [0x84ABB38], eax
0x80A4F3  call 0x660B00
0x80A513  mov  [0x84ABB3C], eax
```

★ `"loadout4enable"` / `"loadout5enable"` **全镜像各只出现一次**（就是这里）⇒ 它们不在镜像的配置文件里，是**运行时配置**。

★ 这是 155 卷「编译期静态种子」家族（`0xE5737C` = `0xA2A5`）的又一次出现 —— **用途是让配置值不能被静态读出**。

---

## §4 ★★★★★ `WL_GetIsLoadoutSlotUnlocked`（impl `0x7DBB60`）

```asm
0x7DBB60  ... / push edi
0x7DBB6A  cmp eax, 3
0x7DBB6D  jne 0x7DBB76
0x7DBB6F  mov eax, [0x84ABB38]        ; index 3 → 60027
0x7DBB74  jmp 0x7DBB80
0x7DBB76  cmp eax, 4
0x7DBB79  jne 0x7DBB84
0x7DBB7B  mov eax, [0x84ABB3C]        ; index 4 → 60028
0x7DBB80  test eax, eax
0x7DBB82  jne 0x7DBB8B                ; item id != 0 → 查拥有
0x7DBB84  mov al, 1                   ; 非 3/4 或 item id == 0 → 【已解锁】
0x7DBB86..8A  pop/ret

0x7DBB8B  lea edi, [esp + 8]
0x7DBB8F  call 0x5E3760               ; ★ 用 item id 查"是否拥有"
0x7DBB94  cmp byte [esp + 0xc], 0     ; flag1
0x7DBB99  je  0x7DBBB0                ; flag1==0 → 返回 0
0x7DBB9B  cmp byte [esp + 0xd], 0     ; flag2
0x7DBBA0  jne 0x7DBBB0                ; flag2!=0 → 返回 0
0x7DBBA2  xor eax,eax / test al,al / sete al   ; → 返回 1 ★【已解锁】
0x7DBBB0  mov eax,1 / test al,al / sete al     ; → 返回 0 ★【未解锁】
```

★ **`0x7DBBB0` 的 `mov eax,1` + `test al,al`（ZF=0）+ `sete al` = 0** —— 两条出口的返回值**相反**，这正是"解锁/未解锁"。

### 4.1 归约式

```
unlocked(idx) =
    (idx ∉ {3,4})        → true          （默认背包本来就解锁）
  | item_id(idx) == 0    → true          （配置未给 item）
  | 否则                 → (flag1 && !flag2)  来自 0x5E3760(item_id, &out)
```

---

## §5 ★★★★ `0x5E3760(item_id, out)` —— 已拥有列表查找

```asm
0x5E3760  push ebp / mov ebp,esp
0x5E3763  mov ecx, [0xC9113D4]        ; ★ 列表计数
0x5E376E  mov esi, eax                ; item_id
0x5E3772  xor eax, eax
0x5E3774  cmp ecx, ebx / jbe 0x5E378A
0x5E3778  mov edx, [0xC9113CC]        ; ★ 列表基址
0x5E3780  cmp esi, [edx + eax*4]      ; ★ 线性查找 item_id
0x5E3783  je  0x5E37F6
0x5E3785  inc eax / cmp eax,ecx / jb 0x5E3780

; 命中后的填充：
0x5E37D0  mov [edi], esi
0x5E37DB  mov word ptr [edi + 4], 1   ; ★★ flag1 = 1（"拥有"）
```

**⇒ `[0xC9113CC]` + `[0xC9113D4]` 是一张「已拥有 item id」表；`0x5E3760` 线性查找它。**

★ flag1 就是 §4 里读的 `[esp+0xc]`（= `out+4`）。**命中 ⇒ flag1=1 ⇒ 解锁。**

---

## §6 ★★★★★ 为什么 4/5 号背包一定坏

| 检查 | 结果 |
|---|---|
| `marketplace-inventory.json` 里 `"60027"` | **无** |
| 同上 `"60028"` | **无** |
| 同上 `"121"` | **= 1** |
| catalog 中 `Item ∈ {60027,60028}` 的 SKU | **空** |
| `mkt_assets/*.csv` 里 60027/60028 | **无出现** |
| SKU 241 / 242 的 `Item` | **都是 121** |

**⇒ 服务端无论如何都不会发放 60027/60028 ⇒ 客户端 `WL_GetIsLoadoutSlotUnlocked(3)` 与 `(4)` 恒为"未解锁"。**

★ 这与 248 卷的离线模拟一致（买 241 与 242 后 `Items[121]` 仍为 1），
**但根因不是"数量没累加"，而是"item id 根本不对"** —— **248 卷的判断需要更正**。

---

## §7 修复方案（未实施）

**把 SKU → Item 的映射改对：**

| SKU | 现在 | 应为 |
|---|---|---|
| 241（4 号背包） | Item 121 | **Item 60027** |
| 242（5 号背包） | Item 121 | **Item 60028** |

**落点**：`marketplace_store.get_extra_sku_mapping()` 里已有的覆写表
（`_extra_sku_map[241] = (121, 1880)` → 改为 `(60027, 1880)`；242 同理 `(60028, 9680)`），
或 `marketplace-catalog.json` 的对应条目。

★ 改后 `purchase()` 的 `key = str(sku.Item)` 就是 60027/60028，`Items` 里出现该键 ⇒ 客户端查得到。

---

## §8 边界与告警

| # | 项 | 状态 |
|---|---|---|
| 1 | 解码 `xor cx, ax`（指针低 16 位）是否**确定性** | ⚠ **需确认** —— 若配置存储是静态地址则确定（表式查找 `[0x779583C]` 支持这一点），否则 60027/60028 只在当次会话成立 |
| 2 | **未实机** | 启动客户端需授权 |
| 3 | `[0xC9113CC]` 列表**由谁填充**（是否来自 80/203 库存） | 未展开 |
| 4 | 60027/60028 是否也是**组合包/徽章**的 item（`WL_GetIsBadgeSlotUnlocked` 存在） | ★ **新线索**，未展开 |
| 5 | 248 卷「让 item 121 累加」的方向 | **作废**（见 §6） |

---

## §9 复现命令

```powershell
python -I _rev_analysis/_p249/a2_wl_item.py    # RTTI -> vtable
python -I _rev_analysis/_p249/a3_impl.py       # 0x7D7470
python -I _rev_analysis/_p249/a4_globals.py    # 60027/60028
python -I _rev_analysis/_p249/a5_init.py       # loadout4enable/5enable
python -I _rev_analysis/_p249/a9_family.py     # WL_* 族
python -I _rev_analysis/_p249/b1_check.py      # 0x7DBB60 解锁判定
```

---

## §10 方法论

1. **★★★★★ 从「客户端函数名」入手是最快的路径。** 248 卷卡在"按 Item 还是按 Id"，而客户端**自己就有** `WL_GetMarketItemIdForLoadoutIndex` —— 名字直接给出答案。**遇到"客户端怎么判"的问题，先扫 RTTI 名字表。**
2. **★★★★ `sete al` 前必看 `test` 的操作数。** `0x7DBBBB0` 的 `mov eax,1; test al,al; sete al` 返回 **0**，与 `xor eax,eax` 那条路径**相反** —— 不逐条算就分不清哪个是"解锁"。
3. **★★★ 248 卷的根因判定需要更正。** "两个 SKU 同指一个 item ⇒ 数量不累加"是**表象**；真因是**两个槽位各要一个不同的 item id**。
4. **★★ 配置值被混淆时不代表不可用。** 解码链（`xor seed` / `xor ptr` / `rol 4`）的结果**已固化为全局**，直接读全局即可。
