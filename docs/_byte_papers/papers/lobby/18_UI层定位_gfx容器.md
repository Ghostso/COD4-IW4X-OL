# ★★ 大厅 UI 三层定位：`ff_init_common_gfx_V109.ifs`

> **这是整个大厅逆向里最重要的一处定位**
> 证据：`tools/ifs_find_keyword.py`、直接字节读

---

## 1. 一个容器装下了整个 UI/脚本层

```
ff_init_common_gfx_V109.ifs   (40,412,080 字节)
```

清单（明文，0xac 起）：

```
ff_init_common_gfx.lst
client_shipRetail/chinese/code_post_gfx_default_mp.ff
client_shipRetail/chinese/code_post_gfx_mp.ff
client_shipRetail/chinese/code_pre_gfx_mp.ff
client_shipRetail/chinese/common_mp_reload.ff
client_shipRetail/chinese/development_mp.ff
client_shipRetail/chinese/localized_code_post_gfx_mp.ff
client_shipRetail/chinese/localized_code_pre_gfx_mp.ff
client_shipRetail/chinese/localized_ui_mp.ff
client_shipRetail/chinese/mp_playlists.ff
client_shipRetail/chinese/ui_mp.ff
```

**10 个 `.ff`，全部是 UI/脚本/播放列表。**

---

## 2. 每个 `.ff` 的职责

| `.ff` | 职责（按 CoD 家族的命名约定） |
|---|---|
| **`ui_mp.ff`** | **UI 定义**（`.menu` 文件、UI 脚本、UI 资产） |
| `localized_ui_mp.ff` | UI 的本地化版本（中文字符串） |
| **`mp_playlists.ff`** | **播放列表 / 模式配置表** |
| `code_pre_gfx_mp.ff` | 启动前执行的前置脚本（GSC） |
| `code_post_gfx_mp.ff` | 启动后执行的脚本（GSC） |
| `code_post_gfx_default_mp.ff` | 默认后置脚本 |
| `development_mp.ff` | 开发者模式 |
| `common_mp_reload.ff` | 热重载支持 |
| `localized_code_pre/post_gfx_mp.ff` | 脚本的本地化 |

---

## 3. 这就是"改大厅"的确切目标

要：

| 目标 | 改哪里 |
|---|---|
| **加/删/改按钮** | `ui_mp.ff` |
| **加/删模式** | `mp_playlists.ff` + `common_gametype_*.ff` |
| **改大厅逻辑** | `code_post_gfx_mp.ff`（GSC） |
| **改中文文本** | `localized_ui_mp.ff` |
| **创建房间/开局流程** | `code_post_gfx_mp.ff` + `mp_playlists.ff` |

**全部在 10 个 `.ff` 里，全都在这一个 40MB 的容器里。**

---

## 4. 容器结构（实测）

| 项 | 值 |
|---|---|
| 文件大小 | 40,412,080 |
| `tbl[4]` | `0x2689A10` |
| `tail_len` | 2464 |
| `IWff` 偏移 | `0x2B2` |
| 载荷长度 | 40,408,902 |

**`tbl[4] + tail_len = 40,412,080 = L`** ✓（974/974 规律成立）

---

## 5. 阻碍点只有一个

```
IWff0100 之后的载荷 → AES 加密（熵 7.9998）
```

**除了这个容器层（明文），里面 10 个 `.ff` 全是加密的。**

---

## 6. 但这给出了明确的攻击面

不再是"23GB 一片黑"，而是：

```
要改大厅 → 只要解这一个 40MB 文件里的 10 个 .ff
         → 其中最关键的是 ui_mp.ff 和 mp_playlists.ff
```

**目标从"整个游戏"缩小到"两个具体的块"。**

---

## 7. 下一步

1. 确定 `IWff0100` 之后的 AES 结构（块大小、IV、密钥长度）
2. 找密钥（可能在 `nt10.py` 的 KDF 里，或客户端内存里）
3. 如果 AES 解不开，走**服务端下发**路径（playlist 可能从服务端来）

---

## 8. 附：playlist 可能来自服务端

`mp_playlists.ff` 在磁盘上，但大厅会话里也有 `10/21` 请求
`mp_playlists_shipRetail_1.0.0.info`（第 8 卷已记录，21412 字节）。

**两条来源并存 ⇒ 服务端可能覆盖磁盘版本。**

如果是这样，**改 playlist 不需要碰 `.ff`**。
