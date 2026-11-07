# -*- coding: utf-8 -*-
"""自包含: TAS 注入 + 早期枚举 + PEB 模块链 + 命名/模块:RVA 两种 hook + 磁盘快照

为什么要独立文件: nt8.py 在本机被反复回滚成半成品(改 A 丢 B), 导致关键函数在运行时不存在。

关键设计
  1. 模块枚举必须"早"(t≈0.2s): 晚了会被 ACE 封掉(toolhelp 返回空)。
  2. hook 安装要"晚"(默认 delay 2.5s): 太早会撞上 TP3 在 t≈2s 的 ws2_32 完整性检查 -> 游戏 0xC0000005。
     两者解耦: 枚举在前, 装 hook 在后。
  3. 但 TenProxy.dll 要到 t≈5s 才被加载, 所以它的基址要在那时用"PEB 模块链"现查
     (句柄用 t≈0 打开的那个, 它一直可用)。
  4. 命中缓冲每 0.4s 落盘一次, 游戏提前退出也不丢数据。

用法:
  python nt10.py --secs 120 --delay 0 --out n10n.txt ^
      --apis OpenFileMappingW,OpenFileMappingA,CreateFileMappingW,CreateFileMappingA,^
MapViewOfFile,connect,sendto,getaddrinfo,GetAddrInfoW,gethostbyname,z1,z2,z3

  补丁规格 / TAS 规格 / 迟到 hook 目标 都从同目录的 patch_spec.txt、tas_spec.txt 读
  (命令行开关会被环境回滚, 文件不会)。--apis 里的 zN 只是占位, 用来把代码洞/计数器槽位
  预留出来(迟到 hook 用), 不会真的去装 hook。要手动钉某个 tenproxy 函数就写
  --apis ...,@tenproxy.dll:0x6BD0
"""
import argparse
import ctypes
import os
import re
import struct
import subprocess
import sys
import threading
import time
from ctypes import wintypes

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROC_ALL = 0x0008 | 0x0010 | 0x0020 | 0x0400
MEM_COMMIT_RESERVE = 0x3000
PAGE_EXECUTE_READWRITE = 0x40
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
JNE_ADDR = 0x0077F6EF

RING = 1024
REC = 72                      # 调用者4 + 参数4 + 内容16 + 调用点机器码48
SLOT = 0x20000
CODE_OFF = 24
CODE_LEN = 48
BUF_LEN = 4 + RING * REC

k32.OpenProcess.restype = wintypes.HANDLE
k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
k32.VirtualAllocEx.restype = ctypes.c_void_p
k32.VirtualAllocEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                               wintypes.DWORD, wintypes.DWORD]
k32.CreateFileMappingW.restype = wintypes.HANDLE
k32.CreateFileMappingW.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                                   wintypes.DWORD, wintypes.DWORD, wintypes.LPCWSTR]
k32.MapViewOfFile.restype = ctypes.c_void_p
k32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
                              wintypes.DWORD, ctypes.c_size_t]
k32.CreateMutexW.restype = wintypes.HANDLE
k32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
for _f in ("WriteProcessMemory", "ReadProcessMemory"):
    getattr(k32, _f).argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                 ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]

MD = Cs(CS_ARCH_X86, CS_MODE_32)
REL_BAD = ("call", "jmp", "ret", "retn", "loop", "loope", "loopne", "loopd")

TRAMP_APIS = {
    "connect": (8, False, "ptr"), "WSAConnect": (8, False, "ptr"),
    "sendto": (0x14, False, "ptr"), "WSASendTo": (0x18, False, "ptr"),
    "bind": (8, False, "ptr"), "send": (8, False, "ptr"),
    "getaddrinfo": (4, False, "ptr"), "GetAddrInfoW": (4, True, "ptr"),
    "gethostbyname": (4, False, "ptr"),
    "socket": (0, False, "args"), "WSASocketW": (0, False, "args"),
    "recv": (0, False, "args"), "recvfrom": (0, False, "args"),
    "WSARecv": (0, False, "args"), "WSARecvFrom": (0, False, "args"),
    # 共享内存(TAS): 用来确认游戏是否在等 TCLS 递交的票据/服务器地址
    # (E:\1\nt8.py 里的原样三项 + A 版两项, nt10 之前漏了这整块, 导致 "跳过(不支持)")
    "OpenFileMappingW": (0xC, True, "ptr"),
    "CreateFileMappingW": (0x18, True, "ptr"),
    "OpenFileMappingA": (0xC, False, "ptr"),
    "CreateFileMappingA": (0x18, False, "ptr"),
    "MapViewOfFile": (0, False, "args"),
    # kernel32 / user32 (最小改动: 只加常用项, 参数统一用 args 模式)
    "CreateProcessW": (0, False, "args"), "CreateProcessA": (0, False, "args"),
    "WinExec": (0, False, "args"),
    "RegisterWindowMessageW": (4, True, "ptr"), "RegisterWindowMessageA": (4, False, "ptr"),
    "PostMessageW": (0xC, False, "args"), "PostMessageA": (0xC, False, "args"),
    "SendMessageW": (0xC, False, "args"), "SendMessageA": (0xC, False, "args"),
    # WinHttp: 大厅/上报的 HTTP 请求全走这里(ws2_32 的 connect 看不到)。
    #   WinHttpConnect(hSession, pswzServerName[W], nServerPort, dwReserved)
    #   WinHttpOpenRequest(hConn, pwszVerb, pwszObjectName[W], pwszVersion, ...)
    # 记下 (serverName, port) 和 (path) 就能拼出游戏访问的完整 URL。
    "WinHttpConnect": (8, True, "ptr"),
    "WinHttpOpenRequest": (0xC, True, "ptr"),
    "WinHttpSendRequest": (0, False, "args"),
    "WinHttpReceiveResponse": (0, False, "args"),
}
K32_APIS = {"CreateProcessW", "CreateProcessA", "WinExec"}
# E:\1\nt8.py 的做法: 这几个在 kernel32 里是真函数(不是转发), 直接用本机 RVA + kernel32 基址定位,
# 不走 ws2_32 导出扫描(那条路在 delay=0 / 枚举为空时会整个落空)
_K32 = {"OpenFileMappingW": 0x221A0, "CreateFileMappingW": 0x20740,
        "OpenFileMappingA": 0x18780, "CreateFileMappingA": 0x116B0,
        "MapViewOfFile": 0x1F830}
U32_APIS = {"RegisterWindowMessageW", "RegisterWindowMessageA",
            "PostMessageW", "PostMessageA", "SendMessageW", "SendMessageA"}
SOCK_APIS = ("connect", "WSAConnect", "sendto", "WSASendTo", "bind")
WHTTP_APIS = ("WinHttpConnect", "WinHttpOpenRequest",
              "WinHttpSendRequest", "WinHttpReceiveResponse")
# 这些 hook 的参数是"指向名字/字符串的指针": 记录内容区只有 16 字节, 装不下
# "stun1-tub.codol.qq.com" 这种域名 —— 所以 timeline 里还要顺着指针去把整串抄回来。
# (CODOL 的大厅是 Demonware: exe 里有 DW_DNS_ERROR/DW_LOBBY_ERROR/DW_LOBBY_CONNECTED
#  这一整套状态 + g_dwConfigVersion, 所以"无法连接大厅服务!"很可能卡在域名解析/连 DW 端点)
STR_HOOKS = {"gethostbyname", "getaddrinfo", "GetAddrInfoW",
             "OpenFileMappingW", "OpenFileMappingA",
             "CreateFileMappingW", "CreateFileMappingA",
             "WinHttpConnect", "WinHttpOpenRequest"}


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("th32ModuleID", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("GlblcntUsage", wintypes.DWORD),
                ("ProccntUsage", wintypes.DWORD), ("modBaseAddr", ctypes.c_void_p),
                ("modBaseSize", wintypes.DWORD), ("hModule", wintypes.HMODULE),
                ("szModule", ctypes.c_char * 256), ("szExePath", ctypes.c_char * 260)]


def rpm(h, addr, size):
    b = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(h, ctypes.c_void_p(addr), b, size, ctypes.byref(got)):
        return b.raw[:got.value]
    return b""


def wpm(h, addr, data):
    n = ctypes.c_size_t(0)
    return (bool(k32.WriteProcessMemory(h, ctypes.c_void_p(addr), data, len(data),
                                        ctypes.byref(n))) and n.value == len(data))


def mods_toolhelp(pid):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    out = []
    if not snap or snap == -1:
        return out
    me = MODULEENTRY32()
    me.dwSize = ctypes.sizeof(MODULEENTRY32)
    if k32.Module32First(snap, ctypes.byref(me)):
        while True:
            out.append((me.szModule.decode(errors="replace"), me.modBaseAddr or 0,
                        me.modBaseSize))
            if not k32.Module32Next(snap, ctypes.byref(me)):
                break
    k32.CloseHandle(snap)
    return out


def mods_peb(h):
    """直接走 PEB 的模块链(绕开被 ACE 封掉的 toolhelp 枚举)"""
    try:
        ntdll = ctypes.WinDLL("ntdll")
        # 我们是 64 位 Python: 该 API 按【调用方】位宽返回结构, PebBaseAddress 在 +8
        # (目标进程里再去用 32 位的 PEB/链表偏移)
        pbi = (ctypes.c_uint64 * 6)()
        ret = ctypes.c_uint32(0)
        if ntdll.NtQueryInformationProcess(h, 0, ctypes.byref(pbi),
                                           ctypes.sizeof(pbi), ctypes.byref(ret)) != 0:
            return []
        peb = pbi[1]
        if not peb:
            return []
        ldr = struct.unpack("<I", rpm(h, peb + 0x0C, 4))[0]
        if not ldr:
            return []
        head = ldr + 0x0C
        cur = struct.unpack("<I", rpm(h, head, 4))[0]
        out = []
        while cur and cur != head and len(out) < 400:
            b = rpm(h, cur + 0x18, 8)
            if len(b) < 8:
                break
            base, size = struct.unpack("<II", b)
            nm = ""
            nb = rpm(h, cur + 0x2C, 8)
            if len(nb) == 8:
                blen, _mx, bbuf = struct.unpack("<HHI", nb)
                if bbuf and 0 < blen < 520:
                    nm = rpm(h, bbuf, blen).decode("utf-16le", "replace")
            out.append((nm, base, size))
            cur = struct.unpack("<I", rpm(h, cur, 4))[0]
        return out
    except Exception:
        return []


def mods_any(pid, h):
    ml = mods_toolhelp(pid)
    if any(n.lower().startswith("ws2_32") for n, b, s in ml):
        return ml, "toolhelp"
    ml2 = mods_peb(h)
    if ml2:
        return ml2, "peb"
    return ml, "toolhelp"


def export_rva(dll, names):
    pe = pefile.PE(dll, fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
    want = {n.lower() for n in names}
    got = {}
    for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        if e.name and e.name.decode("latin1").lower() in want:
            got[e.name.decode("latin1")] = e.address
    return got


def pick_stolen(orig, tgt):
    stolen, n = b"", 0
    for ins in MD.disasm(orig, tgt):
        if ins.mnemonic in REL_BAD or ins.mnemonic.startswith("j"):
            return None, 0
        if "eip" in ins.op_str or "rip" in ins.op_str:
            return None, 0
        stolen += orig[n:n + ins.size]
        n += ins.size
        if n >= 5:
            return stolen, n
    return None, 0


def build_tramp(count_addr, arr_addr, stolen, back_addr, cave_addr, str_off, mode="ptr",
                trace_pending=None, trace_work=None):
    """完整保留 EAX/ECX/EDX/ESI(游戏内部函数大量 thiscall, ECX 就是 this)

    mode="args" : 记录 4 个参数(ws2_32 那批, 参数直接压栈)
    mode="ptr"  : 记录 str_off 位置的指针指向的内容(字符串类)
    mode="decl" : 在 "args" 基础上, 额外把 arg2 处的 pLen 指针解引用, 存进记录内容区
                  第 4 个 DWORD(= 记录 +0x14)。用于 3 参数的 blob 取值函数
                  (tag, dst, pLen): 调用方 pLen 初值 = 它自己声明的缓冲区容量,
                  runtime 会把它改成"实际写入长度" —— 抢在函数执行前记下来,
                  就能拿到每个 tag 的真实期望尺寸。dst==0 的那次(查询长度模式)
                  pLen 里没有意义, 由导出段靠 dst==0 自行区分。
    """
    c = bytearray()
    c += b"\xA1" + struct.pack("<I", count_addr)
    c += b"\x3D" + struct.pack("<I", RING - 1)
    c += b"\x0F\x83" + b"\x00\x00\x00\x00"
    c += b"\x6B\xC8" + bytes([REC])
    c += b"\x81\xC1" + struct.pack("<I", arr_addr)
    c += b"\x8B\x14\x24"
    c += b"\x89\x11"
    c += b"\x8B\x54\x24" + bytes([str_off or 4])
    c += b"\x89\x51\x04"
    c += b"\x50\x51\x52\x56"
    c += b"\x8B\x54\x24\x10"
    c += b"\x83\xEA\x20"
    for k in range(CODE_LEN // 4):
        src, dst = k * 4, CODE_OFF + k * 4
        c += (b"\x8B\x72" + bytes([src])) if src else b"\x8B\x32"
        c += b"\x89\x71" + bytes([dst])
    if mode == "args":
        for k in range(4):
            c += b"\x8B\x54\x24" + bytes([0x14 + k * 4])
            c += b"\x89\x51" + bytes([8 + k * 4])
    elif mode == "decl":
        # 先按 "args" 记 4 个参数, 再把第 4 个槽改写成"调用方声明的缓冲区容量"
        # (从 dst / pLen 双非空才解引用, 避免把栈上垃圾当指针读)
        for k in range(4):
            c += b"\x8B\x54\x24" + bytes([0x14 + k * 4])
            c += b"\x89\x51" + bytes([8 + k * 4])
        c += b"\x31\xC0"                      # xor eax,eax
        c += b"\x89\x41\x14"                  # mov [ecx+0x14], eax   先清零
        c += b"\x8B\x51\x04"                  # mov edx, [ecx+4]  = arg2 = dst
        c += b"\x85\xD2"                      # test edx, edx
        jz0 = len(c) + 1
        c += b"\x74\x00"                      # je done            (dst==0 -> 保持 0)
        c += b"\x8B\x51\x0C"                  # mov edx, [ecx+0x0C] = arg3 = pLen
        c += b"\x85\xD2"                      # test edx, edx
        jz1 = len(c) + 1
        c += b"\x74\x00"                      # je done            (pLen==0 -> 保持 0)
        c += b"\x8B\x32"                      # mov esi, [edx]
        c += b"\x89\x71\x14"                  # mov [ecx+0x14], esi
        c[jz1] = len(c) - (jz1 + 1)
        c[jz0] = len(c) - (jz0 + 1)
    else:
        c += b"\x8B\x51\x04"
        c += b"\x85\xD2"
        je = len(c) + 1
        c += b"\x74\x00"
        c += b"\x8B\x32"
        c += b"\x89\x71\x08"
        c += b"\x8B\x72\x04"
        c += b"\x89\x71\x0C"
        c += b"\x8B\x72\x08"
        c += b"\x89\x71\x10"
        c += b"\x8B\x72\x0C"
        c += b"\x89\x71\x14"
        c[je] = len(c) - (je + 1)
    c += b"\x5E\x5A\x59\x58"
    c += b"\xFF\x05" + struct.pack("<I", count_addr)
    done = len(c)
    c[12:16] = struct.pack("<i", done - 16)
    # ★ 路线A(2026-10-04): 借这个跳板执行客户端原生 trace —— 跳板本来就跑在**游戏线程**里,
    #   于是完全绕开 TP3 对 "外部 CreateRemoteThread" 的拦截（实测 84 次里只有 1 次能跑起来）。
    #   守卫: 只有 Python 把 pending 置 1 才调用; 桩入口立刻清零(防重入)。
    if trace_pending and trace_work:
        c += b"\x9C"                                       # pushfd
        c += b"\x60"                                       # pushad
        c += b"\xA1" + struct.pack("<I", trace_pending)    # mov eax, <pending>
        c += b"\x80\x38\x00"                               # cmp byte [eax], 0
        je_pos = len(c) + 1
        c += b"\x74\x00"                                   # je skip
        call_pos = len(c) + 1
        c += b"\xE8\x00\x00\x00\x00"                       # call <trace_work> (rel32 稍后填)
        # call_pos = E8 的偏移+1(即 rel 字段起点); 下一条指令 = cave + (call_pos-1) + 5
        c[call_pos:call_pos + 4] = struct.pack(
            "<i", trace_work - (cave_addr + call_pos + 4))
        c[je_pos] = len(c) - (je_pos + 1)
        c += b"\x61"                                       # popad
        c += b"\x9D"                                       # popfd
    c += stolen
    jmp_from = cave_addr + len(c) + 5
    c += b"\xE9" + struct.pack("<i", back_addr - jmp_from)
    return bytes(c)


def describe_sockaddr(d, rec):
    """从记录内容区(rec+8, 函数入口瞬间抓的 8 字节)解析 sockaddr_in。
    旧实现顺着 rec+4 指针现读 —— 函数返回后调用方栈已被覆盖, 所以全是乱码族号。
    记录内容区是跳板在入口瞬间复制的原始 sockaddr 前 16 字节, 永远有效。"""
    if rec + 16 > len(d):
        return ""
    fam = struct.unpack_from("<H", d, rec + 8)[0]
    if fam != 2:
        return "sockaddr(族=%d) 8字节=%s" % (fam, d[rec + 8:rec + 16].hex(" "))
    port = struct.unpack_from(">H", d, rec + 10)[0]
    ip = ".".join(str(b) for b in d[rec + 12:rec + 16])
    return "%s:%d" % (ip, port)


def follow_str(h, d, rec, wide, cap=96):
    """记录里只有 16 字节内容, 装不下域名 —— 顺着 argv 里的指针把整串抄回来。
    小心: UTF-16 域名按 2 倍长度读容易跨到不可读页(读失败就白读), 所以逐个长度退让。"""
    argp = struct.unpack_from("<I", d, rec + 4)[0]
    if not argp:
        return ""
    for n in (cap * (2 if wide else 1), cap, 48, 32, 16):
        try:
            raw = rpm(h, argp, n)
        except Exception:
            raw = b""
        if raw:
            return raw.decode("utf-16le" if wide else "gbk",
                              "replace").split("\x00")[0]
    return ""


def decode_cmdline(h, addr):
    """读取 CreateProcessW 的 lpCommandLine (LPWSTR)，容错版"""
    try:
        raw = rpm(h, addr, 4)
        if len(raw) < 4:
            return "<short:%d:%s>" % (len(raw), raw.hex(" "))
        ptr = struct.unpack("<I", raw)[0]
        if not ptr:
            return "<NULL>"
        raw2 = rpm(h, ptr, 1024)
        if not raw2:
            return "<empty_ptr:0x%X>" % ptr
        text = raw2.decode("utf-16le", "replace").split("\x00")[0]
        return text if text else "<empty>"
    except Exception as e:
        return "<err:%r>" % (e,)


def build_tas_image(host, port, name):
    """TCLS_SHAREDMEMEMORY 镜像: 魔数0x40 + table[key-1]=偏移 + (len,value)

    解法来源(静态, 已逐条对齐): TenProxy 0x6BD0 = pad LoginInfo; 0x6310-0x6680 =
    把表里的值复制进 CTclsProxy 对象字段的一段。两处合起来就是下面这张表。
      vtable 0x24 = (tag, dst)            2 参, 只认 len==4 的 DWORD
      vtable 0x28 = (tag, dst, &len)      3 参, blob; dst==0 时只回填 *len
      vtable 0x2c = 同 0x28
      vtable 0x20 = 也是 2 参 DWORD(0x7CA0)
    全局(不带序号, key 就是 tag):
      1 -> +0x004 DWORD    2 -> +0x010 DWORD   6 -> +0x1c4 DWORD
      7 -> +0x1c8 0x200    3 -> +0x040 1B      4 -> +0x041 0x80  5 -> +0x014 0x10
      14 -> 0x410   15 -> 0x410   16 -> 0x28   17 -> DWORD  18 -> DWORD
      19 -> 0x208   26 -> 1B   27 -> 0x70
      22/24/25 -> 只被游戏 exe 读(0x24166F/0x24169D/0x2416CD), 长度按它自己声明的 0x10
    服务器条目(带序号, key = (序号<<16)|tag):
      2 名称 / 4 host / 3 DWORD(端口) / 5 / 6 / 7
    上一版两个根因: (a) 漏了 tag 15 (b) 用 "key+小步长" 铺服务器条目, 结果 0x18+3=27
    把全局 tag 27 覆盖成了端口 DWORD —— DWORD 路径会因 len!=4 直接判失败(不是"内容为空")。
    """
    KEY_MAX = 0x40000
    IMG_LEN = 4 + KEY_MAX * 4 + 0x8000
    b = bytearray(IMG_LEN)
    struct.pack_into("<I", b, 0, 0x40)
    tbl, rec = 4, 4 + KEY_MAX * 4
    entries = {}

    def put(key, val):
        nonlocal rec
        entries[key] = rec
        struct.pack_into("<I", b, rec, len(val))
        b[rec + 4:rec + 4 + len(val)] = val
        rec += 4 + len(val)
        rec = (rec + 15) & ~15

    d4 = lambda v: struct.pack("<I", v & 0xFFFFFFFF)
    # 服务器条目: 序号 1 起, key = (序号 << 16) | tag
    # (TenProxy 里 vtable 0x34 = (tag,dst,&len,seq) 读 tag 2/4, 0x38 = (tag,dst,seq)
    #  读 tag 3/5/6/7; seq 由取值函数内部折进高位)
    entry = (1 << 16)
    put(entry | 2, name.encode("gbk", "replace") + b"\x00")
    put(entry | 4, host.encode("gbk", "replace") + b"\x00")
    put(entry | 3, d4(port))
    put(entry | 5, d4(1))
    put(entry | 6, d4(0))
    put(entry | 7, d4(0))
    # ★ 2026-10-01: exe 0x6418 段 vtable[12](4参带序号: tag,dst,&len,seq) 读服务器条目
    #   tag8; seq=tag18值。旧镜像缺条目 tag8 -> generic 4B, 与 tag7(4B) 等长 -> 长度校验过。
    #   但内容仍要存在, 显式填 4B。
    put(entry | 8, d4(0))
    # ---- 全局命名空间(不带序号, 就是 key=tag) ----
    put(1, d4(0))
    put(2, d4(0))
    put(4, b"0123456789ABCDEF" * 8)      # LoginKey 128B (单独读一次, 不在上面那串里)
    put(6, d4(0))
    put(7, b"\x00" * 0x200)
    # ★ 2026-10-01 更正: exe 0x6418 段 vtable[12] 是 4 参带序号 (tag,dst,&len,seq),
    #   seq = tag18 值 = 服务器条目序号。旧镜像 tag18=0x200 -> 序号 512 -> 条目不存在 -> 失败。
    #   tag18 必须 = 条目序号(1)。tag7/tag8 的长度相等校验走服务器条目命名空间(见上 entry|8)。
    put(18, d4(1))
    put(8, b"\x00" * 0x200)          # 全局 tag8 保持 0x200(与 tag7 等长, 双保险)
    put(14, b"\x00" * 0x410)
    put(16, b"\x00" * 0x28)
    put(17, d4(1))
    put(19, b"\x00" * 0x208)
    # 下面这批的长度是逐条从 TenProxy!0x6310-0x6680 那段"复制到对象字段"里读出来的,
    # 不是猜的(每个 tag 的调用点都在同一处, pLen 常量就在前面 mov 里):
    #   tag 15 -> 对象+0x49c  0x410   tag 3  -> 对象+0x1038  0x1
    #   tag 14 -> 对象+0x08c  0x410   tag 5  -> 对象+0x00c0  0x10
    #   tag 4  -> 对象+0x011c 0x80    tag 26 -> 对象+0x10ac  0x1
    #   tag 27 -> 对象+0x10f4 0x70
    # 注意 tag 1 / 2 / 6 / 7 / 17 / 18 走的是 2 参数的 vtable 0x20/0x24/0x2c,
    # 不经过 0x7EA0/0x7ED0 的 pLen 路径, 所以只从日志看是看不出来的。
    global_spec = ((3, 1), (5, 0x10), (14, 0x410), (15, 0x410), (26, 1), (27, 0x70))
    for tag, ln2 in global_spec:
        put(tag, b"\x00" * ln2)
    # ★ 2026-10-01 新解出: exe 0x641600 段收集登录信息时读这几个 tag 并格式化:
    #   tag25 = OpenID, 格式串 0xdc7104 = "OpenID LoginKey: %s" -> 全 0 = 空账号 = 认证失败。
    #   tag22/24 是票据类 blob, 也尽量非空。tag7/tag8 长度已对齐(见上)。
    put(22, b"0123456789ABCDEF")                       # 16B 票据(非零)
    put(24, b"0123456789ABCDEF" * 8)                   # 128B 大 blob(非零)
    put(25, b"10001\x00" + b"\x00" * 10)               # OpenID "10001", 恰好 16B
    put(27, b"\xA5" * 0x70)                            # 0x70 blob(非零)
    # 兜底记录: 必须是合法 DWORD(len==4), 否则 DWORD 取值路径会因长度不符直接判失败
    generic = rec
    struct.pack_into("<I", b, rec, 4)
    rec += 16
    # ★★ 2026-10-01 决定性破译: vtable[12](0x8250)/vtable[14](0x8510) 读 tag7/tag8 用的是
    #   嵌套结构, 不是 (seq<<16)|tag!
    #   0x8250 寻址: [ebp-0x18] = [base+table[19] + (seq-1)*4]  (seq=1 -> key20 记录的 len 字段)
    #                 [ebp-0x1c] = base + [ebp-0x18]   ← len 字段值 = 条目相对 base 的偏移!
    #                 [ebp-0x20] = [条目 + (tag-1)*4]  ← 条目是裸 DWORD 偏移数组
    #                 [ebp-0x24] = base + [ebp-0x20] = 字段记录 -> 读 (len,value)
    #   0x8510(tag7) 要求字段 len 恰好 4。
    #   布局(全部相对 base 偏移):
    #     key20 记录 = (len=E1偏移, value=0)      ← 0x8510/0x8250 读 [key20记录+0] = len = 条目偏移
    #     条目(E1)   = 8 DWORD 裸数组 [字段偏移]   ← [条目+(tag-1)*4]
    #     字段记录   = (len=4, value)
    nested = rec
    e1 = nested + 8                                # 条目1 = base + (key20 len 字段值)
    struct.pack_into("<I", b, nested, e1)         # key20 len = E1 相对 base 偏移
    struct.pack_into("<I", b, nested + 4, 0)      # value = 0
    for i in range(8):
        struct.pack_into("<I", b, e1 + i * 4, 0)
    f5 = e1 + 32
    struct.pack_into("<I", b, f5, 4)              # 字段记录 tag5: len=4
    struct.pack_into("<I", b, f5 + 4, 4)          #   value = 4
    f7 = f5 + 8
    struct.pack_into("<I", b, f7, 4)              # 字段记录 tag7: len=4
    struct.pack_into("<I", b, f7 + 4, 4)          #   value = 4
    f8 = f7 + 8
    struct.pack_into("<I", b, f8, 4)              # 字段记录 tag8: len=4
    struct.pack_into("<I", b, f8 + 4, 4)          #   value = 4
    struct.pack_into("<I", b, e1 + 4 * 4, f5)     # E1[4] -> tag5 字段
    struct.pack_into("<I", b, e1 + 6 * 4, f7)     # E1[6] -> tag7 字段
    struct.pack_into("<I", b, e1 + 7 * 4, f8)     # E1[7] -> tag8 字段
    entries[20] = nested
    rec = f8 + 8
    b[tbl:tbl + KEY_MAX * 4] = struct.pack("<I", generic) * KEY_MAX
    for k, off in entries.items():
        if 1 <= k <= KEY_MAX:
            struct.pack_into("<I", b, tbl + (k - 1) * 4, off)
    return bytes(b)


# ---- 补丁机制: patch_spec.txt 里每项 "地址:十六进制字节" ----
#   "0x641654:9090"              绝对地址(仅在自己早读到原始字节时才敢用)
#   "tenproxy.dll:0x7CAF:01"     模块名:RVA  (依赖运行时算出的模块基址)
def parse_patches(spec):
    out = []
    for item in (spec or "").split(","):
        item = item.strip()
        if not item:
            continue
        parts = item.split(":")
        try:
            if parts[0].lower().startswith("0x"):
                out.append((int(parts[0], 0), bytes.fromhex("".join(parts[1:])), item))
            else:
                out.append(((parts[0], int(parts[1], 0)),
                            bytes.fromhex("".join(parts[2:])), item))
        except Exception as e:
            out.append((None, None, "%s  (解析失败 %r)" % (item, e)))
    return out


def apply_patches(h, known_bases, ml, spec, log):
    """写前读 / 写后读: 任何一步不对都直接报出来(不猜)"""
    for target, data, text in parse_patches(spec):
        if target is None:
            log("-- patch 跳过 %s" % text)
            continue
        if isinstance(target, tuple):
            mod, rva = target
            mb = known_bases.get(mod.lower(), 0)
            if not mb:
                tw = time.time()
                while time.time() - tw < 40:
                    ml2 = mods_peb(h) or ml
                    mb = next((b for n, b, s in ml2
                               if n.lower().startswith(mod.lower())), 0)
                    if mb:
                        break
                    time.sleep(0.3)
            if not mb:
                log("-- patch %s 找不到模块 %s (也许还没加载)" % (text, mod))
                continue
            addr, where = mb + rva, "%s+0x%X" % (mod, rva)
        else:
            addr, where = target, "0x%08X" % target
        before = rpm(h, addr, len(data))
        if not wpm(h, addr, data):
            log("-- patch %s: %s -> 写失败" % (where, before.hex(" ")))
            continue
        after = rpm(h, addr, len(data))
        log("-- patch %s: %s -> %s (%s)"
            % (where, before.hex(" "), after.hex(" "),
               "OK" if after == data else "!! 未生效"))


# ==================== 三方验证过的 4 个兼容补丁 ====================
# 来源: E:\codol\dist\launcher_src\CodolStateReader.cs + Run-Session.ps1
#   补丁1 PatchUnsignedAuthGate   0x00B9A78C 前 16B 起: 84 C0 74 B2 B0 01 -> 74(JE) 改 75(JNE)
#   补丁2 PatchUnsignedClientTicket 0x00B9A7B0 起:     84 C0 75 2A E8    -> 75(JNE) 改 EB(JMP)
#   补丁3 PatchAuthParseFallback  0x00B9A7B0 起: 某 call 改成 E9 跳 0x00B9A7F1
#   补丁4 PatchLocalLsgNonceCheck 0x00BA3C1A: 85 C0 75 44 -> 在 0x00BA3C1C 写 90 90(NOP)
#         (十进制 12205082 = 0xBA3C1A, 12205084 = 0xBA3C1C —— 上次我误算成 0xBA41DA;
#          用运行时转储 n10ao_exe_lobby.bin 核对: 85 C0 75 44 确实在 0xBA3C1A)
# 效果: 客户端走"未签名"离线路径 —— 实测请求里的 auth_task 会从 32 变成 10(三方同款),
#       且不再校验本地 LSG 的 8 字节 challenge。
# ★ 这些字节在磁盘上是加密的(.tp3 段), 必须【运行时解壳后】才匹配得到,
#   所以照 Run-Session.ps1 的做法: 循环重试直到模式出现。
COMPAT_DEADLINE = 90.0


def _vm_protect(h, addr, size, prot=0x40):
    try:
        k32.VirtualProtectEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                         ctypes.c_size_t, wintypes.DWORD,
                                         ctypes.POINTER(wintypes.DWORD)]
        old = wintypes.DWORD(0)
        ok = bool(k32.VirtualProtectEx(h, ctypes.c_void_p(addr), size, prot,
                                       ctypes.byref(old)))
        return ok, old
    except Exception:
        return False, wintypes.DWORD(0)


def _wpm_code(h, addr, data):
    """写代码段: 先 VirtualProtectEx 开写权限(失败也照样试一次), 写完还原 + 刷 icache。"""
    ok, old = _vm_protect(h, addr, len(data))
    wrote = wpm(h, addr, data)
    if ok:
        try:
            k32.VirtualProtectEx(h, ctypes.c_void_p(addr), len(data), old.value,
                                 ctypes.byref(wintypes.DWORD(0)))
        except Exception:
            pass
    if wrote:
        try:
            k32.FlushInstructionCache.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                                  ctypes.c_size_t]
            k32.FlushInstructionCache(h, ctypes.c_void_p(addr), len(data))
        except Exception:
            pass
    return wrote


def _match_at(buf, off, pat):
    """pat 里元素是 int 或 (等价集合)。"""
    for j, p in enumerate(pat):
        if off + j >= len(buf):
            return False
        b = buf[off + j]
        if isinstance(p, (tuple, list, set)):
            if b not in p:
                return False
        elif b != p:
            return False
    return True


def compat_patch_once(h):
    """尝试打一遍 4 个补丁。返回 (已完成的编号集合, 说明列表)。"""
    done, notes = set(), []

    # --- 1) AuthGate: 0x00B9A78C-16 起 40 字节内找 84 C0 (74|75) B2 B0 01
    base = 0x00B9A78C - 16
    buf = rpm(h, base, 40)
    if len(buf) == 40:
        for i in range(0, 40 - 6 + 1):
            if _match_at(buf, i, (0x84, 0xC0, (0x74, 0x75), 0xB2, 0xB0, 0x01)):
                a = base + i + 2
                cur = rpm(h, a, 1)
                if cur == b"\x75":
                    done.add(1)
                elif cur == b"\x74" and _wpm_code(h, a, b"\x75"):
                    done.add(1)
                    notes.append("补丁1 AuthGate 74->75 @0x%08X" % a)
                break

    # --- 2) ClientTicket: 0x00B9A7B0 起 64 字节内找 84 C0 (75|EB) 2A E8
    base2 = 0x00B9A7B0
    buf2 = rpm(h, base2, 64)
    if len(buf2) == 64:
        for i in range(0, 64 - 5 + 1):
            if _match_at(buf2, i, (0x84, 0xC0, (0x75, 0xEB), 0x2A, 0xE8)):
                a = base2 + i + 2
                cur = rpm(h, a, 1)
                if cur == b"\xEB":
                    done.add(2)
                elif cur == b"\x75" and _wpm_code(h, a, b"\xEB"):
                    done.add(2)
                    notes.append("补丁2 ClientTicket 75->EB @0x%08X" % a)
                break

    # --- 3) ParseFallback: 某 call(E8/E9) + 12 字节模式 -> 改成 E9 跳 0x00B9A7F1
    pat3 = (0x8D, 0x8D, 0x38, 0xFD, 0xFF, 0xFF, 0xC7, 0x85, 0x68, 0xFD, 0xFF, 0xFF)
    if len(buf2) == 64:
        for i in range(0, 64 - 5 - len(pat3) + 1):
            if buf2[i] not in (0xE8, 0xE9):
                continue
            if not _match_at(buf2, i + 5, pat3):
                continue
            a = base2 + i
            if buf2[i] == 0xE9:
                done.add(3)
            else:
                rel = (0x00B9A7F1 - a - 5) & 0xFFFFFFFF
                if _wpm_code(h, a, b"\xE9" + struct.pack("<I", rel)):
                    done.add(3)
                    notes.append("补丁3 ParseFallback E8->E9 @0x%08X -> 0x00B9A7F1" % a)
            break

    # --- 4) LsgNonceCheck: 0x00BA3C1A 处 85 C0 75 44 -> 0x00BA3C1C 写 90 90
    b4 = rpm(h, 0x00BA3C1A, 4)
    if len(b4) == 4:
        if b4 == b"\x85\xC0\x90\x90":
            done.add(4)
        elif b4 == b"\x85\xC0\x75\x44" and _wpm_code(h, 0x00BA3C1C, b"\x90\x90"):
            done.add(4)
            notes.append("补丁4 LsgNonceCheck NOP @0x00BA3C1C (85 C0 75 44 -> 85 C0 90 90)")

    # --- 5) GateB: 0x0062FE80 处 80 B9 14 06 01 00 00 0F 95 C0 C3 -> B0 01 C3
    b5 = rpm(h, 0x0062FE80, 11)
    if len(b5) == 11:
        if b5.startswith(b"\xB0\x01\xC3"):
            done.add(5)
        elif b5.startswith(b"\x80\xB9\x14\x06\x01\x00\x00\x0F\x95\xC0\xC3") and _wpm_code(h, 0x0062FE80, b"\xB0\x01\xC3"):
            done.add(5)
            notes.append("补丁5 GateB 放行 @0x0062FE80 (80 B9 ... -> B0 01 C3)")

    return done, notes


def compat_patch_thread(h, log, deadline=COMPAT_DEADLINE):
    """后台线程: 反复尝试 4 个补丁, 直到全部成功或超时。
    ★ 一旦某个补丁成功就【latch】住不再复查 —— 照抄 Run-Session.ps1 的 patched[$i]。
      原因: 补丁3 会把 0xB9A7C7 的 E8 改成 E9, 于是补丁2 的模式(84 C0 .. 2A E8)
      再也匹配不到; 若每轮重新判定, 补丁2 就会"掉出计数"(上一轮日志里 3/4 变 2/4 就是这个)。"""
    done = set()
    t0 = time.time()
    while time.time() - t0 < deadline and len(done) < 5:
        try:
            cur, notes = compat_patch_once(h)
        except Exception as e:
            log("-- [兼容补丁] 异常: %r" % (e,))
            return
        for n in notes:
            log("-- [兼容补丁] %s" % n)
        new = cur - done
        done |= cur                      # latch
        if new:
            log("-- [兼容补丁] 进度 %d/5 (本轮新增 %s, 用时 %.1fs)"
                % (len(done), sorted(new), time.time() - t0))
        time.sleep(0.25)
    # 收尾回读: 确认 4 个补丁的字节还在(若被 TP3 完整性检查还原, 这里会直接暴露)
    for i, ad, want in ((1, 0x00B9A78E, b"\x75"), (2, 0x00B9A7C5, b"\xEB"),
                        (3, 0x00B9A7C7, b"\xE9"), (4, 0x00BA3C1C, b"\x90\x90"), (5, 0x0062FE80, b"\xB0\x01\xC3")):
        got = rpm(h, ad, len(want))
        log("-- [兼容补丁] 回读#%d @0x%08X = %-8s 期望 %-8s %s"
            % (i, ad, got.hex(" "), want.hex(" "),
               "OK" if got == want else "!! 不匹配(可能被 TP3 还原)"))
    if len(done) == 4:
        log("-- [兼容补丁] 5/5 全部成功 (用时 %.1fs)" % (time.time() - t0))
    else:
        log("-- [兼容补丁] 只完成 %d/5: %s  (超时 %.0fs)"
            % (len(done), sorted(done), deadline))
        for i in (1, 2, 3, 4, 5):
            if i not in done:
                log("     !! 补丁%d 的字节模式始终没出现(该段可能还没解壳)" % i)


# ============== 会话密钥快照(供 lobby_server 解密 0x85 任务帧) ==============
# 来源: 三方 CodolLocalLobbyServer.cs 的 ReadLocalClientSecrets / ReadLocalClientChallenge
#   svc = [0x8269774]                         (我们一直在读的那条链)
#   sub = [svc + 1268(0x4F4)]
#   challenge = read(sub + 1532(0x5FC), 8)    要求 [sub + 1512(0x5E8)] >= 2
#   a = [sub + 1540(0x604)] ; b = [sub + 1544(0x608)]   要求 [sub+0x5E8] == 3
#   blob = read(sub + 1548(0x60C), 40)
#   aes_out = read(a + 156, 16) ; aes_in = read(b + 156, 16)
#   hmac_out = XOR还原(blob[0:20], 表1) ; hmac_in = XOR还原(blob[20:40], 表2)
# 为什么要写文件: 服务端进程读游戏内存会被拦(三方实测), 而 nt10 这条链读得到。
SECRETS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secrets.txt")
_HK_W1 = (2919830337, 4089226047, 3169481240, 3423678985, 4099162642)
_HK_I1 = (7, 17, 14, 16, 9, 19, 13, 0, 2, 3, 4, 8, 1, 10, 11, 5, 18, 6, 12, 15)
_HK_W2 = (2866684544, 4095810571, 938409728, 3457192487, 557642922)
_HK_I2 = (19, 18, 9, 4, 17, 1, 10, 8, 13, 2, 15, 3, 12, 16, 5, 7, 0, 14, 6, 11)


def _decode_key(src, start, words, indices):
    """照抄三方 DecodeKey: out[j] = src[start+j] ^ (小端展开的 words)[indices[j]]"""
    tab = b"".join(struct.pack("<I", w) for w in words)
    return bytes(src[start + j] ^ tab[indices[j]] for j in range(len(indices)))


def snapshot_client(h):
    """读一次客户端会话状态; 返回 {state, sub, challenge?, aes_*/hmac_*}"""
    def r32(a):
        b = rpm(h, a, 4)
        return struct.unpack("<I", b)[0] if len(b) == 4 else 0
    svc = r32(0x08269774)
    if not svc:
        return {}
    sub = r32(svc + 1268)
    if not sub:
        return {}
    st = r32(sub + 1512)
    out = {"state": st, "sub": sub}
    if st >= 2:
        c = rpm(h, sub + 1532, 8)
        if len(c) == 8:
            out["challenge"] = c
    if st == 3:
        a, b = r32(sub + 1540), r32(sub + 1544)
        blob = rpm(h, sub + 1548, 40)
        if a and b and len(blob) == 40:
            ao, ai = rpm(h, a + 156, 16), rpm(h, b + 156, 16)
            if len(ao) == 16 and len(ai) == 16:
                out["aes_out"] = ao
                out["aes_in"] = ai
                out["hmac_out"] = _decode_key(blob, 0, _HK_W1, _HK_I1)
                out["hmac_in"] = _decode_key(blob, 20, _HK_W2, _HK_I2)
    return out


def secrets_snapshot_thread(h, log, pid, seconds=600.0):
    """每 0.5s 读一次; 有变化就原子写 secrets.txt。"""
    last = None
    t0 = time.time()
    while time.time() - t0 < seconds:
        try:
            s = snapshot_client(h)
        except Exception:
            s = {}
        cur = (s.get("aes_out", b""), s.get("hmac_out", b""), s.get("challenge", b""))
        if cur != (b"", b"", b"") and cur != last:
            last = cur
            lines = ["pid %d" % pid, "state %d" % s.get("state", 0)]
            for n in ("challenge", "aes_out", "aes_in", "hmac_out", "hmac_in"):
                if s.get(n):
                    lines.append("%s %s" % (n, s[n].hex()))
            tmp = SECRETS_PATH + ".tmp"
            with open(tmp, "w") as f:
                f.write("\n".join(lines) + "\n")
            os.replace(tmp, SECRETS_PATH)
            log("[secrets] 快照已写 state=%s challenge=%s"
                % (s.get("state"), (s.get("challenge") or b"").hex()))
            log("[secrets]   aes_out=%s" % (s.get("aes_out") or b"").hex())
            log("[secrets]   hmac_out=%s" % (s.get("hmac_out") or b"").hex())
        time.sleep(0.5)


class _MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p),
                ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wintypes.DWORD),
                ("RegionSize", ctypes.c_size_t),
                ("State", wintypes.DWORD),
                ("Protect", wintypes.DWORD),
                ("Type", wintypes.DWORD)]


def scan_dword(h, value, maxtime=60.0, cap=8):
    """在【私有可提交】内存里找 4 字节值(小端)。只扫 MEM_PRIVATE(堆), 不扫镜像,
    这样规模可控。返回命中地址列表。"""
    pat = struct.pack("<I", value)
    hits = []
    addr = 0
    t0 = time.time()
    k32.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                   ctypes.POINTER(_MBI), ctypes.c_size_t]
    k32.VirtualQueryEx.restype = ctypes.c_size_t
    MEM_COMMIT, MEM_PRIVATE = 0x1000, 0x20000
    PAGE_GUARD, PAGE_NOACCESS = 0x100, 0x01
    while addr < 0x7FFF0000 and time.time() - t0 < maxtime:
        mbi = _MBI()
        if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                              ctypes.sizeof(mbi)) == 0:
            addr += 0x1000
            continue
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize or 0
        if (mbi.State == MEM_COMMIT and mbi.Type == MEM_PRIVATE
                and not (mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS))):
            off = 0
            while off < size:
                want = int(min(0x40000, size - off))
                d = rpm(h, base + off, want)
                if d:
                    k = d.find(pat)
                    while k >= 0:
                        hits.append(base + off + k)
                        if len(hits) >= cap:
                            return hits
                        k = d.find(pat, k + 4)
                off += want
        addr = base + size if size else addr + 0x1000
    return hits


def scan_playerstate_bases(h, maxtime=8.0, cap=64):
    """★ 扫【私有可提交】内存找本地 playerstate（返回基址列表）。

    锚点（来自参考产物 `playerstate-fields.json`，并用 `gameplay-playerstate.bin` 实证）：
        +0xa4 = gravity(800)   +0xb0 = movementSpeed(190)
        +0xc0 = cameraEntity(2047)   +0x1fc = groundEntity(2047)
    主判据 = 「+0xa4 处 800」且「+12 处 190」；备用判据 = 「+0x1c 处 2047 且 +0x158 处 2047」。
    """
    grav = struct.pack("<I", 800)
    mspd = struct.pack("<I", 190)
    ent = struct.pack("<I", 2047)
    hits = []
    addr = 0
    t0 = time.time()
    k32.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                   ctypes.POINTER(_MBI), ctypes.c_size_t]
    k32.VirtualQueryEx.restype = ctypes.c_size_t
    MEM_COMMIT, MEM_PRIVATE = 0x1000, 0x20000
    PAGE_GUARD, PAGE_NOACCESS = 0x100, 0x01
    while addr < 0x7FFF0000 and time.time() - t0 < maxtime:
        mbi = _MBI()
        if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                              ctypes.sizeof(mbi)) == 0:
            addr += 0x1000
            continue
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize or 0
        if (mbi.State == MEM_COMMIT and mbi.Type == MEM_PRIVATE
                and not (mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS))):
            off = 0
            while off < size:
                want = int(min(0x40000, size - off))
                d = rpm(h, base + off, want)
                if d:
                    k = d.find(grav)
                    while k >= 0:
                        ok = (d[k + 12:k + 16] == mspd)
                        if ok:
                            # ★ 加严（2026-10-04 事故）：原来只靠 "gravity==800 且 speed==190"，
                            #   会误收"碰巧也是 800/190"的**别的结构**（实测误收过一批
                            #   pm_flags=0x18004000、origin=(-303.9,-2471.1,64.86) 的假货，
                            #   导致探针一整轮 ★=0、镜像全程回落）。
                            #   这里再用 playerstate 的其它已知字段交叉验证：
                            #     +0x0c pm_flags 必须是很小的位集   +0x30/0x34/0x38 origin 必须在地图范围内
                            #     +0xc0 cameraEntity / +0x1fc groundEntity 至少一个是 2047
                            b = k - 0xA4
                            if b >= 0 and b + 0x200 <= len(d):
                                pmf = struct.unpack_from("<I", d, b + 0x0C)[0]
                                ox, oy, oz = struct.unpack_from("<3f", d, b + 0x30)
                                cam = struct.unpack_from("<I", d, b + 0xC0)[0]
                                gnd = struct.unpack_from("<I", d, b + 0x1FC)[0]
                                ok = (pmf < 0x10000
                                      and abs(ox) < 8192.0 and abs(oy) < 8192.0
                                      and abs(oz) < 4096.0
                                      and (cam == 2047 or gnd == 2047))
                            else:
                                ok = False
                        if ok:
                            hits.append(base + off + k - 0xA4)
                            if len(hits) >= cap:
                                return hits
                        k = d.find(grav, k + 4)
                off += want
        addr = base + size if size else addr + 0x1000
    return hits


def read_playerstate(h, base):
    """按已证实的偏移读一个 playerstate，返回 dict（读不到返回 None）。

    ★ 2026-10-04 追加读取"物理/模拟"相关字段，用来判断客户端**是否愿意自己跑 Pmove**：
        +0x04 = pm_type      +0x08 = pm_time      +0x0c = pm_flags
        +0x10 = otherFlags   +0x14 = linkFlags    +0x2c = (idx12, changeHint=3)
    """
    w = rpm(h, base, 0x210)
    if len(w) < 0x210:
        return None
    try:
        x, y, z = struct.unpack_from("<3f", w, 0x30)
        pitch, yaw, roll = struct.unpack_from("<3f", w, 0x160)
        vx, vy, vz = struct.unpack_from("<3f", w, 0x3C)
        cmdtime = struct.unpack_from("<I", w, 0x00)[0]
        return {"x": x, "y": y, "z": z, "pitch": pitch, "yaw": yaw, "roll": roll,
                "vx": vx, "vy": vy, "vz": vz,
                "command_time": cmdtime,
                "gravity": struct.unpack_from("<I", w, 0xA4)[0],
                "move_speed": struct.unpack_from("<I", w, 0xB0)[0],
                "camera_entity": struct.unpack_from("<I", w, 0xC0)[0],
                "ground_entity": struct.unpack_from("<I", w, 0x1FC)[0],
                "pm_type": struct.unpack_from("<I", w, 0x04)[0],
                "pm_time": struct.unpack_from("<I", w, 0x08)[0],
                "pm_flags": struct.unpack_from("<I", w, 0x0C)[0],
                "other_flags": struct.unpack_from("<I", w, 0x10)[0],
                "link_flags": struct.unpack_from("<I", w, 0x14)[0],
                "f2c": struct.unpack_from("<I", w, 0x2C)[0]}
    except Exception:
        return None


def _probe_tick_hz():
    """读 `tick_hz.txt`（与战斗服共用）；默认 **128 tick ≈ 7.8ms**（用户指定）。"""
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tick_hz.txt")
        if os.path.exists(p):
            v = float(open(p, "r", encoding="utf-8").read().replace(",", " ").split()[0])
            if 1.0 <= v <= 1000.0:
                return v
    except Exception:
        pass
    return 128.0


_PROBE_TICK = _probe_tick_hz()
_PROBE_POLL = 1.0 / _PROBE_TICK


def _is_predicted(ps):
    """判"客户端预测态"（2026-10-04 实测修正版）。

    权威态（回声我们快照）：`f2c == 0` 且 `pm_flags ∈ {0, 0x10}`（0x10 = 我方 idx20 的开镜位）。
    预测态：实测 `pm_flags = 0x2020`、`f2c = 4`、并带下落速度。
    ⇒ 判据 = `f2c != 0` 或 `pm_flags ∉ {0, 0x10}`。（前一版只看 `pm_flags != 0` 会误判开镜时的权威态）
    ★ 另加"pm_flags 必须是很小的位集"（`< 0x10000`）：实测误收过一批假结构
      `pm_flags = 0x18004000`（配合 §13.54 的锚点加严一起用）。
    """
    if ps["pm_flags"] >= 0x10000 or ps["f2c"] >= 0x10000:
        return False
    return (ps["f2c"] != 0) or (ps["pm_flags"] not in (0, 0x10))


def _pred_base_file():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "pred_base.txt")


def _load_pred_base():
    """上一轮学到的预测态地址（exe 基址固定 0x400000，故静态 VA 稳定）。"""
    try:
        with open(_pred_base_file(), "r", encoding="utf-8") as f:
            return int(f.read().strip().split()[0], 0)
    except Exception:
        return None


def _save_pred_base(b):
    try:
        with open(_pred_base_file(), "w", encoding="utf-8") as f:
            f.write("0x%08X\n" % b)
    except Exception:
        pass


def _is_live_advancing(a, b):
    """a/b 为同一地址相隔 ~20ms 的两次读数：commandTime 必须严格推进(=每帧被 usercmd 喂的活结构)。"""
    if not a or not b:
        return False
    if b["command_time"] <= a["command_time"]:
        return False
    return not (b["x"] == 0.0 and b["y"] == 0.0 and b["z"] == 0.0)


def _live_score(ps):
    """判"哪个是预测态"的主判据：commandTime 最新的那个（手册 §13.53.4 建议）。
    预测态每帧被 usercmd 推进，commandTime 必然领先/更新于"回声我们快照"的权威副本。"""
    moving = 1 if (ps["vx"] or ps["vy"] or ps["vz"]) else 0
    extra = 1 if ps["pm_flags"] not in (0, 0x10) else 0
    return (ps["command_time"], moving, extra)


def playerstate_probe_thread(h, log, pid, seconds=300.0, interval=3.0):
    """★ 出生点/位置探针（2026-10-04）：周期性扫内存里的本地 playerstate，把 origin/角度落盘。

    为什么需要它：`spawn_from_map.on` 是让客户端**在地图自带的几十个 mp_tdm_spawn 里自己挑**
    出生点，服务端看不到它挑了哪个（挑到几何体里就"卡住走不动"）。读一次内存就能知道
    "客户端实际落在哪"，再与地图出生点清单（`loaded-map-entities-19.txt`）对照。
    结果写 `player_origin.txt`。
    """
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "player_origin.txt")
    t0 = time.time()
    try:
        with open(out, "w", encoding="utf-8") as f:
            f.write("# nt10 playerstate 探针 pid=%d\n" % pid)
            f.write("# 锚点: gravity(800)@+0xa4 / movementSpeed(190)@+0xb0 / cameraEntity(2047)@+0xc0\n")
            f.write("# 列: t base origin(x y z) angles(pitch yaw roll) command_time\n")
    except Exception as e:
        log("  [PS] 打不开 %s: %r" % (out, e))
    n = 0
    dumped = False
    # ★ 预测态（2026-10-04 实测）：客户端自己维护一份"带重力/碰撞"的 playerstate，判据 =
    #   `pm_flags != 0`（实测 0x2020）或 `f2c != 0`；其余结构与"回声我们快照"的权威态同值。
    #   定位到之后**定点高频轮询**它（20ms），写进 predicted.bin 供战斗服镜像回发。
    pred_base = None
    _cached_base = _load_pred_base()   # ★ 上一轮学到的地址：先验证再用，避免每轮重新猜
    pred_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "predicted.bin")
    # ★ 抖动/穿墙分析用：定点轮询时把预测态按 ~40ms 高速落盘（t x y z vx vy vz）
    trace_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pred_trace.txt")
    pred_seq = [0]
    trace_n = [0]
    trace_fh = [None]
    try:
        trace_fh[0] = open(trace_file, "w", encoding="utf-8")
        trace_fh[0].write("# t x y z vx vy vz  (预测态高速轨迹; 每 ~40ms 一条)\n")
    except Exception:
        trace_fh[0] = None

    def _write_pred(ps):
        try:
            pred_seq[0] = (pred_seq[0] + 1) & 0xFFFFFFFF
            with open(pred_file, "wb") as f:
                f.write(struct.pack("<6fI", ps["x"], ps["y"], ps["z"],
                                    ps["vx"], ps["vy"], ps["vz"], pred_seq[0]))
        except Exception:
            pass

    while time.time() - t0 < seconds:
        # ---------- ① 已定位预测态：1 秒内 20ms 一次定点读，写 predicted.bin ----------
        if pred_base is not None:
            t1 = time.time()
            while time.time() - t1 < 1.0 and time.time() - t0 < seconds:
                ps = read_playerstate(h, pred_base)
                # ★ 轮询期间**不再**用 pm_flags/f2c 复判 —— 实测它们在预测态里也会随玩家状态变化
                #   （0x20/0x4000/0x2…），会把稳定命中的地址误判成"失效"。只看读值是否有效。
                _bad = (ps is None)
                if not _bad:
                    _vs = (ps["x"], ps["y"], ps["z"], ps["vx"], ps["vy"], ps["vz"])
                    _bad = any(v != v or abs(v) > 100000.0 for v in _vs)
                    if not _bad and ps["x"] == 0.0 and ps["y"] == 0.0 and ps["z"] == 0.0:
                        _bad = True
                if _bad:
                    log("  [PS] 预测态 0x%08X 读失败/越界 → 重新扫描" % pred_base)
                    pred_base = None
                    break
                _write_pred(ps)
                # ★ 高速轨迹：**每个 tick 都写**（128 tick ⇒ ≈7.8ms 一条），供抖动/穿墙定量分析
                trace_n[0] += 1
                if trace_fh[0] is not None:
                    try:
                        trace_fh[0].write("%.4f %.2f %.2f %.3f %.2f %.2f %.2f\n"
                                          % (time.time() - t0, ps["x"], ps["y"], ps["z"],
                                             ps["vx"], ps["vy"], ps["vz"]))
                        if trace_n[0] % 64 == 0:
                            trace_fh[0].flush()
                    except Exception:
                        pass
                time.sleep(_PROBE_POLL)
            continue
        # ---------- ①.5 有缓存地址：先验证它还在被逐帧 tick（省掉整轮扫描，根除 ★=0） ----------
        if _cached_base is not None:
            _a = read_playerstate(h, _cached_base)
            time.sleep(0.02)
            _b = read_playerstate(h, _cached_base)
            if _is_live_advancing(_a, _b):
                pred_base = _cached_base
                log("  [PS] ★ 复用已学到的预测态 base=0x%08X (commandTime %d -> %d)"
                    % (_cached_base, _a["command_time"], _b["command_time"]))
                continue
            log("  [PS] 缓存地址 0x%08X 已失效(commandTime 未推进) -> 重新扫描" % _cached_base)
            _cached_base = None
        # ---------- ② 未定位：按 interval 扫描 ----------
        time.sleep(interval)
        n += 1
        try:
            bases = scan_playerstate_bases(h, maxtime=6.0, cap=32)
        except Exception as e:
            log("  [PS] 第 %d 轮 scan 异常: %r" % (n, e))
            continue
        good = []
        for b in bases:
            ps = read_playerstate(h, b)
            if ps is None:
                continue
            if not (ps["gravity"] == 800 and ps["move_speed"] == 190):
                continue
            if any((v != v or abs(v) > 100000.0)
                   for v in (ps["x"], ps["y"], ps["z"], ps["pitch"], ps["yaw"], ps["roll"])):
                continue
            good.append((b, ps))
        # ★ 选"预测态"（2026-10-04 加固；见手册 §13.53.4）：
        #   ① 首选 **z 与众数不同** —— 权威副本的 z 恒等于我们下发的常量（当前 -116.00），
        #      而预测态的 z 是客户端自己算的（实测 -99.6 / -123.9），天然是离群值；
        #   ② 退路一：`_is_predicted()`（f2c != 0 或 pm_flags ∉ {0, 0x10}）；
        #   ③ 退路二（本轮新增）：**commandTime 最新** —— 预测态每帧被 usercmd 推进，
        #      权威副本只在收到我们快照时更新 ⇒ 上一轮 `★=0` 那种全落空的情况由它兜住。
        _zs = [q["z"] for _b, q in good]
        _mode_z = max(set(_zs), key=_zs.count) if _zs else None
        _ranked = sorted(good, key=lambda t: _live_score(t[1]), reverse=True)
        _how = ""
        for _b, _ps in good:
            if _mode_z is not None and abs(_ps["z"] - _mode_z) > 1.0:
                pred_base = _b
                _how = "z 离群 %.2f vs 众数 %.2f" % (_ps["z"], _mode_z)
                break
        if pred_base is None:
            for _b, _ps in good:
                if _is_predicted(_ps):
                    pred_base = _b
                    _how = "pm_flags=0x%X f2c=%d" % (_ps["pm_flags"], _ps["f2c"])
                    break
        if pred_base is None and len(_ranked) >= 2 \
                and _ranked[0][1]["command_time"] > _ranked[1][1]["command_time"]:
            pred_base = _ranked[0][0]
            _how = "commandTime 最新 %d > %d" % (_ranked[0][1]["command_time"],
                                                _ranked[1][1]["command_time"])
        if pred_base is not None:
            _ps = read_playerstate(h, pred_base) or good[0][1]
            log("  [PS] ★ 找到预测态 base=0x%08X (%s) origin=(%.1f, %.1f, %.1f) "
                "vel=(%.1f, %.1f, %.1f) pm_flags=0x%X f2c=%d -> 开始定点轮询"
                % (pred_base, _how, _ps["x"], _ps["y"], _ps["z"],
                   _ps["vx"], _ps["vy"], _ps["vz"], _ps["pm_flags"], _ps["f2c"]))
            _save_pred_base(pred_base)      # ★ 记下来：下一轮直接复用，不再靠猜
        # ★ 第一轮命中时把原始字节 dump 出来 —— 用来定位"真正的 origin 偏移"
        #   （+0x30 读出来全是 0 时，要靠 dump 找真正的坐标三元组）
        if good and not dumped:
            dumped = True
            try:
                hx = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "player_origin_hex.txt")
                with open(hx, "w", encoding="utf-8") as f:
                    f.write("# playerstate 原始字节 dump（前 2 个候选，各 0x210 字节）\n")
                    for b, ps in good[:2]:
                        raw = rpm(h, b, 0x210)
                        f.write("\n## base=0x%08X len=%d\n" % (b, len(raw)))
                        for i in range(0, len(raw), 16):
                            f.write("%04x  %-47s  %s\n" % (
                                i,
                                " ".join("%02x" % c for c in raw[i:i + 16]),
                                "".join(chr(c) if 32 <= c < 127 else "." for c in raw[i:i + 16])))
                        # 顺便把 0x00..0x200 里所有"像坐标的 float 三元组"列出来，方便肉眼定位
                        f.write("-- 候选 float 三元组（连续 3 个 |v|<20000 且非全 0 的 float）--\n")
                        for off in range(0, 0x200, 4):
                            if off + 12 > len(raw):
                                break
                            try:
                                a1, a2, a3 = struct.unpack_from("<3f", raw, off)
                            except Exception:
                                break
                            if all(v == v and abs(v) < 20000.0 for v in (a1, a2, a3)) \
                                    and any(v != 0.0 for v in (a1, a2, a3)):
                                f.write("   +0x%03x : %.3f %.3f %.3f\n" % (off, a1, a2, a3))
                log("  [PS] 已 dump 候选原始字节 -> player_origin_hex.txt")
            except Exception as e:
                log("  [PS] dump 失败: %r" % (e,))
        if good:
            try:
                with open(out, "a", encoding="utf-8") as f:
                    for b, ps in good[:24]:
                        f.write("t=%.1f base=0x%08X origin=%.2f %.2f %.2f "
                                "vel=%.2f %.2f %.2f "
                                "angles=%.3f %.3f %.3f commandTime=%d "
                                "pm=%d/%d/%d f2c=%d\n"
                                % (time.time() - t0, b, ps["x"], ps["y"], ps["z"],
                                   ps["vx"], ps["vy"], ps["vz"],
                                   ps["pitch"], ps["yaw"], ps["roll"], ps["command_time"],
                                   ps["pm_type"], ps["pm_flags"], ps["other_flags"],
                                   ps["f2c"]))
            except Exception:
                pass
            p0 = good[0][1]
            _ors = {("%.1f,%.1f,%.1f" % (q["x"], q["y"], q["z"])) for _b, q in good}
            log("  [PS] 第 %d 轮: %d 个 playerstate（不同 origin %d 种）; "
                "第一个 origin=(%.1f, %.1f, %.1f) vel=(%.1f, %.1f, %.1f) yaw=%.2f "
                "pm_type=%d pm_flags=0x%X"
                % (n, len(good), len(_ors), p0["x"], p0["y"], p0["z"],
                   p0["vx"], p0["vy"], p0["vz"], p0["yaw"],
                   p0["pm_type"], p0["pm_flags"]))
        elif n <= 3 or n % 10 == 0:
            log("  [PS] 第 %d 轮: 未找到 playerstate" % n)
    log("  [PS] 探针结束（%d 轮），结果 -> %s" % (n, os.path.basename(out)))


def probe_auth_object(h, log):
    """按 vtable 0xD5A2EC 找出客户端的 auth 对象, 打印关键字段。
    判据参考反汇编:
      [obj+0x18]  = 早期从应答里取的第一个值(0xB9A5CE)
      [obj+0xD8]  = 逐位解析 client_ticket 后的首个 dword, 必须 == DE AD BD EF(0xB9A809)
      [obj+0xCC]/[obj+0xC8]/[obj+0xD0] = 后续一步写入(0xB9A863/0xB9A877/0xB9A888)
    """
    try:
        hits = scan_dword(h, 0xD5A2EC)
    except Exception as e:
        log("  [authobj] 扫描异常: %r" % (e,))
        return
    if not hits:
        log("  [authobj] 没扫到 vtable 0xD5A2EC (对象未创建/已释放/在非私有页)")
        return
    for a in hits[:4]:
        try:
            f = {}
            for off in (0x18, 0x28, 0x2C, 0xC8, 0xCC, 0xD0, 0xD8, 0xE0, 0xF8, 0xFC,
                        0x160, 0x164, 0x168):
                b = rpm(h, a + off, 4)
                f[off] = struct.unpack("<I", b)[0] if len(b) == 4 else -1
            log("  [authobj] 0x%08X  +18=0x%X +28=0x%X +C8=0x%X +CC=0x%X +D0=0x%X "
                "+D8=0x%X(票据魔数应为0xEFBDADDE) +E0=0x%X +F8=0x%X +FC=0x%X +160=0x%X +164=0x%X"
                % (a, f[0x18], f[0x28], f[0xC8], f[0xCC], f[0xD0], f[0xD8], f[0xE0],
                   f[0xF8], f[0xFC], f[0x160], f[0x164]))
            try:
                open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "_authobj_%08X.bin" % a), "wb").write(rpm(h, a, 0x2400))
            except Exception:
                pass
        except Exception as e:
            log("  [authobj] 读字段异常 0x%08X: %r" % (a, e))


def watch_dialogs(pid, t_launch, log, stop):
    """盯游戏自己的 #32770 对话框(错误弹窗), 出现就记下【时刻 + 文字】。
    只调 user32 枚举窗口, 不读游戏内存, 零风险。"""
    u = ctypes.WinDLL("user32", use_last_error=True)
    W = wintypes
    u.GetWindowTextW.argtypes = [W.HWND, W.LPWSTR, ctypes.c_int]
    u.GetClassNameW.argtypes = [W.HWND, W.LPWSTR, ctypes.c_int]
    u.GetWindowThreadProcessId.argtypes = [W.HWND, ctypes.POINTER(W.DWORD)]
    u.EnumWindows.argtypes = [ctypes.c_void_p, W.LPARAM]
    u.EnumChildWindows.argtypes = [W.HWND, ctypes.c_void_p, W.LPARAM]
    found = []

    def _txt(h, n=512):
        b = ctypes.create_unicode_buffer(n)
        u.GetWindowTextW(h, b, n)
        return b.value

    def _cls(h):
        b = ctypes.create_unicode_buffer(64)
        u.GetClassNameW(h, b, 64)
        return b.value

    def _cb(h, l):
        wp = W.DWORD(0)
        u.GetWindowThreadProcessId(h, ctypes.byref(wp))
        if wp.value == pid and _cls(h) == "#32770":
            kids = []

            def _ck(k, ll):
                t = _txt(k)
                if t:
                    kids.append(t)
                return True

            ck = ctypes.WINFUNCTYPE(ctypes.c_bool, W.HWND, W.LPARM)(_ck)
            try:
                u.EnumChildWindows(h, ck, 0)
            except Exception:
                pass
            found.append((int(h) if h else 0, _txt(h), kids))
        return True

    cb = ctypes.WINFUNCTYPE(ctypes.c_bool, W.HWND, W.LPARAM)(_cb)
    seen = set()
    while not stop.is_set():
        del found[:]
        try:
            u.EnumWindows(cb, 0)
        except Exception:
            pass
        for h, t, kids in found:
            if h in seen:
                continue
            seen.add(h)
            log("  [dlg] ★ t=%.1fs 弹出 #32770 hwnd=0x%X 标题=%r 子控件=%s"
                % (time.time() - t_launch, h, t, kids[:4]))
        time.sleep(0.4)


# ============================================================ KDF 入参抓取
# 2026-10-03: 借鉴 ol-mod 的 deriveSessionKeys 后, 我们用 kdf_probe.py 复盘发现
# "算法对、但输入端对不上"。随后 dump 出 0xB9C000..0xBA2000(_exe_b9c.bin) 静态读出了
# 客户端真实的 KDF(见 HANDOFF §10.8), 只剩 transcript 的组装方式未知。
# 这里挂上那个 HMAC(0xBA0D20), 一次拿到两个入参, 就能离线反推 transcript:
#
#   0xBA0D20 是 cdecl 4 参:
#       f(arg1=&transcriptHash(20B), arg2=&sessionKey(24B), arg3=24, arg4=&out(20B))
#   (调用点 0xBA1E96: push &secret; push 0x18; push &sessionKey; push &transcriptHash)
#
# ★ 必须在**入口瞬间**把两个入参指向的内容抄走: 它们都在调用方的栈上
#   ([ebp-0x60] / [ebp-0x38]), 函数一返回就被后续调用覆盖 ——
#   我们在 describe_sockaddr 上踩过一模一样的坑(延迟读取全是乱码)。
KDF_HMAC_VA = 0x00BA0D20
KDF_DATA_OFF = 0x1000          # 数据区放在代码洞内偏移 0x1000 处
# 数据区布局: +0x00 retaddr / +0x04 arg1 / +0x08 arg2 / +0x0C arg3 / +0x10 arg4
#             +0x14 命中计数 / +0x18 标志 0x464B44 ("DKF" 小端可读作 KDF 的倒序)
#             +0x20 transcriptHash(20B) / +0x34 sessionKey(24B)
KDF_MAGIC = 0x464B44


def build_kdf_tramp(cave_addr, data_addr, back_addr, stolen):
    """生成 0xBA0D20 的跳板: 入口抄入参 -> 执行被偷指令 -> 跳回。"""
    c = bytearray()
    c += b"\x9C"                                  # pushfd
    c += b"\x60"                                  # pushad
    # pushfd+pushad 共 36 字节, 故原 [esp+4](arg1) 现在在 [esp+0x28]
    c += b"\xB8" + struct.pack("<I", data_addr)   # mov eax, data
    c += b"\x8B\x54\x24\x24"                      # mov edx,[esp+0x24] retaddr
    c += b"\x89\x50\x00"                          # mov [eax+0], edx
    c += b"\x8B\x54\x24\x28"                      # arg1
    c += b"\x89\x50\x04"
    c += b"\x8B\x54\x24\x2C"                      # arg2
    c += b"\x89\x50\x08"
    c += b"\x8B\x54\x24\x30"                      # arg3
    c += b"\x89\x50\x0C"
    c += b"\x8B\x54\x24\x34"                      # arg4
    c += b"\x89\x50\x10"
    # 抄 arg1 的 20 字节 -> +0x20
    c += b"\x8B\x50\x04"                          # mov edx,[eax+4]
    c += b"\x85\xD2"                              # test edx,edx
    j1 = len(c) + 1
    c += b"\x74\x00"                              # je skip1
    for k in range(5):                            # 5 dword = 20B
        c += (b"\x8B\x32" if k == 0 else b"\x8B\x72" + bytes([k * 4]))
        c += b"\x89\x70" + bytes([0x20 + k * 4])
    c[j1] = len(c) - (j1 + 1)
    # 抄 arg2 的 24 字节 -> +0x34
    c += b"\x8B\x50\x08"                          # mov edx,[eax+8]
    c += b"\x85\xD2"
    j2 = len(c) + 1
    c += b"\x74\x00"                              # je skip2
    for k in range(6):                            # 6 dword = 24B
        c += (b"\x8B\x32" if k == 0 else b"\x8B\x72" + bytes([k * 4]))
        c += b"\x89\x70" + bytes([0x34 + k * 4])
    c[j2] = len(c) - (j2 + 1)
    c += b"\xC7\x40\x18" + struct.pack("<I", KDF_MAGIC)   # mov [eax+0x18], magic
    c += b"\xFF\x40\x14"                          # inc dword [eax+0x14]
    c += b"\x61"                                  # popad
    c += b"\x9D"                                  # popfd
    c += stolen
    jmp_from = cave_addr + len(c) + 5
    c += b"\xE9" + struct.pack("<i", back_addr - jmp_from)
    return bytes(c)


# ======================================================================
# 0xB82A90 「房间报文解析器」入口探针(2026-11-03)
#   背景: 静态已证 —— 入站派发 0xB838A0 只产生 kind 0/3/4, 而房间解析器
#         0xB82A90 **只由 kind==2 进入**; 我们的房间回推疑似根本没到这里。
#   做法: 在 0xB82A90 入口插跳板, 只把"命中计数 + 入参"写进代码洞数据区,
#         **不在客户端内部调用任何系统 API**, 由 nt10 轮询读出并打印。
#   判据: 命中数恒 0 ⇒ 证实"回推没进房间子系统"。
# ======================================================================
ROOMPROBE_VA = 0x00B82A90
ROOMPROBE_DATA_OFF = 0x1800
ROOMPROBE_FLAG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "roomprobe.on")

# 2026-11-03 追加两个下游探针，用来定位链条断点：
#   0x7E7C90 = dwLobbyImp[+0x4F0]->vt[6] 之后(**不是** 0x7F1060)的"按 C 匹配房槽"派发器。
#              args = (C.lo, C.hi, A.lo, A.hi, ctx, D_ptr, D_len)
#              命中 ⇒ 房间推送确实走到了"找槽"这一步。
#   0x6371F0 = 槽回调(slot+0x25B8)。args = (C.lo, C.hi, ?, ?, ctx, D_ptr, D_len)
#              命中 ⇒ blob D 被房间处理器受理。
MATCHPROBE_VA = 0x007E7C90
MATCHPROBE_DATA_OFF = 0x1900
ROOMHANDLER_VA = 0x006371F0
ROOMHANDLER_DATA_OFF = 0x1A00
# ★ 类型读取点：0x634870 内 `mov edx,[ebp+0x1c]` 之前一条刚 movzx 出类型 ⇒ 此处 EAX = 类型号。
#   (所以本探针只看 EAX，栈参数无意义——esp 已下移 0xdbc)
TYPE_VA = 0x006348CE
TYPE_DATA_OFF = 0x1B00
# ★ 类型派发器入口：args = (roomObj, p1..p5)，其中 **arg5 = 位流读取器对象**。
#   读它的字段即可看到客户端真正解码的字节流。
HANDLER_VA = 0x00634870
HANDLER_DATA_OFF = 0x1C00


def build_probe_tramp(cave_addr, data_addr, back_addr, stolen):
    """通用入口跳板: pushfd/pushad -> 记 this/ret/arg0..arg6 -> 执行被偷指令 -> 跳回。

    数据区布局(每项 4B):
        +0x00 命中计数 | +0x04 this(ecx) | +0x10 ret | +0x14..+0x2C  arg0..arg6
    ★ 全程只用寄存器与那 0x30 字节数据区, **不调用任何系统 API**。
    """
    c = bytearray()
    c += b"\x9C"                                    # pushfd
    c += b"\x60"                                    # pushad (+32, 合计 +36=0x24)
    c += b"\xB8" + struct.pack("<I", data_addr)     # mov eax, data
    c += b"\x8B\x54\x24\x1C"                        # mov edx,[esp+0x1C] 原始 EAX
    c += b"\x89\x50\x08"                            # mov [eax+8], edx
    c += b"\x89\x48\x04"                            # mov [eax+4], ecx   (this)
    c += b"\x8B\x54\x24\x24"                        # mov edx,[esp+0x24] 返回地址
    c += b"\x89\x50\x10"
    for k in range(7):
        # mov edx, [esp + 0x28 + 4k] ; mov [eax + 0x14 + 4k], edx
        c += b"\x8B\x94\x24" + struct.pack("<I", 0x28 + 4 * k)
        c += b"\x89\x50" + bytes([0x14 + 4 * k])
    c += b"\xFF\x00"                                # inc dword [eax]
    c += b"\x61"                                    # popad
    c += b"\x9D"                                    # popfd
    c += stolen
    jmp_from = cave_addr + len(c) + 5
    c += b"\xE9" + struct.pack("<i", back_addr - jmp_from)
    return bytes(c)


def build_roomprobe_tramp(cave_addr, data_addr, back_addr, stolen):
    """沿用旧名(0xB82A90 探针)。"""
    return build_probe_tramp(cave_addr, data_addr, back_addr, stolen)


_PROBE_NAMES = {
    ROOMPROBE_VA: "0xB82A90(房间解析器入口)",
    MATCHPROBE_VA: "0x7E7C90(按C匹配房槽)",
    ROOMHANDLER_VA: "0x6371F0(槽回调/房间blob)",
    TYPE_VA: "0x6348CE(房间消息类型读取,EAX=类型)",
    HANDLER_VA: "0x634870(类型派发器入口,arg5=位流读取器)",
}


def _looks_like_code(orig):
    """判断 rpm 读到的字节是不是"已解密的真代码"，防止把补丁写进仍加密的页。

    ★ 2026-11-03 事故：`0x6371F0` 在 t≈0.6s 读出的是乱码
      (`f6 74 3c 8b ce e8 …` = `div byte[esp+edi-0x75]; into; …`)，
      而重建 PE 同一地址是正常序言 `55 8B EC 83 E4 F8 …`。
      ⇒ TP3 按页延迟解密；把 E9 补丁写进未解密页会毁掉该页，
        客户端随后在解壳段 `0x77BEA9` 以 0xC0000005 崩溃（实测 2/2）。
      判据：常见函数序言。不满足就一直重试，等解密完成再装。
    """
    if len(orig) < 8:
        return False
    if orig[0] == 0x55 and orig[1] == 0x8B and orig[2] == 0xEC:      # push ebp; mov ebp,esp
        return True
    if orig[:4] == b"\x8B\xFF\x55\x8B":                              # mov edi,edi; push ebp; ...
        return True
    if orig[0] == 0x53 and orig[1] == 0x55:                          # push ebx; push ebp
        return True
    return False


def entry_probe_thread(h, log, page, slot_index, stop, va, data_off, deadline=420.0,
                       dump_arg=None, dump_n=0x20, gate_va=None):
    """在 `va` 入口挂跳板，轮询命中计数与入参。

    gate_va: 解密判据用哪个地址的字节（默认 `va` 自己）。★ 钩**函数中段**时必须给
             所属函数的入口地址——中段字节本来就不是函数序言，用 `va` 判断会永远不过门。
    dump_arg: 若给出(0..6)，把该参数当指针，读 dump_n 字节并打印(用于核对线上载荷)。
    """
    cave = page + slot_index * SLOT
    data = cave + data_off
    tag = _PROBE_NAMES.get(va, "0x%08X" % va)
    gate = gate_va if gate_va else va
    t0, installed, last, warned = time.time(), False, -1, False
    while not stop.is_set() and time.time() - t0 < deadline:
        if not installed:
            cand = rpm(h, gate, 16)
            orig = rpm(h, va, 16)
            if (len(orig) == 16 and len(cand) == 16 and any(orig)
                    and _looks_like_code(cand)):
                stolen, n = pick_stolen(orig, va)
                if stolen:
                    stub = build_probe_tramp(cave, data, va + n, stolen)
                    try:
                        ok = (_wpm_code(h, cave, stub) and
                              _wpm_code(h, va,
                                        b"\xE9" + struct.pack("<i", cave - (va + 5))
                                        + b"\x90" * (n - 5)))
                        if ok:
                            installed = True
                            log("-- [RP] %s 探针已挂 t=%.1fs (槽 %d, 偷 %d 字节) 实机16B=%s"
                                % (tag, time.time() - t0, slot_index, n, orig.hex()))
                        else:
                            log("-- [RP] %s 打补丁失败" % tag)
                    except Exception as e:
                        log("-- [RP] %s 安装异常: %r" % (tag, e))
            elif orig and not warned:
                warned = True
                log("-- [RP] %s 目标页尚未解密(字节=%s)，等待后再试"
                    % (tag, orig.hex()))
            if not installed:
                time.sleep(1.0)
                continue
        d = rpm(h, data, 0x30)
        if d and len(d) >= 0x30:
            cnt = int.from_bytes(d[0:4], "little")
            if cnt != last:
                last = cnt
                args = [int.from_bytes(d[0x14 + 4 * k:0x18 + 4 * k], "little") for k in range(7)]
                log("  [RP] %s 命中=%d this=0x%08X ret=0x%08X EAX=0x%08X" %
                    (tag, cnt, int.from_bytes(d[4:8], "little"),
                     int.from_bytes(d[0x10:0x14], "little"),
                     int.from_bytes(d[8:12], "little")))
                log("  [RP]   arg0=0x%08X arg1=0x%08X arg2=0x%08X arg3=0x%08X "
                    "arg4=0x%08X arg5=0x%08X arg6=0x%08X" % tuple(args))
                if dump_arg is not None:
                    p = args[dump_arg]
                    if 0x10000 < p < 0x80000000:
                        b = rpm(h, p, dump_n)
                        if b:
                            log("  [RP]   arg%d[%d]=%s" % (dump_arg, len(b), b.hex()))
                            # 顺带把其中像指针的 dword 各读 0x30 字节(一层追踪)
                            for _k in range(0, min(len(b), dump_n) - 4, 4):
                                _q = int.from_bytes(b[_k:_k + 4], "little")
                                if 0x10000 < _q < 0x80000000:
                                    _bb = rpm(h, _q, 0x30)
                                    if _bb and any(_bb):
                                        log("  [RP]     [arg%d+0x%02X]->0x%08X: %s"
                                            % (dump_arg, _k, _q, _bb.hex()))
        time.sleep(2.0)


def roomprobe_thread(h, log, page, slot_index, stop, deadline=420.0):
    """兼容旧入口：只跑 0xB82A90 那一个探针（新代码请用 entry_probe_thread）。"""
    entry_probe_thread(h, log, page, slot_index, stop, ROOMPROBE_VA,
                       ROOMPROBE_DATA_OFF, deadline)


# ======================================================================
# 房间消息「类型 → 处理器」表 —— **只读** dump(2026-11-03)
#   依据: 0x634870 是房间消息派发器:
#        type = 位流读 8 位 (R_TAG(3)+R_VAL(8), 随后 [reader+0x1c]=1 复位)
#        handler = [type*4 + 0x82E1458]      ; 运行时注册表
#        if (!handler && type <= 0x2E) jmp [type*4 + 0x636F3C]   ; 内建跳表 47 项
#   ★ 0x636F3C 在重建 PE 里是代码(该页在 PE 中亦坏), 必须读实机字节。
#   ★ 本线程**只读、不写一个字节** ⇒ 无闪退风险。
# ======================================================================
ROOMMAP_VAS = (0x636F3C, 0x634870, 0x637000, 0x6371F0, 0x633FE0,
               0x634000, 0x6374E0, 0x637520, 0x633D50, 0x6256C0)
ROOMMAP_DECRYPT_CANARY = 0x006371F0


def roommap_thread(h, log, stop, deadline=420.0):
    t0, last = time.time(), None
    while not stop.is_set() and time.time() - t0 < deadline:
        canary = rpm(h, ROOMMAP_DECRYPT_CANARY, 16)
        if not (canary and _looks_like_code(canary)):
            time.sleep(2.0)
            continue
        rows = ["canary 0x%08X = %s" % (ROOMMAP_DECRYPT_CANARY, canary.hex())]
        tbl = rpm(h, 0x82E1458, 0x2F * 4)
        if tbl:
            ptrs = [int.from_bytes(tbl[4 * k:4 * k + 4], "little") for k in range(0x2F)]
            rows.append("[0x82E1458] 注册表: " +
                        " ".join("%d:0x%08X" % (k, v) for k, v in enumerate(ptrs) if v))
        jt = rpm(h, 0x636F3C, 0x2F * 4)
        if jt:
            ptrs = [int.from_bytes(jt[4 * k:4 * k + 4], "little") for k in range(0x2F)]
            rows.append("0x636F3C 跳表: " +
                        " ".join("%d:0x%08X" % (k, v) for k, v in enumerate(ptrs)))
            # 每个内建处理器的前 16 字节(用来确认是代码 + 后续静态分析)
            for k, v in enumerate(ptrs):
                if 0x400000 < v < 0xEA59000:
                    b = rpm(h, v, 16)
                    if b:
                        rows.append("  table[%2d] -> 0x%08X : %s" % (k, v, b.hex()))
        for va in ROOMMAP_VAS:
            b = rpm(h, va, 16)
            if b:
                rows.append("CODE 0x%08X = %s" % (va, b.hex()))
        g = rpm(h, 0x82E1408, 4)
        if g:
            rows.append("G 0x82E1408 = 0x%08X" % int.from_bytes(g, "little"))
        sig = tuple(rows)
        if sig != last:
            last = sig
            for r in rows:
                log("  [RM] " + r)
        time.sleep(5.0)
    """挂 KDF HMAC, 并把两个入参落盘到 kdf_inputs.txt(供 kdf_probe.py 离线判定)。"""
    cave = page + slot_index * SLOT
    data = cave + KDF_DATA_OFF
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kdf_inputs.txt")
    kdf_sec = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secrets_kdf.txt")
    # ★ 多客户端: 每个会话一行, 供 lobby_server 按"从 0x82 帧读出的会话密钥"配对。
    #   格式: <session_key> <transcript_hash> <challenge> <aes_out> <aes_in> <hmac_out> <hmac_in>
    sess_out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kdf_sessions.txt")
    t0, installed, last, wrote = time.time(), False, 0, 0
    while not stop.is_set() and time.time() - t0 < deadline:
        if not installed:
            orig = rpm(h, KDF_HMAC_VA, 16)
            if len(orig) == 16 and any(orig):
                stolen, n = pick_stolen(orig, KDF_HMAC_VA)
                if stolen:
                    stub = build_kdf_tramp(cave, data, KDF_HMAC_VA + n, stolen)
                    try:
                        # ★ 必须用 _wpm_code: exe 的代码页是只读的, 普通 WriteProcessMemory
                        #   会失败; 它内部 VirtualProtectEx 开写 + 写完刷 icache。
                        ok = (_wpm_code(h, cave, stub) and
                              _wpm_code(h, KDF_HMAC_VA,
                                        b"\xE9" + struct.pack("<i", cave - (KDF_HMAC_VA + 5)) +
                                        b"\x90" * (n - 5)))
                    except Exception as e:
                        ok = False
                        log("-- KDF hook 写入异常: %r" % (e,))
                    if ok and rpm(h, KDF_HMAC_VA, 1) == b"\xE9":
                        installed = True
                        log("-- ★ KDF hook 已挂 0x%08X 偷%d字节 (stub 0x%08X 数据 0x%08X)"
                            % (KDF_HMAC_VA, n, cave, data))
                    else:
                        log("-- KDF hook 写入未生效(页面还没解壳/只读) err=%d, 重试中"
                            % ctypes.get_last_error())
                else:
                    log("-- KDF hook 偷指令失败: %s" % orig[:5].hex(" "))
        else:
            d = rpm(h, data, 0x60)
            if len(d) == 0x60:
                cnt = struct.unpack_from("<I", d, 0x14)[0]
                magic = struct.unpack_from("<I", d, 0x18)[0]
                if cnt and cnt != last:
                    last = cnt
                    ret, a1, a2, a3, a4 = struct.unpack_from("<5I", d, 0)
                    th = d[0x20:0x34]        # transcriptHash 20B
                    sk = d[0x34:0x4C]        # sessionKey 24B
                    log("  [kdf] ★HMAC 命中#%d ret=0x%X arg1=0x%X arg2=0x%X arg3=%d arg4=0x%X (magic=%s)"
                        % (cnt, ret, a1, a2, a3, a4,
                           "OK" if magic == KDF_MAGIC else "0x%X" % magic))
                    log("  [kdf] transcriptHash(20B)=%s" % th.hex(" "))
                    log("  [kdf] sessionKey(24B)    =%s" % sk.hex(" "))
                    log("  [kdf] secret 应为 HMAC-SHA1(key=上面20B, data=上面24B)")
                    if any(th) or any(sk):
                        try:
                            with open(out, "a", encoding="utf-8") as f:
                                f.write("# t=%d hit=%d ret=0x%X arg1=0x%X arg2=0x%X\n"
                                        % (int(time.time()), cnt, ret, a1, a2))
                                f.write("transcript_hash %s\n" % th.hex())
                                f.write("session_key %s\n\n" % sk.hex())
                            wrote += 1
                        except Exception as e:
                            log("  [kdf] 写 %s 失败: %r" % (os.path.basename(out), e))
                    # ★ 直接用两个入参算出四把子密钥 + challenge, 写成 secrets_kdf.txt。
                    #   这样就不必再依赖"读 auth 对象内存槽([sub+0x604..0x60C])"以及
                    #   [sub+0x5E8]==3 的时序 —— 彻底脱开内存快照。
                    #   已实测: 派生结果与内存快照逐字段一致(kdf_probe.py --inputs)。
                    try:
                        import codol_crypto as _cc
                        secret = _cc.hmac_sha1(th, sk)          # key=transcriptHash, data=sessionKey
                        chal = _cc.expand_key(secret, b"CLIENTCHAL", 16)
                        dd = _cc.expand_key(secret, b"BDDATA", 72)
                        body = ("pid %d\nstate 3\nchallenge %s\naes_out %s\naes_in %s\n"
                                "hmac_out %s\nhmac_in %s\n"
                                % (pid, chal[8:16].hex(), dd[40:56].hex(), dd[56:72].hex(),
                                   dd[0:20].hex(), dd[20:40].hex()))
                        tmp = kdf_sec + ".tmp"
                        with open(tmp, "w", encoding="utf-8") as f:
                            f.write(body)
                        os.replace(tmp, kdf_sec)                # 原子替换
                        # ★ 追加一条"会话 → 密钥"记录(lobby_server 按会话密钥查表)
                        try:
                            with open(sess_out, "a", encoding="utf-8") as f:
                                f.write("%s %s %s %s %s %s %s\n" % (
                                    sk.hex(), th.hex(), chal[8:16].hex(),
                                    dd[40:56].hex(), dd[56:72].hex(),
                                    dd[0:20].hex(), dd[20:40].hex()))
                        except Exception as _e2:
                            log("  [kdf] 追加 %s 失败: %r" % (os.path.basename(sess_out), _e2))
                        log("  [kdf] ★ 已按派生结果写出 %s (challenge=%s aes_out=%s)"
                            % (os.path.basename(kdf_sec), chal[8:16].hex(), dd[40:56].hex()))
                        log("  [kdf] ★ 会话记录已追加 %s (会话密钥=%s)"
                            % (os.path.basename(sess_out), sk.hex()))
                    except Exception as e:
                        log("  [kdf] 派生/落盘失败: %r" % (e,))
        # ★ 轮询间隔别太长: 客户端可能在 HMAC 之后**立刻**就连大厅,
        #   1s 的延迟会让 lobby_server 查表扑空(第二轮实测: "不在表里 -> 回退全局密钥")。
        time.sleep(0.15)
    if installed:
        log("-- KDF hook 结束: 命中 %d 次, 落盘 %d 条 -> %s"
            % (last, wrote, os.path.basename(out)))
    else:
        log("-- KDF hook 未挂上(0xBA0D20 一直读不到真码)")


# =====================================================================
# 路线 A：调用**客户端原生碰撞 trace**（sub_46E780, build 1649370）
#   规格来自 ol-mod src/game_server/EngineBindings.cpp（同 build 已核对）:
#     void __usercall sub_46E780(
#         float *end@<ecx>, Bounds *bounds@<edx>,       // Bounds = 6 个 float {mins,maxs}
#         trace_t *results, float *start, int passEntityNum, int contentMask,
#         unsigned __int8, char)                        // 6 个栈参数, caller 清 0x18
#     trace_t = 0x28 字节 (fraction/normal[3]/surfaceFlags/contents/hitType/hitId/
#                          modelIndex/partName/partGroup/allSolid/startSolid/walkable)
#   ★ 客户端被 TP3/TVM 加壳 → 必须加载到真实模块基址上, 且只能在**进程内**核对/调用。
# =====================================================================
TRACE_RVA = 0x6E780
TRACE_DATA_OFF = 0x800
# data 区（相对 data_addr）字段偏移
TR_SEQ, TR_DONE, TR_START, TR_END = 0x00, 0x04, 0x08, 0x14
TR_MINS, TR_MAXS, TR_PASS, TR_MASK = 0x20, 0x2C, 0x38, 0x3C
TR_ARG5, TR_ARG6, TR_RESULT, TR_STATUS = 0x40, 0x44, 0x48, 0x70
TR_MODBASE, TR_FUNCADDR = 0x74, 0x78
TR_PENDING = 0x7C          # ★ u8: Python 置 1 表示"有请求待处理"; 桩**入口立刻清零**(防重入)
TR_DATA_LEN = 0x80

TH32CS_SNAPMODULE_ = 0x00000008 | 0x00000010


class MODULEENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("th32ModuleID", wintypes.DWORD),
                ("th32ProcessID", wintypes.DWORD), ("GlblcntUsage", wintypes.DWORD),
                ("ProccntUsage", wintypes.DWORD), ("modBaseAddr", ctypes.c_void_p),
                ("modBaseSize", wintypes.DWORD), ("hModule", ctypes.c_void_p),
                ("szModule", ctypes.c_char * 256), ("szExePath", ctypes.c_char * 260)]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wintypes.DWORD), ("RegionSize", ctypes.c_size_t),
                ("State", wintypes.DWORD), ("Protect", wintypes.DWORD),
                ("Type", wintypes.DWORD)]


# ol-mod 给的 9 字节函数签名（同 build 1649370）—— 用来在活内存里**现找**真实地址
SCAN_SIGS = [
    ("PmoveSingle", bytes([0x55, 0x8B, 0xEC, 0x81, 0xEC, 0x64, 0x01, 0x00, 0x00])),
    ("AngleVectors", bytes([0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x10, 0xD9, 0xEE, 0x53])),
    ("AnglesToQuaternion", bytes([0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x34, 0xD9, 0x46, 0x04])),
    ("MatrixMultiply", bytes([0x55, 0x8B, 0xEC, 0x8B, 0x4D, 0x08, 0xD9, 0x01, 0xD8])),
    ("AxisToAngles", bytes([0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x28, 0x56, 0x57, 0x8B])),
    ("PMSetPitchValues", bytes([0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x28, 0xA1, 0x40, 0xF2])),
]

# ★ 用自己的 WinDLL 实例设这些原型 —— 绝不能改 nt10 全局的 `k32`:
#   2026-10-04 踩过: 把 k32.CreateToolhelp32Snapshot.restype 改成 HANDLE 后,
#   原有 mods_toolhelp() 里 CloseHandle(snap) 拿到 0xFFFFFFFFFFFFFFFF →
#   OverflowError("int too long to convert")。
k32v = ctypes.WinDLL("kernel32", use_last_error=True)
k32v.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
k32v.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
k32v.Module32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32)]
k32v.Module32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32)]
k32v.CloseHandle.argtypes = [wintypes.HANDLE]
k32v.CloseHandle.restype = wintypes.BOOL
k32v.VirtualQueryEx.restype = ctypes.c_size_t
k32v.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
k32v.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                   ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]

MEM_COMMIT_ = 0x1000
PAGE_GUARD_ = 0x100
EXEC_PROTECT = (0x10, 0x20, 0x40, 0x80)      # EXECUTE / EXECUTE_READ / EXECUTE_READWRITE / EXECUTE_WRITECOPY


# ======================================================================
# marketplace zone 内存扫描(2026-10-05)
#   背景: common_marketplace_lite.ff 的层二静态无法解(见 HANDOFF_20261005_LOBBY_BUGS.md
#   §4.0.1~4.0.2), 但客户端启动时会把它解密后放进内存 —— 这里用**早期句柄**去捞明文。
#   ★ 必须用早期句柄: 客户端被 ACE/TP3 保护, 后开的句柄 VirtualQueryEx 会被拒(err=5);
#     只有进程刚启动时拿到的 h 能一直读(secrets_snapshot_thread 就靠它跑 600s)。
# ======================================================================
MARKETPLACE_SCAN_FLAG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "marketplace-scan.on")


def marketplace_mem_scan_once(h, log, budget_s=45.0):
    """遍历可读提交区, 找 marketplace zone 的已解密副本。返回 [(anchor, va)]。"""
    k32v.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                    ctypes.POINTER(MEMORY_BASIC_INFORMATION),
                                    ctypes.c_size_t]
    k32v.VirtualQueryEx.restype = ctypes.c_size_t
    anchors = [b"common_marketplace_lite", b"IWffs100", b"marketplace"]
    hits = []
    addr = 0
    t0 = time.time()
    mbi = MEMORY_BASIC_INFORMATION()
    while addr < 0x7FFF0000 and time.time() - t0 < budget_s:
        if k32v.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                               ctypes.sizeof(mbi)) == 0:
            addr += 0x1000
            continue
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize or 0)
        if size <= 0:
            addr += 0x1000
            continue
        if (mbi.State == MEM_COMMIT_
                and not (mbi.Protect & (PAGE_GUARD_ | 0x01))):
            off = 0
            while off < size:
                want = int(min(0x100000, size - off))
                d = rpm(h, base + off, want)
                if d:
                    for k in anchors:
                        p = d.find(k)
                        while p >= 0:
                            hits.append((k, base + off + p))
                            p = d.find(k, p + 1)
                off += want
        addr = base + size
    return hits


def _looks_like_zone_data(d, min_strings=400):
    """判断一段内存是否像"解密后的 zone 数据"。

    ★ 2026-10-05 教训: 第一版把每个命中点前后 512KB 都导出来, 结果 9.7GB、
      且绝大多数是 exe 镜像里的字符串表碎片(__FILE__ 路径、dvar 表等)。
      zone 数据的特征是**大量连贯可读字符串**(资产名/脚本名), 用它做判据。
    """
    n = 0
    i = 0
    ln = len(d)
    while i < ln:
        c = d[i]
        if 0x20 <= c < 0x7f:
            j = i
            while j < ln and 0x20 <= d[j] < 0x7f:
                j += 1
            if j - i >= 8:
                n += 1
                if n >= min_strings:
                    return True
            i = j
        else:
            i += 1
    return False


def marketplace_mem_scan_thread(h, log, seconds=240.0, interval=30.0):
    """周期扫 marketplace 明文副本; 只导出**像 zone 数据**的窗口。"""
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mem_marketplace")
    try:
        os.makedirs(outdir, exist_ok=True)
    except Exception:
        pass
    seen = set()
    exported = 0
    deadline = time.time() + seconds
    n = 0
    while time.time() < deadline:
        n += 1
        try:
            hits = marketplace_mem_scan_once(h, log)
        except Exception as e:
            log("  [MKT] 第 %d 轮扫描异常: %r" % (n, e))
            hits = []
        new = 0
        for kind, va in hits:
            key = (kind, va)
            if key in seen:
                continue
            seen.add(key)
            new += 1
            name = kind.decode("latin1", "replace")
            # ★ 只导出"像 zone 数据"的窗口, 且限制总导出量。
            if exported >= 40:
                continue
            chunk = rpm(h, max(0x1000, va - 0x40000), 0x80000)
            if chunk and _looks_like_zone_data(chunk, 600):
                fn = os.path.join(outdir, "zone_%s_0x%08X.bin" % (name[:12], va))
                try:
                    open(fn, "wb").write(chunk)
                    exported += 1
                    log("  [MKT] ★★ 导出 zone 候选 %s @0x%08X (%d 字节)"
                        % (name, va, len(chunk)))
                except Exception:
                    pass
        if new:
            log("  [MKT] 第 %d 轮新增 %d 处命中(累计 %d)" % (n, new, len(seen)))
        time.sleep(interval)


def get_module_base(pid, name):
    """Toolhelp 枚举目标进程模块 —— 取真实基址（ASLR，不能假设 0x400000）。"""
    snap = k32v.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE_, pid)
    if not snap or snap == wintypes.HANDLE(-1).value:
        return None, None
    me = MODULEENTRY32()
    me.dwSize = ctypes.sizeof(MODULEENTRY32)
    try:
        ok = k32v.Module32First(snap, ctypes.byref(me))
        while ok:
            if me.szModule.decode("latin1", "replace").lower() == name.lower():
                return int(me.modBaseAddr or 0), int(me.modBaseSize)
            ok = k32v.Module32Next(snap, ctypes.byref(me))
    finally:
        k32v.CloseHandle(snap)
    return None, None


def scan_code_signatures(h, base, size, log, sigs, budget=96 * 1024 * 1024):
    """在目标进程的**可执行已提交区**里按字节签名找函数（用私有 k32v，不动全局 k32）。

    ★ 为什么需要它: 客户端被 TP3 加壳、**按区/按页解密** ——
      2026-10-04 实测 `base+0x6E780` 的运行时字节与磁盘**完全相同**（还没解壳）；
      而 KDF 所在的 `0xB9C000` 是"已解壳"。所以地址必须**运行时现找**，不能照搬 RVA。
    budget: 最多读多少字节，避免把 240MB 虚拟空间全拖一遍（约 1~3s 量级）。
    """
    found = {}
    addr = base
    limit = base + (size or 0x10000000)
    mbi = MEMORY_BASIC_INFORMATION()
    scanned = 0
    while addr < limit and scanned < budget:
        if not k32v.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                                   ctypes.sizeof(mbi)):
            break
        rbase = int(mbi.BaseAddress or 0)
        rsize = int(mbi.RegionSize or 0)
        if rsize <= 0:
            break
        if (mbi.State == MEM_COMMIT_ and not (mbi.Protect & PAGE_GUARD_)
                and (mbi.Protect & 0xFF) in EXEC_PROTECT):
            for off in range(0, rsize, 0x100000):
                if scanned >= budget:
                    break
                chunk = rpm(h, rbase + off, min(0x100000, rsize - off))
                if not chunk:
                    continue
                scanned += len(chunk)
                for name, sig in sigs:
                    if name in found:
                        continue
                    k = chunk.find(sig)
                    if k >= 0:
                        va = rbase + off + k
                        found[name] = va
                        log("  [SCAN] %-22s 命中 VA 0x%08X (RVA 0x%X)" % (name, va, va - base))
        addr = rbase + rsize
    log("  [SCAN] 已扫描可执行内存 %.1f MB，命中 %d/%d 个签名"
        % (scanned / 1048576.0, len(found), len(sigs)))
    return found


def build_trace_stub(data_addr):
    """生成调用原生 trace 的桩：清 pending -> 读请求 -> 按 __usercall 调用 -> 落结果/状态。

    data 区布局见上面的 TR_* 常量。桩用 EBX 保存 data 指针（callee-saved）。
    ★ 入口**立刻清 PENDING**（防重入：trace 内部若又走到被 hook 的 API，不会再调一次）。
      调用前写 status=-1，成功返回后写 done_seq=req_seq、status=0。
    """
    c = bytearray()
    c += b"\x53"                                     # push ebx
    c += b"\xBB" + struct.pack("<I", data_addr)      # mov ebx, <data>
    c += b"\xC6\x43" + bytes([TR_PENDING]) + b"\x00"  # mov byte [ebx+pend], 0  ← 先清, 防重入
    c += b"\xC7\x43" + bytes([TR_STATUS]) + b"\xFF\xFF\xFF\xFF"   # mov dword [ebx+st], -1
    c += b"\xFF\x73" + bytes([TR_ARG6])              # push [ebx+arg6]  (char)
    c += b"\xFF\x73" + bytes([TR_ARG5])              # push [ebx+arg5]  (u8)
    c += b"\xFF\x73" + bytes([TR_MASK])              # push [ebx+mask]  contentMask
    c += b"\xFF\x73" + bytes([TR_PASS])              # push [ebx+pass]  passEntityNum
    c += b"\x8D\x43" + bytes([TR_START]) + b"\x50"   # lea eax,[ebx+start]; push eax
    c += b"\x8D\x43" + bytes([TR_RESULT]) + b"\x50"  # lea eax,[ebx+result]; push eax
    c += b"\x8D\x4B" + bytes([TR_END])               # lea ecx,[ebx+end]     @ecx
    c += b"\x8D\x53" + bytes([TR_MINS])              # lea edx,[ebx+mins]    @edx (Bounds)
    c += b"\xFF\x53" + bytes([TR_FUNCADDR])          # call dword [ebx+func]
    c += b"\x83\xC4\x18"                             # add esp, 0x18  (caller 清栈)
    c += b"\x8B\x43" + bytes([TR_SEQ])               # mov eax,[ebx+req_seq]
    c += b"\x89\x43" + bytes([TR_DONE])              # mov [ebx+done_seq], eax
    c += b"\xC7\x43" + bytes([TR_STATUS]) + b"\x00\x00\x00\x00"   # mov [ebx+st], 0
    c += b"\x5B"                                     # pop ebx
    c += b"\xC3"                                     # ret
    return bytes(c)


TRACE_PROBES = [("+X", (500.0, 0.0, 0.0)), ("-X", (-500.0, 0.0, 0.0)),
                ("+Y", (0.0, 500.0, 0.0)), ("-Y", (0.0, -500.0, 0.0)),
                ("+Z", (0.0, 0.0, 500.0)), ("-Z", (0.0, 0.0, -500.0))]

# 把 trace 挂在哪些 API 的跳板上（谁先被频繁调用就用谁）。
# ★ 2026-10-04 两轮实测:
#   · 游戏发包**不用 sendto**（整轮 2 次）、**也不用 WSASendTo**（0 次）；
#   · 但它**每秒都在收**战斗服快照 —— 所以把**接收侧**(recvfrom/WSARecvFrom/recv/WSARecv)
#     也列为触发器，这是最稳的"高频游戏线程"入口。
TRACE_TRIGGER_APIS = ("recvfrom", "WSARecvFrom", "recv", "WSARecv",
                      "WSASendTo", "sendto", "send")


def trace_probe_thread(h, log, page, slot_index, pid, exe, stop,
                       origin=(48.0, -572.0, -116.0), rounds=8, deadline=240.0):
    """路线 A 第一步：运行时核对 `base+0x6E780`（ol-mod `TraceRva`），并做轴向 trace。

    ★ 2026-10-04 首轮教训：
      · 客户端 TP3 **按区/按页解密** —— 早期读 `base+0x6E780` 拿到的仍是**磁盘上的加壳字节**
        （实测与文件逐字节相同），此时调用必然炸（甚至可能把游戏带崩）。
      · 所以每轮都要**重新判断解壳状态**，只在"已解壳"时才真正发起调用。
      · 状态字用 **canary**：我们预写 0xDEAD0001；桩入口写 -1；成功返回写 0。
        → 仍是 canary = 远程线程没跑；-1 = 桩跑了但调用没返回（炸了）。
    """
    cave = page + slot_index * SLOT
    data = cave + TRACE_DATA_OFF
    base, size = get_module_base(pid, exe)
    if not base:
        log("-- [TRACE] 取模块基址失败(pid=%d) -> 放弃" % pid)
        return
    func = base + TRACE_RVA
    log("-- [TRACE] 模块基址=0x%08X size=0x%X  目标 = base+0x%X = 0x%08X (ol-mod TraceRva)"
        % (base, size or 0, TRACE_RVA, func))
    blob = b""
    try:
        exe_path = os.path.join(r"E:\使命召唤OL\使命召唤OL", exe)
        if os.path.exists(exe_path):
            blob = open(exe_path, "rb").read()
    except Exception:
        pass
    disk = blob[TRACE_RVA:TRACE_RVA + 16] if len(blob) > TRACE_RVA + 16 else b""

    # 先按签名在活内存里现找一遍（判断"代码区到底解壳没有"、以及函数真实位置）
    log("-- [TRACE] 开始按签名扫描活内存(可执行区)…")
    try:
        found = scan_code_signatures(h, base, size, log, SCAN_SIGS)
    except Exception as e:
        log("  [SCAN] 异常: %r" % (e,))
        found = {}
    if found.get("PmoveSingle"):
        got = found["PmoveSingle"] - base
        log("  [SCAN] PmoveSingle 实测 RVA 0x%X vs ol-mod 0x%X  → 差值 %+d"
            % (got, 0x1CB40, got - 0x1CB40))
        log("  [SCAN] 若差值≠0，则 TraceRva 应修正为 0x%X"
            % (TRACE_RVA + (got - 0x1CB40)))

    stub = build_trace_stub(data)
    try:
        ok = _wpm_code(h, cave, stub)
        log("-- [TRACE] 桩写入 %s (%d 字节 @0x%08X)" % ("成功" if ok else "失败", len(stub), cave))
        if not ok:
            return
    except Exception as e:
        log("-- [TRACE] 桩写入异常: %r" % (e,))
        return

    CANARY = 0xDEAD0001
    t0 = time.time()
    seq, runs = 0, 0
    while not stop.is_set() and time.time() - t0 < deadline:
        runs += 1
        live = rpm(h, func, 16)
        unpacked = bool(live) and any(live) and (not disk or live != disk)
        log("-- [TRACE] 第 %d 轮 t=%.0fs: base+0x%X = %s  解壳判定=%s"
            % (runs, time.time() - t0, TRACE_RVA, live.hex(" "),
               "已解壳(可比对磁盘)" if unpacked else "仍是加壳态/全0"))
        if unpacked:
            buf = bytearray(TR_DATA_LEN)
            struct.pack_into("<I", buf, TR_MODBASE, base)
            struct.pack_into("<I", buf, TR_FUNCADDR, func)
            struct.pack_into("<I", buf, TR_PASS, 0xFFFFFFFF)
            struct.pack_into("<I", buf, TR_MASK, 0xFFFFFFFF)
            results = []
            for name, delta in TRACE_PROBES:
                seq += 1
                struct.pack_into("<I", buf, TR_SEQ, seq)
                struct.pack_into("<I", buf, TR_DONE, 0)
                struct.pack_into("<I", buf, TR_STATUS, CANARY)
                struct.pack_into("<f", buf, TR_START, origin[0])
                struct.pack_into("<f", buf, TR_START + 4, origin[1])
                struct.pack_into("<f", buf, TR_START + 8, origin[2])
                struct.pack_into("<f", buf, TR_END, origin[0] + delta[0])
                struct.pack_into("<f", buf, TR_END + 4, origin[1] + delta[1])
                struct.pack_into("<f", buf, TR_END + 8, origin[2] + delta[2])
                for k in range(3):
                    struct.pack_into("<f", buf, TR_MINS + k * 4, -16.0)
                    struct.pack_into("<f", buf, TR_MAXS + k * 4, 16.0)
                buf[TR_PENDING] = 0                      # 先不带 pending 写整块
                if not wpm(h, data, bytes(buf)):
                    log("  [TRACE] 写请求失败"); return
                # ★ pending 单独写一个字节(近似原子): 避免跳板正好在整块写到一半时触发
                if not wpm(h, data + TR_PENDING, b"\x01"):
                    log("  [TRACE] 置 pending 失败"); return
                got = None
                for _ in range(600):                     # 最多等 ~3s(等一次 sendto)
                    d = rpm(h, data + TR_STATUS, 8)
                    if len(d) == 8:
                        st, dn = struct.unpack_from("<Ii", d, 0)
                        if dn == seq and st != CANARY:
                            got = rpm(h, data + TR_RESULT, 0x28)
                            st_final = st
                            break
                    time.sleep(0.005)
                if got is None or len(got) < 0x24:
                    d2 = rpm(h, data + TR_PENDING + 0, 1)
                    still = d2[0] if d2 else None
                    log("  [TRACE] %-3s 无结果 —— %s"
                        % (name, "pending 一直没被取(该 API 没被调用?)" if still == 1
                           else "pending 被取了但没回结果(调用炸了?)"))
                    continue
                frac, nx, ny, nz = struct.unpack_from("<4f", got, 0)
                sflags, contents, htype = struct.unpack_from("<3I", got, 0x10)
                hid, midx, pname = struct.unpack_from("<3H", got, 0x1C)
                results.append((name, frac))
                log("  [TRACE] %-3s fraction=%.4f normal=(%.3f,%.3f,%.3f) surf=0x%X cont=0x%X "
                    "hitType=%d hitId=%d model=%d part=%d allSolid=%d startSolid=%d walkable=%d"
                    % (name, frac, nx, ny, nz, sflags, contents, htype, hid, midx, pname,
                       got[0x24], got[0x25], got[0x26]))
            if results:
                hits = [r for r in results if r[1] < 0.999]
                log("  [TRACE] %d/%d 条命中几何: %s"
                    % (len(hits), len(results), ", ".join("%s=%.3f" % r for r in results)))
                if hits:
                    log("  [TRACE] ★★ 路线 A 成立：原生 trace 可用")
                    return
        rounds -= 1
        if rounds <= 0:
            break
        time.sleep(20.0)
    log("-- [TRACE] 探针结束（未拿到可用结果）")


def provider_dump_thread(h, log, pid=0, seconds=300.0, interval=5.0,
                         span_before=0x4000, span_after=0x20000):
    """只读: 连接对象 -> [obj+0x608] provider -> vtable+0x0C 后端函数。

    这是 80/70 应答分派链的下一跳(exe 0xBA3A05 的 provider 虚调用)。
    拿到后端函数地址后, 把它所在区间按页 dump 出来, 供离线反汇编,
    从中读出 service=80 的 SKUObj 字段解析顺序。
    ★ 全程只读, 不写目标进程、不发任何应答 —— 不会锁界面。
    """
    LOBBY_OBJ_SLOT = 0x08269774
    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "provider_dump")
    try:
        os.makedirs(outdir, exist_ok=True)
    except Exception:
        pass
    seen = set()
    t0 = time.time()
    while time.time() - t0 < seconds:
        try:
            pv = rpm(h, LOBBY_OBJ_SLOT, 4)
            base = struct.unpack("<I", pv)[0] if len(pv) == 4 else 0
            obj = 0
            if base:
                ov = rpm(h, base + 0x4F4, 4)
                obj = struct.unpack("<I", ov)[0] if len(ov) == 4 else 0
            if not obj:
                time.sleep(interval)
                continue
            pp = rpm(h, obj + 0x608, 4)
            prov = struct.unpack("<I", pp)[0] if len(pp) == 4 else 0
            if not prov or prov in seen:
                time.sleep(interval)
                continue
            seen.add(prov)
            vp = rpm(h, prov, 4)
            vt = struct.unpack("<I", vp)[0] if len(vp) == 4 else 0
            slot = 0
            if vt:
                sv = rpm(h, vt + 0x0C, 4)
                slot = struct.unpack("<I", sv)[0] if len(sv) == 4 else 0
            log("  [PROV] obj=0x%08X provider=0x%08X vtable=0x%08X vtable+0x0C=0x%08X"
                % (obj, prov, vt, slot))
            # dump provider 对象本身 + vtable + 后端函数区间
            for tag, addr, size in (("prov", prov, 0x1000),
                                    ("vt", vt, 0x200),
                                    ("handler", slot, span_before + span_after)):
                if not addr:
                    continue
                start = addr if tag != "handler" else max(0x1000, addr - span_before)
                buf = bytearray()
                cur = start
                end = start + size
                while cur < end:
                    d = rpm(h, cur, int(min(0x1000, end - cur)))
                    if d:
                        buf += d
                    else:
                        buf += b"\x00" * int(min(0x1000, end - cur))
                    cur += 0x1000
                fn = os.path.join(outdir, "%s_%08X_%d.bin" % (tag, start, len(buf)))
                try:
                    open(fn, "wb").write(bytes(buf))
                    log("  [PROV] -> %s" % os.path.basename(fn))
                except Exception as e:
                    log("  [PROV] 写 %s 失败: %r" % (fn, e))
                # ★ 2026-10-07: **沿调用链继续 dump**。
                #   上一轮只 dump 了 handler 自己, 结果它只是个"薄封装",
                #   真正读 SKU 字段的逻辑在它 call 的更深函数里(如 0xE3F240 /
                #   0xB74240), 那些地址不在 144KB 窗口内 -> 反汇编断在这里。
                #   做法: 在刚 dump 的 handler 字节里扫"像代码地址"的 u32
                #   (落在一个合理的代码段区间), 逐个 dump 一份窗口。
                if tag == "handler":
                    # ★ 只跟**直接 call rel32**(确定性调用), 不做全字节扫描 ——
                    #   全扫会产出 4000+ 个假候选(大部分是立即数/数据)。
                    cands = []
                    b = bytes(buf)
                    for k in range(0, len(b) - 5):
                        if b[k] != 0xE8:              # call rel32
                            continue
                        rel = struct.unpack_from("<i", b, k + 1)[0]
                        target = start + k + 5 + rel
                        # 只收**真正含代码的两个区间**(见 PE 节表):
                        #   .tp3 #1 0x401000..0xCA789A
                        #   .tp3 #2 0xCA8000..0xE15A70
                        # 其余区段(如 0xE16000 起那个虚拟巨大的解壳区)会引入大量噪声。
                        in_code = (0x401000 <= target < 0xCA789A
                                   or 0xCA8000 <= target < 0xE15A70)
                        if in_code and not (start <= target < start + size):
                            if target not in cands:
                                cands.append(target)
                    log("  [PROV] handler 内直接 call 目标 %d 个" % len(cands))
                    for ci, cva in enumerate(cands[:16]):
                        cbuf = bytearray()
                        cstart = max(0x1000, cva - 0x1000)
                        cur = cstart
                        cend = cstart + 0x4000
                        while cur < cend:
                            d = rpm(h, cur, int(min(0x1000, cend - cur)))
                            cbuf += d if d else b"\x00" * int(min(0x1000, cend - cur))
                            cur += 0x1000
                        cf = os.path.join(outdir, "call%02d_%08X_%d.bin"
                                          % (ci, cstart, len(cbuf)))
                        try:
                            open(cf, "wb").write(bytes(cbuf))
                            log("  [PROV] -> %s (call 到 0x%08X)"
                                % (os.path.basename(cf), cva))
                        except Exception:
                            pass
        except Exception as e:
            log("  [PROV] 异常: %r" % (e,))
        time.sleep(interval)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"E:\使命召唤OL\使命召唤OL")
    ap.add_argument("--exe", default="codoMP_client_shipRetail.exe")
    ap.add_argument("--mutex", default=r"Global\{5BD75B76-601A-4b20-80C8-D2317C94BB30}")
    ap.add_argument("--keep-others", action="store_true",
                    help="多客户端: 启动前**不要**杀其它 codoMP 实例(否则多个 nt10 互相杀对方的游戏)")
    ap.add_argument("--apis", default="connect,sendto,gethostbyname")
    ap.add_argument("--direct", default="")
    ap.add_argument("--delay", type=float, default=2.5)
    ap.add_argument("--secs", type=int, default=60)
    ap.add_argument("--show", type=int, default=6)
    ap.add_argument("--only-exe", action="store_true")
    ap.add_argument("--out", default="n9.txt")
    ap.add_argument("--trace", action="store_true",
                    help="路线A探针: 运行时调用客户端原生 trace(sub_46E780) 做几条轴向碰撞测试")
    ap.add_argument("--ps-probe", action="store_true",
                    help="出生点/位置探针: 周期性扫客户端内存里的本地 playerstate, "
                         "把 origin/角度写进 player_origin.txt（用来对地图出生点清单）")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    snap = os.path.splitext(os.path.abspath(a.out))[0]
    fh = open(a.out, "w", encoding="utf-8", buffering=1)

    def log(s):
        print(s, flush=True)
        fh.write(s + "\n")

    # ★ 把收到的参数原样打出来 —— 2026-10-04 踩过: run_all 的单客户端路径没透传 --trace,
    #   探针静默没启动。有这行就能一眼看出"参数到底传进来没有"。
    log("-- argv: %s" % (" ".join(sys.argv[1:]) or "(无)"))

    # 补丁规格来自文件(避免命令行开关被环境回滚)
    PS = ""
    pf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patch_spec.txt")
    if os.path.exists(pf):
        try:
            PS = open(pf, encoding="utf-8").read().strip()
        except Exception:
            PS = ""
    log("补丁规格 = %r (来自 patch_spec.txt)" % PS)

    # 允许用 "zN" 占位: 只为把代码洞/cnt 槽位预留出来, 不当 hook 装
    apis = [x for x in a.apis.split(",") if x and not re.fullmatch(r"z\d+", x)]
    # ★ --trace: 自动把碰撞 trace 的触发器 API 加进来(不改 run_all 的默认 --apis,
    #   避免把 recv/WSARecv 这类热路径挂进"日常跑"的配置里)。
    if getattr(a, "trace", False):
        for _nm in TRACE_TRIGGER_APIS:
            if _nm in TRAMP_APIS and _nm not in apis:
                apis.append(_nm)
                log("-- [TRACE] 追加触发器 API: %s" % _nm)
    for d in a.direct.split(","):
        if d.strip():
            apis.append("@" + d.strip())

    # ★ 启动 + 存活校验: 这台机器上"坏启动"(0xC0000005 @ t≈2s)概率约 20-40%,
    #   只要在启动后 4s 内就退出, 就直接重新拉起, 不用让上层 run_all 从头再来。
    p, pid, hm = None, 0, None
    for _try in range(1, 2):
        # ★ 多客户端: 默认会先杀掉**所有** codoMP 实例(单客户端时的清理逻辑)。
        #   但 --clients 2 时两个 nt10 会**互相杀对方的游戏**, 形成拉锯 ->
        #   实测永远只有一个游戏活着(第一份的日志里两次启动都被对方杀掉)。
        #   所以多客户端要加 --keep-others, 只清自己的失败残留。
        if not a.keep_others:
            for n in ("codoMP_client_shipRetail.exe", "TP3Helper.exe"):
                subprocess.run(["taskkill", "/F", "/IM", n], capture_output=True)
        else:
            for n in ("TP3Helper.exe",):
                subprocess.run(["taskkill", "/F", "/IM", n], capture_output=True)
        time.sleep(1)
        hm = k32.CreateMutexW(None, False, a.mutex)
        p = subprocess.Popen([os.path.join(a.root, a.exe)], cwd=a.root)
        pid = p.pid
        t_launch = time.time()
        log("game pid=%d mutex=%s apis=%s  (第 %d 次启动)"
            % (pid, bool(hm), apis, _try))
        alive = True
        for _ in range(16):                 # 观察 4s
            time.sleep(0.25)
            if p.poll() is not None:
                alive = False
                break
        if alive:
            break
        rc = p.poll()
        log("  !! 第 %d 次启动在 %.1fs 内退出 rc=%s(0x%X), 重新拉起"
            % (_try, 4.0, rc, (rc or 0) & 0xFFFFFFFF))
    if p is None or p.poll() is not None:
        log("EXC: 连续 5 次都是坏启动(0xC0000005), 放弃本轮")
        return

    # 早期句柄(实测它到 t=6s 仍可读写; 后开的会被 ACE 拒绝)
    h = k32.OpenProcess(PROC_ALL, False, pid)

    # TAS 注入
    spec = ""
    tf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tas_spec.txt")
    if os.path.exists(tf):
        try:
            spec = open(tf, encoding="utf-8").read().strip()
        except Exception:
            spec = ""
    if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "tas_off.flag")):
        if spec:
            log("★ 跳过 TAS 注入(tas_off.flag 存在) —— 隔离实验用, 原规格 %r" % spec)
        spec = ""
    if spec:
        try:
            q = (spec.split(":") + ["", "", ""])[:3]
            host, port, name = q[0] or "127.0.0.1", int(q[1] or 3074), q[2] or "CODOL"
            img = build_tas_image(host, port, name)
            hn = "TCLS_SHAREDMEMEMORY%d" % pid
            hmap = k32.CreateFileMappingW(wintypes.HANDLE(-1), None, 0x04, 0, len(img), hn)
            vp = k32.MapViewOfFile(hmap, 0x000F001F, 0, 0, len(img)) if hmap else None
            if vp:
                ctypes.memmove(vp, img, len(img))
            log("注入 %s host=%s port=%d name=%s -> %s" % (hn, host, port, name,
                                                          "成功" if vp else "失败"))
        except Exception as e:
            log("注入异常: %r" % (e,))

    # 大厅主机/端口全局的目标(另一位开发者提过填这几个全局可消除"无法连接大厅服务")
    # 规格来自同目录 lobby_spec.txt, 形如 "127.0.0.1:3074:3074"
    # ★ 2026-10-02: 改版后默认【不写这些全局】—— 三方"能进大厅"的实现完全不碰它们,
    #   只靠 hosts + dwauth.ini + 4 个内存补丁。要写的话给 run_all 加 --poke。
    LOBBY_HOST, LOBBY_PORT, LOBBY_HTTPS_PORT = "127.0.0.1", 3074, 3074
    lsp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lobby_spec.txt")
    if os.path.exists(lsp):
        try:
            _s = open(lsp, encoding="utf-8").read().strip()
            if _s:
                _q = (_s.split(":") + ["", "", ""])[:3]
                LOBBY_HOST = _q[0] or LOBBY_HOST
                LOBBY_PORT = int(_q[1]) if _q[1].strip().isdigit() else LOBBY_PORT
                LOBBY_HTTPS_PORT = int(_q[2]) if _q[2].strip().isdigit() else LOBBY_HTTPS_PORT
        except Exception as e:
            log("lobby_spec 解析异常: %r" % (e,))
    log("大厅全局目标 host=%s 明文TCP端口=%d HTTPS端口=%d (来自 lobby_spec.txt)"
        % (LOBBY_HOST, LOBBY_PORT, LOBBY_HTTPS_PORT))

    # ★ 三方"能进大厅"的核心: 4 个兼容补丁。后台反复尝试, 等 .tp3 段解壳后再打。
    threading.Thread(target=compat_patch_thread, args=(h, log), daemon=True).start()
    log("-- [兼容补丁] 后台线程已启动 (最多等 %.0fs 解壳)" % COMPAT_DEADLINE)
    # ★ 会话密钥快照(供 lobby_server 解密 0x85) —— 服务端进程读游戏内存会被拦, 所以由 nt10 读
    threading.Thread(target=secrets_snapshot_thread, args=(h, log, pid), daemon=True).start()
    log("-- [secrets] 密钥快照线程已启动 -> %s" % SECRETS_PATH)
    # ★ marketplace zone 内存扫描(默认关, 写 marketplace-scan.on 打开):
    #   用同一个**早期句柄**去捞 common_marketplace_lite 的已解密副本。
    if os.path.exists(MARKETPLACE_SCAN_FLAG):
        threading.Thread(target=marketplace_mem_scan_thread,
                         args=(h, log), daemon=True).start()
        log("-- [MKT] marketplace 内存扫描线程已启动 (marketplace-scan.on)")
    # ★ SKU/目录记录数组扫描(默认关, 写 sku-scan.on 打开):
    #   按"定长记录 + 首字段递增 id"的形态找客户端自己那份目录。
    SKU_SCAN_FLAG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sku-scan.on")
    if os.path.exists(SKU_SCAN_FLAG):
        def _sku_scan(hh, lg):
            try:
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                import _scan_sku_arrays as ssa
                t0 = time.time()
                n = 0
                while time.time() - t0 < 300.0:
                    n += 1
                    try:
                        hits = ssa.scan_marketplace_sku_arrays(hh, lg)
                    except Exception as e:
                        lg("  [SKU] 扫描异常: %r" % (e,))
                        hits = []
                    if hits:
                        lg("  [SKU] 第 %d 轮命中 %d 个目录候选" % (n, len(hits)))
                    time.sleep(20.0)
            except Exception as e:
                log("  [SKU] 线程启动失败: %r" % (e,))
        threading.Thread(target=_sku_scan, args=(h, log), daemon=True).start()
        log("-- [SKU] SKU 目录扫描线程已启动 (sku-scan.on)")
    # ★ dwLobbyImp 的「opcode -> 类型号」表定点 dump(默认关, 写 lobbytable-scan.on 打开):
    #   房间信道的 opcode 由**运行时**填表决定:
    #     · 表在 dwLobbyImp+0x20, 由 ctor 0xB82130 经 0xB7FC20 建好后**运行时插条目**;
    #     · 住在堆上 ⇒ 镜像(241MB)与 client_runtime.bin 都取不到;
    #     · 注册点把名字**从消息流读**(0xB7A550 -> 0xB76BE0), 不是 push imm ⇒ 静态无立即数可查。
    #   ⇒ 只能用早期句柄在运行时把表读出来。节点布局(由 0xB7FAD0 读侧反推):
    #       节点: {+0 = 类型号, +4 = 4 字节 opcode, +8 = 链下一节点}
    #       表  : {+0 = 用量, +4 = 容量(mask = cap-1), +0x10 = bucket 数组}
    LOBBYTABLE_SCAN_FLAG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "lobbytable-scan.on")
    if os.path.exists(LOBBYTABLE_SCAN_FLAG):
        def _lobbytable(hh, lg):
            try:
                t0 = time.time()
                n = 0
                last_sig = None
                last_slot_sig = None
                last_rec = None
                while time.time() - t0 < 280.0:
                    n += 1
                    raw = rpm(hh, 0x8269774, 4)
                    p = int.from_bytes(raw, "little") if (raw and len(raw) == 4) else 0
                    if not p:
                        lg("  [LT] #%d dwLobbyImp 尚未建立" % n)
                        time.sleep(5.0)
                        continue
                    sig_parts = []
                    rows = []
                    for off in (0x08, 0x20, 0xD4):
                        tbl = rpm(hh, p + off, 0x20)
                        if not tbl or len(tbl) < 0x14:
                            continue
                        used = int.from_bytes(tbl[0:4], "little")
                        cap = int.from_bytes(tbl[4:8], "little")
                        bkt = int.from_bytes(tbl[0x10:0x14], "little")
                        sig_parts.append((off, used, cap, bkt))
                        rows.append((off, used, cap, bkt, tbl.hex()))
                    sig = tuple(sig_parts)
                    if sig != last_sig:
                        last_sig = sig
                        lg("  [LT] #%d t=%.0fs dwLobbyImp=0x%08X" % (n, time.time() - t0, p))
                        for off, used, cap, bkt, hx in rows:
                            lg("  [LT]   +0x%02X used=%d cap=0x%X buckets=0x%08X raw=%s"
                               % (off, used, cap, bkt, hx))
                    # ---- 实时状态(每 2s 打一次, 便于与"点击时刻"对齐) ----
                    b4f4 = rpm(hh, p + 0x4F4, 4)
                    conn = int.from_bytes(b4f4, "little") if (b4f4 and len(b4f4) == 4) else 0
                    room = rpm(hh, 0x82E13FC, 4)
                    roomp = int.from_bytes(room, "little") if (room and len(room) == 4) else 0
                    parts = ["t=%.0fs" % (time.time() - t0)]
                    if conn:
                        for no, nn in ((0x5E8, "c5e8"), (0x4F8, "c4f8"), (0xC8, "cc8"),
                                       (0x5B8, "c5b8")):
                            v = rpm(hh, conn + no, 1)
                            parts.append("%s=%s" % (nn, v[0] if v else "-"))
                    else:
                        parts.append("conn=0")
                    if roomp:
                        cnt = rpm(hh, roomp + 0x105D8, 4)
                        parts.append("room=0x%08X" % roomp)
                        parts.append("memberCount=%s"
                                     % (int.from_bytes(cnt, "little") if cnt else "-"))
                        # 成员记录 0: 基址 room+0xE368, 步长 0x1D0; +0x90=准备, +0xB0=阵营
                        rec = rpm(hh, roomp + 0xE368, 0x60)
                        if rec:
                            parts.append("rec0=%s" % rec[:0x28].hex())
                        # ★ 0x635D8F(dwRoomMessageReady 处理器) 实际写的是
                        #   rec+0x94/0x96(u16)、rec+0x98/0x99(u8) —— 旧的 rec+0x90 是错的位置。
                        _r94 = rpm(hh, roomp + 0xE368 + 0x94, 6)
                        if _r94 and len(_r94) >= 6:
                            parts.append("r0[+94..99]=%s" % _r94.hex())
                    else:
                        parts.append("room=0")
                    lg("  [LT] " + " ".join(parts))
                    # ★★ 房间槽表定点 dump（2026-11-03 新增）：
                    #   基址 0xE374650 / 步长 0x25D0 / **2 个槽**（由 0x7E7910 AllocSlot 反推）。
                    #   槽布局（0x7E7C90 与 0x7E7A50 双向对账）：
                    #     +0x00/+0x01 flag、+0x10/+0x14 键 u64、+0x18 成员数、
                    #     +0x40 成员数组(步长 0x60: +0 u64, +8 名字)、
                    #     +0x25B8 cb=0x6371F0 / +0x25BC=0x6374E0 / +0x25C0=0x637520 /
                    #     +0x25C4=0x633D50 / +0x25C8 反向指针=房间对象
                    #   ⇒ 推送体第 3 字段必须 == 这里打出的 key。
                    _slines = []
                    for _si in range(2):
                        _sb = 0xE374650 + _si * 0x25D0
                        _hd = rpm(hh, _sb, 0x1C)
                        if not _hd:
                            continue
                        _klo = int.from_bytes(_hd[0x10:0x14], "little")
                        _khi = int.from_bytes(_hd[0x14:0x18], "little")
                        _cnt = int.from_bytes(_hd[0x18:0x1C], "little")
                        _cb = rpm(hh, _sb + 0x25B8, 0x14)
                        _c0 = int.from_bytes(_cb[0:4], "little") if _cb else 0
                        _bp = int.from_bytes(_cb[0x10:0x14], "little") if _cb else 0
                        _slines.append("  [SLOT%d] f=%d,%d key=0x%016X cnt=%d cb=0x%08X back=0x%08X"
                                       % (_si, _hd[0], _hd[1], (_khi << 32) | _klo, _cnt, _c0, _bp))
                        for _mi in range(3):
                            _mb = rpm(hh, _sb + 0x40 + _mi * 0x60, 0x48)
                            if not _mb:
                                continue
                            _mlo = int.from_bytes(_mb[0:4], "little")
                            _mhi = int.from_bytes(_mb[4:8], "little")
                            _nm = _mb[8:0x48].split(b"\x00")[0]
                            if _mlo or _mhi or _nm:
                                _slines.append("  [SLOT%d.M%d] id=0x%016X name=%r"
                                               % (_si, _mi, (_mhi << 32) | _mlo, _nm[:40]))
                    _ssig = tuple(_slines)
                    if _ssig != last_slot_sig:
                        last_slot_sig = _ssig
                        for _l in _slines:
                            lg("  [ST] " + _l)
                    # ★ 房间成员记录整块 change-gated dump（判"点击后到底有没有字节动"）。
                    if roomp:
                        _rec = rpm(hh, roomp + 0xE368, 0x1D0)
                        if _rec and _rec != last_rec:
                            last_rec = _rec
                            lg("  [REC] room+0xE368[0:0x1D0]=%s" % _rec.hex())
                    for off, used, cap, bkt in sig_parts:
                        if not used or not (0 < cap <= 0x4000):
                            continue
                        for i in range(cap):
                            rb = rpm(hh, bkt + i * 4, 4)
                            node = int.from_bytes(rb, "little") if (rb and len(rb) == 4) else 0
                            guard = 0
                            while node and guard < 64:
                                nb = rpm(hh, node, 12)
                                if not nb or len(nb) < 12:
                                    break
                                typ = int.from_bytes(nb[0:4], "little")
                                key = int.from_bytes(nb[4:8], "little")
                                nxt = int.from_bytes(nb[8:12], "little")
                                lg("  [LT]   +0x%02X bucket[%d] opcode=0x%08X -> type=%d"
                                   % (off, i, key, typ))
                                node = nxt
                                guard += 1
                    time.sleep(2.0)
            except Exception as e:
                log("  [LT] 异常: %r" % (e,))
        threading.Thread(target=_lobbytable, args=(h, log), daemon=True).start()
        log("-- [LT] dwLobbyImp opcode->类型 表 dump 线程已启动 (lobbytable-scan.on)")
    # ★ 商城 6 张 coMarketplace*.csv 定点扫描(默认关, 写 market-tables.on 打开):
    #   客户端真正用的是这 6 张表(由 mp/marketplace.json 索引, 每张带 MD5)。
    #   它们不在任何 .ifs 的 zlib 流里(974 包/146 万流全扫 0 命中), 只存在于
    #   **客户端加载商城后的运行时内存**里。本线程:
    #     (a) 用早期句柄周期扫: zlib 流解压 -> MD5 比对, 命中即落盘到
    #         mkt_assets/co_market/;
    #     (b) 顺带把 Base.dll 的 .tvm0 运行时映像区(资源注册表 0x239B120 所在)
    #         整段 dump 到 mem_tvm0/, 供离线做 RVA 定位。
    MARKET_TABLES_FLAG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "market-tables.on")
    if os.path.exists(MARKET_TABLES_FLAG):
        _mt_secs = max(60.0, float(getattr(a, "secs", 300)) - 5.0)
        _mt_interval = 15.0
        _mtf = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "market-tables_interval.txt")
        try:
            _mt_interval = max(3.0, float(open(_mtf, encoding="ascii").read().strip()))
        except Exception:
            pass

        def _market_tables(hh, _pid, lg):
            try:
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                import _scan_market_tables_live as stl
                stl.scan_live_thread(hh, _pid, log=lg, seconds=_mt_secs,
                                     interval=_mt_interval)
            except Exception as e:
                log("  [MKT2] 线程启动失败: %r" % (e,))

        threading.Thread(target=_market_tables, args=(h, pid, log),
                         daemon=True).start()
        log("-- [MKT2] 商城 6 表定点扫描线程已启动 "
            "(market-tables.on, %.0fs, 间隔 %.0fs)" % (_mt_secs, _mt_interval))
    # ★ 80/70 哨兵探针的扫描线程(与 market-sku-probe.on 联动):
    #   服务端在 80/70 应答里填唯一常量; 客户端解析成功后会把值写进内存。
    #   这里周期扫这些哨兵 -> 命中即证明该线格式被接受。
    PROBE_FLAG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "market-sku-probe.on")
    if os.path.exists(PROBE_FLAG):
        def _probe_scan(hh, lg):
            try:
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                import _scan_probe_sentinels as sps
                sps.scan_live_thread(hh, log=lg,
                                     seconds=max(60.0, a.secs - 5.0),
                                     interval=12.0)
            except Exception as e:
                log("  [PROBE] 线程启动失败: %r" % (e,))
        threading.Thread(target=_probe_scan, args=(h, log), daemon=True).start()
        log("-- [PROBE] 80/70 哨兵扫描线程已启动 (market-sku-probe.on)")
    # ★ provider 只读 dump(默认关, 写 provider-dump.on 打开):
    #   连接对象 -> [obj+0x608] -> vtable+0x0C 后端函数, dump 下来离线反汇编。
    PROV_FLAG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "provider-dump.on")
    if os.path.exists(PROV_FLAG):
        threading.Thread(target=provider_dump_thread,
                         args=(h, log, pid, max(60.0, a.secs - 5.0)),
                         daemon=True).start()
        log("-- [PROV] provider 只读 dump 线程已启动 (provider-dump.on)")
    # ★ 线性内存转储(默认关, 写 memlinear.on 打开; 由 memlinear_after.txt 指定延迟秒数):
    #   进大厅+**打开商城**之后做一次全片转储, 供离线定位 SKU 目录实例。
    MEMLINEAR_FLAG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memlinear.on")
    if os.path.exists(MEMLINEAR_FLAG):
        _delay = 120.0
        _df = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "memlinear_after.txt")
        try:
            _delay = float(open(_df, encoding="ascii").read().strip())
        except Exception:
            pass

        def _memlinear(hh, lg):
            try:
                time.sleep(max(1.0, _delay))
                import _dump_mem_linear as dml
                # ★ 2026-10-07: 目录可用 memlinear_outdir.txt 指定。
                #   不指定则写**带时间戳的新目录** —— 绝不覆盖既有的
                #   mem_linear（用户要求保留，且它是布局反推的基准）。
                _root = os.path.dirname(os.path.abspath(__file__))
                _namef = os.path.join(_root, "memlinear_outdir.txt")
                try:
                    _name = open(_namef, encoding="ascii").read().strip()
                except Exception:
                    _name = ""
                if not _name:
                    _name = "mem_linear_" + time.strftime("%Y%m%d_%H%M%S")
                out = _name if os.path.isabs(_name) else os.path.join(_root, _name)
                lg("  [MEM] 开始线性转储 -> %s (延迟 %.0fs)" % (out, _delay))
                dml.dump_all(hh, out, 3000, log=lg)
            except Exception as e:
                log("  [MEM] 线性转储失败: %r" % (e,))
        threading.Thread(target=_memlinear, args=(h, log), daemon=True).start()
        log("-- [MEM] 线性转储线程已启动 (memlinear.on, 延迟 %.0fs)" % _delay)
    # ★ 定点抓"称号表"(默认关, 写 callsign-scan.on 打开):
    #   进大厅后**打开称号/名片选择界面**并停留, 客户端那时才会把
    #   callsignTitle.csv 解密到内存。这里周期性扫, 一命中就导出。
    CALLSIGN_FLAG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "callsign-scan.on")
    if os.path.exists(CALLSIGN_FLAG):
        def _callsign(hh, lg):
            try:
                import _scan_callsign_mem as scm
                out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "mem_callsign")
                lg("  [CS] 称号扫描线程已启动 -> %s" % out)
                scm.scan_loop(hh, out, lg, seconds=280.0, interval=15.0)
            except Exception as e:
                log("  [CS] 称号扫描失败: %r" % (e,))
        threading.Thread(target=_callsign, args=(h, log), daemon=True).start()
        log("-- [CS] 称号定点扫描线程已启动 (callsign-scan.on)")
    # ★ 实时 SKU 目录采集(默认关, 写 sku-live.on 打开):
    #   轻量、周期扫, 把客户端内存里的 SKU 记录(sku/price)持续并进 sku_live.txt。
    SKULIVE_FLAG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sku-live.on")
    if os.path.exists(SKULIVE_FLAG):
        def _skulive(hh, lg):
            try:
                import _scan_sku_live as ssl
                out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "mem_sku")
                lg("  [SKULIVE] 采集线程已启动 -> %s" % out)
                ssl.scan_loop(hh, out, lg, seconds=280.0, interval=20.0)
            except Exception as e:
                log("  [SKULIVE] 失败: %r" % (e,))
        threading.Thread(target=_skulive, args=(h, log), daemon=True).start()
        log("-- [SKULIVE] 实时 SKU 采集已启动 (sku-live.on)")

    # 早枚举(必须早, 晚了被 ACE 封)
    ml, src = mods_any(pid, h)
    log("早期模块枚举: %d 个 (来源 %s)" % (len(ml), src))
    # 代码洞也在此刻就申请: ACE 之后会拒绝 VirtualAllocEx(实测 t≈2.5s 起 err=5)
    # +8 是给"迟到 hook"(tp 的 3 个取值函数)留代码洞 + 计数器槽; +10 再给房间探针
    page = k32.VirtualAllocEx(h, None, SLOT * (len(apis) + 12),
                              MEM_COMMIT_RESERVE, PAGE_EXECUTE_READWRITE)
    log("早期申请代码洞 0x%08X (err=%d)"
        % (page or 0, 0 if page else ctypes.get_last_error()))

    # 迟到 hook 开关(默认关): 它要往 TenProxy.dll 的代码里写 JMP。
    # 对比发现: nt8 全程不碰 TenProxy 一个字节 -> 稳定停在"连接中";
    #           我们一挂这几个 hook(TenProxy 是 TP3 自己的模块) -> 变成"连接失败"。
    # 而 TenProxy 的关键信息现在由 dumper 直接读内存就能拿到(obj/view/table/逐 tag 长度),
    # 不必再改它的代码。要开就写 late_spec.txt = "on"。
    lf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "late_spec.txt")
    use_late = False
    if os.path.exists(lf):
        try:
            use_late = open(lf, encoding="utf-8").read().strip().lower() in ("on", "1", "yes")
        except Exception:
            use_late = False
    log("迟到 hook(往 TenProxy 写 JMP) = %s (late_spec.txt)" % ("开" if use_late else "关"))

    stop = threading.Event()
    nw = [0]

    # ★ KDF 入参抓取(2026-10-03): 挂 0xBA0D20, 拿 transcriptHash + sessionKey。
    #   ★ 位置必须在 page / stop 之后 —— 上一轮放在前面, 直接
    #     UnboundLocalError("local variable 'page' referenced before assignment") 没起来。
    #   用代码洞的备用槽(申请时留了 +8), 不占用已给 hooks 的槽位。
    try:
        # ★ 先清掉上一轮可能残留的 secrets_kdf.txt —— lobby_server 优先读它,
        #   若本轮 hook 没挂上而文件是旧的, 就会拿旧密钥去解 0x85(bad)。
        _sk = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secrets_kdf.txt")
        if os.path.exists(_sk):
            os.remove(_sk)
            log("-- [KDF] 已清除上一轮的 secrets_kdf.txt (避免用到旧密钥)")
        # ★ 多客户端: 会话表也必须清 —— 否则 lobby_server 可能匹配到**上一轮**的旧会话
        _ss = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kdf_sessions.txt")
        if os.path.exists(_ss):
            os.remove(_ss)
            log("-- [KDF] 已清除上一轮的 kdf_sessions.txt (避免配错会话密钥)")
        threading.Thread(target=kdf_hook_thread,
                         args=(h, log, page, len(apis) + 6, stop, pid), daemon=True).start()
        log("-- [KDF] 抓取线程已启动 (hook 0x%08X, 槽 %d)" % (KDF_HMAC_VA, len(apis) + 6))
    except Exception as _e:
        log("-- [KDF] 线程启动失败: %r" % (_e,))

    # ★ 房间解析器 0xB82A90 入口探针(默认关, 写 roomprobe.on 打开):
    #   判定"服务端回推的房间报文有没有进入房间子系统"。命中恒 0 即证实没进。
    if os.path.exists(ROOMPROBE_FLAG):
        try:
            # ★ 0x6371F0 = 槽回调：它是否被调用 = "C 是否命中了房槽"的**累计**证据
            #   (计数是累计值, 不受 2s 采样只看到最后一条候选的影响)。
            #   它的页在 t≈0.6s 还是加密态 ⇒ 必须等解密后再补(`_looks_like_code` 把关)，
            #   否则补丁写进加密页会让客户端在解壳段崩溃(实测 2/2)。
            for _i, (_va, _doff, _da, _gate) in enumerate((
                    (ROOMPROBE_VA,   0x8000, None, None),
                    (MATCHPROBE_VA,  0x8000, 5,    None),   # arg5 = D_ptr(stack)
                    (ROOMHANDLER_VA, 0x8000, None, None),
                    (TYPE_VA,        0x8000, None, 0x00634870),   # 中段 ⇒ 用入口判解密
                    (HANDLER_VA,     0x8000, 5,    None))):        # arg5 = 位流读取器
                _slot = len(apis) + 8 + _i
                threading.Thread(target=entry_probe_thread,
                                 args=(h, log, page, _slot, stop, _va, _doff),
                                 kwargs={"dump_arg": _da, "dump_n": 0x30,
                                         "gate_va": _gate},
                                 daemon=True).start()
                log("-- [RP] 探针线程已启动 %s (槽 %d)" % (_PROBE_NAMES.get(_va), _slot))
            # ★ 只读的房间「类型→处理器」表 dump(不写任何字节 ⇒ 无闪退风险)
            threading.Thread(target=roommap_thread, args=(h, log, stop),
                             daemon=True).start()
            log("-- [RP] 房间类型表(只读) dump 线程已启动")
        except Exception as _e:
            log("-- [RP] 线程启动失败: %r" % (_e,))

    # ★ 路线A 探针(2026-10-04): 运行时调用客户端原生碰撞 trace(sub_46E780)。
    #   验证"复用引擎碰撞"这条路可行 —— 判据: 某些方向 fraction<1(撞到几何)、
    #   某些方向 fraction==1(空旷)；同时 normal/surfaceFlags 合理。
    if getattr(a, "trace", False):
        try:
            threading.Thread(
                target=trace_probe_thread,
                args=(h, log, page, len(apis) + 7, pid, a.exe, stop),
                kwargs={"rounds": 14, "deadline": max(120.0, float(a.secs) + 30.0)},
                daemon=True).start()
            log("-- [TRACE] 探针线程已启动 (槽 %d, 每 20s 一轮共 14 轮; 先扫签名再决定是否调用)"
                % (len(apis) + 7))
        except Exception as _e:
            log("-- [TRACE] 线程启动失败: %r" % (_e,))

    # ★ 出生点/位置探针（2026-10-04）：扫客户端内存里的本地 playerstate，落盘 origin/角度。
    #   目的：`spawn_from_map.on` 让客户端自己在地图 spawn 里挑，服务端看不到它落在哪 ——
    #   读内存拿到"实际落点"后，才能和地图出生点清单对照（见 HANDOFF §13.36）。
    if getattr(a, "ps_probe", False):
        try:
            threading.Thread(
                target=playerstate_probe_thread,
                args=(h, log, pid),
                kwargs={"seconds": max(120.0, float(a.secs) + 20.0), "interval": 3.0},
                daemon=True).start()
            log("-- [PS] playerstate 探针已启动 (扫 %ss 一轮; 命中预测态后按 %.0f tick≈%.1fms 定点轮询)"
                % (3.0, _PROBE_TICK, _PROBE_POLL * 1000.0))
        except Exception as _e:
            log("-- [PS] 线程启动失败: %r" % (_e,))

    # ★ 弹窗监听: 记录"无法连接大厅服务"到底在【第几秒】弹出, 用来对齐 /auth/ 的时间线
    threading.Thread(target=watch_dialogs, args=(pid, t_launch, log, stop),
                     daemon=True).start()

    def patcher():
        last, t0 = None, time.time()
        while not stop.is_set():
            cur = rpm(h, JNE_ADDR, 2)
            if len(cur) == 2:
                if cur != last:
                    log("  t=%.1fs 0x%08X 字节变为 %s" % (time.time() - t0, JNE_ADDR,
                                                          cur.hex(" ")))
                    last = cur
                if cur[0] == 0x75 and wpm(h, JNE_ADDR, b"\xEB" + cur[1:2]):
                    nw[0] += 1
                    log("  t=%.1fs 75->EB 已写入 (第 %d 次)" % (time.time() - t0, nw[0]))
            time.sleep(0.2)

    threading.Thread(target=patcher, daemon=True).start()

    slots = []
    known_bases = {}          # 模块名(小写) -> 运行时基址, 供 apply_patches 用
    next_slot = 0             # 下一个可用的代码洞/计数器槽
    try:
        log("等待 %.1fs 再装 hook(避开 TP3 在 t≈2s 的完整性检查) ..." % a.delay)
        time.sleep(a.delay)
        # 模块列表: 早期那份优先(ACE 还没封枚举); 但早期枚举经常只拿到十几个模块
        # (进程刚起/还没加载完), ws2_32 很可能不在里面 —— 此时必须继续重试,
        # 直到【ws2_32 出现】或超时。上一轮就是早期只有 11 个 + 不再重试,
        # 导致 ws2_32=0, connect/sendto/getaddrinfo/GetAddrInfoW/gethostbyname 全部跳过。
        need_sock = any(nm in apis and nm not in _K32 and nm not in U32_APIS
                        and not nm.startswith("@") for nm in apis)
        need_whtt = any(nm in WHTTP_APIS for nm in apis)
        early_n = len(ml)

        def has_ws2(lst):
            return any(n.lower().startswith("ws2_32") for n, b, s in lst)

        def need_more(lst):
            if not lst:
                return True
            if need_sock and not has_ws2(lst):
                return True
            if need_whtt and not any(n.lower().startswith("winhttp")
                                     for n, b, s in lst):
                return True
            return not any(n.lower().startswith("kernel32") for n, b, s in lst)

        t_ml, tries = time.time(), 0
        while need_more(ml) and time.time() - t_ml < 60.0:
            try:
                ml2 = mods_any(pid, h)[0]
            except Exception:
                ml2 = []
            if not ml2:
                try:
                    ml2 = mods_peb(h)
                except Exception:
                    ml2 = []
            if ml2 and len(ml2) >= len(ml):
                ml = ml2
            tries += 1
            if tries % 10 == 0:
                log("  ...等 ws2_32 出现: 已重试 %d 次, 当前 %d 个模块, ws2_32=%s"
                    % (tries, len(ml), "有" if has_ws2(ml) else "无"))
            time.sleep(0.3)
        log("模块数=%d (早期枚举 %d, ws2_32 %s)"
            % (len(ml), early_n, "有" if has_ws2(ml) else "!! 仍然没有"))
        if not ml:
            log("!! 模块列表为空 —— 典型症状: 不是管理员窗口。请用【管理员 PowerShell】重跑。")
        sysdir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "SysWOW64")
        rvas = export_rva(os.path.join(sysdir, "ws2_32.dll"), apis)
        ws2 = next((b for n, b, s in ml if n.lower().startswith("ws2_32")), 0)
        log("ws2_32=0x%08X 导出=%s" % (ws2, {k: hex(v) for k, v in rvas.items()}))
        # WinHttp(大厅 HTTP 层): WINHTTP.dll 导出是真函数(不走转发), 用导出表+基址定位
        need_whtt = any(nm in WHTTP_APIS for nm in apis)
        wht_base, wht_rvas = 0, {}
        if need_whtt:
            wht_rvas = export_rva(os.path.join(sysdir, "winhttp.dll"),
                                  [nm for nm in apis if nm in WHTTP_APIS])
            wht_base = next((b for n, b, s in ml
                             if n.lower().startswith("winhttp")), 0)
            log("winhttp 基址=0x%08X 导出=%s" % (wht_base,
                                                 {k: hex(v) for k, v in wht_rvas.items()}))
        if not page:
            page = k32.VirtualAllocEx(h, None, SLOT * (len(apis) + 12),
                                      MEM_COMMIT_RESERVE, PAGE_EXECUTE_READWRITE)
        if not page:
            log("VirtualAllocEx 失败 err=%d" % ctypes.get_last_error())
            return
        log("代码洞 0x%08X" % page)

        # kernel32 / user32 导出与基址 (选项 A)
        k32_base = u32_base = 0
        k32_rvas = u32_rvas = {}
        need_k32 = any(nm in K32_APIS for nm in apis)
        need_u32 = any(nm in U32_APIS for nm in apis)
        sysdir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "SysWOW64")
        if need_k32:
            k32_rvas = export_rva(os.path.join(sysdir, "kernel32.dll"),
                                  [nm for nm in apis if nm in K32_APIS])
            k32_base = next((b for n, b, s in ml if n.lower().startswith("kernel32")), 0)
            log("kernel32 基址=0x%08X 导出=%s" % (k32_base, {k: hex(v) for k, v in k32_rvas.items()}))
        if need_u32:
            u32_rvas = export_rva(os.path.join(sysdir, "user32.dll"),
                                  [nm for nm in apis if nm in U32_APIS])
            u32_base = next((b for n, b, s in ml if n.lower().startswith("user32")), 0)
            log("user32 基址=0x%08X 导出=%s" % (u32_base, {k: hex(v) for k, v in u32_rvas.items()}))

        for nm in apis:
            mode, str_off, wide = "args", 4, False
            if nm.startswith("@"):
                spec2 = nm[1:]
                if ":" in spec2 and not spec2.startswith("0x"):
                    mname, _, mrva = spec2.partition(":")
                    mb, t_w = 0, time.time()
                    while time.time() - t_w < 30:
                        ml2 = mods_peb(h) or ml
                        mb = next((b for n, b, s in ml2
                                   if n.lower() == mname.lower()
                                   or n.lower().startswith(mname.lower())), 0)
                        if mb:
                            break
                        time.sleep(0.3)
                    if not mb:
                        log("-- %s 30 秒内没看到模块 %s" % (nm, mname))
                        continue
                    known_bases[mname.lower()] = mb
                    tgt = mb + int(mrva, 0)
                    # 用 "tp+0xRVA" 命名, 这样导出段会按 tag/dst/pLen 解释参数
                    nm = "tp+%s" % mrva if mname.lower().startswith("tenproxy") else nm
                    log("-- %s -> %s 基址 0x%08X + %s = 0x%08X" % (nm, mname, mb, mrva, tgt))
                else:
                    tgt = int(spec2, 0)
                t_w = time.time()
                ok = False
                while time.time() - t_w < 30:
                    if rpm(h, tgt, 3) == b"\x55\x8b\xec":
                        ok = True
                        break
                    time.sleep(0.3)
                if not ok:
                    log("-- %s 30 秒内没等到 55 8b ec, 跳过: %s" % (nm, rpm(h, tgt, 5).hex(" ")))
                    continue
            else:
                if nm not in TRAMP_APIS:
                    log("-- %s 跳过(不支持)" % nm)
                    continue
                str_off, wide, mode = TRAMP_APIS[nm]
                if nm in _K32:
                    # 本机 RVA + kernel32 基址 (E:\1\nt8.py 的路子, 不依赖 ws2_32 导出扫描)
                    mb = next((b for n, b, s in ml if n.lower().startswith("kernel32")), 0)
                    if not mb:
                        log("-- %s 找不到 kernel32 基址" % nm)
                        continue
                    known_bases["kernel32.dll"] = mb
                    tgt = mb + _K32[nm]
                    log("-- %s 本机 RVA 0x%X -> 0x%08X (kernel32 基址 0x%08X)"
                        % (nm, _K32[nm], tgt, mb))
                elif nm in rvas and ws2:
                    tgt = ws2 + rvas[nm]
                elif nm in wht_rvas and wht_base:
                    tgt = wht_base + wht_rvas[nm]
                    log("-- %s (winhttp) -> 0x%08X" % (nm, tgt))
                elif nm in k32_rvas and k32_base:
                    tgt = k32_base + k32_rvas[nm]
                elif nm in u32_rvas and u32_base:
                    tgt = u32_base + u32_rvas[nm]
                else:
                    log("-- %s 跳过(无导出/无基址)" % nm)
                    continue
            cave = page + next_slot * 0x400
            cnt = page + SLOT * (next_slot + 1)
            orig = rpm(h, tgt, 16)
            stolen, n = pick_stolen(orig, tgt)
            if not stolen:
                log("-- %s 偷指令失败 (%s)" % (nm, orig[:5].hex(" ")))
                continue
            # ★ 路线A: 给"会频繁发包"的 API 挂上"顺带执行 trace"。
            #   2026-10-04 实测: 游戏发包**不用 sendto** —— 整轮 sendto 只命中 2 次!
            #   UDP 走的是 WSASendTo(send/WSASend 也一并兜上), 靶场里每秒 ~20 次。
            tr_pend = tr_work = None
            if getattr(a, "trace", False) and nm in TRACE_TRIGGER_APIS:
                tr_work = page + (len(apis) + 7) * SLOT
                tr_pend = tr_work + TRACE_DATA_OFF + TR_PENDING
                log("-- [TRACE] 已把 trace 执行挂到 %s 跳板 (pending=0x%08X work=0x%08X)"
                    % (nm, tr_pend, tr_work))
            code = build_tramp(cnt, cnt + 4, stolen, tgt + n, cave, str_off, mode,
                               trace_pending=tr_pend, trace_work=tr_work)
            if not wpm(h, cave, code) or not wpm(h, tgt, b"\xE9" +
                                                 struct.pack("<i", cave - (tgt + 5)) +
                                                 b"\x90" * (n - 5)):
                log("-- %s 写 hook 失败" % nm)
                continue
            log("-- hook %-24s @0x%08X 偷%d字节" % (nm, tgt, n))
            slots.append((nm, cnt, wide, mode))
            next_slot += 1

        t0 = time.time()

        def timeline():
            last = {}
            while not stop.is_set():
                for i, (nm, cnt, wide, mode) in enumerate(slots):
                    d = rpm(h, cnt, BUF_LEN)
                    if len(d) < 4:
                        continue
                    try:
                        with open(snap + ".slot%d" % i, "wb") as sf:
                            sf.write(d)
                    except Exception:
                        pass
                    v = struct.unpack_from("<I", d, 0)[0]
                    if v != last.get(nm, 0):
                        extra = ""
                        # 字符串类 hook: 把域名/映射名整串捞出来, 这是"它到底连谁"的直接答案
                        if nm in STR_HOOKS and v > last.get(nm, 0):
                            strs = []
                            for k in range(max(0, v - 6), min(v, RING)):
                                rec = 4 + k * REC
                                if rec + REC > len(d):
                                    break
                                s = follow_str(h, d, rec, wide)
                                if s and s not in strs:
                                    strs.append(s)
                            if strs:
                                extra = "  新串=%s" % strs[-4:]
                        # connect/sendto/bind: 直接从记录内容区解 IP:端口(入口瞬间数据)
                        if nm in SOCK_APIS and v > last.get(nm, 0):
                            for k in range(max(0, v - 4), min(v, RING)):
                                rec = 4 + k * REC
                                if rec + REC > len(d):
                                    break
                                sa = describe_sockaddr(d, rec)
                                if sa and sa not in extra:
                                    extra += "  目标=%s" % sa
                        log("  [t=%5.1fs] %-24s 累计命中 %d%s"
                            % (time.time() - t0, nm, v, extra))
                        last[nm] = v
                time.sleep(0.4)

        threading.Thread(target=timeline, daemon=True).start()

        def late():
            """迟到 hook: 从 OpenFileMappingW 的命中里认出 CTclsProxy 的调用者,
            反推 TenProxy 基址 -> 挂它的取值函数 -> 打"恒成功"补丁。
            必须晚做: TenProxy.dll 是 t≈5s 才加载的。
            注意: 这会往 TenProxy 的代码里写 JMP, 默认关闭(见 use_late)。"""
            nonlocal next_slot
            ocnt = next((c for n2, c, _w, _m in slots if n2 == "OpenFileMappingW"), 0)
            if not ocnt:
                log("-- 迟到 hook 跳过: 本轮没挂 OpenFileMappingW")
                return
            base, callers = 0, []
            t_w = time.time()
            while time.time() - t_w < 15:
                d = rpm(h, ocnt, BUF_LEN)
                if len(d) >= 4:
                    c = struct.unpack_from("<I", d, 0)[0]
                    for k in range(min(c, RING)):
                        rec = 4 + k * REC
                        if rec + REC > len(d):
                            break
                        nm16 = d[rec + 8:rec + 24].decode("utf-16le", "replace")
                        # 注意: 每条只抄 16 字节内容, UTF-16LE 的
                        # "TCLS_SHAREDMEMEMORY<pid>" 只够到 "TCLS_SHA" —— 别拿全名去比
                        if nm16.upper().startswith("TCLS_"):
                            cl = struct.unpack_from("<I", d, rec)[0]
                            if cl not in callers:
                                callers.append(cl)
                for cl in callers:
                    cand = cl - 0x61E8
                    if rpm(h, cand, 2) == b"MZ":
                        base = cand
                        break
                if base:
                    break
                time.sleep(0.5)
            if not base:
                log("-- 迟到 hook: 15s 内没反推出 TenProxy 基址 (TCLS 调用者=%s)"
                    % [hex(x) for x in callers[:4]])
                return
            known_bases["tenproxy.dll"] = base
            log("\n★ 反推 TenProxy 基址 = 0x%08X  (调用者 %s - 0x61E8)"
                % (base, [hex(x) for x in callers[:3]]))

            # 运行时转储 TenProxy 前 0x40000 字节 —— thunk 区(磁盘上是 0)与取值函数体
            # (0x6BD0/0x7CA0/0x7EA0/0x8250/0x8510)都在这段里, 用来消除映射猜测。
            try:
                tb = bytearray()
                for _o in range(0, 0x40000, 0x1000):
                    chunk = rpm(h, base + _o, 0x1000)
                    if len(chunk) < 0x1000:
                        break
                    tb += chunk
                tb = bytes(tb)
                if len(tb) >= 0x1000:
                    tp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           "tp_runtime.bin")
                    open(tp_path, "wb").write(tb)
                    log("  [dump] TenProxy 运行时镜像 %.0fKB -> tp_runtime.bin"
                        % (len(tb) / 1024.0))
                    # thunk 区直接解出 每条 jmp 目标, 打印 RVA 对照
                    md3 = None
                    try:
                        import capstone as _cs
                        md3 = _cs.Cs(_cs.CS_ARCH_X86, _cs.CS_MODE_32)
                    except Exception as _e2:
                        log("  [thunk] capstone 不可用: %s" % _e2)
                    for th in (0x119A, 0x107D, 0x1078, 0x1451, 0x13ED, 0x1226):
                        if md3 is None:
                            break
                        for ins in md3.disasm(tb[th:th + 8], base + th):
                            if ins.mnemonic in ("jmp", "ret"):
                                log("  [thunk] RVA 0x%X -> %s %s"
                                    % (th, ins.mnemonic, ins.op_str))
                                break
                else:
                    log("  [dump] TenProxy 分块读只拿到 %d 字节" % len(tb))
            except Exception as _e:
                log("  [dump] TenProxy 转储失败: %s" % _e)

            if not use_late:
                log("-- 迟到 hook 已关闭: 不改 TenProxy 代码 (仅转储)")
                return

            # 0x7DA0(槽0x24, DWORD 2 参) / 0x7EA0(槽0x28, blob 3 参) 是 pad LoginInfo
            # 和 0x6310 那段共用的取值函数; 0x7EA0 的第 2 个参数 dst 可以为 0
            # (查询长度模式), 这正是"期望尺寸"的最直接来源, 所以给它挂 decl 模式。
            # 0x6BD0 = CTclsProxy::GetLoginInfo(__EH_prolog, 头 3 字节 55 8b ec),
            # 挂上它就能看到服务器列表循环到底跑没跑。
            # 注意 0x7ED0 是 0x7EA0 函数体内部(cmp [ebp+0x10],0), 不是入口, 不能挂。
            # 槽 0x2c(读 tag 14/15/16/19)指向的是另一个函数, 它的 RVA 只能从运行时
            # vtable 里读 —— 由下面的 dumper 打印出来。
            # 2026-10-01: 只挂读 tag7/tag8 的两个真函数(0x8250=vtable[12], 0x8510=vtable[14]),
            # 用 decl 记录 (tag,dst,pLen,seq) + *pLen, 看游戏到底怎么读 —— 这是当前唯一卡点。
            plans = ((0x8250, 4, "decl"), (0x8510, 4, "decl"))
            for rva, soff, md2 in plans:
                tgt = base + rva
                orig = rpm(h, tgt, 16)
                stolen, n = pick_stolen(orig, tgt)
                if not stolen:
                    log("-- tp+0x%X 偷指令失败 (%s)" % (rva, orig[:5].hex(" ")))
                    continue
                s = next_slot
                cave = page + s * 0x400
                ccnt = page + SLOT * (s + 1)
                code = build_tramp(ccnt, ccnt + 4, stolen, tgt + n, cave, soff, md2)
                if not wpm(h, cave, code) or not wpm(h, tgt, b"\xE9" +
                                                     struct.pack("<i", cave - (tgt + 5)) +
                                                     b"\x90" * (n - 5)):
                    log("-- tp+0x%X 写 hook 失败" % rva)
                    continue
                log("-- 迟到 hook tp+0x%X @0x%08X 偷%d字节 (槽 %d, 模式 %s)"
                    % (rva, tgt, n, s, md2))
                slots.append(("tp+0x%X" % rva, ccnt, False, md2))
                next_slot += 1

            if PS:
                try:
                    apply_patches(h, known_bases, ml, PS, log)
                except Exception as e:
                    log("-- patch 异常: %r" % (e,))

        threading.Thread(target=late, daemon=True).start()

        # ---- 运行时取证: 把"游戏自己看到的东西"抄回来 ----
        #  1) exe 的登录读取段(0x241300 起): 磁盘上是加壳态, 只有运行时才是真码
        #  2) exe 全局 [0x82E1580] 指向的 CTclsProxy 对象(它内部 +0x18C4/+0x18C8
        #     就是 TAS 镜像的 记录基址 / table 指针)
        #  3) 逐 tag 打印"记录长度": 直接验证我们的镜像在游戏眼里长什么样
        TAS_OBJ_PTR = 0x82E1580
        got = {"code": False, "rows": None, "vt": None, "tag8": False, "flds": None}

        def dumper():
            exe_base = next((b2 for n2, b2, s2 in ml
                             if n2.lower().startswith("codomp_client")), 0)
            exe_size = next((s2 for n2, b2, s2 in ml
                             if n2.lower().startswith("codomp_client")), 0)
            if exe_base:
                log("  [mod] exe base=0x%08X size=0x%X (末=0x%08X) 场景全局0x%08X %s"
                    % (exe_base, exe_size, exe_base + exe_size, 0x08269774,
                       "在范围内" if exe_base <= 0x08269774 < exe_base + exe_size
                       else "★超出模块范围"))
            # ★ 2026-10-03: 原为 range(40) × sleep(3) = **仅 ~120s 抓取窗口**。
            #   实测问题: `run_all.py --secs 200` 这轮, 窗口在 t≈120s 就关了, 而
            #   .tp3 那几页(0xB80000.. / 0xB9C000.. / 0xBA2000..)在窗口内**还没解壳**
            #   → 读回来全是 0(日志里 `非零 0`), 结果一个 exe 段都没抓到。
            #   .tp3 是**按页惰性解壳**的, 必须一直轮询到"跑完大厅之后"才能拿到真码。
            #   所以改成 240 轮(720s) —— 实际受 nt10 自身的 --secs 限制, 跑满全程即止;
            #   每轮都覆盖写 *_exe_*.bin, 最后留下的就是已解壳那份。
            for _it in range(240):
                if stop.is_set():
                    return
                time.sleep(3)
                # 在 /auth/ 之后按 vtable 找出客户端 auth 对象, 看应答被接受到哪一步
                if _it in (24, 31, 37):
                    probe_auth_object(h, log)
                # 旁证: 直接读游戏的 TCP 连接表(不依赖任何 hook) —— 若 connect 的
                # sockaddr 被解码成垃圾, 这里能看到真实的外连目标与状态(SYN_SENT 等)
                try:
                    import subprocess as _sp
                    _out = _sp.check_output(["netstat", "-ano"], encoding="latin1",
                                            errors="replace", timeout=12)
                except Exception:
                    _out = ""
                if _out:
                    _conns = set()
                    for _ln in _out.splitlines():
                        _p = _ln.split()
                        if len(_p) >= 5 and _p[0].upper() == "TCP" and _p[4] == str(pid):
                            _conns.add("%s [%s]" % (_p[2], _p[3]))
                    _key = "|".join(sorted(_conns))
                    if _key and _key != got.get("conns"):
                        got["conns"] = _key
                        log("  [net] 游戏 TCP 连接 = %s" % " ; ".join(sorted(_conns)))
                    # 谁连了我们的端口? 记 PID/进程名, 用来确认 8446 的来访者到底是不是游戏进程
                    for _ln2 in _out.splitlines():
                        _q2 = _ln2.split()
                        if len(_q2) < 5 or _q2[0].upper() != "TCP":
                            continue
                        _loc, _frn, _stt, _opid = _q2[1], _q2[2], _q2[3], _q2[4]
                        if not any(_loc.endswith(":" + _x) or _frn.endswith(":" + _x)
                                   for _x in ("8443", "8446", "8081")):
                            continue
                        _who = "游戏" if _opid == str(pid) else "?"
                        if _who == "?" and _opid not in got:
                            try:
                                _tl = _sp.check_output(
                                    ["tasklist", "/FI", "PID eq %s" % _opid,
                                     "/FO", "CSV", "/NH"], encoding="gbk",
                                    errors="replace", timeout=8).strip()
                                _who = _tl.split(",")[0].strip('"') or "?"
                            except Exception:
                                _who = "?"
                            got[_opid] = _who
                        elif _who == "?":
                            _who = got.get(_opid, "?")
                        _k2 = "%s -> %s %s pid=%s(%s)" % (_loc, _frn, _stt, _opid, _who)
                        if _k2 not in got.setdefault("who", set()):
                            got["who"].add(_k2)
                            log("  [who] %s" % _k2)
                # ★ 2026-10-01: 按另一位开发者已证结论, 直接写"大厅主机/端口"全局。
                #   注意它们是**绝对 VA**(exe 基址固定 0x400000), 不能再叠 exe_base
                #   —— 之前的 [dump] 就是多加了 0x400000 所以读到空。
                #   主机串: 0x081A76A8 / 0x081A7F34 / 0x081A9784
                #   端口  : 0x081A9780 / 0x081A9EC0 / 0x081A9EC4
                try:
                    _poke_off = os.path.exists(os.path.join(
                        os.path.dirname(os.path.abspath(__file__)), "poke_off.flag"))
                    if _poke_off and not got.get("pokeoff"):
                        got["pokeoff"] = True
                        log("  [lobby] ★ 跳过大厅全局写入(poke_off.flag 存在) —— 隔离实验用")
                    for _va in (() if _poke_off else
                                (0x081A76A8, 0x081A7F34, 0x081A9784)):
                        wpm(h, _va, LOBBY_HOST.encode("ascii", "replace") + b"\x00")
                    # 端口按文档口径分开: 0x081A9EC4 = DW/HTTPS 侧(8443),
                    # 0x081A9780 / 0x081A9EC0 = 大厅明文 TCP 侧(8446)
                    for _va, _vp in (() if _poke_off else
                                     ((0x081A9EC4, LOBBY_HTTPS_PORT),
                                      (0x081A9780, LOBBY_PORT),
                                      (0x081A9EC0, LOBBY_PORT))):
                        wpm(h, _va, struct.pack("<I", _vp))
                    if not got.get("poke"):
                        got["poke"] = True
                        _h = []
                        for _va in (0x081A76A8, 0x081A7F34, 0x081A9784):
                            _b = rpm(h, _va, 32)
                            _h.append("%X=%r" % (_va, _b.split(b"\x00")[0].decode("latin1", "replace")))
                        _p = []
                        for _va in (0x081A9780, 0x081A9EC0, 0x081A9EC4):
                            _b = rpm(h, _va, 4)
                            _p.append("%X=%s" % (_va, struct.unpack("<I", _b)[0] if len(_b) == 4 else "?"))
                        log("  [lobby] 已写大厅全局 主机 %s ; 端口 %s"
                            % (" ".join(_h), " ".join(_p)))
                except Exception as _e:
                    if not got.get("pokeerr"):
                        got["pokeerr"] = True
                        log("  [lobby] 写大厅全局失败: %r" % (_e,))
                # exe 登录读取段(0x241300): 这页是 TP3 加密态, t≈2s 时 dump 出来是乱码,
                # 只有真正跑到那里(登录读取在 t≈40s)才解密 —— 所以每次都覆盖写一份,
                # 最后留下的就是"已经解密"的那份。
                if exe_base:
                    d = rpm(h, exe_base + 0x241300, 0x900)
                    if len(d) >= 0x200:
                        try:
                            open(snap + "_exe_login.bin", "wb").write(d)
                        except Exception:
                            pass
                        if not got["code"]:
                            got["code"] = True
                            log("  [dump] exe 登录读取段 -> %s_exe_login.bin (0x%08X, %d 字节)"
                                % (os.path.basename(snap), exe_base + 0x241300, len(d)))
                    # tag8 字段解析成功后的消费点 0xc40233(VA), 反汇编它才能确定
                    # 9/7/5 个字段分别是什么(host/port/token?) —— 决定 tag8 该填什么。
                    d2 = rpm(h, exe_base + 0xC40000, 0x900)
                    if len(d2) >= 0x200:
                        try:
                            open(snap + "_exe_tag8.bin", "wb").write(d2)
                        except Exception:
                            pass
                        if not got["tag8"]:
                            got["tag8"] = True
                            log("  [dump] tag8 消费段 -> %s_exe_tag8.bin (0x%08X)"
                                % (os.path.basename(snap), exe_base + 0xC40000))
                    # ★ 大厅 0x81/0x83 处理器(0xBA3C70 / 0xBA3BA0): dump 出来才能确定服务端帧
                    #   的精确字节布局 —— 我们发的 0x81 被客户端 RST, 说明格式不对。
                    _lb = bytearray()
                    for _o in range(0, 0x4000, 0x1000):
                        _c = rpm(h, 0x00BA2000 + _o, 0x1000)
                        if len(_c) < 0x1000:
                            break
                        _lb += _c
                    if len(_lb) >= 0x1000:
                        try:
                            open(snap + "_exe_lobby.bin", "wb").write(bytes(_lb))
                        except Exception:
                            pass
                        if not got.get("lobbydump"):
                            got["lobbydump"] = True
                            log("  [dump] 大厅处理器段 -> %s_exe_lobby.bin (0x00BA2000, %d 字节)"
                                % (os.path.basename(snap), len(_lb)))
                    # ★ /auth/ 应答处理段(手册点名的分支点 0xB9A59B / 0xB9A7C7, 以及
                    #   连接对象解析 0xB838A0) —— 磁盘上是 .tp3 加密态(全 0), 只有运行时才是真码
                    _b9 = bytearray()
                    for _o in range(0, 0x1C000, 0x1000):
                        _c = rpm(h, 0x00B80000 + _o, 0x1000)
                        if len(_c) < 0x1000:
                            break
                        _b9 += _c
                    if len(_b9) >= 0x1000:
                        try:
                            open(snap + "_exe_b8b9.bin", "wb").write(bytes(_b9))
                        except Exception:
                            pass
                        if not got.get("b8b9"):
                            got["b8b9"] = True
                            nz = sum(1 for _x in _b9 if _x)
                            log("  [dump] auth应答/连接对象段 -> %s_exe_b8b9.bin (0x00B80000, %d 字节, 非零 %d)"
                                % (os.path.basename(snap), len(_b9), nz))
                    # ★ 2026-10-03 新增: KDF label 引用区 0xB9C000..0xBA2000。
                    #   起因: 借鉴 ol-mod 的 deriveSessionKeys 后, 实测其**输入对不上**我们 build
                    #   (见 HANDOFF.md §10.6)。`CLIENTCHAL`/`BDDATA` 两个 label 在 0xD5A4E0/E8,
                    #   而 0xD5A4D0 附近那张指针表里出现了 0xBA13A0 / 0xBA2A30 / 0xBA3370 ——
                    #   0xBA2A30/0xBA3370 已被 _exe_lobby.bin 覆盖, 唯独 **0xBA13A0 落在
                    #   0xB9C000..0xBA2000 这段没人 dump 的空档里**。补上它才能顺引用找到
                    #   KDF 入参(transcript/根密钥)的组装点。
                    _b9c = bytearray()
                    for _o in range(0, 0x6000, 0x1000):
                        _c = rpm(h, 0x00B9C000 + _o, 0x1000)
                        if len(_c) < 0x1000:
                            break
                        _b9c += _c
                    if len(_b9c) >= 0x1000:
                        try:
                            open(snap + "_exe_b9c.bin", "wb").write(bytes(_b9c))
                        except Exception:
                            pass
                        nz4 = sum(1 for _x in _b9c if _x)
                        # 全 0 = .tp3 这页还没解壳; 一旦变成非 0 再报一次(便于判断抓取是否成功)
                        if not got.get("b9c") or (nz4 and not got.get("b9c_nz")):
                            got["b9c"] = True
                            if nz4:
                                got["b9c_nz"] = True
                            log("  [dump] KDF label 引用段 -> %s_exe_b9c.bin (0x00B9C000, %d 字节, 非零 %d)%s"
                                % (os.path.basename(snap), len(_b9c), nz4,
                                   "  ★ 已解壳" if nz4 else "  (还没解壳, 继续轮询)"))
                    # ★ /auth/ 应答契约要用的字段名字符串(0xD5A114 / 0xD5A31C / 0xD5A32C)
                    #   与常量 0xD59F08 —— 同样是解壳后区
                    _ds = bytearray()
                    for _o in range(0, 0x2000, 0x1000):
                        _c = rpm(h, 0x00D59000 + _o, 0x1000)
                        if len(_c) < 0x1000:
                            break
                        _ds += _c
                    if len(_ds) >= 0x400:
                        try:
                            open(snap + "_exe_d5a.bin", "wb").write(bytes(_ds))
                        except Exception:
                            pass
                        if not got.get("d5a"):
                            got["d5a"] = True
                            nz2 = sum(1 for _x in _ds if _x)
                            log("  [dump] auth字段名区 -> %s_exe_d5a.bin (0x00D59000, %d 字节, 非零 %d)"
                                % (os.path.basename(snap), len(_ds), nz2))
                    # ★ 票据解析器 0xBA9980 / 0xBA95A0 —— 客户端拿 client_ticket 去解析,
                    #   结果要和 DE AD BD EF 比(0xB9A809), 所以要看清它到底按什么结构解析
                    _bt = bytearray()
                    for _o in range(0, 0x6000, 0x1000):
                        _c = rpm(h, 0x00BA6000 + _o, 0x1000)
                        if len(_c) < 0x1000:
                            break
                        _bt += _c
                    if len(_bt) >= 0x1000:
                        try:
                            open(snap + "_exe_ba6.bin", "wb").write(bytes(_bt))
                        except Exception:
                            pass
                        if not got.get("ba6"):
                            got["ba6"] = True
                            nz3 = sum(1 for _x in _bt if _x)
                            log("  [dump] 票据解析器段 -> %s_exe_ba6.bin (0x00BA6000, %d 字节, 非零 %d)"
                                % (os.path.basename(snap), len(_bt), nz3))
                    # 解析成功后字段会拷进这些 exe 全局地址 —— 直接看游戏填入的内容
                    # (这些是**绝对 VA**, 不能再叠 exe_base)
                    flds = []
                    for va in (0x81A76A8, 0xE51184, 0x81A7F34, 0x81A9780,
                               0x81A9784, 0x81A9EC0, 0x81A9EC4):
                        fb = rpm(h, va, 0x40)
                        if fb:
                            txt = fb.split(b"\x00")[0]
                            flds.append("%X:%s" % (va, txt.decode("latin1", "replace")[:24]))
                    if flds:
                        line = "  [dump] tag8 字段 = " + " ".join(flds)
                        if line != got.get("flds"):
                            got["flds"] = line
                            log(line)
                    # 0x8510(tag5) 成功会把"数据指针"写入 exe 全局 0x331caf8:
                    # 非 0 = tag5 读取成功(0x8510 返回 1)。值应为 TAS 内某地址。
                    t5 = rpm(h, exe_base + 0x2F1CAF8, 4)
                    t5v = struct.unpack("<I", t5)[0] if len(t5) == 4 else 0
                    if t5v:
                        line = "  [dump] tag5输出指针 0x331caf8 = 0x%08X" % t5v
                        if line != got.get("t5"):
                            got["t5"] = line
                            log(line)
                pv = rpm(h, TAS_OBJ_PTR, 4)
                obj = struct.unpack("<I", pv)[0] if len(pv) == 4 else 0
                if not obj:
                    continue
                od = rpm(h, obj, 0x1900)
                if len(od) < 0x1900:
                    continue
                try:
                    open(snap + "_obj.bin", "wb").write(od)
                except Exception:
                    pass
                # CTclsProxy 的 vtable 是运行时在堆上建的 —— 从对象头读出来, 打印各槽绝对 VA
                # (不依赖 TenProxy 基址反推; 槽值即函数地址, 可直接拿来 hook)。
                if not got["vt"]:
                    vtp = struct.unpack_from("<I", od, 0)[0]
                    vd = rpm(h, vtp, 0x40) if vtp else b""
                    if len(vd) == 0x40:
                        slots_txt = " ".join(
                            "槽0x%02X=0x%08X" % (k * 4, v)
                            for k, v in enumerate(struct.unpack("<16I", vd)))
                        got["vt"] = slots_txt
                        log("  [dump] vtable=0x%08X %s" % (vtp, slots_txt))
                view, tbl2 = struct.unpack_from("<II", od, 0x18C4)
                if not view or not tbl2:
                    continue
                # 0x8510/0x8250 查找链: [base + obj[0x4c] + (len-1)*4] → 目录项 → 条目 → 字段。
                # 目录偏移存在 obj+0x4C。若为 0(游戏初始化没读), 从 key20 记录 value 兜底写入。
                o4c = struct.unpack_from("<I", od, 0x4C)[0]
                if not o4c:
                    tbl_ptr = struct.unpack_from("<I", od, 0x18C8)[0]
                    if tbl_ptr:
                        r20 = rpm(h, tbl_ptr + 19 * 4, 4)
                        v20 = struct.unpack("<I", r20)[0] if len(r20) == 4 else 0
                        if v20:
                            rr = rpm(h, view + v20 + 4, 4)
                            dirv = struct.unpack("<I", rr)[0] if len(rr) == 4 else 0
                            if dirv:
                                wpm(h, obj + 0x4C, struct.pack("<I", dirv))
                                o4c = dirv
                                log("  [dump] 兜底写入 obj+0x4C = 0x%08X (目录偏移)" % dirv)
                if o4c and not got.get("o4c"):
                    d4v = o4c
                    dir_v = view + d4v
                    dq = rpm(h, dir_v, 0x20)
                    dqword = struct.unpack("<8I", dq) if len(dq) == 0x20 else ()
                    got["o4c"] = True
                    log("  [dump] obj+0x4C = 0x%08X (目录偏移) 目录@0x%08X 前8项 = %s"
                        % (d4v, dir_v, " ".join("%X" % v for v in dqword)))
                magic = rpm(h, view, 4)
                rows = []
                for tag in list(range(1, 32)):
                    tb = rpm(h, tbl2 + (tag - 1) * 4, 4)
                    if len(tb) < 4:
                        break
                    off = struct.unpack("<I", tb)[0]
                    LB = rpm(h, view + off, 4)
                    rows.append("%d:%s" % (tag, struct.unpack("<I", LB)[0]
                                           if len(LB) == 4 else "?"))
                line = ("  [dump] obj=0x%08X view=0x%08X table=0x%08X 魔数=%s\n"
                        "  [dump] tag:记录长度 = %s"
                        % (obj, view, tbl2, magic.hex(" "), " ".join(rows)))
                if line != got["rows"]:
                    got["rows"] = line
                    log(line)

        threading.Thread(target=dumper, daemon=True).start()

        # ---- 大厅"就绪"监视 ----
        # 客户端分发器(0xBA4440)只有在 [obj+0x5E8]==1 时才受理 0x81; 否则 push 9
        # -> 0xBA3420 复位(就是我们看到的 ConnectionReset 10054)。
        # 连接对象(开发者手册 §5.1): obj = [[0x08269774] + 0x4F4], 就绪态 = obj+0x5E8 == 1。
        # 一旦到 1 就写 lobby_ready.flag, lobby_server.py 据此才发 0x81。
        LOBBY_OBJ_SLOT = 0x08269774
        READY_FLAG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "lobby_ready.flag")
        # ★ 多客户端: 再写一份带 pid 的, 便于同时跑多个客户端时区分谁就绪了
        READY_FLAG_PID = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "lobby_ready_%d.flag" % pid)

        def ready_watch():
            prev, t_last = None, 0.0
            while not stop.is_set():
                obj, s5e8, sc8, raw = 0, None, None, "ERR"
                try:
                    pv = rpm(h, LOBBY_OBJ_SLOT, 4)
                    raw = pv.hex(" ") if pv else "ERR"
                    base = struct.unpack("<I", pv)[0] if len(pv) == 4 else 0
                    if base:
                        ov = rpm(h, base + 0x4F4, 4)
                        obj = struct.unpack("<I", ov)[0] if len(ov) == 4 else 0
                    if obj:
                        v1 = rpm(h, obj + 0x5E8, 4)
                        v2 = rpm(h, obj + 0xC8, 4)
                        if len(v1) == 4:
                            s5e8 = struct.unpack("<I", v1)[0]
                        if len(v2) == 4:
                            sc8 = struct.unpack("<I", v2)[0]
                except Exception:
                    raw = "EXC"
                cur = (obj, s5e8, sc8, raw)
                now = time.time()
                if cur != prev or now - t_last > 10:
                    prev, t_last = cur, now
                    log("  [ready] [0x%08X]=%s -> 连接对象=0x%08X 5E8=%s C8=%s"
                        % (LOBBY_OBJ_SLOT, raw, obj, s5e8, sc8))
                try:
                    if s5e8 == 1:
                        _body = "obj=0x%08X 5E8=%s C8=%s pid=%d\n" % (obj, s5e8, sc8, pid)
                        for _f in (READY_FLAG, READY_FLAG_PID):
                            with open(_f, "w", encoding="ascii") as _rf:
                                _rf.write(_body)
                    else:
                        for _f in (READY_FLAG, READY_FLAG_PID):
                            if os.path.exists(_f):
                                os.remove(_f)
                except Exception:
                    pass
                time.sleep(0.05)

        threading.Thread(target=ready_watch, daemon=True).start()

        while time.time() - t0 < a.secs:
            time.sleep(2)
            if p.poll() is not None:
                log("game 退出 rc=%d t=%.1f" % (p.poll(), time.time() - t0))
                break
        else:
            log("game 仍在运行 (%.0fs)" % a.secs)

        ml2 = mods_any(pid, h)[0]

        def own(v):
            for n2, b2, s2 in ml2:
                if b2 <= v < b2 + s2:
                    return "%s+0x%X" % (n2, v - b2)
            return "0x%08X" % v

        for i, (nm, cnt, wide, mode) in enumerate(slots):
            try:
                raw = b""
                sp = snap + ".slot%d" % i
                if os.path.exists(sp):
                    raw = open(sp, "rb").read()
                if len(raw) < 4:
                    raw = rpm(h, cnt, BUF_LEN)
                if len(raw) < 4:
                    log("\n=== %s 无数据 ===" % nm)
                    continue
                c = struct.unpack_from("<I", raw, 0)[0]
                log("\n=== %s 被调用 %d 次 ===" % (nm, c))
                shown = 0
                for k in range(min(c, RING)):
                    rec = 4 + k * REC
                    if rec + REC > len(raw):
                        break
                    caller = struct.unpack_from("<I", raw, rec)[0]
                    argp = struct.unpack_from("<I", raw, rec + 4)[0]
                    cont = raw[rec + 8:rec + 24]   # 每条只有 16 字节内容(UTF-16LE 下 TCLS 名只到 "TCLS_SHA")
                    sc = raw[rec + CODE_OFF:rec + CODE_OFF + CODE_LEN]
                    if nm in SOCK_APIS:
                        s = "raw=" + cont[:8].hex(" ")
                        sa = describe_sockaddr(raw, rec)
                        if sa:
                            s += "  ->  " + sa
                    elif mode in ("args", "decl"):
                        a1, a2, a3, a4 = struct.unpack("<4I", cont)
                        if nm.startswith("tp+"):
                            if a2 == 0:
                                s = "tag=0x%X(%d) 查询长度模式 dst=NULL pLen=0x%X" % (
                                    a1, a1, a3)
                            elif mode == "decl":
                                s = ("tag=0x%X(%d) dst=0x%X pLen=0x%X 声明容量=%d"
                                     % (a1, a1, a2, a3, a4))
                            else:
                                s = "tag=0x%X(%d) dst=0x%X" % (a1, a1, a2)
                        else:
                            s = "a1=0x%X a2=0x%X a3=0x%X a4=0x%X" % (a1, a2, a3, a4)
                    else:
                        s = cont.decode("utf-16le" if wide else "gbk",
                                        "replace").split("\x00")[0]
                        if nm in STR_HOOKS:
                            full = follow_str(h, raw, rec, wide)
                            if full and full != s:
                                s = full
                        if nm in WHTTP_APIS:
                            # WinHttpConnect: a2=pswzServerName(上面的字符串), a3=nServerPort
                            _a1, _a2, _a3, _a4 = struct.unpack("<4I", cont)
                            s = "%s  [a1=0x%X a2=0x%X a3=0x%X(端口=%d) a4=0x%X]" % (
                                s, _a1, _a2, _a3, _a3, _a4)
                    log("  #%-3d 参数=%r 调用者 %s" % (k, s[:120], own(caller)))
                    shown += 1
                    if shown <= a.show:
                        base = max(0, caller - 0x20)
                        for ins in MD.disasm(sc, base):
                            mk = "  <<< 返回地址" if ins.address <= caller < ins.address + ins.size else ""
                            log("         %08X  %-10s %s%s" % (ins.address, ins.mnemonic,
                                                              ins.op_str, mk))
            except Exception as e:
                log("  (导出 %s 出错: %r)" % (nm, e))
    except Exception as e:
        import traceback
        log("EXC: %r" % (e,))
        log(traceback.format_exc())
    finally:
        stop.set()
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "TP3Helper.exe"], capture_output=True)
        log("\n结果已写入 %s" % a.out)
        fh.close()


if __name__ == "__main__":
    main()
