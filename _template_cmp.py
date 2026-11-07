from pathlib import Path
D=Path('COD OL/codoMP_client_shipRetail.exe').read_bytes()
# Compare exact bytes from each occurrence to find maximal common prefix among the four template sites
sites=[0x36675,0xaa176,0xb2d90]
for i,a in enumerate(sites):
 for b in sites[i+1:]:
  n=0
  while a+n<len(D) and b+n<len(D) and D[a+n]==D[b+n] and n<256: n+=1
  print(hex(a),hex(b),'common',n,D[a:a+n].hex())
