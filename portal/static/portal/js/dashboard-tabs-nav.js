(function() {
  var links = Array.from(document.querySelectorAll('[data-section-link]'));
  if (!links.length) return;

  function setActiveByHash() {
    var hash = location.hash || '#users';
    links.forEach(function(a) { a.classList.toggle('active', a.getAttribute('href') === hash); });
  }

  links.forEach(function(a) {
    a.addEventListener('click', function(e) {
      e.preventDefault();
      var href = a.getAttribute('href');
      var target = document.querySelector(href);
      if (target) {
        history.replaceState(null, '', href);
        setActiveByHash();
        var y = target.getBoundingClientRect().top + window.scrollY - 90;
        window.scrollTo({ top: y, behavior: 'smooth' });
      }
    });
  });

  window.addEventListener('hashchange', setActiveByHash);
  setActiveByHash();
})();

(function() {
  var pTable = document.getElementById('portal-users-table');
  var input = document.getElementById('portal-users-filter');
  if (!pTable || !input) return;
  var tbody = pTable.tBodies[0];

  function norm(s) { return (s || '').toLowerCase(); }

  function apply() {
    var q = norm(input.value);
    for (var r of Array.from(tbody.rows)) {
      var hay = norm(r.textContent);
      r.style.display = q === '' || hay.indexOf(q) !== -1 ? '' : 'none';
    }
  }

  input.addEventListener('input', apply);
})();

(function() {
  var modal = document.getElementById('notes-modal');
  if (!modal) return;
  var form = document.getElementById('notes-form');
  var usernameInput = document.getElementById('notes-username');
  var notesText = document.getElementById('notes-text');
  var cancelBtn = document.getElementById('notes-cancel');

  function openModal(username, notes) {
    usernameInput.value = username;
    notesText.value = notes || '';
    modal.style.display = 'block';
    setTimeout(function() { notesText.focus(); }, 0);
  }

  function closeModal() { modal.style.display = 'none'; }

  document.addEventListener('click', function(e) {
    var btn = e.target.closest('.edit-notes-btn');
    if (btn) {
      var username = btn.getAttribute('data-username');
      var notes = btn.getAttribute('data-notes') || '';
      openModal(username, notes);
      return;
    }
    var display = e.target.closest('.notes-display');
    if (display) {
      var username2 = display.dataset.username;
      var notes2 = display.dataset.notes || display.textContent || '';
      openModal(username2, notes2.trim());
    }
  });

  if (cancelBtn) cancelBtn.addEventListener('click', function() { closeModal(); });
  modal.addEventListener('click', function(e) { if (e.target === modal) closeModal(); });
  document.addEventListener('keydown', function(e) { if (e.key === 'Escape') closeModal(); });
})();

(function() {
  function initTablist(tablist) {
    var tabs = Array.from(tablist.querySelectorAll('[role="tab"]'));
    tabs.forEach(function(tab) {
      var controls = tab.getAttribute('aria-controls');
      var panel = controls && document.getElementById(controls);
      if (!panel) return;
      panel.hidden = tab.getAttribute('aria-selected') !== 'true';
    });

    tabs.forEach(function(tab, index) {
      tab.addEventListener('click', function() {
        tabs.forEach(function(t) { t.setAttribute('aria-selected', 'false'); });
        tab.setAttribute('aria-selected', 'true');
        tabs.forEach(function(t) {
          var pid = t.getAttribute('aria-controls');
          var pnl = pid && document.getElementById(pid);
          if (pnl) pnl.hidden = t.getAttribute('aria-selected') !== 'true';
        });
      });

      tab.addEventListener('keydown', function(e) {
        if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
        e.preventDefault();
        var dir = e.key === 'ArrowRight' ? 1 : -1;
        var next = tabs[(index + dir + tabs.length) % tabs.length];
        if (next) { next.focus(); next.click(); }
      });
    });
  }

  var lists = document.querySelectorAll('[role="tablist"]');
  for (var list of lists) initTablist(list);
})();