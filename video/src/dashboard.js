/*
 * dashboard.js: runs the REAL money-agent dashboard (money-agent/templates/index.html, copied
 * into captured.js) inside the video's browser window.
 *
 * The page's own <style>, markup and <script> are mounted in a Shadow DOM so its CSS can't leak
 * into the video. Its network calls are not needed: we hand it the JSON reports that the real
 * Flask server returned during capture (initial analysis, after a correction, after a dismissal)
 * and call its own show()/render() functions. So every number on screen is the app's own output.
 */
const Dash = (() => {
  const src = CAP.dashboard;
  const css = src.match(/<style>([\s\S]*?)<\/style>/)[1]
    .replace(':root', ':host')                       // CSS variables live on the shadow host
    .replace(/body\s*\{/, ':host { display:block; ')
    .replace(/100vh/g, 'var(--vh)')
    .replace('#toast { position: fixed;', '#toast { position: absolute;')
    .replace('transition: opacity .3s;', 'transition: none;');           // the timeline animates it
  const body = src.match(/<body>([\s\S]*?)<script>/)[1];
  const script = src.match(/<script>([\s\S]*?)<\/script>/)[1];

  let host, root, api, shown = null;
  function mount(el) {
    host = document.createElement('div');
    host.style.cssText = 'position:relative;width:1478px;font:15px Inter, system-ui, sans-serif;color:#151922;background:#F5F6F8';
    el.appendChild(host);
    root = host.attachShadow({ mode: 'open' });
    root.innerHTML = `<style>${css}</style>${body}`;
    const fakeDocument = { getElementById: id => root.getElementById(id) };
    const noTimer = () => 0;                      // the video controls the toast itself
    api = new Function('document', 'setTimeout', script +
      '\nreturn { show, render, setStatus, rs, getReport: () => report, reset: () => { report = null; } };')(fakeDocument, noTimer);
  }
  const R = CAP.reports;
  const fixId = CAP.corrected;
  const msgCorrect = (b, n) => {
    const m = n.analysis.month, cat = 'education', old = 'other', rs = api.rs;
    return `Recalculated · ${cat}: ${rs(b.analysis.by_month[m][cat] || 0)} → ${rs(n.analysis.by_month[m][cat] || 0)}` +
      ` · ${old}: ${rs(b.analysis.by_month[m][old] || 0)} → ${rs(n.analysis.by_month[m][old] || 0)}`;
  };
  const dismissedId = R[1].flags[0].txn_id;
  const msgDismiss = (b, n) => `Alert ${dismissedId} dismissed · ${n.flags.length} left to review`;

  // phase: 'empty' | 'picked' | 'running' | 'r1' | 'r2' | 'r3'
  function set(phase, size) {
    host.style.setProperty('--vh', size.h + 'px');
    host.style.width = size.w + 'px';
    if (phase === shown) return;
    shown = phase;
    const content = root.getElementById('content');
    api.reset();
    root.getElementById('month').innerHTML = '';
    root.getElementById('fname').textContent = phase === 'empty' ? 'Choose CSV…' : 'transactions.csv';
    content.innerHTML = '<div class="card empty">Upload a transactions CSV to see where your money went.</div>';
    api.setStatus(phase === 'running' ? 'Agent running: load → categorise → analyse → detect anomalies → insights → report …' : '');
    if (['r1', 'r2', 'r3'].includes(phase)) api.show(R[0], null);
    if (['r2', 'r3'].includes(phase)) api.show(R[1], msgCorrect);
    if (phase === 'r3') api.show(R[2], msgDismiss);
  }
  function toast(opacity) { const t = root.getElementById('toast'); t.style.opacity = opacity; }
  // centre of an element inside the dashboard, in stage coordinates
  function point(selector, nth = 0) {
    const el = root.querySelectorAll(selector)[nth];
    if (!el) return null;
    const r = el.getBoundingClientRect(), s = document.getElementById('stage').getBoundingClientRect();
    const k = 1920 / s.width;
    return { x: (r.left + r.width / 2 - s.left) * k, y: (r.top + r.height / 2 - s.top) * k, w: r.width * k, h: r.height * k, left: (r.left - s.left) * k, bottom: (r.bottom - s.top) * k };
  }
  function checkSelect() {        // the "Check these categories" dropdown for the row we correct
    const rows = [...root.querySelectorAll('table select')];
    const i = api.getReport() ? api.getReport().transactions.filter(t => ['fallback', 'llm', 'you'].includes(t.source))
      .findIndex(t => t.txn_id === fixId) : -1;
    return i >= 0 ? point('table select', i) : null;
  }
  return { mount, set, toast, point, checkSelect, categories: () => R[0].categories };
})();
