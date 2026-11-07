# -*- coding: utf-8 -*-
"""一键集成启动器 (2026-10-02 改版: 对齐三方已验证可用的方案)

流程:
  1) 清理旧占用(只杀"我们自己的"脚本, 按命令行精确匹配)
  2) 修正 hosts / dwauth.ini / 证书 (见下)
  3) 起两个本地服务:
       127.0.0.1:3074  TLS   /auth/   (fake_auth_tls.py)
       127.0.0.2:3074  明文  大厅 lsg  (lobby_server.py)
  4) 跑 nt10.py 注入 + 观测

★ 关键改动(依据 E:\\codol\\dist\\CODOL-Portable 那份"能进大厅"的实现):
  a) 【不再劫持 down.qq.com / intldlgs.qq.com】—— 三方让 ACE/TP3 走真实网络,
     我们之前把 intldlgs.qq.com 指到 127.0.0.1 并让 443 回 404, 等于把
     TP3 从一个活着的服务器上掐断。
  b) 主通道是【3074】, 不是 8443/8446:
       127.0.0.1 formal-zone-auth.codol.qq.com   (TLS /auth/)
       127.0.0.2 formal-zone-lsg.codol.qq.com    (明文大厅 wI)
  c) dwauth.ini 的正确格式(三方 Run-Session.ps1 第 167 行):
       formal-zone-lsg.codol.qq.com 3074
       formal-zone-auth.codol.qq.com 3074
       0x03EA
  d) 证书 SAN 必须是 localhost + formal-zone-auth.codol.qq.com +
     formal-zone-lsg.codol.qq.com (由 make_local_ca.ps1 生成)

用法:
  python run_all.py                       # 默认 150 秒, 输出 n10run.txt
  python run_all.py --secs 180 --out n10an.txt
  python run_all.py --restore-hosts       # 只把 hosts 恢复干净, 不跑游戏
  python run_all.py --no-hosts            # 不改 hosts(你自己管)
"""
import argparse
import os
import re
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
GAME_ROOT = os.environ.get("OLMOD_GAME_ROOT") or r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL"
HOSTS_PATH = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                          "System32", "drivers", "etc", "hosts")
PORTS = [80, 443, 3074, 8081, 8443, 8446, 49155, 49156]

# 我们写入 hosts 的块(三方同款两条)
HOSTS_BEGIN = "# CODOL-LOCAL-BEGIN"
HOSTS_END = "# CODOL-LOCAL-END"
HOSTS_BLOCK = (HOSTS_BEGIN + "\r\n"
               + "127.0.0.1 formal-zone-auth.codol.qq.com\r\n"
               + "127.0.0.2 formal-zone-lsg.codol.qq.com\r\n"
               + HOSTS_END + "\r\n")

# 只匹配"我们自己起的"进程 —— 避免误杀无关程序
KILL_RE = (r"fake_ied_https|fake_auth_https|fake_auth_tls|lobby_server\.py|fake_lobby\.py"
           r"|nt10\.py|setup_auth8443|battle_server\.py")


def ps_run(cmd):
    return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                          capture_output=True, text=True, errors="replace")


def _is_admin():
    try:
        r = ps_run("([Security.Principal.WindowsPrincipal]"
                   "[Security.Principal.WindowsIdentity]::GetCurrent())"
                   ".IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)")
        return (r.stdout or "").strip()
    except Exception:
        return "?"


def _listening_ports():
    """用 netstat 读 LISTENING 的本地端口。
    ★ 绝不能改成"connect 一下试试": lobby_server 会把这个探测连接当成真的大厅连接
      (上一轮 [who] 已证: 8446 的来访者是 run_all 自己的 python.exe), 白白污染日志。"""
    res = {}
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                             errors="replace", timeout=15).stdout
    except Exception:
        return res
    for ln in out.splitlines():
        p = ln.split()
        if len(p) >= 5 and p[0].upper() == "TCP" and p[3].upper() == "LISTENING":
            loc = p[1]
            if ":" in loc:
                port = loc.rsplit(":", 1)[1]
                if port.isdigit():
                    res.setdefault(int(port), p[4])
    return res


def show_ports(tag):
    lp = _listening_ports()
    print("[*] 端口监听状态(%s):" % tag)
    for p in PORTS:
        print("      %-6d %s" % (p, ("LISTENING pid=%s" % lp[p]) if p in lp else "空闲"))


def port_listening(port):
    return port in _listening_ports()


def _listening_endpoints():
    """返回 (addr, port) 集合 —— 用来区分 127.0.0.1:3074 与 127.0.0.2:3074。"""
    res = set()
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                             errors="replace", timeout=15).stdout
    except Exception:
        return res
    for ln in out.splitlines():
        p = ln.split()
        if len(p) >= 5 and p[0].upper() == "TCP" and p[3].upper() == "LISTENING":
            loc = p[1]
            if ":" in loc:
                a, _, pt = loc.rpartition(":")
                if pt.isdigit():
                    res.add((a.strip("[]"), int(pt)))
    return res


def addr_listening(addr, port):
    return (addr, port) in _listening_endpoints()


# ---------------------------------------------------------------- hosts
def _read_hosts():
    return open(HOSTS_PATH, "rb").read().decode("latin-1")


def _write_hosts(text):
    open(HOSTS_PATH, "wb").write(text.encode("latin-1"))


def clean_hosts(verbose=True):
    """删掉: 1) 我们写的块  2) plan A 遗留的 intldlgs/down.qq.com 本地劫持行。
    ★ down.qq.com / intldlgs.qq.com 必须交还给真实网络 —— 三方实现就是这么做的,
      否则 ACE/TP3 拿不到配置和 DLL。"""
    txt = _read_hosts()
    orig = txt
    txt = re.sub(re.escape(HOSTS_BEGIN) + r".*?" + re.escape(HOSTS_END) + r"\r?\n?",
                 "", txt, flags=re.S)
    kept, removed = [], []
    for ln in txt.splitlines():
        s = ln.strip()
        if s.startswith("#") and "fake iedsafe" in s:
            removed.append(ln)
            continue
        if re.match(r"^\s*127\.0\.0\.\d+\s+.*(intldlgs\.qq\.com|down\.qq\.com)\b", ln):
            removed.append(ln)
            continue
        kept.append(ln)
    txt = "\r\n".join(kept)
    if txt and not txt.endswith("\r\n"):
        txt += "\r\n"
    if txt != orig:
        _write_hosts(txt)
    if verbose:
        for ln in removed:
            print("      - 删除 hosts 行: %s" % ln.strip())
        print("      hosts 清理: %s" % ("已改动" if txt != orig else "无需改动"))
    return txt


def verify_hosts():
    txt = _read_hosts()
    print("      hosts 现状(与 codol/qq 相关的行):")
    bad = []
    for ln in txt.splitlines():
        if re.search(r"formal-zone|codol|intldlgs|down\.qq", ln, re.I):
            print("          %s" % ln.strip())
            if re.match(r"^\s*127\.0\.0\.\d+\s+.*(intldlgs\.qq\.com|down\.qq\.com)\b", ln):
                bad.append(ln.strip())
    if bad:
        print("      !! 仍有 iedsafe 劫持行: %s" % bad)
    else:
        print("      [+] 无 intldlgs/down.qq.com 劫持 —— ACE/TP3 走真实网络 OK")


def ensure_hosts():
    print("=" * 70)
    print("[2/5] 修正 hosts")
    print("=" * 70)
    txt = clean_hosts()
    if HOSTS_BEGIN in txt:
        print("      [=] 我们的 hosts 块已存在")
    else:
        if txt and not txt.endswith("\r\n"):
            txt += "\r\n"
        txt += HOSTS_BLOCK
        _write_hosts(txt)
        print("      [+] 已写入:")
        for ln in HOSTS_BLOCK.strip().splitlines():
            print("          %s" % ln)
    verify_hosts()


# ---------------------------------------------------- cert / dwauth
def ensure_cacert():
    """把 _ca.pem(本地 root CA) 追加进游戏 cacert.pem。
    用 Python 做 —— 路径含中文, PowerShell 5.1 读无 BOM 脚本会乱码。"""
    ca = os.path.join(ROOT, "_ca.pem")
    dst = os.path.join(GAME_ROOT, "cacert.pem")
    if not os.path.exists(ca):
        print("      !! 找不到 %s" % ca)
        return False
    if not os.path.exists(dst):
        print("      !! 找不到 %s" % dst)
        return False
    pem = open(ca, "r", encoding="ascii", errors="replace").read()
    flat = pem.split("-----")
    body = "".join(flat[2].split()) if len(flat) > 2 else ""
    cur = open(dst, "rb").read().decode("latin-1")
    if body and body in "".join(cur.split()):
        print("      [=] 该 root CA 已在 cacert.pem 内 (共 %d 张)"
              % cur.count("BEGIN CERTIFICATE"))
        return True
    n0 = cur.count("BEGIN CERTIFICATE")
    if not cur.endswith("\n"):
        cur += "\n"
    cur += pem if pem.endswith("\n") else pem + "\n"
    open(dst, "wb").write(cur.encode("latin-1"))
    print("      [+] 已追加 root CA 到 %s (证书数 %d -> %d)"
          % (dst, n0, cur.count("BEGIN CERTIFICATE")))
    return True


def make_certs():
    ps1 = os.path.join(ROOT, "make_local_ca.ps1")
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                        "-ExecutionPolicy", "Bypass", "-File", ps1, "-Root", ROOT],
                       capture_output=True, text=True, errors="replace")
    for ln in (r.stdout or "").splitlines():
        if ln.strip():
            print("      | %s" % ln.rstrip())
    ok = (os.path.exists(os.path.join(ROOT, "_leaf2.cer"))
          and os.path.exists(os.path.join(ROOT, "_ca.pem")))
    if r.returncode != 0 or not ok:
        print("      !! 证书生成失败 rc=%s" % r.returncode)
        for ln in (r.stderr or "").splitlines()[:12]:
            print("      !! %s" % ln.rstrip())
        return False
    return ensure_cacert()


def write_dwauth():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "write_dwauth.py"),
                        "--root", GAME_ROOT],
                       capture_output=True, text=True, errors="replace")
    for ln in (r.stdout or "").splitlines():
        if ln.strip():
            print("      | %s" % ln.rstrip())
    if r.returncode != 0:
        print("      !! write_dwauth 失败 rc=%s" % r.returncode)
        for ln in (r.stderr or "").splitlines()[:8]:
            print("      !! %s" % ln.rstrip())
        return False
    return True


def zombie_count():
    """残留的 codoMP_client_shipRetail 进程数。用户态杀不掉, 只有重启能清。"""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                            "(Get-Process codoMP_client_shipRetail -ErrorAction SilentlyContinue "
                            "| Measure-Object).Count"],
                           capture_output=True, text=True, errors="replace")
        return int((r.stdout or "0").strip() or 0)
    except Exception:
        return 0


def kill_udp_owners(port):
    """杀掉占用 UDP <port> 的进程 —— 战斗服专用(28960)。

    ★ 为什么不只靠 KILL_RE: 那条路要读别的进程的 CommandLine, 跨权限时常常读到空串
      (2026-10-04 实测: 21 个管理员权限的战斗服残留, CommandLine 全为空, 过滤不出来)。
      按端口所有者杀更稳 —— 本机 UDP 28960 只可能是我们的 battle_server。"""
    try:
        r = subprocess.run(["netstat", "-ano", "-p", "UDP"],
                           capture_output=True, text=True, errors="replace")
    except Exception:
        return
    pids = set()
    for ln in (r.stdout or "").splitlines():
        parts = ln.split()
        if len(parts) >= 4 and parts[0].upper() == "UDP" and parts[1].endswith(":%d" % port):
            if parts[-1].isdigit():
                pids.add(parts[-1])
    for pid in sorted(pids):
        try:
            r = subprocess.run(["taskkill", "/F", "/PID", pid],
                               capture_output=True, text=True, errors="replace")
        except Exception as e:
            print("  kill(UDP %d) PID %s -> 异常 %r" % (port, pid, e))
            continue
        ok = (r.returncode == 0)
        msg = "OK" if ok else ((r.stdout or r.stderr or "").strip().replace("\n", " ") or "失败")
        print("  kill(UDP %d) PID %s -> %s" % (port, pid, msg))
    if pids:
        print("  (按端口清掉 %d 个战斗服残留 —— UDP %d)" % (len(pids), port))
    else:
        # ★ 2026-10-04: 曾出现"netstat 里没有占用者, 但战斗服 bind 仍报 10048" —— 打印原始状态,
        #   下次一眼能看出是 netstat 没查到、还是查到了没杀成。
        print("  (UDP %d 没查到占用者 —— 若战斗服仍报 bind 10048, 看下面原始 netstat)"
              % port)
        try:
            r2 = subprocess.run(["netstat", "-ano", "-p", "UDP"],
                                capture_output=True, text=True, errors="replace")
            hits = [ln.strip() for ln in (r2.stdout or "").splitlines()
                    if ":%d" % port in ln]
            print("    netstat 命中 %d 行: %s" % (len(hits), hits[:5] if hits else "(无)"))
        except Exception as e:
            print("    netstat 复读失败: %r" % (e,))


def free_ports():
    print("=" * 70)
    print("[1/5] 清理旧占用")
    print("=" * 70)
    cmd = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -match '%s' } | "
        "Where-Object { $_.ProcessId -ne $PID } | "
        "ForEach-Object { $c=$_.CommandLine; if(-not $c){$c=''}; "
        "Write-Output ('  kill PID ' + $_.ProcessId + ' : ' + $c.Substring(0,[Math]::Min(100,$c.Length))); "
        "Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    ) % KILL_RE
    r = ps_run(cmd)
    out = (r.stdout or "").strip()
    print(out if out else "  (没有匹配到我们自己的脚本)")
    kill_udp_owners(28960)
    time.sleep(2)
    show_ports("清理后")


def start_py_service(tag, script, port, logname, addr=None):
    """起一个 Python 写的服务(自己实现协议, 如 fake_auth_tls.py)。
    addr 给了就按 (addr, port) 精确校验监听(区分 127.0.0.1 / 127.0.0.2 的 3074)。"""
    print("=" * 70)
    print("[*] 起 %s (%s:%d) : %s" % (tag, addr or "0.0.0.0", port, script))
    print("=" * 70)
    out = os.path.join(ROOT, "_%s_out.txt" % tag)
    err = os.path.join(ROOT, "_%s_err.txt" % tag)
    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, script)],
                            stdout=open(out, "w"), stderr=open(err, "w"),
                            stdin=subprocess.DEVNULL, creationflags=0x08000000)

    def _up():
        return addr_listening(addr, port) if addr else port_listening(port)

    ok = False
    for _ in range(24):
        time.sleep(0.5)
        if _up():
            ok = True
            break
        if proc.poll() is not None:
            break
    if ok:
        print("      %s:%d 已监听 OK (pid=%s, 日志 %s)"
              % (addr or "0.0.0.0", port, proc.pid, os.path.basename(logname)))
        return True
    print("      !! %s:%d 未监听 (子进程 pid=%s rc=%s)"
          % (addr or "0.0.0.0", port, proc.pid, proc.poll()))
    for f in (logname, out, err):
        try:
            txt = open(f, encoding="utf-8", errors="replace").read().strip()
        except Exception:
            txt = ""
        print("      --- %s ---" % os.path.basename(f))
        if txt:
            print("      " + txt.replace("\n", "\n      "))
    return False


def start_auth_tls():
    """127.0.0.1:3074 的 /auth/ 服务 (TLS)。
    三方 Run-Session.ps1 就是把 auth 服务放在 127.0.0.1:3074
    (hosts: 127.0.0.1 formal-zone-auth.codol.qq.com)。
    用 Python 自己做 TLS —— http.sys 关连接时不发 close-notify。"""
    for f in ("auth3074.log",):
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    return start_py_service("auth", "fake_auth_tls.py", 3074,
                            os.path.join(ROOT, "auth3074.log"), addr="127.0.0.1")


def start_battle_server(bind="0.0.0.0", port=28960):
    """战斗服(UDP)。当前是"最小骨架 + 抓包观察通道": 只实现 NAT 遍历应答,
    其余包全部记进 battle_srv.log —— 进对局时客户端会连它, 先看清它发什么。"""
    print("=" * 70)
    print("[*] 起战斗服 UDP %s:%d : battle_server.py" % (bind, port))
    print("=" * 70)
    out = os.path.join(ROOT, "_battle_out.txt")
    err = os.path.join(ROOT, "_battle_err.txt")
    try:
        subprocess.Popen([sys.executable, os.path.join(ROOT, "battle_server.py"),
                          "--bind", bind, "--port", str(port)],
                         stdout=open(out, "w"), stderr=open(err, "w"),
                         stdin=subprocess.DEVNULL, creationflags=0x08000000)
    except Exception as e:
        print("      !! 起战斗服失败: %r" % (e,))
        return False
    time.sleep(1.5)
    logs = []
    for f in (os.path.join(ROOT, "battle_srv.log"), out, err):
        try:
            txt = open(f, encoding="utf-8", errors="replace").read().strip()
        except Exception:
            txt = ""
        if txt:
            logs.append(txt.splitlines()[-3:])
    print("      战斗服已拉起; 日志 battle_srv.log")
    for ls in logs:
        for ln in ls:
            print("      " + ln)
    return True


def start_lobby_server(lobby_bind="127.0.0.2", lobby_port=3074, raw_ports=""):
    """127.0.0.2:3074 的明文大厅服务 (= formal-zone-lsg.codol.qq.com)。
    ★ 不再默认起 443/80/8081 的原始抓包 —— 那些端口已交还真实网络
      (三方不劫持 down.qq.com / intldlgs.qq.com)。"""
    print("=" * 70)
    print("[*] 起大厅服务 (明文 %s:%d)  raw=[%s]" % (lobby_bind, lobby_port, raw_ports))
    print("=" * 70)
    logf = os.path.join(ROOT, "lobby_srv.log")
    if os.path.exists(logf):
        try:
            os.remove(logf)
        except Exception:
            pass
    # 清掉上一轮留下的就绪标志/抓包/密钥快照, 否则会用到过期的 key
    for f in ("lobby_ready.flag", "lobby_rx.bin", "lobby_tasks.bin", "secrets.txt"):
        p = os.path.join(ROOT, f)
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    subprocess.Popen([sys.executable, os.path.join(ROOT, "lobby_server.py"),
                      "--lobby-bind", lobby_bind, "--lobby-port", str(lobby_port),
                      "--raw-ports", raw_ports],
                     creationflags=0x00000008)
    print("      已启动 lobby_server.py (日志 lobby_srv.log)")


def is_good(path, secs):
    """判断本次启动是否为"好启动"。
    好: game 仍在运行(跑满窗口) / 或正常退出(rc=0)且存活 >= 80% 窗口。
    坏: 崩溃退出(如 0xC0000005=3221225477)、t 很小、或钩子一次都没命中。"""
    try:
        t = open(path, encoding="utf-8", errors="replace").read()
    except Exception:
        return False, "输出文件读取失败"
    if "game 仍在运行" in t:
        return True, "跑满窗口"
    m = re.search(r"game 退出 rc=(-?\d+) t=([\d.]+)", t)
    if m:
        rc = int(m.group(1))
        tt = float(m.group(2))
        if rc == 0 and tt >= secs * 0.8:
            return True, "正常退出 rc=0 t=%.1f" % tt
        return False, "退出 rc=%d(0x%X) t=%.1f" % (rc, rc & 0xFFFFFFFF, tt)
    if "注入" in t and "-> 成功" not in t:
        return False, "TAS 注入失败"
    return False, "未见存活标志(可能早退)"


def run_nt10(secs, out, apis, retries=6, trace=False, ps=False):
    print("=" * 70)
    print("[4/4] 跑 nt10.py (注入 + 观测), 失败自动重试, 最多 %d 次" % retries)
    print("=" * 70)
    base, ext = os.path.splitext(out)
    last = out
    for i in range(1, retries + 1):
        dst = out if i == 1 else "%s_a%d%s" % (base, i, ext)
        cmd = [sys.executable, os.path.join(ROOT, "nt10.py"),
               "--root", GAME_ROOT,
               "--secs", str(secs), "--delay", "0", "--out", dst, "--apis", apis]
        if trace:
            cmd.append("--trace")
        if ps:
            cmd.append("--ps-probe")
        print("\n>>> 第 %d/%d 次启动 ..." % (i, retries))
        subprocess.run(cmd, cwd=ROOT)
        ok, why = is_good(os.path.join(ROOT, dst), secs)
        if ok:
            print(">>> 第 %d 次 = 好启动 (%s) -> %s" % (i, why, dst))
            last = dst
            break
        print(">>> 第 %d 次 = 坏启动 (%s), 重新启动 ..." % (i, why))
        time.sleep(2)
    else:
        print(">>> %d 次都没起好(启动 flake), 可再跑一次 run_all.py" % retries)
    print()
    print("=" * 70)
    print("完成。看这三处:")
    print("  %s" % os.path.join(ROOT, last))
    print("  %s" % os.path.join(ROOT, "lobby_srv.log"))
    print("  %s" % os.path.join(ROOT, "auth3074.log"))
    print("=" * 70)


def run_nt10_multi(secs, out, apis, clients=1, retries=6, trace=False, ps=False):
    """★ 多客户端(2026-10-03): 同时跑 N 份 nt10 —— 每个 nt10 自己拉起一份游戏并注入。

    服务端侧的配对已经在 lobby_server.py / fake_auth_tls.py 落地:
      · `fake_auth_tls` 给每个 /auth/ 请求发**唯一的 24B 会话密钥**(写在票据 97..121);
      · 每个 nt10 的 KDF hook 把该会话的密钥追加进 `kdf_sessions.txt`;
      · `lobby_server` 收到 0x82 后, 从帧里读票据[97:121] 当配对键查表,
        用**该客户端自己的**密钥解 0x85、签应答。
    所以这里只负责"同时起 N 份"; N=1 时行为与以前完全一致。
    """
    if clients <= 1:
        return run_nt10(secs, out, apis, retries, trace, ps)
    print("=" * 70)
    print("[4/4] 多客户端: 同时跑 %d 份 nt10 (各自拉起一份游戏实例)" % clients)
    print("=" * 70)
    base, ext = os.path.splitext(out)
    procs = []
    for i in range(clients):
        dst = out if i == 0 else "%s_c%d%s" % (base, i + 1, ext)
        cmd = [sys.executable, os.path.join(ROOT, "nt10.py"),
               "--root", GAME_ROOT,
               "--secs", str(secs), "--delay", "0", "--out", dst, "--apis", apis,
               # ★ 多客户端必须加这个: 否则两个 nt10 会互相 taskkill 对方的游戏
               "--keep-others"]
        if trace:
            cmd.append("--trace")
        if ps:
            cmd.append("--ps-probe")
        print(">>> 客户端 %d: %s" % (i + 1, " ".join(cmd[2:])))
        procs.append((dst, subprocess.Popen(cmd, cwd=ROOT)))
        time.sleep(1.5)          # 错开一点, 避免同时抢 hosts/单实例互斥
    for dst, p in procs:
        p.wait()
    print()
    print("=" * 70)
    print("完成。各客户端 nt10 日志: %s" % ", ".join(d for d, _ in procs))
    print("  %s" % os.path.join(ROOT, "lobby_srv.log"))
    print("  %s" % os.path.join(ROOT, "auth3074.log"))
    print("  %s   (每会话一行的 会话密钥→四把子密钥 表, 配对用)" % os.path.join(ROOT, "kdf_sessions.txt"))
    print("  %s   (每个 /auth/ 发的会话密钥)" % os.path.join(ROOT, "auth_sessions.txt"))
    print("=" * 70)


def run_nt8o(secs, out, directs, apis):
    """用【原始 nt8 的副本】(nt8o.py) 驱动。
    nt8 的 --direct 会一直等"解壳就绪"再挂 hook；另外它的支持表里有
    WSAConnect/WSASocketW/WSARecv/send/recv —— 用来找"到底是谁发起了那条
    /auth/ TLS 连接、谁在收应答"(ws2_32 的 connect 钩子从来没见过 8443)。"""
    print("=" * 70)
    print("[4/4] 跑 nt8o.py (原始 nt8 副本)")
    print("=" * 70)
    cmd = [sys.executable, os.path.join(ROOT, "nt8o.py"),
           "--secs", str(secs),
           "--apis", apis,
           "--direct", directs, "--show", "8",
           "--out", os.path.join(ROOT, out)]
    print(">>> " + " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT)
    print()
    print("完成。看: %s" % os.path.join(ROOT, out))


def _run_driver(a):
    if a.driver == "nt8o":
        run_nt8o(a.secs, a.out, a.direct, a.n8apis)
    else:
        run_nt10_multi(a.secs, a.out, a.apis, a.clients, a.retries,
                       trace=getattr(a, "trace", False),
                       ps=getattr(a, "ps_probe", False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--secs", type=int, default=150)
    ap.add_argument("--out", default="n10run.txt")
    ap.add_argument("--apis", default="OpenFileMappingW,CreateFileMappingW,MapViewOfFile,"
                                      "connect,sendto,WinHttpConnect,WinHttpOpenRequest,"
                                      "WinHttpSendRequest,z1,z2",
                    help="要 hook 的 API（逗号分隔）。★ 2026-10-04: 别再往默认里加 recv/WSARecv 等"
                         "热路径 —— hook 它们会把游戏网络带崩。--trace 时由 nt10 自己追加触发器。")
    ap.add_argument("--driver", default="nt10", choices=["nt10", "nt8o"],
                    help="用哪个注入器: nt10(自己维护) / nt8o(原始 nt8 的副本)")
    ap.add_argument("--trace", action="store_true",
                    help="路线A探针: 让 nt10 运行时调用客户端原生碰撞 trace(sub_46E780)，"
                         "每 10s 一轮共 8 轮，结果打在 nt10 日志里")
    ap.add_argument("--ps-probe", action="store_true",
                    help="出生点/位置探针: nt10 周期性扫客户端内存里的本地 playerstate，"
                         "把 origin/角度写进 player_origin.txt（用来和地图出生点清单对照）")
    ap.add_argument("--direct", default="0xBA9980,0xBC3E10",
                    help="--driver nt8o 时直挂的绝对地址(票据解析 / JSON 取字段)")
    ap.add_argument("--n8apis", default="WSAConnect,WSASocketW,connect,sendto,WSASendTo,"
                                        "send,recv,WSARecv,"
                                        "OpenFileMappingW,CreateFileMappingW,MapViewOfFile",
                    help="--driver nt8o 时的 hook 集合(必须是 nt8 支持表里的名字; 不传 --only-exe 以看到 DLL 调用者)")
    ap.add_argument("--no-kill", action="store_true")
    ap.add_argument("--retries", type=int, default=6, help="坏启动时最多重试几次")
    ap.add_argument("--clients", type=int, default=1,
                    help="同时跑几个客户端(每个 nt10 拉起一份游戏; 服务端按会话密钥自动配对)")
    ap.add_argument("--raw-ports", default="",
                    help="诊断: 额外在 0.0.0.0 上抓这些端口(逗号分隔), 如 80,8081。默认空")
    ap.add_argument("--no-hosts", action="store_true",
                    help="不改 hosts(你自己管)")
    ap.add_argument("--restore-hosts", action="store_true",
                    help="只把 hosts 恢复干净(删掉我们的块 + intldlgs/down.qq.com 劫持行), 然后退出")
    ap.add_argument("--no-certs", action="store_true",
                    help="不重新生成证书(复用现有的 _ca.pem/_leaf2.cer)")
    ap.add_argument("--no-dwauth", action="store_true",
                    help="不改 dwauth.ini")
    ap.add_argument("--poke", action="store_true",
                    help="写大厅主机/端口全局(默认不写 —— 三方实现只靠 hosts+dwauth.ini+4 个补丁)")
    ap.add_argument("--tas", action="store_true",
                    help="注入 TAS 镜像。默认【不注入】—— 实测 TAS 会把客户端推到 DSA 签名路径"
                         "(auth_task=32 + codo_request 签名块), 从而卡在\"无法连接大厅服务\"")
    ap.add_argument("--no-services", action="store_true",
                    help="隔离实验: 不起任何假服务, 只跑 nt10 —— 等价于 nt8 的环境")
    ap.add_argument("--no-battle", action="store_true",
                    help="不起战斗服(UDP 127.0.0.1:28960)。默认起 —— 进对局时客户端会连它")
    ap.add_argument("--force", action="store_true",
                    help="检测到残留游戏进程(僵尸)时也继续跑")
    a = ap.parse_args()

    # 僵尸进程自检: 残留的 codoMP_client_shipRetail 会占住游戏单实例互斥,
    # 新实例一起来就退出(表现为"坏启动 rc=1 t≈10s"), 而且用户态 taskkill 杀不掉。
    z = zombie_count()
    if z:
        print("=" * 70)
        print("!! 检测到 %d 个残留的 codoMP_client_shipRetail 进程" % z)
        print("   它们会占住游戏的单实例互斥 → 新实例起来就退(坏启动 rc=1 t≈10s),")
        print("   而且 taskkill/Stop-Process 都杀不掉(实测 Access is denied)。")
        print("   处理办法: 重启一次机器再跑。想忽略请加 --force。")
        print("=" * 70)
        if not getattr(a, "force", False):
            return
        print("[!] --force: 忽略僵尸进程继续")
    else:
        print("[*] 无残留游戏进程 OK")

    if a.restore_hosts:
        print("=" * 70)
        print("[*] --restore-hosts: 只修 hosts")
        print("=" * 70)
        clean_hosts()
        verify_hosts()
        return

    flag = os.path.join(ROOT, "poke_off.flag")
    if a.poke:
        if os.path.exists(flag):
            try:
                os.remove(flag)
            except Exception:
                pass
        print("[!] --poke: 本轮会写大厅主机/端口全局")
    else:
        open(flag, "w").close()
        print("[*] 默认不写大厅全局(三方实现只靠 hosts + dwauth.ini + 内存补丁); 要写请加 --poke")
    tflag = os.path.join(ROOT, "tas_off.flag")
    if a.tas:
        if os.path.exists(tflag):
            try:
                os.remove(tflag)
            except Exception:
                pass
        print("[!] --tas: 本轮会注入 TAS 镜像(注意: 这会让客户端走 DSA 签名路径)")
    else:
        open(tflag, "w").close()
        print("[*] 默认不注入 TAS 镜像(必需 —— 否则 auth_task=32 走签名路径会卡住); 要注入请加 --tas")

    if not a.no_kill:
        free_ports()

    # ---- [2/5] hosts: 交还 down.qq.com / intldlgs.qq.com, 只劫持两个 CODOL 域名
    if a.no_hosts:
        print("[!] --no-hosts: 不改 hosts")
    else:
        ensure_hosts()

    # ---- [3/5] dwauth.ini + 证书
    print("=" * 70)
    print("[3/5] 写 dwauth.ini + 生成/校验本地证书")
    print("=" * 70)
    if a.no_dwauth:
        print("      [!] --no-dwauth: 跳过")
    else:
        write_dwauth()
    if a.no_certs:
        print("      [!] --no-certs: 跳过证书生成, 仅校验 cacert.pem")
        ensure_cacert()
    else:
        make_certs()

    if a.no_services:
        print("=" * 70)
        print("[!] --no-services 隔离模式: 不起任何假服务, 只跑 nt10")
        print("=" * 70)
        show_ports("清理后")
        _run_driver(a)
        return

    # ---- [4/5] 两个本地服务: 127.0.0.1:3074(TLS /auth/) + 127.0.0.2:3074(明文大厅)
    print("=" * 70)
    print("[4/5] 起本地服务")
    print("=" * 70)
    start_auth_tls()
    start_lobby_server(raw_ports=a.raw_ports)
    # ★ 2026-10-05: 战斗服只允许由一处拉起。
    #   lobby_server 自己会在 "127.0.0.2 + firingrange-battle.enabled" 时起一份
    #   (见 maybe_start_battle_server); 这里若再起一份就会抢 28960, 结果是
    #   两份互相顶掉: 一份写日志、一份占端口, 实际收包全 0。
    #   所以开关文件在时交给 lobby_server 起; 只有开关不在时才由这里兜底。
    fr_battle_on = os.path.exists(os.path.join(ROOT, "firingrange-battle.enabled"))
    if not a.no_battle and not fr_battle_on:
        start_battle_server()
    time.sleep(3)
    show_ports("启动后")
    print("      ★ 注意: 443/80/8081 应当【空闲】—— 它们已交还真实网络")
    _run_driver(a)


if __name__ == "__main__":
    main()
