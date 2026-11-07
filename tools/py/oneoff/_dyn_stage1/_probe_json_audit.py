import json
from pathlib import Path
p=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\_dyn_stage1\context_diff_probe\probe.json")
d=json.loads(p.read_text(encoding='utf-8-sig'))
print('started',d.get('started'),'pid',d.get('pid'),'exit',d.get('exit'),'elapsed',d.get('elapsed'))
print('before_pipes_interesting')
for x in d.get('before_pipes',[]):
 if any(k.lower() in x.lower() for k in ['tcls','tgp','ten','xtd','ace','codo','cod','game']): print(x)
print('after_pipes_interesting')
for x in d.get('after_pipes',[]):
 if any(k.lower() in x.lower() for k in ['tcls','tgp','ten','xtd','ace','codo','cod','game']): print(x)
print('new pipes')
before=set(x.lower() for x in d.get('before_pipes',[])); after=set(x.lower() for x in d.get('after_pipes',[]))
for x in sorted(after-before): print(x)
print('samples')
for s in d.get('samples',[]):
 print(s.get('t'),s.get('alive'),s.get('title'),len(s.get('modules',[])),[m for m in s.get('modules',[]) if any(k.lower() in m.lower() for k in ['tenproxy','tersafe','tp3','ace','base','tcls'])])
