import struct,capstone,json
IMG=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin"
b=open(IMG,'rb').read();IB=0x400000
# Quantify direct call graph quality in restored image
# prologue heuristic: valid function entry preceded by 0xcc padding and starts with common prologues
entries=set()
for i in range(0x1000,min(len(b),0x8a6000)-2):
 if b[i] in (0x55,0x6a,0x8b) and i>=2 and b[i-1]==0xcc and b[i-2]==0xcc:
  entries.add(i)
# count E8 targets
stats={'e8_total':0,'target_in_file':0,'target_entry':0,'target_mid':0,'target_oob':0}
bad=[]
for i in range(0x1000,min(len(b),0x8a6000)-5):
 if b[i]==0xe8:
  stats['e8_total']+=1
  rel=struct.unpack_from('<i',b,i+1)[0];t=i+5+rel
  if 0<=t<len(b):
   stats['target_in_file']+=1
   if t in entries:stats['target_entry']+=1
   else:
    stats['target_mid']+=1
    if len(bad)<20:bad.append((i,t))
  else:stats['target_oob']+=1
print(json.dumps(stats,indent=2))
print('first mid-target callers:',[(hex(a),hex(t)) for a,t in bad])
# E8/E9 stats in .tvm0-like second virtual section? identify raw region 0x8a8000..0xa16000
tv=b[0x8a8000:0xa16000]
n=0;valid=0
for i in range(len(tv)-5):
 if tv[i] in (0xe8,0xe9):
  n+=1
  rel=struct.unpack_from('<i',tv,i+1)[0];t=0x8a8000+i+5+rel
  if 0x1000<=t<0x8a6000:valid+=1
print('tvm0-like region E8/E9',n,'target-in-text',valid,'ratio',valid/max(1,n))
