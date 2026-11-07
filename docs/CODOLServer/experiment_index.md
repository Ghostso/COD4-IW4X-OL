# CODOLServer 实验记录

## 目录结构速览
```
CODOLServer/
├─ lobby_server/
├─ experiments/
│   ├─ _aeskey_iips/
│   ├─ _aeskey_run1-8/
│   ├─ _aeskey_tqmcenter/
│   ├─ _capture1/
│   ├─ _liveplat1-A02/
│   ├─ _expA_live*
│   └─ _fullimage/
├─ subagents/
├─ logs/
└─ _write_handoff.py
```

## 关键文件示例
| 路径 | 说明 |
|------|------|
| `CODOLServer/lobby_server/server.py` | 基于 `asyncio` 的大厅 TCP 服务器，实现握手、心跳、房间列表、匹配请求 |
| `CODOLServer/experiments/_aeskey_iips/derive.py` | 从 iips 契约（JSON）推导 `key = HKDF(master, salt, info)` 并验证 GCM tag |
| `CODOLServer/_write_handoff.py` | 将 `tas_crypt.py` 生成的 TAS payload 以原始二进制写入文件，供 `probe_handoff.py` 复用 |
| `CODOLServer/logs/*.log` | 每次实验的标准输出/错误、网络抓包、异常堆栈 |
