#!/usr/bin/env python3
"""138 动态卷 · 提权侧观察者（经 elevated agent 运行）。

★ 只读：OpenProcess + ReadProcessMemory，不写、不注入、不改目标进程。
★ 关键：**客户端一出现就立刻 OpenProcess 抢早期句柄**（记忆: 只有刚启动时拿到的 h 能一直读;
   t+25s 才开会被 ACE 挡成 0 字节 —— 第 4 轮实测）。
   拿到 h 后，用**同一个 h** 做: ①立即可读性自证 ②定点地址周期采样 ③分块全量转储。

用法: python -I dyn138_watcher.py <outdir> [--full-at 20] [--full-mb 400] [--sample-secs 90]
"""
import argparse
import ctypes
import ctypes.wintypes as wt
import os
import struct
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class PE32(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.c_void_p), ("th32ModuleID", wt.DWORD),
                ("cntThreads", wt.DWORD), ("th32ParentProcessID", wt.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                ("szExeFile", wt.WCHAR * 260)]


class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD), ("PartitionId", wt.DWORD),
                ("RegionSize", ctypes.c_size_t), ("State", wt.DWORD),
                ("Protect", wt.DWORD), ("Type", wt.DWORD)]


k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
k32.OpenProcess.restype = wt.HANDLE
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.ReadProcessMemory.restype = wt.BOOL
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI),
                               ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t

TARGET = "codoMP_client_shipRetail.exe"
CHUNK = 0x10000
READABLE = (0x02 | 0x04 | 0x20 | 0x40 | 0x08 | 0x80)

# 关心的定点地址（静态逆向得到的全局/链头）
ADDRS = [
    0x0849BA30, 0x0849BA34, 0x0849BA3D, 0x084ABA50, 0x00E59D20, 0x082E13FC,
    0x08269774, 0x00E778DC, 0x0C911F60, 0x00E5735B, 0x032B5854, 0x076456FC,
    0x0E7B8644, 0x0E7B6309, 0x0331D408, 0x033303B0,
    # ★ 138 专项新增
    0x076446B0,   # ★★ 开局闸门②：必须 < 3
    0x0849B61C,   # 开局中标志（StartGame apply 置 1）
    0x034027E7,   # 房间 UI 脏标志（cpp* 刷新用）
    0x0E36E4D0,   # 对等玩家槽表基址（19×0x40）
    0x0E69CB0,    # InRoomEventHandler 单例
]


def pids():
    h = k32.CreateToolhelp32Snapshot(2, 0)
    out = []
    e = PE32()
    e.dwSize = ctypes.sizeof(e)
    ok = k32.Process32FirstW(h, ctypes.byref(e))
    while ok:
        if e.szExeFile.lower() == TARGET.lower():
            out.append(int(e.th32ProcessID))
        ok = k32.Process32NextW(h, ctypes.byref(e))
    k32.CloseHandle(h)
    return out


def rd(h, va, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, size, ctypes.byref(got)):
        return buf.raw[:got.value]
    return b""


def u32(h, va):
    d = rd(h, va, 4)
    return struct.unpack("<I", d)[0] if len(d) == 4 else -1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--full-at", type=float, default=20.0)
    ap.add_argument("--full-mb", type=int, default=400)
    ap.add_argument("--sample-secs", type=float, default=90.0)
    ap.add_argument("--wait", type=float, default=180.0)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    mem = os.path.join(a.outdir, "mem")
    os.makedirs(mem, exist_ok=True)
    probe = os.path.join(a.outdir, "probe.txt")
    pf = open(probe, "w", encoding="utf-8")

    def say(s):
        print(s, flush=True)
        pf.write(s + "\n")
        pf.flush()

    # ---- 抢早期句柄 ----
    t0 = time.time()
    pid = None
    while time.time() - t0 < a.wait:
        ps = pids()
        if ps:
            pid = ps[0]
            break
        time.sleep(0.05)
    if pid is None:
        say("!! 等待 %ss 未见客户端" % a.wait)
        return 2
    tseen = time.time() - t0
    h = k32.OpenProcess(0x400 | 0x10, False, pid)
    terr = ctypes.get_last_error()
    t_open = time.time() - t0
    say("pid=%d 出现于 t+%.2fs ; **OpenProcess 于 t+%.2fs** h=%s err=%d"
        % (pid, tseen, t_open, h, terr))
    if not h:
        return 3
    # 立即自证可读
    imm = rd(h, 0x00400000, 4)
    say("立即自证: RPM 4B@0x400000 -> %s err=%d"
        % (imm.hex() if imm else "(空)", ctypes.get_last_error()))

    # ---- 定点周期采样（同一个早期 h）----
    ts = time.time()
    room_seen = None
    while time.time() - ts < a.sample_secs:
        rel = time.time() - t0
        parts = ["%08X=%08X" % (x, u32(h, x) & 0xFFFFFFFF) for x in ADDRS]
        base = u32(h, 0x08269774)
        if base > 0x10000:
            sub = u32(h, base + 0x4F4)
            parts.append("sub=%08X" % sub)
            if sub > 0x10000:
                for off in (0x4F4, 0x5E8, 0x5FC, 0x604, 0x608, 0x60C):
                    parts.append("sub+%X=%08X" % (off, u32(h, sub + off) & 0xFFFFFFFF))

        # ★★ 房间对象关键字段（成员数 / 上限 / 每个成员的 ready@+0x90 与 team@+0x88）
        room = u32(h, 0x082E13FC)
        if room and room > 0x10000:
            if room_seen is not None and room != room_seen:
                say("★ 房间对象已更换: %08X -> %08X" % (room_seen, room))
            room_seen = room
            n = u32(h, room + 0x105D8)
            cap = u32(h, room + 0x105FE)
            st = u32(h, room + 0x0278)
            parts.append("room=%08X n=%s cap=%s built=%s" % (room, n, cap, st))
            if n is not None and 0 < n <= 19:
                mem = []
                for i in range(min(n, 19)):
                    ra = room + 0xE368 + i * 0x1D0
                    uid = rd(h, ra, 8)
                    team = u32(h, ra + 0x88)
                    rdy = u32(h, ra + 0x90)
                    mem.append("[%d uid=%s t=%s r=%s]"
                               % (i, uid.hex()[:16] if uid and len(uid) == 8 else "?",
                                  hex(team) if team is not None else "?",
                                  hex(rdy) if rdy is not None else "?"))
                parts.append("MEM " + " ".join(mem))
        say("t+%.1f %s" % (rel, " ".join(parts)))
        time.sleep(2.0)

        # ---- 到点做一次分块全量转储（仍用早期 h）----
        if abs(rel - a.full_at) < 5.0:
            regs = []
            addr = 0
            while addr < 0x7FFF0000:
                m = MBI()
                n = k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(m),
                                       ctypes.sizeof(m))
                if not n:
                    break
                size = int(m.RegionSize or 0)
                base_a = int(m.BaseAddress or 0)
                if m.State == 0x1000 and size > 0 and not (m.Protect & 0x101) \
                        and (m.Protect & READABLE):
                    regs.append((base_a, size))
                addr = base_a + max(size, 1)
            cap = a.full_mb * 1048576
            written = 0
            kept = 0
            idx = open(os.path.join(a.outdir, "regions.txt"), "w", encoding="utf-8")
            idx.write("# base size file\n")

            # ★★ 修正(138): 之前按地址升序 + 400MB 配额 ⇒ 到不了高堆区(0x3Axxxxxx),
            #   房间/连接对象全在堆里 => "对象字段读不到"是假象。
            #   先按"关键对象的当前值"定位并**优先**转储它们所在区, 再走全量。
            prio = []
            for slot in (0x082E13FC, 0x08269774):
                p = u32(h, slot)
                if p and p > 0x10000:
                    prio.append(p & 0xFFFFF000)
                    q = u32(h, p + 0x4F4)
                    if q and q > 0x10000:
                        prio.append(q & 0xFFFFF000)
            prio = sorted(set(prio))
            if prio:
                say("★ 优先转储关键对象页: %s" % ", ".join("%08X" % x for x in prio))

            def dump_region(base_a, size, tag=""):
                nonlocal written, kept
                out = bytearray()
                off = 0
                while off < size:
                    n = int(min(CHUNK, size - off))
                    d = rd(h, base_a + off, n)
                    out += d if d else b"\x00" * n
                    off += CHUNK
                fn = "r_%08X.bin" % base_a
                try:
                    open(os.path.join(mem, fn), "wb").write(bytes(out))
                except Exception as e:
                    say("  写 %s 失败 %r" % (fn, e))
                    return False
                idx.write("%08X %08X %s\n" % (base_a, size, fn))
                written += len(out)
                kept += 1
                if tag:
                    say("  %s %08X (%d B)" % (tag, base_a, size))
                return True

            # ① 先转关键页(每页 0x10000, 不受 cap 限制)
            for pv in prio:
                for delta in (0, -0x10000, 0x10000):
                    a2 = pv + delta
                    if a2 < 0x10000:
                        continue
                    dump_region(a2, 0x10000, "[prio]")

            # ② 再走全量(受 cap 约束)
            for base_a, size in regs:
                if written >= cap:
                    break
                dump_region(base_a, size)
            idx.close()
            say("★ 分块全量转储: %d 区域, %.1f MB -> %s"
                % (kept, written / 1048576, mem))
    pf.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
