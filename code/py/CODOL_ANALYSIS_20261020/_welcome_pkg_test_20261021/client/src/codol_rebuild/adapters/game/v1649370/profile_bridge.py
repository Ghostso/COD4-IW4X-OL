"""本地档案原生桥：一致采样、库存边界与应用服务连接。"""
import time
from codol_rebuild.adapters.game.v1649370.profile import PUBLIC, SECURE, CAPACITY, STRIDE, view_state
from codol_rebuild.runtime.contracts import PeriodicTrigger

class LocalProfileBridge:
    """原生采样状态与应用服务显式分离。"""
    def __init__(self, process, factory, log, record):
        self.process=process; self.factory=factory; self.log=log; self.record=record
        self.service=None; self.schemas=None; self.ready=False; self.inventory=None
        self.catalog={}
        self.task=process.periodic(2); self.last_view=None
    @property
    def account(self):
        return self.service.account if self.service else None
    @property
    def name_snapshot(self):
        return self.service.name_snapshot if self.service else None
    def initialize(self, schemas, tables, catalog):
        self.schemas=schemas
        self.catalog={item['id']: item for item in catalog}
        self.service=self.factory(schemas,tables,catalog)
        return self.service.initialize()
    def validate_name(self, value):
        return self.service.validate_name(value)

    def rename(self, value):
        from codol_rebuild.adapters.game.v1649370.player_name import consume_card, NAME_CARD
        self.save(force=True)
        return consume_card(self.process.read, self.process.write, self.inventory,
                            lambda: self.service.rename(value, NAME_CARD))

    def commit_balances(self, balances):
        """为同步余额操作保存当前档案；未就绪、旧格式或采样失败均拒绝成功。"""
        if not self.ready or not self.account or self.account.get('initialization') is None:
            raise ValueError('本地余额档案尚未就绪')
        self.save(force=True)
        state = self.account['initialization']
        if any(state[key] != balances[key] for key in ('gp', 'cp')):
            raise ValueError('本地余额未完成保存')

    def purchase(self, offer, quantity=1):
        """通过应用服务规划交易，版本适配暂存原生库存，单事务持久化。"""
        from codol_rebuild.adapters.game.v1649370.purchase import publish_transaction
        if not self.ready or not self.account:
            raise ValueError('本地档案尚未就绪')
        self.save(force=True)
        blobs = {kind: self.process.read(base + 0x90, 0x7FFC)
                 for kind, base in [('public', PUBLIC), ('secure', SECURE)]}
        if blobs != self.account['profiles']:
            raise ValueError('档案快照尚未同步，请重试')
        next_state = self.service.purchase_state(offer, quantity)
        return publish_transaction(
            self.process.read, self.process.write, self.inventory,
            [self.catalog[row['item_id']] for row in offer.get('contents', [{'item_id': offer['item_id']}])], next_state,
            lambda: self.service.commit_purchase(blobs, offer, quantity))

    def save(self, force=False):
        if not self.account or not self.ready: return
        if not self.task.due(force=force): return
        mem=self.process.read
        current_view=view_state(mem)
        if current_view!=self.last_view:
            self.last_view=current_view
            self.log['local_view_state']=current_view
            self.record({'local_view_state':current_view})
        blobs={k:mem(base+0x90,0x7FFC) for k,base in [('public',PUBLIC),('secure',SECURE)]}
        if any(mem(base+0x90,0x7FFC)!=blobs[k] for k,base in [('public',PUBLIC),('secure',SECURE)]): return
        character=self.service.inspect_snapshot(blobs)
        pool=int(self.inventory['pool'],16)
        if mem(pool-16,16)!=b'LOCAL-INVENTORY!' or mem(pool+CAPACITY*STRIDE,16)!=b'LOCAL-INVENTORY!':
            raise ValueError('Inventory boundary changed')
        balances = None
        if self.account.get('initialization') is not None:
            from codol_rebuild.adapters.game.v1649370.profile import currency_snapshot
            balances = currency_snapshot(mem)
            if currency_snapshot(mem) != balances:
                return
        if self.service.save(blobs, balances=balances):
            row={'revision':self.account['revision'],'character':character,'time':time.time()}
            self.log['local_profile_saved']=row
            self.record({'local_profile_saved':row})
