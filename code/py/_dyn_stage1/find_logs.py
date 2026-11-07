import pathlib  
roots=[pathlib.Path('COD OL'),pathlib.Path('WeGame')]  
for r in roots:  
    for p in r.rglob('*'):  
        if p.is_file() and any(k in p.name.lower() for k in ['tenproxy','tcls','launcher','game','start','log']): print(p)  
