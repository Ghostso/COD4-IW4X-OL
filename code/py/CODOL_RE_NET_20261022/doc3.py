import struct
d=open(r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B=0x400000
lines=[]
lines.append('# CODOL 3.19 in-match delta tables (all three)')
lines.append('')
lines.append('Source: run_codol_001\\runs\\OMIT_RETEST_20261022\\mem\\mem_005.bin  (ImageBase 0x400000)')
lines.append('Entry layout: struct netField_t { uint32 offset; int32 bits; uint32 pad; }; 12 bytes')
lines.append('bits > 0 = bit width; bits < 0 = codec type; bits = 0 = unused')
lines.append('')
lines.append('Discovered via 5 call sites of WriteDeltaStruct 0x670FF0:')
lines.append('  0x4717A4  table 0xDA8078  numFields 0x57 = 87  -> playerState')
lines.append('  0x471886  table 0xDA8078  numFields 0x57 = 87  -> playerState (second path)')
lines.append('  0x471BC8  table 0xDA63E8  numFields 0x18 = 24  -> entityState')
lines.append('  0x471C84  table 0xDA63E8  numFields 0x18 = 24  -> entityState (second path)')
lines.append('  0x673FC6  table 0xDA90A8  numFields 0x09 = 9   -> third struct')
lines.append('')
lines.append('Index width = floor(log2(numFields))+1 : 87->7bit, 24->5bit, 9->4bit')
lines.append('')