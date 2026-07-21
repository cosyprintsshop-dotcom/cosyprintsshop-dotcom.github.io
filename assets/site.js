/* ============================================================================
   Cosy Prints — shared page behaviour (loaded on index / boutique / engagement)
   ----------------------------------------------------------------------------
   1. Cart drawer — in-memory intent capture, not a checkout. Items collect in
      the drawer; "checkout" hands over to Vinted where payment actually
      happens. No localStorage on purpose (GitHub Pages iframes restrict it,
      and the cart is a showcase).
   2. Impact figures — 20% of the cart funds ocean plastic removal at an
      estimated 15 g of plastic per euro donated, i.e. total × 3 g.
   3. Count-up — animates [data-countup] numbers when scrolled into view.
      Skipped entirely under prefers-reduced-motion (the HTML already holds
      the final number, so no-JS and reduced-motion both read correctly).

   The drawer markup is injected here (single source for all pages) BEFORE the
   i18n layer initialises, so its data-i18n nodes are captured like static
   HTML. Dynamic strings (count, total, grams) come from the S dictionary
   below and re-render on the cp:langchange event.
   ========================================================================== */
(function () {
  'use strict';

  var L = function () { return document.documentElement.getAttribute('lang') === 'en' ? 'en' : 'fr'; };

  /* Dynamic (JS-rendered) strings only — static drawer text uses data-i18n. */
  var S = {
    fr: {
      one: 'article', many: 'articles',
      plastic: '≈ <b>{g} g</b> de plastique retiré des océans',
      remove: 'Retirer'
    },
    en: {
      one: 'item', many: 'items',
      plastic: '≈ <b>{g} g</b> of ocean plastic removed',
      remove: 'Remove'
    }
  };
  var s = function (k) { return S[L()][k] != null ? S[L()][k] : S.fr[k]; };

  var esc = function (v) {
    return String(v).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  };
  var fmtPrice = function (n) {
    return n.toLocaleString(L() === 'en' ? 'en-IE' : 'fr-FR',
      { style: 'currency', currency: 'EUR', minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  /* Icons: Lucide paths (ISC) inlined — no runtime, no CDN. */
  var svg = function (paths) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + paths + '</svg>';
  };
  var I_X = svg('<path d="M18 6 6 18M6 6l12 12"/>');
  var I_WAVES = svg('<path d="M2 6c.6.5 1.2 1 2.5 1C7 7 7 5 9.5 5c2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/><path d="M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>');
  var I_HEART = svg('<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>');

  /* ------------------------------ Drawer markup --------------------------- */
  document.body.insertAdjacentHTML('beforeend',
    '<div class="cart-scrim" data-cart-close></div>' +
    '<aside class="cart-drawer" id="cartDrawer" role="dialog" aria-modal="true" ' +
      'aria-label="Panier" data-i18n-attr="aria-label:cart.aria">' +
      '<div class="cart-drawer__head">' +
        '<h2 class="cart-drawer__title" data-i18n="cart.title">Ton panier</h2>' +
        '<span class="cart-drawer__count" data-cart-drawer-count aria-live="polite"></span>' +
        '<button class="cart-drawer__close" type="button" data-cart-close ' +
          'aria-label="Fermer le panier" data-i18n-attr="aria-label:cart.close_aria">' + I_X + '</button>' +
      '</div>' +
      '<div class="cart-items">' +
        '<p class="cart-empty" data-cart-empty data-i18n="cart.empty">Ton panier est vide. Chaque pièce est fabriquée rien que pour toi.</p>' +
        '<ul class="cart-list" data-cart-list hidden></ul>' +
      '</div>' +
      '<div class="cart-impact">' +
        '<p class="cart-impact__title" data-i18n="cart.impact_title">Ton impact</p>' +
        '<p class="cart-impact__row" data-cart-hint>' + I_WAVES +
          '<span data-i18n="cart.impact_hint">Commence tes achats pour suivre ton impact.</span></p>' +
        '<p class="cart-impact__row" data-cart-row-plastic hidden>' + I_WAVES +
          '<span data-cart-plastic></span></p>' +
        '<p class="cart-impact__row" data-cart-row-cancer hidden>' + I_HEART +
          '<span data-i18n="cart.impact_cancer">Soutien à la recherche contre le cancer</span></p>' +
      '</div>' +
      '<div class="cart-foot" data-cart-foot hidden>' +
        '<p class="cart-total"><span data-i18n="cart.total">Total</span><b data-cart-total></b></p>' +
        '<a class="btn btn--accent" href="https://www.vinted.fr/member/60879390-cosyprints" target="_blank" rel="noopener">' +
          '<span data-i18n="cart.checkout">Finaliser sur Vinted</span> <span aria-hidden="true">↗</span></a>' +
        '<p class="cart-note" data-i18n="cart.note">Paiement protégé via Vinted ou Leboncoin.</p>' +
      '</div>' +
    '</aside>');

  var drawer = document.getElementById('cartDrawer');
  var scrim = document.querySelector('.cart-scrim');
  var q = function (sel) { return drawer.querySelector(sel); };

  var items = [];       // { id, name, price, url } — in-memory only, by design
  var lastFocus = null;
  var isOpen = false;

  /* ------------------------------ Rendering ------------------------------- */
  function render() {
    var n = items.length;
    var total = items.reduce(function (sum, it) { return sum + (it.price || 0); }, 0);
    var grams = Math.round(total * 0.20 * 15);

    document.querySelectorAll('[data-cart-count]').forEach(function (el) {
      el.textContent = n;
    });

    q('[data-cart-drawer-count]').textContent = n === 0 ? '' : n + ' ' + (n > 1 ? s('many') : s('one'));
    q('[data-cart-empty]').hidden = n > 0;

    var list = q('[data-cart-list]');
    list.hidden = n === 0;
    list.innerHTML = items.map(function (it) {
      return '<li class="cart-item">' +
        '<span class="cart-item__name">' + esc(it.name) + '</span>' +
        '<span class="cart-item__price">' + (it.price != null ? fmtPrice(it.price) : '') + '</span>' +
        '<button class="cart-item__rm" type="button" data-cart-rm="' + esc(it.id) + '">' + esc(s('remove')) + '</button>' +
      '</li>';
    }).join('');

    q('[data-cart-hint]').hidden = n > 0;
    q('[data-cart-row-plastic]').hidden = n === 0;
    q('[data-cart-row-cancer]').hidden = n === 0;
    if (n > 0) q('[data-cart-plastic]').innerHTML = s('plastic').replace('{g}', grams);

    q('[data-cart-foot]').hidden = n === 0;
    if (n > 0) q('[data-cart-total]').textContent = fmtPrice(total);
  }

  /* ------------------------- Open / close + focus trap -------------------- */
  function open() {
    if (isOpen) return;
    isOpen = true;
    lastFocus = document.activeElement;
    drawer.classList.add('is-open');
    scrim.classList.add('is-open');
    document.body.style.overflow = 'hidden';
    q('.cart-drawer__close').focus();
  }
  function close() {
    if (!isOpen) return;
    isOpen = false;
    drawer.classList.remove('is-open');
    scrim.classList.remove('is-open');
    document.body.style.overflow = '';
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  document.addEventListener('keydown', function (e) {
    if (!isOpen) return;
    if (e.key === 'Escape') { close(); return; }
    if (e.key !== 'Tab') return;
    var f = Array.prototype.filter.call(
      drawer.querySelectorAll('button, a[href], input, select, [tabindex]:not([tabindex="-1"])'),
      function (el) { return el.offsetParent !== null && !el.hidden; });
    if (!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    else if (!drawer.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
  });

  document.addEventListener('click', function (e) {
    if (e.target.closest('[data-cart-open]')) { open(); return; }
    if (e.target.closest('[data-cart-close]')) { close(); return; }
    var rm = e.target.closest('[data-cart-rm]');
    if (rm) {
      items = items.filter(function (it) { return String(it.id) !== rm.getAttribute('data-cart-rm'); });
      render();
      q('.cart-drawer__close').focus();
    }
  });

  document.addEventListener('cp:langchange', render);
  render();

  window.CosyCart = {
    add: function (item) {
      if (!item || item.id == null) return;
      if (!items.some(function (it) { return it.id === item.id; })) {
        items.push(item);
        render();
      }
      open();
    },
    open: open
  };

  /* --------------------------- Count-up enhancer -------------------------- */
  (function () {
    var els = document.querySelectorAll('[data-countup]');
    if (!els.length || !('IntersectionObserver' in window)) return;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        io.unobserve(en.target);
        var el = en.target;
        var target = parseInt(el.getAttribute('data-countup'), 10) || 0;
        var t0 = null, dur = 900;
        var step = function (ts) {
          if (t0 === null) t0 = ts;
          var p = Math.min(1, (ts - t0) / dur);
          p = 1 - Math.pow(1 - p, 3); /* ease-out cubic */
          el.textContent = Math.round(target * p);
          if (p < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
      });
    }, { threshold: 0.4 });
    els.forEach(function (el) { io.observe(el); });
  })();
})();

/* ==========================================================================
   Shared page behaviour — consolidated here so index/boutique/engagement no
   longer duplicate these IIFEs inline. Each one guards for the elements it
   needs, so it is a silent no-op on any page that lacks them. site.js loads on
   every page (before the i18n layer), which is why this is the right home.
   ========================================================================== */

/* Reveal on scroll — calm, once per element. */
(function () {
  if (!('IntersectionObserver' in window)) {
    document.querySelectorAll('.reveal').forEach(function (e) { e.classList.add('in'); });
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
  }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
  document.querySelectorAll('.reveal').forEach(function (e) { io.observe(e); });
})();

/* Mobile menu drawer. */
(function () {
  var btn = document.getElementById('menuBtn');
  var nav = document.getElementById('mobileNav');
  if (!btn || !nav) return;
  var setOpen = function (open) {
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    btn.setAttribute('aria-label', open ? 'Fermer le menu' : 'Ouvrir le menu');
    nav.classList.toggle('is-open', open);
  };
  btn.addEventListener('click', function () { setOpen(btn.getAttribute('aria-expanded') !== 'true'); });
  nav.querySelectorAll('a').forEach(function (a) { a.addEventListener('click', function () { setOpen(false); }); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setOpen(false); });
})();

/* Newsletter — no backend yet (Phase 2). Falls back to a prefilled email. */
(function () {
  var form = document.getElementById('newsForm');
  var note = document.getElementById('newsNote');
  if (!form) return;
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var email = document.getElementById('newsEmail').value.trim();
    if (!email || email.indexOf('@') === -1) { document.getElementById('newsEmail').focus(); return; }
    var en = document.documentElement.getAttribute('lang') === 'en';
    var subject = encodeURIComponent(en ? 'Newsletter sign-up' : 'Inscription newsletter');
    var body = encodeURIComponent((en ? 'Please add me to the list: ' : 'Ajoutez-moi à la liste : ') + email);
    window.location.href = 'mailto:cosyprints.shop@gmail.com?subject=' + subject + '&body=' + body;
    if (note) note.textContent = en ? 'Opening your email app…' : 'Ouverture de ta messagerie…';
  });
})();
