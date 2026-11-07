from pathlib import Path
files=['exe_functions.csv','exe_callgraph.csv','exe_globals.csv','exe_strings_refs.csv','exe_mainloop_candidates.csv','exe_external_calls.csv']
for p in files:
    path=Path(p)
    print('###',p,'exists',path.exists(),'size', path.stat().st_size if path.exists() else None)
    if path.exists():
        with path.open('r',encoding='utf-8',newline='') as f:
            for i,line in zip(range(8),f):
                print(line.rstrip())
