# -*- coding: utf-8 -*-
"""Generate job-data-gk.js (nationwide 国考) from the 2027 招考简章 .xls
Compact-key schema (documented in output header):
  i  = id (部门代码+职位代码)   d = deptCode 部门代码   c = postCode 职位代码
  dp = dept 部门名称(招录单位)  ju = bureau 用人司局     nm = name 招考职位
  n  = recruit 招考人数        ed = education 学历      dg = degree 学位
  mj = major 专业              pl = politics 政治面貌   ob = object 服务基层项目经历
  yr = years 基层工作最低年限  nt = note 备注           or = openRatio 面试人员比例
  lv = level 机构层级          ct = cat 考试类别        na = nature 机构性质
  at = attr 职位属性           dt = dist 职位分布       tt = test 是否面试专业测试
  lc = loc 工作地点原文        st = settle 落户地点     pv = province 省
  cy = city 市                 ar = area 区县           pt = part 机关分区(sheet)
  tl = tel 咨询电话(顿号分隔)
"""
import xlrd, json, io

SRC = r'C:\Users\Huawei\Desktop\中央机关及其直属机构2027年度考试录用公务员招考简章\中央机关及其直属机构2027年度考试录用公务员招考简章.xls'
OUT = r'C:\Users\Huawei\.openclaw\xxpuan-site\job-data-gk.js'

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

def main():
    wb = xlrd.open_workbook(SRC)
    posts = []
    unmatched = {}
    stat = {}
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

            posts.append({
                'i': pid, 'd': dept, 'c': postCode,
                'dp': deptName, 'ju': bureau, 'nm': jobName,
                'n': n or 1, 'ed': edu or '不限', 'dg': degree,
                'mj': major or '不限', 'pl': politics or '不限', 'ob': object_ or '不限',
                'yr': years_to_num(years), 'nt': note, 'or': ratio,
                'lv': level, 'ct': examCat, 'na': nature, 'at': attr, 'dt': dist, 'tt': test,
                'lc': loc, 'st': settle, 'pv': prov, 'cy': city, 'ar': area,
                'pt': part, 'tl': tels,
            })
            cnt += 1
        stat[sn] = cnt

    payload = {
        'meta': {
            'year': 2027,
            'exam': '国考',
            'published': True,
            'updatedAt': '2026-10-14',
            'note': '2027年度中央机关及其直属机构考试录用公务员招考简章，全国岗位，共 %d 条。' % len(posts),
            'source': '官方招考简章 Excel 解析',
        },
        'posts': posts,
    }

    header = ('/* 2027 国考全国岗位数据（自动生成，勿手改）\n'
              '   字段映射见 _gen_gk.py 顶部注释\n'
              '   id = d + c（部门代码+职位代码）\n*/\n')
    js = header + 'window.GK_DATA=' + json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + ';\n'

    with io.open(OUT, 'w', encoding='utf-8') as f:
        f.write(js)

    size = len(js.encode('utf-8'))
    print('total posts:', len(posts))
    print('output bytes:', size, '=', round(size / 1024 / 1024, 2), 'MB')
    print('sheets:', stat)
    print('unmatched locations:', len(unmatched))
    for k, v in sorted(unmatched.items()):
        print('  UNMATCHED:', repr(k), v)

if __name__ == '__main__':
    main()
