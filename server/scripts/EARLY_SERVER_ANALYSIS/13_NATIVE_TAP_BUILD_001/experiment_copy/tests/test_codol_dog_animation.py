"""Dog actor state machine and C1 animation-tree binding.

Two failures this catches, both of which are silent at runtime:

1.  A clip name in `codol_dog_states.cpp` that the C1 dog animation tree does
    not declare.  `CODOL_DogStateApply` binds the whole clip table before it
    runs any state, so ONE unbound name disables every dog animation, with no
    error anywhere.  The staged T5 port had 19 of them: OpenBLOPS
    `bg_dog_animations_mp.cpp` spells the model `german_shepard` (one 'h') and
    names turn/directional-pain/directional-death clips that exist in T5's
    tree and in no C1 zone.

2.  A `setanimstate( "..." )` in the ported dog animscripts whose state has no
    row in the native table.  That is a script-visible error the state machine
    can only report at the moment the state is first entered, i.e. during a
    live match.

The animation tree is ground truth, not a copy kept in this file: C1
1.1.1.13 ships `animtrees/dog.atr` as rawfile #206 of `common_mp.zone`, and
that payload is byte-identical to the IW4 tree already collated into
`bin/home/codol_rawfiles/animtrees/dog.atr` (C1's dog is the IW4 dog, not
T5's).  The collated copy is what the test reads, so the check keeps working
without a mounted client install; `--atr` points it at any other copy.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATES = ROOT/'src/codol/player/codol_dog_states.cpp'
TREE = ROOT/'bin/home/codol_rawfiles/animtrees/dog.atr'
SCRIPTS = ROOT/'scripts/codol/maps/mp/animscripts'


def tree_nodes(text):
    """Every name the tree declares: group heads and their leaves alike.

    A group head is a usable animation reference in its own right - the run
    knob `german_shepherd_run_knob` is exactly how the locomotion goal is
    driven - so both sides of a `name : class { ... }` block count.
    """
    names = set()
    for raw in text.splitlines():
        line = raw.split('//')[0].strip()
        if not line or line in '{}':
            continue
        line = line.rstrip('{').strip()
        if not line:
            continue
        names.add(line.split(':')[0].strip())
    names.discard('')
    return names


def source_array(text, name):
    """Read a `static const char *const <name>[N] = { ... };` string table."""
    start = re.search(r'\b' + name + r'\s*\[\s*\d*\s*\]\s*=\s*\{', text)
    assert start, f'{name} table not found in {STATES.name}'
    depth, i = 1, start.end()
    while depth:
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
        i += 1
    return re.findall(r'"([^"]*)"', text[start.end():i])


def state_rows(text):
    start = text.index('static const dog_state_row stateRows[]')
    end = text.index('};', start)
    return re.findall(r'\{\s*"([^"]+)"', text[start:end])


def script_states(directory):
    """setanimstate( "literal" ) across the ported dog animscripts.

    Computed state names (`"death_" + direction`) are deliberately not guessed
    here; the death/pain families are covered by the explicit list below.
    """
    used = {}
    for path in sorted(directory.glob('dog_*.gsc')):
        text = path.read_text(errors='replace')
        for name in re.findall(r'setanimstate\s*\(\s*"([^"]+)"', text):
            used.setdefault(name, path.name)
    return used


# maps/mp/animscripts/dog_death.gsc builds "death_" + getAnimDirection(), and
# dog_pain.gsc builds "pain_" / "pain_run_" + the same four directions.
COMPUTED = ['death_' + d for d in ('front', 'back', 'left', 'right')] + \
           ['pain_' + d for d in ('front', 'back', 'left', 'right')] + \
           ['pain_run_' + d for d in ('front', 'back', 'left', 'right')]

# dog_turn.gsc passes these through do_turn_anim( stopped_anim, run_anim, ... ).
TURNS = ['move_turn_left', 'move_turn_right',
         'move_run_turn_left', 'move_run_turn_right',
         'move_turn_around_left', 'move_turn_around_right',
         'move_run_turn_around_left', 'move_run_turn_around_right']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--atr', type=Path, default=TREE,
                        help='dog animation tree to check against')
    parser.add_argument('--scripts', type=Path, default=SCRIPTS,
                        help='directory holding the ported dog animscripts')
    args = parser.parse_args()

    assert args.atr.is_file(), f'missing animation tree {args.atr}'
    nodes = tree_nodes(args.atr.read_text(errors='replace'))
    assert 'german_shepherd_idle' in nodes, f'{args.atr} is not a dog tree'

    source = STATES.read_text(errors='replace')
    clips = source_array(source, 'clipNames')
    rows = state_rows(source)

    # Index 0 is the tree root; CODOL_DogStateApply hardcodes ref 0 for it and
    # never looks it up, so it is the one entry with no node of its own.
    unbound = sorted({c for c in clips[1:] if c not in nodes})
    assert not unbound, (
        'clip names not declared by the C1 dog tree (every dog animation '
        'would silently fail to bind): ' + ', '.join(unbound))

    # CODOL_DogStateApply range-checks against ACTOR_ANIMATION_COUNT; the row
    # table and that enum must stay the same width or a state either cannot be
    # reached or indexes past the table.
    count = re.search(r'ACTOR_ANIMATION_COUNT\s*=\s*(\d+)', source)
    assert count, 'ACTOR_ANIMATION_COUNT not found'
    assert len(rows) == int(count.group(1)), (
        f'{len(rows)} state rows but ACTOR_ANIMATION_COUNT is {count.group(1)}')
    assert len(set(rows)) == len(rows), 'duplicate state name in stateRows'

    checked_scripts = 0
    if args.scripts.is_dir():
        used = script_states(args.scripts)
        checked_scripts = len(set(p for p in used.values()))
        missing = sorted({n: f for n, f in used.items() if n not in rows}.items())
        assert not missing, (
            'dog animscripts call setanimstate with states the native table '
            'has no row for: ' + ', '.join(f'{n} ({f})' for n, f in missing))

    for name in COMPUTED + TURNS:
        assert name in rows, f'computed script state {name!r} has no native row'

    print(f'PASS: {len(clips)} clips bind in {args.atr.name} '
          f'({len(nodes)} nodes); {len(rows)} states; '
          f'{len(COMPUTED) + len(TURNS)} computed script states; '
          f'{checked_scripts} animscript files checked')


if __name__ == '__main__':
    sys.exit(main())
