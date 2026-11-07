# -*- coding: utf-8 -*-
"""Read back a _po5_live_pop.py run and print the panel timeline.

Usage: python -X utf8 _po5_summary.py CODOLServer/_po5/live1
"""
import json
import os
import sys

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL'


def main():
    d = sys.argv[1]
    if not os.path.isabs(d):
        d = os.path.join(ROOT, d)
    log = os.path.join(d, 'live_pop.jsonl')
    if not os.path.exists(log):
        print('no log at', log)
        return 1
    recs = []
    for line in open(log, encoding='utf-8'):
        line = line.strip()
        if not line:
            continue
        try:
            recs.append(json.loads(line))
        except ValueError:
            pass
    print('dir      :', d)
    print('ticks    :', len(recs))
    if not recs:
        return 0
    pids = sorted(set(r.get('game_pid') for r in recs if r.get('game_pid')))
    print('game pids:', pids)
    events = [r for r in recs if r.get('event')]
    print('events   :', len(events))
    for r in events:
        print('   t=%-7s %-16s pid=%s score=%s bbox=%s shot=%s'
              % (r.get('t'), r.get('event'), r.get('game_pid'),
                 r.get('panel_score'), r.get('panel_bbox'), r.get('shot')))
    hits = [r for r in recs if r.get('panel')]
    print('panel-hit ticks :', len(hits))
    if hits:
        print('   first hit t=%s  last hit t=%s' % (hits[0].get('t'), hits[-1].get('t')))
    alive = [r for r in recs if r.get('alive')]
    if alive:
        print('alive window    : t=%s .. %s' % (alive[0].get('t'), alive[-1].get('t')))
        gone = [r for r in recs if not r.get('alive') and r.get('t') > alive[0].get('t')]
        if gone:
            print('game gone at t  :', gone[0].get('t'), 'exit=', gone[0].get('exit_code'))
    bboxes = [r.get('panel_bbox') for r in hits if r.get('panel_bbox')]
    if bboxes:
        xs0 = min(b[0] for b in bboxes)
        xs1 = max(b[2] for b in bboxes)
        ys0 = min(b[1] for b in bboxes)
        ys1 = max(b[3] for b in bboxes)
        print('bbox union      :', [xs0, ys0, xs1, ys1])
    print('')
    print('last 8 ticks:')
    for r in recs[-8:]:
        print('   t=%-7s pid=%-6s alive=%-5s panel=%-5s score=%-6s wins=%s'
              % (r.get('t'), r.get('game_pid'), r.get('alive'),
                 r.get('panel'), r.get('panel_score'), r.get('window_count')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
