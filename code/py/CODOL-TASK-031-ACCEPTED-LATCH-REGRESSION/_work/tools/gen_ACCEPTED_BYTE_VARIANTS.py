import os, sys
root = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION"
def hx(b): return "".join("%02x"%x for x in b)
FR_NUL=b"mmbook accepted\x00"; TEXT15=b"mmbook accepted"
variants=[("A","current_kit_post023","Current REF_LOBBY_KIT_CAP009 definition (lobby_server.py:385). Inner blob has NO u32 prefix; the 13 08 tag + u32 length are supplied by the envelope.",FR_NUL),
          ("B","olmod_archived_candidate","009 / OLMod DemonwareTests.cpp:1602-1606 archived form. The inner blob carries an ADDITIONAL u32(15) prefix inside the envelope's own length.",(15).to_bytes(4,"little")+TEXT15),
          ("C","pre023_double_prefix","023 pre-fix regression form: an inner u32(16) prefix inside the envelope's own length.",(16).to_bytes(4,"little")+FR_NUL)]
hdr=["variant_id","name","description","inner_len_bytes","inner_hex",
     "envelope_blob_field_len_bytes","envelope_blob_field_hex",
     "full_push_body_len","full_push_body_hex",
     "gate_strncmp_target","gate_arg5_first15_ascii","gate_first15_matches","gate_predicted_result",
     "sender_id","sender_name","encoding_used","evidence","status"]
lines=["\t".join(hdr)]
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT_CAP009")
import codol_crypto as cc
for vid,name,desc,inner in variants:
    body=cc.instant_push_body(0x1122334455667788,"localhost",inner)
    blob_field=bytes([0x13,0x08])+(len(inner)).to_bytes(4,"little")+inner
    f15=inner[:15]; m=(f15==TEXT15)
    ascii15="".join(chr(x) if 32<=x<127 else ("\\x%02x"%x) for x in f15)
    lines.append("\t".join([vid,name,desc,str(len(inner)),hx(inner),
        str(len(blob_field)),hx(blob_field),str(len(body)),hx(body),
        "strncmp(arg5, b'mmbook accepted', 15) @ 0x6326DF ; length push 0xf @ 0x6326D7 ; cmp fn 0xC3C678 (byte-wise)",
        ascii15,"YES" if m else "NO",
        ("PASS" if m else "REACHES_FAIL_EXIT_0x632876")+" (CONDITIONAL: only if arg5 points at the inner-data start; that binding is INFERRED)",
        "0x1122334455667788","localhost",
        "typed envelope (08/0A/10/13 08) + inner bytes as listed",
        "offline: evidence/offline_wirecheck_variants.py ; static: _work/static_verify/dis_632680.py",
        "STATIC_OFFLINE_DETERMINED ; DYNAMIC_INVALID_PRECONDITION (client never entered the lobby)"]) )
open(os.path.join(root,"ACCEPTED_BYTE_VARIANTS.tsv"),"w",encoding="utf-8").write("\n".join(lines)+"\n")
print("\n".join(lines))
