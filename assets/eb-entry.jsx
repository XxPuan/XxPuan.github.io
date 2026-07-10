import React from 'react';
import { createRoot } from 'react-dom/client';

// Inline ElectricBorder CSS
const ebCSS = `
.electric-border {
  --electric-light-color: oklch(from var(--electric-border-color) l c h);
  position: relative;
  border-radius: inherit;
  overflow: visible;
  isolation: isolate;
}
.eb-canvas-container {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  pointer-events: none;
  z-index: 2;
}
.eb-canvas { display: block; }
.eb-content {
  position: relative;
  border-radius: inherit;
  z-index: 1;
}
.eb-layers {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  z-index: 0;
}
.eb-glow-1, .eb-glow-2, .eb-background-glow {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  box-sizing: border-box;
}
.eb-glow-1 {
  border: 2px solid oklch(from var(--electric-border-color) l c h / 0.6);
  filter: blur(1px);
}
.eb-glow-2 {
  border: 2px solid var(--electric-light-color);
  filter: blur(4px);
}
.eb-background-glow {
  z-index: -1;
  transform: scale(1.1);
  filter: blur(32px);
  opacity: 0.3;
  background: linear-gradient(-30deg, var(--electric-light-color), transparent, var(--electric-border-color));
}
`;

// Inject CSS once
const styleId = '__eb_style';
if (!document.getElementById(styleId)) {
  const s = document.createElement('style');
  s.id = styleId;
  s.textContent = ebCSS;
  document.head.appendChild(s);
}

// --- ElectricBorder 组件（从 React Bits 原生移植，保持相同逻辑） ---

const random = x => (Math.sin(x * 12.9898) * 43758.5453) % 1;

function noise2D(x, y) {
  const i = Math.floor(x), j = Math.floor(y);
  const fx = x - i, fy = y - j;
  const a = random(i + j * 57), b = random(i + 1 + j * 57);
  const c = random(i + (j + 1) * 57), d = random(i + 1 + (j + 1) * 57);
  const ux = fx * fx * (3 - 2 * fx), uy = fy * fy * (3 - 2 * fy);
  return a * (1 - ux) * (1 - uy) + b * ux * (1 - uy) + c * (1 - ux) * uy + d * ux * uy;
}

function oct(x, octaves, lac, gain, baseAmp, baseFreq, time, seed, flat) {
  let y = 0, amp = baseAmp, freq = baseFreq;
  for (let i = 0; i < octaves; i++) {
    const oa = i === 0 ? amp * flat : amp;
    y += oa * noise2D(freq * x + seed * 100, time * freq * 0.3);
    freq *= lac; amp *= gain;
  }
  return y;
}

function cornerP(cx, cy, r, sa, al, pct) {
  const a = sa + pct * al;
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
}

function rndRectP(t, left, top, w, h, r) {
  const sw = w - 2 * r, sh = h - 2 * r, ca = (Math.PI * r) / 2, peri = 2 * sw + 2 * sh + 4 * ca;
  const d = t * peri; let acc = 0;
  if (d <= acc + sw) return { x: left + r + (d - acc) / sw * sw, y: top };
  acc += sw;
  if (d <= acc + ca) return cornerP(left + w - r, top + r, r, -Math.PI / 2, Math.PI / 2, (d - acc) / ca);
  acc += ca;
  if (d <= acc + sh) return { x: left + w, y: top + r + (d - acc) / sh * sh };
  acc += sh;
  if (d <= acc + ca) return cornerP(left + w - r, top + h - r, r, 0, Math.PI / 2, (d - acc) / ca);
  acc += ca;
  if (d <= acc + sw) return { x: left + w - r - (d - acc) / sw * sw, y: top + h };
  acc += sw;
  if (d <= acc + ca) return cornerP(left + r, top + h - r, r, Math.PI / 2, Math.PI / 2, (d - acc) / ca);
  acc += ca;
  if (d <= acc + sh) return { x: left, y: top + h - r - (d - acc) / sh * sh };
  acc += sh;
  return cornerP(left + r, top + r, r, Math.PI, Math.PI / 2, (d - acc) / ca);
}

function ElectricBorder({ children, color = '#5227FF', speed = 1, chaos = 0.12, borderRadius = 24, className, style }) {
  const canvasRef = React.useRef(null);
  const containerRef = React.useRef(null);
  const animRef = React.useRef(null);
  const timeRef = React.useRef(0);
  const lastTRef = React.useRef(0);

  React.useEffect(() => {
    const canvas = canvasRef.current, container = containerRef.current;
    if (!canvas || !container) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const octaves = 10, lac = 1.6, gain = 0.7, amp = chaos, freq = 10, flat = 0, disp = 60, off = 60;

    const resize = () => {
      const rect = container.getBoundingClientRect();
      const w = rect.width + off * 2, h = rect.height + off * 2;
      const dpr = Math.min(devicePixelRatio || 1, 2);
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = w + 'px';
      canvas.style.height = h + 'px';
      ctx.scale(dpr, dpr);
      return { w, h };
    };

    let dims = resize(), lastDpr = Math.min(devicePixelRatio || 1, 2);

    const draw = t => {
      if (!canvas || !ctx) return;
      const dpr = Math.min(devicePixelRatio || 1, 2);
      if (dpr !== lastDpr) { lastDpr = dpr; dims = resize(); }
      const dt = (t - lastTRef.current) / 1000;
      timeRef.current += dt * speed;
      lastTRef.current = t;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.scale(dpr, dpr);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      const sc = disp, L = off, bw = dims.w - 2 * off, bh = dims.h - 2 * off;
      const mxR = Math.min(bw, bh) / 2, R = Math.min(borderRadius, mxR);
      const cnt = Math.floor((2 * (bw + bh) + 2 * Math.PI * R) / 2);
      ctx.beginPath();
      for (let i = 0; i <= cnt; i++) {
        const pr = i / cnt;
        const pt = rndRectP(pr, L, L, bw, bh, R);
        const nx = oct(pr * 8, octaves, lac, gain, amp, freq, timeRef.current, 0, flat) * sc;
        const ny = oct(pr * 8, octaves, lac, gain, amp, freq, timeRef.current, 1, flat) * sc;
        i === 0 ? ctx.moveTo(pt.x + nx, pt.y + ny) : ctx.lineTo(pt.x + nx, pt.y + ny);
      }
      ctx.closePath();
      ctx.stroke();
      animRef.current = requestAnimationFrame(draw);
    };

    const ro = new ResizeObserver(() => { dims = resize(); });
    ro.observe(container);
    animRef.current = requestAnimationFrame(draw);

    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
      ro.disconnect();
    };
  }, [color, speed, chaos, borderRadius]);

  const vars = { '--electric-border-color': color, borderRadius };

  return React.createElement('div', {
    ref: containerRef,
    className: 'electric-border' + (className ? ' ' + className : ''),
    style: { ...vars, ...style }
  },
    React.createElement('div', { className: 'eb-canvas-container' },
      React.createElement('canvas', { ref: canvasRef, className: 'eb-canvas' })
    ),
    React.createElement('div', { className: 'eb-layers' },
      React.createElement('div', { className: 'eb-glow-1' }),
      React.createElement('div', { className: 'eb-glow-2' }),
      React.createElement('div', { className: 'eb-background-glow' })
    ),
    React.createElement('div', { className: 'eb-content' }, children)
  );
}

// --- 挂载/卸载 API（保留原始 DOM，不触碰卡片内容） ---
const roots = new Map();

window.mountElectricBorder = (hostEl, props) => {
  if (!hostEl || roots.has(hostEl)) return;

  // 卡片原本 overflow:hidden，但边框需要延伸到卡片外
  const origOverflow = hostEl.style.overflow;
  hostEl.style.overflow = 'visible';

  // 创建一个叠加层 wrapper，不碰卡片原本的 DOM
  const wrapper = document.createElement('div');
  wrapper.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;border-radius:inherit;pointer-events:none;z-index:10;overflow:visible;';
  hostEl.appendChild(wrapper);

  // 给 ElectricBorder 一个撑起尺寸的子元素
  const sizeKeeper = document.createElement('div');
  sizeKeeper.style.cssText = 'width:100%;height:100%;';

  const root = createRoot(wrapper);
  roots.set(hostEl, { root, wrapper, origOverflow });
  root.render(React.createElement(ElectricBorder, { ...props, borderRadius: 24 }, sizeKeeper));
};

window.unmountElectricBorder = (hostEl) => {
  const entry = roots.get(hostEl);
  if (entry) {
    entry.root.unmount();
    if (entry.wrapper.parentNode) {
      entry.wrapper.parentNode.removeChild(entry.wrapper);
    }
    // 恢复卡片原本的 overflow
    hostEl.style.overflow = entry.origOverflow || '';
    roots.delete(hostEl);
  }
};
