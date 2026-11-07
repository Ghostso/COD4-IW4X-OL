import struct
exe=r"run_codol_001\sandbox_datafix_20260929\codoMP_client_shipRetail.exe"
d=open(exe,'rb').read()
# the packed image: use image_best.bin instead
img=open(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin",'rb').read()
off=0xBA373E-0x400000
print(img[off:off+24].hex())
