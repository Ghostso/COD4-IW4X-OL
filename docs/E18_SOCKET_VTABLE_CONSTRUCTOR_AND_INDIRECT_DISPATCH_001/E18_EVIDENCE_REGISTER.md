# E18 — 证据登记 / EVIDENCE REGISTER

> 新增证据 ID（E-18 系列）。全部来自本轮自建脚本与恢复镜像原始字节。

| EV ID | 类型 | 定位 | 内容 | 原始输出 | 等级 |
|---|---|---|---|---|---|
| EV-18-01 | VTABLE | .rdata 0x898568..0x898634 | 52 槽连续函数指针表；0x898588=VA 0xB75A50、0x898590=VA 0xB75AB0 | out_t01_vtable | PROVEN |
| EV-18-02 | LIBID | 0xC98638/0xC98648/0xC98650..70 | 表后字符串 i386-pc-win32 / 7.38.0 / smtps / rtsp / pop3s / imaps / gopher | out_t04_ident | PROVEN |
| EV-18-03 | LIBID | 0xC986B0/0xC987D0/0xC98C68 | 反斜杠 crypto 路径 / BIO_ZLIB_* / OCSP_sendreq_bio 等 OpenSSL 串 | out_t04_ident | PROVEN |
| EV-18-04 | CTOR | 0x776139、0x776188 | 写 vptr=0xC98568；全镜像 dword 扫描仅此 2 处 | out_t02_ctor | PROVEN |
| EV-18-05 | CTOR | 0x776170 | 堆分配 0x24 字节 + 写 vptr；经 [0xD3A588]+0x28 | out_ctors.txt | PROVEN |
| EV-18-06 | DTOR | 0x776130 | test flag,1 后经 [0xD3A588]+0x30 归还；ret 4 | out_ctors.txt | PROVEN |
| EV-18-07 | DERIVED | 0x7763A6/0x7767D2/0x776B64/0x776BE6/0x776C1A/0x776F15/0x473F1C | 5 个 vptr：0xC985CC/EC/FC/0xC98620 | out_ctors.txt | PROVEN |
| EV-18-08 | METHOD | 0x775A50 | thiscall：recv(this[0x14], buf=[ebp+8], len=[ebp+0xC], 0)；ret 8 | out_t04_ident | PROVEN |
| EV-18-09 | METHOD | 0x775AB0 | thiscall：recvfrom(..., &this[4], 16)；写对端地址到对象 | out_t04_ident | PROVEN |
| EV-18-10 | SEMANTICS | VA 0xA84CE0 (RVA 0x684CE0) | 定长 0x84 字节 rep movsd 拷贝 + 写 this+0x84 word | out_t06_fix | PROVEN |
| EV-18-11 | NULL | libcurl 4 根 x 6 层 | 不含 0xA2660/0x3547D0/0x354100/0x350170/0x34FD80/0xA2E50 | out_t07_last | PROVEN（负） |
| EV-18-12 | ADDR | E-17 报告 | E-17 的 0xA84CE0 为 VA；RVA=0x684CE0（口径更正） | out_t06_fix | PROVEN |
| EV-18-13 | HASH | 三样本 | 冻结基线开工/收工各复核一次，均一致 | Get-FileHash | PROVEN |
