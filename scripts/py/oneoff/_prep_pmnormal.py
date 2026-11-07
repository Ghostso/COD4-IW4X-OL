import shutil, os

# 1. Restore clean nt10.py
clean_bak = r"REF_LOBBY_KIT\nt10.py.bak_before_native_inject"
target_nt10 = r"REF_LOBBY_KIT\nt10.py"
shutil.copy2(clean_bak, target_nt10)
print(f"Restored clean {target_nt10} from {clean_bak}")

# 2. Re-enable firingrange-battle.enabled
flag_bak = r"REF_LOBBY_KIT\firingrange-battle.enabled.bak"
flag_target = r"REF_LOBBY_KIT\firingrange-battle.enabled"
if os.path.exists(flag_bak):
    if os.path.exists(flag_target):
        os.remove(flag_target)
    os.rename(flag_bak, flag_target)
    print("Re-enabled firingrange-battle.enabled!")
elif os.path.exists(flag_target):
    print("firingrange-battle.enabled already active.")
else:
    with open(flag_target, "w") as f:
        f.write("1\n")
    print("Created firingrange-battle.enabled!")

# 3. Clean old logs
for p in [r"CODOL-Combat-Server-v0.1\logs\firingrange_live.log"]:
    if os.path.exists(p):
        try: os.remove(p)
        except: pass
print("Cleaned firingrange_live.log!")
