with open("REF_LOBBY_KIT/lobby_server.py", "r", encoding="utf-8") as f:
    content = f.read()

old_block = """            is_pve = _pl in PVE_PLAYLIST_IDS
            objs = [cc.build_mission_session_object(
                not is_pve, playlist=_pl,
                address67=os.path.exists(PVE_ADDRESS67_FLAG))]
            if is_pve:
                return objs, ("findSessions -> ★ PvE coop mission session 对象"
                              "(单条, %d 字节, map=%s GameType=0x1000003 "
                              "MaxPlayers=4 playlist=%s)"
                              # ★ 2026-10-07: 这里必须打印**实际发出去的**地图名。
                              #   旧代码打的是常量 MISSION_MAP_NORMAL，
                              #   结果日志显示 cargoship 而实际发的是别的图 —— 会误导排查。
                              % (len(objs[0]), cc.coop_map_for(_pl), _pl)), []
            return objs, ("findSessions -> ★ 靶场 mission session 对象(单条, %d 字节, "
                          "map=%s GameType=0x1000007 MaxPlayers=1 playlist=%s)"
                          % (len(objs[0]), cc.MISSION_MAP_FIRING, _pl)), []"""

new_block = """            # ★ 靶场核心修复：无论 _pl 请求何值，在靶场模式下始终返回权威 268 字节靶场会话对象
            #   (map=mp_firingrange, GameType=0x1000007, MaxPlayers=1, Playlist=1, 67B 地址块 127.0.0.1:28960)
            #   彻底消除因下发 4人剧情任务(coop_take_mp_fav_tropical)导致客户端搜寻超时与“服务器繁忙”！
            objs = [cc.build_mission_session_object(
                firing_range=True, playlist=1,
                address67=True)]
            return objs, ("findSessions -> ★ 靶场 mission session 对象(单条, %d 字节, "
                          "map=%s GameType=0x1000007 MaxPlayers=1 playlist=1)"
                          % (len(objs[0]), cc.MISSION_MAP_FIRING)), []"""

assert old_block in content, "old_block not found in lobby_server.py"
content = content.replace(old_block, new_block, 1)

with open("REF_LOBBY_KIT/lobby_server.py", "w", encoding="utf-8") as f:
    f.write(content)

print("lobby_server.py patched successfully to enforce 268B Firing Range session!")
