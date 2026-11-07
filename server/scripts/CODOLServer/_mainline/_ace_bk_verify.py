import os,glob,hashlib
files=glob.glob('files/*')
print("备份文件数:",len(files))
# 抽查几个大文件：非零字节占比
for pat in ['*ACE-DRV64.dll','*tvsd.dll','*ACE-BASE.sys','*ace-ats32.dll','*ACE-DRV32.dll','*PolicyProbe.dll']:
    for p in glob.glob('files/'+pat):
        d=open(p,'rb').read()
        nz=sum(1 for b in d[:2000000] if b)
        print("%-58s size=%-10d nonzero(first2MB)=%d%%  head=%s"%(os.path.basename(p)[:58],len(d),int(100*nz/min(len(d),2000000)),d[:8].hex()))
