"""重构差分验证：原生安装轨迹与真实档案初始化字节等价。"""
import ast
import ctypes as C
from ctypes import wintypes as W
import copy
import json
from pathlib import Path
import struct
import sys
import tempfile
import textwrap
import types
import unittest
import pefile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'client/src'))
BASE=ROOT/'client/tests/fixtures/refactor-20261020'
PKG=ROOT/'client/src/codol_rebuild'
CAPTURE=ROOT/'client/workspaces/offline-runs/offline-20261020-040037-7938274a/local-profile'
IMAGE=ROOT/'client/bin/v1649370/codol1649370-offline.exe'
REPLACEMENTS={'codol_rebuild.accounts.bootstrap_service':'codol_rebuild.application.accounts.service',
 'codol_rebuild.accounts':'codol_rebuild.application.accounts','codol_rebuild.storage':'codol_rebuild.adapters.persistence',
 'codol_rebuild.profiles':'codol_rebuild.adapters.game.profile_format','codol_rebuild.client.v1649370':'codol_rebuild.adapters.game.v1649370'}

def old_source(path):
    text=(BASE/path).read_text(encoding='utf-8-sig')
    for a,b in REPLACEMENTS.items():text=text.replace(a,b)
    return text

class MemoryProcess:
    """固定镜像只读底图加独立写入记录，不访问运行游戏。"""
    def __init__(self):
        self.pe=pefile.PE(str(IMAGE));self.memory={};self.cursor=0x20000000;self.writes=[];self.protections=[]
        self.main_thread_id=123
    def allocate(self,size=4096):
        address=self.cursor;self.cursor+=(size+4095)&~4095
        self.memory.update({i:0 for i in range(address,address+size)})
        return address
    def read(self,address,size):
        data=self.pe.get_data(address-0x400000,size) if 0x400000<=address<0x10000000 else bytes(size)
        data=data.ljust(size,b'\0')
        return bytes(self.memory.get(address+i,data[i]) for i in range(size))
    def write(self,address,data):
        self.writes.append((address,bytes(data)))
        self.memory.update({address+i:b for i,b in enumerate(data)})
    def executable(self,address,size=4096):self.protections.append((address,size))
    def periodic(self,interval):
        from codol_rebuild.runtime.scheduler import PeriodicTask
        return PeriodicTask(interval)

class Debugger:
    def __init__(self,process):self.process=process;self.breaks={}
    def arm(self,address,label):
        if address not in self.breaks:
            self.breaks[address]=(self.process.read(address,1),label);self.process.write(address,b'\xcc')

class RefactorEquivalenceTests(unittest.TestCase):
    def test_native_generators_unchanged(self):
        files=list((BASE/'client/v1649370').glob('*.py'))
        self.assertGreater(len(files),10)
        for old in files:
            if old.name=='image.py':continue
            baseline=ast.parse(old_source(old.relative_to(BASE)))
            current=ast.parse((PKG/'adapters/game/v1649370'/old.name).read_text(encoding='utf-8'))
            if old.name == 'profile.py':
                # 新档授权改动由专门测试覆盖，其余原生函数保持差分约束。
                changed = {'build_initializer', 'capture', 'populate_inventory'}
                current_functions = {n.name: n for n in current.body if isinstance(n, ast.FunctionDef)}
                for node in baseline.body:
                    if isinstance(node, ast.FunctionDef) and node.name not in changed:
                        self.assertEqual(ast.dump(node), ast.dump(current_functions[node.name]), node.name)
                continue
            self.assertEqual(ast.dump(baseline),ast.dump(current),old.name)

    def test_full_local_install_trace_equivalent(self):
        from codol_rebuild.adapters.game.v1649370.session_bridge import GameSessionBridge
        from codol_rebuild.adapters.game.v1649370 import layout
        from codol_rebuild.adapters.game.v1649370.menu_preview import PreviewActivationCycles
        src=old_source('runtime/offline_debug.py')
        # 基线流程调用当前生成器，需要同样大小的物品分类结果缓冲。
        src=src.replace("profile_data=check(api(K,'VirtualAllocEx',PTR,PTR,PTR,SIZE,W.DWORD,W.DWORD)(pi.process,None,4096,0x3000,4))",
                        "profile_data=check(api(K,'VirtualAllocEx',PTR,PTR,PTR,SIZE,W.DWORD,W.DWORD)(pi.process,None,69632,0x3000,4))")
        run=next(n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name=='run')
        fun=next(n for n in run.body if isinstance(n,ast.FunctionDef) and n.name=='install_menu_preview')
        fun.body=[ast.Global(names=n.names) if isinstance(n,ast.Nonlocal) else n for n in fun.body]
        for local in (False,True):
            with self.subTest(local_profile=local), tempfile.TemporaryDirectory() as tmp:
                args=types.SimpleNamespace(local_profile=local)
                before=MemoryProcess();after=MemoryProcess();bdebug=Debugger(before);adebug=Debugger(after)
                def api(lib,name,*signature):
                    if name=='VirtualAllocEx':return lambda handle,addr,size,*tail:before.allocate(size)
                    if name=='VirtualProtectEx':return lambda handle,addr,size,*tail: before.executable(addr,size) or 1
                    raise AssertionError(name)
                namespace={'__package__':'codol_rebuild','C':C,'W':W,'api':api,'K':None,'PTR':None,'SIZE':None,
                    'check':lambda v:v,'pi':types.SimpleNamespace(process=1), 'args':args,'image':IMAGE,
                    'mem':before.read,'write':before.write,'arm':bdebug.arm,'layout':layout,
                    'record':lambda row:None,'log':{},'profile_traps':{},'preview_traps':{},'preview_metadata':{},
                    'name_adapter':None,'run_dir':Path(tmp),'struct':struct,'hashlib':__import__('hashlib')}
                exec(compile(ast.fix_missing_locations(ast.Module(body=[fun],type_ignores=[])),'baseline-install','exec'),namespace)
                namespace['install_menu_preview']()
                bridge=GameSessionBridge(args,Path(tmp),IMAGE,after.pe,{},lambda row:None,lambda name:None,after,None,(ValueError,))
                bridge.bind_debugger(adebug);bridge.install_menu_preview()
                self.assertEqual(before.writes,after.writes)
                self.assertEqual(before.protections,after.protections)
                self.assertEqual(bdebug.breaks,adebug.breaks)
                self.assertEqual(namespace['profile_traps'],bridge.profile_traps)
                self.assertEqual(namespace['preview_traps'],bridge.preview_traps)
                self.assertEqual(namespace['name_adapter'],bridge.name_adapter)

    def test_real_profile_bootstrap_equivalent(self):
        from codol_rebuild.application.accounts.service import bootstrap
        from codol_rebuild.adapters.game.profile_format.account_codec import AccountCodec
        captured=json.loads((CAPTURE/'capture.json').read_text(encoding='utf-8'))
        schemas={kind:json.loads((CAPTURE/label/'playerdata-schema.json').read_text(encoding='utf-8'))
                 for kind,label in [('public','playerdata'),('secure','playersecuredata')]}
        ns={};exec(old_source('accounts/bootstrap_service.py'),ns)
        class Store:
            def __init__(self):self.state={'uid':0x8765432198765432,'profiles':{},'revision':0};self.calls=[]
            def identity(self,name):return self.state
            def load(self,name,identities):return copy.deepcopy(self.state)
            def save(self,name,revision,profiles,identities):
                self.calls.append((name,revision,profiles,identities))
                assert revision==self.state['revision']
                self.state={**self.state,'profiles':profiles,'revision':revision+1}
                return revision+1
        before=Store();after=Store();codec=AccountCodec(schemas,captured['tables'],captured['catalog'])
        # 旧档保留全解锁行为；新档授权策略另有验证。
        ns['bootstrap'](before,schemas,captured['tables'],captured['catalog'])
        after.state=copy.deepcopy(before.state)
        before.calls.clear()
        for cycle in range(2):
            old=ns['bootstrap'](before,schemas,captured['tables'],captured['catalog'])
            new=bootstrap(after,codec)
            self.assertEqual(old,new,f'cycle {cycle}')
            self.assertEqual(before.calls,after.calls)

    def test_account_failed_save_keeps_revision(self):
        from codol_rebuild.application.accounts.service import AccountSession
        from codol_rebuild.application.accounts.contracts import RevisionConflict
        class Codec:
            identities={}
            def validate_snapshot(self,blobs):return 545
        class Store:
            def save(self,*args):raise RevisionConflict('stale')
        service=AccountSession(Store(),Codec())
        service.account={'profiles':{'public':b'old','secure':b'old'},'revision':8}
        previous=copy.deepcopy(service.account)
        with self.assertRaises(RevisionConflict):service.save({'public':b'new','secure':b'new'})
        self.assertEqual(previous,service.account)

if __name__=='__main__':unittest.main()

