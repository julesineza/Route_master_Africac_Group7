/* ============================================================
   Route Master Africa — Vanilla JS
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {

  /* ── Toggle create-container form panel ─────────────────── */
  const toggleBtn  = document.getElementById('toggle-form-btn');
  const formPanel  = document.getElementById('create-form-panel');

  if (toggleBtn && formPanel) {
    toggleBtn.addEventListener('click', () => {
      const isOpen = formPanel.classList.toggle('open');
      toggleBtn.setAttribute('aria-expanded', String(isOpen));

      if (isOpen) {
        toggleBtn.textContent = '✕  Cancel';
        toggleBtn.classList.remove('btn-primary');
        toggleBtn.classList.add('btn-secondary');
        // Scroll panel into view smoothly
        setTimeout(() => formPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' }), 50);
      } else {
        toggleBtn.textContent = '+ New Container';
        toggleBtn.classList.add('btn-primary');
        toggleBtn.classList.remove('btn-secondary');
      }
    });
  }

  /* ── Auto-dismiss flash messages ────────────────────────── */
  const flashes = document.querySelectorAll('.flash');
  flashes.forEach(flash => {
    setTimeout(() => {
      flash.style.transition = 'opacity .5s, max-height .5s';
      flash.style.opacity = '0';
      flash.style.maxHeight = '0';
      flash.style.overflow = 'hidden';
      setTimeout(() => flash.remove(), 500);
    }, 4000);
  });

  /* ── Trader: search form active state ───────────────────── */
  const searchForm  = document.getElementById('search-form');
  const searchBtn   = searchForm && searchForm.querySelector('.btn-primary');

  if (searchForm && searchBtn) {
    searchForm.addEventListener('submit', () => {
      searchBtn.textContent = 'Searching…';
      searchBtn.disabled = true;
    });
  }

  /* ── Input: highlight label on focus ────────────────────── */
  document.querySelectorAll('.field input, .field select').forEach(input => {
    const label = input.closest('.field')?.querySelector('label');
    if (!label) return;
    input.addEventListener('focus',  () => label.style.color = 'var(--green-700)');
    input.addEventListener('blur',   () => label.style.color = '');
  });

});
