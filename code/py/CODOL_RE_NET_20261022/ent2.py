d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin", "rb").read()
B = 0x400000
for k in [b"mp_firingrange_tire_wall", b"com_folding_table", b"info_player_start_so", b"worldspawn"]:
    n = d.count(k)
    print(k, n)
    if n:
        print("   first VA", hex(B + d.find(k)))
