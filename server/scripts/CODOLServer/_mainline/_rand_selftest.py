import sys
sys.path.insert(0,r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline')
import rand_key_recover as R
# consistency: prev(next(s))==s
for s in (1,0x12345678,0xdeadbeef,0xffffffff):
    assert R.prev_state(R.next_state(s))==s, hex(s)
print('LCG inverse OK')
# generate a key from a known state and confirm alphabet-only
st=0x12345678
outs=R.outputs_from(st,16)
k=R.key_from_rand_outputs(outs)
print('key', k, 'alphabet-only', all(c in R.ALPHABET for c in k))
print('outs', outs[:8])
