import re
p=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-DEMONWARE-BUNDLE-001\_build_register.py"
t=open(p,encoding="utf-8").read()
t=t.replace('impact=norm_impact(r.get("XVAL02_Impact")),',
            'impact=norm_impact(r.get("XVAL02_Impact") or r.get("XVAL01_Impact") or r.get("Hist_Impact")),')
open(p,"w",encoding="utf-8").write(t)
print("patched")
