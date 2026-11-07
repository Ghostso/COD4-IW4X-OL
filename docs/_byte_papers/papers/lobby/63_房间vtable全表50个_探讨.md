# 房间 vtable 全表 · 探讨：一半靠 memory，一半靠重算

> 对应：`lobby/63_房间vtable全表50个.md`

---

## 一、一开始失败了

我写了两个 RTTI 解析脚本：

1. `dwroom_vtables.py` —— **0 个成功**
2. `dwroom_rtti2.py` —— 解析出 TD，但 **COL 0 个**

**两次都失败。**

---

## 二、为什么会失败

**第一次：我用的是"name - 9"作为 TypeDescriptor。**

**但实测 `dwRoomMessageStartGame` 的名字前 8 字节是 `0x00D77818`
（TypeDescriptor 的 vftable），所以 TD = name - 8。**

**一个字节的偏差，导致全部失败。**

---

## 三、怎么发现的

**我没有继续猜，而是做了一个校准：**

```
名字 ".?AVdwRoomMessageStartGame@@"
memory 里已经记录：TD = 0x00E6F754，vtable = 0x00DC7518
```

**这是项目里已有的、被验证过的两个地址。**

**用它反推布局，就能确定偏移。**

**结果：**

```
磁盘 offset 0x75b76d  名字
前 8 字节 = 18 78 d7 00 = 0x00D77818   ← TypeDescriptor 的 vftable
```

**⇒ TD 从名字 - 8 开始。**

---

## 四、第二次失败：COL 在磁盘上没有

**第二次解析，TD 全对（50 个），但 COL 一个都没有。**

**原因：COL 在磁盘上的 `.tp3` 里是**未初始化**的（重定位前）。**

**⇒ 必须用运行时镜像。**

**换到 `client_runtime.bin`，50/50 全中。**

---

## 五、50/50 全中的意义

**这不是"差不多对"，是**全部**对。**

**每个都满足：**
- TD 前 8 字节 = `0x00D77818`
- COL 前三字段全 0
- vtable 首项指向 COL

**三重约束同时成立，不可能巧合。**

---

## 六、最有价值的三个地址

| 类 | vtable | 为什么重要 |
|---|---|---|
| `dwRoomMessageStartGame` | `0xdc7518` | 已有的校准点，验证方法正确 |
| `dwRoomMessageRoomInfo` | `0xdc7614` | **建房必需的第一条消息** |
| `dwRoomImp` | `0xdc7270` | **与 `[0x82e13fc]` 的 vtable `0xdc7274` 对应** |

**第三个是惊喜：**

**`lobby/50` 里我从构造函数读到房间对象 vtable = `0xdc7274`。**

**现在知道 `dwRoomImp` 的 vtable 是 `0xdc7270`。**

**`0xdc7270 + 4 = 0xdc7274`。**

**⇒ 完全对上。房间对象 = `dwRoomImp` 实例。**

**两条独立路径（构造代码 / RTTI）得到同一个结论。**

---

## 七、vtable 间隔 0xC 的发现

**42 个消息类的 vtable 全部间隔 12 字节。**

**⇒ 每个类只有 3 个虚函数。**

**⇒ 这与 memory 里记录的"serialize / deserialize"两点吻合。**

**⇒ 所有房间消息类都是"三相"结构：**
```
vtable[0] = 析构
vtable[1] = serialize   （写）
vtable[2] = deserialize （读）
```

**⇒ 只要反汇编 vtable[1]，就能得到每个消息的线格式。**

**这是下一轮最直接的路径。**

---

## 八、方法论收获

> **失败两次后，先找"已知答案"校准，不要继续猜。**

**我用 memory 里已有的 `0x00E6F754` / `0x00DC7518` 校准，
一次就把偏移搞对了。**

**如果没有这个校准点，我可能会在 offset 上反复试错。**

**⇒ 项目积累的 memory，本身就是"校准点库"。**

---

## 九、下一步

**反汇编 42 个消息类的 `serialize`（vtable[1]），
逐条提取线格式。**

**这将补齐 `lobby/62` 里"92% 盲区"的大部分。**
