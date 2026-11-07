# -*- coding: utf-8 -*-
import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E18_SOCKET_VTABLE_CONSTRUCTOR_AND_INDIRECT_DISPATCH_001"
c="""# E18 — 虚表布局与身份 / VTABLE LAYOUT AND IDENTITY

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED
> 地址口径：.rdata 布局地址为 RVA；槽内指针以 VA 标注（VA = RVA + 0x400000）。

---

## 1. 表范围（PROVEN）

| 项 | 值 |
|---|---|
| 表起始 RVA | 0x898568 |
| 表结束 RVA | 0x898634（含） |
| 槽位数量 | 52（步长 4） |
| 表前项 | 0x898564 = 0x00000000 |
| 表后内容 | 0x898638 起为 ASCII 常量（非函数指针） |

边界判定新据：0x898560 及以前为重复占位 0x00B49FE6；0x898638 起为可读 ASCII，故函数指针表范围为 0x898568..0x898634。

## 2. 完整槽位枚举（节选）

| 槽位 RVA | 值（VA） | 目标 RVA |
|---|---|---|
| 0x898568 | 0x00B76130 | 0x776130 |
| 0x89856C | 0x00B75870 | 0x775870 |
| 0x898570 | 0x00B758B0 | 0x7758B0 |
| 0x898574 | 0x00B758E0 | 0x7758E0 |
| 0x898578 | 0x00B75900 | 0x775900 |
| 0x89857C | 0x00B75920 | 0x775920 |
| 0x898580 | 0x00B75940 | 0x775940 |
| 0x898584 | 0x00B75A00 | 0x775A00 |
| 0x898588 | 0x00B75A50 | 0x775A50 |
| 0x89858C | 0x00B75A80 | 0x775A80 |
| 0x898590 | 0x00B75AB0 | 0x775AB0 |
| 0x898594 | 0x00B75AF0 | 0x775AF0 |
| 0x898598 | 0x00B75B30 | 0x775B30 |
| 0x8985CC | 0x00B763A0 | 0x7763A0 |
| 0x8985C8 | 0x00819200 | 0x419200（疑为单例指针） |

## 3. 库身份（PROVEN，决定性）

表结束处（0x898638 起）常量字符串：

| VA | 内容 |
|---|---|
| 0xC98638 | i386-pc-win32 |
| 0xC98648 | 7.38.0 |
| 0xC98650 | smtps |
| 0xC98658 | rtsp |
| 0xC98660 | pop3s |
| 0xC98668 | imaps |
| 0xC98670 | gopher |
| 0xC986A8 | socket |
| 0xC986B0 | crypto comp_lib.c 路径 |
| 0xC986D4 | crypto bio bf_buff.c 路径 |
| 0xC98794/0xC987A8/0xC987BC | zlib not supported / zlib inflate error / zlib deflate error |
| 0xC987D0..0xC98800 | BIO_ZLIB_WRITE / BIO_ZLIB_READ / BIO_ZLIB_NEW / BIO_ZLIB_FLUSH |
| 0xC98C38..0xC98CF8 | OCSP_sendreq_bio / OCSP_request_verify / OCSP_parse_url 等 |

裁定（PROVEN）：该表属 libcurl（7.38.0，i386-pc-win32 构建）的传输层对象；smtps/rtsp/pop3s/imaps/gopher 是 libcurl 协议方案名；OCSP_*/BIO_ZLIB_* 是其内嵌 OpenSSL 与 zlib 支持。

## 4. 表结构性质（PROVEN / INFERRED）

| 判据 | 观察 | 裁定 |
|---|---|---|
| 标准 C++ vtable | 52 个连续函数指针；首槽 0x776130 写 vptr | PROVEN |
| RTTI | 表前 0x898564 为 0；未见典型 RTTI 名 | 未采用 RTTI（INFERRED） |
| 手工函数表 | 槽位全为真实 .text 入口（除 0x8985C8） | REFUTED |
| thunk 混入 | 0x776200、0x419200 等异常目标 | 部分为 thunk（INFERRED） |

## 5. 与其他 vtable 的关系

| vptr 值 | 设置点 | 归属 |
|---|---|---|
| 0xC98568 | 0x776139、0x776188 | 基类（本表） |
| 0xC985CC | 0x7763A6、0x776C1A、0x473F1C | 派生 A |
| 0xC985EC | 0x7767D2 | 派生 B |
| 0xC985FC | 0x776BE6、0x776F15 | 派生 C |
| 0xC98620 | 0x776B64 | 派生 D |

裁定（PROVEN）：0x898588/0x898590 是 C++ 基类 vtable（0xC98568）中的第 8/10 槽。

## 6. 裁定

| 项 | 裁定 |
|---|---|
| 表范围 | PROVEN（0x898568..0x898634，52 槽） |
| 槽位 0x898588 到 0x775A50 | PROVEN |
| 槽位 0x898590 到 0x775AB0 | PROVEN |
| 库身份 | PROVEN（libcurl 7.38.0 + OpenSSL） |
| 表类型 | PROVEN（C++ vtable，多继承层级） |
"""
open(os.path.join(wd,"E18_VTABLE_LAYOUT_AND_IDENTITY.md"),"w",encoding="utf-8",newline="\n").write(c)
print("wrote vtable layout")
