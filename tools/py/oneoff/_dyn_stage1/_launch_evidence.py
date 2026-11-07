import os,re,time,sys
roots=[r'WeGame',r'COD OL']
min_mtime=time.mktime(time.strptime('2026-09-13 18:40:00','%Y-%m-%d %H:%M:%S'))
terms=re.compile(r'(?i)(codoMP_client_shipRetail|StartFor\s*=?\s*29|game_id[^\r\n]{0,20}29|gameID[:=\s]+29|LaunchProcess|CreateProcess|tcls_core|TCLS_SHAREDMEMEMORY|TCLS_TASMEMORY|IsSubWegameProcess|GetWegameProcessCount|SetCurrentStage|GetCurrentStage|RecvLoginInfo|login ok|StartNewMainProcess|WeGameLauncher|tgp_daemon|TCLSHost|Client\.exe|launch tcls|wegame exit|exit_app|process exit)')
seen=set(); hits=[]; files=[]
for root in roots:
  for r,d,fs in os.walk(root):
    for f in fs:
      p=os.path.join(r,f)
      if os.path.splitext(f)[1].lower() not in {'.log','.txt','.ini','.info','.xml','.json','.cfg'}: continue
      try:
        st=os.stat(p)
        if st.st_mtime < min_mtime: continue
        b=open(p,'rb').read()
      except Exception: continue
      files.append((st.st_mtime,st.st_size,p))
      text=b.decode('utf-8-sig',errors='replace')
      if '\ufffd' in text:
        text=b.decode('gb18030',errors='replace')
      lines=text.splitlines()
      for i,line in enumerate(lines,1):
        if terms.search(line):
          key=(p,i,line)
          if key not in seen:
            seen.add(key); hits.append((st.st_mtime,p,i,line))
with open(r'_dyn_stage1\_launch_evidence.txt','w',encoding='utf-8') as out:
  out.write('FILES\n')
  for t,s,p in sorted(files): out.write(f'{time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(t))}\t{s}\t{p}\n')
  out.write('\nHITS\n')
  for t,p,i,line in sorted(hits): out.write(f'{p}:{i}:{line}\n')
print('files',len(files),'hits',len(hits))
for t,p,i,line in sorted(hits):
  print(f'{p}:{i}:{line[:700]}'.encode('ascii','backslashreplace').decode('ascii'))
