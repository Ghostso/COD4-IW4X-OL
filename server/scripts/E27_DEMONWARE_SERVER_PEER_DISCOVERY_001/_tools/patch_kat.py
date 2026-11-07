from pathlib import Path
base=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001")
p=base/"E27_CLIENT_SERVER_PEER_CROSSWALK.md"; t=p.read_text(encoding="utf-8")
add="""

## 7. KAT 向量的证据等级（重要限定）

`DemonwareTests.cpp:2466-2477` 与 `codol_crypto.py` 自测使用**同一组** KAT：

```text
sessionKey  = "Shippo fuute, mofu-mofu!" (24B)
transcript  = 0x00..0x3F (64B)
response_id = ea09fd53518d4361     (challenge[8:16])
request_hmac= 96548bb09f4bd93996465628b618c9d3ec09ddd5
response_hmac=4395bd6340aa21bc95d9b77db1c04afc67061382
decrypt     = 71120733ba54e6ff13ded72c69deca7f
encrypt     = b1adf0f2663cde670df4f20fbe37fc2e
```

**限定**：该 KAT 的两份实现（C++ 与 Python）**同源于 `ol-mod` 项目**，因此它证明的是**两套实现彼此一致 + 派生公式内部自洽**（`INFERRED（强）`），**不是**对原版 Demonware 服务端的独立测量。要提升为 `PROVEN`（客户端↔服务端独立交叉验证），需把该派生在 **2697 客户端**内定位并比特级比对（见 E27-NEXT-GATE 第 2 步）。
"""
t=t.rstrip()+add
p.write_text(t,encoding="utf-8")
print("appended KAT caveat")
