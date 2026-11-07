import pefile
pe=pefile.PE('C:\\Windows\\System32\\kernel32.dll')
pe.FILE_HEADER.NumberOfSections=3
pe.sections=[]
# .text
t=pefile.SECTION_HEADER()
t.Name=b'.text\x00\x00\x00'
t.VirtualSize=len(bytearray(b'\xb8\x78\x56\x34\x12\xc3\xc3'))
t.VirtualAddress=0
t.SizeOfRawData=len(bytearray(b'\xb8\x78\x56\x34\x12\xc3\xc3'))
t.PointerToRawData=0
t.Characteristics=0x60000020
pe.sections.append(t)
# .rdata
r=pefile.SECTION_HEADER()
r.Name=b'.rdata\x00\x00\x00'
s1=b'GetResourceManagerII\x00'
s2=b'ReleaseResourceManagerII\x00'
rdata=bytearray()
rdata+=s1
rdata+=s2
r.VirtualSize=len(rdata)
r.VirtualAddress=0
r.SizeOfRawData=len(rdata)
r.PointerToRawData=0
r.Characteristics=0x40000040
pe.sections.append(r)
# .data
d=pefile.SECTION_HEADER()
d.Name=b'.data\x00\x00\x00'
datalen=bytearray(struct.pack('<L',0))+b'\x00'*0x410
d.VirtualSize=len(datalen)
d.VirtualAddress=0
d.SizeOfRawData=len(datalen)
d.PointerToRawData=0
d.Characteristics=0xC0000040
pe.sections.append(d)
# Set data
pe.sections[0].set_data(bytearray(b'\xb8\x78\x56\x34\x12\xc3\xc3'))
pe.sections[1].set_data(rdata)
pe.sections[2].set_data(datalen)
pe.write('LocalRM.dll')
print('LocalRM.dll')