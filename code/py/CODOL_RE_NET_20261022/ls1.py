d=open("run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin","rb").read()
for k in [b"listen", b"dedicated", b"sv_", b"SV_", b"maxclients", b"hostname"]:
    print(k, d.count(k))
