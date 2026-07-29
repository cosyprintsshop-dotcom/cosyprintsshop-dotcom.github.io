/* ============================================================================
   Cosy Prints — behaviour and motion.

   Progressive enhancement, in three tiers:
     tier 0  no JS at all  -> everything visible, everything works
     tier 1  this file     -> nav, accordion, filters, IntersectionObserver reveals
     tier 2  GSAP + Lenis  -> smooth scroll, line-masked headings, batched grids

   Tier 2 is loaded only when the visitor has not asked for reduced motion, so
   those users never pay the ~55 KB.
   ========================================================================== */
(function () {
  "use strict";

  var root = document.documentElement;
  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  var canMove = !reduced.matches;

  /* Only opt into the hiding styles once we know we can un-hide them. */
  if (canMove) root.classList.add("js-motion");

  /* ------------------------------------------------------------------ nav */
  (function nav() {
    var last = 0, ticking = false;
    var DELTA = 6;       // ignore sub-pixel jitter
    var REVEAL_AT = 80;  // never hide inside the first 80px

    var darkZones = [];
    function measureDark() {
      darkZones = Array.prototype.map.call(
        document.querySelectorAll('[data-tone="night"]'),
        function (el) {
          var r = el.getBoundingClientRect();
          var top = r.top + window.scrollY;
          return [top, top + r.height];
        }
      );
    }

    function onScroll() {
      var y = Math.max(0, window.scrollY);
      root.classList.toggle("nav-solid", y > 24);
      if (Math.abs(y - last) >= DELTA) {
        root.classList.toggle("nav-hidden", y > last && y > REVEAL_AT);
        last = y;
      }
      // invert the nav while it sits over a night section
      var probe = y + 40;
      var dark = false;
      for (var i = 0; i < darkZones.length; i++) {
        if (probe >= darkZones[i][0] && probe <= darkZones[i][1]) { dark = true; break; }
      }
      root.classList.toggle("nav-dark", dark);
    }

    function request() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () { onScroll(); ticking = false; });
    }

    measureDark();
    onScroll();
    addEventListener("scroll", request, { passive: true });
    addEventListener("resize", function () { measureDark(); request(); }, { passive: true });
    addEventListener("load", measureDark);
  })();

  /* ------------------------------------------------- accordion (details) */
  (function accordion() {
    var items = document.querySelectorAll(".qa");
    Array.prototype.forEach.call(items, function (d) {
      var body = d.querySelector(".qa__a");
      if (!body) return;

      // <details> has no animatable height, so drive it by hand
      d.addEventListener("toggle", function () {
        if (!canMove) return;
        if (d.open) {
          var h = body.scrollHeight;
          body.style.height = "0px";
          body.getBoundingClientRect();          // force a reflow so the 0 sticks
          body.style.transition = "height 420ms cubic-bezier(.23,1,.32,1)";
          body.style.height = h + "px";
          body.addEventListener("transitionend", function done() {
            body.style.height = ""; body.style.transition = "";
            body.removeEventListener("transitionend", done);
          });
        }
      });

      // closing needs to be intercepted, or the browser collapses it instantly
      var summary = d.querySelector("summary");
      if (!summary) return;
      summary.addEventListener("click", function (e) {
        if (!canMove || !d.open) return;
        e.preventDefault();
        var h = body.scrollHeight;
        body.style.height = h + "px";
        body.getBoundingClientRect();
        body.style.transition = "height 320ms cubic-bezier(.5,0,.75,0)";
        body.style.height = "0px";
        body.addEventListener("transitionend", function done() {
          d.open = false;
          body.style.height = ""; body.style.transition = "";
          body.removeEventListener("transitionend", done);
        });
      });
    });
  })();

  /* ------------------------------------------------------------ filters */
  (function filters() {
    var bar = document.querySelector("[data-filters]");
    if (!bar) return;
    var cards = document.querySelectorAll("[data-rooms]");
    var live = document.querySelector("[data-filter-count]");

    bar.addEventListener("click", function (e) {
      var btn = e.target.closest(".filter");
      if (!btn) return;
      var room = btn.dataset.room || "";

      Array.prototype.forEach.call(bar.querySelectorAll(".filter"), function (b) {
        b.setAttribute("aria-pressed", String(b === btn));
      });

      var shown = 0;
      Array.prototype.forEach.call(cards, function (c) {
        var match = !room || (c.dataset.rooms || "").split("|").indexOf(room) > -1;
        c.hidden = !match;
        if (match) shown++;
      });
      if (live) live.textContent = shown + (shown === 1 ? " piece" : " pieces");
    });
  })();

  /* ----------------------------------------------- tier 1 scroll reveals */
  (function reveals() {
    var targets = document.querySelectorAll(".lay, .rise, .lines");
    if (!canMove || !targets.length) return;

    function show(el) { el.classList.add("is-in"); }

    if (!("IntersectionObserver" in window)) {
      targets.forEach(show);
      return;
    }

    var fired = false;
    var io = new IntersectionObserver(function (entries) {
      fired = true;
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        show(en.target);
        io.unobserve(en.target);
      });
    }, { rootMargin: "0px 0px -12% 0px", threshold: 0.01 });

    var above = [];
    targets.forEach(function (el) {
      // anything already on screen at load reveals immediately, not on scroll
      if (el.getBoundingClientRect().top < innerHeight * 0.9) {
        above.push(el);
        requestAnimationFrame(function () { show(el); });
      } else {
        io.observe(el);
      }
    });

    /* Safety nets. These styles hide content, so JS must not be the only thing
       that can bring it back: rAF and IntersectionObserver callbacks both need a
       rendering opportunity, which a background or non-compositing tab never
       gets. setTimeout still fires there. */
    setTimeout(function () { above.forEach(show); }, 1200);
    setTimeout(function () {
      if (fired) return;          // the observer works — leave the scroll reveals alone
      io.disconnect();
      targets.forEach(show);      // it does not, so nothing stays invisible
    }, 2500);
  })();

  /* --------------------------------------------- view transition naming */
  /* Give the clicked card's image the same name as the hero on the page we are
     going to, so the browser morphs one into the other instead of cross-fading. */
  (function morph() {
    if (!canMove || !document.startViewTransition) return;
    document.addEventListener("click", function (e) {
      var card = e.target.closest("[data-morph]");
      if (!card) return;
      document.querySelectorAll("[data-morph]").forEach(function (c) {
        var m = c.querySelector(".pcard__media, .cat__media");
        if (m) m.style.viewTransitionName = "";
      });
      var media = card.querySelector(".pcard__media, .cat__media");
      if (media) media.style.viewTransitionName = "hero-media";
    }, true);

    // clear it again if the visitor comes back, or the name leaks into the next transition
    addEventListener("pageswap", function () {
      document.querySelectorAll('[style*="hero-media"]').forEach(function (el) {
        el.style.viewTransitionName = "";
      });
    });
  })();

  /* ============================== tier 2 ================================ */
  if (!canMove) return;

  function load(src) {
    return new Promise(function (res, rej) {
      var s = document.createElement("script");
      s.src = src; s.async = false;
      s.onload = res; s.onerror = rej;
      document.head.appendChild(s);
    });
  }

  var V = "/assets/vendor/";
  load(V + "lenis.min.js")
    .then(function () { return load(V + "gsap.min.js"); })
    .then(function () { return load(V + "ScrollTrigger.min.js"); })
    .then(function () { return load(V + "SplitText.min.js"); })
    .then(upgrade)
    .catch(function () { /* tier 1 already looks fine — nothing to do */ });

  function upgrade() {
    if (!window.gsap || !window.ScrollTrigger) return;
    gsap.registerPlugin(ScrollTrigger, window.SplitText);

    /* -------------------------------------------------- smooth scroll */
    if (window.Lenis) {
      var lenis = new Lenis({
        lerp: 0.09,          // 0.1 default; slightly heavier reads as weighted, not floaty
        wheelMultiplier: 0.9,
        syncTouch: false,    // never hijack touch — native momentum already feels right
        anchors: true
      });
      lenis.on("scroll", ScrollTrigger.update);
      gsap.ticker.add(function (t) { lenis.raf(t * 1000); });
      gsap.ticker.lagSmoothing(0);   // not optional: lag smoothing fights Lenis
      window.__lenis = lenis;        // so scripted scrolling can drive it instead of fighting it
    }

    /* ------------------------------------- headings: line-masked reveal */
    if (window.SplitText) {
      document.querySelectorAll("[data-split]").forEach(function (el) {
        SplitText.create(el, {
          type: "lines",
          mask: "lines",     // makes its own overflow:clip wrappers
          autoSplit: true,   // re-splits on resize and after the webfont swaps
          onSplit: function (self) {
            return gsap.from(self.lines, {
              yPercent: 100,
              duration: 0.9,
              stagger: 0.08,
              ease: "power4.out",   // === easeOutQuart
              scrollTrigger: { trigger: el, start: "top 88%", once: true }
              // deliberately no opacity — the mask is the reveal
            });
          }
        });
      });
    }

    /* --------------------------------------------- product grids: batch */
    ScrollTrigger.batch("[data-batch] > *", {
      start: "top 88%",
      once: true,
      interval: 0.1,
      batchMax: 4,          // stops 20 cards rippling down the page
      onEnter: function (els) {
        gsap.to(els, {
          opacity: 1, y: 0,
          duration: 0.8, stagger: 0.09,
          ease: "power3.out", overwrite: true
        });
      }
    });
    gsap.set("[data-batch] > *", { opacity: 0, y: 22 });

    /* The hero is deliberately NOT animated here. It is above the fold, so a
       GSAP timeline created after the libraries arrive would visibly re-hide
       content that has already painted. Its stagger is CSS `--rd` delays. */

    addEventListener("load", function () { ScrollTrigger.refresh(); });
  }
})();
