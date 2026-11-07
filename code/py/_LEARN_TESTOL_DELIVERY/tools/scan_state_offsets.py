import struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

MEM = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\CAMPAIGN_FIX_20261024_1839\mem\mem_000.bin"
BASE = 0x400000

def scan_disp(data, md, disp, label, cap=60):
    """搜 mov dword ptr [reg+disp32], imm/reg 与 mov reg,[reg+disp32]"""
    print("=" * 78)
    print("=== disp = 0x%X  %s ===" % (disp, label))
    print("=" * 78)
    pat = struct.pack("<I", disp)
    added = 0
    i = 0
    n = len(data)
    seen = set()
    while i < n - 8 and added < cap:
        # 形式1: 89 /r mod=10 (disp32)  -> 89 8x/9x/Bx  reg
        b = data[i]
        if b in (0x89, 0x8B, 0x8D, 0xC7) and data[i+2:i+6] == pat:
            modrm = data[i+1]
            mod = (modrm >> 6) & 3
            if mod == 2:
                start = i - 4
                if start >= 0:
                    for ins in md.disasm(data[start:i+8], BASE+start):
                        if ins.address <= BASE+i < ins.address+ins.size:
                            key = ins.address
                            if key not in seen:
                                seen.add(key)
                                print("  %08X  %-22s %s %s" % (
                                    ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
                                added += 1
                            break
                        if ins.address > BASE+i:
                            break
        i += 1
    print("  ... total shown = %d\n" % added)

def main():
    data = open(MEM, "rb").read()
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    scan_disp(data, md, 0xC8, "main state", 40)
    scan_disp(data, md, 0x5E8, "LSG state", 40)

if __name__ == "__main__":
    main()
