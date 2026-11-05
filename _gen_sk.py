# -*- coding: utf-8 -*-
"""Generate 2027 江苏省考 数据 (job-data-sk.js)
字段：i=编号(地区代码+单位代码+职位代码) a=地区代码 u=单位代码 p=职位代码
      un=单位名称 nm=职位名称 it=职位简介
      lv=隶属关系(省/市/县/乡镇/垂直) ct=考试类别(A/B/C) cy=城市 dt=地区名称
      n=招考人数 rt=开考比例 ed=学历 mj=专业 nt=其它(备注)
      pl=政治面貌('党员'/'团员'/'') g=性别('m'/'f'/'') yr=基层年限 fr=应届(0/1/2)
      vt=退役军人 vc=村社区书记 hk=户籍 vh=裸眼视力 vj=矫正视力 fa=法考A证
专业目录：catalog=[{c:大类, m:[专业...]}]
"""
import openpyxl, json, io, re

SRC = r'C:\Users\Huawei\Desktop\【江苏华图】2027江苏省考职位表汇总含专业目录.xlsx'
OUT = r'C:\Users\Huawei\.openclaw\xxpuan-site\job-data-sk.js'
SRC26 = r'C:\Users\Huawei\Desktop\【江苏华图】2026江苏省考职位表&报名数据&进面分汇总.xlsx'

CITY = {'00':'江苏省','01':'南京市','02':'无锡市','03':'徐州市','04':'常州市','05':'苏州市',
        '06':'南通市','07':'连云港市','08':'淮安市','09':'盐城市','10':'扬州市','11':'镇江市',
        '12':'泰州市','13':'宿迁市'}

def cv(v):
    if v is None:
        return ''
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).strip()

def split_majors(s):
    return [x for x in re.split(r'[，,、；;\s]+', s) if x]

def flags(note):
    pl = '党员' if '中共党员' in note else ('团员' if '共青团员' in note else '')
    g = 'm' if '男性' in note else ('f' if '女性' in note else '')
    yr = 2 if '两年以上' in note else 0
    if re.search(r'2027年|2027届', note):
        fr = 2
    elif '应届' in note:
        fr = 1
    else:
        fr = 0
    vt = 1 if ('退役军人' in note or '退役士兵' in note) else 0
    vc = 1 if '村（社区）' in note else 0
    hk = 1 if '户籍' in note else 0
    m = re.search(r'裸眼视力低于([\d.]+)不合格', note); vh = float(m.group(1)) if m else 0
    m = re.search(r'矫正视力低于([\d.]+)不合格', note); vj = float(m.group(1)) if m else 0
    fa = 1 if '法律职业资格' in note else 0
    return pl, g, yr, fr, vt, vc, hk, vh, vj, fa

def norm_pos(s):
    return re.sub(r'[\s\u3000]+', '', s)

def load_2026():
    """返回 {单位代码(前9位): [{pos, apply, min, max}, ...]}"""
    from collections import defaultdict
    wb26 = openpyxl.load_workbook(SRC26, read_only=True, data_only=True)
    ws26 = wb26['总表']
    idx = defaultdict(list)
    for row in ws26.iter_rows(values_only=True):
        code = cv(row[0])
        if not code or len(code) < 11:
            continue
        idx[code[:9]].append({'pos': cv(row[4]), 'apply': cv(row[10]), 'min': cv(row[12]), 'max': cv(row[13])})
    return idx

def main():
    wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)

    # 专业目录
    catalog = []
    ws2 = wb['专业目录']
    for row in ws2.iter_rows(values_only=True):
        if row[0] is None or row[0] == '序号':
            continue
        cat = cv(row[1])
        majors = []
        for i in (2, 3, 4):
            if row[i]:
                majors += split_majors(cv(row[i]))
        catalog.append({'c': cat, 'm': majors})
    # 修正源文件截断的大类名（华图把"仪表仪器及测试技术类"截成了"仪表仪器及"）
    for c in catalog:
        if c['c'] == '仪表仪器及':
            c['c'] = '仪表仪器及测试技术类'

    # 汇总 sheet：表头在第1行，数据从第2行起
    ws = wb['汇总']
    rows = list(ws.iter_rows(values_only=True))
    posts = []
    for r in rows[2:]:
        area_code = cv(r[1])
        if not area_code:
            continue
        unit_code = cv(r[3])
        post_code = cv(r[5])
        unit = cv(r[4])
        name = cv(r[6])
        if not unit and not name:
            continue
        note = cv(r[13])
        pl, g, yr, fr, vt, vc, hk, vh, vj, fa = flags(note)
        city = CITY.get(area_code[:2], '')
        district = cv(r[2]) or city
        try:
            n = int(cv(r[10])) if cv(r[10]) else 1
        except ValueError:
            n = 1
        pid = area_code + unit_code + post_code
        posts.append({
            'i': pid, 'a': area_code, 'u': unit_code, 'p': post_code,
            'un': unit, 'nm': name, 'it': cv(r[7]),
            'lv': cv(r[0]), 'ct': cv(r[8]), 'cy': city, 'dt': district,
            'n': n, 'rt': cv(r[9]), 'ed': cv(r[11]), 'mj': cv(r[12]), 'nt': note,
            'pl': pl, 'g': g, 'yr': yr, 'fr': fr, 'vt': vt, 'vc': vc, 'hk': hk,
            'vh': vh, 'vj': vj, 'fa': fa,
        })

    # 接入 2026 报名人数/进面最低分/进面最高分（单位代码 + 职位名精确匹配）
    idx26 = load_2026()
    matched26 = 0
    for p in posts:
        ap = mn = mx = ''
        for v in idx26.get(p['i'][:9], []):
            if norm_pos(v['pos']) == norm_pos(p['nm']):
                ap, mn, mx = v['apply'], v['min'], v['max']
                matched26 += 1
                break
        p['ap'] = ap
        p['mn'] = mn
        p['mx'] = mx

    payload = {
        'meta': {
            'year': 2027, 'exam': '江苏省考', 'published': True,
            'note': '2027年度江苏省考录职位表，共 %d 个职位。' % len(posts),
            'source': '江苏华图 2027 江苏省考职位表汇总',
        },
        'catalog': catalog,
        'posts': posts,
    }
    header = '/* 2027 江苏省考岗位数据（自动生成，勿手改）字段见 _gen_sk.py */\n'
    js = header + 'window.SK_DATA=' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ';\n'
    with io.open(OUT, 'w', encoding='utf-8') as f:
        f.write(js)

    print('total posts:', len(posts))
    print('bytes:', round(len(js.encode('utf-8'))/1024/1024, 2), 'MB')
    print('catalog 大类:', len(catalog))

    # 分布验证
    from collections import Counter
    print('隶属:', dict(Counter(p['lv'] for p in posts)))
    print('考试类别:', dict(Counter(p['ct'] for p in posts)))
    print('学历:', dict(Counter(p['ed'] for p in posts)))
    print('应届 fr:', dict(Counter(p['fr'] for p in posts)))
    print('性别 g:', dict(Counter(p['g'] for p in posts)))
    print('政治面貌 pl:', dict(Counter(p['pl'] for p in posts)))
    print('退役军人:', sum(1 for p in posts if p['vt']), '村社区:', sum(1 for p in posts if p['vc']), '户籍:', sum(1 for p in posts if p['hk']), '法考A:', sum(1 for p in posts if p['fa']))
    print('裸眼视力:', sum(1 for p in posts if p['vh']>0), '矫正视力:', sum(1 for p in posts if p['vj']>0))
    print('2026报名数据匹配:', matched26, '/', len(posts))

if __name__ == '__main__':
    main()
