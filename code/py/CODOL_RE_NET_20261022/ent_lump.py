d=open("run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin","rb").read()
B=0x400000
i=d.find(b"mp_firingrange_tire_wall")
print("off",hex(i),"VA",hex(B+i))
s=d[i-400:i+900]
print(bytes(c if 32<=c<127 else 46 for c in s).decode())
