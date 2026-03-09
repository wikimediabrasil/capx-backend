(function() {
  var table = document.getElementById('users-table');
  if (!table) return;
  var thead = table.tHead;
  var tbody = table.tBodies[0];
  var headers = Array.from(thead.rows[0].cells);
  var filterInput = document.getElementById('users-filter-input');
  var togglesContainer = document.getElementById('users-col-toggles');
  var csvBtn = document.getElementById('users-csv-btn');

  var sortState = [];

  function textOf(node) {
    return node.textContent.trim();
  }

  function parseValue(text) {
    if (text === '') return '';
    var ts = Date.parse(text);
    if (!isNaN(ts)) return ts;
    var num = parseFloat(text.replace(/\s/g, '').replace(',', '.'));
    if (!isNaN(num) && isFinite(num)) return num;
    return text.toLowerCase();
  }

  function getCellValue(tr, idx) {
    var cell = tr.cells[idx];
    return parseValue(textOf(cell || { textContent: '' }));
  }

  function compareRows(a, b) {
    for (var i = 0; i < sortState.length; i++) {
      var s = sortState[i];
      var va = getCellValue(a, s.index);
      var vb = getCellValue(b, s.index);
      if (va < vb) return -1 * s.dir;
      if (va > vb) return 1 * s.dir;
    }
    return 0;
  }

  function clearIndicators() {
    headers.forEach(function(th) {
      th.dataset.sort = '';
      var ind = th.querySelector('.sort-indicator');
      if (ind) ind.textContent = '';
    });
  }

  function refreshIndicators() {
    clearIndicators();
    sortState.forEach(function(s, idx) {
      var th = headers[s.index];
      th.dataset.sort = s.dir === 1 ? 'asc' : 'desc';
      var ind = th.querySelector('.sort-indicator');
      if (!ind) {
        ind = document.createElement('span');
        ind.className = 'sort-indicator';
        th.appendChild(ind);
      }
      var arrow = s.dir === 1 ? '▲' : '▼';
      var pos = sortState.length > 1 ? ' ' + (idx + 1) : '';
      ind.textContent = arrow + pos;
    });
  }

  function applySort() {
    if (!sortState.length) return;
    var rows = Array.from(tbody.rows);
    rows.sort(compareRows);
    rows.forEach(function(r) { tbody.appendChild(r); });
    refreshIndicators();
    if (typeof applyRowLimit === 'function') applyRowLimit();
  }

  function toggleSort(index, additive) {
    var existingIdx = sortState.findIndex(function(s) { return s.index === index; });
    if (additive) {
      if (existingIdx === -1) {
        sortState.push({ index: index, dir: 1 });
      } else {
        var s = sortState[existingIdx];
        if (s.dir === 1) s.dir = -1; else { sortState.splice(existingIdx, 1); }
      }
    } else {
      if (existingIdx === -1) {
        sortState = [{ index: index, dir: 1 }];
      } else {
        var d = sortState[existingIdx].dir;
        sortState = [{ index: index, dir: d === 1 ? -1 : 1 }];
      }
    }
    applySort();
  }

  headers.forEach(function(th, idx) {
    th.classList.add('sortable');
    th.title = 'Click to sort. Shift-click for multi-column.';
    th.addEventListener('click', function(e) {
      toggleSort(idx, e.shiftKey);
    });
    var ind = document.createElement('span');
    ind.className = 'sort-indicator';
    th.appendChild(ind);
  });

  function normalize(s) { return s.toLowerCase(); }
  var DEFAULT_LIMIT = 20;
  var limitOn = true;
  var infoEl = document.getElementById('users-row-limit-info');
  var toggleBtn = document.getElementById('users-toggle-limit-btn');

  function countVisibleRows() {
    var c = 0;
    for (var r of Array.from(tbody.rows)) {
      if (getComputedStyle(r).display !== 'none') c++;
    }
    return c;
  }

  function clearRowLimit() {
    for (var r of Array.from(tbody.rows)) {
      if (r.dataset.hiddenByLimit === '1') {
        r.style.display = '';
        delete r.dataset.hiddenByLimit;
      }
    }
  }

  function applyRowLimit() {
    clearRowLimit();
    var q = normalize(filterInput.value || '');
    var totalVisible = countVisibleRows();
    if (!limitOn || q !== '' || totalVisible <= DEFAULT_LIMIT) {
      if (infoEl) infoEl.textContent = q !== '' ? ('Showing ' + totalVisible + ' matched') : ('Showing all ' + totalVisible);
      if (toggleBtn) toggleBtn.style.display = (q === '' && totalVisible > DEFAULT_LIMIT) ? '' : 'none';
      if (toggleBtn) toggleBtn.textContent = 'Show less';
      return;
    }
    var shown = 0;
    for (var r of Array.from(tbody.rows)) {
      if (getComputedStyle(r).display === 'none') continue;
      shown++;
      if (shown > DEFAULT_LIMIT) {
        r.style.display = 'none';
        r.dataset.hiddenByLimit = '1';
      }
    }
    var remaining = totalVisible - DEFAULT_LIMIT;
    if (infoEl) infoEl.textContent = 'Showing first ' + DEFAULT_LIMIT + ' of ' + totalVisible;
    if (toggleBtn) { toggleBtn.style.display = ''; toggleBtn.textContent = 'Show all (' + remaining + ' more)'; }
  }

  function applyFilter() {
    var q = normalize(filterInput.value || '');
    var rows = Array.from(tbody.rows);
    rows.forEach(function(r) {
      var hay = normalize(r.textContent);
      r.style.display = q === '' || hay.indexOf(q) !== -1 ? '' : 'none';
    });
    limitOn = (q === '');
    applyRowLimit();
  }
  filterInput.addEventListener('input', applyFilter);

  if (toggleBtn) {
    toggleBtn.addEventListener('click', function() {
      if (limitOn) {
        limitOn = false;
        applyRowLimit();
        if (toggleBtn) toggleBtn.textContent = 'Show less';
      } else {
        limitOn = true;
        applyRowLimit();
      }
    });
  }

  function visibleColumnCount() {
    return headers.filter(function(th) { return th.style.display !== 'none'; }).length;
  }
  function setColumnVisibility(colIdx, visible) {
    if (!visible && visibleColumnCount() <= 1) return;
    var display = visible ? '' : 'none';
    headers[colIdx].style.display = display;
    Array.from(tbody.rows).forEach(function(r) {
      if (r.cells[colIdx]) r.cells[colIdx].style.display = display;
    });
    if (!visible) {
      var i = sortState.findIndex(function(s) { return s.index === colIdx; });
      if (i !== -1) { sortState.splice(i, 1); refreshIndicators(); }
    }
  }
  function buildColumnToggles() {
    headers.forEach(function(th, idx) {
      var id = 'toggle-col-' + idx;
      var label = document.createElement('label');
      var cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.id = id;
      cb.checked = th.style.display !== 'none';
      cb.addEventListener('change', function() { setColumnVisibility(idx, cb.checked); });
      var span = document.createElement('span');
      span.textContent = ' ' + textOf(th);
      label.appendChild(cb);
      label.appendChild(span);
      togglesContainer.appendChild(label);
    });
  }
  buildColumnToggles();

  function hasHorizontalOverflow(container) {
    return container.scrollWidth - container.clientWidth > 1;
  }
  function setToggleChecked(idx, checked) {
    var cb = document.getElementById('toggle-col-' + idx);
    if (cb) cb.checked = !!checked;
  }

  function getVisibleColumnIndexes() {
    var idxs = [];
    headers.forEach(function(th, idx) {
      if (getComputedStyle(th).display !== 'none') idxs.push(idx);
    });
    return idxs;
  }

  function autoFitColumns(minVisible) {
    var container = table.closest('.card') || table.parentElement || document.body;
    var min = (typeof minVisible === 'number' && minVisible > 0) ? minVisible : 5;
    if (!hasHorizontalOverflow(container)) return;
    var guard = 0;
    while (hasHorizontalOverflow(container) && visibleColumnCount() > min && guard++ < headers.length) {
      var visibleIdxs = getVisibleColumnIndexes();
      if (!visibleIdxs.length) break;
      var lastIdx = visibleIdxs[visibleIdxs.length - 1];
      setColumnVisibility(lastIdx, false);
      setToggleChecked(lastIdx, false);
    }
  }

  autoFitColumns(5);
  applyRowLimit();

  function escapeCSV(value) {
    var s = String(value).replace(/"/g, '""');
    return '"' + s + '"';
  }
  function downloadCSV() {
    var colIdxs = getVisibleColumnIndexes();
    var lines = [];
    var headerLine = colIdxs.map(function(i) { return escapeCSV(textOf(headers[i])); }).join(',');
    lines.push(headerLine);
    Array.from(tbody.rows).forEach(function(r) {
      var isHidden = getComputedStyle(r).display === 'none';
      var hiddenByLimit = r.dataset.hiddenByLimit === '1';
      if (isHidden && !hiddenByLimit) return;
      var vals = colIdxs.map(function(i) { return escapeCSV(textOf(r.cells[i] || { textContent: '' })); });
      lines.push(vals.join(','));
    });
    var csv = lines.join('\r\n');
    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'users.csv';
    document.body.appendChild(a);
    a.click();
    setTimeout(function() { URL.revokeObjectURL(url); a.remove(); }, 0);
  }
  csvBtn.addEventListener('click', downloadCSV);

  function makeResizable() {
    var minWidth = 60;
    headers.forEach(function(th, colIdx) {
      if (th.querySelector('.col-resizer')) return;
      var resizer = document.createElement('span');
      resizer.className = 'col-resizer';
      resizer.title = 'Drag to resize';
      th.appendChild(resizer);

      var startX, startWidth, cells;
      function onMouseMove(e) {
        var dx = e.clientX - startX;
        var newWidth = Math.max(minWidth, startWidth + dx);
        cells.forEach(function(cell) {
          cell.style.width = newWidth + 'px';
          cell.style.minWidth = newWidth + 'px';
          cell.style.maxWidth = newWidth + 'px';
        });
      }
      function onMouseUp() {
        document.body.classList.remove('col-resizing');
        cells.forEach(function(cell) { cell.classList.remove('col-resizing'); });
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
      }
      resizer.addEventListener('mousedown', function(e) {
        e.preventDefault();
        e.stopPropagation();
        startX = e.clientX;
        startWidth = th.getBoundingClientRect().width;
        cells = [th];
        Array.from(tbody.rows).forEach(function(r) {
          if (r.cells[colIdx]) cells.push(r.cells[colIdx]);
        });
        document.body.classList.add('col-resizing');
        cells.forEach(function(cell) { cell.classList.add('col-resizing'); });
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
      });
    });
  }
  makeResizable();
})();