IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
# Compare size/image metadata of the local EXE vs the image
import struct
for p,lbl in [(r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe","local EXE")]:
    b=open(p,'rb').read(); pe=struct.unpack_from("<I",b,0x3C)[0]; opt=pe+24
    print("%-10s TimeDateStamp=%08X SizeOfImage=%08X SizeOfHeaders/FileAlign=%X" % (lbl,
      struct.unpack_from("<I",b,pe+8)[0], struct.unpack_from("<I",b,opt+56)[0], struct.unpack_from("<I",b,opt+60)[0]))
b=d; pe=struct.unpack_from("<I",b,0x3C)[0]; opt=pe+24
print("%-10s TimeDateStamp=%08X SizeOfImage=%08X SizeOfHeaders/FileAlign=%X" % ("image_best",
      struct.unpack_from("<I",b,pe+8)[0], struct.unpack_from("<I",b,opt+56)[0], struct.unpack_from("<I",b,opt+60)[0]))
print()
print("009 manifest: ol-mod out.exe (044c396c...) TimeDateStamp 0x6096930A SizeOfImage 0x0E5D6000  <-- NOT local")
print("009 manifest: local EXE (36997674...)  TimeDateStamp 0x6096930A SizeOfImage 0x0E659000")
print("=> image_best SizeOfImage=%08X matches local EXE (0x0E659000)?" % struct.unpack_from("<I",b,opt+56)[0])
