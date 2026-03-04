/**
 * Basic interactions for dashboard-badges.js
 */
function setupDom() {
  document.body.innerHTML = `
    <div>
      <button id="tab-badges-manage" aria-controls="panel-manage"></button>
      <button id="tab-badges-assign" aria-controls="panel-assign"></button>
      <div id="panel-badges-assign"></div>
      <select id="assignments-badge-select">
        <option value="1">Badge 1</option>
        <option value="2">Badge 2</option>
      </select>
      <ul id="awarded-users-list"></ul>
      <input id="assign-badge-hidden" />
      <form id="badge-remove-shared-form"></form>
      <input id="badge-remove-username" />
      <input id="badge-remove-badge-id" />
      <script id="partner-badges-awarded-data" type="application/json">{"1": ["alice"]}</script>
      <button data-action="manage-assign" data-badge-id="1"></button>
      <button data-action="manage-assign" data-badge-id="2"></button>
    </div>
  `;
}

describe('dashboard-badges.js', () => {
  beforeEach(() => {
    setupDom();
  });

  afterEach(() => {
    jest.resetModules();
    document.body.innerHTML = '';
  });

  test('clicking manage-assign populates hidden fields and list', () => {
    require('../dashboard-badges.js');
    const btn = document.querySelector('[data-action="manage-assign"]');
    expect(btn).not.toBeNull();
    btn.click();
    const hidden = document.getElementById('assign-badge-hidden');
    expect(hidden.value).toBe('1');
    const listItems = document.querySelectorAll('#awarded-users-list li');
    expect(listItems.length).toBe(1);
    expect(listItems[0].textContent.includes('alice')).toBe(true);
  });

  test('shows empty state', () => {
    document.getElementById('partner-badges-awarded-data').textContent = '{}';
    jest.resetModules();
    require('../dashboard-badges.js');
    const btn2 = document.querySelector('[data-action="manage-assign"][data-badge-id="2"]');
    btn2.click();
    const listItems = document.querySelectorAll('#awarded-users-list li');
    expect(listItems.length).toBe(1);
    expect(listItems[0].textContent).toContain('No users');
  });

  test('remove button populates form inputs', () => {
    document.getElementById('partner-badges-awarded-data').textContent = '{"2": ["bob"]}';
    jest.resetModules();
    const form = document.getElementById('badge-remove-shared-form');
    form.submit = jest.fn();
    require('../dashboard-badges.js');
    const btn2 = document.querySelector('[data-action="manage-assign"][data-badge-id="2"]');
    btn2.click();
    const removeBtn = document.querySelector('#awarded-users-list button');
    removeBtn.click();
    expect(document.getElementById('badge-remove-username').value).toBe('bob');
    expect(document.getElementById('badge-remove-badge-id').value).toBe('2');
  });
});
