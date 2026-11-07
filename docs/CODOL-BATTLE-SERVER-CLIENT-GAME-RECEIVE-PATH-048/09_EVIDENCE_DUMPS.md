# 09 — 关键反汇编、交叉引用与数据流证据索引

所有 dump 均由 `scripts\048_harness.py` + `scripts\analyze_048.py` 在**只读**模式下生成,
落在 `evidence\`。可由一条命令完整重建:

```
python scripts\analyze_048.py
python scripts\verify_048.py     # 26/26 PASS 表示 046 继承与 048 结论均自洽
```

---

## 1. 机器可读索引

| 文件 | 内容 |
|---|---|
| `evidence/048_analysis.json` | **主索引**:19 个锚点的 RVA/字符串/xref/宿主函数/上游;ws2_32 IAT 全表;22 个 socket API 函数 |
| `evidence/a050_callgraph.json` | 调用图:39,018 个函数起点 + 157,148 个调用点(直接 `E8/E9` + IAT `FF15`) |
| `evidence/s232_iat_named.json` | IAT 槽 → API 名(按磁盘 EXE 的 ws2_32 序号) |
| `evidence/s20_funcstarts.json` | 函数起点索引(序言 `55 8B EC` / `sub esp` + ≥3×`0xCC` 后继 + 直接调用目标) |
| `evidence/s200_exports.json` | 映像导出表(22 项,Scaleform/NvOptimus 等) |
| `evidence/s520_coverage.json` | 长常量串清单(恢复覆盖/空洞量化,812 段) |
| `evidence/s520_tokentable.tsv` | 连接无关 token 表:RVA / token / 方向 / 首个 xref |
| `evidence/s21_netstrings.txt` | 网络/协议相关字符串清单(163 条) |

## 2. 反汇编证据(文本)

| 文件 | 目标 | 报告引用 |
|---|---|---|
| `evidence/d20_1C13A0_dispatcher.txt` | 连接无关命令分派器 `0x1C13A0..0x1C1EE0` | `03` §2.5 |
| `evidence/d21_1C15AB_connectResponse.txt` | connectResponse 处理 `0x1C15AB..0x1C1D47` | `03` §2.5 |
| `evidence/d23_1C1EE0_connless_parse.txt` | 连接无关解析器 `0x1C1EE0..0x1C2170` | `04` §4 |
| `evidence/d22_1BF300_oob_send.txt` | 连接无关发送 `0x1BF300..0x1BF3E0` | `04` §5 |
| `evidence/s53_0F8FB0.txt` | 连接无关泵 `0x0F8FB0..0x0F9155` | `04` §4 |
| `evidence/s160_1C2260.txt` | 泵→解析桥 `0x1C2170..0x1C24D0` | `04` §4 |
| `evidence/d10_P5_recv_876ED0.txt` | P5 `recv` 包装 `0x876ED0` | `04` §2.1 |
| `evidence/d11_P5_send_876DB0.txt` | P5 `send` 包装 | `04` §2 |
| `evidence/d12_873A00.txt` | `0x873A00`(`recv` 调用者) | `04` §2.2 |
| `evidence/s91_873E00.txt` | `0x873FC0`(`recvfrom` 消费) | `04` §3 |
| `evidence/s130_621E50.txt` | 报文出队 `0x621D90..0x622100` | `04` §4 |
| `evidence/s12_P4_cluster.txt` | P4 簇 `0x865300..0x866200` | `02` §3 |
| `evidence/s11_P5_cluster.txt` | P5 簇 `0x876800..0x877000` | `02` §4 |
| `evidence/s13_TQOS_recv.txt` | TQOS select+recv `0x87BA00..0x87BF80` | `02` §2 |
| `evidence/d24_F2350_servercmd.txt` | 命令/错误分派 `0xF2350..0xF2900` | `03` §2.1,§2.4 |
| `evidence/d25_376A60_lostreliable.txt` | EXE_LOSTRELIABLECOMMANDS 上报 `0x376A60` | `03` §2.1 |
| `evidence/d26_53760_host.txt` | gamestateupdate 宿主 `0x53760` | `03` §2.2 |
| `evidence/d27_37DBC0.txt` | CA_GAMESTATE 上游/UI 汇 `0x37DBC0` | `03` §2.3 |

## 3. 关键交叉引用(逐条可复核)

见 `evidence/048_analysis.json` → `anchors`。每条给出 `string`(实际字节)、`va`、`rva`、
`xrefs`(站点)、`handlers`(宿主函数区间 + 上游调用者)。

示例(connectResponse):

```json
"connectResponse": {
  "va": "0x00DBFF0C", "rva": "0x9BFF0C", "string": "connectResponse",
  "xrefs": ["0x1C17B5"],
  "handlers": [{ "xref": "0x1C17B5", "func": ["0x1C13A0", "0x1C1EE0"],
                 "callers": ["0x1C2040", "0x1C2112"] }]
}
```

## 4. 数据流证据(参数级)

| 链 | 缓冲/长度来源 | 证据文件 |
|---|---|---|
| P5 recv | `buf=[ebp+8]`、`len=[ebp+0xc]` → `recv(sock,buf,len,0)` | `d10` / `d12` |
| P5 send | `buf/len` 直通 `send` | `d11` |
| OOB 解析 | `msg_t[+8]=data`、`[+0xc]=len`、`[+0x14]=readcount`、`[+0x18]=datalen`、`[+0x1c]=curoff` | `d23` |
| OOB 分派 | 栈缓冲 `[ebp-0x408]` → `0x1C13A0` | `d23` / `d20` |
| OOB 泵→解析 | `0x621E50` 取包 → 组装 `msg_t` → `0x1C1EE0` | `s53` |

## 5. 复现命令

```powershell
cd D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-CLIENT-GAME-RECEIVE-PATH-048
python scripts\analyze_048.py
python scripts\verify_048.py
```

## 6. 证据缺口(诚实标注)

| 编号 | 缺口 | 影响 |
|---|---|---|
| E-048-1 | 第 3 节区 `0xA16000` 之后完整可读映像(仅 0x4F000/0xDBB1CC0 可读) | in-match 解析器可能在此 |
| E-048-2 | 第二样本(预期构建 `E3823FD6..F37B`) | 无法做构建差异交叉验证 |
| E-048-3 | 完整导入名表(磁盘 EXE 仅 1 个 by-name 导入) | 只能按序号识别 ws2_32(已绕过) |
| E-048-4 | 只读调用栈采样 | 需单独授权,本轮未执行 |
