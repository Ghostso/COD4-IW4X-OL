s=open(r'CODOL_SERVER_319_20261021\HANDOFF_20261022_PAUSE.md',encoding='utf-8',errors='replace').read().splitlines()
print(len(s))
for i in range(299, min(415,len(s))): print(i+1, s[i][:220])
