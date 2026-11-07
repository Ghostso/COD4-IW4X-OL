from pathlib import Path
import re
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll')
data=p.read_bytes()
# raw offsets found earlier, dump local .rdata region only
start=0x88d800; end=0x890800
out=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\_dyn_stage1\base_rdata_context_cluster.txt')
with out.open('w',encoding='utf-8') as f:
 f.write(f'raw {start:08X}..{end:08X}\n')
 for m in re.finditer(rb'[\x20-\x7e]{4,}',data[start:end]):
  off=start+m.start(); s=m.group().decode('latin1')
  f.write(f'{off:08X} {s}\n')
print(out)
