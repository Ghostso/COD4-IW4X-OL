import struct
d=open(r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B=0x400000
p=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\docs\INMATCH_TABLES_20261022.md'
lines=open(p,'r',encoding='utf-8').read().splitlines() if False else []
lines.append('# CODOL 3.19 in-match delta tables (all three)')
lines.append('')
lines.append('Source: run_codol_001\\runs\\OMIT_RETEST_20261022\\mem\\mem_005.bin  (ImageBase 0x400000)')
lines.append('')
lines.append('struct netField_t { uint32 offset; int32 bits; uint32 pad; }; 12 bytes')
lines.append('bits > 0 = bit width; bits < 0 = codec type; bits = 0 = unused')
lines.append('')
lines.append('## Discovery: 5 call sites of WriteDeltaStruct 0x670FF0')
lines.append('')
lines.append('| Call site | Table | numFields | Meaning |')
lines.append('|---|---|---|---|')
lines.append('| 0x4717A4 | 0xDA8078 | 0x57 = 87 | playerState |')
lines.append('| 0x471886 | 0xDA8078 | 0x57 = 87 | playerState (2nd path) |')
lines.append('| 0x471BC8 | 0xDA63E8 | 0x18 = 24 | entityState |')
lines.append('| 0x471C84 | 0xDA63E8 | 0x18 = 24 | entityState (2nd path) |')
lines.append('| 0x673FC6 | 0xDA90A8 | 0x09 = 9 | third struct |')
lines.append('')
lines.append('Index width = floor(log2(numFields))+1 : 87->7bit, 24->5bit, 9->4bit')
lines.append('')
for name,va,n in [('playerState',0xDA8078,87),('entityState',0xDA63E8,24),('struct3',0xDA90A8,9)]:
    lines.append('## %s  table=0x%X  entries=%d'%(name,va,n))
    lines.append('')
    lines.append('| Index | Offset | Bits |')
    lines.append('|---|---|---|')
    o=va-B
    for i in range(n):
        q=o+i*12
        off=struct.unpack_from('<I',d[q:q+4])[0]
        bits=struct.unpack_from('<i',d[q+4:q+8])[0]
        lines.append('| %d | 0x%03X | %d |'%(i,off,bits))
    lines.append('')
lines.append('## Codec dispatch (0x670D30)')
lines.append('')
lines.append('| bits value | Meaning |')
lines.append('|---|---|')
lines.append('| -57 | angle codec |')
lines.append('| -58 | single-byte angle |')
lines.append('| -94 | raw 8-byte copy |')
lines.append('| -97 | packed angle |')
lines.append('| -100 | packed angle |')
lines.append('| -101 | float to int A |')
lines.append('| -102 | float to int B |')
lines.append('')
open(p,'w',encoding='utf-8',newline='\n').write('\n'.join(lines)+'\n')
import os
print('bytes', os.path.getsize(p))