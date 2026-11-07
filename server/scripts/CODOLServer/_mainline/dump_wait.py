"""常驻等待式内存转储 —— 提前提权启动，等客户端出现后自动抓取。

解决时序问题: UAC 确认需要时间, 而客户端的运行窗口有限。
本脚本以管理员身份常驻, 轮询等待 codoMP_client_shipRetail.exe 出现,
检测到后等 N 秒(让游戏初始化完), 立刻转储, 然后退出。

用法（管理员）:
    python -I dump_wait.py <outdir> <result_json> [--delay 45] [--timeout 600]
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline')
from memdump_core import dump_client, find_pids   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("result_json")
    ap.add_argument("--delay", type=float, default=45.0,
                    help="检测到进程后再等多少秒(让游戏初始化)")
    ap.add_argument("--timeout", type=float, default=600.0,
                    help="总共等多久还没看到进程就放弃")
    a = ap.parse_args()

    t0 = time.time()
    seen = None
    while time.time() - t0 < a.timeout:
        pids = find_pids()
        if pids:
            seen = pids[0]
            break
        time.sleep(1.0)

    if seen is None:
        with open(a.result_json, 'w', encoding='utf-8') as f:
            json.dump({'ok': False, 'lines': ['超时未检测到客户端进程']}, f,
                      ensure_ascii=False, indent=2)
        return 2

    lines = ['检测到客户端 PID=%d, 等待 %.0f 秒后转储' % (seen, a.delay)]
    time.sleep(a.delay)

    # 转储前再次确认进程还在
    if not find_pids():
        lines.append('等待期间客户端已退出')
        with open(a.result_json, 'w', encoding='utf-8') as f:
            json.dump({'ok': False, 'lines': lines}, f, ensure_ascii=False, indent=2)
        return 3

    try:
        lines += dump_client(a.outdir, max_mb=2048)
        ok = True
    except Exception as e:
        lines.append('EXCEPTION: %r' % (e,))
        ok = False

    with open(a.result_json, 'w', encoding='utf-8') as f:
        json.dump({'ok': ok, 'lines': lines}, f, ensure_ascii=False, indent=2)
    for ln in lines:
        print(ln)
    return 0


if __name__ == '__main__':
    sys.exit(main())
