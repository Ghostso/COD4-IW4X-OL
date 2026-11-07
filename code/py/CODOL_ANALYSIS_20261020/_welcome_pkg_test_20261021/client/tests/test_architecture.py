"""架构验证：实际扫描新模块、依赖方向和运行路径。"""
import ast
import importlib
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
PACKAGE=ROOT/'client/src/codol_rebuild'

def boundary(module):
    name=module.removeprefix('codol_rebuild.')
    for prefix in ('adapters.game.profile_format','adapters.game.v1649370','adapters.persistence','adapters.transport'):
        if name==prefix or name.startswith(prefix+'.'):return prefix
    return name.split('.')[0]

ALLOWED={
 'application':{'application','core'},
 'adapters.persistence':{'adapters.persistence','application','core'},
 'adapters.transport':{'adapters.transport','application','core'},
 'adapters.game.profile_format':{'adapters.game.profile_format','application','core'},
 'adapters.game.v1649370':{'adapters.game.v1649370','adapters.game.profile_format','application','runtime','analysis','core'},
 'runtime':{'runtime','platform','core'},
 'bootstrap':{'bootstrap','application','adapters.persistence','adapters.transport','adapters.game.profile_format','adapters.game.v1649370','runtime','platform','resources','core'},
 'core':{'core'},'resources':{'resources','core'},'platform':{'platform','core'},'analysis':{'analysis','core'},
}

class ArchitectureTests(unittest.TestCase):
    def test_production_dependency_direction(self):
        files=list(PACKAGE.rglob('*.py'))
        self.assertGreater(len(files),40,'扫描目录错误，禁止空扫描通过')
        for path in files:
            module='codol_rebuild.'+'.'.join(path.relative_to(PACKAGE).with_suffix('').parts)
            layer=boundary(module)
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
                imports=([node.module or ''] if isinstance(node,ast.ImportFrom) else [a.name for a in node.names] if isinstance(node,ast.Import) else [])
                if isinstance(node,ast.ImportFrom):self.assertEqual(node.level,0,str(path))
                for target in imports:
                    self.assertFalse(target.startswith(('verification','research')),str(path))
                    if target.startswith('codol_rebuild.') and layer in ALLOWED:
                        self.assertIn(boundary(target),ALLOWED[layer],f'{path}: {target}')
                        if layer=='adapters.game.v1649370' and boundary(target)=='runtime':
                            self.assertEqual(target,'codol_rebuild.runtime.contracts',str(path))
                        if layer in ('adapters.persistence','adapters.transport') and boundary(target)=='application':
                            self.assertTrue(target.endswith('.contracts'),str(path))
                    if layer=='application':
                        self.assertNotIn(target.split('.')[0],{'ctypes','sqlite3','subprocess','struct','socket','requests'},str(path))

    def test_owned_python_modules_have_chinese_purpose(self):
        for folder in ('client/src','client/tools','client/tests','verification/client/tools'):
            for path in (ROOT/folder).rglob('*.py'):
                self.assertRegex(ast.get_docstring(ast.parse(path.read_text(encoding='utf-8-sig'))) or '',r'[\u4e00-\u9fff]',str(path))

    def test_paths_stay_at_existing_data_root(self):
        from codol_rebuild.core.paths import REBUILD_ROOT,PROJECT_ROOT
        self.assertEqual(PROJECT_ROOT,ROOT)
        self.assertEqual(REBUILD_ROOT,ROOT/'client')

    def test_no_old_packages_or_dynamic_imports(self):
        for path in PACKAGE.rglob('*.py'):
            text=path.read_text(encoding='utf-8-sig')
            for prefix in ('codol_rebuild.accounts','codol_rebuild.storage','codol_rebuild.profiles','codol_rebuild.client','codol_rebuild.runtime.offline_debug'):
                self.assertNotIn(prefix,text,str(path))
        for path in PACKAGE.rglob('*.py'):
            parts=path.relative_to(PACKAGE).with_suffix('').parts
            importlib.import_module('codol_rebuild.'+'.'.join(parts))

    def test_runtime_has_no_game_layout_import(self):
        for path in (PACKAGE/'runtime').glob('*.py'):
            text=path.read_text(encoding='utf-8')
            self.assertNotIn('v1649370',text,str(path))
            self.assertNotIn('local_account',text,str(path))
