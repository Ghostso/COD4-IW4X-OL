import struct, os
D=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump"
p=os.path.join(D,"snap_002.bin"); LO=0x00010000
data=open(p,"rb").read()
BASE=0x400000; END=0x400000+0x0E659000
lo=BASE-LO; hi=END-LO
txt=data[lo:hi]
# search for immediate-compare patterns against the Demonware codes
pats=[(b"\x3C\x81","cmp al,0x81"),(b"\x3C\x83","cmp al,0x83"),(b"\x3C\x84","cmp al,0x84"),(b"\x3C\x85","cmp al,0x85"),
      (b"\x80\xF9\x81","cmp cl,0x81"),(b"\x80\xF9\x83","cmp cl,0x83"),(b"\x80\xF9\x84","cmp cl,0x84"),(b"\x80\xF9\x85","cmp cl,0x85"),
      (b"\x80\xFA\x81","cmp dl,0x81"),(b"\x80\xFA\x83","cmp dl,0x83"),(b"\x80\xFA\x84","cmp dl,0x84"),(b"\x80\xFA\x85","cmp dl,0x85"),
      (b"\x3D\x81\x00\x00\x00","cmp eax,0x81"),(b"\x3D\x83\x00\x00\x00","cmp eax,0x83"),
      (b"\x3D\x84\x00\x00\x00","cmp eax,0x84"),(b"\x3D\x85\x00\x00\x00","cmp eax,0x85")]
hits={}
for pat,name in pats:
    i=0; lst=[]
    while True:
        i=txt.find(pat,i)
        if i<0: break
        lst.append(BASE+i); i+=1
        if len(lst)>60: break
    if lst: hits[name]=lst
for k,v in hits.items():
    print("%-16s %3d  %s"%(k,len(v),", ".join("0x%X"%x for x in v[:10])+(" ..." if len(v)>10 else "")))
