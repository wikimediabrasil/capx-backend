(function() {
  var manageTabBtn = document.getElementById('tab-badges-manage');
  var assignTabBtn = document.getElementById('tab-badges-assign');
  var panelAssign = document.getElementById('panel-badges-assign');
  var badgeSelect = document.getElementById('assignments-badge-select');
  var awardedList = document.getElementById('awarded-users-list');
  var assignHidden = document.getElementById('assign-badge-hidden');
  var removeForm = document.getElementById('badge-remove-shared-form');
  var removeUserInput = document.getElementById('badge-remove-username');
  var removeBadgeInput = document.getElementById('badge-remove-badge-id');
  var dataEl = document.getElementById('partner-badges-awarded-data');
  var awardedMap = {};
  if (dataEl) {
    try { awardedMap = JSON.parse(dataEl.textContent || '{}'); } catch (e) { awardedMap = {}; }
  }

  function setSelectedBadge(bid) {
    if (!badgeSelect) return;
    var opt = badgeSelect.querySelector('option[value="' + bid + '"]');
    if (opt) { badgeSelect.value = String(bid); }
    syncAssignHidden();
    renderAwarded();
  }

  function syncAssignHidden() {
    if (assignHidden && badgeSelect) assignHidden.value = badgeSelect.value || '';
  }

  function renderAwarded() {
    if (!awardedList || !badgeSelect) return;
    awardedList.innerHTML = '';
    var bid = badgeSelect.value;
    var users = awardedMap[bid] || [];
    if (!users.length) {
      var li = document.createElement('li');
      li.className = 'muted';
      li.textContent = 'No users have this badge yet.';
      awardedList.appendChild(li);
      return;
    }

    users.forEach(function(u) {
      var li = document.createElement('li');
      li.style.display = 'flex';
      li.style.alignItems = 'center';
      li.style.justifyContent = 'space-between';
      li.style.gap = '8px';
      var span = document.createElement('span');
      span.textContent = u;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'form btn-danger';
      btn.textContent = 'Remove';
      btn.addEventListener('click', function() {
        if (!removeForm) return;
        removeUserInput.value = u;
        removeBadgeInput.value = bid;
        removeForm.submit();
      });
      li.appendChild(span);
      li.appendChild(btn);
      awardedList.appendChild(li);
    });
  }

  if (badgeSelect) {
    badgeSelect.addEventListener('change', function() { syncAssignHidden(); renderAwarded(); });
    syncAssignHidden();
    renderAwarded();
  }

  document.addEventListener('click', function(e) {
    var m = e.target.closest('[data-action="manage-assign"]');
    if (m) {
      var bid = m.getAttribute('data-badge-id');
      if (assignTabBtn && manageTabBtn) {
        manageTabBtn.setAttribute('aria-selected', 'false');
        assignTabBtn.setAttribute('aria-selected', 'true');
        var managePanel = document.getElementById(manageTabBtn.getAttribute('aria-controls'));
        var assignPanel = document.getElementById(assignTabBtn.getAttribute('aria-controls'));
        if (managePanel) managePanel.hidden = true;
        if (assignPanel) assignPanel.hidden = false;
      }
      setSelectedBadge(bid);
      if (panelAssign) {
        var y = panelAssign.getBoundingClientRect().top + window.scrollY - 90;
        window.scrollTo({ top: y, behavior: 'smooth' });
      }
    }

    var editBtn = e.target.closest('[data-action="edit-badge"]');
    if (editBtn) {
      var id = editBtn.getAttribute('data-badge-id');
      var row = document.querySelector('tr[data-badge-edit-row][data-for="' + id + '"]');
      if (row) { row.hidden = !row.hidden; }
    }
  });
})();