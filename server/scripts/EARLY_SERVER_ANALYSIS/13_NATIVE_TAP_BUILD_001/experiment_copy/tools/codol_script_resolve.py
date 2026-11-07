#!/usr/bin/env python3
"""Resolve every GSC name the server will actually compile.

A GSC call to a builtin the VM does not register is a COMPILE-time
"unknown function", and the server treats a script compile error at map load
as Sys_Error: the whole match dies.  The failure is therefore not visible at
runtime and not visible in a partial test - it needs the same reachability
walk the loader does, done offline before a script lands in the tree.

What this does:

1.  Builds the VM's builtin table the way Scr_InitFunctions does, by reading
    every Scr_AddFunction / Scr_AddMethod call in src/.  C comments are
    stripped FIRST, so a commented-out registration (for example the legacy
    `// Scr_AddFunction("spawnvehicle", GScr_SpawnVehicle, 0);`) is correctly
    counted as absent.  `#ifdef CODOL_SERVER` arms are included because the
    shipped build defines CODOL_SERVER (makefile IW4OL_DEFINES).
2.  Builds the effective script tree from the active codol_rawfiles root.
    Additional --root paths use first-root-wins precedence, like the loader.
3.  Walks the reachable set from the entry scripts, following #include and
    file::function references, exactly like the lowering pass the log prints
    as "CoDOL lowering: <path>".  Unreachable files are never compiled and are
    deliberately not checked.
4.  Reports, per file: unresolved call names, missing #include targets and
    namespaced calls whose file or function does not exist.

The server registers developer_script as false by default. In that mode GSC
/# ... #/ blocks are ignored; pass --developer-script when checking a server
that enables them.

Exit status is nonzero when anything is unresolved, so this can gate a batch.
"""

import argparse
import collections
import os
import re
import sys

BS = chr(92)
NUL = bytes([0])

DEFAULT_ROOTS = ["bin/home/codol_rawfiles"]

# Everything GScr_LoadScripts reaches DIRECTLY, in src/scr_vm_main.c order.
#
# Get this list wrong and the gate passes something that dies at map load.  It
# happened on 2026-09-20: the zm closure was gated with only _callbacksetup,
# the gametype script and the level script, reported 4 files and "everything
# resolves", and the server then fatally failed to compile
# maps/mp/gametypes/_spawnlogic.gsc -- a file the gate had never looked at.
# The tool was fine; the seeds were not.  Seed what the ENGINE loads, not what
# the scripts you just wrote appear to reference.
BASE_SEEDS = [
    # GScr_LoadScripts, unconditional (scr_vm_main.c:1432-1434).
    "codescripts/delete.gsc",
    "codescripts/struct.gsc",
    # GScr_LoadGameTypeScript loads this by name (scr_vm_main.c:1398-1404).
    "maps/mp/gametypes/_callbacksetup.gsc",
]

# CODOL_ActorScriptsLoadMapTypes selects its unconditional species preload by
# the mounted asset category (codol_actor_scripts.cpp). MP loads dog scripts;
# zm loads zombie scripts; coop loads neither. A category's entity string may
# name further spawners, which still need an explicit --seed for that map.
ACTOR_SUFFIXES = ('init', 'stop', 'move', 'combat', 'death', 'pain',
                  'flashed', 'turn', 'jump')
CATEGORY_SEEDS = {
    'mp': [
    "aitype/enemy_dog_mp.gsc",
    ] + ["maps/mp/animscripts/dog_%s.gsc" % suffix for suffix in ACTOR_SUFFIXES],
    'coop': [],
    'zm': [
        "aitype/enemy_zombie_zm.gsc",
    ] + ["maps/mp/animscripts/zombie_%s.gsc" % suffix for suffix in ACTOR_SUFFIXES],
}

# NOT defaults, because they are per-match and per-category -- pass them with
# --seed, alongside --root <category root> --root <shared root>:
#
#   the gametype script   maps/mp/gametypes/<g_gametype>.gsc
#                         (mp: war/dm/... ; coop: coop.gsc ; zm: zm.gsc)
#   the level script      maps/mp/<mapname>.gsc
#
# e.g. a zombies match on zm_prototype_sh:
#   python tools/codol_script_resolve.py --category zm \
#     --root bin/home/codol_rawfiles/zm --root bin/home/codol_rawfiles \
#     --seed maps/mp/gametypes/zm.gsc --seed maps/mp/zm_prototype_sh.gsc \
#     --binary bin/codol_dedrun_next.exe

# Reserved words and statement keywords that parse like a call but are not one.
KEYWORDS = set("""
if while for switch return wait waittill waittillframeend endon notify thread
foreach else case break continue default waittillmatch self level game anim
true false undefined realwait childthread assert assertex assertmsg waitframe
using_animtree include animtree
""".split())

COMMENT = re.compile(r'/\*.*?\*/', re.S)
LINE_COMMENT = re.compile(r'//[^\n]*')
# Keep the quotes so nothing merges across a removed literal, drop the body.
# GSC string bodies carry prose such as "... use gameFlagInit( <flagName> )",
# which parses as a call and is not one.
#
# Shipped GSC uses escaped quotes inside strings, including Domination's
# diagnostic text and _art's fileprint_launcher source generator. A backslash
# and following character must stay in the same literal when locating its end;
# this also keeps path literals such as "maps\mp\..." entirely masked.
STRING = re.compile(r'"(?:\\.|[^"\\\n])*"')
CALL = re.compile(r'(?:^|[^\w:.])([A-Za-z_][A-Za-z0-9_]*)\s*\(')
NAMESPACED = re.compile(
    '([A-Za-z_][A-Za-z0-9_' + BS + BS + '/]*)' + r'[ \t]*::[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]*\(')
INCLUDE = re.compile(r'#include\s+([^;]+);')
# A definition is a name at column zero or one whose parameter list may span
# lines (maps/mp/gametypes/_killcam.gsc::killcam is written that way) and whose
# body brace follows.
DEFINITION = re.compile(
    r'^[ \t]{0,1}([A-Za-z_][A-Za-z0-9_]*)[ \t]*\(([^()]*)\)[ \t]*\r?\n?[ \t]*\{', re.M | re.S)
REGISTRATION = re.compile(r'Scr_Add(?:Function|Method)\s*\(\s*"([A-Za-z0-9_]+)"')


def normalize(text):
    """Some shipped IW4 scripts use CR-only line endings.

    Without this, `//comment` would swallow the rest of the file and every
    definition after it would vanish, which reads as a wall of false
    "unknown function" reports.
    """
    return text.replace('\r\n', '\n').replace('\r', '\n')


def strip_comments(text):
    return LINE_COMMENT.sub('', COMMENT.sub('', normalize(text)))


def strip_strings(text):
    return STRING.sub('""', text)


def scan_developer_blocks(text, enabled=False):
    """Mask inactive /# ... #/ code and report malformed delimiters.

    Call after stripping strings and ordinary comments, so delimiters inside
    those regions cannot hide live script code.
    """
    output = list(text)
    opened = None
    errors = []
    for match in re.finditer(r'/#|#/', text):
        if match.group() == '/#':
            if opened is not None:
                errors.append('line %d: cannot recurse /#' %
                              (text.count('\n', 0, match.start()) + 1))
            else:
                opened = match.start()
        elif opened is None:
            errors.append('line %d: #/ has no matching /#' %
                          (text.count('\n', 0, match.start()) + 1))
        else:
            if not enabled:
                for pos in range(opened, match.end()):
                    if output[pos] != '\n':
                        output[pos] = ' '
            opened = None
    if opened is not None:
        errors.append('line %d: /# has no matching #/' %
                      (text.count('\n', 0, opened) + 1))
    return ''.join(output), errors


def builtin_table(src_dir):
    """Every name the VM will resolve, from live (uncommented) registrations."""
    names = set()
    for base, _dirs, files in os.walk(src_dir):
        for name in files:
            if not name.endswith(('.c', '.cpp')):
                continue
            path = os.path.join(base, name)
            try:
                text = open(path, errors='replace').read()
            except OSError:
                continue
            for match in REGISTRATION.finditer(strip_comments(text)):
                names.add(match.group(1).lower())
    return names


def effective_tree(roots):
    """rel path -> on-disk path, first root wins, like the overlay loader."""
    tree, origin = {}, {}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for base, _dirs, files in os.walk(root):
            for name in files:
                if not name.lower().endswith('.gsc'):
                    continue
                path = os.path.join(base, name)
                rel = os.path.relpath(path, root).replace(BS, '/').lower()
                if rel not in tree:
                    tree[rel] = path
                    origin[rel] = root
    return tree, origin


def dependencies(text):
    includes = [m.group(1).strip().lower().replace(BS, '/') + '.gsc'
                for m in INCLUDE.finditer(text)]
    referenced = set(m.group(1).lower().replace(BS, '/') + '.gsc'
                     for m in NAMESPACED.finditer(text))
    return includes, referenced


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--src', default='src', help='native source root')
    parser.add_argument('--category', choices=tuple(CATEGORY_SEEDS), default='mp',
                        help='mounted asset category; selects its native actor '
                             'preload seeds (default: mp)')
    parser.add_argument('--root', action='append', dest='roots',
                        help='script root, highest precedence first (repeatable)')
    parser.add_argument('--seed', action='append', dest='seeds',
                        help='ADDITIONAL entry script, relative and lowercase '
                             '(repeatable). Added to the category load seeds, which are the '
                             'scripts the engine always loads; use it for the '
                             'per-match gametype and level scripts. It used to '
                             'REPLACE the defaults, which is how a zm gate once '
                             'passed a tree that fatally failed to compile.')
    parser.add_argument('--only-seeds', action='store_true', dest='only_seeds',
                        help='use ONLY the --seed entries, ignoring engine and category seeds. '
                             'For probing one subtree; never for gating a batch.')
    parser.add_argument('--binary', dest='binary',
                        help='validate against a BUILT server binary as well as '
                             'the source: a builtin registered in src/ but absent '
                             'from this exe is not callable by the server that is '
                             'actually running. Use the deployed exe before '
                             'shipping scripts, because GSC resolves builtin '
                             'names at compile time and naming a missing one is a '
                             'fatal map-load error, not a runtime failure.')
    parser.add_argument('--only', action='append', dest='only',
                        help='only report scripts whose path starts with this '
                             'prefix (repeatable); use it to gate one batch '
                             'without inheriting unrelated vendor diagnostics')
    parser.add_argument('--list-reachable', action='store_true',
                        help='print every script the loader would lower')
    parser.add_argument('--quiet', action='store_true')
    parser.add_argument('--developer-script', action='store_true',
                        help='include GSC /# ... #/ developer blocks (the '
                             'server developer_script cvar defaults to false)')
    args = parser.parse_args()

    roots = args.roots or DEFAULT_ROOTS
    # --seed ADDS to the engine's own load set. Replacing it is opt-in, because
    # a short seed list is indistinguishable from a clean gate in the output.
    if args.only_seeds:
        seeds = list(args.seeds or [])
    else:
        defaults = BASE_SEEDS + CATEGORY_SEEDS[args.category]
        seeds = defaults + [s for s in (args.seeds or []) if s not in defaults]

    registered = builtin_table(args.src)
    if not registered:
        print('error: no builtin registrations found under %s' % args.src)
        return 2
    binary_missing = set()
    if args.binary:
        try:
            blob = open(args.binary, 'rb').read()
        except OSError as error:
            print('error: cannot read %s: %s' % (args.binary, error))
            return 2
        # Registration names are stored as NUL-terminated literals; require the
        # exact token so a substring of a longer name cannot vouch for it.
        present = set()
        for name in registered:
            token = NUL + name.encode() + NUL
            if token in blob:
                present.add(name)
        binary_missing = registered - present
        registered = present
    tree, origin = effective_tree(roots)
    if not tree:
        print('error: no scripts found under %s' % ', '.join(roots))
        return 2

    text = {}
    defined = collections.defaultdict(set)
    syntax_errors = {}
    for rel, path in tree.items():
        body = strip_strings(strip_comments(open(path, errors='replace').read()))
        body, syntax_errors[rel] = scan_developer_blocks(
            body, enabled=args.developer_script)
        text[rel] = body
        for match in DEFINITION.finditer(body):
            defined[rel].add(match.group(1).lower())

    reachable, pending, absent_seeds = set(), list(seeds), []
    for seed in seeds:
        if seed not in tree:
            absent_seeds.append(seed)
    while pending:
        rel = pending.pop()
        if rel in reachable or rel not in tree:
            continue
        reachable.add(rel)
        includes, referenced = dependencies(text[rel])
        pending.extend(includes)
        pending.extend(referenced)

    problems = collections.OrderedDict()
    for rel in sorted(reachable):
        includes, _ = dependencies(text[rel])
        scope = set(defined[rel])
        missing_includes = []
        for include in includes:
            if include in tree:
                scope |= defined[include]
            else:
                missing_includes.append(include)

        unresolved = collections.Counter()
        for match in CALL.finditer(text[rel]):
            name = match.group(1).lower()
            if name in KEYWORDS or name in registered or name in scope:
                continue
            unresolved[name] += 1

        bad_namespaced = []
        for match in NAMESPACED.finditer(text[rel]):
            target = match.group(1).lower().replace(BS, '/') + '.gsc'
            function = match.group(2).lower()
            if target not in tree:
                bad_namespaced.append('no such script: ' + target)
            elif function not in defined[target]:
                bad_namespaced.append('no such function: %s::%s' % (target, function))

        # Directive ORDER. Every #include must precede every #using_animtree.
        # MEASURED across the shipped tree: 236 files put #include first and
        # ZERO do the reverse. The compiler rejects the other order with
        # "bad syntax" pointing at the #include line, which is a Sys_Error at
        # map load -- and this gate happily passed a zm tree that did exactly
        # that on 2026-09-20, because resolving an include says nothing about
        # whether the file parses. Cheap structural check, real failure class.
        order_problems = []
        first_include = first_animtree = None
        for lineno, line in enumerate(text[rel].splitlines(), 1):
            stripped = line.strip()
            if first_include is None and stripped.startswith('#include'):
                first_include = lineno
            if first_animtree is None and stripped.startswith('#using_animtree'):
                first_animtree = lineno
        if first_include is not None and first_animtree is not None \
                and first_include > first_animtree:
            order_problems.append(
                '#using_animtree (line %d) precedes #include (line %d): the '
                'compiler rejects this with "bad syntax" at the #include'
                % (first_animtree, first_include))

        # Assignment to a RESERVED object name. `level`, `game`, `self` and
        # `anim` are built-in object references, not identifiers you may bind.
        # MEASURED 2026-09-20: three ported T5 functions declared a local
        # named `anim`, and the compiler answered "bad syntax" at the
        # assignment -- a Sys_Error at map load. The shipped mp tree, which is
        # thousands of files, does this exactly zero times.
        for lineno, line in enumerate(text[rel].splitlines(), 1):
            code = line.split('//', 1)[0]
            for reserved in ('anim', 'level', 'game', 'self'):
                if re.search(r'(?<![A-Za-z0-9_.])' + reserved + r'\s*=(?!=)', code):
                    order_problems.append(
                        'line %d assigns to the reserved object name "%s"; '
                        'the compiler rejects this with "bad syntax"'
                        % (lineno, reserved))

        if args.only and not any(rel.startswith(prefix.lower()) for prefix in args.only):
            continue

        bad_namespaced = bad_namespaced + order_problems + syntax_errors[rel]
        if unresolved or missing_includes or bad_namespaced:
            problems[rel] = (unresolved, missing_includes, sorted(set(bad_namespaced)))

    if args.list_reachable:
        for rel in sorted(reachable):
            print('%-60s %s' % (rel, origin[rel]))

    if not args.quiet:
        print('builtins registered: %d' % len(registered))
        if args.binary:
            print('validated against binary: %s (%d source registrations absent '
                  'from it)' % (args.binary, len(binary_missing)))
        print('scripts in effective tree: %d' % len(tree))
        print('scripts the loader would lower: %d' % len(reachable))

    status = 0
    if absent_seeds:
        status = 1
        print('\nMISSING ENTRY SCRIPTS')
        for seed in absent_seeds:
            print('  %s' % seed)

    if problems:
        status = 1
        print('\nUNRESOLVED NAMES (each one is a fatal map-load compile error)')
        for rel, (unresolved, missing_includes, bad_namespaced) in problems.items():
            print('\n  %s' % rel)
            print('    %s' % tree[rel])
            for include in missing_includes:
                print('    missing #include: %s' % include)
            for entry in bad_namespaced:
                print('    %s' % entry)
            for name, count in sorted(unresolved.items()):
                print('    unknown function: %s (%d call site%s)'
                      % (name, count, '' if count == 1 else 's'))
    elif not args.quiet:
        print('\nevery reachable script resolves against the registered builtin table')

    return status


if __name__ == '__main__':
    sys.exit(main())
