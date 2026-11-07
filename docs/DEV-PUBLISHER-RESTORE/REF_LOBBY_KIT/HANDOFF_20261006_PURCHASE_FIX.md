# 购买应答修正 —— 2026-10-06

## 找到的确切差异

对照 `_ref/CodolLocalLobbyServer.cs` 第 1333-1346 行(购买分支):

```csharp
uint purchaseStatus = 1;                    // 默认失败
try {
    ...
    purchaseStatus = MarketplaceStore.Purchase(...);   // 成功返回 0
} catch (Exception ex) { Log("RAW_PURCHASE_REJECT reason=" + ex.Message); }
byte[] array27 = BuildTaskReply(localSecrets, b4, num8++, ++num9,
                                null,        // ← 结果对象为 null
                                purchaseStatus);
```

**参考实现在购买成功后回的是"空对象 + status=0"，不携带任何结果对象。**

而 `BuildTaskReplyObjects` 的第 558-574 行决定了这个 status 怎么编码:

```csharp
binaryWriter.Write((byte)10);  binaryWriter.Write(replyId);
binaryWriter.Write((byte)8);   binaryWriter.Write(status);   // ← status 在这里
binaryWriter.Write((byte)3);   binaryWriter.Write(task);
binaryWriter.Write((byte)8);   binaryWriter.Write((uint)resultObjects.Length);
...
```

## 我们之前错在哪

`lobby_server.py` 的购买分支原本回的是**一个余额对象**:

```python
obj = ms.balance_object(OUTDIR, cur)
return ([obj] if obj else []), ...
```

客户端收到 `resultObjects.Length == 1`，会按"有结果对象"去解析，
而它期望的是 0 个对象 + status —— 于是判定购买失败。
游戏内表现就是"点了购买没反应"。

## 已修正

改为与参考实现一致:

```python
return [], ("marketplace 80/%d 购买成功 sku=%d qty=%d (空对象+status=0)" ...), []
```

注意 `build_task_reply_objects` 本身就带 `status` 参数(第 618 行),
空对象时 `resultObjects.Length = 0`, 与 C# 逐字节一致。

## 待验证

起一轮, 买任意商品, 看客户端是否认。重点观察:
- 购买应答的"对象=0"
- 客户端是否随之刷新库存(80/203)
- 游戏内是否出现商品
