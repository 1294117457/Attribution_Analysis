"""检查 BO 与 Entity 字段差异"""
import os
import ast

mappings = [
    ('contexts/market/domain/base_adj_factor/bo.py', 'BaseAdjFactor'),
    ('contexts/market/domain/base_dividend/bo.py', 'BaseDividend'),
    ('contexts/market/domain/base_name_change/bo.py', 'BaseNameChange'),
    ('contexts/market/domain/base_suspend/bo.py', 'BaseSuspend'),
    ('contexts/market/domain/cap_block_trade/bo.py', 'CapBlockTrade'),
    ('contexts/market/domain/cap_holder_num/bo.py', 'CapHolderNum'),
    ('contexts/market/domain/cap_margin_detail/bo.py', 'CapMarginDetail'),
    ('contexts/market/domain/cap_moneyflow/bo.py', 'CapMoneyflow'),
    ('contexts/market/domain/cap_top_inst/bo.py', 'CapTopInst'),
    ('contexts/market/domain/cap_top_list/bo.py', 'CapTopList'),
    ('contexts/market/domain/fin_daily_basic/bo.py', 'FinDailyBasic'),
    ('contexts/market/domain/fin_report/bo.py', 'FinReport'),
    ('contexts/market/domain/fin_top10_float/bo.py', 'FinTop10Float'),
    ('contexts/market/domain/fin_top10_holders/bo.py', 'FinTop10Holders'),
]


def get_class_fields(path):
    with open(path, 'r', encoding='utf-8') as fp:
        tree = ast.parse(fp.read(), path)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            fields = []
            for n in node.body:
                if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
                    fields.append(n.target.id)
                elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Attribute):
                    fields.append(n.target.attr)
            return fields, node.name
    return [], None


def find_entity_path(name):
    for root, dirs, files in os.walk('contexts/market/domain'):
        for f in files:
            if f == 'entity.py':
                fields, cls = get_class_fields(os.path.join(root, f))
                if cls == name:
                    return os.path.join(root, f), fields
    return None, None


print(f'{"Entity":<20} {"BO 字段数":<10} {"Entity字段数":<12} {"差异"}')
print('-' * 80)
for bo_path, entity_name in mappings:
    bo_fields, _ = get_class_fields(bo_path)
    ent_path, ent_fields = find_entity_path(entity_name)
    if ent_path is None:
        print(f'{entity_name:<20} 实体找不到')
        continue
    bo_only = set(bo_fields) - set(ent_fields)
    ent_only = set(ent_fields) - set(bo_fields)
    if bo_only or ent_only:
        diff = f'BO独有={bo_only}; Ent独有={ent_only}'
    else:
        diff = 'OK'
    print(f'{entity_name:<20} {len(bo_fields):<10} {len(ent_fields):<12} {diff}')
