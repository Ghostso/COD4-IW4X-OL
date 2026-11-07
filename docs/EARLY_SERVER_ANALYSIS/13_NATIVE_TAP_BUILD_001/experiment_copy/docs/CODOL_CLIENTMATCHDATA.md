# Client match data integration investigation

The current full-reference compile stops at `setClientMatchData` in
`maps/mp/_highlights.gsc:9`. No placeholder binding has been registered.

## Reference mismatch

alpha0022 `gsc/builtin_surface.py:1692` treats argument zero as a numeric client
index and stores the remaining path in a Python dictionary. The actual vendor
calls begin with strings: `highlights`, `players`, `scoreboards`, etc.
`_gamelogic.gsc:2161` selects `mp/clientmatchdata.def`; `_highlights.gsc` limits
its array to 18 according to that definition. The Python dictionary is not a
faithful native schema/wire implementation and must not be copied as one.

## Engine and asset evidence

In C1.exe (SHA-256 d990610732258b1d00dd6fe63d6691f294312a2e0562955a01ce16216115390d),
`0x553599` resolves the selected definition name at `0x27f297c` as asset type
39. `0x5535a5` loads the first definition from set+8; its size at +0x30 must
fit 0x400 bytes. `0x5535cf` passes the diagnostic name `setclientmatchdata`,
definition and buffer descriptor (data `0x27f29bc`, capacity 0x400) to the
typed writer at `0x553340`. This is a shared structured record, not argument-zero
client-index dispatch. The client read path at `0x5dfcd5` resolves the same
asset type and capacity, and dispatches on the resolved field's type tag.

The native stream replay already recognizes type 39 in
`src/codol_load_blocks.c:replay_structured_data`. It consumes 60-byte
definitions, 20-byte struct records, 24-byte properties, 16-byte array types,
and a trailing word map. A runtime native schema model is still required.

`tools/codol_structured_catalog.py` follows that stream order through trusted
alpha0022 zone assets and records raw words without fabricating pointer
resolutions. Its output is [CODOL_CLIENTMATCHDATA_SCHEMA.json](CODOL_CLIENTMATCHDATA_SCHEMA.json).
The asset in `code_post_gfx_mp` is 2654 bytes, consumed exactly: one definition,
version 16, format checksum 0x3fd7bbad, size 858, root type [5,0]. It contains
three enums, three structs, three indexed-array types, one enum-array type,
and 246 trailing map words. Some member names are packed archive references;
their numeric references are preserved and their text remains unresolved.

Indexed arrays declare 19 player records of size 34, 18 highlights of size 7,
and 19 byte elements. Root property indices are 0 (`highlightCount`), 1
(`highlights`), 55 (`players`), 169 (`scoreboardPlayerCount`) and 170
(`scoreboards`). **These are not byte offsets.** The trailing map contains
654, 655, 36, 781 and 820 at those indices respectively. Runtime lookup and
typed access must establish how to apply the map and headers; do not directly
index the data by property number.

The offline decoder rejected 10 truncated/trailing variants in addition to
exactly consuming the shipped asset. No server was launched or live process
modified during this investigation.

## Next implementation

The native schema reader is now implemented in `codol_structured_schema.c`.
It owns decoded definition/enum/struct/array records, borrows archive strings
and maps, and resolves packed names via `CODOL_LoadBlockString`. It validates
stream counts and exact asset extent, and preserves prior output on failure.
It does not yet validate all type-graph relationships or field storage ranges.
Mounted lookup uses native definition precedence; type 39 now registers in the
load-block asset alias index (previously it was replayed but not indexed).

`codol_checkstructured mp/clientmatchdata.def` on the isolated native Bog server
returned status 1, version 16, size 858 and all 14 property names across three
structs. Previously unresolved names now resolve natively: `award`, `value`,
`assists`, `deaths`, `kills`, and `score`. The probe used UDP 17759 and home
`%TEMP%/sh1x-schema-final-20260908-080456`; its server was stopped after checking.
This verifies real mounted schema/name loading, not GSC record access.
The synthetic schema test passed Linux ASan/UBSan, covering ownership, every
truncation, trailing data, unresolved packed names and failure preservation.
The final Windows build passed (`/tmp/sh1x-structured-schema-alias-win32.log`).

Native mapped scalar access is now implemented in `codol_structured_data.c`:
type 0 reads/writes four LE bytes, type 1 reads/writes one byte (rejecting values
above 255), and type 2 addresses one bit while preserving neighboring bits.
The supplied record must cover the schema size; mapped access must remain inside
that size. Unknown types, missing/misaligned map data, invalid property numbers
and out-of-range writes fail without mutating output. This is a storage primitive,
not a complete schema loader, GSC binding, dirty-bit tracker or transport.

Additional static C1 evidence: `0x61f4b0` maps the logical property index through
definition+0x38 and reads int32/byte directly at the resulting buffer byte offset.
There is no added header displacement. `0x61f500` maps booleans to bit positions
(`address >> 3`, mask `1 << (address & 7)`). `0x61f748` rejects unsigned byte
values above 255 before writing. Struct-name traversal at `0x61f130` compares
names case-sensitively and adds the property's logical index (+0xc) to the
lookup state. Indexed-array traversal at `0x61f0a0` rejects negative/out-of-bound
indices and advances by the element struct's logical field count (+0x10), or
one for scalar elements; it does not use its serialized byte stride here.

The focused native test covers nonidentity maps, unaligned integers, byte range,
shared-byte booleans, schema/capacity boundaries and atomic failure. Linux
ASan/UBSan and a Windows executable passed; the Windows server was rebuilt.

`CODOL_ResolveStructuredField` now resolves a complete typed path and verifies
the final scalar storage extent. Named fields and enums are case-sensitive;
indexed arrays reject negative/out-of-range indices. Visited type references,
logical-index overflow, incomplete aggregate paths and invalid scalar widths
are rejected without changing the output. String widths, enum/short widths,
float/int widths and bit-addressed boolean bounds are checked, but this does
not yet implement their value conversion or setters.

`codol_checkstructured <asset> <field> #<index> <field> ...` exercises the native
resolver against mounted definitions. The Windows build and isolated Bog probe
on UDP 17760 passed: `players #18 score` resolved logical 167 / byte 642;
`highlights #17 value` resolved logical 54 / byte 777; `highlightCount` resolved
logical 0 / byte 654. `players #19 score` was rejected. The probe home was
`%TEMP%/sh1x-schema-path-20260908-081452`; its process was stopped afterward.
Linux ASan/UBSan passed the expanded schema test, including typed paths,
nonidentity maps, array element struct counts, bit bounds and atomic failures.
Windows build log: `/tmp/sh1x-schema-path-win32.log`.

An unresolved nested enum-array discrepancy remains. C1's server writer
`0x553340` calls path traversal `0x551760`, which dispatches enum names through
`0x61f270`, the same routine used by the client reader. It adds the low 16 bits
of enum entry+4 directly to the logical index. The native resolver reproduces
that observed arithmetic. The shipped scoreboard enum values 0..3 and nested
19-byte arrays appear inconsistent with separated groups in the logical map.
Runtime schema transformation or other missing context must be investigated
before claiming correct scoreboard writes; no guessed stride multiplication
has been introduced.

A read-only live C1 check on 2026-09-08 located the active asset through the
24-byte DB entry table at 0x1c402c8 (lookup evidence: 0x4cb540). The type-39
set at 0x203b1b4 referenced definition 0x0db266f4, version 16, checksum
0x3fd7bbad, size 858. Its enum 2 remained `allies=2`, `axis=3`, `neutral=1`,
`none=0`. The indexed/enum-array words matched the serialized catalog, as did
map entries 170/171/172/173/188/189/208/227/245. Live bytes at 0x61f270
(92 bytes) and 0x61f0a0 (114 bytes) matched the on-disk instructions. Thus a
load-time schema/index transformation does not explain the discrepancy in this
running client. This was ReadProcessMemory only: no breakpoints, suspension,
hooks or memory writes. It establishes loaded data and code, not execution of
a scoreboard setter or observed end-of-match display.

Native `CODOL_StructuredReadText` / `CODOL_StructuredWriteText` now support
strings and named enums through resolved paths. C1 writer 0x61f860 resolves
enum names with 0x61f1f0 and writes the low word from enum entry+4 as two LE
bytes. Its string branch at 0x61f92c requires length including NUL to fit the
type's string bound, and writes only that prefix, preserving the old suffix.
The native implementation follows those behaviors. Reads require a bounded
terminator or a known enum value; unknown names, insufficient capacity and
overlong strings fail without changing data/output. Dirty-byte tracking and
VM coercion remain separate work.

The expanded schema test passed Linux ASan/UBSan, including exact-fit strings,
shorter overwrite suffix preservation, failed writes, unknown enum values,
case sensitivity and LE enum storage. The Windows server build passed in
`/tmp/sh1x-schema-text-win32.log`. C1 and the Python lobby remained responsive.

Numeric storage now also supports type 8 as four raw float bytes and type 9
as two short bytes. C1 0x61f9e0 writes the supplied float bit pattern bytewise;
0x61fb70 writes the low 16 bits of its integer argument without a range check.
The native scalar API preserves float bits and truncates short writes; short
reads return raw zero-extended bits for later VM interpretation. Byte and bool
range checks are unchanged. Linux ASan/UBSan passed float payload, short
truncation, unaligned access and boundary tests; the Windows build passed
(`/tmp/sh1x-numeric-win32.log`).

Definition-selection evidence for the next GSC integration: C1 0x553d90
requires one argument, compares it with the selected name, and returns without
reinitializing when the name matches. A different name is rejected once a
nonempty name is selected. Names must be shorter than 64 bytes. It resolves
type 39, selects the first definition, requires size <= 0x400, and copies
definition version/checksum into the first eight bytes of the shared record
(0x553ed8 onward). Record reset and lifetime must be established separately;
definition selection itself does not clear the remaining record bytes.

`codol_matchdata.c` now owns the native server's selected schema and 1,024-byte
record. Selection loads the first mounted definition, requires 8..1,024 bytes,
writes its LE version/checksum header, and preserves state on failure. Name
comparison is ASCII-case-insensitive, matching C1 helper 0x6283d0. Selecting
the same name preserves existing values; selecting another name requires reset.
`SV_ClearServer` calls `CODOL_ResetClientMatchData` to release schema arrays
and clear the name and full record. This is the native map/server lifetime
integration; the exact C1 whole-state clear site has not yet been identified.
The record remains internal and is not yet exposed through GSC bindings.

The focused ownership test uses a fixture loader and passed Linux ASan/UBSan:
invalid/missing/oversized definitions, header bytes, no reload or value reset
on repeated selection, rejection of replacement, and complete reset/reselection.
It does not prove live script behavior. Windows build passed in
`/tmp/sh1x-matchdata-win32.log`.

Additional transport evidence: C1 0x5d1f4d writes opcode 4, then calls 0x59f060
with the selected definition name and copies exactly 0x400 record bytes at
0x5d1f84. Surrounding per-client scheduling/acknowledgment and the applicable
message envelope still require investigation before adding native transmission.

Native GSC bindings now expose `setClientMatchDataDef`, `getClientMatchDataDef`,
`setClientMatchData` and `getClientMatchData` in `codol_script_matchdata.c`.
They consume string/integer path components against the selected schema and
operate on the shared native record. They support int, byte, bool, string,
enum, float and short leaves; invalid paths/values raise script errors. Short
reads sign-extend, matching the client read branch at 0x5dfe39. Bool setters
normalize integer truth values. No Python runtime or hook is involved.

The isolated Bog native VM fixture on UDP 17761 printed
`SH1X_MATCHDATA_VM_PASS`: byte count, negative score, low-word short writes
read back as signed values, xuid strings, and case-insensitive repeated
definition selection preserving data. Probe home:
`%TEMP%/sh1x-matchdata-vm-20260908-082557`. Windows build passed in
`/tmp/sh1x-matchdata-gsc-win32.log`. Float/enum storage has focused native
tests but was not covered by this shipped-schema VM fixture. Transmission
and full live-client end-of-match behavior remain unverified.

The full vendor/overlay probe on UDP 17762 advanced beyond the missing
`setClientMatchData` compile failure. Its next fatal error is missing script
`character/mp_character_us_army_lmg`, referenced by
`mptype/mptype_us_army_lmg.gsc:8`. The server shut down its game/network;
the remaining process was stopped. Probe home:
`%TEMP%/sh1x-matchdata-reference-20260908-082623`. C1 and Python remained
responsive. Full vendor-script compilation is still incomplete.

Further server-message tracing located the caller of C1 0x5d1f20 at
0x5d82ab. The enclosing routine immediately writes opcode 5 (EOF) afterward
at 0x5d82bb. Match data is therefore a separate message section preceding
EOF, not the snapshot's sixth entity-like bit section. 0x5d1f20 requires
client state 5, a pending byte at client+0x74013 and at least 1000 ms since
client+0x74014. It updates that timestamp, writes opcode 4, the selected
definition string and exactly 1024 record bytes. Scheduling and acknowledgment
integration still need completion; observing this routine does not prove
the client has received a native-generated record.

`CODOL_WriteClientMatchDataSection` in `codol_matchdata_wire.c` now serializes
that section. It requires a nonempty name shorter than 64 bytes and a full
1024-byte record, checks all capacity before writing, and preserves the
interleaved stream's pending bit pool. Failure sets the message error flag
without changing its size, bit cursor or payload. The enclosing writer remains
responsible for EOF. The helper is not yet called by the live snapshot path.

Linux ASan/UBSan passed exact byte-layout and all insufficient-capacity tests,
including a nonzero prefix bit pool, subsequent bit writes and EOF, full-record
extent and name boundaries. Windows build passed in
`/tmp/sh1x-matchdata-wire-win32.log`. No live process was changed.

Delivery is now connected to native snapshot preparation. `sendClientMatchData`
queues connected game clients when a definition is selected, resetting their
resend timestamp. Active snapshots append the section before EOF when at least
1000 ms have elapsed. The timestamp is committed only when the prepared
message is accepted by transport; rejected/modified messages retain retry
eligibility. This strengthens failure handling compared with C1's timestamp
update during serialization. Client snapshot reset clears its pending delivery;
server clear resets every delivery and the match record.

C1's command table pointer at 0xcd149c binds 0x5d1fb0 to `matchdatadone`
(name at 0xc494d8). That routine clears client+0x74013. The native reliable
client-command dispatcher now handles `matchdatadone` by clearing only the
issuing client's delivery. C1 0x554410 queues game clients whose connection
state is 2; the native GSC entry point uses `CON_CONNECTED`.

The focused match-data test passed ASan/UBSan with timer boundaries, repeat
requests, acknowledgment isolation and reset. The production send test now
includes a match-data section and passed accepted-send timing, rejection,
every-byte mutation recovery, frame rollback and EOF placement. It uses a
fixture schema/transport; real encrypted client receipt and acknowledgment
remain unverified. Windows build passed in `/tmp/sh1x-delivery-win32.log`.

Implement defaults and value access against the verified definition;
own/reset its buffer for the match; then bind set/get/definition-selection and
implement the actual client transport. Verify with real native GSC paths and
client parsing, not just setter/getter dictionary round trips. Completion of
these functions and full vendor-script execution remains unproven.
# Encrypted native delivery verification (2026-09-08)

An isolated Windows server on UDP 17768 loaded the shipped Bog assets and the
`codol_matchdata_vm` overlay. Its native GSC callback requested delivery after
client activation. `tools/codol_transport_probe.py --matchdata-fixture --move
--delta` completed encrypted authentication, synthetic stats upload, reliable
commands, and pure validation, then received opcode 4 before snapshot EOF.
The independent decoder verified the schema name, 1024-byte record, version 16,
checksum 0x3fd7bbad, highlight count 2, player 18 score -12345, and fixture text.
The following delta snapshot also decoded exactly through EOF.

The decoder accepts the optional section after the sixth snapshot section;
it rejects truncation, unterminated/empty names, and trailing sections. The
captured packet was checked at every truncation within its match-data tail,
with trailing data, and with the optional section removed.

The callback waits two seconds in this synthetic fixture so the request happens
after activation; a 0.05-second request produced no delivered section. This does
not establish support for requests made while the client is connecting. The
probe was stopped, and C1 and the Python lobby remained responsive. These checks
prove native-to-synthetic-peer delivery, not C1 consumption, acknowledgement
retry cessation, or completion of a real vendor-script match.

A subsequent isolated UDP 17769 run used `--matchdata-fixture --matchdata-ack
--move` (without `--delta`). The peer first required a second identical record
at least 1000 server milliseconds after the first. It then sent reliable command
3, `matchdatadone`, in netchan packet 5. The native command log confirmed dispatch.
The peer decoded 11 subsequent snapshots acknowledging command 3 over 1500
server milliseconds, all without opcode 4. This proves retransmission before
acknowledgement and cessation while snapshots continue after acknowledgement.
The probe selects the netchan XOR command text from each packet's reliable ACK,
so in-flight messages acknowledging the preceding `cp` command remain valid.
The isolated server was stopped afterward. Real C1 consumption remains unverified.
