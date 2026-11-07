import pefile, os, re, struct, collections
root=r'COD OL'
def load(p): return open(p,'rb').read()
files={
 'exe': os.path.join(root,'codoMP_client_shipRetail.exe'),
 'dll': os.path.join(root,'codoMP_client_shipRetailBase.dll'),
 'dll_local': os.path.join(root,r'codoMP_client_shipRetail.exe.local\codoMP_client_shipRetailBase.dll'),
}
# diff the two dlls
a=load(files['dll']); b=load(files['dll_local'])
print('dll sizes',len(a),len(b))
diffs=[]
i=0
while i<min(len(a),len(b)):
    if a[i]!=b[i]:
        j=i
        while j<min(len(a),len(b)) and a[j]!=b[j]: j+=1
        diffs.append((i,j-i)); i=j
    else: i+=1
print('diff runs:',len(diffs),'total diff bytes',sum(n for _,n in diffs))
for off,n in diffs[:40]:
    print(f'  off={off:#010x} len={n} fileA={a[off:off+min(n,16)].hex()} fileB={b[off:off+min(n,16)].hex()}')
