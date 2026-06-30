/* ============================================================================
   Cosy Prints — lightweight bilingual layer (FR source, EN secondary)
   ----------------------------------------------------------------------------
   How it works, kept deliberately simple so the site stays a no-build static
   site on GitHub Pages:

   • French is the source language and lives directly in the HTML. That keeps
     the page meaningful with JavaScript disabled and gives Google real French
     content to index (no client-only French).
   • English strings live in a dictionary (window.CP_EN, loaded from
     assets/i18n.en.js). Only the *English* copy is duplicated — never French.
   • Translatable nodes are tagged with data-i18n="key". On first run we capture
     each node's original French markup as the baseline, so switching back to FR
     restores the exact source. Switching to EN swaps in window.CP_EN[key].
   • Attributes (aria-label, title, alt, placeholder…) use
     data-i18n-attr="aria-label:key; title:key".
   • <title> and <meta name="description"> follow the keys meta.title /
     meta.description when present in the dictionary.

   Locale resolution order: ?lang= → localStorage → <html lang> → 'fr'.
   ========================================================================== */
(function () {
  var DEFAULT = 'fr';
  var SUPPORTED = ['fr', 'en'];
  var dict = { fr: {}, en: window.CP_EN || {} };

  // Runtime baseline captured from the source HTML (French). Filled on first apply.
  var baseText = {};   // key -> original innerHTML
  var baseAttr = {};   // "key|attr" -> original attribute value
  var captured = false;

  function supported(l) { return SUPPORTED.indexOf(l) !== -1; }

  function resolve() {
    try {
      var q = new URLSearchParams(location.search).get('lang');
      if (supported(q)) return q;
    } catch (e) {}
    try {
      var s = localStorage.getItem('lang');
      if (supported(s)) return s;
    } catch (e) {}
    var h = document.documentElement.getAttribute('lang');
    return supported(h) ? h : DEFAULT;
  }

  // Capture the French source once, so 'fr' is always restorable from the DOM.
  function capture() {
    if (captured) return;
    captured = true;
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var key = el.getAttribute('data-i18n');
      if (!(key in baseText)) baseText[key] = el.innerHTML;
    });
    document.querySelectorAll('[data-i18n-attr]').forEach(function (el) {
      el.getAttribute('data-i18n-attr').split(';').forEach(function (pair) {
        var bits = pair.split(':');
        var attr = (bits[0] || '').trim();
        var key = (bits[1] || '').trim();
        if (!attr || !key) return;
        var id = key + '|' + attr;
        if (!(id in baseAttr)) baseAttr[id] = el.getAttribute(attr) || '';
      });
    });
  }

  // Return the string for (lang, key): EN from the dictionary, FR from baseline.
  function str(lang, key) {
    if (lang === 'en') return (dict.en[key] != null) ? dict.en[key] : baseText[key];
    return baseText[key];
  }

  function apply(lang, relight) {
    capture();
    var root = document.documentElement;
    root.setAttribute('lang', lang);

    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var v = str(lang, el.getAttribute('data-i18n'));
      if (v != null && el.innerHTML !== v) el.innerHTML = v;
    });

    document.querySelectorAll('[data-i18n-attr]').forEach(function (el) {
      el.getAttribute('data-i18n-attr').split(';').forEach(function (pair) {
        var bits = pair.split(':');
        var attr = (bits[0] || '').trim();
        var key = (bits[1] || '').trim();
        if (!attr || !key) return;
        var v = (lang === 'en' && dict.en[key] != null) ? dict.en[key] : baseAttr[key + '|' + attr];
        if (v != null) el.setAttribute(attr, v);
      });
    });

    // Update the language toggle to advertise the *other* language.
    document.querySelectorAll('[data-lang-toggle]').forEach(function (btn) {
      btn.setAttribute('aria-label', lang === 'fr' ? 'Switch to English' : 'Passer en français');
      var code = btn.querySelector('.lang-code');
      if (code) code.textContent = (lang === 'fr' ? 'EN' : 'FR');
      btn.setAttribute('aria-pressed', lang === 'en' ? 'true' : 'false');
    });

    // The headline marker (.hl) reveals via IntersectionObserver at load; after a
    // runtime language swap its node is replaced, so re-light it directly.
    if (relight) {
      document.querySelectorAll('.hl').forEach(function (e) { e.classList.add('is-lit'); });
    }

    try { localStorage.setItem('lang', lang); } catch (e) {}
    document.dispatchEvent(new CustomEvent('cp:langchange', { detail: { lang: lang } }));
  }

  function setLang(lang) {
    if (!supported(lang)) return;
    apply(lang, true);
    try {
      var u = new URL(location.href);
      if (lang === DEFAULT) u.searchParams.delete('lang');
      else u.searchParams.set('lang', lang);
      history.replaceState(null, '', u);
    } catch (e) {}
  }

  window.CosyI18n = { setLang: setLang, current: function () { return document.documentElement.getAttribute('lang'); } };

  function init() {
    apply(resolve(), false);
    document.querySelectorAll('[data-lang-toggle]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        setLang(document.documentElement.getAttribute('lang') === 'fr' ? 'en' : 'fr');
      });
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
