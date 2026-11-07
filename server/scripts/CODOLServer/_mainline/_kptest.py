import sys, importlib.util, json, glob
from Crypto.Cipher import AES
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)
d="CODOLServer\\logs\\E57A5C_20261001_220416_a2\\plain.jsonl"
buf=bytearray()
for line in open(d,encoding="utf-8"):
    try: ev=json.loads(line)
    except Exception: continue
    if ev.get("event")=="hold_recv" and ev.get("len",0)>10:
        buf += bytes.fromhex(ev["hex"])
buf=bytes(buf); off=0; frames=[]
while off+10<=len(buf):
    fl=int.from_bytes(buf[off:off+4],"little")
    if fl<10 or off+4+fl>len(buf): break
    if buf[off+5]==0x85: frames.append(buf[off:off+4+fl])
    off+=4+fl
f=frames[0]
# known plaintext for seq=1: u32 340 | 86 47 03 04 13 08 10 | "CODOL-LOCAL-0001"
kp = b"CODOL-LOCAL-0001"
ct = f[26:-8]
# "CODOL-LOCAL-0001" begins at plaintext offset 4+7 = 11
# find its block offset
pt_off = 11
blk = pt_off // 16
inblk = pt_off % 16
target = ct[blk*16:(blk+1)*16]
print("known plaintext:", kp, "at pt offset", pt_off, "block", blk, "inblk", inblk)
# AES key schedule: K_prev = D(target) xor C_prev xor P ; brute force one key? cannot.
# Instead: verify by trying candidate keys and checking this known plaintext
tx=bytes.fromhex("b74faff5c1d503a13545d5372efe8851639555e7")
rx=bytes.fromhex("266a380d05cb3e730b1bb00eca691820cebc9a0f")
cands={}
for kn,k20 in (("tx",tx),("rx",rx)):
    for cn,cf in (("c02a0",lp.codec_02a0),("c0420",lp.codec_0420)):
        d20=cf(k20)
        for sl,s in (("0:16",d20[:16]),("[4:20]",d20[4:20])):
            cands[f"{kn}/{cn}{sl}"]=s
for name,k in cands.items():
    pt=AES.new(k,AES.MODE_CBC,f[10:26]).decrypt(ct[:len(ct)//16*16])
    if kp in pt:
        print("  ★ CONTAINS KNOWN PLAINTEXT:", name)
    else:
        print("   no:", name, pt[:16].hex())
