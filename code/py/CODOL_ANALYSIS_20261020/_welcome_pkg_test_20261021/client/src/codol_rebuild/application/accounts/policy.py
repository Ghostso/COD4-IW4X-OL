"""本地账号初始化策略：最高进度、初始角色与配装选择。"""
def initialization_policy(data):
    """输入为格式适配已解析的游戏数据；原生数值编码仍由格式层负责。"""
    return {'progression': dict(data['progression']), 'character': 545,
            'loadouts': [dict(data['starting_loadouts'][slot % 3], name=f'Loadout {slot+1}')
                         for slot in range(5)] if data['starting_loadouts'] else [],
            'fill_unlock_flags': True, 'unlock_threshold': 32767}


def new_account_policy(data):
    """新档按适配层排除清单授予物品（排位赛荣誉渠道优先）；预算仅创建时发放。"""
    items = data['items']
    if any(type(row.get('gp_cp_sale')) is not bool for row in items):
        raise ValueError('Missing native marketplace classification')
    owned = {row['id'] for row in items if row['id'] not in (0, 15400, 20000) and not row['gp_cp_sale']}
    by_id = {row['id']: row for row in items}
    policy = initialization_policy(data)
    characters = sorted(row['id'] for row in items if row['id'] in owned and row['kind'] == 2)
    if not characters:
        raise ValueError('No non-market initial character available')
    if policy['character'] not in owned:
        policy['character'] = characters[0]
    for loadout in policy['loadouts']:
        for key in ('primaryBase', 'secondaryBase'):
            original = loadout[key]
            if original and original not in owned:
                source = by_id[original]
                candidates = sorted(row['id'] for row in items if row['id'] in owned
                                    and row['kind'] == source['kind'] and row['group'] == source['group'])
                loadout[key] = candidates[0] if candidates else 0
                attach = 'primaryAttach' if key == 'primaryBase' else 'secondaryAttach'
                for index in range(2):
                    loadout[f'{attach}.{index}'] = 0
        for key in loadout:
            if key.startswith(('primaryAttach.', 'secondaryAttach.', 'perks.', 'wildcards.')) or key in ('lethal', 'tactical'):
                if loadout[key] not in owned:
                    loadout[key] = 0
        if not loadout['lethal']:
            loadout['lethalDoubleAmmo'] = False
        if not loadout['tactical']:
            loadout['tacticalDoubleAmmo'] = False
    policy['initialization'] = {'version': 1, 'owned_ids': sorted(owned), 'gp': 2000000000, 'cp': 100000}
    return policy


def validate_initialization(state):
    """校验持久化授权状态，拒绝损坏数据而非恢复成全解锁。"""
    if not isinstance(state, dict) or state.get('version') != 1:
        raise ValueError('Unsupported account initialization version')
    ids = state.get('owned_ids')
    if not isinstance(ids, list) or not ids or any(type(v) is not int or not 0 < v < 65535 for v in ids):
        raise ValueError('Invalid account entitlement IDs')
    if len(ids) != len(set(ids)) or any(v in ids for v in (15400, 20000)):
        raise ValueError('Invalid duplicate or reserved account entitlement')
    for key in ('gp', 'cp'):
        if type(state.get(key)) is not int or not 0 <= state[key] <= 2147483647:
            raise ValueError('Invalid account currency balance')
    quantities = state.get('quantities', {})
    quantity_ids = {str(item) for item in ids}
    if not isinstance(quantities, dict) or any(
            key not in quantity_ids or type(value) is not int
            or not 1 <= value <= 2147483647 for key, value in quantities.items()):
        raise ValueError('Invalid account item quantities')
    return state
