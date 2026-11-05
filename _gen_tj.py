# -*- coding: utf-8 -*-
"""Generate 天津市 2027 省考数据 (job-data-tj.js)，schema 与江苏/上海统一。
字段同 _gen_sk.py：i/un/nm/it/lv/ct/cy/dt/n/rt/ed/mj/nt/pl/g/yr/fr/sp/hk/vh/vj/fa/ap/mn/mx
天津映射：
  i=代码 un=招考单位 nm=招考职位 it=职位简介
  lv=职位层级(市级/区级/街道/乡镇) ct=职位类别(综合管理/行政执法/专业技术)
  cy=天津市 dt=招考部门 n=招考人数 ed=学历(从学历学位拆) mj=专业 nt=其他资格条件
  pl=政治面貌 g=性别 yr=基层年限 fr=应届(招考对象) sp=特殊身份 hk=户籍
"""
import openpyxl, json, io, re

SRC = r'C:\Users\Huawei\Desktop\岗位报名\天津\天津市2027年度考试录用公务员职位表.xlsx'
OUT = r'C:\Users\Huawei\.openclaw\xxpuan-site\job-data-tj.js'

def cv(v):
    if v is None:
        return ''
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).strip()

def parse_edu(edu_deg):
    edu = edu_deg.split(';')[0].strip()
    m = {'研究生': '研究生', '博士研究生': '博士研究生', '硕士研究生': '硕士研究生',
         '大学本科以上': '本科及以上', '大学本科': '本科', '大学专科以上': '大专及以上', '大学专科': '大专'}
    return m.get(edu, edu)

def parse_obj(obj):
    fr = 0
    sp = ''
    if '2027届高校毕业生' in obj:
        fr = 2
    elif '应届高校毕业生' in obj:
        fr = 1
    if '退役' in obj:
        sp = '退役'
    elif '服务基层项目' in obj:
        sp = '基层'
    elif '社区工作者' in obj or '两委' in obj:
        sp = '村社'
    return fr, sp

def level_of(lv):
    if '市级' in lv:
        return '市级'
    if '区级' in lv:
        return '区级'
    if '街道' in lv:
        return '街道'
    if '乡镇' in lv:
        return '乡镇'
    return lv

def main():
    wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
    ws = wb['Sheet1']
    rows = list(ws.iter_rows(values_only=True))
    posts = []
    for r in rows[2:]:
        code = cv(r[0])
        if not code:
            continue
        unit = cv(r[1])          # 招考单位
        dept = cv(r[2])          # 招考部门
        nm = cv(r[3])            # 招考职位
        intro = cv(r[4])
        n = cv(r[5])
        ed = parse_edu(cv(r[6])) # 学历
        mj = cv(r[7])            # 专业
        obj = cv(r[8])           # 招考对象
        pl_raw = cv(r[9])        # 政治面貌
        g_raw = cv(r[11])        # 性别
        work = cv(r[12])         # 工作经历
        cert = cv(r[14])         # 资格证书
        hk_raw = cv(r[15])       # 户别要求
        other = cv(r[16])        # 其他资格条件
        ct = cv(r[20]).replace('类', '')  # 职位类别
        lv = level_of(cv(r[21])) # 职位层级

        fr, sp = parse_obj(obj)
        pl = '党员' if '中共党员' in pl_raw else ''
        g = 'm' if '适合男性' in g_raw else ('f' if '适合女性' in g_raw else '')
        yr = 2 if '2年以上' in work else 0
        fa = 1 if '法律职业资格' in cert else 0
        hk = 1 if '户籍' in hk_raw else 0
        try:
            n = int(n) if n else 1
        except ValueError:
            n = 1

        posts.append({
            'i': code, 'a': '', 'u': '', 'p': code,
            'un': unit, 'nm': nm, 'it': intro,
            'lv': lv, 'ct': ct, 'cy': '天津市', 'dt': dept,
            'n': n, 'rt': '', 'ed': ed, 'mj': mj, 'nt': other,
            'pl': pl, 'g': g, 'yr': yr, 'fr': fr, 'sp': sp, 'hk': hk,
            'vh': 0, 'vj': 0, 'fa': fa,
            'ap': '', 'mn': '', 'mx': '',
        })

    payload = {
        'meta': {'year': 2027, 'exam': '天津市考', 'published': True,
                 'note': '2027年度天津市考录职位，共 %d 个职位。' % len(posts),
                 'source': '天津市2027年度考试录用公务员职位表'},
        'catalog': [],
        'posts': posts,
    }
    header = '/* 2027 天津市考岗位数据（自动生成，勿手改）字段见 _gen_tj.py */\n'
    js = header + 'window.TJ_DATA=' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ';\n'
    with io.open(OUT, 'w', encoding='utf-8') as f:
        f.write(js)

    print('total posts:', len(posts))
    print('bytes:', round(len(js.encode('utf-8')) / 1024 / 1024, 2), 'MB')
    from collections import Counter
    print('层级 lv:', dict(Counter(p['lv'] for p in posts)))
    print('类别 ct:', dict(Counter(p['ct'] for p in posts)))
    print('应届 fr:', dict(Counter(p['fr'] for p in posts)))
    print('特殊身份 sp:', dict(Counter(p['sp'] for p in posts)))
    print('学历 ed:', dict(Counter(p['ed'] for p in posts)))
    print('政治面貌 pl:', dict(Counter(p['pl'] for p in posts)))
    print('性别 g:', dict(Counter(p['g'] for p in posts)))
    print('户籍 hk:', dict(Counter(p['hk'] for p in posts)))
    print('法考 fa:', dict(Counter(p['fa'] for p in posts)))

if __name__ == '__main__':
    main()
