const fs = require('fs');
const html = fs.readFileSync('C:/Users/Huawei/.openclaw/xxpuan-site/sk.html', 'utf8');

try {
  const m = html.match(/<script>([\s\S]*?)<\/script>/);
  new Function(m[1]);
  console.log('inline script: SYNTAX OK');
} catch (e) { console.log('SYNTAX ERROR:', e.message); }

const im = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const ids = new Set();
for (const mm of im.matchAll(/\$\('([^']+)'\)/g)) ids.add(mm[1]);
const defs = new Set();
for (const mm of html.matchAll(/id="([^"]+)"/g)) defs.add(mm[1]);
let miss = [];
for (const id of ids) if (!defs.has(id)) miss.push(id);
console.log('referenced ids:', ids.size, '| missing:', miss.length ? miss : 'none');

for (const s of ['provSeg', 'provNote', 'applyCell', 'scoreCell', '26报名', '26进面', 'data-prov', 'apply-num']) {
  console.log(s, html.includes(s) ? 'present' : 'MISSING');
}

// 数据含 2026 字段
const fs2 = require('fs');
const vm = require('vm');
const ctx = { window: {} };
vm.createContext(ctx);
vm.runInContext(fs2.readFileSync('C:/Users/Huawei/.openclaw/xxpuan-site/job-data-sk.js', 'utf8'), ctx);
const D = ctx.window.SK_DATA;
const with26 = D.posts.filter(p => p.ap).length;
console.log('数据含 2026 报名数据的职位数:', with26);
const s = D.posts.find(p => p.ap);
console.log('样例:', s.i, s.un, s.nm, '报名', s.ap, '进面', s.mn, '~', s.mx);
