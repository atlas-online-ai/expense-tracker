/*
 * engine.js: reusable building blocks for the video. Nothing in here knows the story;
 * timeline.js decides WHAT happens WHEN and calls these helpers from seek(t).
 *
 *   helpers ......... clamp / lerp / ease / prog / typeN / kf (keyframes) / fadeWin
 *   highlighters .... Python and HTML(+CSS+JS) -> coloured spans (VS Code Dark Modern colours)
 *   Doc ............. a text document built from timed edits {pos, del, ins} (the real diffs)
 *   renderEditor .... draws a Doc at time t: line numbers, caret, auto-scroll
 *   renderTerm ...... draws a terminal transcript at time t (typed commands + streamed output)
 */
const $ = id => document.getElementById(id);
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const lerp = (a, b, u) => a + (b - a) * u;
const ease = u => u < .5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2;
const easeOut = u => 1 - Math.pow(1 - u, 3);
const prog = (t, a, b) => clamp((t - a) / Math.max(1e-6, b - a));
const fadeWin = (t, a, b, f = .35) => Math.min(prog(t, a, a + f), 1 - prog(t, b - f, b));
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const blink = t => Math.floor(t * 1.9) % 2 === 0;
// characters typed by time t, with a little human jitter (monotonic)
const typeN = (t, t0, t1, n) => { let p = prog(t, t0, t1); if (p > 0 && p < 1) p = clamp(p + 0.006 * Math.sin(p * 70)); return Math.floor(p * n); };

function kf(list, t, keys) {
  if (t <= list[0].t) return list[0];
  for (let i = 0; i < list.length - 1; i++) {
    const A = list[i], B = list[i + 1];
    if (t <= B.t) {
      const u0 = (t - A.t) / Math.max(1e-6, B.t - A.t), u = B.lin ? u0 : ease(u0), o = {};
      for (const k of keys) o[k] = lerp(A[k], B[k], u);
      return o;
    }
  }
  return list[list.length - 1];
}

/* ============================ syntax highlighting ============================ */
const PY_CTRL = new Set('import from return if else elif for in while with as try except raise pass break continue yield await async not and or is lambda'.split(' '));
const PY_DECL = new Set('def class None True False'.split(' '));
const PY_TYPES = new Set('str int dict list float bool tuple set'.split(' '));
function hlPython(src) {
  const re = /(#[^\n]*)|("""[\s\S]*?(?:"""|$)|[rf]?"(?:[^"\\\n]|\\.)*"?|[rf]?'(?:[^'\\\n]|\\.)*'?)|(@\w+)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_]\w*)|(\s+)|([^\sA-Za-z_\d])/g;
  const out = []; let m, prev = '';
  while ((m = re.exec(src))) {
    const s = m[0]; let c = 'p';
    if (m[1]) c = 'c'; else if (m[2]) c = 's'; else if (m[3]) c = 'd'; else if (m[4]) c = 'n';
    else if (m[5]) {
      const next = src.slice(re.lastIndex).match(/^\s*(.)/);
      if (PY_CTRL.has(s)) c = 'k'; else if (PY_DECL.has(s)) c = 'b';
      else if (prev === 'def') c = 'f'; else if (prev === 'class') c = 't';
      else if (/^[A-Z][A-Z_0-9]+$/.test(s)) c = 'C';
      else if (/^[A-Z]/.test(s) || PY_TYPES.has(s)) c = 't';
      else if (next && next[1] === '(') c = 'f';
      else c = 'v';
      prev = s;
    } else if (m[6]) c = 'w';
    out.push([s, c]);
  }
  return out;
}
const JS_DECL = new Set('const let var function async new null true false this typeof instanceof'.split(' '));
const JS_CTRL = new Set('return if else await for of in while try catch throw'.split(' '));
function hlHTML(src) {
  // one pass, switching between HTML, CSS (<style>) and JS (<script>) modes
  const out = []; let i = 0, mode = 'html';
  const push = (s, c) => s && out.push([s, c]);
  while (i < src.length) {
    const rest = src.slice(i); let m;
    if (mode === 'html') {
      if ((m = rest.match(/^<!--[\s\S]*?(-->|$)/))) { push(m[0], 'c'); i += m[0].length; continue; }
      if ((m = rest.match(/^(<\/?)([A-Za-z!][\w-]*)/))) {
        push(m[1], 'ag'); push(m[2], 'tg'); i += m[0].length;
        const tag = m[2].toLowerCase(), closing = m[1] === '</';
        let a;
        while ((a = src.slice(i).match(/^(\s+)|^([\w-]+)|^(=)|^("[^"]*"?|'[^']*'?)|^(\/?>)/))) {
          if (a[1]) push(a[1], 'w'); else if (a[2]) push(a[2], 'at'); else if (a[3]) push(a[3], 'p'); else if (a[4]) push(a[4], 's');
          else { push(a[5], 'ag'); i += a[0].length; if (!closing && tag === 'style') mode = 'css'; if (!closing && tag === 'script') mode = 'js'; break; }
          i += a[0].length;
        }
        continue;
      }
      m = rest.match(/^[^<]+/) || [rest[0]]; push(m[0], 'p'); i += m[0].length; continue;
    }
    if (mode === 'css') {
      if (rest.startsWith('</style')) { mode = 'html'; continue; }
      if ((m = rest.match(/^\/\*[\s\S]*?(\*\/|$)/))) { push(m[0], 'c'); i += m[0].length; continue; }
      if ((m = rest.match(/^#[0-9A-Fa-f]{3,6}\b/))) { out.push([m[0], 'hex']); i += m[0].length; continue; }
      if ((m = rest.match(/^--?[a-zA-Z][\w-]*(?=\s*:)/)) || (m = rest.match(/^[a-z-]+(?=\s*:)/))) {
        const inBlock = src.lastIndexOf('{', i) > src.lastIndexOf('}', i);
        push(m[0], inBlock ? 'pr' : 'sel'); i += m[0].length; continue;
      }
      if ((m = rest.match(/^var(?=\()|^calc(?=\()|^repeat(?=\()/))) { push(m[0], 'f'); i += m[0].length; continue; }
      if ((m = rest.match(/^-?\d*\.?\d+(px|fr|em|vh|%|s)?/))) { push(m[0], 'n'); i += m[0].length; continue; }
      if ((m = rest.match(/^[^\s{}:;,()#]+/))) {
        const inBlock = src.lastIndexOf('{', i) > src.lastIndexOf('}', i);
        push(m[0], inBlock ? 's' : 'sel'); i += m[0].length; continue;
      }
      push(rest[0], rest[0].trim() ? 'p' : 'w'); i += 1; continue;
    }
    // js
    if (rest.startsWith('</script')) { mode = 'html'; continue; }
    if ((m = rest.match(/^\/\/[^\n]*/))) { push(m[0], 'c'); i += m[0].length; continue; }
    if ((m = rest.match(/^`(?:[^`\\]|\\.)*`?/))) { push(m[0], 's'); i += m[0].length; continue; }
    if ((m = rest.match(/^"(?:[^"\\\n]|\\.)*"?|^'(?:[^'\\\n]|\\.)*'?/))) { push(m[0], 's'); i += m[0].length; continue; }
    if ((m = rest.match(/^\d+(\.\d+)?/))) { push(m[0], 'n'); i += m[0].length; continue; }
    if ((m = rest.match(/^[A-Za-z_$][\w$]*/))) {
      const s = m[0], next = src.slice(i + s.length).match(/^\s*(.)/);
      let c = JS_DECL.has(s) ? 'b' : JS_CTRL.has(s) ? 'k' : /^[A-Z][A-Z_]+$/.test(s) ? 'C' : /^[A-Z]/.test(s) ? 't' : next && next[1] === '(' ? 'f' : 'v';
      push(s, c); i += s.length; continue;
    }
    push(rest[0], rest[0].trim() ? 'p' : 'w'); i += 1;
  }
  return out;
}
function hlPlain(src) {
  return src.split(/(\n)/).map(l => [l, l.trim().startsWith('#') ? 'c' : 'p']);
}
const HL = { py: hlPython, html: hlHTML, txt: hlPlain };

// tokens -> array of line HTML strings
function tokLines(tokens) {
  const lines = [''];
  for (const [s, c] of tokens) {
    s.split('\n').forEach((part, k) => {
      if (k > 0) lines.push('');
      if (!part) return;
      if (c === 'hex') lines[lines.length - 1] += `<i class="sw" style="background:${part}"></i><span class="s">${esc(part)}</span>`;
      else lines[lines.length - 1] += c === 'w' ? esc(part) : `<span class="${c}">${esc(part)}</span>`;
    });
  }
  return lines;
}

/* ============================ documents built from edits ============================ */
// A Doc is a list of timed edits. edit = {pos, del, ins, t0, t1}. At time t every finished edit is
// applied in full; the running edit deletes its old text at t0 and then "types" its new text.
class Doc {
  constructor(lang, edits) { this.lang = lang; this.edits = edits; }
  state(t) {
    let text = '', caret = 0, typing = false;
    for (const e of this.edits) {
      if (t < e.t0) break;
      const n = t >= e.t1 ? e.ins.length : typeN(t, e.t0, e.t1, e.ins.length);
      text = text.slice(0, e.pos) + e.ins.slice(0, n) + text.slice(e.pos + e.del);
      caret = e.pos + n;
      if (t < e.t1) { typing = true; break; }
    }
    return { text, caret, typing };
  }
  get start() { return this.edits.length ? this.edits[0].t0 : 0; }
  get end() { return this.edits.length ? this.edits[this.edits.length - 1].t1 : 0; }
}
// spread a list of {pos,del,ins} hunks over [t0, t1] proportionally to how much text they type
function timeHunks(hunks, t0, t1, gap = 0.12) {
  const total = hunks.reduce((s, h) => s + h.ins.length + 20, 0);
  const span = t1 - t0 - gap * (hunks.length - 1);
  let t = t0;
  return hunks.map(h => { const d = span * (h.ins.length + 20) / total; const e = { ...h, t0: t, t1: t + d }; t += d + gap; return e; });
}

/* ============================ editor rendering ============================ */
const LINE_H = 25;
function caretLine(text, caret) { let n = 0; for (let i = 0; i < caret; i++) if (text.charCodeAt(i) === 10) n++; return n; }
function renderEditor(doc, t, heightPx, showCaret = true, typingHeightPx = heightPx) {
  const st = doc.state(t);
  const lines = tokLines(HL[doc.lang](st.text));
  const vis = Math.floor((heightPx - 8) / LINE_H);
  const tvis = Math.floor((typingHeightPx - 8) / LINE_H);  // scrolling follows the caret in the typing view
  const cl = caretLine(st.text, st.caret);
  // smooth scroll: average the target over the last 0.3 s
  let sc = 0;
  for (let k = 0; k < 6; k++) {
    const s2 = doc.state(t - k * 0.06), l2 = caretLine(s2.text, s2.caret);
    const n2 = s2.text.split('\n').length;
    sc += clamp(l2 - Math.floor(tvis * 0.62), 0, Math.max(0, n2 - tvis + 2));
  }
  sc /= 6;
  const top = Math.floor(sc), off = (sc - top) * LINE_H;
  let html = '';
  for (let i = top; i < Math.min(lines.length, top + vis + 2); i++) {
    const cur = i === cl;
    const caretHtml = cur && showCaret && (st.typing || blink(t)) ? '<span class="caret"></span>' : '';
    let body = lines[i];
    if (cur && caretHtml) {
      // place the caret at the right column of the current line
      const lineStart = st.text.lastIndexOf('\n', st.caret - 1) + 1;
      const col = st.caret - lineStart;
      const lineText = st.text.slice(lineStart).split('\n')[0];
      const toks = tokLines(HL[doc.lang](lineText.slice(0, col)))[0] || '';
      const after = tokLines(HL[doc.lang](lineText.slice(col)))[0] || '';
      body = col < lineText.length ? toks + caretHtml + after : body + caretHtml;
    }
    html += `<div class="ln${cur ? ' cur' : ''}"><span class="no">${i + 1}</span><span>${body}</span></div>`;
  }
  $('code').innerHTML = html;
  $('code').style.transform = `translateY(${-off}px)`;
  const total = Math.max(lines.length, vis);
  $('vscroll').style.display = lines.length > vis ? 'block' : 'none';
  $('vscroll').style.top = (sc / total * heightPx) + 'px';
  $('vscroll').style.height = Math.max(30, vis / total * heightPx) + 'px';
  const lastNl = st.text.lastIndexOf('\n', st.caret - 1);
  return { line: cl + 1, col: st.caret - lastNl, typing: st.typing };
}

/* ============================ terminal rendering ============================ */
// script entries: {k:'cmd', prompt, text, t0, t1} | {k:'out', text, t0, t1} | {k:'prompt', prompt, t}
const PROMPTS = {
  p0: '<span class="pg">dev</span>:<span class="pb">~/projects</span>$ ',
  p1: '<span class="pg">dev</span>:<span class="pb">~/projects/money-agent</span>$ ',
  p2: '(.venv) <span class="pg">dev</span>:<span class="pb">~/projects/money-agent</span>$ ',
};
function colourOut(line) {
  const l = esc(line);
  if (/^\s*File "/.test(line)) return l.replace(/(File )(&quot;|")([^"]+)("|&quot;)/, '$1<span class="mg">"$3"</span>');
  if (/^\w*Error:/.test(line)) return `<span class="er">${l}</span>`;
  if (/^\s*[~^]+\s*$/.test(line)) return `<span class="er">${l}</span>`;
  if (line.startsWith('WARNING:')) return `<span class="wn">${l}</span>`;
  if (line.startsWith('Press CTRL+C')) return `<span class="ye">${l}</span>`;
  if (/^\d\d:\d\d:\d\d \| /.test(line)) return l.replace(/^(\d\d:\d\d:\d\d)/, '<span class="dm">$1</span>');
  return l;
}
function renderTerm(script, t, el, maxLines = 140) {
  const out = []; let last = null;
  for (const e of script) {
    const st = e.k === 'prompt' || e.k === 'clear' ? e.t : e.t0;
    if (t < st) break;
    if (e.k === 'clear') { out.length = 0; last = null; continue; }   // `clear` / Ctrl+L
    last = e;
    const wasPrompt = out.isPrompt; out.isPrompt = false;
    if (e.k === 'cmd') {
      if (out.length && wasPrompt) out.pop();               // typed onto the waiting prompt
      out.push(PROMPTS[e.prompt] + esc(e.text.slice(0, typeN(t, e.t0, e.t1, e.text.length))));
    }
    else if (e.k === 'prompt') { out.push(PROMPTS[e.prompt]); out.isPrompt = true; continue; }
    else {
      const lines = e.text.split('\n');
      const n = t >= e.t1 ? lines.length : Math.max(1, Math.ceil(prog(t, e.t0, e.t1) * lines.length));
      for (const l of lines.slice(0, n)) out.push(colourOut(l));
    }
  }
  if (last && ((last.k === 'cmd' && (t < last.t1 + 0.1 || blink(t))) || (last.k === 'prompt' && blink(t))))
    out[out.length - 1] += '<span style="background:#cccccc">&nbsp;</span>';
  el.innerHTML = out.slice(-maxLines).join('\n');
  // like a real terminal: text starts at the top and only scrolls once the panel is full
  const full = el.scrollHeight > el.parentElement.clientHeight;
  el.style.top = full ? 'auto' : '0'; el.style.bottom = full ? '0' : 'auto';
}
