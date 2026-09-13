/* The playable-deck shell. Content-agnostic: it knows about .s sections and nothing else.
 *
 * EXTRACTED 2026-09-12 from the one deck this form rests on, where every mechanic below was
 * earned against a real audience on real phones. The comments that explain WHY are carried
 * over verbatim where they exist, because each one records a failure that is invisible in
 * working code.
 */
(function () {
  var S = [].slice.call(document.querySelectorAll('section.s'));
  if (!S.length) return;
  var i = 0;
  var D = document.getElementById('dots');
  var SCRUB = document.getElementById('scrub');
  var NO = document.getElementById('no');
  var BAR = document.getElementById('bar');

  var titles = S.map(function (s, k) {
    var h = s.querySelector('h1,h2,h3');
    return h ? h.textContent.trim() : ('Slide ' + (k + 1));
  });

  /* THE MOBILE TRICK, and the reason this deck reads on a phone without scrolling.
   *
   * Measure the slide's content UNSCALED on both axes, then CSS-scale it to fit slightly
   * less than the space available. Width matters in landscape, where the padding is wide
   * and the viewport is short, so both axes are measured rather than just height.
   *
   * Fitting to slightly LESS than 100% is deliberate. Scaling to exactly the available
   * space is technically a fit and visually a mistake: the content ends up flush against
   * the frame with no air, which reads as clipped even though nothing is.
   */
  function fitSlide(sec) {
    var box = sec && sec.querySelector('.in');
    if (!box) return;

    /* An image has no intrinsic height until it loads, so a slide measured before its
     * illustration arrives looks shorter than it is, fits at full size, and overflows the
     * instant the image paints. Re-fit as each one lands. Attached before any early return. */
    var imgs = sec.querySelectorAll('img');
    for (var n = 0; n < imgs.length; n++) {
      if (!imgs[n].complete) imgs[n].addEventListener('load', fitCurrent, { once: true });
    }
    /* A <video> has NO intrinsic size until its metadata lands, exactly like an image with
     * no declared dimensions. `loadedmetadata` is the moment it has a width and height; the
     * poster paint can land later still, so take both. */
    var vids = sec.querySelectorAll('video');
    for (var v = 0; v < vids.length; v++) {
      if (vids[v].readyState < 1) {
        vids[v].addEventListener('loadedmetadata', fitCurrent, { once: true });
        vids[v].addEventListener('loadeddata', fitCurrent, { once: true });
      }
    }

    box.style.transform = '';
    box.style.marginBottom = '';
    /* Clear any explicit width before measuring, or the next slide is measured at the
     * previous slide's widened geometry. */
    box.style.width = '';
    box.style.maxWidth = '';

    var cs = getComputedStyle(sec);
    var availH = sec.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
    var availW = sec.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    var needH = box.scrollHeight, needW = box.scrollWidth;
    if (!availH || !needH) return;

    var k = Math.min(availH / needH, availW / needW) * 0.97;
    if (k >= 1) return;                       // it already fits; never scale UP
    if (k < 0.55) k = 0.55;                   // past here it is unreadable; let it scroll
    box.style.transformOrigin = 'top center';
    box.style.transform = 'scale(' + k + ')';
    /* A scaled element still occupies its UNSCALED height in layout, so the section would
     * keep a scrollbar for space nothing is drawn in. Pull the difference back. */
    box.style.marginBottom = (-(needH * (1 - k))) + 'px';
  }
  function fitCurrent() { fitSlide(S[i]); }

  /* The URL carries the slide number, so a refresh, a bookmark, or a link someone pastes
   * lands on the slide the reader was actually on instead of snapping back to the cover.
   * replaceState rather than pushState: the back button should leave the deck, not walk
   * backwards through twelve slides. */
  /* A HASH IS EITHER A POSITION OR AN ID, AND AN ID IS THE STABLE ONE.
   *
   * This used to strip every non-digit out of the hash, which had two faults. It could not
   * resolve an id at all, even though the builder writes every slide's id into the section, so
   * a link naming a slide silently landed on slide one. And worse, it MIS-resolved any id that
   * happens to contain a digit: `#why-2` became "2" and opened slide two, which is a different
   * slide, with nothing anywhere reporting a problem.
   *
   * A position is what a person says out loud and it moves the moment a slide is inserted. An
   * id does not move, which is why anything durable (a review file, a comment, a message) should
   * point at the id. So both resolve, digits-only first, then an exact id. */
  function slideFromHash() {
    var h = (location.hash || '').replace(/^#/, '');
    if (/^[0-9]+$/.test(h)) {
      var n = parseInt(h, 10);
      return (n >= 1 && n <= S.length) ? n - 1 : 0;
    }
    if (h) {
      for (var k = 0; k < S.length; k++) {
        if (S[k].id === h) return k;
      }
    }
    return 0;
  }

  function go(k, fromHash) {
    i = Math.max(0, Math.min(S.length - 1, k));
    S.forEach(function (s, j) { s.classList.toggle('on', j === i); });
    if (D) [].slice.call(D.children).forEach(function (d, j) { d.classList.toggle('on', j === i); });
    if (NO) NO.textContent = (i + 1) + ' / ' + S.length;
    if (BAR) BAR.style.width = ((i + 1) / S.length * 100) + '%';
    S[i].scrollTop = 0;
    /* THE CHROME FOLLOWS THE SLIDE'S GROUND. The footer and counter sit OUTSIDE the section,
     * so a cream slide otherwise gets a dark bar across its bottom that reads as a separate
     * layer bolted onto the page. The class goes on <body> because that is the only element
     * above both the sections and the fixed chrome. */
    document.body.classList.toggle('on-cream', S[i].classList.contains('ground-cream'));
    if (!fromHash) {
      var h = '#' + (i + 1);
      if (location.hash !== h) history.replaceState(null, '', h);
    }
    document.dispatchEvent(new Event('slidechange'));
    fitCurrent();
  }

  if (D) {
    S.forEach(function (s, k) {
      var b = document.createElement('button');
      b.className = 'dot';
      b.setAttribute('aria-label', 'Go to ' + titles[k]);
      b.addEventListener('click', function () { go(k); });
      D.appendChild(b);
    });
  }

  /* THE SCRUB BAR is what makes it feel playable rather than merely navigable: you can drag
   * across the whole argument and watch the titles go by, which is how someone decides where
   * to start reading. Seeking with fromHash=true so a drag does not write 30 history entries. */
  if (SCRUB) {
    var seekIdx = null;
    var fromX = function (clientX) {
      var r = SCRUB.getBoundingClientRect();
      var pct = Math.max(0, Math.min(1, (clientX - r.left) / r.width));
      return Math.round(pct * (S.length - 1));
    };
    var paintScrub = function (k) {
      var pct = S.length > 1 ? (k / (S.length - 1)) * 100 : 0;
      SCRUB.querySelector('.thumb').style.left = pct + '%';
      SCRUB.querySelector('.fill').style.width = pct + '%';
      var pill = SCRUB.querySelector('.pill');
      pill.textContent = titles[k];
      pill.style.left = Math.max(14, Math.min(86, pct)) + '%';
      SCRUB.setAttribute('aria-valuenow', k + 1);
    };
    SCRUB.addEventListener('pointerdown', function (e) {
      SCRUB.setPointerCapture(e.pointerId);
      SCRUB.classList.add('seeking');
      seekIdx = fromX(e.clientX); go(seekIdx, true); e.preventDefault();
    });
    SCRUB.addEventListener('pointermove', function (e) {
      if (seekIdx === null) return;
      var k = fromX(e.clientX);
      if (k !== seekIdx) { seekIdx = k; go(k, true); }
    });
    var land = function () {
      if (seekIdx === null) return;
      SCRUB.classList.remove('seeking'); go(seekIdx); seekIdx = null;
    };
    SCRUB.addEventListener('pointerup', land);
    SCRUB.addEventListener('pointercancel', land);
    document.addEventListener('slidechange', function () { paintScrub(i); });
    paintScrub(0);
  }

  /* SWIPE. Horizontal intent only: a vertical drag must stay available for scrolling a slide
   * that genuinely overflows, and a diagonal drag is almost always a scroll. */
  var sx = 0, sy = 0, tracking = false;
  var stage = document.getElementById('stage') || document.body;
  stage.addEventListener('touchstart', function (e) {
    if (e.touches.length !== 1) { tracking = false; return; }
    /* A DRAG THAT STARTS INSIDE A PASTE BLOCK IS A SELECTION, NEVER A SWIPE. Selecting text
     * with a thumb is a horizontal drag of exactly the shape this handler reads as "next
     * slide", so without this the reader loses both the selection and their place. */
    if (e.target && e.target.closest && e.target.closest('.paste')) { tracking = false; return; }
    sx = e.touches[0].clientX; sy = e.touches[0].clientY; tracking = true;
  }, { passive: true });
  stage.addEventListener('touchend', function (e) {
    if (!tracking) return;
    tracking = false;
    var t = e.changedTouches[0];
    var dx = t.clientX - sx, dy = t.clientY - sy;
    if (Math.abs(dx) < 45 || Math.abs(dx) < Math.abs(dy) * 1.6) return;
    go(i + (dx < 0 ? 1 : -1));
  }, { passive: true });

  document.addEventListener('keydown', function (e) {
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    var k = e.key;
    if (k === 'ArrowRight' || k === ' ' || k === 'PageDown') { go(i + 1); e.preventDefault(); }
    else if (k === 'ArrowLeft' || k === 'PageUp') { go(i - 1); e.preventDefault(); }
    else if (k === 'Home') { go(0); }
    else if (k === 'End') { go(S.length - 1); }
  });

  var next = document.getElementById('next'), prev = document.getElementById('prev');
  if (next) next.addEventListener('click', function () { go(i + 1); });
  if (prev) prev.addEventListener('click', function () { go(i - 1); });

  /* COPY, with a real fallback. navigator.clipboard is unavailable on any page not served
   * over https (and on older iOS Safari), which is exactly the case where a deck gets opened
   * from a local build to check it. A button that silently does nothing there is worse than no
   * button, because the reader has no way to tell it failed. */
  document.addEventListener('click', function (e) {
    var b = e.target && e.target.closest && e.target.closest('.paste .copy');
    if (!b) return;
    var pre = document.getElementById(b.getAttribute('data-for'));
    if (!pre) return;
    var text = pre.textContent, was = b.getAttribute('data-was') || b.textContent;
    b.setAttribute('data-was', was);
    function ok() {
      b.textContent = 'Copied';
      b.classList.add('done');
      setTimeout(function () { b.textContent = was; b.classList.remove('done'); }, 2200);
    }
    function manual() {
      /* Select it for them, so the next action is one tap on their own Copy. */
      var r = document.createRange(); r.selectNodeContents(pre);
      var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
      b.textContent = 'Selected, copy it';
      setTimeout(function () { b.textContent = was; }, 3200);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(ok, manual);
    } else { manual(); }
  });

  window.addEventListener('hashchange', function () { go(slideFromHash(), true); });
  window.addEventListener('resize', fitCurrent);
  window.addEventListener('orientationchange', function () { setTimeout(fitCurrent, 120); });
  window.addEventListener('load', fitCurrent);

  go(slideFromHash(), true);
})();
