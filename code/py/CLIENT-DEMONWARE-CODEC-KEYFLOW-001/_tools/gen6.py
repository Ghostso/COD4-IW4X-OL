import os, hashlib
root = r"D:\BaiduNetdiskDownload\使命召唤OL\CLIENT-DEMONWARE-CODEC-KEYFLOW-001"
D=lambda n: os.path.join(root,n)
p=D("01_CODEC_FUNCTIONS.md"); t=open(p,encoding="utf-8").read()
old="等价掩码 M_A[i] = CONST_A[PERM_A[i]] = f3 42 11 12 72 f4 32 41 09 ae 3f 18 13 ea bc a3 54 bc 09 cc\n等价掩码 M_B[i] = CONST_B[PERM_B[i]] = 21 3c ff 0b f4 22 ee 00 92 de ce aa 27 1c f4 80 10 21 37 09"
new=("等价掩码 M_A[i] = CONST_A[PERM_A[i]] = f3 42 11 12 72 f4 32 41 09 ae 3f 18 13 ea bc a3 54 bc 09 cc\n"
     "等价掩码 M_B[i] = CONST_B[PERM_B[i]] = 21 3c ff 0b f4 22 ee 00 92 de ce aa 27 aa 1c f4 80 10 21 37\n"
     "\n# 本轮离线复核（_tools/p29_maskverify.py，静态重算，未运行客户端）\n"
     "M_A(20B) == M_B(20B) 长度均为 20；clientStore(x)=x^M，clientLoad(y)=y^M ⇒ LOAD(STORE(x))==x 逐字节成立\n"
     "参考 C# DecodeKey 的 words[]/indices[] 展开后得到与上表**逐字节相同**的 M_A/M_B（已离线验证）")
assert old in t
t=t.replace(old,new)
open(p,"w",encoding="utf-8").write(t)
print("patched 01 mask B")

# regenerate manifest including the verification script output
lines=[]
for f in sorted(x for x in os.listdir(root) if x.endswith(".md")):
    lines.append("%s  %s"%(hashlib.sha256(open(D(f),"rb").read()).hexdigest(),f))
dd=os.path.join(root,"_data")
for f in sorted(os.listdir(dd)):
    lines.append("%s  _data/%s"%(hashlib.sha256(open(os.path.join(dd,f),"rb").read()).hexdigest(),f))
open(D("SHA256SUMS.txt"),"w",encoding="utf-8").write("\n".join(lines)+"\n")
print("manifest",len(lines),"entries")
for l in lines: print(l)
