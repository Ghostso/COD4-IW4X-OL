from pathlib import Path
root=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\_dyn_stage1')
for n in ['_target_context_xrefs.txt','_startup_candidates.txt','_startup_strings.txt','_read_launch_params.txt','official_launch_watch2.log']:
 p=root/n
 print('\n===== '+n+' =====')
 if not p.exists(): print('MISSING'); continue
 b=p.read_bytes()
 try:s=b.decode('utf-8')
 except:s=b.decode('gbk','replace')
 lines=s.splitlines()
 if n=='official_launch_watch2.log': lines=lines[-260:]
 else: lines=lines[:300]
 print('\n'.join(lines))
