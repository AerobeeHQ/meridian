/* Codex brochure site — main.js */

(function () {
  'use strict';

  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ─── Sticky nav ─────────────────────────────────────────────────
  const nav = document.getElementById('nav');
  const onScroll = () => {
    nav.classList.toggle('scrolled', window.scrollY > 20);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  // ─── Mobile nav toggle ───────────────────────────────────────────
  const toggle  = document.getElementById('navToggle');
  const navLinks = document.getElementById('navLinks');

  if (toggle && navLinks) {
    toggle.addEventListener('click', () => {
      const open = navLinks.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open);
    });

    // Close on link click
    navLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        navLinks.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  // ─── Step tabs ───────────────────────────────────────────────────
  const stepTabs   = document.querySelectorAll('.step-tab');
  const stepPanels = document.querySelectorAll('.step-panel');

  stepTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.step;

      stepTabs.forEach(t => t.classList.remove('active'));
      stepPanels.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const panel = document.querySelector(`.step-panel[data-panel="${target}"]`);
      if (panel) panel.classList.add('active');
    });
  });

  // ─── Screenshot carousel ─────────────────────────────────────────
  const carousel     = document.getElementById('carousel');
  const track        = document.getElementById('carouselTrack');
  const dotsWrap     = document.getElementById('carouselDots');
  const progressBar  = document.getElementById('carouselProgress');
  const btnPrev      = document.getElementById('carouselPrev');
  const btnNext      = document.getElementById('carouselNext');

  if (carousel && track) {
    const slides     = Array.from(track.querySelectorAll('.carousel-slide'));
    const TOTAL      = slides.length;
    const DURATION   = 60000;                    // 60s total
    const PER_SLIDE  = DURATION / TOTAL;         // ~3.33s per slide

    let current  = 0;
    let timer    = null;
    let paused   = false;
    let startTs  = null;
    let elapsed  = 0;

    // Build dot indicators
    slides.forEach((_, i) => {
      const dot = document.createElement('button');
      dot.className = 'carousel-dot' + (i === 0 ? ' active' : '');
      dot.setAttribute('aria-label', `Screenshot ${i + 1} of ${TOTAL}`);
      if (i === 0) {
        dot.setAttribute('aria-current', 'true');
      }
      dot.addEventListener('click', () => goTo(i));
      dotsWrap.appendChild(dot);
    });

    const dots = Array.from(dotsWrap.querySelectorAll('.carousel-dot'));

    function goTo(idx) {
      slides[current].setAttribute('aria-hidden', 'true');
      dots[current].classList.remove('active');
      dots[current].removeAttribute('aria-current');

      current = (idx + TOTAL) % TOTAL;

      slides[current].setAttribute('aria-hidden', 'false');
      dots[current].classList.add('active');
      dots[current].setAttribute('aria-current', 'true');
      track.style.transform = `translateX(-${current * 100}%)`;

      resetProgress();
    }

    function next() { goTo(current + 1); }
    function prev() { goTo(current - 1); }

    btnPrev.addEventListener('click', () => { prev(); pauseResume(true); });
    btnNext.addEventListener('click', () => { next(); pauseResume(true); });

    // Keyboard navigation
    carousel.addEventListener('keydown', e => {
      if (e.key === 'ArrowLeft')  { prev(); pauseResume(true); }
      if (e.key === 'ArrowRight') { next(); pauseResume(true); }
    });

    // Touch swipe
    let touchX = null;
    carousel.addEventListener('touchstart', e => { touchX = e.touches[0].clientX; }, { passive: true });
    carousel.addEventListener('touchend', e => {
      if (touchX === null) return;
      const dx = e.changedTouches[0].clientX - touchX;
      if (Math.abs(dx) > 40) { dx < 0 ? next() : prev(); }
      touchX = null;
    });

    // Pause on hover / focus
    carousel.addEventListener('mouseenter', () => pauseResume(true));
    carousel.addEventListener('mouseleave', () => pauseResume(false));
    carousel.addEventListener('focusin',    () => pauseResume(true));
    carousel.addEventListener('focusout',   () => pauseResume(false));

    // Progress bar animation
    function resetProgress() {
      elapsed = 0;
      startTs = null;
      cancelAnimationFrame(timer);
      if (!paused) animateProgress();
    }

    // Respect prefers-reduced-motion for all auto-advance entry points,
    // not only the initial startup.
    const autoAdvanceEnabled = !prefersReduced;

    function startProgressAnimation() {
      if (!autoAdvanceEnabled) return;
      timer = requestAnimationFrame(animateProgress);
    }

    function animateProgress(ts) {
      if (!autoAdvanceEnabled) return;
      if (!startTs) startTs = ts;
      elapsed = ts - startTs;
      const pct = Math.min((elapsed / PER_SLIDE) * 100, 100);
      progressBar.style.width = pct + '%';
      progressBar.style.transition = 'none';

      if (elapsed >= PER_SLIDE) {
        next();
        return;
      }
      timer = requestAnimationFrame(animateProgress);
    }

    function pauseResume(shouldPause) {
      if (shouldPause && !paused) {
        paused = true;
        cancelAnimationFrame(timer);
        carousel.classList.add('paused');
      } else if (!shouldPause && paused) {
        paused = false;
        startTs = null;       // restart the per-slide timer from now
        carousel.classList.remove('paused');
        startProgressAnimation();
      }
    }

    startProgressAnimation();
  }

  // ─── Lightbox ────────────────────────────────────────────────────
  const lbOverlay = document.getElementById('lbOverlay');
  const lbImg     = document.getElementById('lbImg');
  const lbCaption = document.getElementById('lbCaption');
  const lbCounter = document.getElementById('lbCounter');
  const lbClose   = document.getElementById('lbClose');
  const lbPrev    = document.getElementById('lbPrev');
  const lbNext    = document.getElementById('lbNext');

  if (lbOverlay) {
    const gallery  = [];
    let lbCurrent  = 0;
    let lbOpener   = null;  // element that triggered the open — restored on close

    // Focus-trap: the three interactive controls inside the dialog
    const lbFocusable = [lbClose, lbPrev, lbNext];

    // Make a non-interactive element keyboard-activatable (Enter / Space)
    function makeActivatable(el, handler) {
      el.setAttribute('tabindex', '0');
      el.setAttribute('role', 'button');
      el.addEventListener('click', handler);
      el.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          handler();
        }
      });
    }

    // Hero image — index 0
    const heroImg = document.querySelector('.hero-image');
    if (heroImg) {
      gallery.push({ src: heroImg.src, alt: heroImg.alt, caption: 'Codex \u2014 Configuration Hub' });
      makeActivatable(heroImg, () => openLightbox(0));
    }

    // Carousel slides — indices 1 … n
    document.querySelectorAll('.carousel-slide').forEach((fig, i) => {
      const img    = fig.querySelector('img');
      const strong = fig.querySelector('figcaption strong');
      gallery.push({ src: img.src, alt: img.alt, caption: strong ? strong.textContent : '' });
      makeActivatable(fig, () => openLightbox(i + 1));
    });

    function openLightbox(idx) {
      lbOpener  = document.activeElement;   // save so we can restore on close
      lbCurrent = (idx + gallery.length) % gallery.length;
      const item = gallery[lbCurrent];
      lbImg.src = item.src;
      lbImg.alt = item.alt;
      lbCaption.textContent = item.caption;
      lbCounter.textContent = 'Image ' + (lbCurrent + 1) + ' of ' + gallery.length;
      lbOverlay.hidden = false;
      document.body.style.overflow = 'hidden';
      lbClose.focus();    // move focus into the dialog immediately
    }

    function closeLightbox() {
      lbOverlay.hidden = true;
      lbImg.src = '';
      document.body.style.overflow = '';
      // Only restore focus if the opener is still in the document (it could have
      // been removed or disabled while the lightbox was open)
      if (lbOpener && document.body.contains(lbOpener)) {
        lbOpener.focus();
      }
      lbOpener = null;
    }

    lbClose.addEventListener('click', closeLightbox);
    lbPrev.addEventListener('click',  () => openLightbox(lbCurrent - 1));
    lbNext.addEventListener('click',  () => openLightbox(lbCurrent + 1));

    lbOverlay.addEventListener('click', (e) => {
      if (e.target === lbOverlay) closeLightbox();
    });

    document.addEventListener('keydown', (e) => {
      if (lbOverlay.hidden) return;
      if (e.key === 'Escape')     { closeLightbox(); return; }
      if (e.key === 'ArrowLeft')  { openLightbox(lbCurrent - 1); return; }
      if (e.key === 'ArrowRight') { openLightbox(lbCurrent + 1); return; }
      // Focus trap: keep Tab cycling within the dialog controls.
      // If focus is somehow outside the list (idx === -1), default to first.
      if (e.key === 'Tab') {
        e.preventDefault();
        const idx  = lbFocusable.indexOf(document.activeElement);
        const next = e.shiftKey
          ? (idx <= 0 ? lbFocusable.length - 1 : idx - 1)
          : (idx + 1) % lbFocusable.length;
        lbFocusable[next].focus();
      }
    });
  }

})();
