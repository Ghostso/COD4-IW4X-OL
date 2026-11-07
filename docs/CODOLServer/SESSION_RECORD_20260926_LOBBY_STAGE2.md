# SESSION RECORD 2026-09-26: Lobby Handshake Stage 2

Scope: what was actually proven this session about the CODOL lobby
handshake, what was disproven, and where the work stopped. All findings are
either measured at runtime or read from the runtime-decrypted image
(`_mainline/_dyn100_run_20260925_182324/live/image_best.bin`, base 0x400000).

---

## 1. Confirmed working (do not re-litigate)

### 1.1 The client trusts our CA now

The client's `cacert.pem` had been appended with a CA whose SHA-256 did NOT
match the CA that signed `lobby_server.pem`. Both CAs shared the same CN/O,
so the mismatch was invisible by name.

    signing CA : O=CODOL-LOCAL,CN=CODOL Local Lobby CA  501dcebb...33926c
    file's CA  : O=CODOL-LOCAL,CN=CODOL Local Lobby CA  1582d9c6...00e1df

Replacing the appended block with the current `ca_append.pem` made
`POST /auth/` reach the probe for the first time. Before the fix the client
never sent it and only did the `GET /` cert-probe fallback
(`0xDE09E4` = "https://%s/", `0xDE09F0` = "SF_UI_DW_LIVE_CERT_FAILED").

Backup made: `cacert.pem.bak_before_ca_refresh_20260926_171549`.

### 1.2 Stage-1 auth completes

Measured at 20 ms resolution:

    t=20.12  http_state=5  http_status=200
    t=20.14  uA50=3   sub_state=9   obj_code=700 (0x2BC)
             nm=DW_ACCOUNT_LOGIN_COMPLETE

This requires the probe to answer `auth_task` with the TABLE-DRIVEN answer
from `0xB99C0` (stage 10 -> 11). A runtime override that forced 10 -> 1 was
removed; it contradicted `mklobby_response.py` and caused 0x2DE.

### 1.3 TCLS config block is required and now proven effective

`0x7F2E7F` gates the whole lobby stage on `[0x331C5C0]`:

    007F2E7F  cmp [0x331C5C0], ebx
    007F2E85  je  0x7F2EEA          ; zero -> skip objC creation entirely
    ...
    007F2EAE  call 0x801A00         ; creates objC (ticket object)

`cfg_applied` was 0 in every run (degraded path, objA=0, objB used).
Publishing `TCLS_SHAREDMEMEMORY<pid>` from `_subagents/_tenproxy_shm.bin`
(0x80000 bytes, slot capacity 0x40, channel ptr at +0x50, tag8 text
"127.0.0.1;443;1004;0;0") makes it flip to 1, objA becomes non-zero, and
the client stops using the degraded path.

The older `suspend_host_redirect.create_tcls_handoff` built a 0x7AC-byte
block with no slot table. TenProxy reads `[base+0x50]` and gets zero, so
`ApplySettings` fails. Use the 0x80000 image, not the 0x7AC one.

### 1.4 Stage-2 request shape (first observed)

With cfg_applied=1 the client sends a second `POST /auth/` with
`auth_task` **32**. Probe answers 33.

The request body carries an encrypted blob:

    {"auth_task":"32","iv_seed":"<n>","title_id":"0","identity":"356c4bc3",
     "extra_data":"{\"codo_request_size_bits\":1366,
                    \"codo_request\":\"DSAAAA...\"}"}

`codo_request` is unpadded base64, decodes to 188 bytes.

---

## 2. Disproven this session (do not repeat)

| Hypothesis | Evidence against |
|---|---|
| Tickets must be <=45 bytes (base64<=64) | The 0x7F2A00 check is on `simplePassword` (string key 0xDE09A8), not tickets |
| `32 -> 33` is wrong and only 10->11 matters | Runtime really sends 32 on the objA path; both are real, different stages |
| Graceful TLS close was the blocker | http_status was already 200 before the change; 0x2E5 came from the pre-CA run |
| portproxy corrupts TLS | Direct bind on 127.0.0.3:443 reproduced the identical TLS failure |
| `objA+0xD8` holds the ticket tag | Measured 0 for the whole run, and unaffected by ticket content |
| `objA+0x30` holds client_ticket | Controlled experiment: changed server_ticket prefix 11223344; objA_30 became 0x44332211. It is **server_ticket** |
| The two tickets are interchangeable | They land in different fields; both are separately decoded |

---

## 3. Stage-2 blocker as currently understood

After answering stage 32, the client reports `obj_code=735 (0x2DF)` and
`DW_ACCOUNT_ERROR`, then destroys objA.

735 has two producers in `0xB9A470`:

    00B9A59B  mov [ebp-0x298], 0x2DF   ; auth_task validator rejected
    00B9A7CC  mov [ebp-0x298], 0x2DF   ; ticket/tag path rejected

The second is reached when the extracted ticket tag at `[objA+0x2AC]` does
not equal `[0xD59F08]` (= 0xEFBDADDE). Sampling shows `objA+0x2AC` never
holds the marker, and it does not track ticket content, so it is not a plain
ticket field.

---

## 4. Two hardcoded XOR ciphers (both fully disassembled)

Both are byte-wise XOR keyed by a 24-byte table indexed by a 24-entry
permutation. `byte [ebp+0xc]` selects encrypt vs decrypt; the transform is
symmetric.

`0xBA9600`  (writes at eax+0x69)      `0xBA97C0`  (writes at eax+0x89)
key:
    ea3f8834 dced9930 7603ffca 21c33b34 43618909 d31858fd
    cdea3856 488743fe 2136aa09 c9d28e75 f48042f0 3f5d01b1
perm:
    [12,14,18,3,11,20, 2,6,15,10,17,23, 1,7,13,19,16,0, 5,22,21,4,8,0]
    [13,3,0,17,18,11, 2,14,10,5,15,7, 21,19,8,22,9,4, 1,12,16,6,20,23]

Resulting keystreams:
    0xBA9600: 34 c3 61 ea 76 fd 3f ed 21 03 89 d3 88 dc 3b 43 09 34 99 18 58 30 ca 34
    0xBA97C0: 8e cd 56 42 80 21 ea d2 36 43 c9 48 01 f4 09 5d aa fe 38 75 f0 87 b1 3f

Callers of the thunk `0xBA97B0`: `0xB988D3`, `0xB9A821` (inside 0xB9A470,
right after the `0xBA9980` ticket reader), `0xBA9B14`.

STATUS: XORing the captured codo_request with either keystream does not
yield readable structure. Whether these ciphers apply to codo_request at
all is NOT established. Do not assume it.

---

## 5. Open / unknown

1. What fills `[objA+0x2AC]` and why it never becomes 0xEFBDADDE.
2. Whether `codo_request` is covered by 0xBA9600/0xBA97C0 or by something else.
3. Meaning of `objA+0xD8` (constantly 0) and of `0xB9A809`.
4. Real origin of JumpSignature / GameSignature / LoginKey (previous reports
   concluded these come from an online TCLS response and are not present in
   any local static file).
5. Whether stage 2 can be satisfied without those online credentials.

---

## 6. Working harness (current state)

    probe   : CODOLServer/lobby_server/lobby_probe_server.py  (graceful
              TLS close_notify added; TASK_ANSWER includes 32->33)
    socket  : CODOLServer/lobby_server/lobby_socket_server.py
    template: CODOLServer/lobby_server/lobby_response.json (generated)
    watcher : CODOLServer/_mainline/_lobby_watch.py
              --tenproxy-shm publishes TCLS_SHAREDMEMEMORY<pid> before resume
    agent   : CODOLServer/_mainline/elevated_agent.py + agent_client.py

TEMPORARY EXPERIMENT STILL IN PLACE: `mklobby_response.py` has
`SERVER_TICKET_PREFIX = b"\x11\x22\x33\x44"`. Revert to `NULL_REF_BYTES`
before any real run.

Ports: probe 127.0.0.1:8443, socket 127.0.0.2:8444, portproxy 443->8443/8444.
dwauth.ini must point at 127.0.0.1:443.
