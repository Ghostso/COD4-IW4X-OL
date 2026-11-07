p = r"restore_iips_contract_001\observer2\AboProbe.cs"
s = open(p, encoding="utf-8").read()

# 0x6D4 -> 0x5E0 (a byte field with a single write and zero reads)
s = s.replace("88 97 D4060000  mov [edi+0x6D4], dl", "88 9F E0050000  mov [edi+0x5E0], bl")
s = s.replace("8A 8F D4060000  mov cl, [edi+0x6D4]", "8A 8F E0050000  mov cl, [edi+0x5E0]")

old = '''                        bool okB = preB == "889577fcffff" && WriteRemoteBytes(
                            proc, 0x00BA3AA3,
                            new byte[] { 0x88, 0x97, 0xD4, 0x06, 0x00, 0x00 });
                        bool okC = preC == "8a8d77fcffff" && WriteRemoteBytes(
                            proc, 0x00BA3AE0,
                            new byte[] { 0x8A, 0x8F, 0xD4, 0x06, 0x00, 0x00 });'''
new = '''                        // obj+0x5E0 is written once (0xBA2950) and read
                        // nowhere in the whole image -> a safe scratch byte.
                        // (obj+0x6D4 was a pointer field; using it crashed
                        //  with 0xC0000005.)
                        bool okB = preB == "889577fcffff" && WriteRemoteBytes(
                            proc, 0x00BA3AA3,
                            new byte[] { 0x88, 0x9F, 0xE0, 0x05, 0x00, 0x00 });
                        bool okC = preC == "8a8d77fcffff" && WriteRemoteBytes(
                            proc, 0x00BA3AE0,
                            new byte[] { 0x8A, 0x8F, 0xE0, 0x05, 0x00, 0x00 });'''
assert old in s
s = s.replace(old, new, 1)

# update the FRAMEBUF sampling: d4 -> 5e0
s = s.replace('" d4=" + V(ReadU32(process, keyObj + 0x6D4))',
              '" d4=" + (ReadU32(process, keyObj + 0x5E0) & 0xFF)')
open(p,"w",encoding="utf-8").write(s)
print("moved stub to obj+0x5E0")
