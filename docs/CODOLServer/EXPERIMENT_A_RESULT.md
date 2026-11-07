# 实验 A（假 TQoS 闭环）— 结果与结论

日期：2026-09-25  运行目录：`CODOLServer\_expA3`

## 一、实验设置（成功建立）

```
宿主：console session 1, 1920x1080
命令：suspend_host_redirect.py --no-handoff --reply-variant 3 --seconds 55
      （经提权代理 agent_client.py 执行）
```

三条关键链路全部打通：

| 步骤 | 结果 |
|---|---|
| 挂起期改写主机名 | `ied-tqos.qq.com@0x00DD98A0 -> 127.0.0.1` ok=True |
| 本地 UDP 8000 监听 | 起成功（去掉 80/443 后不再崩） |
| 抓到客户端 TQoS 请求 | **是** |

**捕获到的请求（原始）**
```
peer    = 127.0.0.1:55913
data    = 75720010000800030000000b000064e90000006400180000   (24 字节)
解析    = magic 'ur', ruHeadLen 16, bodyLen 8, cmd 3, protoVer 0,
          reserved 11, seq 25833, businessID 100
```

**我方应答（variant 3，268 字节）**
```
7572 0010 00fc 0004 0000 0000 0000 64e9 0000 0064 0000 000f
0000 0018 | 24 x (7f000001 1f40 00000000)
```
seq 回显正确，BusinessID 100 回显，QosResFlag=0xF，24 条 GameSvr/ConndIP 全指向 `127.0.0.1:8000`。

## 二、结果

| 观察项 | 结果 |
|---|---|
| 客户端是否重传 | **否**（只抓到 1 个请求）⇒ 传输层**接受**了我方应答 |
| 游戏进程 | **存活**到实验结束（--no-handoff 后不再崩溃） |
| 后续外连 | 仅 4 轮 late-patch（tqos.gamesafe.qq.com / stun1-tub.codol.qq.com），**未再落到本地监听** |
| **`[100]` 面板** | **依然出现** |

实拍：`_expA3\after_real.png`
```
黑底 + 蓝框面板，内容：「[100]无法连接大厅服务!」，左下角「确定」按钮
```

## 三、结论

1. **崩溃根因锁定**：`len1=774` 的 TCLS 交接块 → `codoMP_client_shipRetailBase.dll +0x02ae4fe1` 访问违规（0xc0000005）。
   三次实验崩溃偏移完全一致。**去掉交接块（--no-handoff）即不崩。**
   ⇒ 与 `SHM_HANDOFF_REVERSE.md` 的警告一致：`+0x008/+0x00C` 不应带数据。
2. **拦截链路可用**：`ied-tqos.qq.com` 改写 + 本地 UDP/8000 应答，客户端**接受**。
3. **但 `[100]` 不是这条 UDP 交换的成败决定的**：
   应答被接受、不重传，`[100]` 仍然出现。
   ⇒ TQoS 8000 交换**不是** `[100]` 的直接触发点（至少"答对"它并不足以消除）。
4. 另注：本次面板是**黑底 + `确定` 按钮**，与早先实拍（splash 底 + 右上 `官网`）**外观不同**，
   可能是两个不同的错误面板 / 不同状态。

## 四、下一步

- 试其它应答变体（variant 4 / 5 / 0 / 1）与 `--qos-mode`，看 `[100]` 是否变化
- 查 `[100]` 前后游戏是否发起了**新的 TCP 连接**（尤其指向所广告的 `127.0.0.1:8000`）
- 与子代理 Nash（专职弹窗溯源）的结果交叉验证

## 五、产物

```
_expA3\local_listeners.jsonl   请求 + 应答原文
_expA3\host_redirect.log       改写/交接块/TCLS 时间线
_expA3\after.png / after_real.png   实拍（32bpp BMP 转 PNG）
CODOLServer\_mainline\_A_run.py / _A_shotloop.py   实验脚本
```
