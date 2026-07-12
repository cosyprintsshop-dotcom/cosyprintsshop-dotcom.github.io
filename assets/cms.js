/* ============================================================================
   CMS render layer
   ----------------------------------------------------------------------------
   Fills the CMS-driven pieces of the static pages from window.CP_CONTENT
   (generated from Sanity into assets/content.js) and window.CP_PRODUCTS.
   Handles two things editors change often:
     • donation / impact numbers   [data-cms="impact.*"]
     • the homepage featured grid   #featured
   Everything else (hero, headings, FAQ copy) stays in the bilingual i18n layer.
   No-op when CP_CONTENT is absent, so pages still render their static fallback.
   Re-runs on language toggle (cp:langchange) so formatting follows the locale.
   ========================================================================== */
(function () {
  var C = window.CP_CONTENT;
  if (!C) return;

  function isEn() { return document.documentElement.getAttribute('lang') === 'en'; }

  function fillImpact() {
    if (!C.impact) return;
    var en = isEn();
    var num = function (v) { return (Number(v) || 0).toLocaleString(en ? 'en' : 'fr'); };
    var format = {
      'impact.percentage': function (v) { return String(v); },
      'impact.donationsRaised': function (v) { return num(v) + ' €'; },
      'impact.plasticRemoved': function (v) { return num(v) + ' g'; },
    };
    document.querySelectorAll('[data-cms]').forEach(function (el) {
      var key = el.getAttribute('data-cms');
      var val = key.split('.').reduce(function (o, k) { return o && o[k]; }, C);
      if (val == null) return;
      el.textContent = format[key] ? format[key](val) : String(val);
      if (el.hasAttribute('data-countup')) el.setAttribute('data-countup', String(val));
    });
  }

  function fillFeatured() {
    var grid = document.getElementById('featured');
    if (!grid || !C.homepage || !C.homepage.featured || !window.CP_PRODUCTS) return;
    var en = isEn();
    var bySlug = {};
    window.CP_PRODUCTS.forEach(function (p) { bySlug[String(p.id).replace(/^sanity-/, '')] = p; });

    var soon = en ? 'Coming soon' : 'Bientôt';
    var soonNote = en ? 'In stock soon' : 'En stock bientôt';
    var view = en ? 'View' : 'Voir';

    var cards = C.homepage.featured.map(function (f) {
      var p = bySlug[f.slug];
      if (!p) return '';
      var available = p.status === 'active';
      var badge = available ? '' : '<span class="pcard__tag pcard__tag--soon">' + soon + '</span>';
      var action = available && p.source_url
        ? '<a class="pcard__go" href="' + p.source_url + '" target="_blank" rel="noopener">' + view + '</a>'
        : '<span class="pcard__go" style="text-decoration:none;color:var(--sage-deep)">' + soonNote + '</span>';
      return (
        '<article class="pcard">' +
        '<div class="pcard__media">' +
        '<img src="' + (p.img || '') + '" alt="" width="600" height="750" loading="lazy" />' + badge +
        '</div>' +
        '<h3 class="pcard__name">' + (p.title_fr || f.name || '') + '</h3>' +
        '<p class="pcard__desc">' + (p.desc_fr || '') + '</p>' +
        '<div class="pcard__actions">' + action + '</div>' +
        '</article>'
      );
    }).join('');

    if (cards.replace(/\s/g, '')) grid.innerHTML = cards;
  }

  function render() { fillImpact(); fillFeatured(); }

  render();
  // Re-render on language switch so number formatting + labels follow the locale.
  document.addEventListener('cp:langchange', render);
})();
