/*
 * timeline.js: the script of the video. Every "when" lives here; engine.js does the drawing.
 *
 *   0.0  Scene 1  set up the project (terminal, venv, files, requirements, pip install)
 *  11.0  Scene 2  tools.py v1 -> real crash on '15,000' -> fix -> rerun
 *  24.0  Scene 3  categorisation (rules, optional LLM, fallback)
 *  34.0  Scene 4  analysis + transparent anomaly rules
 *  42.0  Scene 5  agent.py: the LangGraph workflow
 *  50.0  Scene 6  main.py + a real run
 *  56.0  Scene 7  app.py + templates/index.html, start the server
 *  64.0  Scene 8  the working dashboard: upload, correct a category, dismiss an alert
 *  81.0  Scene 9  dashboard + live server log
 *  87.5  end
 * To change timing, edit the numbers below. To change content, edit the money-agent and re-run
 * scripts/capture.py; the video picks the new code and output up automatically.
 */
const DUR = 87.5;

/* ---------------- documents (the real files, typed as the real diffs) ---------------- */
const TV = CAP.tools_hunks;
const DOCS = {
  'requirements.txt': new Doc('txt', [{ pos: 0, del: 0, ins: CAP.files['requirements.txt'], t0: 6.75, t1: 7.85 }]),
  'tools.py': new Doc('py', [...timeHunks(TV[0], 11.3, 14.6), ...timeHunks(TV[1], 21.0, 22.5),
                             ...timeHunks(TV[2], 24.3, 32.4), ...timeHunks(TV[3], 34.2, 40.0)]),
  'agent.py': new Doc('py', [{ pos: 0, del: 0, ins: CAP.files['agent.py'], t0: 42.7, t1: 48.8 }]),
  'main.py': new Doc('py', [{ pos: 0, del: 0, ins: CAP.files['main.py'], t0: 50.3, t1: 51.7 }]),
  'app.py': new Doc('py', [{ pos: 0, del: 0, ins: CAP.files['app.py'], t0: 56.2, t1: 58.9 }]),
  'index.html': new Doc('html', [{ pos: 0, del: 0, ins: CAP.files['templates/index.html'], t0: 59.7, t1: 62.5 }]),
};
const OPEN = [['requirements.txt', 6.5], ['tools.py', 11.0], ['agent.py', 42.5], ['main.py', 50.0], ['app.py', 56.0], ['index.html', 59.4]];
const ICON = { py: ['◆', '#4b9fd6'], txt: ['≡', '#9d9d9d'], html: ['<>', '#e37933'] };
const kindOf = f => f.endsWith('.py') ? 'py' : f.endsWith('.html') ? 'html' : 'txt';
const activeFile = t => { let a = null; for (const [f, ts] of OPEN) if (t >= ts) a = f; return a; };
const dirty = (f, t) => DOCS[f].edits.some(e => t >= e.t0 && t < e.t1 + 0.35);   // unsaved while typing, saved right after

/* ---------------- terminal transcript (real output from captured.js) ---------------- */
const T = CAP.term;
const RUN = 'python tools.py data/transactions.csv';
const srv = T.server.split('\n');
const cut = re => srv.findIndex(l => re.test(l));
const iHead = cut(/Press CTRL\+C/), iGet = cut(/"GET \//), iA = cut(/POST \/api\/analyse/), iC = cut(/POST \/api\/correct/), iD = cut(/POST \/api\/dismiss/);
const part = (a, b) => srv.slice(a, b + 1).join('\n');
const TERM = [
  { k: 'prompt', prompt: 'p0', t: 0.7 },
  { k: 'cmd', prompt: 'p0', text: 'mkdir money-agent && cd money-agent', t0: 0.9, t1: 1.7 },
  { k: 'cmd', prompt: 'p1', text: 'python3 -m venv .venv && source .venv/bin/activate', t0: 2.0, t1: 3.0 },
  { k: 'cmd', prompt: 'p2', text: 'mkdir data templates && touch main.py agent.py tools.py app.py requirements.txt templates/index.html', t0: 3.3, t1: 4.9 },
  { k: 'cmd', prompt: 'p2', text: 'cp ~/Downloads/sample_transactions.csv data/transactions.csv', t0: 5.2, t1: 6.1 },
  { k: 'cmd', prompt: 'p2', text: 'pip install -r requirements.txt', t0: 8.3, t1: 8.9 },
  { k: 'out', text: T.pip, t0: 9.0, t1: 10.8 },
  { k: 'cmd', prompt: 'p2', text: 'head -6 data/transactions.csv', t0: 15.0, t1: 15.6 },
  { k: 'out', text: T.head, t0: 15.7, t1: 15.8 },
  { k: 'cmd', prompt: 'p2', text: RUN, t0: 16.4, t1: 17.3 },
  { k: 'out', text: T.tools_v1, t0: 17.5, t1: 17.9 },
  { k: 'cmd', prompt: 'p2', text: RUN, t0: 22.8, t1: 23.3 },
  { k: 'out', text: T.tools_v2, t0: 23.4, t1: 23.6 },
  { k: 'cmd', prompt: 'p2', text: RUN, t0: 32.7, t1: 33.2 },
  { k: 'out', text: T.tools_v3, t0: 33.3, t1: 33.6 },
  { k: 'cmd', prompt: 'p2', text: RUN, t0: 40.3, t1: 40.8 },
  { k: 'out', text: T.tools_v4, t0: 40.9, t1: 41.2 },
  { k: 'clear', t: 52.1 },
  { k: 'cmd', prompt: 'p2', text: 'python main.py data/transactions.csv', t0: 52.2, t1: 52.8 },
  { k: 'out', text: T.main, t0: 53.0, t1: 54.0 },
  { k: 'cmd', prompt: 'p2', text: 'python app.py', t0: 62.8, t1: 63.2 },
  { k: 'out', text: part(0, iHead), t0: 63.4, t1: 63.5 },
  { k: 'out', text: part(iHead + 1, iGet), t0: 64.6, t1: 64.6 },
  { k: 'out', text: part(iGet + 1, iA), t0: 67.0, t1: 67.6 },
  { k: 'out', text: part(iA + 1, iC), t0: 73.9, t1: 74.3 },
  { k: 'out', text: part(iC + 1, iD), t0: 77.5, t1: 77.9 },
];
// the prompt comes back after every command finishes (a following command is typed onto it)
{
  const nextPrompt = { 'mkdir money-agent && cd money-agent': 'p1', 'python3 -m venv .venv && source .venv/bin/activate': 'p2' };
  for (let i = TERM.length - 1; i >= 0; i--) {
    const e = TERM[i];
    if (e.k !== 'cmd' || e.text === 'python app.py') continue;
    let j = i + 1;
    while (TERM[j] && TERM[j].k === 'out') j++;
    const done = TERM[j - 1].k === 'out' ? TERM[j - 1].t1 : e.t1;
    TERM.splice(j, 0, { k: 'prompt', prompt: nextPrompt[e.text] || 'p2', t: done + 0.08 });
  }
}
// VS Code bottom panel: closed / normal / maximised
const PANEL = [[0, 'hide'], [0.55, 'normal'], [11.0, 'hide'], [14.8, 'normal'], [24.0, 'hide'], [32.55, 'normal'], [34.0, 'hide'],
  [40.2, 'normal'], [42.3, 'hide'], [52.0, 'max'], [56.0, 'hide'], [62.65, 'normal']];
const PANEL_H = { hide: 0, normal: 455, max: 1023 };

/* ---------------- explorer tree ---------------- */
function tree(t) {
  if (t < 1.75) return [];
  const r = [{ name: 'money-agent', dir: 1, depth: 0, open: 1 }];
  if (t >= 4.95) {
    r.push({ name: 'data', dir: 1, depth: 1 });
    if (t >= 53.1) r.push({ name: 'output', dir: 1, depth: 1 });
    r.push({ name: 'templates', dir: 1, depth: 1, open: t >= 59.4 });
    if (t >= 59.4) r.push({ name: 'index.html', depth: 2 });
    for (const f of ['agent.py', 'app.py', 'main.py', 'requirements.txt', 'tools.py']) r.push({ name: f, depth: 1 });
  }
  return r;
}
const rowY = (name, t) => { const i = tree(t).findIndex(r => r.name === name); return 70 + 22 * (i + 1) + 11; };

/* ---------------- cards (top right) ---------------- */
const CARDS = [
  [0, 1, 'Set up the project', 'Empty workspace → venv, dependencies, project files'],
  [11.0, 2, 'Load & clean transactions', 'pandas · invalid amounts, missing values, mixed date formats'],
  [17.9, 2, 'A real error', '‘15,000’ isn’t a float, and dates come in three formats. Fix it properly.'],
  [20.9, 2, 'Load & clean transactions', 'Bad rows are dropped and reported — never guessed'],
  [24.0, 3, 'Categorise expenses', 'Rules first → LLM only if configured (validated) → ‘other’ fallback'],
  [34.0, 4, 'Build the analysis tools', 'Totals · categories · month-over-month · recurring · unusual spends'],
  [37.0, 4, 'Transparent anomaly rules', '3× your usual spend · new merchant > ₹2,500 · duplicate. Unusual ≠ fraud.'],
  [40.0, 4, 'Build the analysis tools', 'Totals · categories · month-over-month · recurring · unusual spends'],
  [42.0, 5, 'Connect the agent workflow', 'LangGraph: load → categorise → analyse → detect → insights → report'],
  [50.0, 6, 'Run the agent', 'Real execution on the sample CSV — every number below is computed'],
  [56.0, 7, 'Build the dashboard', 'Flask serves the agent’s real report · user corrections are saved'],
  [64.0, 8, 'Use the working app', 'Upload a CSV → the agent runs → the dashboard fills from its output'],
  [72.6, 8, 'Correct a category', 'You stay in charge: your correction overrides the agent and totals recalculate'],
  [76.3, 8, 'Review, then dismiss an alert', 'Flagged ≠ fraud. Nothing is blocked or reported — you decide.'],
  [81.0, 9, 'The finished product', 'Live dashboard + the server log confirming each analysis run'],
];
const BADGES = [[8.3, 10.9, 30], [11.3, 14.6, 30], [21.0, 22.5, 30], [24.3, 32.4, 55], [34.2, 40.0, 52], [42.7, 48.8, 60],
  [56.2, 58.9, 120], [59.7, 62.5, 200]];
const PALETTE = [[42.0, 42.5, 'agent', 'agent.py', 'money-agent'], [59.0, 59.4, 'index', 'index.html', 'money-agent/templates']];

/* ---------------- browser story ---------------- */
const dashPhase = t => t < 65.85 ? 'empty' : t < 66.65 ? 'picked' : t < 67.6 ? 'running' : t < 73.9 ? 'r1' : t < 77.55 ? 'r2' : 'r3';
const TOASTS = [[74.0, 76.8], [77.6, 80.4]];
const DROPDOWN = [73.0, 73.9];

/* ---------------- cursor: {t, x, y} or {t, at: () => point} ; c:1 = click ---------------- */
const sel = q => () => Dash.point(q);
const CUR = [
  { t: 0, x: 1250, y: 330 }, { t: 0.6, x: 1180, y: 860 }, { t: 6.1, x: 1180, y: 870 },
  { t: 6.45, x: 150, y: () => rowY('requirements.txt', 6.4) }, { t: 6.5, x: 150, y: () => rowY('requirements.txt', 6.4), c: 1 },
  { t: 6.9, x: 1250, y: 520 }, { t: 10.7, x: 1250, y: 520 },
  { t: 10.95, x: 130, y: () => rowY('tools.py', 10.9) }, { t: 11.0, x: 130, y: () => rowY('tools.py', 10.9), c: 1 },
  { t: 11.4, x: 1300, y: 640 }, { t: 14.6, x: 1300, y: 640 }, { t: 14.9, x: 1250, y: 900 },
  { t: 41.5, x: 1250, y: 900 }, { t: 42.0, x: 1350, y: 560 },
  { t: 49.7, x: 1350, y: 560 }, { t: 49.95, x: 130, y: () => rowY('main.py', 49.9) }, { t: 50.0, x: 130, y: () => rowY('main.py', 49.9), c: 1 },
  { t: 50.4, x: 1300, y: 700 }, { t: 55.7, x: 1300, y: 700 },
  { t: 55.95, x: 130, y: () => rowY('app.py', 55.9) }, { t: 56.0, x: 130, y: () => rowY('app.py', 55.9), c: 1 },
  { t: 56.4, x: 1300, y: 640 }, { t: 63.6, x: 1300, y: 640 },
  { t: 64.6, x: 1180, y: 300 }, { t: 65.6, at: sel('.file') }, { t: 65.8, at: sel('.file'), c: 1 },
  { t: 66.4, at: sel('#run') }, { t: 66.6, at: sel('#run'), c: 1 },
  { t: 68.4, x: 430, y: 460 }, { t: 70.6, x: 1180, y: 380 }, { t: 72.0, x: 1150, y: 420 },
  { t: 72.9, at: () => Dash.checkSelect() }, { t: 73.0, at: () => Dash.checkSelect(), c: 1 },
  { t: 73.75, at: () => dropItem('education') }, { t: 73.85, at: () => dropItem('education'), c: 1 },
  { t: 74.4, x: 520, y: 470 }, { t: 76.4, x: 520, y: 470 },
  { t: 77.3, at: () => Dash.point('.flag button', 0) }, { t: 77.5, at: () => Dash.point('.flag button', 0), c: 1 },
  { t: 78.2, x: 1100, y: 900 }, { t: 81.0, x: 1100, y: 900 }, { t: 82.0, x: 1060, y: 980 },
];
let dropRect = null;
const dropItem = name => {
  if (!dropRect) return null;
  const i = Dash.categories().indexOf(name);
  return { x: dropRect.left + 60, y: dropRect.top + 4 + 15 + i * 30 };
};

/* ======================================== seek(t) ======================================== */
let lastCursor = { x: 960, y: 540 };
function resolve(k) {
  if (k.at) { const p = k.at(); return p ? { x: p.x, y: p.y } : null; }
  return { x: typeof k.x === 'function' ? k.x() : k.x, y: typeof k.y === 'function' ? k.y() : k.y };
}
function cursorAt(t) {
  let i = CUR.findIndex(k => k.t > t);
  if (i === -1) i = CUR.length;
  const A = CUR[Math.max(0, i - 1)], B = CUR[Math.min(CUR.length - 1, i)];
  const pa = resolve(A) || lastCursor, pb = resolve(B) || pa;
  const u = B.t === A.t ? 1 : ease(prog(t, A.t, B.t));
  return { x: lerp(pa.x, pb.x, u), y: lerp(pa.y, pb.y, u) };
}

function seek(t) {
  /* ---------- VS Code ---------- */
  const web = prog(t, 64.0, 64.4);
  $('vsc').style.opacity = 1 - web;
  $('vsc').style.display = web >= 1 ? 'none' : 'block';
  $('web').style.opacity = web;
  $('web').style.display = web > 0 ? 'block' : 'none';
  if (web < 1) {
    const act = activeFile(t);
    // explorer
    $('tree').innerHTML = `<div class="row h"><span class="tw">⌄</span><b>PROJECTS</b></div>` + tree(t).map(r => {
      const [ic, col] = r.dir ? [r.open ? '⌄' : '›', '#c5c5c5'] : ICON[kindOf(r.name)];
      return `<div class="row${r.name === act ? ' sel' : ''}" style="padding-left:${8 + r.depth * 12}px">` +
        (r.dir ? `<span class="tw">${ic}</span>` : `<span class="ic" style="color:${col}">${ic}</span>`) + `<span>${r.name}</span></div>`;
    }).join('');
    // tabs
    $('tabs').innerHTML = OPEN.filter(([f, ts]) => t >= ts).map(([f]) => {
      const [ic, col] = ICON[kindOf(f)], on = f === act;
      return `<div class="tab${on ? ' on' : ''}"><span class="fi" style="color:${col}">${ic}</span>${f}` +
        `<span class="x">${dirty(f, t) ? '●' : on ? '×' : ''}</span></div>`;
    }).join('');
    // panel
    let ph = 0;
    for (let i = 0; i < PANEL.length; i++) {
      const [ts, mode] = PANEL[i], prevH = i ? PANEL_H[PANEL[i - 1][1]] : 0;
      if (t >= ts) ph = lerp(prevH, PANEL_H[mode], ease(prog(t, ts, ts + 0.25)));
    }
    $('panel').style.height = ph + 'px';
    $('panel').style.display = ph > 1 ? 'block' : 'none';
    if (ph > 1) renderTerm(TERM, t, $('tbody'));
    $('shname').textContent = t < 1.7 ? '1: bash' : (t > 52.2 && t < 54.1) || t > 62.8 ? '1: python3 (money-ag' : '1: bash (money-agent)';
    // editor
    const edH = Math.max(0, 1023 - 35 - ph);
    $('editor').style.height = edH + 'px';
    $('watermark').style.display = act ? 'none' : 'block';
    $('editor').style.display = act ? 'block' : 'none';
    if (act) {
      const pos = renderEditor(DOCS[act], t, edH, true, 1023 - 35);
      $('stpos').textContent = `Ln ${pos.line}, Col ${pos.col}`;
      $('stlang').textContent = { py: 'Python', html: 'HTML', txt: 'Plain Text' }[kindOf(act)];
    }
    // quick-open palette
    const pal = PALETTE.find(([a, b]) => t >= a && t < b);
    $('palette').style.display = pal ? 'block' : 'none';
    if (pal) {
      const n = typeN(t, pal[0] + 0.05, pal[1] - 0.15, pal[2].length);
      $('palin').innerHTML = esc(pal[2].slice(0, n)) + '<span class="caret" style="height:15px;vertical-align:-2px"></span>';
      $('palres').innerHTML = n >= 3 ? `${pal[3]}<i>${pal[4]}</i>` : '';
      $('palres').style.display = n >= 3 ? 'block' : 'none';
    }
  }

  /* ---------- browser + server log ---------- */
  if (web > 0) {
    const split = ease(prog(t, 81.0, 81.8));
    const bw = lerp(1478, 1078, split), scale = bw / 1478;
    $('bwin').style.width = bw + 'px';
    const vw = 1478, vh = (1038 - 82) / scale;
    $('dash').style.transform = `scale(${scale})`;
    Dash.set(dashPhase(t), { w: vw, h: vh });
    let toastO = 0;
    for (const [a, b] of TOASTS) toastO = Math.max(toastO, Math.min(prog(t, a, a + 0.25), 1 - prog(t, b - 0.3, b)));
    Dash.toast(toastO);
    // fake native dropdown for the category <select>
    const dd = $('dropdown');
    if (t >= DROPDOWN[0] && t < DROPDOWN[1]) {
      const p = Dash.checkSelect();
      if (p) {
        const cats = Dash.categories(), listH = 8 + cats.length * 30;
        const below = p.bottom + 2 + listH <= 1050;                 // open upwards when there is no room
        dropRect = { left: p.left, top: below ? p.bottom + 2 : p.y - p.h / 2 - 2 - listH };
        dd.style.display = 'block';
        dd.style.left = (p.left - 24) + 'px'; dd.style.top = (dropRect.top - 102) + 'px'; dd.style.width = p.w + 'px';
        const cur = cursorAt(t);
        const over = i => cur.y >= dropRect.top + 4 + i * 30 && cur.y < dropRect.top + 34 + i * 30 && cur.x > p.left && cur.x < p.left + p.w;
        const hov = cats.findIndex((c, i) => over(i));
        dd.innerHTML = cats.map((c, i) => `<div${(hov === -1 ? c === 'other' : i === hov) ? ' class="hi"' : ''}>${c}</div>`).join('');
      }
    } else { dd.style.display = 'none'; }
    $('swin').style.opacity = split;
    $('swin').style.transform = `translateX(${(1 - split) * 60}px)`;
    if (split > 0) renderTerm(TERM, t, $('sbody'), 90);
  }

  /* ---------- scene card + time-lapse badge ---------- */
  let card = CARDS[0];
  for (const c of CARDS) if (t >= c[0]) card = c;
  $('cn').textContent = `SCENE ${card[1]} / 9`;
  $('ct').textContent = card[2];
  $('cs').textContent = card[3];
  $('cp').innerHTML = Array.from({ length: 9 }, (_, i) => `<i class="${i < card[1] ? 'on' : ''}"></i>`).join('');
  const cw = lerp(478, 362, web), cx = lerp(1414, 1530, web), cy = lerp(74, 66, web);
  const cEl = $('card');
  cEl.style.width = cw + 'px'; cEl.style.left = cx + 'px'; cEl.style.top = cy + 'px';
  const sinceSwap = t - card[0];
  cEl.style.opacity = (card[0] > 0 ? 0.55 + 0.45 * prog(sinceSwap, 0, 0.25) : 1) * (1 - prog(t, 82.6, 83.2));
  const bd = BADGES.find(([a, b]) => t >= a && t <= b);
  $('badge').style.opacity = bd ? Math.min(prog(t, bd[0], bd[0] + 0.15), 1 - prog(t, bd[1] - 0.15, bd[1])) : 0;
  if (bd) $('badge').textContent = `▶▶ time-lapse ${bd[2]}×`;

  /* ---------- cursor, clicks, fade ---------- */
  const p = cursorAt(t); lastCursor = p;
  $('cursor').style.transform = `translate(${p.x - 2}px,${p.y - 2}px)`;
  $('cursor').style.opacity = 1 - prog(t, 82.0, 82.6);
  let rp = 0, rx = 0, ry = 0;
  for (const k of CUR) if (k.c && t >= k.t && t < k.t + 0.35) { const q = resolve(k) || p; rp = prog(t, k.t, k.t + 0.35); rx = q.x; ry = q.y; }
  $('ripple').style.opacity = rp > 0 ? 0.9 * (1 - rp) : 0;
  $('ripple').style.left = rx + 'px'; $('ripple').style.top = ry + 'px';
  $('ripple').style.transform = `scale(${0.4 + rp * 0.9})`;
  const tg = easeOut(prog(t, 83.0, 83.5));
  $('tagline').style.opacity = tg;
  $('tagline').style.transform = `translate(-50%, ${(1 - tg) * 16}px)`;
  return true;
}

Dash.mount($('dash'));
window.seek = seek; window.DUR = DUR;
seek(parseFloat(new URLSearchParams(location.search).get('t') || '0'));
