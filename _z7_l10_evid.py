import sys, os, struct, zlib, importlib.util, collections, math, json, hashlib
sys.path.insert(0, r"_PLAINTEXT_PROJECT\tools")
spec = importlib.util.spec_from_file_location("cod", r"_PLAINTEXT_PROJECT\tools\codol_ff_decrypt.py")
cod = importlib.util.module_from_spec(spec); spec.loader.exec_module(cod)

def H(x):
    c=collections.Counter(x); n=len(x)
    return -sum((v/n)*math.log2(v/n) for v in c.values()) if n else 0.0

names=["code_post_gfx_default_mp.ff","code_post_gfx_mp.ff","code_pre_gfx_mp.ff",
       "common_mp_reload.ff","development_mp.ff","localized_code_post_gfx_mp.ff",
       "localized_code_pre_gfx_mp.ff","localized_ui_mp.ff","mp_playlists.ff","ui_mp.ff"]

evidence={"generated":"2026-10-02","method":"layer-1 only, recomputed from raw bytes","files":[]}
print("%-32s %10s %10s %8s %8s  %s" % ("file","cipher","plain","H(body)","zeros%","zone_name"))
for nm in names:
    i = cod.decrypt_layer1(os.path.join("COD OL","main",nm))
    p = i["plain"]; b = p[0x14C:]
    hdr = cod.parse_zone_header(p)
    h = H(b[:1<<20])
    z = 100*p.count(0)/len(p)
    print("%-32s %10d %10d %8.4f %8.3f  %s" % (nm, i["cipher_size"], i["plain_size"], h, z, hdr.get("zone_name","?")))
    evidence["files"].append({
        "file": nm,
        "cipher_size": i["cipher_size"],
        "plain_size": i["plain_size"],
        "sha256_layer1": hashlib.sha256(p).hexdigest(),
        "layer1_magic": p[:8].decode("ascii","replace"),
        "inner_u32_at_8": struct.unpack_from("<I",p,8)[0],
        "zone_name": hdr.get("zone_name"),
        "zone_name_offset": hex(0x12C),
        "body_offset": hex(0x14C),
        "body_len": len(b),
        "body_entropy_1MB": round(h,6),
        "body_u32_0": struct.unpack_from("<I",b,0)[0],
        "aes_key": i["key"].hex(),
        "iv": i["iv"].hex(),
    })

os.makedirs(r"_PLAINTEXT_PROJECT\evidence", exist_ok=True)
with open(r"_PLAINTEXT_PROJECT\evidence\layer1_evidence.json","w",encoding="utf-8") as f:
    json.dump(evidence, f, indent=1, ensure_ascii=False)
print("\nwrote _PLAINTEXT_PROJECT\\evidence\\layer1_evidence.json")
