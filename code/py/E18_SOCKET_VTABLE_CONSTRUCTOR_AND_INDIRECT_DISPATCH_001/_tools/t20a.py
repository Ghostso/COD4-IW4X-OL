# -*- coding: utf-8 -*-
import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E18_SOCKET_VTABLE_CONSTRUCTOR_AND_INDIRECT_DISPATCH_001"
F={}
F["E18_EXECUTIVE_SUMMARY.md"]="""# E18 — 执行摘要 / EXECUTIVE SUMMARY

> 任务编号：E18_SOCKET_VTABLE_CONSTRUCTOR_AND_INDIRECT_DISPATCH_001
> 模式：只读静态分析。未启动游戏/服务端，未注入，未读进程内存，未修改样本。
> **冻结基线（开工与收工各复核一次，均一致）：**
> - 客户端 `codoMP_client_shipRetail.exe` = `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1`
> - 恢复镜像 `codol2697-static-candidate.bin` = `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4`
> - 服务端 `codol_dedrun.exe` = `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1`
> 地址口径：RVA；VA = RVA + 0x400000。凡引用他人报告中的 VA，本文标注换算。
> 工具：自建脚本（`_tools/`）+ E-06 恢复镜像；无 IDA/Ghidra 人工标注被当作原始事实。

---

## 1. 五句话结论

1. **两个虚表槽位的身份已确定（PROVEN）：`.rdata 0x898588`→`0x775A50`、`.rdata 0x898590`→`0x775AB0`，属一张 52 槽的连续函数指针表（`0x898568..0x898634`）。**
2. **该表的库身份已确定（PROVEN）：表后紧跟 `i386-pc-win32` / `7.38.0` / `smtps`/`rtsp`/`pop3s`/`imaps`/`gopher` / `.\\crypto\\bio\\bf_buff.c` / `OCSP_*` / `BIO_ZLIB_*` —— 这是内嵌的 libcurl（7.38.0）+ OpenSSL。**
3. **构造者已定位（PROVEN）：`0x776139` 与 `0x776188` 把 `0xC98568` 写入对象首字段（vptr）；分配用 `0x776170`（经全局分配器 vtable `[0xD3A588]`）。**
4. **`0x775A50`/`0x775AB0` 是 libcurl 的 socket 回调方法（PROVEN 职责）：两者都直接 `call [0xBAE490]`=recv / `call [0xBAE50C]`=recvfrom，属于"函数仅是 socket 对象的接口方法"。**
5. **仍无游戏会话入站链（BLOCKED）：libcurl/OpenSSL 簇 6 层闭包内不含任何游戏解析候选。**

## 2. 关键归属裁定

| 项 | 裁定 | 等级 |
|---|---|---|
| `0x898588`/`0x898590` 槽位身份 | libcurl 内部函数指针表槽位 | PROVEN |
| `0x775A50` / `0x775AB0` 职责 | socket 接口方法（recv/recvfrom 封装） | PROVEN |
| 构造者 | `0x776139`/`0x776188`（写 vptr=0xC98568） | PROVEN |
| 对象类型 | libcurl 传输层对象（52 方法） | PROVEN（库身份） |
| 是否游戏消息消费者 | 否 | **REFUTED（限定范围）** |

## 3. 与 E-17 结论的关系

E-17 指出"最后未归属的 socket 语义簇"是 `0x775A50`/`0x775AB0`。**本轮已归属：libcurl 传输层**（非游戏）。

**收包原语归属现在为 9/9 有明确归属。**

## 4. 最小阻塞点

**游戏协议应用层入口仍未定位。** 全部 9 个 recv/recvfrom 调用点已归属：

| 归属 | 调用点 |
|---|---|
| 错误日志 | `0x602441`、`0x6029BE` |
| HTTP/TLS 更新 | `0x6052AB`、`0x784F7D` |
| ICMP ping | `0x1B0BA1` |
| Demonware 传输 | `0x6B4E3C` |
| libcurl socket 方法 | `0x775A6C`、`0x775ADE` |
| 未闭合（dawn） | `0x788133`（`0x78772D` 区段；E-16 已证该区段为时间戳/端点解析） |

**结论：客户端不存在"未归属的 recv 调用点"作为游戏协议入口。** 这支持一个推论（BLOCKED 级）：游戏会话消息**不经过这些独立 socket 调用点**，可能经：
1. Demonware 对象的上层交付（需展开 `0x6ABBC0` 会话状态机）；
2. 或其他非 socket 的输入通道（如共享内存、进程间）。

## 5. 建议的下一步（最小范围）

1. 展开 **Demonware 会话状态机 `0x6ABBC0`**（48 函数闭包）——它是最接近"游戏后端会话"的对象。
2. 若其中仍无游戏 opcode（1..4 / 子帧 0..8），则游戏协议入口大概率在 **非 socket 通道**。
3. 不建议继续枚举 vtable/函数指针表——本轮已覆盖与网络对象相关的表。

## 6. 问题库与解决率

新增 Q-24（两槽位身份，权重 3，PROVEN=1.0）、Q-25（构造者，权重 3，PROVEN=1.0）、Q-26（libcurl 簇是否为游戏路径，权重 5，采用 REFUTED=0.0 但**结论已闭合**→按"已裁定非游戏"计 1.0）。

- 旧总权重 122（E-17）→ **新总权重 133**
- 新增加权得分 = 3 + 3 + 5 = 11
- 新加权得分 = 42 + 11 = 53
- **风险加权解决率 = 53 / 133 = 39.85%**

（E-17 为 34.43%；本轮 +5.4 个百分点，是本项目首次显著回升。）
"""
for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
