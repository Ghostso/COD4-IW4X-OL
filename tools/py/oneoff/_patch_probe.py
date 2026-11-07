from pathlib import Path
p = Path('_tcls_dynamic_probe_fixed.py')
s = p.read_text(encoding='utf-8-sig')
s = s.replace("name_first = {}\nname_last = {}", "name_first = {}\nname_last = {}\nbase_names = {(ns, name, typ) for ns in (r'\\BaseNamedObjects', session_namespace()) for name, typ in enum_named_directory(ns) if is_relevant_name(name)}")
s = s.replace("base_pids = set(base)\nbase_files", "base_pids = set(base)\nbase_names = {(ns, name, typ) for ns in (r'\\BaseNamedObjects', session_namespace()) for name, typ in enum_named_directory(ns) if is_relevant_name(name)}\nbase_files")
s = s.replace("if key not in name_first:\n                    name_first[key] = now\n                    print('NAMED_FIRST_SEEN'", "if key not in base_names and key not in name_first:\n                    name_first[key] = now\n                    print('NAMED_FIRST_SEEN'")
s = s.replace("root_selected = descendants(root, procs)\n        for pid in sorted(new | root_selected):", "base_selected = {pid for pid in base_pids if pid in procs and is_relevant_name(procs[pid]['name'])}\n        root_selected = descendants(root, procs)\n        for pid in sorted((new - base_pids) | base_selected):")
s = s.replace("selected = descendants(root, procs)\n        for pid, info in procs.items():\n            if is_relevant_name(info['name']):\n                selected.add(pid)", "selected = {pid for pid in base_pids if pid in procs and is_relevant_name(procs[pid]['name'])}\n        selected |= descendants(root, procs)\n        selected |= {pid for pid, info in procs.items() if pid not in base_pids and is_relevant_name(info['name'])}")
p.write_text(s, encoding='utf-8')
