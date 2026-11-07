# CODOL Capture Reproduction Report

This report summarizes existing AFD ETW JSONL captures. The captures contain metadata only; payload is null and no gameplay endpoint is confirmed.

## Capture Matrix

| File | Events | PIDs | Payload availability |
| --- | ---: | --- | --- |
| `D:\BaiduNetdiskDownload\使命召唤OL\工具\EX035_DIR\Logs\game2.jsonl` | 1227 | 12192, 13012, 14188, 16088, 1960, 2228, 2856, 6928 | 0 non-null records |
| `D:\BaiduNetdiskDownload\使命召唤OL\工具\EX035_DIR\Logs\game3.jsonl` | 1395 | 13596 | 0 non-null records |
| `D:\BaiduNetdiskDownload\使命召唤OL\工具\EX035_DIR\Logs\t4.jsonl` | 191 | 1960, 21352, 21404, 2228, 2856, 6928 | 0 non-null records |

## Observed Endpoints

| Endpoint | Records | Classification |
| --- | ---: | --- |
| `122.96.96.225:8081` | 114 | QOS/telemetry candidate; not gameplay-confirmed |
| `192.168.5.22:51815` | 28 | unknown external endpoint |
| `fe80::54ba:60e8:5930:d84c%21:39798` | 28 | unknown external endpoint |
| `182.50.14.56:8081` | 13 | QOS/telemetry candidate; not gameplay-confirmed |
| `239.255.255.250:1900` | 12 | unknown external endpoint |
| `192.168.5.22:43736` | 8 | unknown external endpoint |
| `fe80::54ba:60e8:5930:d84c%21:57521` | 8 | unknown external endpoint |
| `218.69.49.90:443` | 4 | HTTP(S)/bootstrap candidate; not gameplay-confirmed |
| `61.182.140.173:80` | 3 | HTTP(S)/bootstrap candidate; not gameplay-confirmed |
| `127.0.0.1:34568` | 3 | localhost/CEF-or-test |
| `127.0.0.1:63954` | 2 | localhost/CEF-or-test |
| `127.0.0.1:63956` | 2 | localhost/CEF-or-test |
| `127.0.0.1:63959` | 2 | localhost/CEF-or-test |
| `127.0.0.1:63961` | 2 | localhost/CEF-or-test |
| `127.0.0.1:63965` | 2 | localhost/CEF-or-test |
| `127.0.0.1:63967` | 2 | localhost/CEF-or-test |
| `127.0.0.1:63971` | 2 | localhost/CEF-or-test |
| `127.0.0.1:63973` | 2 | localhost/CEF-or-test |
| `127.0.0.1:34567` | 2 | localhost/CEF-or-test |
| `0.0.0.0:63914` | 1 | unknown external endpoint |
| `0.0.0.0:63915` | 1 | unknown external endpoint |
| `0.0.0.0:63916` | 1 | unknown external endpoint |
| `0.0.0.0:63917` | 1 | unknown external endpoint |
| `0.0.0.0:63918` | 1 | unknown external endpoint |
| `192.168.5.11:54962` | 1 | unknown external endpoint |
| `192.168.237.1:54963` | 1 | unknown external endpoint |
| `192.168.85.1:54964` | 1 | unknown external endpoint |
| `157.240.8.36:443` | 1 | HTTP(S)/bootstrap candidate; not gameplay-confirmed |
| `0.0.0.0:63919` | 1 | unknown external endpoint |
| `0.0.0.0:63920` | 1 | unknown external endpoint |
| `0.0.0.0:63921` | 1 | unknown external endpoint |
| `127.0.0.1:10090` | 1 | localhost/CEF-or-test |
| `0.0.0.0:63922` | 1 | unknown external endpoint |
| `0.0.0.0:63923` | 1 | unknown external endpoint |
| `0.0.0.0:63924` | 1 | unknown external endpoint |
| `0.0.0.0:63925` | 1 | unknown external endpoint |
| `0.0.0.0:63926` | 1 | unknown external endpoint |
| `0.0.0.0:63927` | 1 | unknown external endpoint |
| `0.0.0.0:63928` | 1 | unknown external endpoint |
| `0.0.0.0:63929` | 1 | unknown external endpoint |
| `:::51462` | 1 | unknown external endpoint |
| `0.0.0.0:63930` | 1 | unknown external endpoint |
| `0.0.0.0:51410` | 1 | unknown external endpoint |
| `0.0.0.0:63949` | 1 | unknown external endpoint |
| `0.0.0.0:63950` | 1 | unknown external endpoint |
| `0.0.0.0:63953` | 1 | unknown external endpoint |
| `0.0.0.0:63955` | 1 | unknown external endpoint |
| `127.0.0.1:63955` | 1 | localhost/CEF-or-test |
| `0.0.0.0:63957` | 1 | unknown external endpoint |
| `127.0.0.1:63957` | 1 | localhost/CEF-or-test |
| `0.0.0.0:63958` | 1 | unknown external endpoint |
| `0.0.0.0:63960` | 1 | unknown external endpoint |
| `127.0.0.1:63960` | 1 | localhost/CEF-or-test |
| `0.0.0.0:63962` | 1 | unknown external endpoint |
| `127.0.0.1:63962` | 1 | localhost/CEF-or-test |
| `0.0.0.0:63963` | 1 | unknown external endpoint |
| `0.0.0.0:63966` | 1 | unknown external endpoint |
| `127.0.0.1:63966` | 1 | localhost/CEF-or-test |
| `0.0.0.0:63968` | 1 | unknown external endpoint |
| `127.0.0.1:63968` | 1 | localhost/CEF-or-test |
| `0.0.0.0:63969` | 1 | unknown external endpoint |
| `0.0.0.0:63972` | 1 | unknown external endpoint |
| `127.0.0.1:63972` | 1 | localhost/CEF-or-test |
| `0.0.0.0:63974` | 1 | unknown external endpoint |
| `127.0.0.1:63974` | 1 | localhost/CEF-or-test |
| `0.0.0.0:63975` | 1 | unknown external endpoint |
| `0.0.0.0:63976` | 1 | unknown external endpoint |
| `61.182.140.173:443` | 1 | HTTP(S)/bootstrap candidate; not gameplay-confirmed |
| `0.0.0.0:63977` | 1 | unknown external endpoint |
| `0.0.0.0:63980` | 1 | unknown external endpoint |
| `0.0.0.0:63981` | 1 | unknown external endpoint |
| `0.0.0.0:63982` | 1 | unknown external endpoint |
| `0.0.0.0:63983` | 1 | unknown external endpoint |
| `0.0.0.0:50820` | 1 | unknown external endpoint |
| `0.0.0.0:50821` | 1 | unknown external endpoint |
| `0.0.0.0:63898` | 1 | unknown external endpoint |
| `0.0.0.0:63899` | 1 | unknown external endpoint |
| `0.0.0.0:63900` | 1 | unknown external endpoint |
| `127.0.0.1:63900` | 1 | localhost/CEF-or-test |
| `0.0.0.0:63901` | 1 | unknown external endpoint |
| `:::54961` | 1 | unknown external endpoint |
| `127.0.0.1:9` | 1 | localhost/CEF-or-test |
| `0.0.0.0:63902` | 1 | unknown external endpoint |
| `0.0.0.0:63903` | 1 | unknown external endpoint |
| `0.0.0.0:63904` | 1 | unknown external endpoint |

## API Counts

| API | Count |
| --- | ---: |
| `recv` | 1705 |
| `send` | 409 |
| `closesocket` | 230 |
| `sendto` | 140 |
| `socket` | 119 |
| `recvfrom` | 73 |
| `bind` | 63 |
| `setsockopt` | 21 |
| `connect` | 20 |
| `disconnect` | 15 |
| `listen` | 9 |
| `accept` | 9 |

## Length Fingerprints

| API | Length | Count |
| --- | ---: | ---: |
| `send` | 2 | 112 |
| `sendto` | 308 | 93 |
| `send` | 18 | 86 |
| `send` | 7 | 22 |
| `send` | 9 | 18 |
| `sendto` | 170 | 12 |
| `send` | 24 | 10 |
| `send` | 31 | 10 |
| `sendto` | 196 | 9 |
| `send` | 239 | 8 |
| `send` | 16 | 8 |
| `send` | 10 | 8 |
| `send` | 1 | 8 |
| `send` | 517 | 8 |
| `send` | 19 | 6 |
| `send` | 134 | 6 |
| `sendto` | 228 | 5 |
| `send` | 6000 | 4 |
| `send` | 6505 | 4 |
| `send` | 92 | 4 |
| `send` | 225 | 4 |
| `send` | 9738 | 4 |
| `send` | 80 | 4 |
| `send` | 318 | 4 |
| `sendto` | 436 | 4 |
| `send` | 32812 | 3 |
| `send` | 131248 | 3 |
| `send` | 149 | 3 |
| `sendto` | 356 | 3 |
| `send` | 132 | 3 |
| `send` | 129 | 3 |
| `send` | 103 | 2 |
| `sendto` | 340 | 2 |
| `send` | 1451 | 2 |
| `send` | 300 | 2 |
| `send` | 64 | 2 |
| `send` | 1766 | 2 |
| `send` | 21 | 2 |
| `send` | 17 | 2 |
| `send` | 5 | 2 |
| `send` | 12 | 2 |
| `send` | 4 | 2 |
| `send` | 29 | 2 |
| `send` | 832 | 2 |
| `send` | 20 | 2 |
| `send` | 255 | 2 |
| `send` | 286 | 2 |
| `send` | 104 | 2 |
| `sendto` | 132 | 2 |
| `sendto` | 244 | 2 |
| `sendto` | 372 | 2 |
| `sendto` | 260 | 2 |
| `send` | 326 | 2 |
| `send` | 170 | 2 |
| `send` | 37 | 2 |
| `send` | 146 | 2 |
| `send` | 178 | 2 |
| `send` | 162 | 2 |
| `send` | 191 | 2 |
| `send` | 312 | 2 |
| `send` | 218 | 2 |
| `send` | 379 | 2 |
| `send` | 54 | 1 |
| `send` | 486 | 1 |
| `send` | 2051 | 1 |
| `send` | 846 | 1 |
| `sendto` | 324 | 1 |
| `sendto` | 164 | 1 |
| `sendto` | 452 | 1 |
| `sendto` | 8 | 1 |

## Verdict

- UDP `:8081` traffic is a QOS/telemetry candidate, supported by the `tqos.gamesafe.qq.com` DNS evidence and one-way `sendto` pattern. It is not a recovered game-server protocol.
- TCP `:80`/`:443` traffic is HTTP(S)/bootstrap traffic in the captured startup window. It is not a recovered gameplay protocol.
- The captures contain no payload bytes and no call stacks, so no opcode, framing, authentication exchange, game-server address, or response rule can be implemented from them honestly.
- Static RTTI names such as `MatchMaking_FIND_SERVERS_Query` and `dwRoomMessage*` prove compiled protocol-shaped types exist, but not that they were instantiated or sent in these runs.
