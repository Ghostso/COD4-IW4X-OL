# 这份 dump 的真实身份：插件已加载的沙箱运行

> 承接 `lobby/80`
> 从 dump manifest 的模块列表反推运行环境

---

## 1. 关键模块（142 个里的 3 个）

```
localnetworking.ayria32        ← Ayria Localnetworking 插件
codolgameserver.localnet32     ← 进程内战斗服插件
alwaysoffline.localnet32       ← Ayria AlwaysOffline
```

**⇒ 这份 dump 是在"插件已加载"的环境里抓的。**

**⇒ 对应 `memory: codol-testol-go-v2-working-package` 里的架构。**

---

## 2. 同时还在的模块

```
ws2_32.dll         ← 标准 Winsock
winhttp.dll
tenproxy.dll       ← 腾讯代理
ace-ats32.dll / ace-drv32.dll   ← ACE 反作弊
```

**⇒ 反作弊也加载了。**

**⇒ 这是完整的真实运行环境，不是简化沙箱。**

---

## 3. 那为什么连接单例是 0

**`[0x8269774] = 0` 意味着 `0x803830()` 从没被调用过，或调用后失败。**

**而 `0x803830` 会被 `0x808650`（初始化）之外的地方调用。**

**⇒ 如果插件把网络接管了（Localnetworking hook ws2_32），
客户端可能走了另一条路径。**

**`memory: codol-lsg-never-listening` 记录：**

> GOLDEN 版 hook 全成功 + KDF 挂载（可观测网络），
> **外部版全失败**（Localnetworking 抢先 hook 了 ws2_32）

**⇒ 这份 dump 的模块列表里有 `localnetworking.ayria32`，
说明是**外部版**路径。**

**⇒ hook 可能失败了。**

---

## 4. 这与状态的关系

**如果网络层被切断：**

```
连接单例 [0x8269774] = 0
        ↓
0xb7a670() 返回 0
        ↓
[0x84aba50] 到不了 5
        ↓
0x7f25b0() 返回 4
        ↓
状态机停在 0
        ↓
房间不初始化
```

**⇒ 整条链断在**连接**，不是**房间**。**

---

## 5. 与 `[0xe59d20] = 2` 的关系

**`[0xe59d20] = 2` 与"连接未建立"是一致的。**

**⇒ 模式 2 可能是"等待连接"的状态。**

**⇒ 客户端正常启动，但网络没通。**

---

## 6. 所以真正的结论

**这份 dump 说明：**

> **客户端的房间子系统没有问题（代码路径完整），
>  问题是网络层没建立连接。**

**⇒ 与 `memory: codol-lsg-never-listening` 的结论一致：**

> "混合方案架构成立但解决不了（外部让出 3074+我们的 lobby 接管，
>  客户端仍不 connect）"

**⇒ 房间逆向的 40 卷，证明了"房间代码是好的"，
障碍在网络层。**

---

## 7. 这个结论的价值

**它把问题**重新定位**了：**

| 之前的假设 | 现在的判断 |
|---|---|
| 房间对象不存在 = 房间模块坏了 | ❌ |
| 房间对象不存在 = **网络没连上** | ✅ |

**⇒ 修房间要先修连接。**

---

## 8. 下一步

1. 确认 `localnetworking.ayria32` 是否成功 hook 了 ws2_32
2. 确认 `[0x8269774]` 在 GOLDEN 版里是否非 0
3. 如果 GOLDEN 版有连接，抓它的 dump 对比

**这与 `codol-lsg-never-listening` 的收口结论一致：
外部方案卡在 hook。**
