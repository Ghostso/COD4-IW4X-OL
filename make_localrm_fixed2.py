import pefile
import struct
def align(v,a):return (v+a-1)&~(-a)
template_path='D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL\\IIPS\\iips.dll'
pe=pefile.PE(template_path)
# Our data
text=bytearray(b'\xb8\x78\x56\x34\x12\xc3\xc3')
s1=b'GetResourceManagerII\x00'
s2=b'ReleaseResourceManagerII\x00'
rdata=bytearray()
rdata+=s1
rdata+=s2
data=bytearray(struct.pack('<L',0))+b'\x00'*0x410
# Find sections by name
text_sec=None
rdata_sec=None
data_sec=None
for sec in pe.sections:
    n=sec.Name.decode().rstrip('\x00')
    if n=='.text': text_sec=sec
    elif n=='.rdata': rdata_sec=sec
    elif n=='.data': data_sec=sec
if not (text_sec and rdata_sec and data_sec):
    text_sec=pe.sections[0]
    rdata_sec=pe.sections[1]
    data_sec=pe.sections[2]
fh=pe.OPTIONAL_HEADER.FileAlignment
sh=pe.OPTIONAL_HEADER.SectionAlignment
# Update .text
text_sec.Misc_VirtualSize=len(text)
text_sec.SizeOfRawData=align(len(text),fh)
ptr=text_sec.PointerToRawData
with open(template_path,'r+b') as f:
    f.seek(ptr)
    f.write(text)
    if len(text)<text_sec.SizeOfRawData:
        f.write(b'\x00'*(text_sec.SizeOfRawData-len(text)))
# Update .rdata (we will replace entirely later)
# Write strings at start of .rdata
ptr=rdata_sec.PointerToRawData
with open(template_path,'r+b') as f:
    f.seek(ptr)
    f.write(s1)
    f.write(s2)
# Update .data
data_sec.Misc_VirtualSize=len(data)
data_sec.SizeOfRawData=align(len(data),fh)
ptr=data_sec.PointerToRawData
with open(template_path,'r+b') as f:
    f.seek(ptr)
    f.write(data)
    if len(data)<data_sec.SizeOfRawData:
        f.write(b'\x00'*(data_sec.SizeOfRawData-len(data)))
# Build export directory and arrays in .rdata after strings
string1_rva=rdata_sec.VirtualAddress
string2_rva=rdata_sec.VirtualAddress+len(s1)
func1_rva=text_sec.VirtualAddress
func2_rva=text_sec.VirtualAddress+6
# We'll place export directory and arrays right after the strings in .rdata
# Build export directory
exp_dir=bytearray()
exp_dir+=struct.pack('<IHHIILLLLLL',0,0,0,0,0,1,2,2,0,0,0)
off_funcs=28
off_names=32
off_ords=36
funcs_array=struct.pack('<LL',func1_rva,func2_rva)
names_array=struct.pack('<LL',string1_rva,string2_rva)
ords_array=struct.pack('<HH',0,1)
new_rdata=bytearray()
new_rdata+=s1
new_rdata+=s2
new_rdata+=exp_dir
new_rdata+=funcs_array
new_rdata+=names_array
new_rdata+=ords_array
# Set the three RVAs in export directory
funcs_array_rva=rdata_sec.VirtualAddress+len(s1)+len(s2)+len(exp_dir)
names_array_rva=rdata_sec.VirtualAddress+len(s1)+len(s2)+len(exp_dir)+len(funcs_array)
ords_array_rva=rdata_sec.VirtualAddress+len(s1)+len(s2)+len(exp_dir)+len(funcs_array)+len(names_array)
struct.pack_into('<L',new_rdata,len(s1)+len(s2)+off_funcs,funcs_array_rva)
struct.pack_into('<L',new_rdata,len(s1)+len(s2)+off_names,names_array_rva)
struct.pack_into('<L',new_rdata,len(s1)+len(s2)+off_ords,ords_array_rva)
# Update .rdata section
rdata_sec.Misc_VirtualSize=len(new_rdata)
rdata_sec.SizeOfRawData=align(len(new_rdata),fh)
ptr=rdata_sec.PointerToRawData
with open(template_path,'r+b') as f:
    f.seek(ptr)
    f.write(new_rdata)
    if len(new_rdata)<rdata_sec.SizeOfRawData:
        f.write(b'\x00'*(rdata_sec.SizeOfRawData-len(new_rdata)))
# Update export directory in data directory
export_dir_rva=rdata_sec.VirtualAddress+len(s1)+len(s2)
pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT']].VirtualAddress=export_dir_rva
pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT']].Size=40
# Update sizes and addresses
# Align virtual sizes to section alignment
text_sec.Misc_VirtualSize=align(text_sec.Misc_VirtualSize,sh)
rdata_sec.Misc_VirtualSize=align(rdata_sec.Misc_VirtualSize,sh)
data_sec.Misc_VirtualSize=align(data_sec.Misc_VirtualSize,sh)
# Set virtual addresses
cva=0x1000
for sec in [text_sec,rdata_sec,data_sec]:
    sec.VirtualAddress=cva
    cva+=sec.Misc_VirtualSize
# Size of image
pe.OPTIONAL_HEADER.SizeOfImage=align(cva-0x1000,sh)
# Size of headers
pe.OPTIONAL_HEADER.SizeOfHeaders=align(pe.OPTIONAL_HEADER.SizeOfHeaders,fh)
# Address of entry point, base of code, base of data
pe.OPTIONAL_HEADER.AddressOfEntryPoint=text_sec.VirtualAddress
pe.OPTIONAL_HEADER.BaseOfCode=text_sec.VirtualAddress
pe.OPTIONAL_HEADER.BaseOfData=data_sec.VirtualAddress
# Size of code and initialized data
pe.OPTIONAL_HEADER.SizeOfCode=text_sec.Misc_VirtualSize
pe.OPTIONAL_HEADER.SizeOfInitializedData=rdata_sec.Misc_VirtualSize+data_sec.Misc_VirtualSize
# Write file
pe.write('D:\\BaiduNetdiskDownload\\使命召唤OL\\LocalRM.dll')
print('LocalRM.dll written')