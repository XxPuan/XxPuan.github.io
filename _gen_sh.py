# -*- coding: utf-8 -*-
"""Generate 上海市 2027 省考数据 (job-data-sh.js)，schema 与江苏统一。
字段同 _gen_sk.py：i/un/nm/it/lv/ct/cy/dt/n/rt/ed/mj/nt/pl/g/yr/fr/sp/hk/vh/vj/fa/ap/mn/mx
上海映射：
  un=招录机关·用人单位  lv=市级/区级  ct=综合管理/行政执法/执法勤务/警务技术
  cy=上海市  dt=区  mn/mx=2026 最低分/最高分（无报名人数 ap）
"""
import xlrd, openpyxl, json, io, re
from collections import defaultdict

SRC = r'C:\Users\Huawei\Downloads\上海市2027年度考试录用公务员招考简章.xls'
SRC26 = r'C:\Users\Huawei\Desktop\上海市2026年度公务员招考简章含最高最低线.xlsx'
OUT = r'C:\Users\Huawei\.openclaw\xxpuan-site\job-data-sh.js'

def cv(v):
    if v is None:
        return ''
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).strip()

def norm(s):
    return re.sub(r'[\s\u3000]+', '', s)

def parse_cat_name(nm):
    """职位名称 '综合管理类/二级主任科员及以下' -> (类别, 职位名)"""
    if '/' in nm:
        return nm.split('/', 1)[0], nm.split('/', 1)[1]
    return '', nm

def level_of(org):
    return '区级' if '区' in org else '市级'

def politics(pl_raw):
    if '群众' in pl_raw or pl_raw == '不限' or not pl_raw:
        return ''
    if '共青' in pl_raw:
        return '党员团员'
    return '党员'

def flags(note):
    """从 其他条件+备注 提取 性别/视力/户籍/法考/应届"""
    g = 'm' if '限男性' in note else ('f' if '限女性' in note else '')
    m = re.search(r'裸眼视力低于([\d.]+)不合格', note); vh = float(m.group(1)) if m else 0
    m = re.search(r'矫正视力低于([\d.]+)不合格', note); vj = float(m.group(1)) if m else 0
    fa = 1 if '法律职业资格' in note else 0
    hk = 0 if '户籍不限' in note else (1 if '户籍' in note else 0)
    fr = 2 if ('应届' in note and ('2027' in note or '2026' in note)) else (1 if '应届' in note else 0)
    return g, vh, vj, fa, hk, fr

def special_of(obj, sheet):
    o = obj
    if '退役' in o or '退役' in sheet:
        return '退役'
    if '三支一扶' in o or '村官' in o or '特岗' in o or '西部' in o or '服务基层' in sheet:
        return '基层'
    if '残疾' in sheet or '残疾' in o:
        return '残疾'
    return ''

def main():
    wb = xlrd.open_workbook(SRC)
    posts = []
    for sn in wb.sheet_names():
        sh = wb.sheet_by_name(sn)
        ncols = sh.ncols
        # 找表头
        hdr = None
        for r in range(min(6, sh.nrows)):
            txt = ''.join(str(sh.cell_value(r, c)) for c in range(ncols))
            if '职位代码' in txt:
                hdr = r
                break
        if hdr is None:
            continue
        for r in range(hdr + 1, sh.nrows):
            seq = cv(sh.cell_value(r, 0))
            if not seq:
                continue
            org = cv(sh.cell_value(r, 1))       # 招录机关
            dep = cv(sh.cell_value(r, 2))       # 用人单位
            nm = cv(sh.cell_value(r, 3))        # 职位名称
            code = cv(sh.cell_value(r, 4))      # 职位代码
            intro = cv(sh.cell_value(r, 5))
            n = cv(sh.cell_value(r, 6))
            obj = cv(sh.cell_value(r, 7))       # 招考对象
            years = cv(sh.cell_value(r, 8))     # 基层工作经历
            major_b = cv(sh.cell_value(r, 9))   # 本科专业
            major_g = cv(sh.cell_value(r, 10))  # 研究生专业
            # 17列有专业类别(11)，16列没有
            if ncols == 17:
                edu = cv(sh.cell_value(r, 12))
                pl_raw = cv(sh.cell_value(r, 14))
                other = cv(sh.cell_value(r, 15))
                note = cv(sh.cell_value(r, 16))
            else:
                edu = cv(sh.cell_value(r, 11))
                pl_raw = cv(sh.cell_value(r, 13))
                other = cv(sh.cell_value(r, 14))
                note = cv(sh.cell_value(r, 15))

            cat, nm2 = parse_cat_name(nm)
            if not nm2:
                nm2 = nm
            # 类别去"类"后缀并统一
            cat = cat.replace('类', '')
            un = org + ('·' + dep if dep and dep != org and dep != '内设处室' and dep != '市局业务部门' else '')
            major = '；'.join([x for x in [major_b, major_g] if x and x != '不限'])
            if not major:
                major = '不限'
            nt = ('；'.join([x for x in [other, note] if x])).strip()
            g, vh, vj, fa, hk, fr = flags(other + note)
            yr = 2 if '2年' in years or '两年' in years else 0
            try:
                n = int(n) if n else 1
            except ValueError:
                n = 1
            posts.append({
                'i': code, 'a': '', 'u': '', 'p': code,
                'un': un, 'nm': nm2, 'it': intro,
                'lv': level_of(org), 'ct': cat, 'cy': '上海市', 'dt': org,
                'n': n, 'rt': '3', 'ed': edu, 'mj': major, 'nt': nt,
                'pl': politics(pl_raw), 'g': g, 'yr': yr, 'fr': fr,
                'sp': special_of(obj, sn), 'hk': hk, 'vh': vh, 'vj': vj, 'fa': fa,
                'ap': '', 'mn': '', 'mx': '', 'org': org, 'dep': dep,
            })

    # 上海 2026 最高分/最低分 接入（招录机关/用人单位 + 职位名 匹配，职位名去类别前缀）
    wb26 = openpyxl.load_workbook(SRC26, read_only=True, data_only=True)
    idx26 = defaultdict(list)
    for sheet in wb26.sheetnames:
        ws26 = wb26[sheet]
        rows26 = list(ws26.iter_rows(values_only=True))
        hi = None
        for ri in range(min(3, len(rows26))):
            if any('职位代码' in str(c) for c in rows26[ri] if c):
                hi = ri
                break
        if hi is None:
            continue
        for row in rows26[hi + 1:]:
            org26 = cv(row[2]) if len(row) > 2 else ''
            dep26 = cv(row[3]) if len(row) > 3 else ''
            nm26 = cv(row[4]) if len(row) > 4 else ''
            mx = cv(row[6]) if len(row) > 6 else ''
            mn = cv(row[7]) if len(row) > 7 else ''
            _, nm26s = parse_cat_name(nm26)
            if not nm26s:
                nm26s = nm26
            if org26 and nm26s:
                idx26[norm(org26) + '|' + norm(nm26s)].append((mn, mx))
            if dep26 and nm26s:
                idx26[norm(dep26) + '|' + norm(nm26s)].append((mn, mx))

    matched = 0
    for p in posts:
        for k in (norm(p['org']) + '|' + norm(p['nm']), norm(p['dep']) + '|' + norm(p['nm'])):
            if k in idx26:
                p['mn'], p['mx'] = idx26[k][0]
                matched += 1
                break
        p.pop('org', None)
        p.pop('dep', None)

    payload = {
        'meta': {'year': 2027, 'exam': '上海市考', 'published': True,
                 'note': '2027年度上海市考录职位，共 %d 个职位。' % len(posts),
                 'source': '上海市2027年度考试录用公务员招考简章'},
        'catalog': [],
        'posts': posts,
    }
    header = '/* 2027 上海市考岗位数据（自动生成，勿手改）字段见 _gen_sh.py */\n'
    js = header + 'window.SH_DATA=' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ';\n'
    with io.open(OUT, 'w', encoding='utf-8') as f:
        f.write(js)

    print('total posts:', len(posts))
    print('bytes:', round(len(js.encode('utf-8')) / 1024 / 1024, 2), 'MB')
    print('2026分数线匹配:', matched, '/', len(posts))
    from collections import Counter
    print('层级 lv:', dict(Counter(p['lv'] for p in posts)))
    print('类别 ct:', dict(Counter(p['ct'] for p in posts)))
    print('政治面貌 pl:', dict(Counter(p['pl'] for p in posts)))
    print('特殊身份 sp:', dict(Counter(p['sp'] for p in posts)))
    print('学历 ed:', dict(Counter(p['ed'] for p in posts)))
    print('性别 g:', dict(Counter(p['g'] for p in posts)))
    print('户籍 hk:', dict(Counter(p['hk'] for p in posts)))

if __name__ == '__main__':
    main()
