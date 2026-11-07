import struct
p=r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); BASE=0x400000
want=[b'gamestateupdate',b'CA_GAMESTATE',b'northyaw',b'netchan',b'NET_OutOfBand',b'clc_',b'svc_',b'CL_Parse',b'CL_Send',b'Bad packet',b'reliable',b'configstring']
for w in want:
    print('\n==',w.decode())
    i=0; n=0
    while True:
        i=d.find(w,i)
        if i<0: break
        va=BASE+i
        s=i
        while s>0 and 32<=d[s-1]<127: s-=1
        e=d.find(b'\0',i)
        txt=d[s:e][:120]
        print('  %#010x %r'%(va,txt))
        i+=1; n+=1
        if n>=12: break
