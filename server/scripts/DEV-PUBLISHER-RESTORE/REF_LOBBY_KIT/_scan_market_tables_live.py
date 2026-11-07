# -*- coding: utf-8 -*-
"""运行时/离线定位客户端真正使用的 6 张商城表。

背景(见 HANDOFF_20261006_MAIN.md §3/§7):
  * 客户端商城数据源是 coMarketplace*.csv / unlockFlags.csv 六张表,
    由 mp/marketplace.json 索引, 每张表带一个 MD5, version=1625160。
  * 这六张表不在任何 .ifs 的 zlib 流里(974 包 / 146 万流全扫 0 命中),
    只能从**客户端运行时内存**里取。
  * 资源注册表在 Base.dll 的 .tvm0(TP3 壳虚拟化节), 静态文件里是密文,
    必须抓运行时映像区。

本模块提供三条腿:
  1) scan_buffer()      —— 对一段内存做 zlib 流解压 + MD5 比对, 兼扫表名锚点;
  2) scan_dir()         —— 离线扫 mem_linear / mem_marketplace 等转储目录;
  3) scan_live_thread() —— 由 nt10 用**早期句柄**在线周期扫, 命中即落盘;
     并额外把 Base.dll 的 .tvm0 运行时映像区整段 dump 出来。

用法(离线, 不需要游戏):
    python _scan_market_tables_live.py dir mem_linear
    python _scan_market_tables_live.py dir ..\..\mem_marketplace
用法(离线, 单文件):
    python _scan_market_tables_live.py file mem_linear\r_48110000_0105A000.bin
自检:
    python _scan_market_tables_live.py selftest
"""
import ctypes
import hashlib
import json
import os
import re
import sys
import threading
import time
import zlib
from ctypes import wintypes

ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(ROOT, "mkt_assets", "marketplace.client.json")
OUTDIR = os.path.join(ROOT, "mkt_assets", "co_market")

CHUNK = 8 * 1024 * 1024
OVERLAP = 2 * 1024 * 1024          # zlib 流可能跨块, 重叠留足
MAXOUT = 64 * 1024 * 1024          # 单条流解压上限
FLGS = (0x01, 0x5E, 0x9C, 0xDA)
ZLIB_RE = re.compile(rb"\x78[\x01\x5e\x9c\xda]")

# 表名/结构锚点: 命中说明附近就是商城表加载区, 即使 MD5 匹不上也值得 dump 窗口。
ANCHORS = [
    b"coMarketplaceSKUs.csv",
    b"coMarketplaceProducts.csv",
    b"coMarketplaceProductItems.csv",
    b"coMarketplaceItems.csv",
    b"coMarketplaceDiscounts.csv",
    b"unlockFlags.csv",
    b"mp/marketplace.json",
    b"common_marketplace_lite",
    b"IWffs100",
    b"AS_GetItemIDsFromProduct",
    b"AS_GetProductIDFromSKU",
    b"MKT_UpdateInventory",
    b"selectBestSKU",
    b"promoSkuId",
    b"unlockFlags",
]


# --------------------------------------------------------------------------
# 目标表
# --------------------------------------------------------------------------
def load_targets(manifest=MANIFEST):
    """返回 {大写MD5: 表名}。清单里 version 是数字串, 会被长度过滤掉。"""
    targets = {}
    try:
        j = json.load(open(manifest, "r", encoding="utf-8"))
    except Exception:
        return targets
    for k, v in j.items():
        if isinstance(v, str) and len(v) == 32:
            try:
                int(v, 16)
            except ValueError:
                continue
            targets[v.upper()] = k
    return targets


# --------------------------------------------------------------------------
# 单段扫描
# --------------------------------------------------------------------------
def _inflate_at(buf, i):
    """从 buf[i] 起尝试解一条 zlib 流。

    返回 (解压结果, 该流在 buf 里实际占用的压缩字节数); 失败返回 (None, 0)。
    consumed 用来顺带校验"清单 MD5 是压缩态哈希"的情形。
    """
    try:
        d = zlib.decompressobj(15)
        payload = buf[i:i + MAXOUT]
        out = d.decompress(payload)
        out += d.flush()
    except Exception:
        return None, 0
    if not out:
        return None, 0
    consumed = len(payload) - len(d.unused_data)
    return out, consumed


def scan_buffer(buf, base_va, targets, log=print, found=None, anchors=None,
                dump_dir=None):
    """扫一段内存。返回 (zlib候选数, 命中数)。

    found   : {表名: (va, 解压字节)}, 就地更新
    anchors : {锚点: [(va, region_base), ...]}, 就地更新
    """
    if found is None:
        found = {}
    if anchors is None:
        anchors = {}
    checked = 0

    # 0) 整段本身的 MD5(小表可能整段原样驻留)
    whole = hashlib.md5(buf).hexdigest().upper()
    if whole in targets:
        name = targets[whole]
        log("  ★★ 整段命中 %s @0x%X (%d 字节)" % (name, base_va, len(buf)))
        found[name] = (base_va, buf)

    # 1) 表名锚点
    for a in ANCHORS:
        p = buf.find(a)
        while p >= 0:
            lst = anchors.setdefault(a.decode("latin1"), [])
            if len(lst) < 64:
                lst.append((base_va + p, base_va))
            p = buf.find(a, p + 1)

    # 2) zlib -> MD5
    for m in ZLIB_RE.finditer(buf):
        i = m.start()
        if (0x78 * 256 + buf[i + 1]) % 31 != 0:
            continue
        out, consumed = _inflate_at(buf, i)
        checked += 1
        if not out:
            continue
        h = hashlib.md5(out).hexdigest().upper()
        if h in targets:
            name = targets[h]
            va = base_va + i
            log("  ★★ 命中 %s @0x%X (%d 解压字节)" % (name, va, len(out)))
            found[name] = (va, out)
            if dump_dir:
                try:
                    os.makedirs(dump_dir, exist_ok=True)
                    fn = os.path.join(dump_dir, name)
                    open(fn, "wb").write(out)
                    log("     已写出 %s" % fn)
                except Exception as e:
                    log("     写出失败: %r" % (e,))
        elif consumed:
            # 清单里的 MD5 也可能是"压缩态资产"的哈希
            hc = hashlib.md5(buf[i:i + consumed]).hexdigest().upper()
            if hc in targets:
                name = targets[hc]
                va = base_va + i
                log("  ★★ 命中(压缩态) %s @0x%X (%d 压缩字节)"
                    % (name, va, consumed))
                found[name] = (va, buf[i:i + consumed])
    return checked, len(found)


# --------------------------------------------------------------------------
# 离线扫描
# --------------------------------------------------------------------------
def _base_from_name(path):
    """从 r_<base>_<size>.bin 文件名还原区基址, 便于报告真实 VA。"""
    bn = os.path.basename(path)
    if bn.startswith("r_") and bn.endswith(".bin"):
        try:
            return int(bn.split("_")[1], 16)
        except Exception:
            return 0
    return 0


def scan_file(path, targets, log=print, found=None, anchors=None, dump_dir=None):
    if found is None:
        found = {}
    if anchors is None:
        anchors = {}
    size = os.path.getsize(path)
    file_base = _base_from_name(path)
    off = 0
    checked = 0
    with open(path, "rb") as f:
        tail = b""
        while True:
            block = f.read(CHUNK)
            if not block:
                break
            buf = tail + block
            base = file_base + off - len(tail)
            c, _ = scan_buffer(buf, base, targets, log=log, found=found,
                               anchors=anchors, dump_dir=dump_dir)
            checked += c
            tail = buf[-OVERLAP:]
            off += len(block)
    return checked


def scan_dir(dirpath, log=print, targets=None, dump_dir=None):
    targets = targets or load_targets()
    found, anchors = {}, {}
    files = sorted(f for f in os.listdir(dirpath)
                   if os.path.isfile(os.path.join(dirpath, f)))
    log("扫描目录 %s (%d 个文件, 目标 %d 张表)"
        % (dirpath, len(files), len(targets)))
    t0 = time.time()
    checked = 0
    for n, fn in enumerate(files, 1):
        p = os.path.join(dirpath, fn)
        try:
            c = scan_file(p, targets, log=log, found=found, anchors=anchors,
                          dump_dir=dump_dir)
            checked += c
        except Exception as e:
            log("  %s 扫描失败: %r" % (fn, e))
        if n % 100 == 0:
            log("  ... %d/%d, 已检查 zlib 候选 %d, 用时 %.0fs"
                % (n, len(files), checked, time.time() - t0))
    log("完成: zlib 候选 %d, 命中 %d/%d, 用时 %.0fs"
        % (checked, len(found), len(targets), time.time() - t0))
    return found, anchors


def report(anchors, found, outdir=OUTDIR):
    os.makedirs(outdir, exist_ok=True)
    if anchors:
        p = os.path.join(outdir, "market_anchors.txt")
        with open(p, "w", encoding="utf-8") as f:
            for a in sorted(anchors):
                for va, rb in anchors[a][:32]:
                    f.write("%-32s va=0x%08X region=0x%08X\n" % (a, va, rb))
        print("锚点 %d 类 -> %s" % (len(anchors), p))
    if found:
        p = os.path.join(outdir, "market_tables_found.txt")
        with open(p, "w", encoding="utf-8") as f:
            for name in sorted(found):
                va, data = found[name]
                f.write("%s va=0x%08X len=%d md5=%s\n"
                        % (name, va, len(data), hashlib.md5(data).hexdigest().upper()))
        print("命中 %d 张表 -> %s" % (len(found), p))


# --------------------------------------------------------------------------
# 在线扫描(nt10 早期句柄)
# --------------------------------------------------------------------------
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
MEM_COMMIT = 0x1000
MEM_IMAGE = 0x1000000
MEM_MAPPED = 0x40000
MEM_PRIVATE = 0x20000
PAGE_GUARD = 0x100
PAGE_NOACCESS = 0x01
PAGE_READABLE = (0x02 | 0x04 | 0x08 | 0x10 | 0x20 | 0x40 | 0x80)


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p),
                ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wintypes.DWORD),
                ("RegionSize", ctypes.c_size_t),
                ("State", wintypes.DWORD), ("Protect", wintypes.DWORD),
                ("Type", wintypes.DWORD)]


k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MEMORY_BASIC_INFORMATION),
                               ctypes.c_size_t]
k32.ReadProcessMemory.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                  ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]


def rpm(h, addr, size):
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t(0)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, size,
                                 ctypes.byref(got)):
        return None
    return buf.raw[:got.value]


def iter_regions(h, types=(MEM_PRIVATE, MEM_IMAGE, MEM_MAPPED), start=0):
    mbi = MEMORY_BASIC_INFORMATION()
    addr = start
    while addr < 0x7FFF0000:
        if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                              ctypes.sizeof(mbi)) == 0:
            addr += 0x1000
            continue
        base = int(mbi.BaseAddress or 0)
        size = int(mbi.RegionSize or 0)
        if size <= 0:
            addr += 0x1000
            continue
        if (mbi.State == MEM_COMMIT and mbi.Type in types
                and (mbi.Protect & PAGE_READABLE)
                and not (mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS))
                and size <= 512 * 1024 * 1024):
            yield base, size, mbi.Type, mbi.Protect
        addr = base + size


def scan_live_once(h, log=print, targets=None, found=None, anchors=None,
                   budget_s=120.0, dump_dir=OUTDIR, skip_image=False,
                   start_addr=0):
    """从 start_addr 起遍历可读区并扫描。

    返回 (检查到的 zlib 候选数, 下一轮起始地址)。
    ★ 2026-10-06 修复: 原来每轮都从 0 开始, 预算用尽后高地址区永远扫不到;
      现在返回断点地址, 跨轮续扫, 绕一圈后回到 0。
    """
    targets = targets or load_targets()
    if found is None:
        found = {}
    if anchors is None:
        anchors = {}
    checked = 0
    t0 = time.time()
    nreg = 0
    next_addr = 0
    for base, size, rtype, prot in iter_regions(h, start=start_addr):
        if time.time() - t0 > budget_s:
            next_addr = base
            log("  [MKT] 本轮达到时间预算 %.0fs, 断点=0x%08X 留到下一轮"
                % (budget_s, next_addr))
            break
        if skip_image and rtype == MEM_IMAGE:
            continue
        nreg += 1
        off = 0
        carry = b""
        while off < size:
            want = int(min(CHUNK, size - off))
            d = rpm(h, base + off, want)
            off += want
            if not d:
                carry = b""
                continue
            buf = carry + d
            # 当前 buf 的起始虚拟地址(off 已推进, 减掉 buf 长度即可)
            bva = (base + off) - len(buf)
            c, _ = scan_buffer(buf, bva, targets, log=log, found=found,
                               anchors=anchors, dump_dir=dump_dir)
            checked += c
            carry = buf[-OVERLAP:]
    log("  [MKT] 扫了 %d 个区(从 0x%08X 起), zlib 候选 %d, 累计命中 %d/%d, "
        "用时 %.0fs, 下轮起点=0x%08X"
        % (nreg, start_addr, checked, len(found), len(targets),
           time.time() - t0, next_addr))
    return checked, next_addr


def find_module_base(pid, name="codoMP_client_shipRetailBase.dll"):
    """Toolhelp 枚举目标模块基址。注意: 不要用后开的 OpenProcess 读, 仅供定位。"""
    TH32CS_SNAPMODULE = 0x00000008
    TH32CS_SNAPMODULE32 = 0x00000010
    INVALID = ctypes.c_void_p(-1).value

    class MODULEENTRY32(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("th32ModuleID", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD),
                    ("GlblcntUsage", wintypes.DWORD),
                    ("ProccntUsage", wintypes.DWORD),
                    ("modBaseAddr", ctypes.c_void_p),
                    ("modBaseSize", wintypes.DWORD),
                    ("hModule", ctypes.c_void_p),
                    ("szModule", ctypes.c_char * 256),
                    ("szExePath", ctypes.c_char * 260)]

    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32,
                                        pid)
    if not snap or snap == INVALID:
        return None, None
    me = MODULEENTRY32()
    me.dwSize = ctypes.sizeof(MODULEENTRY32)
    try:
        ok = k32.Module32First(snap, ctypes.byref(me))
        while ok:
            if me.szModule.decode("latin1", "replace").lower() == name.lower():
                return int(me.modBaseAddr or 0), int(me.modBaseSize)
            ok = k32.Module32Next(snap, ctypes.byref(me))
    finally:
        k32.CloseHandle(snap)
    return None, None


def iter_image_bases(h):
    """按 AllocationBase 归并出所有映像模块基址(不依赖 Toolhelp)。"""
    spans = {}
    for base, size, rtype, prot in iter_regions(h, types=(MEM_IMAGE,)):
        # AllocationBase 需要单独查一次
        mbi = MEMORY_BASIC_INFORMATION()
        if k32.VirtualQueryEx(h, ctypes.c_void_p(base), ctypes.byref(mbi),
                              ctypes.sizeof(mbi)) == 0:
            continue
        ab = int(mbi.AllocationBase or 0)
        if not ab:
            continue
        lo, hi = spans.get(ab, (base, base + size))
        spans[ab] = (min(lo, base), max(hi, base + size))
    for ab in sorted(spans):
        yield ab, spans[ab][1] - spans[ab][0]


# 真 Base.dll 的 .tvm0 节签名(见 HANDOFF_20261006_MAIN §3.3)。
# ★ 很多 TenProtect/TGuard 模块也有 .tvm0(如 TerSafe.dll 是 0x310000/0x4C2000),
#   所以必须按签名精确匹配, 否则会 dump 到错模块。
TVM_VA_SIG = 0x19DD000
TVM_VS_SIG = 0x1F5E000


def _parse_sections(h, base):
    """解析模块 base 的 PE 节表, 返回 [(name, va, vs), ...]。"""
    head = rpm(h, base, 0x1000)
    if not head or head[:2] != b"MZ":
        return []
    e_lfanew = int.from_bytes(head[0x3C:0x40], "little")
    if e_lfanew <= 0:
        return []
    hdr = head[e_lfanew:e_lfanew + 0x40]
    if len(hdr) < 0x40 or hdr[:4] != b"PE\x00\x00":
        hdr = rpm(h, base + e_lfanew, 0x40)
        if not hdr or hdr[:4] != b"PE\x00\x00":
            return []
    nsec = int.from_bytes(hdr[6:8], "little")
    optsz = int.from_bytes(hdr[0x14:0x16], "little")
    if not (0 < nsec <= 96):
        return []
    sh_off = e_lfanew + 0x18 + optsz
    sh = rpm(h, base + sh_off, 40 * nsec)
    if not sh:
        return []
    out = []
    for i in range(nsec):
        s = sh[i * 40:(i + 1) * 40]
        if len(s) < 40:
            break
        out.append((s[:8].rstrip(b"\x00"),
                    int.from_bytes(s[12:16], "little"),
                    int.from_bytes(s[8:12], "little")))
    return out


def find_tvm_section(h, log=print, sig=True, only_base=None):
    """找带"真 Base.dll 签名"的 .tvm0 节。

    sig=True 时只认 va=0x19DD000 / vs=0x1F5E000, 避免命中 TGuard/TenProtect
    那些同样带 .tvm0 的模块。
    返回 (模块基址, 模块跨度, .tvm0 RVA, .tvm0 虚拟大小); 找不到返回全 0。
    """
    it = ([(only_base, 0)] if only_base else iter_image_bases(h))
    for base, span in it:
        for nm, va, vs in _parse_sections(h, base):
            if nm != b".tvm0":
                continue
            if sig and (va != TVM_VA_SIG or vs != TVM_VS_SIG):
                log("  [TVM0] 跳过非 Base.dll 的 .tvm0: module=0x%08X rva=0x%X size=0x%X"
                    % (base, va, vs))
                continue
            log("  [TVM0] 节表定位到 Base.dll .tvm0: module=0x%08X rva=0x%X size=0x%X"
                % (base, va, vs))
            return base, span, va, vs
    return 0, 0, 0, 0


def dump_tvm0(h, pid, log=print, outdir=None,
              name="codoMP_client_shipRetailBase.dll",
              lo=0x19DD000, hi=0x3940000):
    """把 Base.dll 的 .tvm0 运行时映像区整段 dump 出来(壳解密后的)。"""
    outdir = outdir or os.path.join(ROOT, "mem_tvm0")
    base, msize = find_module_base(pid, name)
    sec_va, sec_vs = 0, 0
    if base:
        # Toolhelp 基址优先: 在它自己的 PE 节表里找 .tvm0 并校验签名。
        for nm, va, vs in _parse_sections(h, base):
            if nm == b".tvm0":
                sec_va, sec_vs = va, vs
                break
        if (sec_va, sec_vs) != (TVM_VA_SIG, TVM_VS_SIG):
            log("  [TVM0] Toolhelp 基址 0x%08X 的 .tvm0 签名不符(0x%X/0x%X), "
                "改用全局签名搜索" % (base, sec_va, sec_vs))
            sec_va = sec_vs = 0
    else:
        log("  [TVM0] Toolhelp 没拿到模块名, 改用 PE 节表兜底定位")
    if not sec_vs:
        # 只认 Base.dll 的 .tvm0 签名, 避免命中 TerSafe/TenProtect 等同名节
        b2, _span2, sec_va, sec_vs = find_tvm_section(h, log=log)
        if b2:
            base = b2
    if not base:
        log("  [TVM0] 找不到 Base.dll 映像区 (基址未知), 跳过")
        return 0
    if sec_vs:
        a, b = base + sec_va, base + sec_va + sec_vs
    else:
        a, b = base + lo, base + hi
    log("  [TVM0] %s base=0x%08X size=0x%X, dump 0x%08X..0x%08X"
        % (name, base, msize or 0, a, b))
    os.makedirs(outdir, exist_ok=True)
    # ★ 按页读: TP3 壳只对"已被访问过"的页提交/解密, 整块 4MB 读会因
    #   个别不可读页而整块失败。逐页读能把已解密页全部保住, 不可读页跳过。
    total = 0
    cur = a
    run_start = None
    run_buf = bytearray()

    def _flush():
        nonlocal total, run_start, run_buf
        if not run_buf:
            return
        fn = os.path.join(outdir, "tvm0_%08X.bin" % run_start)
        try:
            open(fn, "wb").write(run_buf)
            total += len(run_buf)
        except Exception as e:
            log("  [TVM0] 写 %s 失败: %r" % (fn, e))
        run_start = None
        run_buf = bytearray()

    while cur < b:
        want = int(min(0x1000, b - cur))
        d = rpm(h, cur, want)
        if d:
            if run_start is None:
                run_start = cur
            run_buf += d
        else:
            _flush()
        cur += want
    _flush()
    log("  [TVM0] 完成: %d 字节可读 -> %s" % (total, outdir))
    return total


def scan_live_thread(h, pid, log=print, seconds=600.0, interval=10.0,
                     dump_dir=OUTDIR, do_tvm0=True):
    """周期扫描线程。一命中就把表写到 dump_dir 并继续扫其余表。"""
    targets = load_targets()
    found, anchors = {}, {}
    log("  [MKT] 目标 %d 张表: %s" % (len(targets), ", ".join(sorted(targets.values()))))
    if not targets:
        log("  [MKT] 没有读到 marketplace.client.json, 退出")
        return found, anchors

    # .tvm0 是惰性解密的, 一次早期 dump 可能还是密文 —— 取多个时间点快照。
    # ★ 放到独立线程: 主扫描一轮可能要 180s, 不能把快照拖到扫描之后。
    dump_times = [20.0, 90.0, 180.0, 300.0]
    stop_evt = threading.Event()

    def _tvm_timer():
        t0 = time.time()
        for dt in dump_times:
            while time.time() - t0 < dt:
                if stop_evt.is_set():
                    return
                time.sleep(0.5)
            if stop_evt.is_set():
                return
            try:
                dump_tvm0(h, pid, log=log,
                          outdir=os.path.join(ROOT, "mem_tvm0", "t%03d" % int(dt)))
            except Exception as e:
                log("  [TVM0] t=%.0fs dump 异常: %r" % (dt, e))

    if do_tvm0:
        threading.Thread(target=_tvm_timer, daemon=True).start()

    deadline = time.time() + seconds
    n = 0
    cursor = 0
    while time.time() < deadline and len(found) < len(targets):
        n += 1
        t0 = time.time()
        try:
            _checked, cursor = scan_live_once(
                h, log=log, targets=targets, found=found, anchors=anchors,
                budget_s=min(180.0, max(30.0, interval * 12)),
                dump_dir=dump_dir, start_addr=cursor)
        except Exception as e:
            log("  [MKT] 第 %d 轮异常: %r" % (n, e))
        log("  [MKT] 第 %d 轮结束, 命中 %d/%d" % (n, len(found), len(targets)))
        if len(found) >= len(targets):
            break
        time.sleep(max(0.0, interval - (time.time() - t0)))
    stop_evt.set()
    if anchors:
        try:
            report(anchors, found, dump_dir)
        except Exception as e:
            log("  [MKT] 写报告失败: %r" % (e,))
    return found, anchors


# --------------------------------------------------------------------------
# 自检: 造一段带 zlib 表的数据, 验证 zlib->MD5 通路
# --------------------------------------------------------------------------
def selftest():
    plain = (b"SKU,ProductId,Price\n" + b"".join(
        ("%d,%d,%d\n" % (i, i * 2, i * 3)).encode() for i in range(20000)))
    comp = zlib.compress(plain, 6)
    md5 = hashlib.md5(plain).hexdigest().upper()
    targets = {md5: "coMarketplaceSKUs.csv"}
    buf = b"\x00" * 1234 + comp + b"\x00" * 77
    found = {}
    anchors = {}
    c, n = scan_buffer(buf, 0x10000000, targets, log=lambda s: None,
                       found=found, anchors=anchors)
    ok = (n == 1 and "coMarketplaceSKUs.csv" in found
          and found["coMarketplaceSKUs.csv"][1] == plain
          and found["coMarketplaceSKUs.csv"][0] == 0x10000000 + 1234)
    print("自检: zlib候选=%d 命中=%d %s" % (c, n, "PASS" if ok else "FAIL"))
    if not ok:
        return 1

    # 锚点测试
    found2, anchors2 = {}, {}
    scan_buffer(b"xxcoMarketplaceItems.csv\x00", 0x20000000, {},
                log=lambda s: None, found=found2, anchors=anchors2)
    ok2 = anchors2.get("coMarketplaceItems.csv", [None])[0][0] == 0x20000000 + 2
    print("自检: 锚点 %s" % ("PASS" if ok2 else "FAIL"))

    # 压缩态 MD5(清单哈希可能针对压缩资产)测试
    cmp_md5 = hashlib.md5(comp).hexdigest().upper()
    found3 = {}
    scan_buffer(buf, 0x30000000, {cmp_md5: "unlockFlags.csv"},
                log=lambda s: None, found=found3)
    ok3 = "unlockFlags.csv" in found3
    print("自检: 压缩态MD5 %s" % ("PASS" if ok3 else "FAIL"))
    return 0 if (ok2 and ok3) else 1


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print(__doc__)
        return 0
    mode = sys.argv[1].lower()
    if mode == "selftest":
        return selftest()
    if mode == "dir" and len(sys.argv) >= 3:
        targets = load_targets()
        for h, n in targets.items():
            print("  目标 %-32s %s" % (n, h))
        found, anchors = scan_dir(sys.argv[2])
        for name in sorted(found):
            va, data = found[name]
            p = os.path.join(OUTDIR, name)
            os.makedirs(OUTDIR, exist_ok=True)
            open(p, "wb").write(data)
            print("  写出 %s (%d 字节) <- 0x%X" % (p, len(data), va))
        report(anchors, found)
        return 0
    if mode == "file" and len(sys.argv) >= 3:
        targets = load_targets()
        found, anchors = {}, {}
        scan_file(sys.argv[2], targets, found=found, anchors=anchors,
                  dump_dir=OUTDIR)
        report(anchors, found)
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
