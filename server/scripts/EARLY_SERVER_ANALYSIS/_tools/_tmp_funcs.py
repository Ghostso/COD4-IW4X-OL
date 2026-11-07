import os, re, sys, json
root = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\src"
targets = [
 r"sys_main.c", r"sv_main.c", r"sv_init_mp.cpp", r"sv_client.c", r"sv_snapshot.c",
 r"sv_game.c", r"netchan.c", r"net_game.c", r"msg.c", r"common.c",
 r"codol\net\codol_wire.c", r"codol\net\codol_connect.c", r"codol\net\codol_handshake.c",
 r"codol\net\codol_association.c", r"codol\net\codol_network.c", r"codol\net\codol_netchan.c",
 r"codol\net\codol_msg.c", r"codol\net\codol_admission.c", r"codol\net\codol_ecdh.c",
 r"codol\net\codol_crypto.c", r"codol\net\codol_client_command.c", r"codol\net\codol_usercmd_queue.c",
 r"codol\net\codol_pure.c", r"codol\net\codol_match_status.c",
]
pat = re.compile(r'^[A-Za-z_][\w\s\*&:<>,]*?\b(\w+)\s*\([^;]*\)\s*\{?\s*$')
for rel in targets:
    p = os.path.join(root, rel)
    if not os.path.exists(p):
        print("MISSING", rel); continue
    print("="*70); print("FILE", rel)
    with open(p, 'r', encoding='utf-8', errors='replace') as f:
        for i, line in enumerate(f, 1):
            s = line.rstrip()
            # function-ish: line has '(' and ')' and no ';' at end and no '=' 
            if '(' in s and ')' in s and not s.lstrip().startswith(('//','*','#')):
                stripped = s.strip()
                if stripped.endswith(')') or stripped.endswith('{') or stripped.endswith(') {'):
                    if ';' not in stripped and '=' not in stripped.split('(')[0]:
                        # crude: identifier before first (
                        m = re.search(r'(\w+)\s*\(', stripped)
                        if m and not stripped.startswith(('if','for','while','switch','return','else')):
                            print(f"{i:5d}  {stripped}")
