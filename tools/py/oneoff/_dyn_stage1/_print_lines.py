import sys
p=sys.argv[1]; a=int(sys.argv[2]); b=int(sys.argv[3])
lines=open(p,encoding='utf-16').read().splitlines()
for i in range(max(0,a-1),min(len(lines),b)):
    print(f'{i+1}: {lines[i]}')
