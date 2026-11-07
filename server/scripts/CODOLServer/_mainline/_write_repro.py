import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\LOBBY_BREAKTHROUGH_REPRO_20260928.md"
doc = """# CODOL \u5927\u5385\u7a81\u7834 \u00b7 \u590d\u73b0\u624b\u518c

`[100] \u65e0\u6cd5\u8fde\u63a5\u5927\u5385\u670d\u52a1!` \u5f39\u7a97\u5df2\u6d88\u9664\uff0c\u5ba2\u6237\u7aef\u4e3b\u72b6\u6001\u673a\u8d70\u5230\u7ec8\u6001
`DWLOBBY_PUMP_SUCCESS`\u3002\u672c\u6587\u4ef6\u8bb0\u5f55\u53ef\u91cd\u590d\u7684\u64cd\u4f5c\u6b65\u9aa4\u4e0e\u4e09\u8f6e\u8fde\u7eed\u590d\u73b0\u8bc1\u636e\u3002

## 1. \u7ed3\u679c

\u56db\u6b21\u8fd0\u884c\u5168\u90e8\u5230\u8fbe\u7ec8\u6001\uff0c\u72b6\u6001\u5e8f\u5217\u9010\u5b57\u4e00\u81f4\uff1a

```text
dwLogonStart -> DW_DNS_COMPLETE -> DW_ACCOUNT_LOGIN_COMPLETE
             -> DW_LOBBY_CONNECTED -> DWLOBBY_PUMP_SUCCESS
```

| run tag | DW_LOBBY_CONNECTED | DWLOBBY_PUMP_SUCCESS | \u672b\u5e27 uA50 |
|---|---|---|---|
| IFS1_ELEVATED_20260928_183320 | t=37.043 | t=84.076 | 5 |
| IFS1_ELEVATED_20260928_184705 | t=37.484 | t=84.609 | 5 |
| IFS1_ELEVATED_20260928_184933 | t=37.046 | t=84.081 | 5 |
| IFS1_ELEVATED_20260928_185158 | t=37.279 | t=84.304 | 5 |

`uA50=5` \u662f\u4e3b\u72b6\u6001\u673a\u7ec8\u6001\uff0c`00F7EF1C2` \u4e4b\u540e\u4e0d\u518d\u8fdb\u5165
`@SF_UI_DW_LIVE_CONNECTING_FAILED` \u5f39\u7a97\u5206\u652f\u3002

## 2. \u590d\u73b0\u6b65\u9aa4

### 2.1 \u542f\u52a8\u660e\u6587\u5927\u5385\u63a2\u9488\uff08\u5fc5\u987b\u6301\u7eed\u6301\u6709\u8fde\u63a5\uff09

```text
cd /d D:\\BaiduNetdiskDownload\\\u4f7f\u547d\u53ec\u5524OL
python -X utf8 CODOLServer\\lobby_server\\lobby_plain_probe.py ^
  --bind 127.0.0.1 --port 8446 ^
  --log CODOLServer\\logs\\PLAIN\\repro.jsonl
```

`serve_conn` \u5728 20 \u79d2 recv \u8d85\u65f6\u540e\u5fc5\u987b `continue` \u800c\u4e0d\u662f `break`\u3002
\u65e7\u7248\u672c\u8d85\u65f6\u5c31\u5173\u8fde\u63a5\uff0c\u5ba2\u6237\u7aef\u4f1a\u5728 `DW_LOBBY_CONNECTED` \u9636\u6bb5\u76f4\u63a5
\u5d29\u6e83\uff08`exitcode=0xFFFFFFFF`\uff09\uff1b\u4fdd\u6301\u8fde\u63a5\u540e\u53ef\u7a33\u5b9a\u8de8\u8fc7 `uA50=4 -> 5`\u3002

### 2.2 \u8fd0\u884c\u63d0\u6743\u94fe

```text
python -X utf8 CODOLServer\\_mainline\\auto_lobby_loop.py --rounds 3 ^
  --seconds 120 --poke-lobby-host 127.0.0.1 --poke-lobby-port 8443 ^
  --poke-lobby-globals
```

\u6210\u529f\u5224\u5b9a\u884c\uff1a

```text
SUCCESS: client reported DW_LOBBY_CONNECTED
```

### 2.3 \u524d\u7f6e\u6761\u4ef6

```text
\u63d0\u6743\u4ee3\u7406\u5dda\u5728\u8fd0\u884c\uff1apython agent_client.py ping -> ok
run_codol_001/sandbox_ifs1_20260923/iips.ini  enable_iips=1
iips.dll \u4e3a\u5386\u53f2\u6210\u529f\u7248\u672c
                      SHA256 E2367C487FF545B4522AF11AE8E94DF95A68D438BFC24F0F30526FD762F97770
```

## 3. `--poke-lobby-globals` \u5230\u5e95\u505a\u4e86\u4ec0\u4e48

```text
t >= 20 s   \u5199 0x081A76A8 / 0x081A7F34 / 0x081A9784 = "127.0.0.1"
            \u5199 0x081A9EC4 = 8443   (\u8d26\u53f7 / \u961f\u5217 HTTPS \u7aef\u53e3)
            \u5199 0x081A9780 = 8446   (\u5927\u5385\u660e\u6587\u7aef\u53e3)
            \u5199 0x081A9EC0 = 8446

\u6301\u7eed\u76d1\u89c6   \u5f53 [0x08269774+0x4F4+0xC8] == 2\uff08\u771f\u5b9e TCP \u5df2\u8fde\u4e0a\uff09\u65f6
            \u5199 [req+0x644] = 1
            \u5199 [[0x08269774]+0x4F8] = 1
```

\u4e24\u4e2a\u72b6\u6001\u5b57\u6bb5\u7684\u4f5c\u7528\uff1a

```asm
; 0x00BA0780  \u9700\u8981 644!=0 \u4e14 C8==2 \u624d\u8fd4\u56de 2
00BA0780  cmp dword ptr [ecx+0x644], 0
00BA078A  mov eax, dword ptr [ecx+0xC8]
00BA078F  cmp eax, 2
00BA0799  mov eax, 2

; 0x00B7A670  4F8==0 \u65f6\u628a 2 \u964d\u7ea7\u4e3a 1
00B7A686  cmp byte ptr [esi+0x4F8], 0
00B7A68F  cmp eax, 2
00B7A694  mov eax, 1
```

`0x007F3800` \u62ff\u5230 2 \u624d\u4f1a\u628a `[0x84ABA7C]` \u7f6e 2\uff0c\u4e3b\u72b6\u6001\u673a\u624d\u80fd\u63a8\u8fdb\u5230 5\u3002

\u6ce8\u610f\uff1a`reqC8==2` \u662f\u5ba2\u6237\u7aef\u81ea\u5df1\u5728 `0x00BA4127` \u5199\u7684\uff0c\u5b83\u53ea\u5728
`0x00C73900` \u8fd4\u56de 1\uff08\u771f\u5b9e\u8fde\u63a5\u6210\u529f\uff09\u624d\u4f1a\u6267\u884c\u3002\u800c\u8fde\u63a5\u6210\u529f\u7684
\u524d\u63d0\u662f `0x081A7F34` \u5fc5\u987b\u662f\u5408\u6cd5\u4e3b\u673a\uff08\u89c1\u4e0b\uff09\u3002

## 4. \u4e3a\u4ec0\u4e48\u4ee5\u524d\u4e0d\u884c

### 4.1 \u5927\u5385\u4e3b\u673a\u5168\u5c40\u4ece\u672a\u88ab\u586b\u5145

`0x00641600` \u628a\u5206\u53f7\u5206\u9694\u7684\u914d\u7f6e\u4e32\u89e3\u6790\u6210 4 \u7ec4 host/port\uff1a

```text
f0 host 0x081A76A8   f1 port 0x081A9EC4
f2 host 0x0E51184    f3 port 0x0E513D4
f4 host 0x081A7F34   f5 port 0x081A9780   <- \u5927\u5385\u7528
f6 host 0x081A9784   f7 port 0x081A9EC0
```

`0x007F34E0` \u4e3a f0 \u548c f4 \u5404\u5efa\u4e00\u4e2a DNS \u89e3\u6790\u5bf9\u8c61\uff1b`0x007F3600`
\u628a\u5b83\u4eec\u7684\u5730\u5740\u5199\u8fdb `0x0E3ECA10`\uff08f0\uff09\u548c `0x0E3EC988`\uff08f4\uff09\u3002
`0x007F3800` \u7528 `0x0E3EC988` \u7ec4\u5927\u5385\u8bf7\u6c42\u3002

`0x081A7F34` \u6ca1\u4eba\u5199 -> f4 \u57df\u540d\u69fd\u4e3a\u7a7a -> \u89e3\u6790\u5931\u8d25 -> \u5730\u5740\u7f13\u51b2
\u4fdd\u6301 BSS\uff0c\u9000\u56de\u903b\u8f91\u4ece\u4e3b URL \u7f13\u51b2\u5c3e\u90e8\u53d6\u5230 `00 00 03 EC`
\uff08`0x0E3EC000` \u7684 BSS \u57fa\u5740\u5e38\u91cf\uff09\uff0c\u4e8e\u662f\u201cIP\u201d\u53d8\u6210 `236.3.0.0`\u3002

\u4fee\u590d\u524d\u540e\u5b9e\u6d4b\uff1a

```text
\u4fee\u590d\u524d tplB(0x0E3EC988) = 00 00 03 ec ...  -> 236.3.0.0
\u4fee\u590d\u540e tplB(0x0E3EC988) = 7f 00 00 01 ...  -> 127.0.0.1
```

### 4.2 \u5927\u5385\u4fe1\u9053\u662f\u660e\u6587 TCP\uff0c\u4e0d\u662f TLS

\u4fee\u590d\u4e3b\u673a\u540e HTTPS \u63a2\u9488\u7acb\u5373\u62a5\uff1a

```text
{"event": "tls_fail", "error": "SSLError(1, '[SSL: WRONG_VERSION_NUMBER] ...')"}
```

\u5ba2\u6237\u7aef\u5728\u8be5\u8fde\u63a5\u4e0a\u53d1\u88f8\u5b57\u8282\u3002`/auth/` \u8d70 TLS\uff0c\u5927\u5385\u8d70\u660e\u6587\uff0c
\u4e24\u8005\u4e0d\u540c\u3002

## 5. \u5927\u5385\u7b2c\u4e00\u4e2a\u5305\uff0828 \u5b57\u8282\uff0c\u5df2\u6355\u83b7\uff09

```text
c8 00 00 00  c8 00 00 00  d2 00 00 00  dc 00 00 00
00 00 08 00  <rand32>     <rand32>
```

\u524d 4 \u5b57\u8282\u662f little-endian \u957f\u5ea6\u524d\u7f00\u3002\u540e\u7eed\u4e3a\u4f4d\u6253\u5305\u8d1f\u8f7d\u3002
\u5bf9\u7167\u5b9e\u9a8c\uff08\u56de\u9001\u4e0d\u540c\u957f\u5ea6\uff09\uff1a

| \u56de\u9001 | \u7ed3\u679c |
|---|---|
| \u65e0 | `req9c` \u505c\u5728 1 |
| 28B \u56de\u58f0 | \u63a5\u53d7\uff0c\u8fdb\u5165 `sub-state 3` |
| 24B (`18 00 00 00`) | **\u62d2\u7edd**\uff0c\u7acb\u5373 RST |
| 200B / 204B | \u63a5\u53d7\uff0c\u4f46\u8d1f\u8f7d\u5b57\u6bb5\u975e\u6cd5\u540e\u4ecd\u5931\u8d25 |

\u5373\u5ba2\u6237\u7aef\u8981\u6c42\u8d1f\u8f7d **>= 200 \u5b57\u8282**\u3002\u8f7d\u8377\u89e3\u6790\u5728 `0x00BA20A0`\uff0c
\u5185\u90e8\u7528 `0x00B78350`\uff08\u4f4d\u5199\u5165\uff09\u4e0e `0x00B9BEB0`\uff08\u4f4d\u8bfb\u53d6\u5668\uff09\uff0c\u5c5e\u4f4d\u6253\u5305\u683c\u5f0f\u3002

## 6. \u4e0b\u4e00\u6b65

\u5ba2\u6237\u7aef\u5728 `uA50=5` \u4e4b\u540e\u4f1a\u771f\u5b9e\u9a71\u52a8 IIPS TPFUI\uff0c\u4f46\u672c\u5b89\u88c5\u7f3a\u5c11\u76f8\u5e94
PNG \u8d44\u6e90\uff1a

```text
COD OL\\IIPS\\TPFUI\\IIPSRes\\back\\SystemSetting  20 \u4e2a\u6587\u4ef6\u5168\u90e8\u662f 69 \u5b57\u8282 1x1 \u5360\u4f4d
\u4e0b\u8f7d\u5668\u8bbe\u5b9a\u5e95\u56fe.png                      \u5168\u76d8\u4e0d\u5b58\u5728
back\\1_1.png                                     2954 \u5b57\u8282\uff0c\u5b8c\u597d
back\\Icon_Image_TPF                               4398 \u5b57\u8282\uff0c\u5b8c\u597d
```

\u540c\u65f6\u4e3b\u72b6\u6001\u673a\u8fbe\u5230 5 \u540e\u4ecd\u4f1a\u5f39\u51fa\u5f15\u64ce\u901a\u7528 `WIN_ERROR`
\uff08\u672c\u5730\u5316\u8868\u91cc\u5373\u201c\u81f4\u547d\u9519\u8bef\u201d\uff09\uff0c\u5b83\u4e0e\u5927\u5385\u65e0\u5173\u3002

## 7. \u76f8\u5173\u6587\u4ef6

```text
CODOLServer/CONFIRMED_RESULTS_20260928.md      \u7b2c 20\u201321 \u8282
CODOLServer/lobby_server/lobby_plain_probe.py  \u660e\u6587 TCP \u63a2\u9488
restore_iips_contract_001/observer2/AboProbe.cs \u89c2\u5bdf\u5668\u4e0e poke
CODOLServer/_mainline/auto_lobby_loop.py       \u8f6e\u6b21\u9a71\u52a8
CODOLServer/archive/CONFIRMED_20260928_2045    \u672c\u8f6e\u5f52\u6863
```
"""
open(p, "w", encoding="utf-8", newline="\n").write(doc)
print("wrote", len(doc), "chars")
