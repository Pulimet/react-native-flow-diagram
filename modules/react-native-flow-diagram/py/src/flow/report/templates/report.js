(function () {
  'use strict';

  const DATA = JSON.parse(document.getElementById('flow-data').textContent);
  const META = DATA.meta || {};
  const EVENTS = DATA.events || [];
  const BY_ID = new Map(EVENTS.map(e => [e.id, e]));
  const KINDS = [
    { id: 'native', label: 'Native (Sync)' },
    { id: 'rn', label: 'React Native' },
    { id: 'net_req', label: 'Network Request' },
    { id: 'net_rsp', label: 'Network Response' },
    { id: 'async', label: 'Async (Native/RN)' },
  ];
  const KIND_LABEL = Object.fromEntries(KINDS.map(k => [k.id, k.label]));
  const isMarker = e => e.kind === 'async' || e.kind === 'net_req';
  const end = e => e.start + e.duration;
  const kindColor = k => `var(--c-${k})`;
  const $ = s => document.querySelector(s);
  const fmt = n => (n == null || Number.isNaN(n) ? '–' : Math.round(n).toLocaleString('en-US'));
  const ms = n => (n == null ? '–' : `${fmt(n)} ms`);
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const debounce = (fn, wait) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), wait); }; };
  const LS = 'flowdiagram.report.';

  // ---------- Derived stats ----------
  const stats = e => {
    const v = e.all && e.all.length ? e.all.slice().sort((a, b) => a - b) : [e.time];
    const mean = v.reduce((a, b) => a + b, 0) / v.length;
    const sd = Math.sqrt(v.reduce((a, b) => a + (b - mean) ** 2, 0) / v.length);
    const mid = Math.floor(v.length / 2);
    const median = v.length % 2 ? v[mid] : (v[mid - 1] + v[mid]) / 2;
    return { sorted: v, mean, sd, median, spread: v[v.length - 1] - v[0] };
  };
  EVENTS.forEach(e => { const s = stats(e); e.spread = s.spread; e.sd = Math.round(s.sd); e.median = Math.round(s.median); });
  const MAX_END = Math.max(1, ...EVENTS.map(e => Math.max(end(e), e.max || 0)));
  const MAX_DUR = Math.max(0, ...EVENTS.filter(e => !isMarker(e)).map(e => e.duration));
  const syncEvents = EVENTS.filter(e => (e.kind === 'native' || e.kind === 'rn') && e.mode !== 'ASYNC');
  const lastSync = syncEvents.length ? syncEvents.reduce((a, b) => (end(b) > end(a) ? b : a)) : null;
  const slowestStep = syncEvents.length ? syncEvents.reduce((a, b) => (b.duration > a.duration ? b : a)) : null;

  const milestones = [];
  const appInit = EVENTS.find(e => e.msg === 'Process start -> App init');
  if (appInit) milestones.push({ t: appInit.time, label: 'App init' });
  const firstRn = EVENTS.find(e => e.kind === 'rn');
  if (firstRn) milestones.push({ t: firstRn.time, label: 'First RN' });
  if (META.system_total_time_ms) milestones.push({ t: META.system_total_time_ms, label: 'AM TotalTime' });
  if (lastSync) milestones.push({ t: end(lastSync), label: 'Last SYNC' });
  milestones.sort((a, b) => a.t - b.t);

  // ---------- Network pairing ----------
  const NET = (() => {
    const reqs = EVENTS.filter(e => e.kind === 'net_req');
    const used = new Set();
    return EVENTS.filter(e => e.kind === 'net_rsp').map(r => {
      const m = /^\[(\w+)\]\s+(.*)$/.exec(r.msg);
      const status = m ? m[1] : '';
      const url = m ? m[2] : r.msg;
      const req = reqs.find(q => !used.has(q.id) && q.msg === url);
      if (req) used.add(req.id);
      const start = req ? req.time : r.time - r.duration;
      let domain = '(unknown)';
      try { domain = new URL(url.replace(/\(\d+\)$/, '')).host; } catch (_) { /* not a URL */ }
      return { id: r.id, reqId: req ? req.id : null, url, status, domain, start, end: r.time, duration: r.duration, count: r.count };
    }).concat(reqs.filter(q => !used.has(q.id)).map(q => {
      let domain = '(unknown)';
      try { domain = new URL(q.msg.replace(/\(\d+\)$/, '')).host; } catch (_) { /* not a URL */ }
      return { id: q.id, reqId: q.id, url: q.msg, status: 'no response', domain, start: q.time, end: q.time, duration: null, count: q.count };
    }));
  })();

  // ---------- State + URL hash ----------
  const state = {
    view: 'split', q: '', kinds: new Set(KINDS.map(k => k.id)), minDur: 0, slowest: 0, critical: false, hideMarkers: false,
    whiskers: true, linkWindow: false, selected: null, domain: null,
  };
  (function readHash() {
    const p = new URLSearchParams(location.hash.slice(1));
    if (p.has('v')) state.view = p.get('v');
    if (p.has('q')) state.q = p.get('q');
    if (p.has('k')) state.kinds = new Set(p.get('k').split(',').filter(Boolean));
    if (p.has('md')) state.minDur = +p.get('md') || 0;
    if (p.has('sl')) state.slowest = +p.get('sl') || 0;
    state.critical = p.get('cp') === '1';
    state.hideMarkers = p.get('hm') === '1';
    if (p.has('wh')) state.whiskers = p.get('wh') !== '0';
    state.linkWindow = p.get('lw') === '1';
    if (p.has('sel') && BY_ID.has(+p.get('sel'))) state.selected = +p.get('sel');
    if (p.has('z')) { const z = p.get('z').split('~').map(Number); if (z.length === 2 && z[1] > z[0]) state.domain = z; }
  })();
  const writeHash = debounce(() => {
    const p = new URLSearchParams();
    if (state.view !== 'split') p.set('v', state.view);
    if (state.q) p.set('q', state.q);
    if (state.kinds.size !== KINDS.length) p.set('k', [...state.kinds].join(','));
    if (state.minDur) p.set('md', state.minDur);
    if (state.slowest) p.set('sl', state.slowest);
    if (state.critical) p.set('cp', '1');
    if (state.hideMarkers) p.set('hm', '1');
    if (!state.whiskers) p.set('wh', '0');
    if (state.linkWindow) p.set('lw', '1');
    if (state.selected != null) p.set('sel', state.selected);
    if (state.domain) p.set('z', state.domain.map(Math.round).join('~'));
    history.replaceState(null, '', p.toString() ? `#${p}` : location.pathname + location.search);
  }, 150);

  // ---------- Filtering ----------
  function queryMatcher() {
    const q = state.q.trim();
    if (!q) return null;
    const rx = /^\/(.+)\/([a-z]*)$/.exec(q);
    if (rx) { try { const r = new RegExp(rx[1], rx[2].includes('i') ? rx[2] : rx[2] + 'i'); return s => r.test(s); } catch (_) { /* fall through */ } }
    const lower = q.toLowerCase();
    return s => s.toLowerCase().includes(lower);
  }
  function passes(e, match) {
    if (!state.kinds.has(e.kind)) return false;
    if (match && !match(e.msg)) return false;
    if (state.minDur > 0 && e.duration < state.minDur) return false;
    if (state.hideMarkers && isMarker(e)) return false;
    return true;
  }
  function inWindow(e) {
    if (!state.linkWindow || !state.domain) return true;
    return end(e) >= state.domain[0] && e.start <= state.domain[1];
  }
  let visible = EVENTS;
  function recompute() {
    const match = queryMatcher();
    visible = EVENTS.filter(e => passes(e, match));
    $('#filter-count').textContent = visible.length === EVENTS.length ? `${EVENTS.length} events` : `${visible.length} of ${EVENTS.length} events`;
  }
  function hotSet() {
    const hot = new Set();
    if (state.critical) syncEvents.forEach(e => hot.add(e.id));
    if (state.slowest) visible.filter(e => !isMarker(e)).sort((a, b) => b.duration - a.duration).slice(0, state.slowest).forEach(e => hot.add(e.id));
    return hot;
  }

  // ---------- Theme ----------
  const applyTheme = t => { document.documentElement.dataset.theme = t; localStorage.setItem(LS + 'theme', t); };
  applyTheme(localStorage.getItem(LS + 'theme') || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'));

  // ---------- Toast / tooltip / clipboard ----------
  function toast(text) {
    const el = document.createElement('div'); el.className = 'toast'; el.textContent = text;
    $('#toasts').appendChild(el); setTimeout(() => el.remove(), 2700);
  }
  async function copy(text, label) {
    try { await navigator.clipboard.writeText(text); } catch (_) {
      const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select();
      document.execCommand('copy'); ta.remove();
    }
    toast(label || 'Copied');
  }
  const tip = $('#tooltip');
  function showTip(ev, e) {
    tip.innerHTML = `<div class="t-msg">${esc(e.msg)}</div>
      <div class="t-row"><span class="pill" style="--pc:${kindColor(e.kind)}">${KIND_LABEL[e.kind]}</span></div>
      <div class="t-row">Time <b>${ms(e.time)}</b>${isMarker(e) ? '' : ` · Duration <b>${ms(e.duration)}</b>`}</div>
      <div class="t-row">Runs <b>${e.count}</b> · Min <b>${ms(e.min)}</b> · Max <b>${ms(e.max)}</b> · σ <b>${ms(e.sd)}</b></div>`;
    tip.classList.add('show'); moveTip(ev);
  }
  function moveTip(ev) {
    const r = tip.getBoundingClientRect();
    tip.style.left = Math.min(ev.clientX + 14, innerWidth - r.width - 8) + 'px';
    tip.style.top = Math.min(ev.clientY + 14, innerHeight - r.height - 8) + 'px';
  }
  const hideTip = () => tip.classList.remove('show');

  // ---------- Header + cards ----------
  $('#subtitle').textContent = [META.app_id, META.platform, META.generated_at && `generated ${META.generated_at.replace('T', ' ')}`]
    .filter(Boolean).join(' · ');
  (function cards() {
    const items = [
      { k: 'Device', v: META.device || '–', s: [META.platform, META.os && `OS ${META.os}`].filter(Boolean).join(' · ') },
      { k: 'Build', v: META.build || '–', s: META.app_version ? `version ${META.app_version}` : '' },
      { k: 'Runs', v: META.runs ?? (DATA.runs || []).length, s: DATA.failures && DATA.failures.length ? `${DATA.failures.length} failed` : `t0: ${META.t0 || '–'}` },
      { k: 'Last SYNC', v: lastSync ? ms(end(lastSync)) : '–', s: lastSync ? lastSync.msg : '', id: lastSync && lastSync.id },
      META.system_total_time_ms ? { k: 'AM TotalTime', v: ms(META.system_total_time_ms), s: 'am start -W average' } : null,
      { k: 'Slowest step', v: slowestStep ? ms(slowestStep.duration) : '–', s: slowestStep ? slowestStep.msg : '', id: slowestStep && slowestStep.id },
      { k: 'Events', v: EVENTS.length, s: `${syncEvents.length} sync · ${EVENTS.filter(e => e.kind === 'async').length} async` },
      { k: 'Network', v: NET.length, s: `${new Set(NET.map(n => n.domain)).size} domains` },
    ];
    if (META.note) items.push({ k: 'Note', v: '⚠', s: META.note });
    const shown = items.filter(Boolean);
    $('#cards').innerHTML = shown.map((c, i) => `<div class="card${c.id != null ? ' clickable' : ''}" style="animation-delay:${i * 45}ms"
        ${c.id != null ? `data-id="${c.id}"` : ''} title="${esc(c.s || '')}"><div class="k">${c.k}</div><div class="v">${esc(c.v)}</div><div class="s">${esc(c.s || '')}</div></div>`).join('');
    $('#cards').addEventListener('click', ev => { const c = ev.target.closest('.card[data-id]'); if (c) select(+c.dataset.id, { locate: true, open: true }); });
  })();

  if (!window.d3 || !window.Tabulator) { $('#cdn-error').hidden = false; return; }

  // ---------- Filter controls ----------
  const chipCount = k => EVENTS.filter(e => e.kind === k).length;
  $('#kind-chips').innerHTML = KINDS.map(k => `<button class="chip" data-kind="${k.id}" title="Click to toggle, double click to show only this type">
      <i style="background:${kindColor(k.id)}"></i>${k.label}<b>${chipCount(k.id)}</b></button>`).join('');
  $('#legend').innerHTML = KINDS.map(k => `<span><i style="background:${kindColor(k.id)}"></i>${k.label}</span>`).join('')
    + '<span class="ms"><i></i>Milestone</span><span>── min/max across runs</span>';
  function syncControls() {
    document.querySelectorAll('.chip').forEach(c => c.classList.toggle('off', !state.kinds.has(c.dataset.kind)));
    $('#search').value = state.q;
    $('#min-dur').max = Math.max(1, MAX_DUR); $('#min-dur').value = state.minDur; $('#min-dur-out').textContent = `${state.minDur} ms`;
    $('#slowest').value = String(state.slowest);
    $('#critical').checked = state.critical; $('#hide-markers').checked = state.hideMarkers; $('#whiskers').checked = state.whiskers; $('#link-window').checked = state.linkWindow;
  }
  let chipClickTimer;
  $('#kind-chips').addEventListener('click', ev => {
    const c = ev.target.closest('.chip'); if (!c) return;
    clearTimeout(chipClickTimer);
    chipClickTimer = setTimeout(() => {
      const k = c.dataset.kind; state.kinds.has(k) ? state.kinds.delete(k) : state.kinds.add(k); update();
    }, 200);
  });
  $('#kind-chips').addEventListener('dblclick', ev => {
    const c = ev.target.closest('.chip'); if (!c) return;
    clearTimeout(chipClickTimer); state.kinds = new Set([c.dataset.kind]); update();
  });
  $('#search').addEventListener('input', debounce(ev => { state.q = ev.target.value; update(); }, 120));
  $('#min-dur').addEventListener('input', ev => { state.minDur = +ev.target.value; $('#min-dur-out').textContent = `${state.minDur} ms`; updateDebounced(); });
  $('#slowest').addEventListener('change', ev => { state.slowest = +ev.target.value; update(); });
  $('#hide-markers').addEventListener('change', ev => { state.hideMarkers = ev.target.checked; update(); });
  $('#critical').addEventListener('change', ev => { state.critical = ev.target.checked; update(); });
  $('#whiskers').addEventListener('change', ev => { state.whiskers = ev.target.checked; update(); });
  $('#link-window').addEventListener('change', ev => { state.linkWindow = ev.target.checked; refreshTable(); writeHash(); });
  $('#btn-reset-filters').addEventListener('click', () => {
    Object.assign(state, { q: '', kinds: new Set(KINDS.map(k => k.id)), minDur: 0, slowest: 0, critical: false, hideMarkers: false, linkWindow: false });
    table.clearHeaderFilter(); update(); toast('Filters reset');
  });

  // ---------- Views ----------
  function setView(v) {
    state.view = v;
    const main = $('#main'); main.className = `view-${v}`;
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.view === v));
    const active = document.querySelector('.tab.active'), ink = $('.tab-ink');
    if (active) { ink.style.left = active.offsetLeft + 'px'; ink.style.width = active.offsetWidth + 'px'; }
    requestAnimationFrame(() => { diagram.resize(); table.redraw(); netTable.redraw(); });
    writeHash();
  }
  document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => setView(t.dataset.view)));

  // Split gutter
  (function gutter() {
    const g = $('#gutter'), dp = $('#diagram-panel'), tp = $('#table-panel');
    const saved = +localStorage.getItem(LS + 'split');
    const apply = f => { dp.style.flex = `1 1 ${f * 100}%`; tp.style.flex = `1 1 ${(1 - f) * 100}%`; };
    if (saved) apply(saved);
    g.addEventListener('pointerdown', ev => {
      g.setPointerCapture(ev.pointerId);
      const rect = $('#main').getBoundingClientRect();
      const move = e => { const f = Math.min(.85, Math.max(.15, (e.clientY - rect.top) / rect.height)); apply(f); localStorage.setItem(LS + 'split', f); diagram.resize(); };
      const up = () => { g.removeEventListener('pointermove', move); g.removeEventListener('pointerup', up); table.redraw(); };
      g.addEventListener('pointermove', move); g.addEventListener('pointerup', up);
    });
  })();

  // ---------- Diagram ----------
  const diagram = (function () {
    const ROW = 24, BAR = 14, M = { l: 14, r: 18 };
    const wrap = $('#chart-wrap');
    const svg = d3.select('#chart'), axisSvg = d3.select('#axis'), mini = d3.select('#minimap');
    const defs = svg.append('defs');
    defs.append('clipPath').attr('id', 'clip').append('rect');
    const gGrid = svg.append('g').attr('class', 'grid');
    const gRows = svg.append('g').attr('clip-path', 'url(#clip)');
    const gMiles = svg.append('g');
    const emptyText = svg.append('text').attr('class', 'empty').attr('text-anchor', 'middle').text('No events match the filters');
    const gAxis = axisSvg.append('g').attr('class', 'axis').attr('transform', 'translate(0,38)');
    const gAxisMiles = axisSvg.append('g').attr('class', 'milestone');
    const gMini = mini.append('g'), gBrush = mini.append('g').attr('class', 'brush');

    const x0 = d3.scaleLinear().domain([0, MAX_END * 1.04 + 100]);
    let zx = x0.copy(), width = 0, height = 0, hot = new Set(), first = true, syncing = false;

    const zoom = d3.zoom()
      .scaleExtent([1, Math.max(50, MAX_END / 20)])
      .filter(ev => (ev.type === 'wheel' ? ev.ctrlKey || ev.metaKey || ev.shiftKey : !ev.button) && ev.type !== 'dblclick')
      .on('zoom', ev => {
        zx = ev.transform.rescaleX(x0);
        const d = zx.domain();
        state.domain = ev.transform.k === 1 && ev.transform.x === 0 ? null : d;
        position(gRows.selectAll('g.row'));
        drawAxis();
        if (!syncing) { syncing = true; gBrush.call(brush.move, d.map(x0)); syncing = false; }
        writeHash(); followZoom();
      });
    svg.call(zoom);
    svg.on('wheel.pan', ev => { // horizontal trackpad swipe pans the timeline
      if (Math.abs(ev.deltaX) > Math.abs(ev.deltaY) && !ev.ctrlKey && !ev.metaKey) {
        ev.preventDefault(); zoom.translateBy(svg, -ev.deltaX / d3.zoomTransform(svg.node()).k, 0);
      }
    }, { passive: false });
    const brush = d3.brushX().on('brush end', ev => {
      if (syncing || !ev.sourceEvent || !ev.selection) return;
      const [a, b] = ev.selection.map(x0.invert);
      syncing = true; zoomTo(a, b, 0); syncing = false;
    });

    function zoomTo(a, b, duration = 650) {
      const k = Math.max(1, (x0.range()[1] - x0.range()[0]) / Math.max(1e-6, x0(b) - x0(a)));
      const t = d3.zoomIdentity.scale(k).translate(-x0(a) + M.l / k, 0);
      (duration ? svg.transition().duration(duration).ease(d3.easeCubicInOut) : svg).call(zoom.transform, t);
    }

    function drawAxis() {
      const ticks = Math.max(2, Math.floor(width / 90));
      gAxis.call(d3.axisTop(zx).ticks(ticks).tickFormat(d => (d >= 1000 ? `${d3.format(',.2~f')(d / 1000)} s` : `${d} ms`)));
      const [a, b] = zx.domain(), span = b - a;
      const minor = span > 20000 ? 1000 : span > 3000 ? 100 : span > 600 ? 50 : 10;
      const major = minor * 10;
      const lines = d3.range(Math.ceil(a / minor) * minor, b, minor).slice(0, 600);
      gGrid.selectAll('line').data(lines, d => d).join('line')
        .attr('class', d => (d % major === 0 ? 'major' : null))
        .attr('x1', zx).attr('x2', zx).attr('y1', 0).attr('y2', height);
      const ms = gMiles.selectAll('g').data(milestones).join(enter => {
        const g = enter.append('g').attr('class', 'milestone'); g.append('line'); return g;
      });
      ms.select('line').attr('x1', d => zx(d.t)).attr('x2', d => zx(d.t)).attr('y1', 0).attr('y2', height);
      const ams = gAxisMiles.selectAll('text').data(milestones).join('text')
        .attr('x', d => zx(d.t) + 3).attr('y', 11).attr('display', null).text(d => `${d.label} ${fmt(d.t)}`);
      ams.attr('display', d => (zx(d.t) < 0 || zx(d.t) > width ? 'none' : null));
      // Close milestones share one label instead of drawing over each other.
      let prev = null;
      ams.each(function () {
        if (this.getAttribute('display') === 'none') return;
        const x = +this.getAttribute('x');
        if (prev && x < +prev.getAttribute('x') + prev.getComputedTextLength() + 8) {
          prev.textContent += ` · ${this.textContent}`; this.setAttribute('display', 'none');
        } else prev = this;
      });
      gAxisMiles.selectAll('line').data(milestones).join('line').attr('x1', d => zx(d.t)).attr('x2', d => zx(d.t)).attr('y1', 14).attr('y2', 42);
    }

    function markerPath(e) { return e.kind === 'net_req' ? 'M0,-7L6,0L0,7L-6,0Z' : 'M-5,-6L5,-6L0,6Z'; }

    function position(rows) {
      rows.select('.row-bg').attr('width', width);
      rows.select('.bar').attr('x', e => zx(e.start)).attr('width', e => Math.max(2, zx(end(e)) - zx(e.start)));
      rows.select('.marker').attr('transform', e => `translate(${zx(e.time)},${ROW / 2})`);
      rows.select('.whisker').attr('x1', e => zx(e.min)).attr('x2', e => zx(e.max))
        .attr('display', e => (state.whiskers && e.max > e.min ? null : 'none'));
      rows.select('.dur-label').attr('x', e => zx(e.start) + 5)
        .attr('display', e => (!isMarker(e) && zx(end(e)) - zx(e.start) > 52 ? null : 'none'));
      rows.select('.label').attr('x', e => {
        const right = (isMarker(e) ? zx(e.time) + 9 : zx(end(e)) + 6);
        return Math.max(4, state.whiskers && e.max > e.min ? Math.max(right, zx(e.max) + 6) : right);
      });
    }

    function render() {
      hot = hotSet();
      const rows = visible;
      height = Math.max(rows.length * ROW + 8, wrap.clientHeight - 2);
      svg.attr('height', height).attr('width', width);
      defs.select('#clip rect').attr('width', width).attr('height', height);
      emptyText.attr('x', width / 2).attr('y', 60).attr('display', rows.length ? 'none' : null);
      const dur = first ? 0 : 450;
      const sel = gRows.selectAll('g.row').data(rows, e => e.id).join(
        enter => {
          const g = enter.append('g').attr('class', 'row').attr('transform', (e, i) => `translate(0,${i * ROW})`).style('opacity', 0);
          g.append('rect').attr('class', 'row-bg').attr('height', ROW);
          g.append('line').attr('class', 'whisker').attr('y1', ROW / 2).attr('y2', ROW / 2);
          g.filter(e => !isMarker(e)).append('rect').attr('class', 'bar').attr('y', (ROW - BAR) / 2).attr('height', BAR)
            .attr('rx', 3).style('fill', e => kindColor(e.kind)).style('color', e => kindColor(e.kind));
          g.filter(isMarker).append('path').attr('class', 'marker').attr('d', markerPath).style('fill', e => kindColor(e.kind));
          g.filter(e => !isMarker(e)).append('text').attr('class', 'dur-label').attr('y', ROW / 2 + 3.5).text(e => `${fmt(e.duration)} ms`);
          g.append('text').attr('class', 'label').attr('y', ROW / 2 + 4).text(e => e.msg);
          g.on('click', (ev, e) => select(e.id, { from: 'diagram', open: true }))
            .on('mouseenter', (ev, e) => showTip(ev, e)).on('mousemove', moveTip).on('mouseleave', hideTip);
          g.transition().delay((e, i) => (first ? Math.min(i * 12, 900) : 0)).duration(first ? 500 : dur).style('opacity', 1);
          if (first) {
            g.select('.bar').attr('transform', 'scale(0,1)').style('transform-origin', e => `${zx(e.start)}px 0`)
              .transition().delay((e, i) => Math.min(i * 12, 900) + 100).duration(600).ease(d3.easeCubicOut).attr('transform', null);
          }
          return g;
        },
        update => update.call(u => u.transition().duration(dur).ease(d3.easeCubicInOut)
          .attr('transform', (e, i) => `translate(0,${i * ROW})`).style('opacity', 1)),
        exit => exit.call(x => x.transition().duration(dur / 1.5).style('opacity', 0).remove()),
      );
      sel.classed('hot', e => hot.has(e.id)).classed('dim', e => hot.size > 0 && !hot.has(e.id))
        .classed('selected', e => e.id === state.selected);
      position(sel);
      drawAxis();
      drawMinimap();
      first = false;
    }

    function drawMinimap() {
      const h = 46, n = Math.max(1, EVENTS.length);
      mini.attr('width', width).attr('height', h);
      gMini.selectAll('rect').data(EVENTS, e => e.id).join('rect').attr('class', 'minimap-bar')
        .attr('x', e => x0(e.start)).attr('width', e => Math.max(1.5, x0(end(e)) - x0(e.start)))
        .attr('y', (e, i) => 4 + (i / n) * (h - 10)).attr('height', Math.max(1.5, (h - 10) / n))
        .style('fill', e => kindColor(e.kind)).style('opacity', e => (visible.includes(e) ? .85 : .15));
      brush.extent([[x0.range()[0], 0], [x0.range()[1], h]]);
      gBrush.call(brush);
      syncing = true; gBrush.call(brush.move, zx.domain().map(x0)); syncing = false;
    }

    function resize() {
      const w = wrap.clientWidth;
      if (!w) return;
      const t = d3.zoomTransform(svg.node());
      width = w;
      axisSvg.attr('width', width).attr('height', 42);
      x0.range([M.l, width - M.r]);
      zoom.extent([[0, 0], [width, Math.max(1, height)]]).translateExtent([[0, 0], [width, Math.max(1, height)]]);
      zx = t.rescaleX(x0);
      render();
    }

    function scrollToRow(id) {
      const i = visible.findIndex(e => e.id === id);
      if (i < 0) return;
      const top = i * ROW, view = wrap.clientHeight;
      if (top < wrap.scrollTop + 10 || top > wrap.scrollTop + view - ROW * 2) wrap.scrollTo({ top: top - view / 2, behavior: 'smooth' });
    }

    function locate(id) {
      const e = BY_ID.get(id); if (!e) return;
      const span = Math.max(e.duration, e.max - e.min, 150);
      zoomTo(Math.max(0, e.start - span * 1.2), end(e) + span * 1.6);
      scrollToRow(id);
    }

    const followZoom = debounce(() => { if (state.linkWindow) refreshTable(); }, 200);

    new ResizeObserver(debounce(resize, 60)).observe(wrap);
    $('#zoom-in').onclick = () => svg.transition().duration(300).call(zoom.scaleBy, 1.6);
    $('#zoom-out').onclick = () => svg.transition().duration(300).call(zoom.scaleBy, 1 / 1.6);
    $('#zoom-fit').onclick = () => svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
    $('#zoom-sel').onclick = () => (state.selected != null ? locate(state.selected) : toast('Select an event first'));

    return {
      render, resize, locate, scrollToRow,
      zoomIn: () => $('#zoom-in').click(), zoomOut: () => $('#zoom-out').click(), fit: () => $('#zoom-fit').click(),
      restore() { if (state.domain) zoomTo(state.domain[0], state.domain[1], 0); },
      markSelected() { gRows.selectAll('g.row').classed('selected', e => e.id === state.selected); },
    };
  })();

  // ---------- Table ----------
  function numFilter(headerValue, rowValue) {
    const v = String(headerValue).trim();
    if (!v) return true;
    let m;
    if ((m = /^(-?\d+(?:\.\d+)?)\s*(?:-|\.\.)\s*(-?\d+(?:\.\d+)?)$/.exec(v))) return rowValue >= +m[1] && rowValue <= +m[2];
    if ((m = /^(>=|<=|>|<|=)\s*(-?\d+(?:\.\d+)?)$/.exec(v))) {
      const n = +m[2];
      return { '>': rowValue > n, '<': rowValue < n, '>=': rowValue >= n, '<=': rowValue <= n, '=': rowValue === n }[m[1]];
    }
    return String(rowValue).includes(v);
  }
  const numCol = (title, field, extra = {}) => ({
    title, field, hozAlign: 'right', sorter: 'number', headerFilter: 'input', headerFilterFunc: numFilter,
    headerFilterPlaceholder: '>100, 10-50', width: 92, formatter: c => `<span class="num">${fmt(c.getValue())}</span>`, ...extra,
  });
  function sparkline(values, w = 110, h = 20) {
    if (!values || values.length < 2) return `<span class="muted">${values && values.length ? fmt(values[0]) : ''}</span>`;
    const lo = Math.min(...values), hi = Math.max(...values), r = hi - lo || 1;
    const pts = values.map((v, i) => `${(i / (values.length - 1)) * (w - 4) + 2},${h - 3 - ((v - lo) / r) * (h - 6)}`).join(' ');
    return `<svg class="spark" width="${w}" height="${h}"><polyline points="${pts}" fill="none" stroke="var(--accent2)" stroke-width="1.5"/>`
      + `<line x1="2" x2="${w - 2}" y1="${h - 3 - ((values.reduce((a, b) => a + b, 0) / values.length - lo) / r) * (h - 6)}" y2="${h - 3 - ((values.reduce((a, b) => a + b, 0) / values.length - lo) / r) * (h - 6)}" stroke="var(--accent)" stroke-dasharray="2 2" stroke-width="1"/></svg>`;
  }
  const table = new Tabulator('#table', {
    data: EVENTS, index: 'id', layout: 'fitDataStretch', height: '100%', reactiveData: false,
    selectableRows: 1, movableColumns: true, placeholder: 'No events match the filters',
    persistence: { columns: ['width', 'visible'], sort: true }, persistenceID: 'flowdiagram-events', persistenceMode: 'local',
    initialSort: [{ column: 'time', dir: 'asc' }],
    columns: [
      { title: '', field: '_locate', width: 38, headerSort: false, resizable: false, download: false, frozen: true,
        formatter: () => '<button class="locate" title="Locate in diagram">◎</button>',
        cellClick: (ev, cell) => { ev.stopPropagation(); select(cell.getRow().getData().id, { locate: true, from: 'table' }); } },
      numCol('Time', 'time', { frozen: true }),
      numCol('Duration', 'duration', { formatter: c => (isMarker(c.getData()) ? '<span class="muted">marker</span>' : `<span class="num">${fmt(c.getValue())}</span>`) }),
      { title: 'Kind', field: 'kind', width: 150, headerFilter: 'list',
        headerFilterParams: { values: Object.fromEntries([['', 'All']].concat(KINDS.map(k => [k.id, k.label]))), clearable: true },
        formatter: c => `<span class="pill" style="--pc:${kindColor(c.getValue())}">${KIND_LABEL[c.getValue()]}</span>`,
        accessorDownload: v => KIND_LABEL[v] },
      { title: 'Type', field: 'type', width: 72, headerFilter: 'list', headerFilterParams: { valuesLookup: true, clearable: true } },
      { title: 'Mode', field: 'mode', width: 80, headerFilter: 'list', headerFilterParams: { valuesLookup: true, clearable: true } },
      { title: 'Req/Rsp', field: 'reqRsp', width: 80, headerFilter: 'list', headerFilterParams: { valuesLookup: true, clearable: true }, visible: false },
      { title: 'Level', field: 'level', width: 76, headerFilter: 'list', headerFilterParams: { valuesLookup: true, clearable: true }, visible: false },
      { title: 'Message', field: 'msg', minWidth: 260, width: 420, widthGrow: 3, headerFilter: 'input', headerFilterPlaceholder: 'filter…', tooltip: true,
        formatter: c => `<span title="${esc(c.getValue())}">${esc(c.getValue())}</span>` },
      numCol('Runs', 'count', { width: 72 }),
      numCol('Min', 'min'), numCol('Max', 'max'), numCol('Spread', 'spread'),
      numCol('Median', 'median', { visible: false }), numCol('σ', 'sd', { width: 76 }),
      { title: 'Per run', field: 'all', width: 130, headerSort: false, download: true, accessorDownload: v => (v || []).join(' '),
        formatter: c => sparkline(c.getValue()) },
    ],
  });
  let tableReady = false;
  const tableBuilt = new Promise(r => table.on('tableBuilt', () => { tableReady = true; r(); }));
  table.on('rowClick', (ev, row) => select(row.getData().id, { from: 'table', open: true }));
  table.on('rowDblClick', (ev, row) => select(row.getData().id, { from: 'table', locate: true }));
  table.on('dataFiltered', (filters, rows) => { $('#row-count').textContent = `${rows.length} rows`; });
  table.on('dataSorted', () => tableReady && markTableSelection());

  function refreshTable() {
    if (!tableReady) return;
    const match = queryMatcher();
    table.setFilter(e => passes(e, match) && inWindow(e));
  }
  function markTableSelection(scroll) {
    if (!tableReady) return;
    table.deselectRow();
    if (state.selected == null) return;
    const row = table.getRow(state.selected);
    if (!row || row.getPosition() === false) return;
    row.select();
    if (scroll) {
      table.scrollToRow(row, 'center', false).then(() => {
        const el = row.getElement(); el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash');
      }).catch(() => {});
    }
  }

  // Column chooser
  function buildColumnsMenu() {
    const menu = $('#columns-menu');
    menu.innerHTML = table.getColumns().filter(c => c.getDefinition().title).map(c =>
      `<label><input type="checkbox" data-field="${c.getField()}" ${c.isVisible() ? 'checked' : ''}>${esc(c.getDefinition().title)}</label>`).join('')
      + '<div class="menu-foot"><button id="cols-all">Show all</button><button id="cols-reset">Reset layout</button></div>';
  }
  $('#btn-columns').addEventListener('click', ev => {
    ev.stopPropagation(); const m = $('#columns-menu'); m.hidden = !m.hidden; if (!m.hidden) buildColumnsMenu();
  });
  $('#columns-menu').addEventListener('click', ev => ev.stopPropagation());
  $('#columns-menu').addEventListener('change', ev => {
    const f = ev.target.dataset.field; if (!f) return;
    ev.target.checked ? table.showColumn(f) : table.hideColumn(f);
  });
  $('#columns-menu').addEventListener('click', ev => {
    if (ev.target.id === 'cols-all') { table.getColumns().forEach(c => c.show()); buildColumnsMenu(); }
    if (ev.target.id === 'cols-reset') {
      Object.keys(localStorage).filter(k => k.startsWith('tabulator-flowdiagram-events')).forEach(k => localStorage.removeItem(k));
      location.reload();
    }
  });
  document.addEventListener('click', () => { $('#columns-menu').hidden = true; });
  $('#btn-clear-head').addEventListener('click', () => { table.clearHeaderFilter(); toast('Column filters cleared'); });
  $('#btn-export').addEventListener('click', () => table.download('csv', 'flow_events.csv'));
  $('#btn-export-json').addEventListener('click', () => table.download('json', 'flow_events.json'));

  // ---------- Network table ----------
  const NET_MAX = Math.max(1, ...NET.map(n => n.end));
  const netTable = new Tabulator('#net-table', {
    data: NET, index: 'id', layout: 'fitDataStretch', height: '100%', groupBy: 'domain', placeholder: 'No network requests',
    groupHeader: (value, count, data) => {
      const total = data.reduce((a, d) => a + (d.duration || 0), 0);
      return `${esc(value)}<span>${count} request${count === 1 ? '' : 's'} · ${fmt(total)} ms total</span>`;
    },
    initialSort: [{ column: 'start', dir: 'asc' }],
    columns: [
      { title: 'Status', field: 'status', width: 96, headerFilter: 'list', headerFilterParams: { valuesLookup: true, clearable: true },
        formatter: c => { const v = String(c.getValue()); return `<span class="${/^[23]/.test(v) ? 'status-ok' : 'status-bad'}">${esc(v)}</span>`; } },
      numCol('Start', 'start'), numCol('End', 'end'),
      numCol('Duration', 'duration'),
      { title: 'Waterfall', field: '_wf', width: 220, headerSort: false, download: false,
        formatter: c => { const d = c.getData(); return `<div class="wf"><span style="left:${(d.start / NET_MAX) * 100}%;width:${(((d.end - d.start) || 0) / NET_MAX) * 100}%"></span></div>`; } },
      { title: 'URL', field: 'url', minWidth: 320, width: 560, widthGrow: 3, headerFilter: 'input', headerFilterPlaceholder: 'filter…', tooltip: true },
      numCol('Runs', 'count', { width: 72 }),
    ],
  });
  netTable.on('rowClick', (ev, row) => select(row.getData().id, { open: true }));
  netTable.on('tableBuilt', () => {
    const total = NET.reduce((a, n) => a + (n.duration || 0), 0);
    $('#net-summary').textContent = `${NET.length} requests · ${new Set(NET.map(n => n.domain)).size} domains · ${fmt(total)} ms summed`;
  });
  let netCollapsed = false;
  $('#btn-net-collapse').addEventListener('click', ev => {
    netCollapsed = !netCollapsed;
    netTable.getGroups().forEach(g => (netCollapsed ? g.hide() : g.show()));
    ev.target.textContent = netCollapsed ? 'Expand all' : 'Collapse all';
  });
  $('#btn-net-export').addEventListener('click', () => netTable.download('csv', 'flow_network.csv'));

  // ---------- Details drawer ----------
  const drawer = $('#details');
  function openDetails() {
    const e = BY_ID.get(state.selected); if (!e) return;
    const s = stats(e);
    $('#d-kind').style.setProperty('--pc', kindColor(e.kind));
    $('#d-kind').textContent = `${KIND_LABEL[e.kind]} · ${e.type}${e.mode ? ' · ' + e.mode : ''}`;
    $('#d-msg').textContent = e.msg;
    const st = [['Time', ms(e.time)], ['Duration', isMarker(e) ? 'marker' : ms(e.duration)], ['Runs', e.count],
      ['Min', ms(e.min)], ['Max', ms(e.max)], ['Spread', ms(s.spread)], ['Median', ms(s.median)], ['σ', ms(s.sd)],
      ['Start', ms(e.start)]];
    $('#d-stats').innerHTML = st.map(([k, v]) => `<div class="stat"><div class="k">${k}</div><div class="v">${v}</div></div>`).join('');
    const svg = d3.select('#d-runs'), w = $('#d-runs').clientWidth || 360, h = 70;
    svg.selectAll('*').remove();
    const x = d3.scaleLinear().domain(s.spread ? [s.sorted[0], s.sorted[s.sorted.length - 1]] : [e.time - 1, e.time + 1]).range([14, w - 14]);
    svg.append('line').attr('class', 'axisline').attr('x1', 14).attr('x2', w - 14).attr('y1', 40).attr('y2', 40);
    svg.append('line').attr('class', 'avg').attr('x1', x(s.mean)).attr('x2', x(s.mean)).attr('y1', 18).attr('y2', 52);
    svg.selectAll('circle').data(e.all || []).join('circle').attr('cx', x).attr('cy', 40).attr('r', 0)
      .transition().delay((d, i) => i * 25).duration(300).attr('r', 5);
    svg.append('text').attr('x', 14).attr('y', 66).text(ms(x.domain()[0]));
    svg.append('text').attr('x', w - 14).attr('y', 66).attr('text-anchor', 'end').text(ms(x.domain()[1]));
    svg.append('text').attr('x', x(s.mean)).attr('y', 12).attr('text-anchor', 'middle').text(`avg ${ms(s.mean)}`);
    const runIds = (DATA.runs || []).map(r => r.run_id);
    $('#d-runs-list').innerHTML = (e.all || []).map((t, i) => `<span title="${esc(runIds[i] || '')}">${fmt(t)}</span>`).join('');
    drawer.classList.add('open'); drawer.setAttribute('aria-hidden', 'false');
  }
  function closeDetails() { drawer.classList.remove('open'); drawer.setAttribute('aria-hidden', 'true'); }
  $('#d-close').onclick = closeDetails;
  $('#d-prev').onclick = () => step(-1);
  $('#d-next').onclick = () => step(1);
  $('#d-locate').onclick = () => { if (state.view === 'table' || state.view === 'network') setView('split'); diagram.locate(state.selected); };
  $('#d-table').onclick = () => { if (state.view === 'diagram' || state.view === 'network') setView('split'); markTableSelection(true); };
  $('#d-copy').onclick = () => {
    const e = BY_ID.get(state.selected); if (!e) return;
    copy(`${e.msg}\ntime=${e.time}ms duration=${e.duration}ms kind=${KIND_LABEL[e.kind]} runs=${e.count} min=${e.min} max=${e.max}\nall: ${(e.all || []).join(' ')}`, 'Event copied');
  };

  // ---------- Selection (shared between diagram, table, network) ----------
  function select(id, opts = {}) {
    if (!BY_ID.has(id)) return;
    state.selected = id;
    const e = BY_ID.get(id);
    if (!visible.includes(e)) { state.kinds.add(e.kind); if (state.minDur > e.duration) state.minDur = 0; if (isMarker(e)) state.hideMarkers = false; if (state.q) state.q = ''; update(); }
    diagram.markSelected();
    if (opts.from !== 'diagram' && state.view !== 'table' && state.view !== 'network') diagram.scrollToRow(id);
    markTableSelection(opts.from !== 'table');
    if (opts.locate) { if (state.view === 'table' || state.view === 'network') setView('split'); diagram.locate(id); }
    if (opts.open || drawer.classList.contains('open')) openDetails();
    writeHash();
  }
  function step(dir) {
    if (!visible.length) return;
    const i = visible.findIndex(e => e.id === state.selected);
    const next = visible[i < 0 ? (dir > 0 ? 0 : visible.length - 1) : Math.min(visible.length - 1, Math.max(0, i + dir))];
    select(next.id, { from: 'keys' });
  }

  // ---------- Update loop ----------
  function update() {
    recompute(); syncControls(); diagram.render(); refreshTable(); writeHash();
  }
  const updateDebounced = debounce(update, 80);

  // ---------- Global buttons + keys ----------
  $('#btn-theme').onclick = () => applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
  $('#btn-help').onclick = () => $('#help').showModal();
  $('#btn-share').onclick = () => { writeHash(); setTimeout(() => copy(location.href, 'Link to this view copied'), 200); };
  document.addEventListener('keydown', ev => {
    const typing = /INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName);
    if (ev.key === 'Escape') {
      if (typing) { document.activeElement.blur(); return; }
      if (drawer.classList.contains('open')) closeDetails();
      else { state.selected = null; diagram.markSelected(); markTableSelection(); writeHash(); }
      return;
    }
    if (typing || ev.metaKey || ev.ctrlKey || ev.altKey) return;
    const k = ev.key;
    if (k === '/') { ev.preventDefault(); $('#search').focus(); $('#search').select(); }
    else if (k === 'j' || k === 'ArrowDown') { ev.preventDefault(); step(1); }
    else if (k === 'k' || k === 'ArrowUp') { ev.preventDefault(); step(-1); }
    else if (k === 'Enter') openDetails();
    else if (k === '+' || k === '=') diagram.zoomIn();
    else if (k === '-' || k === '_') diagram.zoomOut();
    else if (k === '0') diagram.fit();
    else if (k === 'z') $('#zoom-sel').click();
    else if (k === 't') $('#btn-theme').click();
    else if (k === '?') $('#help').showModal();
    else if ('1234'.includes(k)) setView(['split', 'diagram', 'table', 'network'][+k - 1]);
  });

  // ---------- Boot ----------
  recompute(); syncControls(); setView(state.view);
  requestAnimationFrame(() => { diagram.resize(); diagram.restore(); });
  tableBuilt.then(() => {
    refreshTable();
    if (state.selected != null) { select(state.selected, {}); setTimeout(() => markTableSelection(true), 300); }
  });
  if (DATA.failures && DATA.failures.length) toast(`${DATA.failures.length} run(s) failed and are not included`);
})();
