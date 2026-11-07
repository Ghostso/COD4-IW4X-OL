"""在提权进程中内联执行内存转储，结果写 JSON 到指定文件。

不开子进程（子进程不继承 SeDebugPrivilege）。
用法（由提权 agent 的 run 动作调用，或手动以管理员身份运行）:
    python -I dump_inline.py <outdir> <result_json>
"""
import json
import os
import sys

sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline')
from memdump_core import dump_client   # noqa: E402


def main():
    outdir = sys.argv[1]
    result_json = sys.argv[2]
    try:
        lines = dump_client(outdir, max_mb=2048)
        ok = True
    except Exception as e:
        lines = ['EXCEPTION: %r' % (e,)]
        ok = False
    with open(result_json, 'w', encoding='utf-8') as f:
        json.dump({'ok': ok, 'lines': lines}, f, ensure_ascii=False, indent=2)
    for ln in lines:
        print(ln)


if __name__ == '__main__':
    main()
