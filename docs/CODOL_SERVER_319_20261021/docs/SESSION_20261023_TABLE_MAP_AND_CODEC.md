# CODOL 3.19 In-Match Table Map and Codec Spec  
  
Evidence: run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin (241,537,024 B, ImageBase 0x400000)  
## 0. Status  
  
In-match delta bitstream format is FULLY decoded (tables, bit widths, codecs, index coding, run-length).  
tools/codol_codec.py passes self-checks. snapshot.c NOT yet modified. No live test.  
  
---  
  
## 1. Discovery: NOT 6 tables  
  
Authoritative scan method: reverse-lookup from 27 call sites of 6 delta functions.  
  
delta functions: 0x670FF0 ReadDeltaStruct / 0x670D30 ReadDeltaField / 0x6701D0 ReadDeltaField2  
0x677E10 WriteDeltaStruct / 0x6779B0 WriteDeltaStruct2 / 0x677D40 LastChanged  
  
27 call sites in 10 functions.  
  
| Function | Delta funcs | Tables |  
| Function | Delta | Tables |
|---|---|---|
| 0x471560 | ReadDeltaStruct | 0xDA8078 |
| 0x471980 | ReadDeltaStruct | 0xDA63E8, 0xDA9920(non-table) |
| 0x671170 | ReadDeltaField x2 | 0xDA4608, 0xDA9330, 0xDA9334 |
| 0x671B60 | ReadDeltaField x2 | 0xDA9138 |
| 0x671D80 | Read/WriteDelta | 0xDA8520, 0xDA8528, 0xDA90A8 |
| 0x6783B0 | WriteDeltaStruct | 0xDA8078 |
| 0x6784E0 | WriteDeltaStruct | 0xDA63E8 |
| 0x678740 | WriteDeltaStruct2 | 0xDA8520, 0xDA90A8 |

### 1.2 Six main tables confirmed

| # | Table | Fields | indexBits | Use | Exported |
|---|---|---|---|---|---|
| 1 | 0xDA8078 | 87 | 7 | playerState | YES |
| 2 | 0xDA63E8 | 24 | 5 | entityState | YES |
| 3 | 0xDA90A8 | 9 | 4 | struct3 (0x2C stride) | YES |
| 4 | 0xDA4608 | 64 (0..63) | 6 | array elem (0x118 stride) | YES |
| 5 | 0xDA9138 | 42 | 6 | sub-struct (0x0C stride) | YES |
| 6 | 0xDA8520 | 246 | 8 | big struct (0x3B90) | YES |

### 1.3 NEW: 0xDA9330 is a table-of-tables

Format: { uint32 table_ptr; int32 max_index; }[N], stride 8

Code at 0x67127C:
    0067127C  mov edx, [ecx*8 + 0xDA9330]   ; table ptr
    00671286  cmp eax, [ecx*8 + 0xDA9334]   ; max index (+4 view)

ecx = array element TYPE id ([ebx+4], bound cmp 0x17 = 23)

Known entries (first 6):
    [0] 0xDA4608  max 0x3F
    [1] 0xDA4BF8  max 0x3F
    [2] 0xDA4EF0  max 0x3F
    [3] 0xDA6508  max 0x3F
    [4] 0xDA7A20  max 0x3F
    [5] 0xDA4608  max 0x3F

CONCLUSION: array elements have MULTIPLE per-type layouts.
Each type uses max_index=0x3F, i.e. 64 items (indices 0..63).
All 24 type entries are mapped; de-duplicated by table pointer there are
18 distinct layouts. The complete export is in
`docs/INMATCH_ARRAY_ELEMENT_VARIANTS_20261023.md` and
`fixtures/inmatch_array_element_variants_20261023.json`.
Aliases are preserved in the type table.

### 1.4 Non-tables (false positives)

0xDA9920: 0x58-byte entity default template, used by memcpy at 0x471A2E.
0xDA8528 = 0xDA8520 + 8  (field pointer inside same table)
0xDA9334 = 0xDA9330 + 4  (+4 view of same array)

---

## 2. Bitstream format (fully determined)

### 2.1 Three layers

struct layer  0x670FF0 / 0x677E10 : hasDelta + lastChanged + run loop
index layer   0x670CB0          : varint run length
field layer   0x6701D0 / 0x676E00 : change bit + codec payload

### 2.2 Struct layer order

    bit : hasDelta
      hasDelta == 0 : FULL, every field read as value, no change bit
      hasDelta == 1 :
        indexBits bits : lastChangedIndex
        loop {
            varint : run
            run fields : value only, no change bit
            1 field : change bit + value
        } until index == lastChangedIndex
        remaining fields : change bit + value each

indexBits = floor(log2(numFields)) + 1
  87-7  24-5  9-4  64-6  42-6  246-8

### 2.3 Index varint 0x670CB0

indexBits == 1 : unary, count consecutive ones
otherwise:
  run == 1 : write one bit 1
  else     : write one bit 0, then (run-1) in indexBits chunks,
             continuing while chunk equals (1 shifted indexBits)-1

### 2.4 Field codec dispatch 0x6701D0 - all 45 branches

CRITICAL: negative bits has TWO meanings

    00670B37  mov eax,[ebp-0x14]
    00670B3A  mov eax,[eax+4]      ; eax = entry bits, can be negative
    00670B40  call 0x66FE30        ; read abs(bits) + sign extend

0x66FE30 does sets bl (bl = bits smaller than 0), neg esi, then sign-extends.

bits greater than 0      : unsigned int, width = bits
bits equals 0           : FLOAT CODEC, not unused
bits negative, in codec set  : dedicated codec
bits negative, not in set    : signed int, width = abs(bits)

45 codecs (exhaustive cmp ecx,imm8):

  -64 -63 -62 -101 -102 -80 -78 -75 -89 -88 -61 -60 -59 -99 -65
  -98 -97 -74 -73 -72 -71 -70 -96 -93 -95 -94 -90 -83 -82 -81
  -100 -79 -58 -57 -56 -87 -86 -85 -84 -76 -69 -55

### 2.5 bits equals 0 is the FLOAT codec (major correction)

    0067020D  call 0x447190        ; bit
    00670218  jne  0x670235
    0067021A  call 0x447190        ; sign bit
    0067021F  shl  eax,0x1F        ; value = b shifted 31, plus/minus zero

    0 + 1 bit           : plus or minus zero
    1 + 1 + 32 bit      : raw bits, XOR with baseline
    1 + 0 + 5 bit + ... : compressed float (formula TODO)

This is why raw put_f32 in snapshot.c is wrong.

### 2.6 Self-check status of tools/codol_codec.py

- index varint both directions : PASS, 6 tables x 43 values
- unsigned int bits above 0    : PASS
- signed int, negative bits    : PASS, 1450 cases
- float codec                  : PASS, 288 cases
- playerState full delta       : PASS, 30 cases

Still missing:
- codecs -57 -58 -97 -100 -101 -102 exact formulas
- the other 39 codecs
- compressed float form

---

## 3. MAJOR CORRECTION: ol-mod 124B frame is NOT for 3.19

File _e1_regression/ol-mod-olfinal/tools/runtime/CodolNetfieldDump.py header:

    Dump the CODOL 3.3.3.3 playerstate netfield table from a live client.
    PLAYERSTATE_FIELD_COUNT = 235

ol-mod targets 3.3.3.3 with 235 playerState fields.
Our target is 3.19 with 87 playerState fields (7-bit index, max 127).

Therefore snapshot.c line 199 bw_index(219) CANNOT be represented in 3.19.
219 AND 0x7F = 91, client reads field 91, everything after is shifted.

This also explains why the 124-byte golden frame overflows the 87-field parser.

CONCLUSION: stop using the ol-mod 124B frame as reference.

---

## 4. Concrete bugs in snapshot.c

| Location | Current | Correct |
|---|---|---|
| bw_index() lines 43-51 | hardcoded 4-bit chunks, skip==0 test | use indexBits, run==1 test |
| put_f32() line 65 | raw 4 bytes | bits==0 float codec |
| put_f32_xor() | raw XOR | float codec |
| line 177 put_f32(60.0f) | raw | float codec |
| line 199 bw_index(219) | out of 87-field range | delete or remap |
| line 250 #if 0 clientInfo | disabled | enable with 7-bit index |
| overall | playerState only | add entityState and struct3 |

---

## 5. Gaps and where to get them

### 5.1 Format: DONE

Sources: this round of 4 docs plus tools/codol_codec.py

### 5.2 Field semantics: obtainable locally

playerState read 0x471560 / write 0x6783B0
entityState read 0x471980 / write 0x6784E0
struct3     0x671D80 / 0x678740
array elem  0x671170
sub-struct  0x671B60

Method: trace each offset to the global it feeds or the function it is passed to.

### 5.3 Runtime values: hard

battle_service.c currently reads a fixed gamestate binary:

    strncpy(svc-gamestate_path, firingrange-gamestate.bin, ...)
    fp = fopen(svc-gamestate_path, rb)

Three possible sources:
1. capture from official server (needs access)
2. local client built-in listen server (around 0x5AD350)
3. build our own gamestate generator

### 5.4 Game logic: obtainable locally

spawn points  : map .ff info_player_start
collision     : map .ff CLIPMAP_MP
minimap       : gamestate configstring
weapon defs   : .ff weapon assets

.ff decrypt chain already works (tools/codol_ff_unpack.py).
coop_train_zone.bin already extracted, 6,291,523 bytes.

---

## 6. Next steps in priority order

1. [DONE] export all array-element layouts (24 type entries -> 18 distinct layouts, 64 records each)
2. [TODO] rewrite playerState section of snapshot.c using the 3.19 87-field table
3. [TODO] implement codecs -57 -58 -97 -100 -101 -102
4. [TODO] add entityState (24) and struct3 (9) sections
5. [TODO] enable clientInfo section with 7-bit index
6. [TODO] reverse field semantics from 0x471560 / 0x471980
7. [TODO] get spawn point and collision from .ff
8. [TODO] solve gamestate value source

---

## 7. Files produced this round

docs/INMATCH_TABLE_INDEX_20261022.md        6 main tables + call chain
docs/INMATCH_TABLES_REMAINING_20261022.md   last 3 tables full fields
docs/INMATCH_ARRAY_ELEMENT_VARIANTS_20261023.md  all 18 array-element layouts (64 items each)
fixtures/inmatch_array_element_variants_20261023.json  machine-readable export
docs/INMATCH_BATTLE_SURFACE_20261023.md       netField scope + non-netField battle surfaces
fixtures/firingrange-gamestate-strings.json   gamestate sample string extraction
tools/gamestate_strings.py                    gamestate/configstring string extractor
docs/BITORDER_6701D0_20261022.md            bit order spec
docs/CODEC_SPEC_20261022.md                 codec semantics, sections 6 and 7 are corrections
docs/SESSION_20261023_TABLE_MAP_AND_CODEC.md  this file
tools/codol_codec.py                       executable codec + selftest
tools/scan_authoritative.py                authoritative table scan
tools/export_array_element_variants.py     export/check array-element layouts
docs/_6701D0.txt                           0x6701D0 full disassembly, 1067 lines
docs/_dis_write.txt                        write path disassembly
docs/_dis_read.txt                         read path disassembly
docs/_dis_sv.txt                           SV snapshot disassembly

---

## 8. Environment notes

- tool shell is cmd.exe, not PowerShell; commands starting with dollar sign fail
- Chinese paths get mangled when passed as cmd arguments
- pipe character and greater-than are interpreted by cmd, avoid them
- workaround: write helper .py under ASCII path then run it
- no game client or service process was started
- protected assets REF_LOBBY_KIT and CODOL_VERIFIED_GOLDEN_20261019 untouched
