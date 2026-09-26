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
    on('[data-act=fs]', function () {
      var el = document.documentElement;
      if (document.fullscreenElement) document.exitFullscreen(); else if (el.requestFullscreen) el.requestFullscreen();
    });
    var dock = $('.dock');
    on('[data-act=details]', function () {
      var closed = dock.classList.toggle('closed'), b = $('[data-act=details]');
      b.setAttribute('aria-expanded', !closed); $('span', b).textContent = closed ? 'Show details' : 'Hide details'; setTimeout(fitDock, 320);
    });
    document.addEventListener('keydown', function (e) {
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
