import pathlib  
p=pathlib.Path('CODOL_RUNTIME_COD_20261019/run_all.py')  
s=p.read_text(encoding='utf-8')  
lines=s.splitlines()  
lines=[('GAME_ROOT = r\\\"D:\\\\BaiduNetdiskDownload\\\\\u547d\u4ee4\u53ec\u5524OL\\\\COD OL\\\"' if l.startswith('GAME_ROOT') else l) for l in lines] 
