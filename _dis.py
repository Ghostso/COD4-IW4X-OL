import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMAGE = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000


def main():
    start = int(sys.argv[1], 0)
    end = int(sys.argv[2], 0)
    data = open(IMAGE, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for ins in md.disasm(data[start - BASE:end - BASE], start):
        print(f"{ins.address:08X}  {ins.bytes.hex():<22} {ins.mnemonic} {ins.op_str}")


if __name__ == "__main__":
    main()
