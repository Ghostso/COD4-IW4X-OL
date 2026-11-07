"""拆分后的事件契约：改名提交顺序、失败补偿和准备阶段收尾。"""
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock

from codol_rebuild.adapters.game.v1649370.session_bridge import GameSessionBridge
from codol_rebuild.adapters.game.v1649370 import player_name
from codol_rebuild.bootstrap import launch
from codol_rebuild.runtime.scheduler import PeriodicTask
from codol_rebuild.runtime.session import ProcessSession

class BridgeEventTests(unittest.TestCase):
    def bridge(self, fail=False):
        events=[]; memory={};ctx=bytearray(716)
        struct.pack_into('<I',ctx,180,0x30000000);struct.pack_into('<I',ctx,196,0x30000000)
        def write(address,data):
            events.append(('write',address,bytes(data)));memory[address]=bytes(data)
        process=SimpleNamespace(main_thread_id=17,read=lambda address,size:memory.get(address,bytes(size)),
            write=write,context=lambda tid:(1,ctx),set_context=lambda *a:None,close_thread=lambda h:events.append(('close',)),
            periodic=lambda interval:PeriodicTask(interval))
        bridge=GameSessionBridge(SimpleNamespace(local_profile=True),Path('.'),None,None,{},lambda r:None,lambda n:None,process,None,(OSError,ValueError))
        class Names:
            name_snapshot={'revision':2,'value':'Before'}
            def validate_name(self,value):events.append(('validate',value))
            def rename(self,value):
                events.append(('commit',value))
                if fail:raise ValueError('conflict')
                self.name_snapshot={'revision':3,'value':value}
        bridge.profiles=Names()
        bridge.observe_state=lambda:{'dw_enabled':0}
        bridge.name_adapter={'state':0x20000000,'ready':0x20001000,'traps':{101:'request',102:'applied',103:'rolled_back'}}
        return bridge,events

    def test_success_requires_readback_then_commit_then_ack(self):
        bridge,events=self.bridge()
        with patch.object(player_name,'read_request',return_value='After'),patch.object(player_name,'stage_name',side_effect=lambda *a:events.append(('stage',))),patch.object(player_name,'verify_applied',side_effect=lambda *a,**k:events.append(('readback',))):
            bridge.handle_exception(SimpleNamespace(tid=17),0x80000003,101,{})
            bridge.handle_exception(SimpleNamespace(tid=17),0x80000003,102,{})
        self.assertLess(events.index(('stage',)),events.index(('readback',)))
        self.assertLess(events.index(('readback',)),events.index(('commit','After')))
        self.assertLess(events.index(('commit','After')),events.index(('write',0x20000004,b'\1\0\0\0')))
        self.assertIsNone(bridge.pending_name)

    def test_failed_commit_requests_rollback_and_preserves_snapshot(self):
        bridge,events=self.bridge(fail=True);bridge.pending_name='After'
        with patch.object(player_name,'verify_applied') as verify:
            row={};bridge.handle_exception(SimpleNamespace(tid=17),0x80000003,102,row)
            self.assertEqual(row['local_player_name_error'],'conflict')
            self.assertIn(('write',0x20000004,bytes(4)),events)
            self.assertEqual(bridge.profiles.name_snapshot,{'revision':2,'value':'Before'})
            bridge.handle_exception(SimpleNamespace(tid=17),0x80000003,103,{})
            self.assertTrue(verify.call_args.kwargs['rollback'])
        self.assertIsNone(bridge.pending_name)

    def test_wrong_thread_rejected_before_native_access(self):
        bridge,events=self.bridge()
        with self.assertRaises(ValueError):bridge.handle_exception(SimpleNamespace(tid=99),0x80000003,101,{})
        self.assertEqual(events,[])

class LifecycleTests(unittest.TestCase):
    def test_prepare_failure_records_result_without_starting(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(launch,'ROOT',Path(tmp)),patch.object(launch,'prepare',side_effect=ValueError('bad image')),patch.object(launch,'ProcessSession') as cls:
            process=cls.return_value;process.is_running.return_value=False
            result=launch.run(SimpleNamespace(name='failure'))
            self.assertEqual(result['error'],'bad image')
            process.start.assert_not_called();process.close.assert_called_once()
            self.assertTrue((Path(tmp)/'workspaces/offline-runs/failure/result.json').is_file())

    def test_prepare_only_never_starts_guard_or_debug_loop(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(launch,'ROOT',Path(tmp)),patch.object(launch,'prepare',return_value={}),patch.object(launch,'ProcessSession') as cls:
            result=launch.run(SimpleNamespace(name='prepared',prepare_only=True))
            self.assertTrue(result['prepared_only']);cls.return_value.start.assert_not_called()
            cls.return_value.close.assert_called_once()

    def test_closed_process_cannot_read_or_write(self):
        process=ProcessSession(None,None,None,{},lambda r:None,lambda n:None,None)
        process.closed=True
        with self.assertRaises(ValueError):process.read(0x400000,4)
        with self.assertRaises(ValueError):process.write(0x400000,b'1234')

    def test_periodic_due_and_forced_checkpoint(self):
        now=[0.0];task=PeriodicTask(2,clock=lambda:now[0])
        self.assertTrue(task.due());self.assertFalse(task.due())
        now[0]=1;self.assertTrue(task.due(force=True))
        now[0]=2;self.assertFalse(task.due())
        now[0]=3;self.assertTrue(task.due())
