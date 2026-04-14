/* Codex brochure site — main.js */

(function () {
  'use strict';

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
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
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

  // ─── Intersection observer — fade-in on scroll ───────────────────
  const observerOpts = { threshold: 0.08, rootMargin: '0px 0px -20px 0px' };
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, observerOpts);

  document.querySelectorAll('.feature-card, .lineage-list li, .req-card, .diagram-card').forEach((el, i) => {
    el.classList.add('observe');
    el.style.setProperty('--delay', `${i * 60}ms`);
    observer.observe(el);
  });

})();
