"""Offline check of a captured native snapshot against trusted alpha0022 readers."""
import argparse
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--reference', required=True, type=Path)
args = parser.parse_args()
sys.path[:0] = [str(root / 'tools'), str(args.reference.resolve())]
from codol_snapshot_decode import decode_baseline, decode_snapshot

payload = (root / 'tests/fixtures/codol_snapshot/native_bog_baseline.bin').read_bytes()
decoded = decode_baseline(payload)
assert decoded['bytes'] == 3078 and decoded['server_time'] == 6600
assert decoded['entities'] == 140 and decoded['clients'] == [0] and decoded['actors'] == 0
assert decoded['entity_types'] == {6: 140} and decoded['exact_eof']
assert [row['model'] for row in decoded['brush_models']] == list(range(1, 36))
assert decoded['brush_models'][0] == {'number': 72, 'model': 1}
bad_payloads = [payload[:size] for size in
                (0, 1, 7, 8, 40, len(payload)//2, len(payload)-100,
                 len(payload)-8, len(payload)-2, len(payload)-1)]
bad_payloads += [payload + b'\0', payload[:-1] + b'\0', payload[:5] + b'\1' + payload[6:]]
for bad in bad_payloads:
    try:
        decode_baseline(bad)
    except (ValueError, IndexError):
        continue
    raise AssertionError('Malformed snapshot accepted')
print('PASS: captured native baseline; all sections, 140 entities, 35 brush models, exact EOF; 13 malformed variants rejected')

fixtures = root / 'tests/fixtures/codol_snapshot'
base_report, base = decode_snapshot((fixtures / 'native_bog_delta_base.bin').read_bytes(), 6)
delta = (fixtures / 'native_bog_delta.bin').read_bytes()
report, state = decode_snapshot(delta, 7, base)
assert report['delta'] == 1 and report['base_sequence'] == 6
assert report['bytes'] == 1758 and report['server_time'] == 5800 and report['exact_eof']
assert report['entities'] == 140 and report['clients'] == [0]
assert report['brush_models'] == base_report['brush_models']
assert state['ps'] != base['ps'], 'Second movement must update player state'
for bad, sequence, prior in [(delta, 7, None), (delta, 8, base),
                             (delta[:-1], 7, base), (delta + b'\0', 7, base)]:
    try:
        decode_snapshot(bad, sequence, prior)
    except (ValueError, IndexError):
        continue
    raise AssertionError('Invalid delta or missing/mismatched base accepted')
print('PASS: acknowledged baseline -> native delta; updated player state, retained brush models; invalid deltas rejected')
