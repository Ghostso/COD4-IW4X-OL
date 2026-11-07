from pathlib import Path
for n in [r'COD OL\TCLS\config\commonconfig.cfg',r'COD OL\TCLS\config\check.ini',r'COD OL\TCLS\config\name2id.xml',r'COD OL\TCLS\config\dirserver.xml',r'COD OL\TCLS\version.ini',r'COD OL\TCLS\Tenio.ini',r'COD OL\TCLS\TCLSCheck.lst']:
 p=Path(n)
 try: txt=p.read_text(encoding='utf-8',errors='replace')
 except: txt='<binary>'
 Path(r'_dyn_stage1\one_config.txt').write_text(f'==={n}===\n{txt}\n',encoding='utf-8')
 print('WROTE',n)
 break
