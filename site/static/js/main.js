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
