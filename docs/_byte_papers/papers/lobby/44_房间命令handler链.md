# 房间命令的 handler 链与"对象为空"

> 承接 `lobby/43`
> 本篇把 `room.*` 命令的实现追到根上。

---

## 1. 注册模式（`0x63a0xx`–`0x63a300`）

每个命令注册都是同一套：

```asm
mov esi, <命令名 VA>          ; 例如 0xdc6b98 = "room.startgame"
call 0x4f37a0                 ; 查找/分配注册槽
test eax, eax
jne  <已存在，跳过>
mov [slot+0], edi             ; 上一个链
mov edi, <slot>
mov [slot+4], esi             ; 名字
mov [slot+8], <handler VA>    ; ★
mov [0x33303b0], edi          ; 链表头
```

**结构体：`{next, name, handler, ...}`。**

### 已提取的映射

| 命令 | 名字 VA | handler |
|---|---|---|
| `room.leave` | `0xdc6b8c` | `0x0639890` |
| `room.startgame` | `0xdc6b98` | **`0x639890`** |
| `room.balance` | `0xdc6c00` | `0x0639a10` |
| `room.changemap` | `0xdc6c20` | **`0x639a50`** |

---

## 2. handler 是"转发器"

### `room.startgame`（`0x639890`）

```asm
mov ecx, [0x082e13fc]     ; 取房间对象
mov eax, [ecx]
mov edx, [eax+0x38]       ; ★ vtable + 0x38
jmp edx
```

### `room.changemap`（`0x639a50`）

```asm
mov ecx, [0x082e13fc]     ; 同一个对象
mov eax, [ecx]
mov edx, [eax+0xC0]       ; ★ vtable + 0xC0
jmp edx
```

**⇒ 两条命令都转发到同一个对象的虚函数，
只是 vtable 槽不同（`+0x38` vs `+0xC0`）。**

---

## 3. ★★ 关键：那个对象指针是 **0**

```
[0x082e13fc] = 0x00000000
```

**实测（本 dump）。**

**⇒ `room.startgame` 和 `room.changemap` 如果现在被调用，
会访问空指针。**

**⇒ 房间对象在抓 dump 时还没创建。**

---

## 4. 与项目已有结论的呼应

`memory: codol-myhandler-never-created-root-cause`：

> `dwRoomMatch::Init` 的 MyEventHandler 实例数 = 0
> ⇒ 建房回调永不触发 ⇒ 整条链断

**现在多了一条独立佐证：**

**房间对象 `[0x082e13fc]` 本身就是 0。**

**⇒ 不只是"回调没注册"，是"宿主对象根本不存在"。**

---

## 5. `0x082e13fc` 的 302 处引用

```
refs = 302
```

**302 处代码读这个全局。**

**这说明：房间对象是整个房间子系统的中心。**

**一旦它被创建，302 处逻辑会同时活过来。**

---

## 6. 命令参数格式（从 handler 反推）

`room.startgame` 的 handler 只做了：

```
mov ecx, [obj]; mov eax, [ecx]; jmp [eax+0x38]
```

**没有读任何参数栈。**

**⇒ `room.startgame` 不接受参数（或者参数在虚函数里读，
从 `[esp+...]` 直接拿）。**

**`room.changemap` 同理。**

**⇒ 如果要传地图名，可能是通过另一个 dvar 或约定好的全局状态。**

---

## 7. 对"控制房间"的影响

| 事实 | 影响 |
|---|---|
| 命令存在且已注册 | ✅ 可调用 |
| handler 是 vtable 转发 | ✅ 结构简单 |
| **房间对象为 0** | ❌ 调用会崩 |
| handler 不读参数 | ⚠️ 参数传递方式未知 |

**⇒ "调 `room.changemap` 换地图"这个想法，
卡在"房间对象不存在"这一步。**

**这与整个项目的核心问题一致：
房间子系统从未初始化。**

---

## 8. 下一步

1. 找 `0x082e13fc` 的写入点（谁创建房间对象）
2. 确认是否与 `dwRoomMatchUber`（`memory: codol-dwroommatchuber-never-created`）是同一个
3. 如果对象创建了，vtable `+0x38` / `+0xC0` 分别是什么函数
