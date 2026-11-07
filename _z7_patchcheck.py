import io
IMG = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d = open(IMG,"rb").read()
BASE = 0x400000
def hx(va,n):
    o = va-BASE
    return " ".join("%02X"%x for x in d[o:o+n])
print("=== doc section 4, exactly as written ===")
print()
print("[1] at 0x00B9A78E  expect 74 (JE) -> change to 75 (JNE)")
print("    0xB9A788:", hx(0xB9A788, 16))
print("    byte @0xB9A78E =", hx(0xB9A78E,1))
print()
print("[2] at 0x00B9A7C5  expect 75 (JNE) -> change to EB (JMP)")
print("    0xB9A7C0:", hx(0xB9A7C0, 16))
print("    byte @0xB9A7C5 =", hx(0xB9A7C5,1))
print()
print("[3] at 0x00B9A7C7  expect E8 (call) -> change to E9 (jmp 0xB9A7F1)")
print("    byte @0xB9A7C7 =", hx(0xB9A7C7,1))
print("    target calc: E8 rel32 ->", hx(0xB9A7C7,5))
print()
print("[4] at 0x00BA3C1C  expect 75 44 -> NOP NOP")
print("    0xBA3C1A:", hx(0xBA3C1A, 8))
print("    bytes @0xBA3C1C =", hx(0xBA3C1C,2))
