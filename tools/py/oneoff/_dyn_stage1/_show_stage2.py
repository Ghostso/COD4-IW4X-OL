from pathlib import Path
import sys
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\_dyn_stage1\stage2_focus.txt')
s=p.read_text(encoding='utf-8')
mode=sys.argv[1] if len(sys.argv)>1 else 'all'
if mode=='head':
    print(s[:24000])
elif mode=='slice':
    a=s.find(sys.argv[2]); b=s.find(sys.argv[3],a+1) if len(sys.argv)>3 else -1
    print(s[a:b if b>=0 else None])
elif mode=='lines':
    for line in s.splitlines():
        if any(k.lower() in line.lower() for k in sys.argv[2:]):
            print(line)
else:
    print(s)
