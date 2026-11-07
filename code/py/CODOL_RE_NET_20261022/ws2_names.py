import pefile
ws=r'C:\Windows\SysWOW64\ws2_32.dll'
pe=pefile.PE(ws)
ex={}
for s in pe.DIRECTORY_ENTRY_EXPORT.symbols:
    if s.name: ex[s.address]=s.name.decode()
print('exports',len(ex))
slots={0x00ca8534:0x9cc0,0x00ca8538:0x300a0,0x00ca853c:0x5d50,0x00ca8540:0x57e0,0x00ca8544:0xea60,0x00ca8548:0xc990,0x00ca854c:0x12520,0x00ca8550:0x56e0,0x00ca8554:0xd890,0x00ca855c:0x2ff10,0x007fc7d0:0xe8fc,0x00b9e040:0xe95e}
for s,r in sorted(slots.items()):
    print('%#010x -> ws2+%#08x = %s' % (s,r,ex.get(r,'?')))
