// Prize Custom Card Vault — static rebuild. No framework, no external services.
(function () {
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  function toast(msg) {
    var t = $('.toast') || document.body.appendChild(Object.assign(document.createElement('div'), { className: 'toast' }));
    t.textContent = msg; t.classList.add('show'); clearTimeout(t._h);
    t._h = setTimeout(function () { t.classList.remove('show'); }, 1600);
  }

  // Gallery rarity filters (ALL / UR / SSR)
  $$('[data-filters]').forEach(function (bar) {
    var grid = document.getElementById(bar.getAttribute('data-filters'));
    var count = $('[data-count]', bar.parentNode);
    $$('button', bar).forEach(function (b) {
      b.addEventListener('click', function () {
        var f = b.getAttribute('data-filter'), n = 0;
        $$('button', bar).forEach(function (x) { x.classList.toggle('on', x === b); });
        $$('.tile', grid).forEach(function (t) {
          var show = f === 'ALL' || t.getAttribute('data-rarity') === f;
          t.classList.toggle('hidden', !show); if (show) n++;
        });
        if (count) count.textContent = n + ' cards';
      });
    });
  });

  // Tilt + foil shine on gallery tiles (pointer devices only)
  if (window.matchMedia('(hover: hover)').matches) {
    $$('.tile').forEach(function (t) {
      t.addEventListener('pointermove', function (e) {
        var r = t.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
        t.style.transform = 'rotateX(' + ((0.5 - y) * 10).toFixed(2) + 'deg) rotateY(' + ((x - 0.5) * 12).toFixed(2) + 'deg) translateZ(6px)';
        t.style.setProperty('--sx', (x * 100) + '%'); t.style.setProperty('--sy', (y * 100) + '%');
      });
      t.addEventListener('pointerleave', function () { t.style.transform = ''; });
    });
  }

  // Shop tabs: /shop?kind=sports | /shop?kind=game
  var shop = $('[data-shop]');
  if (shop) {
    var kind = new URLSearchParams(location.search).get('kind') === 'game' ? 'game' : 'sports';
    $$('[data-kind-panel]').forEach(function (p) { p.classList.toggle('hidden', p.getAttribute('data-kind-panel') !== kind); });
    $$('[data-kind-tab]').forEach(function (a) { a.classList.toggle('on', a.getAttribute('data-kind-tab') === kind); });
    $$('[data-kind-text]').forEach(function (el) { el.textContent = el.getAttribute('data-' + kind); });
    if (kind === 'game') document.title = 'Shop game cards · Prize Custom Card Vault';
  }

  // NFC page: copy + search
  $$('[data-copy]').forEach(function (b) {
    b.addEventListener('click', function () {
      var v = b.getAttribute('data-copy');
      (navigator.clipboard ? navigator.clipboard.writeText(v) : Promise.reject()).then(function () { toast('Copied ' + v); }, function () {
        var ta = document.createElement('textarea'); ta.value = v; document.body.appendChild(ta); ta.select();
        try { document.execCommand('copy'); toast('Copied ' + v); } catch (e) { prompt('Copy this URL', v); }
        ta.remove();
      });
    });
  });
  var q = $('[data-search]');
  if (q) q.addEventListener('input', function () {
    var v = q.value.trim().toLowerCase();
    $$('#nfc-list li').forEach(function (li) { li.classList.toggle('hidden', v && li.textContent.toLowerCase().indexOf(v) < 0); });
  });

  // Card page: drag-to-turn 3D plate, flip, reset, 2D, living reel, fullscreen
  var card = $('.card3d');
  if (card) {
    var scene = $('.scene'), stage = $('.stage'), rx = 0, ry = 0, flipped = false, drag = null, lastTap = 0;
    function apply() { card.style.transform = 'rotateX(' + rx.toFixed(1) + 'deg) rotateY(' + (ry + (flipped ? 180 : 0)).toFixed(1) + 'deg)'; }
    function reset() { rx = 0; ry = 0; flipped = false; apply(); }
    scene.addEventListener('pointerdown', function (e) {
      if (e.target.closest('button,a')) return;
      drag = { x: e.clientX, y: e.clientY, rx: rx, ry: ry }; card.classList.add('dragging'); scene.setPointerCapture(e.pointerId);
      var now = Date.now(); if (now - lastTap < 300) { card.classList.remove('dragging'); reset(); drag = null; } lastTap = now;
    });
    scene.addEventListener('pointermove', function (e) {
      var r = card.getBoundingClientRect();
      card.style.setProperty('--sx', ((e.clientX - r.left) / r.width * 100) + '%');
      card.style.setProperty('--sy', ((e.clientY - r.top) / r.height * 100) + '%');
      if (!drag) return;
      ry = drag.ry + (e.clientX - drag.x) * 0.45; rx = Math.max(-35, Math.min(35, drag.rx - (e.clientY - drag.y) * 0.3)); apply();
    });
    function end() {
      if (!drag) return; drag = null; card.classList.remove('dragging');
      // settle to nearest face
      var total = ry + (flipped ? 180 : 0), n = Math.round(total / 180);
      flipped = Math.abs(n) % 2 === 1; ry = n * 180 - (flipped ? 180 : 0); rx = 0; apply();
    }
    scene.addEventListener('pointerup', end); scene.addEventListener('pointercancel', end);
    function on(sel, fn) { var b = $(sel); if (b) b.addEventListener('click', fn); }
    on('[data-act=flip]', function () { flipped = !flipped; apply(); });
    on('[data-act=reset]', reset);
    on('[data-act=hint]', reset);
    on('[data-act=d3]', function () { reset(); });
    on('[data-act=d2]', function () {
      var lb = document.createElement('div'); lb.className = 'lightbox fit';
      var src = flipped ? card.getAttribute('data-back') : card.getAttribute('data-front');
      lb.innerHTML = '<img alt="" src="' + src + '"><button class="icon-btn close btn" aria-label="Close">✕</button>';
      lb.addEventListener('click', function (e) {
        if (e.target.tagName === 'IMG') { lb.classList.toggle('fit'); return; }
        lb.remove();
      });
      document.body.appendChild(lb);
    });
    on('[data-act=reel]', function () {
      var v = $('video', stage), b = $('[data-act=reel]'), onNow = !stage.classList.contains('reel');
      stage.classList.toggle('reel', onNow); b.setAttribute('aria-pressed', onNow);
      if (onNow) { v.play().catch(function () {}); } else { v.pause(); }
    });
    // Full screen: plays the card's living reel (muted, looping, inline for iPhone) in a full-screen
    // player; cards without a reel show the plate image full screen. Native fullscreen where the
    // browser allows it on an element (desktop, Android, iPad); a fixed full-viewport overlay on iPhone.
    var fsv = null;
    function fsEl() { return document.fullscreenElement || document.webkitFullscreenElement || null; }
    function closeFs() {
      if (!fsv) return;
      var o = fsv; fsv = null;
      var v = $('video', o); if (v) { v.pause(); v.removeAttribute('src'); v.load(); }
      if (fsEl() === o) { (document.exitFullscreen || document.webkitExitFullscreen).call(document); }
      o.remove(); document.body.classList.remove('fs-open');
      var b = $('[data-act=fs]'); if (b) b.focus({ preventScroll: true });
    }
    function openFs() {
      if (fsv) return closeFs();
      var b = $('[data-act=fs]'), reel = b.getAttribute('data-reel'), name = card.getAttribute('data-name') || '';
      var o = document.createElement('div');
      o.className = 'fsv' + (reel ? ' has-reel' : '');
      o.setAttribute('role', 'dialog'); o.setAttribute('aria-modal', 'true');
      o.setAttribute('aria-label', name + (reel ? ' — living reel' : ' — full screen'));
      var media;
      if (reel) {
        media = document.createElement('video');
        media.muted = true; media.defaultMuted = true; media.loop = true; media.autoplay = true; media.playsInline = true;
        ['muted', 'loop', 'autoplay', 'playsinline', 'webkit-playsinline'].forEach(function (a) { media.setAttribute(a, ''); });
        media.setAttribute('preload', 'auto'); media.setAttribute('poster', card.getAttribute('data-front'));
        media.setAttribute('disablepictureinpicture', ''); media.setAttribute('aria-label', name + ' living reel');
        media.src = reel;
      } else {
        media = document.createElement('img'); media.alt = name;
        media.src = flipped ? card.getAttribute('data-back') : card.getAttribute('data-front');
      }
      media.className = 'fsv-media';
      var close = document.createElement('button');
      close.type = 'button'; close.className = 'icon-btn fsv-close'; close.setAttribute('aria-label', 'Close full screen'); close.textContent = '✕';
      close.addEventListener('click', function (e) { e.stopPropagation(); closeFs(); });
      var cap = document.createElement('p'); cap.className = 'fsv-cap';
      cap.textContent = (reel ? 'Living reel · ' : '') + name;
      o.appendChild(media); o.appendChild(close); o.appendChild(cap);
      o.addEventListener('click', function (e) { if (e.target === o) closeFs(); });
      document.body.appendChild(o); document.body.classList.add('fs-open'); fsv = o;
      if (reel) { var pr = media.play(); if (pr && pr.catch) pr.catch(function () {}); }
      var req = o.requestFullscreen || o.webkitRequestFullscreen;
      if (req) { try { var r = req.call(o); if (r && r.catch) r.catch(function () {}); } catch (err) {} }
      close.focus({ preventScroll: true });
    }
    function onFsChange() { if (fsv && !fsEl()) closeFs(); }
    document.addEventListener('fullscreenchange', onFsChange);
    document.addEventListener('webkitfullscreenchange', onFsChange);
    on('[data-act=fs]', openFs);
    var dock = $('.dock');
    on('[data-act=details]', function () {
      var closed = dock.classList.toggle('closed'), b = $('[data-act=details]');
      b.setAttribute('aria-expanded', !closed); $('span', b).textContent = closed ? 'Show details' : 'Hide details'; setTimeout(fitDock, 320);
    });
    document.addEventListener('keydown', function (e) {
      if (fsv) { if (e.key === 'Escape') closeFs(); return; }
      if (e.key === 'f') { flipped = !flipped; apply(); }
      if (e.key === 'Escape') { var lb = $('.lightbox'); if (lb) lb.remove(); }
    });
    function fitDock() {
      var h = dock.classList.contains('closed') ? 60 : dock.offsetHeight - 40;
      scene.style.setProperty('--dock', Math.max(0, h) + 'px');
    }
    if (window.ResizeObserver) new ResizeObserver(fitDock).observe(dock); else window.addEventListener('resize', fitDock);
    fitDock();
    apply();
  }
})();

// Stats tab (sports cards): renders /data/stats/{slug}.json client-side
(function () {
  var tabs = document.querySelector('.viewtabs'), panel = document.getElementById('stats');
  if (!tabs || !panel) return;
  var loaded = false;
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function show(view, push) {
    var stats = view === 'stats';
    tabs.querySelectorAll('button').forEach(function (b) { b.setAttribute('aria-selected', b.getAttribute('data-view') === view); });
    panel.hidden = !stats;
    if (stats && !loaded) load();
    if (push !== false) history.replaceState(null, '', stats ? '#stats' : location.pathname + location.search);
  }
  tabs.addEventListener('click', function (e) { var b = e.target.closest('button[data-view]'); if (b) show(b.getAttribute('data-view')); });
  window.addEventListener('hashchange', function () { show(location.hash === '#stats' ? 'stats' : 'card', false); });
  var REASON = {
    'multi-player': 'This card features several players, so there’s no single stat line to show.',
    'coach': 'This card honors a coach — player stats don’t apply.',
    'executive': 'This card honors a front-office executive — player stats don’t apply.',
    'no-stats-yet': 'No regular-season stats have been recorded yet. Check back after game day.',
    'no-confident-match': 'We’re confirming this player’s record before showing numbers.',
    'no-source': 'We’re still lining up a reliable stats source for this athlete.'
  };
  function fmtDate(iso) {
    try { return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }); } catch (e) { return iso; }
  }
  function soon(d) {
    var r = (d && REASON[d.reason]) || 'Stats for this card are on the way.';
    return '<div class="st-soon"><p class="eyebrow">Stats</p><h2>Stats coming soon</h2><p>' + esc(r) + '</p>' +
      (d && d.updated ? '<p class="st-foot" style="border:0">Checked ' + esc(fmtDate(d.updated)) + '</p>' : '') + '</div>';
  }
  function table(g, curYear) {
    var plain = g.plain, h = '<div class="tbl"><table><thead><tr>' + (plain ? '' : '<th>Season</th><th>Team</th>') +
      g.columns.map(function (c) { return '<th>' + esc(c) + '</th>'; }).join('') + '</tr></thead><tbody>';
    g.rows.forEach(function (r) {
      h += '<tr' + (!plain && r.year === curYear ? ' class="cur"' : '') + '>' + (plain ? '<td>' + esc(r.season) + '</td>' : '<td>' + esc(r.season) + '</td><td>' + esc(r.team) + '</td>') +
        r.stats.map(function (v) { return '<td>' + esc(v) + '</td>'; }).join('') + '</tr>';
    });
    if (g.career) h += '<tr class="career"><td>' + esc(g.careerLabel || 'Career') + '</td>' + (plain ? '' : '<td></td>') +
      g.career.map(function (v) { return '<td>' + esc(v) + '</td>'; }).join('') + '</tr>';
    return h + '</tbody></table></div>';
  }
  function render(d) {
    if (!d || d.status !== 'ok' || !d.groups || !d.groups.length) { panel.firstElementChild.innerHTML = soon(d); return; }
    var p = d.player || {}, cs = d.currentSeason || {};
    var meta = [p.team, p.position, p.jersey ? '#' + p.jersey : ''].filter(Boolean).join(' · ');
    var h = '<div class="st-head"><div><p class="eyebrow">Player stats</p><h2>' + esc(p.name || d.card) + '</h2><p class="meta">' + esc(meta) + '</p></div>' +
      '<span class="st-league">' + esc(d.league || '') + '</span></div>';
    // current season (or latest completed season if the new one hasn't started)
    var g0 = d.groups.filter(function (g) { return !g.plain; })[0] || d.groups[0], vals = g0.current, label;
    if (vals) label = cs.label + ' season';
    else if (g0.rows.length && !g0.plain) { var last = g0.rows[g0.rows.length - 1]; vals = last.stats; label = 'Latest season · ' + last.season + (cs.label ? ' (' + cs.label + ' not started or no games yet)' : ''); }
    if (vals) {
      h += '<div class="st-now"><h3>' + esc(label) + ' · ' + esc(g0.title) + '</h3><div class="tiles">' +
        g0.columns.slice(0, 8).map(function (c, i) { return '<div><b>' + esc(vals[i]) + '</b><span>' + esc(c) + '</span></div>'; }).join('') + '</div></div>';
    }
    d.groups.forEach(function (g) {
      h += '<div class="st-block"><h3>' + esc(g.title) + (g.plain ? '' : ' · season by season') + '</h3>' + table(g, cs.year) + '</div>';
    });
    var src = d.source || {};
    h += '<div class="st-foot">' + (d.note ? esc(d.note) + '<br>' : '') + 'Last updated ' + esc(fmtDate(d.updated)) + ' · Source: ' +
      (src.url ? '<a href="' + esc(src.url) + '" rel="noopener nofollow" target="_blank">' + esc(src.name) + '</a>' : esc(src.name || '')) +
      '. Regular season only. Unofficial; stats refresh daily and may lag live games.</div>';
    panel.firstElementChild.innerHTML = h;
  }
  function load() {
    loaded = true;
    fetch(panel.getAttribute('data-src'), { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(render).catch(function () { loaded = false; panel.firstElementChild.innerHTML = soon(null); });
  }
  if (location.hash === '#stats') show('stats', false);
})();

// Featured promo strip: click → fullscreen player (with audio + controls; same overlay pattern as living reels)
(function () {
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var fsv = null;
  function fsEl() { return document.fullscreenElement || document.webkitFullscreenElement || null; }
  function closeFs() {
    if (!fsv) return;
    var o = fsv; fsv = null;
    var v = $('video', o); if (v) { v.pause(); v.removeAttribute('src'); v.load(); }
    if (fsEl() === o) { (document.exitFullscreen || document.webkitExitFullscreen).call(document); }
    o.remove(); document.body.classList.remove('fs-open');
  }
  function openPromo(btn) {
    if (fsv) closeFs();
    var src = btn.getAttribute('data-promo-src');
    if (!src) return;
    var poster = btn.getAttribute('data-promo-poster') || '';
    var title = btn.getAttribute('data-promo-title') || 'Promo';
    var sub = btn.getAttribute('data-promo-sub') || 'Promo';
    var o = document.createElement('div');
    o.className = 'fsv has-reel has-promo';
    o.setAttribute('role', 'dialog'); o.setAttribute('aria-modal', 'true');
    o.setAttribute('aria-label', title + ' — ' + sub);
    var media = document.createElement('video');
    media.className = 'fsv-media';
    media.controls = true; media.playsInline = true; media.autoplay = true;
    ['controls', 'playsinline', 'webkit-playsinline', 'autoplay'].forEach(function (a) { media.setAttribute(a, ''); });
    media.setAttribute('preload', 'auto');
    if (poster) media.setAttribute('poster', poster);
    media.setAttribute('aria-label', title + ' promo');
    media.src = src;
    var close = document.createElement('button');
    close.type = 'button'; close.className = 'icon-btn fsv-close'; close.setAttribute('aria-label', 'Close'); close.textContent = '✕';
    close.addEventListener('click', function (e) { e.stopPropagation(); closeFs(); });
    var cap = document.createElement('p'); cap.className = 'fsv-cap';
    cap.textContent = sub + ' · ' + title;
    o.appendChild(media); o.appendChild(close); o.appendChild(cap);
    o.addEventListener('click', function (e) { if (e.target === o) closeFs(); });
    document.body.appendChild(o); document.body.classList.add('fs-open'); fsv = o;
    var pr = media.play(); if (pr && pr.catch) pr.catch(function () {});
    var req = o.requestFullscreen || o.webkitRequestFullscreen;
    if (req) { try { var r = req.call(o); if (r && r.catch) r.catch(function () {}); } catch (err) {} }
    close.focus({ preventScroll: true });
  }
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-promo-src]');
    if (btn) openPromo(btn);
  });
  document.addEventListener('keydown', function (e) { if (fsv && e.key === 'Escape') closeFs(); });
  document.addEventListener('fullscreenchange', function () { if (fsv && !fsEl()) closeFs(); });
  document.addEventListener('webkitfullscreenchange', function () { if (fsv && !fsEl()) closeFs(); });
})();
