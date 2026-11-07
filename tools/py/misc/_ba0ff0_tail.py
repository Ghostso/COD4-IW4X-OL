import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL")
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
IMAGE = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
data = open(IMAGE, "rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
for ins in md.disasm(data[0xBA11F0-BASE:0xBA12C0-BASE], 0xBA11F0):
    print(f"{ins.address:08X}  {ins.bytes.hex():<20} {ins.mnemonic} {ins.op_str}")
