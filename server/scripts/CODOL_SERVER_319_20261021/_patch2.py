root = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021"
p = root + r"\src\battle\battle_service.c"
s = open(p, encoding="utf-8").read()

anchor = "        /* ---- World \u5c42: \u89e3\u6790 usercmd \u5e76\u63a8\u8fdb\u73a9\u5bb6(\u5185\u90e8\u79fb\u52a8\u6a21\u578b) ---- */\n        if (len >= 14) {\n"
assert anchor in s, "world block anchor not found"

insert = ("        /* \u53c2\u7167\u5b9e\u73b0: head \u9ad8 3 \u4f4d\u975e 0 \u8868\u793a\u5206\u7247/\u80d6\u5305, \u4e0d\u5f53\u666e\u901a\u8f93\u5165\u5305\u89e3\u6790 */\n"
          "        bool fat = (head & 0xE0000000u) != 0;\n"
          "        if (fat)\n"
          "            CODOL_LOG_INFO(\"[battle] RX_FAT_HEADER head=0x%08X bytes=%d (\u8df3\u8fc7 usercmd \u89e3\u6790)\", head, len);\n\n"
          "        /* ---- World \u5c42: \u89e3\u6790 usercmd \u5e76\u63a8\u8fdb\u73a9\u5bb6(\u5185\u90e8\u79fb\u52a8\u6a21\u578b) ---- */\n"
          "        if (!fat) {\n")
s = s.replace(anchor, insert, 1)

# body hex dump for the first bodies
old_log = '                if (codol_usercmd_parse(body, blen, ack,'
assert old_log in s
add_dump = (
  '                {   /* \u8bca\u65ad: \u524d 16 \u5e27\u539f\u59cb body \u843d\u76d8, \u4f9b\u79bb\u7ebf\u4e0e\u53c2\u7167\u9010\u4f4d\u5bf9\u8d26 */\n'
  '                    static int dbg_body = 0;\n'
  '                    if (dbg_body < 16) {\n'
  '                        char hx[512]; int j, dn = blen < 120 ? blen : 120;\n'
  '                        for (j = 0; j < dn; j++) sprintf(hx + j*2, "%02X", body[j]);\n'
  '                        hx[dn*2] = 0;\n'
  '                        CODOL_LOG_INFO("[world] RX_BODY blen=%d head=0x%08X ack=%u hex=%s", blen, head, ack, hx);\n'
  '                        dbg_body++;\n'
  '                    }\n'
  '                }\n'
)
s = s.replace(old_log, add_dump + old_log, 1)

open(p, "w", encoding="utf-8", newline="\n").write(s)
print("battle_service.c patched")
