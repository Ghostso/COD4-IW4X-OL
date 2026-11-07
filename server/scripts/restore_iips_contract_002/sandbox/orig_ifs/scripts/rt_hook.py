"""Frida 宿主：驱动 rt_hook.js，把每条记录落成 JSONL。

这是**有注入**的采集方式（高风险档，见 rt_hook.js 头部说明）。
进程外的部分请先用 rt_sockets.py，只有当它不够用时（需要调用栈 / 载荷）
才用本脚本。

用法：
    # 附加到已运行的游戏进程（按进程名模糊匹配）
    python scripts/rt_hook.py --name codoMP --out logs/rt.jsonl

    # 启动即挂钩（进程刚起就注入，能抓到最早的 WSAStartup / socket）
    python scripts/rt_hook.py --spawn "C:\\...\\codoMP_client.exe" --out logs/rt.jsonl

    # 只关心 connect/send/recv，减小噪音
    python scripts/rt_hook.py --name codoMP --hooks connect,send,recv,WSASend,WSARecv

    # 只看载荷前 256 字节，且不抓调用栈
    python scripts/rt_hook.py --name codoMP --payload 256 --no-backtrace

记录落盘后：
    python scripts/rt_summary.py logs/rt.jsonl
"""
import argparse
import json
import os
import shlex
import sys
import time

try:
    import frida
except ImportError:
    print('[!] 未安装 frida。pip install frida frida-tools')
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = os.path.join(HERE, 'rt_hook.js')


def find_pids(sub):
    out = []
    for p in frida.get_local_device().enumerate_processes():
        if sub.lower() in p.name.lower():
            out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pid', type=int)
    ap.add_argument('--name', help='进程名子串，模糊匹配')
    ap.add_argument('--spawn', help='启动即注入；可带参数，如 "app.exe --x"')
    ap.add_argument('--seconds', type=int, default=0,
                    help='采集 N 秒后自动停止（0=一直等到 Ctrl-C）')
    ap.add_argument('--out', default='logs/rt.jsonl')
    ap.add_argument('--hooks', help='逗号分隔的白名单，默认全部')
    ap.add_argument('--payload', type=int, default=64, help='记录前 N 字节载荷，0=不记录')
    ap.add_argument('--no-backtrace', action='store_true')
    a = ap.parse_args()

    if not (a.pid or a.name or a.spawn):
        ap.error('需要 --pid / --name / --spawn 之一')

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    fh = open(a.out, 'w', encoding='utf-8')
    fh.write(json.dumps({'note': 'session start', 'at': time.time()}, ensure_ascii=False) + '\n')

    cfg = {
        'payloadBytes': a.payload,
        'backtrace': not a.no_backtrace,
        'hooks': [h.strip() for h in a.hooks.split(',')] if a.hooks else None,
    }

    def on_message(msg, data):
        if msg.get('type') == 'send':
            rec = msg['payload']
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
            fh.flush()
            api = rec.get('api') or rec.get('note')
            if api in ('connect', 'WSAConnect', 'bind', 'sendto'):
                addr = rec.get('addr') or {}
                print('[%8.3f] tid=%-6s %-11s %s -> %s:%s ret=%s err=%s'
                      % (rec.get('t', 0), rec.get('tid'), api,
                         rec.get('handle'), addr.get('ip', addr.get('family')),
                         addr.get('port'), rec.get('ret'), rec.get('err')))
            elif api in ('send', 'recv', 'WSASend', 'WSARecv', 'sendto', 'recvfrom'):
                print('[%8.3f] tid=%-6s %-11s h=%s len=%s ret=%s'
                      % (rec.get('t', 0), rec.get('tid'), api, rec.get('handle'),
                         rec.get('len', rec.get('want')), rec.get('ret')))
            elif rec.get('note'):
                print('[*] %s %s' % (rec.get('note'), rec.get('count', '')))
        elif msg.get('type') == 'error':
            print('[!] agent error: %s' % msg.get('stack', msg.get('description')))

    def on_destroyed(*_):
        print('[*] session detached')
        fh.close()

    def arm(sess, label):
        script = sess.create_script(open(AGENT, encoding='utf-8').read())
        script.on('message', on_message)
        sess.on('detached', on_destroyed)
        script.load()
        # 配置必须在 hook 安装前送达，否则 --hooks/--payload 不生效。
        r = script.exports_sync.configure(cfg)
        print('[*] %s：已装 %s 个 hook（待装 %s）'
              % (label, r.get('installed'), len(r.get('pending') or [])))
        return script

    if a.spawn:
        argv = shlex.split(a.spawn, posix=False)
        argv = [t.strip('"') for t in argv]
        print('[*] spawn %s' % argv)
        pid = frida.spawn(argv)
        sess = frida.attach(pid)
        arm(sess, 'spawn')
        frida.resume(pid)
        print('[*] pid=%d 已恢复运行；记录写入 %s' % (pid, a.out))
    else:
        if a.pid:
            target = a.pid
        else:
            hits = find_pids(a.name)
            if not hits:
                print('[!] 没有进程名匹配 %r' % a.name)
                return 2
            for i, p in enumerate(hits):
                print('  [%d] pid=%d %s' % (i, p.pid, p.name))
            target = hits[0].pid
            print('[i] 选用 pid=%d %s' % (target, hits[0].name))
        print('[*] attach %s' % target)
        sess = frida.attach(target)
        arm(sess, 'attach')
        print('[*] 已挂钩；Ctrl-C 停止。记录写入 %s' % a.out)

    print('\n[*] 提示：只用进程外手段时请改跑 `python scripts/rt_sockets.py --name %s --watch`'
          % (a.name or '<进程名>'))
    try:
        if a.seconds:
            time.sleep(a.seconds)
        else:
            sys.stdin.read()
    except KeyboardInterrupt:
        pass
    finally:
        fh.close()
        print('[*] 已停止，记录在 %s' % a.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
