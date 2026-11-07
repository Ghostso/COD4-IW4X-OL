import pickle
p=r"D:\BaiduNetdiskDownload\使命召唤OL\E20_TYPE_BRANCH_CLOSURE_001\_work\client_callgraph.pkl"
D=pickle.load(open(p,"rb"))
print(D.keys())
for k,v in D.items():
    try: print(k, type(v), len(v))
    except: print(k,type(v))
