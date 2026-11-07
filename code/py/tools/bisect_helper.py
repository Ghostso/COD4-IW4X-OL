"""给 lobby_server 加"应答开关"，用于二分定位 dwRoomMatch::Init 的触发条件。

设计:
    在 OUTDIR 下放 `bisect-disable.txt`，每行一个 "service/task"。
    被列入的条目回空 ACK（等价于该功能未实现）。
    这样能逐个关闭大厅功能，看哪个关掉后 MyEventHandler 不创建。

反向: `bisect-only.txt` 只放行列出的条目，其余全禁。

用法:
    echo "102/7" > bisect-disable.txt
    echo "71/3" >> bisect-disable.txt

    或
    echo "21/5" > bisect-only.txt
"""
import os

BISECT_DISABLE = "bisect-disable.txt"
BISECT_ONLY = "bisect-only.txt"


def bisect_should_disable(service, task, outdir):
    """返回 True 表示这条请求应当被强制回空 ACK。"""
    key = "%d/%d" % (service, task)

    only_p = os.path.join(outdir, BISECT_ONLY)
    if os.path.exists(only_p):
        try:
            allowed = set()
            for ln in open(only_p, encoding="utf-8"):
                ln = ln.strip()
                if ln and not ln.startswith("#"):
                    allowed.add(ln)
            return key not in allowed
        except Exception:
            return False

    dis_p = os.path.join(outdir, BISECT_DISABLE)
    if os.path.exists(dis_p):
        try:
            blocked = set()
            for ln in open(dis_p, encoding="utf-8"):
                ln = ln.strip()
                if ln and not ln.startswith("#"):
                    blocked.add(ln)
            return key in blocked
        except Exception:
            return False

    return False
