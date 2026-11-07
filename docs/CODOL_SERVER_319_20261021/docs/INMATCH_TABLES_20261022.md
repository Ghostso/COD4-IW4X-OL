# CODOL 3.19 in-match delta tables (all three)

Source: run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin  (ImageBase 0x400000)

struct netField_t { uint32 offset; int32 bits; uint32 pad; }; 12 bytes
bits > 0 = bit width; bits < 0 = codec type; bits = 0 = unused

## Discovery: 5 call sites of WriteDeltaStruct 0x670FF0

| Call site | Table | numFields | Meaning |
|---|---|---|---|
| 0x4717A4 | 0xDA8078 | 0x57 = 87 | playerState |
| 0x471886 | 0xDA8078 | 0x57 = 87 | playerState (2nd path) |
| 0x471BC8 | 0xDA63E8 | 0x18 = 24 | entityState |
| 0x471C84 | 0xDA63E8 | 0x18 = 24 | entityState (2nd path) |
| 0x673FC6 | 0xDA90A8 | 0x09 = 9 | third struct |

Index width = floor(log2(numFields))+1 : 87->7bit, 24->5bit, 9->4bit

## playerState  table=0xDA8078  entries=87

| Index | Offset | Bits |
|---|---|---|
| 0 | 0x140 | 11 |
| 1 | 0x040 | 32 |
| 2 | 0x098 | 32 |
| 3 | 0x09C | 32 |
| 4 | 0x0A0 | 32 |
| 5 | 0x0A4 | 32 |
| 6 | 0x0A8 | 32 |
| 7 | 0x0AC | 32 |
| 8 | 0x0B0 | 0 |
| 9 | 0x0B4 | 0 |
| 10 | 0x0B8 | 0 |
| 11 | 0x0BC | 0 |
| 12 | 0x0C0 | 0 |
| 13 | 0x0C4 | 0 |
| 14 | 0x0C8 | 0 |
| 15 | 0x0CC | 0 |
| 16 | 0x0D0 | 0 |
| 17 | 0x150 | 4 |
| 18 | 0x154 | 1 |
| 19 | 0x158 | 1 |
| 20 | 0x07C | 16 |
| 21 | 0x04C | 32 |
| 22 | 0x050 | 32 |
| 23 | 0x054 | 32 |
| 24 | 0x058 | 32 |
| 25 | 0x05C | 32 |
| 26 | 0x060 | 32 |
| 27 | 0x064 | 32 |
| 28 | 0x068 | 32 |
| 29 | 0x06C | 32 |
| 30 | 0x070 | 32 |
| 31 | 0x074 | 32 |
| 32 | 0x078 | 32 |
| 33 | 0x018 | 10 |
| 34 | 0x01C | 10 |
| 35 | 0x020 | 10 |
| 36 | 0x004 | 11 |
| 37 | 0x008 | 32 |
| 38 | 0x00C | 32 |
| 39 | 0x010 | 3 |
| 40 | 0x014 | 10 |
| 41 | 0x144 | 11 |
| 42 | 0x14C | 16 |
| 43 | 0x044 | 8 |
| 44 | 0x024 | 10 |
| 45 | 0x028 | 10 |
| 46 | 0x030 | 6 |
| 47 | 0x034 | 6 |
| 48 | 0x038 | 6 |
| 49 | 0x048 | 8 |
| 50 | 0x148 | 6 |
| 51 | 0x080 | 10 |
| 52 | 0x084 | 10 |
| 53 | 0x088 | 11 |
| 54 | 0x08C | 10 |
| 55 | 0x090 | 10 |
| 56 | 0x15C | 5 |
| 57 | 0x02C | 6 |
| 58 | 0x03C | 6 |
| 59 | 0x094 | 32 |
| 60 | 0x0D4 | 0 |
| 61 | 0x0D8 | 0 |
| 62 | 0x0DC | 0 |
| 63 | 0x0E0 | 0 |
| 64 | 0x0E4 | 0 |
| 65 | 0x0E8 | 0 |
| 66 | 0x0EC | 0 |
| 67 | 0x0F0 | 0 |
| 68 | 0x0F4 | 0 |
| 69 | 0x0F8 | 0 |
| 70 | 0x0FC | 0 |
| 71 | 0x100 | 0 |
| 72 | 0x104 | 0 |
| 73 | 0x108 | 0 |
| 74 | 0x10C | 0 |
| 75 | 0x110 | 0 |
| 76 | 0x114 | 0 |
| 77 | 0x118 | 0 |
| 78 | 0x11C | 0 |
| 79 | 0x120 | 0 |
| 80 | 0x124 | 0 |
| 81 | 0x128 | 0 |
| 82 | 0x12C | 0 |
| 83 | 0x130 | 0 |
| 84 | 0x134 | 0 |
| 85 | 0x138 | 0 |
| 86 | 0x13C | 0 |

## entityState  table=0xDA63E8  entries=24

| Index | Offset | Bits |
|---|---|---|
| 0 | 0x04C | -58 |
| 1 | 0x050 | -100 |
| 2 | 0x054 | -100 |
| 3 | 0x041 | -57 |
| 4 | 0x044 | -97 |
| 5 | 0x048 | 16 |
| 6 | 0x042 | -57 |
| 7 | 0x043 | -100 |
| 8 | 0x00C | 10 |
| 9 | 0x038 | 12 |
| 10 | 0x03C | -97 |
| 11 | 0x040 | -57 |
| 12 | 0x034 | 32 |
| 13 | 0x014 | 10 |
| 14 | 0x018 | 10 |
| 15 | 0x028 | 6 |
| 16 | 0x01C | 10 |
| 17 | 0x02C | 6 |
| 18 | 0x020 | 10 |
| 19 | 0x030 | 6 |
| 20 | 0x004 | 11 |
| 21 | 0x008 | 11 |
| 22 | 0x010 | 11 |
| 23 | 0x024 | 6 |

## struct3  table=0xDA90A8  entries=9

| Index | Offset | Bits |
|---|---|---|
| 0 | 0x004 | 0 |
| 1 | 0x008 | 0 |
| 2 | 0x00C | 0 |
| 3 | 0x020 | 12 |
| 4 | 0x010 | 11 |
| 5 | 0x014 | 4 |
| 6 | 0x024 | -97 |
| 7 | 0x01C | 4 |
| 8 | 0x028 | -57 |

## Codec dispatch (0x670D30)

| bits value | Meaning |
|---|---|
| -57 | angle codec |
| -58 | single-byte angle |
| -94 | raw 8-byte copy |
| -97 | packed angle |
| -100 | packed angle |
| -101 | float to int A |
| -102 | float to int B |


---

## Appendix: table at 0xDA4608 (all-codec struct, 9 fields)

Referenced from 0x671242 (mov ecx, 0xDA4608). Entry layout same as netField_t: { uint32 offset; int32 bits; uint32 pad; } 12 bytes.

| # | offset | bits |
|---|---|---|
| 0 | 0x004 | -77 |
| 1 | 0x008 | -98 |
| 2 | 0x018 | -83 |
| 3 | 0x01C | -82 |
| 4 | 0x020 | -81 |
| 5 | 0x0B8 | -94 |
| 6 | 0x0B4 | -75 |
| 7 | 0x0D8 | 32 |
| 8 | 0x094 | 8 |

Index width for 9 fields = 4 bits.

## Complete codec inventory

| codec | seen in |
|---|---|
| -57 | entityState 0x041,0x040; struct3 0x028 |
| -58 | entityState 0x04C |
| -75 | 0xDA4608 0x0B4 |
| -77 | 0xDA4608 0x004 |
| -81 | 0xDA4608 0x020 |
| -82 | 0xDA4608 0x01C |
| -83 | 0xDA4608 0x018 |
| -94 | 0xDA4608 0x0B8; raw 8-byte copy at 0x670EF4 |
| -97 | entityState 0x044,0x03C; struct3 0x024 |
| -98 | 0xDA4608 0x008 |
| -100 | entityState 0x050,0x054,0x043 |
| -101 | branch at 0x670D65, no table entry |
| -102 | branch at 0x670E2C, no table entry |

## Codec dispatch (0x670D30)

670D49 mov ecx,[eax+4] / 670D53 cmp ecx,-0x5E(-94) -> 0x670EF4 raw memcpy / 670D65 cmp ecx,-0x65(-101) -> float->int A / 670E2C cmp ecx,-0x66(-102) -> float->int B / 670EDF default plain copy

