"""Prepare an isolated inflated-zone repair; never install or emit a disk FF.

The existing writer's IWffu100 container is only accepted for memory FFOTD.
This output is a review artifact pending faithful client asset delivery.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reference-root', type=Path, required=True)
    ap.add_argument('--out-dir', type=Path, required=True)
    args = ap.parse_args()
    reference = args.reference_root.resolve()
    output = args.out_dir.resolve()
    install = reference.parents[2]
    if output == install or install in output.parents:
        raise SystemExit('Output must be outside the client install and lobby tree')
    sys.path.insert(0, str(reference))
    import zone_assets as za
    source = Path(za.ff_dir()) / 'patch_common_gametype_mp.ff'
    archive = source.read_bytes()
    expected = '04f5290c5b705260b832a3ba8455233e48381d17a8cb5b77d773138ce26f4256'
    if sha(archive) != expected:
        raise SystemExit('Source archive differs from the audited build')
    original = za.inflate_ff(str(source), verify=True)
    zone = za.Zone(original, source.stem)
    matches = [a for a in zone.by_type(28)
               if a.blob[0xbfc:].startswith(b'm4a1techevent_mp\0')]
    if len(matches) != 1:
        raise SystemExit('Expected exactly one event WeaponDef')
    asset = matches[0]
    repaired = bytearray(original)
    changes = []
    for dest, source_field, expected_value in ((0xa4, 0xa0, 0x30090205),
                                              (0xac, 0xa8, 0x30095066)):
        absolute = 0x28 + asset.offset + dest
        old = struct.unpack_from('<I', repaired, absolute)[0]
        value = struct.unpack_from('<I', asset.blob, source_field)[0]
        if old != 0x300080b1 or value != expected_value:
            raise SystemExit('Weapon fields differ from audited source')
        struct.pack_into('<I', repaired, absolute, value)
        changes.append(dict(field=hex(dest), absolute_zone_offset=hex(absolute),
                            before=hex(old), after=hex(value)))
    output.mkdir(parents=True, exist_ok=True)
    artifact = output / 'patch_common_gametype_mp.event_fastmag.zone'
    manifest = dict(status='isolated inflated artifact; not client-loadable FF',
                    source=str(source), source_sha256=sha(archive),
                    source_zone_sha256=sha(original), artifact=str(artifact),
                    artifact_sha256=sha(repaired), zone_bytes=len(repaired),
                    asset_index=asset.index, asset_type=28,
                    asset_name='m4a1techevent_mp',
                    asset_zone_offset=hex(0x28 + asset.offset), changes=changes)
    # Exclusive creation avoids overwriting a previously reviewed artifact.
    with artifact.open('xb') as f:
        f.write(repaired)
    with (output / 'manifest.json').open('x', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
        f.write('\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
