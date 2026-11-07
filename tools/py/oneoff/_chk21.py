import sqlite3, os, re, datetime
home = os.path.expanduser('~')
TZ = datetime.timezone(datetime.timedelta(hours=8))
def ts2s(ts):
    return datetime.datetime.fromtimestamp(ts, TZ).strftime('%m-%d %H:%M:%S')
db = os.path.join(home, '.codex', 'logs_2.sqlite')
con = sqlite3.connect('file:' + db.replace(os.sep, '/') + '?mode=ro', uri=True)
cur = con.cursor()
T0 = 1792496400  # 10-20 19:40 approx start; will also show earlier
print('=== errors/timeouts since 17:00 ===')
rows = cur.execute("SELECT ts, level, target, substr(feedback_log_body, -330) FROM logs WHERE ts >= 1792486800 AND level IN ('WARN','ERROR') AND (feedback_log_body LIKE '%504%' OR feedback_log_body LIKE '%RELAY%' OR feedback_log_body LIKE '%timeout%' OR feedback_log_body LIKE '%timed out%' OR feedback_log_body LIKE '%upstream%') ORDER BY ts DESC LIMIT 20").fetchall()
if not rows: print('(none)')
for ts, lv, tg, b in rows:
    i = b.rfind('}:')
    print(ts2s(ts), lv, tg.replace('codex_', ''), '|', (b[i+2:] if i >= 0 else b).strip()[:260])
print()
print('=== latest 8 sampling rows (tokens) ===')
rows = cur.execute('SELECT ts, feedback_log_body FROM logs WHERE feedback_log_body LIKE ? ORDER BY ts DESC LIMIT 8', ('%post sampling token usage%',)).fetchall()
for ts, b in rows:
    m = re.search(r'model=([\w.\-]+)', b)
    t = re.search(r'total_usage_tokens=(\d+)', b)
    lim = re.search(r'auto_compact_scope_limit=Some\((\d+)\)', b)
    full = re.search(r'full_context_window_limit=Some\((\d+)\)', b)
    print(ts2s(ts), m.group(1) if m else '?', 'tokens=', t.group(1) if t else '?', 'limit=', lim.group(1) if lim else '?', 'full=', full.group(1) if full else '?')
print()
print('=== http client timing lines (last 12) ===')
rows = cur.execute("SELECT ts, substr(feedback_log_body, -300) FROM logs WHERE target LIKE '%http_client%' ORDER BY ts DESC LIMIT 12").fetchall()
for ts, b in rows:
    i = b.rfind('}:')
    print(ts2s(ts), '|', (b[i+2:] if i >= 0 else b).strip()[:240])
con.close()
