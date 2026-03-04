/**
 * Basic coverage for dashboard-mentorship.js fallback paths (no jQuery present).
 */
describe('dashboard-mentorship.js', () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <form id="mentorship-form-create">
        <div id="mentorship-form-builder"></div>
        <textarea id="mentorship-form-json"></textarea>
        <div id="mentorship-form-builder-status"></div>
        <select id="mentorship-form-partner"></select>
        <select id="mentorship-form-public-key"></select>
      </form>
      <select id="mentorship-csv-partner"></select>
      <select id="mentorship-csv-type"></select>
      <select id="mentorship-csv-form"></select>
      <textarea id="mentorship-csv-private-key"></textarea>
      <button id="mentorship-csv-download-btn"></button>
      <div id="mentorship-csv-status"></div>
    `;
    // Ensure no jQuery present to hit fallback branch
    global.jQuery = undefined;
  });

  afterEach(() => {
    jest.resetModules();
    document.body.innerHTML = '';
    delete global.jQuery;
  });

  test('loads without throwing when builder libs are absent', () => {
    expect(() => require('../dashboard-mentorship.js')).not.toThrow();
    const status = document.getElementById('mentorship-form-builder-status');
    expect(status).not.toBeNull();
    // Fallback should reveal status message
    expect(status.textContent).toContain('Visual builder unavailable');
  });

  test('filters public keys by partner and enforces selection', () => {
    const jq = jest.fn(() => ({ formBuilder: jest.fn(() => ({ actions: { getData: () => '[{"name":"x"}]' } })) }));
    jq.fn = { formBuilder: true };
    global.jQuery = jq;
    document.body.innerHTML = `
      <form id="mentorship-form-create">
        <div id="mentorship-form-builder"></div>
        <textarea id="mentorship-form-json"></textarea>
        <div id="mentorship-form-builder-status"></div>
        <select id="mentorship-form-partner">
          <option value="p1">P1</option>
          <option value="p2">P2</option>
        </select>
        <select id="mentorship-form-public-key">
          <option data-partner-id="p1" value="k1">K1</option>
          <option data-partner-id="p2" value="k2">K2</option>
        </select>
      </form>
      <select id="mentorship-csv-partner"></select>
      <select id="mentorship-csv-type"></select>
      <select id="mentorship-csv-form"></select>
      <textarea id="mentorship-csv-private-key"></textarea>
      <button id="mentorship-csv-download-btn"></button>
      <div id="mentorship-csv-status"></div>
    `;
    require('../dashboard-mentorship.js');
    const partnerField = document.getElementById('mentorship-form-partner');
    const keyField = document.getElementById('mentorship-form-public-key');
    // Change to partner p2 should hide other option
    partnerField.value = 'p2';
    partnerField.dispatchEvent(new window.Event('change', { bubbles: true }));
    expect(keyField.value).toBe('k2');
    expect(keyField.options[0].hidden).toBe(true);
  });

  test('uses formBuilder when jQuery is available and validates empty form', () => {
    const actions = { getData: jest.fn(() => '[]') };
    const fbInstance = { actions };
    const jq = jest.fn(() => ({ formBuilder: jest.fn(() => fbInstance) }));
    jq.fn = { formBuilder: true };
    global.jQuery = jq;
    document.body.innerHTML = `
      <form id="mentorship-form-create">
        <div id="mentorship-form-builder"></div>
        <textarea id="mentorship-form-json"></textarea>
        <div id="mentorship-form-builder-status"></div>
        <select id="mentorship-form-partner"><option value="p1">P1</option></select>
        <select id="mentorship-form-public-key"><option data-partner-id="p1" value="k1">K1</option></select>
      </form>
      <select id="mentorship-csv-partner"></select>
      <select id="mentorship-csv-type"></select>
      <select id="mentorship-csv-form"></select>
      <textarea id="mentorship-csv-private-key"></textarea>
      <button id="mentorship-csv-download-btn"></button>
      <div id="mentorship-csv-status"></div>
    `;
    require('../dashboard-mentorship.js');
    const form = document.getElementById('mentorship-form-create');
    const status = document.getElementById('mentorship-form-builder-status');
    form.dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true }));
    expect(status.textContent).toContain('Add at least one field');
  });

  test('csv download shows message when WebCrypto missing', () => {
    document.body.innerHTML = `
      <select id="mentorship-csv-partner"></select>
      <select id="mentorship-csv-type"></select>
      <select id="mentorship-csv-form"></select>
      <textarea id="mentorship-csv-private-key"></textarea>
      <button id="mentorship-csv-download-btn"></button>
      <div id="mentorship-csv-status"></div>
    `;
    // Ensure the rest of the DOM required by the first IIFE is absent so it returns early
    global.crypto = undefined;
    require('../dashboard-mentorship.js');
    const btn = document.getElementById('mentorship-csv-download-btn');
    btn.click();
    const status = document.getElementById('mentorship-csv-status');
    expect(status.textContent).toContain('WebCrypto is not available');
  });

  test('csv download decrypts responses and updates status', async () => {
    jest.resetModules();
    const forms = [
      { id: 1, partner_id: 'p1', created_at: '2024-01-01', json: [{ name: 'field', label: 'Field' }] },
    ];
    const responses = [
      { form_id: 1, username: 'alice', created_at: '2024-01-02', data: { __encrypted__: true, key: 'AA==', nonce: 'AA==', ciphertext: 'AA==' } },
    ];
    document.body.innerHTML = `
      <select id="mentorship-csv-partner"><option value="p1">P1</option></select>
      <select id="mentorship-csv-type"><option value="mentor">mentor</option></select>
      <select id="mentorship-csv-form"><option value="1">1</option></select>
      <textarea id="mentorship-csv-private-key">-----BEGIN PRIVATE KEY-----abc-----END PRIVATE KEY-----</textarea>
      <button id="mentorship-csv-download-btn"></button>
      <div id="mentorship-csv-status"></div>
      <script id="mentorship-forms-mentor-data" type="application/json">${JSON.stringify(forms)}</script>
      <script id="mentorship-forms-mentee-data" type="application/json">[]</script>
      <script id="mentorship-responses-mentor-data" type="application/json">${JSON.stringify(responses)}</script>
      <script id="mentorship-responses-mentee-data" type="application/json">[]</script>
    `;
    const subtle = {
      importKey: jest.fn().mockResolvedValue({}),
      decrypt: jest.fn().mockResolvedValue(new TextEncoder().encode('{"field":"value"}')),
    };
    Object.defineProperty(window, 'crypto', { value: { subtle }, configurable: true });
    global.crypto = window.crypto;
    if (!window.URL) {
      window.URL = {};
    }
    window.URL.createObjectURL = jest.fn().mockReturnValue('blob:url');
    const origCreate = document.createElement.bind(document);
    jest.spyOn(document, 'createElement').mockImplementation((tag) => {
      const el = origCreate(tag);
      if (tag === 'a') {
        el.click = () => {};
      }
      return el;
    });

    require('../dashboard-mentorship.js');
    // Ensure crypto still set after module load
    Object.defineProperty(window, 'crypto', { value: { subtle }, configurable: true });
    global.crypto = window.crypto;
    const btn = document.getElementById('mentorship-csv-download-btn');
    await btn.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await Promise.resolve();
    const status = document.getElementById('mentorship-csv-status');
    expect(status.textContent).toContain('response(s) decrypted');
    expect(subtle.decrypt).toHaveBeenCalled();
  });
});
