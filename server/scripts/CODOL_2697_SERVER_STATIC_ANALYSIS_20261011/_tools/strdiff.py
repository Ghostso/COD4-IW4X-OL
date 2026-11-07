import sys,io
def load(p): return set(x.rstrip('\n') for x in open(p,encoding='utf-8'))
new=load(sys.argv[1]); old=load(sys.argv[2]); c13=load(sys.argv[3])
out=io.open(sys.argv[4],'w',encoding='utf-8',newline='\n')
def w(h,*lines):
    out.write('\n'+h+'\n'+'-'*len(h)+'\n')
    for l in lines: out.write(l+'\n')
w('NEW_ONLY_vs_OLD (count=%d)'%len(new-old), *sorted(new-old))
w('OLD_ONLY_vs_NEW (count=%d)'%len(old-new), *sorted(old-new))
w('NEW_ONLY_vs_1113 (count=%d)'%len(new-c13), *sorted(new-c13))
w('1113_ONLY_vs_NEW (count=%d)'%len(c13-new), *sorted(c13-new))
w('OLD_vs_1113 DIFF (old-only=%d 1113-only=%d)'%(len(old-c13),len(c13-old)), *sorted(set(['OLDONLY '+x for x in old-c13])|set(['1113ONLY '+x for x in c13-old])))
w('SHARED_ALL3 (count=%d)'%len(new&old&c13), *sorted(new&old&c13))
print('new-only',len(new-old),'old-only',len(old-new),'new-only-vs-1113',len(new-c13))
