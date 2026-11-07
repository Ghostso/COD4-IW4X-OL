import os, re, shutil, time
home = os.path.expanduser('~')
cfg = os.path.join(home, '.codex', 'config.toml')
bak = cfg + '.bak-timeout-' + time.strftime('%Y%m%d-%H%M%S')
shutil.copy2(cfg, bak)
print('backup ->', bak)
lines = open(cfg, encoding='utf-8').read().splitlines(keepends=True)
start = None
for i, ln in enumerate(lines):
    if ln.strip() == '[model_providers.custom]':
        start = i
        break
if start is None:
    raise SystemExit('provider block not found')
end = len(lines)
for j in range(start + 1, len(lines)):
    if lines[j].lstrip().startswith('['):
        end = j
        break
block = ''.join(lines[start:end])
print('=== current block ===')
print(block)
want = {'stream_idle_timeout_ms': '300000', 'request_max_retries': '8', 'stream_max_retries': '8'}
new_lines = []
for ln in lines[start:end]:
    new_lines.append(ln)
for k, v in want.items():
    if re.search(r'^\s*' + re.escape(k) + r'\s*=', block, re.M):
        new_lines = [re.sub(r'^(\s*)' + re.escape(k) + r'\s*=.*$', r'\g<1>' + k + ' = ' + v, l) for l in new_lines]
    else:
        new_lines.append(k + ' = ' + v + '\n')
lines[start:end] = new_lines
open(cfg, 'w', encoding='utf-8').writelines(lines)
print('=== new block ===')
out = open(cfg, encoding='utf-8').read().splitlines()
s2 = out.index('[model_providers.custom]')
e2 = s2 + 1
while e2 < len(out) and not out[e2].startswith('['):
    e2 += 1
print('\n'.join(out[s2:e2]))
