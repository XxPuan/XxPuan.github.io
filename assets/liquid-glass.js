/* =============================================================================
 * Liquid Glass —— 网页液态玻璃效果引擎（ES 模块版，浏览器可直接 import）
 * 折射(SVG 位移贴图) + 物理高光(specular)
 *
 * 用法：
 * import { createLiquidGlass } from './liquidGlass.js';
 * import './liquidGlass.css';
 * const glass = createLiquidGlass(el, { draggable:true, specular:'physical' });
 * glass.update({ scale: 70 }); glass.destroy();
 *
 * 仅 Chromium 内核支持把 SVG 滤镜用作 backdrop-filter（折射核心）；
 * 其它浏览器自动降级为普通模糊，不报错。
 * ========================================================================== */

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const smoother = (x) => x * x * x * (x * (x * 6 - 15) + 10);
const TRANSPARENT =
 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';
const ETA = 1 / 1.5;

function surfaceHeight(type, x) {
 x = clamp(x, 0, 1);
 const cC = Math.sqrt(Math.max(0, 1 - (1 - x) ** 2));
 const cS = Math.pow(Math.max(0, 1 - (1 - x) ** 4), 0.25);
 switch (type) {
 case 'convexCircle': return cC;
 case 'convexSquircle': return cS;
 case 'concave': return 1 - cS;
 case 'lip': return cS * (1 - smoother(x)) + (1 - cS) * smoother(x);
 default: return cS;
 }
}

function snell(type, t, bezel, thick) {
 const e = 1e-3, f = (xx) => surfaceHeight(type, xx);
 const h = thick * f(t);
 const slope = (thick * (f(t + e) - f(t - e))) / (2 * e) / bezel;
 const L = Math.hypot(slope, 1), nx = -slope / L, nz = 1 / L, cosi = nz;
 const k = 1 - ETA * ETA * (1 - cosi * cosi);
 if (k < 0) return 0;
 const cost = Math.sqrt(k), fac = ETA * cosi - cost;
 const Tx = fac * nx, Tz = -ETA + fac * nz;
 if (Tz >= 0) return 0;
 return Tx * (h / -Tz);
}

function buildProfile(type, bezel, thick, n) {
 n = n || 127;
 const disp = [], slope = [];
 let md = 1e-6, ms = 1e-6, e = 1e-3;
 for (let i = 0; i < n; i++) {
 const t = i / (n - 1);
 disp.push(snell(type, t, bezel, thick)); md = Math.max(md, Math.abs(disp[i]));
 const sl = Math.abs((thick * (surfaceHeight(type, t + e) - surfaceHeight(type, t - e))) / (2 * e) / bezel);
 slope.push(sl); ms = Math.max(ms, sl);
 }
 return { disp: disp.map((v) => v / md), slope: slope.map((v) => v / ms), n };
}

function makeSDF(W, H, r) {
 return (x, y) => {
 const qx = Math.abs(x - W / 2) - (W / 2 - r), qy = Math.abs(y - H / 2) - (H / 2 - r);
 return Math.hypot(Math.max(qx, 0), Math.max(qy, 0)) + Math.min(Math.max(qx, qy), 0) - r;
 };
}

const LIGHT = { x: -0.7071, y: -0.7071 };
function buildMaps(wCss, hCss, o) {
 const dpr = o.dpr;
 const W = Math.max(2, Math.round(wCss * dpr)), H = Math.max(2, Math.round(hCss * dpr));
 const r = clamp(o.radius * dpr, 0, Math.min(W, H) / 2), bz = o.bezel * dpr;
 const sdf = makeSDF(W, H, r);
 const prof = o.mode === 'physics' ? buildProfile(o.surface, bz, o.thickness * dpr) : null;
 const sign = o.flip ? -1 : 1;
 const wantSpec = o.specular === 'physical';
 // 高光光源方向：优先用角度 lightAngle（度；225° 对应旧默认的左上方向），否则回退 light 向量
 let LX, LY;
 if (o.lightAngle != null) { const a = (o.lightAngle * Math.PI) / 180; LX = Math.cos(a); LY = Math.sin(a); }
 else { LX = (o.light || LIGHT).x; LY = (o.light || LIGHT).y; }

 const cvD = document.createElement('canvas'); cvD.width = W; cvD.height = H;
 const dCtx = cvD.getContext('2d'); const dImg = dCtx.createImageData(W, H); const D = dImg.data;
 let sCtx, sImg, S, cvS;
 if (wantSpec) {
 cvS = document.createElement('canvas'); cvS.width = W; cvS.height = H;
 sCtx = cvS.getContext('2d'); sImg = sCtx.createImageData(W, H); S = sImg.data;
 }

 // 象限镜像：圆角矩形折射上下左右对称，故只计算左上 1/4，其余三块翻转法线镜像写入（约 4× 提速）。
 // 位移方向 outx/outy 在水平/垂直镜像下精确翻转符号；mag/rim/高光各自用翻转后的法线重算，与逐像素完全等价。
 const halfW = (W + 1) >> 1, halfH = (H + 1) >> 1;
 const bendAmt = o.bend || 0;
 // 写一个像素的位移(D)与高光(S)；outx/outy 是该点指向外的法线
 function putD(x, y, mag, outx, outy, rim) {
 const i = (y * W + x) * 4;
 D[i] = clamp(128 + (-outx) * mag * 127, 0, 255);
 D[i + 1] = clamp(128 + (-outy) * mag * 127, 0, 255);
 D[i + 2] = 128; D[i + 3] = 255;
 if (wantSpec) {
 const facing = outx * LX + outy * LY;
 const lit = Math.pow(clamp(0.5 + 0.5 * facing, 0, 1), 3);
 S[i] = 255; S[i + 1] = 255; S[i + 2] = 255;
 S[i + 3] = Math.round(clamp(rim * lit * o.specularIntensity, 0, 1) * 255);
 }
 }
 // 折射带外：中性灰、零位移（高光保持透明）
 function putNeutral(x, y) {
 const i = (y * W + x) * 4;
 D[i] = 128; D[i + 1] = 128; D[i + 2] = 128; D[i + 3] = 255;
 }
 for (let y = 0; y < halfH; y++) {
 const my = H - 1 - y;
 for (let x = 0; x < halfW; x++) {
 const mx = W - 1 - x;
 const dist = -sdf(x + 0.5, y + 0.5);
 if (dist > 0 && dist < bz) {
 const t = dist / bz;
 let mag, rim;
 if (o.mode === 'physics') {
 const fi = t * (prof.n - 1), i0 = Math.floor(fi), i1 = Math.min(i0 + 1, prof.n - 1), fr = fi - i0;
 mag = prof.disp[i0] * (1 - fr) + prof.disp[i1] * fr;
 rim = prof.slope[i0] * (1 - fr) + prof.slope[i1] * fr;
 } else { mag = Math.cos((t * Math.PI) / 2); rim = mag; }
 // 弯液面 bend：沿同方向在最外缘薄带内追加向内折射，峰值落在带外 1/3、clip 线上为 0
 // —— 背景在玻璃边缘"裹"一圈、像液珠的弯月面（6.75 = 27/4，把 s²(1−s) 归一到峰值 1）
 if (bendAmt > 0) { const s = 1 - t; mag += bendAmt * 6.75 * s * s * (1 - s); }
 mag *= sign;
 const gx = sdf(x + 1, y) - sdf(x - 1, y), gy = sdf(x, y + 1) - sdf(x, y - 1);
 const gl = Math.hypot(gx, gy) || 1, outx = gx / gl, outy = gy / gl;
 putD(x, y, mag, outx, outy, rim); // 左上（本体）
 putD(mx, y, mag, -outx, outy, rim); // 右上（镜像 X）
 putD(x, my, mag, outx, -outy, rim); // 左下（镜像 Y）
 putD(mx, my, mag, -outx, -outy, rim); // 右下（镜像 XY）
 } else {
 putNeutral(x, y); putNeutral(mx, y); putNeutral(x, my); putNeutral(mx, my);
 }
 }
 }
 dCtx.putImageData(dImg, 0, 0);
 const out = { disp: cvD.toDataURL() };
 if (wantSpec) { sCtx.putImageData(sImg, 0, 0); out.spec = cvS.toDataURL(); }
 return out;
}

let _defs = null, _uid = 0;
function ensureDefs() {
 if (_defs) return _defs;
 const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
 svg.setAttribute('aria-hidden', 'true');
 svg.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden';
 const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
 svg.appendChild(defs); document.body.appendChild(svg);
 _defs = defs; return defs;
}
function filterMarkup(id) {
 return (
 '<filter id="' + id + '" x="-20%" y="-20%" width="140%" height="140%"' +
 ' color-interpolation-filters="sRGB" primitiveUnits="userSpaceOnUse">' +
 '<feImage class="lg-fe-disp" result="dispmap"/>' +
 '<feGaussianBlur in="SourceGraphic" class="lg-fe-blur" stdDeviation="0.5" result="b"/>' +
 // 色散(chromatic aberration)：RGB 三遍位移——红外偏 / 绿居中 / 蓝内偏（对称，故不整体偏移），再按通道合并
 '<feDisplacementMap in="b" in2="dispmap" class="lg-fe-dmR" xChannelSelector="R" yChannelSelector="G" result="dR"/>' +
 '<feColorMatrix in="dR" type="matrix" values="1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0" result="cR"/>' +
 '<feDisplacementMap in="b" in2="dispmap" class="lg-fe-dmG" xChannelSelector="R" yChannelSelector="G" result="dG"/>' +
 '<feColorMatrix in="dG" type="matrix" values="0 0 0 0 0 0 0 0 0 0 1 0 0 0 0 0 0 0 1 0" result="cG"/>' +
 '<feDisplacementMap in="b" in2="dispmap" class="lg-fe-dmB" xChannelSelector="R" yChannelSelector="G" result="dB"/>' +
 '<feColorMatrix in="dB" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0 0 1 0" result="cB"/>' +
 '<feComposite in="cR" in2="cG" operator="arithmetic" k1="0" k2="1" k3="1" k4="0" result="cRG"/>' +
 '<feComposite in="cRG" in2="cB" operator="arithmetic" k1="0" k2="1" k3="1" k4="0" result="disp"/>' +
 '<feColorMatrix in="disp" type="saturate" class="lg-fe-sat" values="1.2" result="sat"/>' +
 '<feImage class="lg-fe-spec" result="specmap"/>' +
 '<feComposite in="specmap" in2="sat" operator="over"/></filter>'
 );
}
function supportsUrlFilter() {
 return (typeof CSS !== 'undefined' && CSS.supports &&
 (CSS.supports('backdrop-filter', 'url(#x)') || CSS.supports('-webkit-backdrop-filter', 'url(#x)'))) || false;
}
function setBackdrop(el, v) { el.style.backdropFilter = v; el.style.webkitBackdropFilter = v; }
function elDiv(cls) { const d = document.createElement('div'); d.className = cls; return d; }

export const DEFAULTS = {
 mode: 'physics', surface: 'convexSquircle', specular: 'physical',
 bezel: 30, thickness: 80, scale: 58, specularIntensity: 0.85, blur: 0.5, saturate: 1.2,
 dispersion: 0.4, lightAngle: 225, bend: 0.4,
 flip: false, light: { x: -0.7071, y: -0.7071 }, radius: null, draggable: false,
 dpr: Math.min((typeof window !== 'undefined' ? window.devicePixelRatio : 1) || 1, 2),
};

export function createLiquidGlass(host, options) {
 const o = Object.assign({}, DEFAULTS, options || {});
 host.classList.add('liquid-glass');

 const content = elDiv('lg-content');
 while (host.firstChild) content.appendChild(host.firstChild);
 const refract = elDiv('lg-refract'), tint = elDiv('lg-tint'), edge = elDiv('lg-edge');
 host.appendChild(refract); host.appendChild(tint); host.appendChild(edge); host.appendChild(content);

 const id = 'lg-filter-' + (++_uid);
 const defs = ensureDefs();
 defs.insertAdjacentHTML('beforeend', filterMarkup(id));
 const f = defs.querySelector('#' + id);
 const feDisp = f.querySelector('.lg-fe-disp'), feSpec = f.querySelector('.lg-fe-spec'),
 feDMR = f.querySelector('.lg-fe-dmR'), feDMG = f.querySelector('.lg-fe-dmG'), feDMB = f.querySelector('.lg-fe-dmB'),
 feBlur = f.querySelector('.lg-fe-blur'), feSat = f.querySelector('.lg-fe-sat');
 // 折射强度 + 色散：基准位移 = o.scale，红/蓝按 dispersion 在基准上对称偏移（0.11 = 0.22×0.5，与参考实现一致）
 function applyScale() {
 const base = o.scale, k = 0.11 * (o.dispersion || 0);
 feDMR.setAttribute('scale', base * (1 + k));
 feDMG.setAttribute('scale', base);
 feDMB.setAttribute('scale', base * (1 - k));
 }

 const SUP = supportsUrlFilter();
 if (SUP) setBackdrop(refract, 'url(#' + id + ')');
 function nudge() {
 if (!SUP) return;
 setBackdrop(refract, 'none'); void refract.offsetWidth;
 setBackdrop(refract, 'url(#' + id + ')');
 }
 function setFeImg(node, url, w, h) {
 node.setAttribute('x', 0); node.setAttribute('y', 0);
 node.setAttribute('width', w); node.setAttribute('height', h);
 node.setAttribute('href', url);
 node.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', url);
 }
 function resolveRadius(rect) {
 if (o.radius != null) return o.radius;
 const br = parseFloat(getComputedStyle(host).borderRadius) || 0;
 return br || Math.min(rect.width, rect.height) / 2;
 }
 function rebuild() {
 const rect = host.getBoundingClientRect();
 if (rect.width < 2) return;
 host.classList.toggle('lg-spec-css', o.specular === 'css');
 host.classList.toggle('lg-spec-none', o.specular === 'none');
 feSat.setAttribute('values', o.saturate);
 const maps = buildMaps(rect.width, rect.height, Object.assign({}, o, { radius: resolveRadius(rect) }));
 setFeImg(feDisp, maps.disp, rect.width, rect.height);
 setFeImg(feSpec, maps.spec || TRANSPARENT, rect.width, rect.height);
 applyScale();
 feBlur.setAttribute('stdDeviation', o.blur);
 const pre = new Image(); pre.onload = nudge; pre.onerror = nudge; pre.src = maps.disp;
 }
 function tune() { applyScale(); feBlur.setAttribute('stdDeviation', o.blur); nudge(); }

 const ro = new ResizeObserver(() => rebuild());
 ro.observe(host);

 let drag = null;
 if (o.draggable) { drag = attachDrag(host); }

 rebuild();

 return {
 host, options: o,
 update(patch) {
 const onlyTune = patch && Object.keys(patch).every((k) => k === 'scale' || k === 'blur' || k === 'dispersion');
 Object.assign(o, patch);
 onlyTune ? tune() : rebuild();
 },
 refresh: rebuild,
 destroy() {
 ro.disconnect(); if (drag) drag.destroy();
 f.remove(); refract.remove(); tint.remove(); edge.remove();
 while (content.firstChild) host.appendChild(content.firstChild);
 content.remove();
 host.classList.remove('liquid-glass', 'lg-spec-css', 'lg-spec-none');
 },
 };
}

// 让玻璃可拖动（纯移动，无额外动效）—— 主要用于在调试工具里移动取景
function attachDrag(glass) {
 let dragging = false, ox = 0, oy = 0;
 const onDown = (e) => {
 dragging = true; glass.setPointerCapture(e.pointerId);
 const r = glass.getBoundingClientRect(); ox = e.clientX - r.left; oy = e.clientY - r.top;
 };
 const onMove = (e) => {
 if (!dragging) return;
 glass.style.left = (e.clientX - ox) + 'px'; glass.style.top = (e.clientY - oy) + 'px';
 };
 const onUp = () => { dragging = false; };
 glass.addEventListener('pointerdown', onDown);
 glass.addEventListener('pointermove', onMove);
 glass.addEventListener('pointerup', onUp);
 glass.style.touchAction = 'none'; glass.style.cursor = 'grab';
 return { destroy() { glass.removeEventListener('pointerdown', onDown); glass.removeEventListener('pointermove', onMove); glass.removeEventListener('pointerup', onUp); } };
}
