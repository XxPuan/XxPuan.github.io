# -*- coding: utf-8 -*-
"""Generate nationwide 国考 data (optimized for fast front-end):
- intern low-cardinality string fields into a shared S table (stored as int index)
- precompute match flags (f=限应届, g=性别, v=裸眼视力, e=英语) so matchPost avoids regex on note
- move the long 备注 (note) to a separate lazy-loaded file job-data-gk-notes.js

posts schema (int fields resolve via S table on the page):
  i=id d=deptCode c=postCode dp=部门名称 ju=用人司局 nm=职位 n=招录人数
  [interned->int]: na=机构性质 pt=机关分区 lv=机构层级 ct=考试类别 dt=职位分布 at=职位属性 tt=面试测试 ed=学历 pl=政治面貌 dg=学位 ob=服务基层项目
  yr=基层年限 or=面试比例 lc=工作地点 st=落户地点 pv=省 cy=市 ar=区县 tl=电话
  f=限应届(0/1) g=性别('m'/'f'/'') v=裸眼视力阈值(number,0=无) e=英语('6'/'4'/'')
"""
import xlrd, json, io, re

SRC = r'C:\Users\Huawei\Desktop\中央机关及其直属机构2027年度考试录用公务员招考简章\中央机关及其直属机构2027年度考试录用公务员招考简章.xls'
OUT = r'C:\Users\Huawei\.openclaw\xxpuan-site\job-data-gk.js'
OUT_NOTES = r'C:\Users\Huawei\.openclaw\xxpuan-site\job-data-gk-notes.js'

MUNI = ['北京市', '上海市', '天津市', '重庆市']
PROV = ['河北省', '山西省', '辽宁省', '吉林省', '黑龙江省', '江苏省', '浙江省', '安徽省',
        '福建省', '江西省', '山东省', '河南省', '湖北省', '湖南省', '广东省', '海南省',
        '四川省', '贵州省', '云南省', '陕西省', '甘肃省', '青海省', '台湾省']
AUTON = ['内蒙古自治区', '广西壮族自治区', '西藏自治区', '宁夏回族自治区', '新疆维吾尔自治区']
SAR = ['香港特别行政区', '澳门特别行政区']
ALL_PROV = MUNI + PROV + AUTON + SAR

SHEET_MAP = {
    '中央党群机关': '中央党群机关',
    '中央国家行政机关（本级）': '中央国家行政机关（本级）',
    '中央国家行政机关省级以下直属机构': '省级以下直属机构',
    '中央国家行政机关参照公务员法管理事业单位': '参照公务员法管理事业单位',
}

def parse_region(loc):
    loc = (loc or '').strip()
    if not loc:
        return '', '', ''
    prov = ''
    for p in sorted(ALL_PROV, key=len, reverse=True):
        if loc.startswith(p):
            prov = p
            break
    if not prov:
        return '', '', loc
    rest = loc[len(prov):]
    if prov in MUNI:
        return prov, prov, rest
    positions = []
    for marker in ['市', '地区', '州', '盟']:
        idx = rest.find(marker)
        if idx >= 0:
            positions.append((idx, len(marker)))
    if positions:
        positions.sort()
        idx, ln = positions[0]
        city = rest[:idx + ln]
        area = rest[idx + ln:]
    else:
        city = rest
        area = ''
    return prov, city, area

def years_to_num(v):
    v = (v or '').strip()
    if not v or v == '无限制':
        return 0
    return {'一年': 1, '二年': 2, '三年': 3, '四年': 4, '五年': 5}.get(v, 0)

def cv(sh, r, c):
    v = sh.cell_value(r, c)
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v).strip()

def flags(note):
    f = 1 if re.search(r'限应届|仅限应届|限20\d\d届|仅限20\d\d届|应届毕业生报考', note) else 0
    g = ''
    if re.search(r'限男性|仅限男性|限招男性', note):
        g = 'm'
    elif re.search(r'限女性|仅限女性|限招女性', note):
        g = 'f'
    v = 0
    m = re.search(r'裸眼视力低于([\d.]+)不合格', note)
    if m:
        v = float(m.group(1))
    e = ''
    if re.search(r'英语六级|CET6|六级425', note) and '425' in note:
        e = '6'
    elif re.search(r'英语四级|CET4|四级425', note) and '425' in note:
        e = '4'
    return f, g, v, e

class Intern:
    def __init__(self):
        self.table = []
        self.idx = {}
    def add(self, val):
        val = val or ''
        if val not in self.idx:
            self.idx[val] = len(self.table)
            self.table.append(val)
        return self.idx[val]

def main():
    wb = xlrd.open_workbook(SRC)
    posts = []
    notes = {}
    unmatched = {}
    stat = {}
    IN = Intern()

    for sn in wb.sheet_names():
        if sn == 'Sheet1' or sn not in SHEET_MAP:
            continue
        sh = wb.sheet_by_name(sn)
        part = SHEET_MAP[sn]
        cnt = 0
        for r in range(2, sh.nrows):
            dept = cv(sh, r, 0)
            deptName = cv(sh, r, 1)
            bureau = cv(sh, r, 2)
            nature = cv(sh, r, 3)
            jobName = cv(sh, r, 4)
            attr = cv(sh, r, 5)
            dist = cv(sh, r, 6)
            postCode = cv(sh, r, 8)
            level = cv(sh, r, 9)
            examCat = cv(sh, r, 10)
            recruit = cv(sh, r, 11)
            major = cv(sh, r, 12)
            edu = cv(sh, r, 13)
            degree = cv(sh, r, 14)
            politics = cv(sh, r, 15)
            years = cv(sh, r, 16)
            object_ = cv(sh, r, 17)
            test = cv(sh, r, 18)
            ratio = cv(sh, r, 19)
            loc = cv(sh, r, 20)
            settle = cv(sh, r, 21)
            note = cv(sh, r, 22)
            tel1 = cv(sh, r, 24)
            tel2 = cv(sh, r, 25)
            tel3 = cv(sh, r, 26)

            if not dept and not deptName and not jobName and not postCode:
                continue

            prov, city, area = parse_region(loc)
            if loc and not prov:
                unmatched[loc] = unmatched.get(loc, 0) + 1

            try:
                n = int(recruit) if recruit else 0
            except ValueError:
                n = 0

            pid = (dept + postCode) if (dept and postCode) else ('GK-' + str(len(posts)))
            tels = '、'.join(t for t in (tel1, tel2, tel3) if t)
            f, g, v, e = flags(note)

            posts.append({
                'i': pid, 'd': dept, 'c': postCode,
                'dp': deptName, 'ju': bureau, 'nm': jobName,
                'n': n or 1,
                'na': IN.add(nature), 'pt': IN.add(part), 'lv': IN.add(level),
                'ct': IN.add(examCat), 'dt': IN.add(dist), 'at': IN.add(attr), 'tt': IN.add(test),
                'ed': IN.add(edu or '不限'), 'pl': IN.add(politics or '不限'),
                'dg': IN.add(degree), 'ob': IN.add(object_ or '不限'),
                'yr': years_to_num(years), 'or': ratio,
                'mj': major or '不限',
                'lc': loc, 'st': settle, 'pv': prov, 'cy': city, 'ar': area, 'tl': tels,
                'f': f, 'g': g, 'v': v, 'e': e,
            })
            notes[pid] = note
            cnt += 1
        stat[sn] = cnt

    payload = {
        'meta': {
            'year': 2027, 'exam': '国考', 'published': True, 'updatedAt': '2026-10-14',
            'note': '2027年度中央机关及其直属机构考试录用公务员招考简章，全国岗位，共 %d 条。' % len(posts),
            'source': '官方招考简章 Excel 解析',
        },
        'S': IN.table,
        'posts': posts,
    }

    header = ('/* 2027 国考全国岗位数据（自动生成，勿手改）\n'
              '   字段映射见 _gen_gk.py 顶部注释；带 int 的字段为 S 表索引\n'
              '   备注全文见 job-data-gk-notes.js（懒加载）\n*/\n')
    js = header + 'window.GK_DATA=' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ';\n'
    with io.open(OUT, 'w', encoding='utf-8') as f:
        f.write(js)

    notes_js = '/* 2027 国考岗位备注全文（懒加载） */\nwindow.GK_NOTES=' + json.dumps(notes, ensure_ascii=False, separators=(',', ':')) + ';\n'
    with io.open(OUT_NOTES, 'w', encoding='utf-8') as f:
        f.write(notes_js)

    print('total posts:', len(posts))
    print('main bytes:', round(len(js.encode('utf-8'))/1024/1024, 2), 'MB')
    print('notes bytes:', round(len(notes_js.encode('utf-8'))/1024/1024, 2), 'MB')
    print('S table size:', len(IN.table))
    print('sheets:', stat)
    print('unmatched locations:', len(unmatched))
    for k, v in sorted(unmatched.items()):
        print('  UNMATCHED:', repr(k), v)

if __name__ == '__main__':
    main()
