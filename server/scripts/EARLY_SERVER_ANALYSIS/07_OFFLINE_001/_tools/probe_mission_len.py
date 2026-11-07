import sys, hashlib
kit = r"D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT"
sys.path.insert(0, kit)
import codol_crypto as cc
def build(layout67, mapname):
    # replicate BuildMissionSessionObject length math via reference default path
    return None
nm_default = cc.build_mission_session_object(False, "coop_training_mp_cargoship")
print("NM default map len:", len(nm_default))
# The exporter passes cfg.SessionMapName = mp_crash_tropical (17 chars) instead of 26
print("map len diff:", len("coop_training_mp_cargoship") - len("mp_crash_tropical"))
print("predicted exported len:", len(nm_default) - (len("coop_training_mp_cargoship") - len("mp_crash_tropical")))
