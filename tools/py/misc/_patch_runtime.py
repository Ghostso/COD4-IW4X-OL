import io 
p='CODOL_RUNTIME_COD_20261019/run_all.py' 
s=open(p,encoding='utf-8').read() 
old='GAME_ROOT = r\\\"D:\\BaiduNetdiskDownload\\ π√¸’ŸªΩOL\\run_codol_001\\sandbox_datafix_20260929\\\"' 
new='GAME_ROOT = r\\\"D:\\BaiduNetdiskDownload\\ π√¸’ŸªΩOL\\COD OL\\\"' 
assert old in s 
open(p,'w',encoding='utf-8').write(s.replace(old,new)) 
