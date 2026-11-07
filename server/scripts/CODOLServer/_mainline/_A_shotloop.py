"""Capture desktop every N seconds into a folder (for [100] popup timing)."""
import ctypes, ctypes.wintypes as wt, os, sys, time

u32 = ctypes.windll.user32
g32 = ctypes.windll.gdi32

def grab(out):
    w = u32.GetSystemMetrics(0); h = u32.GetSystemMetrics(1)
    hdc = u32.GetDC(0); mdc = g32.CreateCompatibleDC(hdc)
    bmp = g32.CreateCompatibleBitmap(hdc, w, h); g32.SelectObject(mdc, bmp)
    if not g32.BitBlt(mdc, 0, 0, w, h, hdc, 0, 0, 0x00CC0020):
        return False
    class BMI(ctypes.Structure):
        _fields_=[("biSize",wt.DWORD),("biWidth",ctypes.c_long),("biHeight",ctypes.c_long),
                  ("biPlanes",wt.WORD),("biBitCount",wt.WORD),("biCompression",wt.DWORD),
                  ("biSizeImage",wt.DWORD),("biXPelsPerMeter",ctypes.c_long),("biYPelsPerMeter",ctypes.c_long),
                  ("biClrUsed",wt.DWORD),("biClrImportant",wt.DWORD)]
    bi=BMI(); bi.biSize=ctypes.sizeof(BMI); bi.biWidth=w; bi.biHeight=-h
    bi.biPlanes=1; bi.biBitCount=24; bi.biCompression=0
    row=((w*3+3)//4)*4; bufsz=row*h
    buf=ctypes.create_string_buffer(bufsz)
    g32.GetDIBits(mdc,bmp,0,h,buf,ctypes.byref(bi),0)
    hdr=(b"BM"+(54+bufsz).to_bytes(4,"little")+b"\x00\x00\x00\x00"+(54).to_bytes(4,"little")+
         (40).to_bytes(4,"little")+w.to_bytes(4,"little")+h.to_bytes(4,"little")+
         (1).to_bytes(2,"little")+(24).to_bytes(2,"little")+(0).to_bytes(4,"little")+
         bufsz.to_bytes(4,"little")+b"\x00"*16)
    with open(out,"wb") as f: f.write(hdr); f.write(buf.raw)
    g32.DeleteObject(bmp); g32.DeleteDC(mdc); u32.ReleaseDC(0,hdc)
    return True

outdir=sys.argv[1]; seconds=float(sys.argv[2]); step=float(sys.argv[3]) if len(sys.argv)>3 else 3.0
os.makedirs(outdir, exist_ok=True)
t0=time.time(); i=0
while time.time()-t0 < seconds:
    p=os.path.join(outdir,"t%05.1f.bmp"%(time.time()-t0))
    try:
        if grab(p): print("shot",p,flush=True)
    except Exception as e:
        print("err",e,flush=True)
    i+=1
    time.sleep(step)
print("done shots=%d"%i,flush=True)
