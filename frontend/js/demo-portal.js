(function () {
  const buttons = document.querySelectorAll('[data-nav-view]');
  const viewGeneral = document.getElementById('view-general');
  const viewDatabase = document.getElementById('view-database');

  function setView(view) {
    if (!viewGeneral || !viewDatabase) return;
    const isGeneral = view === 'general';
    viewGeneral.hidden = !isGeneral;
    viewDatabase.hidden = isGeneral;
    buttons.forEach((btn) => {
      btn.classList.toggle('nav-active', btn.getAttribute('data-nav-view') === view);
    });
    try {
      sessionStorage.setItem('demoPortalView', view);
    } catch (e) {
      /* ignore */
    }
  }

  buttons.forEach((btn) => {
    btn.addEventListener('click', () => setView(btn.getAttribute('data-nav-view')));
  });

  let initial = 'general';
  try {
    const saved = sessionStorage.getItem('demoPortalView');
    if (saved === 'general' || saved === 'database') initial = saved;
  } catch (e) {
    /* ignore */
  }
  setView(initial);
})();
