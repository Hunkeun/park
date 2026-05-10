# -*- coding: utf-8 -*-
# PATCHED:utf8-stdout-v1
"""s3_panorama.json 골격 균형 1회성 점검."""
import json, sys, os, re
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.abspath(__file__))

panorama = json.load(open(os.path.join(ROOT, 's3_panorama.json'), encoding='utf-8'))
isbn120  = json.load(open(os.path.join(ROOT, 'isbn_list_120books.json'), encoding='utf-8'))
isbnomn  = json.load(open(os.path.join(ROOT, 'isbn_list_120omnibus.json'), encoding='utf-8'))
batch120 = json.load(open(os.path.join(ROOT, 'batch_books_120.json'), encoding='utf-8'))

groups = panorama['groups']

# 1. 골격 균형
print('='*70); print('1. 골격 균형'); print('='*70)
print(f'  그룹 수: {len(groups)} (기대 12)  → {"OK" if len(groups)==12 else "FAIL"}')
for i, g in enumerate(groups, 1):
    bc = g.get('base_cells', [])
    sc = g.get('synthesis_cell', {})
    ic = g.get('group_internal_consistency_check', {})
    code = g['group']['code']
    flag = 'OK' if len(bc)==10 and sc and ic else '!!'
    print(f'  G{i:02d} {code}: base_cells={len(bc):2d}, synthesis={"O" if sc else "X"}, consistency={"O" if ic else "X"} [{flag}]')

# 2. 필수 필드
print(); print('='*70); print('2. 필수 필드 누락'); print('='*70)
REQ_BASE = ['tonggwon','seq','title','hint','isbn','scope','depth','narrative_position','representative_verse','representative_metaphor','non_overlap_with']
REQ_SYN  = ['isbn','title','subtitle','depends_on','synthesis_axis','culmination_message','representative_verse','representative_metaphor','non_overlap_with']
miss_base = []
for g in groups:
    for b in g['base_cells']:
        for k in REQ_BASE:
            v = b.get(k)
            if v is None or v == '' or v == [] or v == {}:
                miss_base.append(f"{g['group']['code']} seq{b.get('seq','?')}: {k}")
miss_syn = []
for g in groups:
    s = g['synthesis_cell']
    for k in REQ_SYN:
        v = s.get(k)
        if v is None or v == '' or v == [] or v == {}:
            miss_syn.append(f"{g['group']['code']} synthesis: {k}")
print(f'  base_cells 누락: {len(miss_base)}건')
for x in miss_base[:8]: print(f'    {x}')
print(f'  synthesis 누락: {len(miss_syn)}건')
for x in miss_syn[:8]: print(f'    {x}')

# 3. 유일성
print(); print('='*70); print('3. 유일성 검증 (132셀)'); print('='*70)
all_cells = []
for g in groups:
    code = g['group']['code']
    for b in g['base_cells']:
        all_cells.append((code, f"seq{b['seq']}", b))
    all_cells.append((code, 'synthesis', g['synthesis_cell']))
print(f'  총 셀: {len(all_cells)} (기대 132)')
for field in ['representative_verse','representative_metaphor','title','isbn']:
    cnt = Counter()
    for code, lab, c in all_cells:
        v = c.get(field, '')
        if isinstance(v, str): v = v.strip()
        cnt[v] += 1
    dups = [(v, n) for v, n in cnt.items() if n > 1 and v]
    print(f'  {field}: {len(cnt)} 종류 / 중복 {len(dups)}건')
    for v, n in dups[:5]:
        wheres = [f"{c}/{l}" for c, l, b in all_cells if (b.get(field,'') or '').strip() == v]
        v_show = v[:60] + ('...' if len(v) > 60 else '')
        print(f'    "{v_show}" x{n} → {", ".join(wheres)}')

# 4. depth 패턴
print(); print('='*70); print('4. depth 패턴 (1=도입, 2-4=심화-1, 5-7=심화-2, 8-10=통합)'); print('='*70)
expected = {1:'도입', 2:'심화-1',3:'심화-1',4:'심화-1', 5:'심화-2',6:'심화-2',7:'심화-2', 8:'통합',9:'통합',10:'통합'}
fails = []
for g in groups:
    code = g['group']['code']
    for b in g['base_cells']:
        seq = b['seq']
        depth = b.get('depth','')
        exp = expected.get(seq,'')
        if depth != exp:
            fails.append(f"{code} seq{seq}: depth=\"{depth}\" (기대 \"{exp}\")")
print(f'  패턴 어긋남: {len(fails)}/120권')
for x in fails[:10]: print(f'    {x}')

# 5. synthesis depends_on
print(); print('='*70); print('5. 종합권 depends_on'); print('='*70)
fail = 0
for g in groups:
    code = g['group']['code']
    deps = sorted(g['synthesis_cell'].get('depends_on', []))
    if deps != list(range(1, 11)):
        fail += 1
        print(f"    {code}: depends_on={deps}")
if fail == 0:
    print('  12 종합권 모두 1~10 의존 OK')

# 6. ISBN 외부 일치
print(); print('='*70); print('6. ISBN 외부 자료 일치'); print('='*70)
mis_base = []
for g in groups:
    for b in g['base_cells']:
        gn = g['group']['number']
        seq = b['seq']
        serial = (gn - 1) * 10 + seq
        ext = isbn120.get(f'120-{serial}', '')
        pan = (b.get('isbn','') or '').replace('-','')
        if pan != ext:
            mis_base.append(f"G{gn:02d} seq{seq}: panorama={pan} vs list={ext}")
print(f'  본권 ISBN 불일치: {len(mis_base)}건')
for x in mis_base[:5]: print(f'    {x}')
mis_syn = []
for g in groups:
    code = g['group']['code']
    pan = (g['synthesis_cell'].get('isbn','') or '').replace('-','')
    ext = (isbnomn.get(f'120-omnibus-{code}','') or '').replace('-','')
    if pan != ext:
        mis_syn.append(f"{code}: panorama={pan} vs list={ext}")
print(f'  종합권 ISBN 불일치: {len(mis_syn)}건')
for x in mis_syn[:5]: print(f'    {x}')

# 7. title 일치 (panorama vs batch_books_120)
print(); print('='*70); print('7. title 일치 (panorama vs batch_books_120)'); print('='*70)
batch_groups = batch120['groups'] if isinstance(batch120, dict) else batch120
mis_title = []
for g_pan, g_bat in zip(groups, batch_groups):
    code = g_pan['group']['code']
    bat_books = {b['seq']: b['title'] for b in g_bat['books']}
    for b in g_pan['base_cells']:
        bat = bat_books.get(b['seq'])
        if b.get('title') != bat:
            mis_title.append(f'{code} seq{b["seq"]}: panorama="{b.get("title")}" vs batch="{bat}"')
print(f'  본권 title 불일치: {len(mis_title)}건')
for x in mis_title[:8]: print(f'    {x}')

# 8. scope 양도 일관성
print(); print('='*70); print('8. scope 양도 일관성'); print('='*70)
loose = 0
for g in groups:
    code = g['group']['code']
    cells = g['base_cells']
    all_inc = ' \n '.join(t for c in cells for t in (c.get('scope',{}).get('include') or []))
    for c in cells:
        for ex in (c.get('scope',{}).get('exclude') or []):
            if re.search(r'seq\s*\d+', ex):
                continue
            tokens = re.findall(r'[가-힣]{2,}', ex)
            hit = any(tok in all_inc for tok in tokens[:3])
            if not hit:
                loose += 1
                if loose <= 3:
                    ex_show = ex[:60] + ('...' if len(ex) > 60 else '')
                    print(f'    {code} seq{c["seq"]} exclude: "{ex_show}" → 같은 그룹 어디에도 명시적 매핑 안 보임')
print(f'  exclude 미매핑(휴리스틱): {loose}건')

# 9. non_overlap_with
print(); print('='*70); print('9. non_overlap_with 채워짐'); print('='*70)
empty = []
for code, lab, c in all_cells:
    nov = c.get('non_overlap_with')
    if not nov:
        empty.append(f"{code}/{lab}")
print(f'  non_overlap_with 비어 있는 셀: {len(empty)}/132')
for x in empty[:10]: print(f'    {x}')

# 10. bridges_to_next_group
print(); print('='*70); print('10. 종합권 bridges_to_next_group (G12 제외 11개 있어야)'); print('='*70)
miss_bridge = []
for i, g in enumerate(groups):
    code = g['group']['code']
    bridge = g['synthesis_cell'].get('bridges_to_next_group')
    if i < 11 and not bridge:
        miss_bridge.append(code)
print(f'  bridge 누락 (G01~G11): {len(miss_bridge)}건 → {miss_bridge}')

print(); print('='*70); print('점검 끝'); print('='*70)
