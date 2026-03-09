/**
 * Basic DOM-driven tests for dashboard-users.js
 */
function setupDom() {
  document.body.innerHTML = `
    <div>
      <button id="users-csv-btn"></button>
      <div id="users-col-toggles"></div>
      <div class="card"><table id="users-table">
        <thead><tr><th>Username</th><th>Updated</th></tr></thead>
        <tbody>
          <tr><td>Alice</td><td>2023-01-01</td></tr>
          <tr><td>Bob</td><td>2024-01-01</td></tr>
        </tbody>
      </table></div>
      <input id="users-filter-input" />
      <div id="users-row-limit-info"></div>
      <button id="users-toggle-limit-btn"></button>
    </div>
  `;
  // Mock URL for CSV download
  global.URL.createObjectURL = () => 'blob:url';
  global.Blob = window.Blob;
}

describe('dashboard-users.js', () => {
  beforeEach(() => {
    setupDom();
  });

  afterEach(() => {
    jest.resetModules();
    document.body.innerHTML = '';
  });

  test('filters rows when typing', () => {
    require('../dashboard-users.js');
    const filter = document.getElementById('users-filter-input');
    expect(filter).not.toBeNull();
    const rows = Array.from(document.querySelectorAll('#users-table tbody tr'));
    filter.value = 'bob';
    filter.dispatchEvent(new window.Event('input', { bubbles: true }));
    const displays = rows.map((r) => r.style.display);
    expect(displays[0]).toBe('none');
    expect(displays[1]).toBe('');
  });

  test('sorts rows on header click', () => {
    require('../dashboard-users.js');
    const header = document.querySelector('#users-table thead th');
    header.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    const firstRowText = document.querySelector('#users-table tbody tr td').textContent;
    // After sort asc by username, Alice should remain first (already sorted)
    expect(firstRowText).toBe('Alice');
    // Toggle sort desc
    header.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
    const firstRowTextDesc = document.querySelector('#users-table tbody tr td').textContent;
    expect(firstRowTextDesc).toBe('Bob');
  });

  test('column toggle hides column and csv respects visible columns', () => {
    require('../dashboard-users.js');
    const toggle = document.getElementById('toggle-col-1');
    expect(toggle).not.toBeNull();
    toggle.checked = false;
    toggle.dispatchEvent(new window.Event('change', { bubbles: true }));
    // Updated header visibility
    const header2 = document.querySelectorAll('#users-table thead th')[1];
    expect(header2.style.display).toBe('none');
    // Trigger CSV download; ensure createObjectURL called
    const createSpy = jest.spyOn(URL, 'createObjectURL');
    document.getElementById('users-csv-btn').click();
    expect(createSpy).toHaveBeenCalled();
    createSpy.mockRestore();
  });

  test('row limit toggle works', () => {
    require('../dashboard-users.js');
    const info = document.getElementById('users-row-limit-info');
    const btn = document.getElementById('users-toggle-limit-btn');
    // Initially limitOn true, info set
    expect(info.textContent).toContain('Showing');
    btn.click(); // toggles limitOff then back
    btn.click();
    expect(info.textContent).toContain('Showing');
  });
});
