#!/usr/bin/env python3
"""检查所有关键状态量在这份 dump 里的实际值，判断抓取时机。"""
import struct

DUMP = (r"CODOL_LOCAL_ENGINE_CHAIN_20261019\logs"
        r"\ROUND2_STATIC_DUMP_20261019_203103\client_runtime.bin")
BASE = 0x400000

VARS = {
    "0xe59d20 应用模式": 0x0e59d20,
    "0x849ba34 大厅状态机": 0x0849ba34,
    "0x849ba30 镜像": 0x0849ba30,
    "0x84aba50 登录阶段": 0x084aba50,
    "0x84aba54 旧登录阶段": 0x084aba54,
    "0x849ba3d 标志B": 0x0849ba3d,
    "0x849ba28 计数": 0x0849ba28,
    "0x8269774 连接单例": 0x08269774,
    "0x82e13fc 房间对象": 0x082e13fc,
    "0x82e1400": 0x082e1400,
    "0x82e13f8 计数": 0x082e13f8,
    "0x849b874 对象": 0x0849b874,
    "0x849ba50": 0x0849ba50,
    "0x84aba50相关0x1cd1780": 0x01cd1780,
}


def main():
    b = open(DUMP, "rb").read()
    print("%-28s %-12s %s" % ("变量", "值", "地址"))
    for name, va in VARS.items():
        o = va - BASE
        if 0 <= o < len(b) - 4:
            v = struct.unpack_from("<I", b, o)[0]
            print("%-28s %#-12x %#x" % (name, v, va))
        else:
            print("%-28s %-12s %#x" % (name, "越界", va))


if __name__ == "__main__":
    main()
