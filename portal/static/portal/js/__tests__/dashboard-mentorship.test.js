/**
 * Basic coverage for dashboard-mentorship.js fallback paths (no jQuery present).
 */
function renderMentorshipDom(extraHtml = '') {
  document.body.innerHTML = `
    <select id="mentorship-partner-global">
      <option value="p1">P1</option>
      <option value="p2">P2</option>
    </select>

    <form id="mentorship-form-create">
      <div id="mentorship-form-builder"></div>
      <textarea id="mentorship-form-json"></textarea>
      <div id="mentorship-form-builder-status"></div>
      <input id="mentorship-form-partner" />
      <select id="mentorship-form-type">
        <option value="mentor" selected>mentor</option>
        <option value="mentee">mentee</option>
      </select>
      <select id="mentorship-form-public-key">
        <option data-partner-id="p1" value="k1">K1</option>
        <option data-partner-id="p2" value="k2">K2</option>
      </select>
    </form>

    <form id="mentorship-form-update">
      <input id="mentorship-form-update-partner" />
      <input id="mentorship-form-update-type" />
      <select id="mentorship-form-update-id"></select>
      <input id="mentorship-form-update-json" />
      <button type="button" id="mentorship-form-load-btn"></button>
      <button type="submit" id="mentorship-form-update-btn"></button>
    </form>

    <select id="mentorship-csv-type"><option value="mentor" selected>mentor</option></select>
    <select id="mentorship-csv-form"></select>
    <textarea id="mentorship-csv-private-key"></textarea>
    <button id="mentorship-csv-download-btn"></button>
    <div id="mentorship-csv-status"></div>
    <div id="mentorship-csv-summary"></div>
    <div id="mentorship-csv-respondents"></div>

    ${extraHtml}
  `;
}

describe('dashboard-mentorship.js', () => {
  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ results: [] }),
    });
    window.fetch = global.fetch;
    if (!global.URL) {
      global.URL = {};
    }
    global.URL.createObjectURL = jest.fn().mockReturnValue('blob:url');
    global.URL.revokeObjectURL = jest.fn();
    window.URL = global.URL;
    renderMentorshipDom();
    // Ensure no jQuery present to hit fallback branch
    global.jQuery = undefined;
  });

  afterEach(() => {
    jest.resetModules();
    document.body.innerHTML = '';
    delete global.jQuery;
    delete global.fetch;
    delete window.fetch;
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
    renderMentorshipDom();
    require('../dashboard-mentorship.js');
    const partnerField = document.getElementById('mentorship-partner-global');
    const keyField = document.getElementById('mentorship-form-public-key');
    // Change to partner p2 should hide other option
    partnerField.value = 'p2';
    partnerField.dispatchEvent(new window.Event('change', { bubbles: true }));
    expect(keyField.value).toBe('k2');
    expect(keyField.options[0].hidden).toBe(true);
  });

  test('hydrates all QID labels with a single request to /portal/qid-labels/', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        labels: { Q123: 'Facilitation', Q456: 'Wikidata Item' },
      }),
    });
    window.fetch = global.fetch;
    renderMentorshipDom(`
      <select id="mentorship-settings-skills">
        <option value="1" data-skill-qid="Q123">Q123</option>
      </select>
      <span data-skill-qid="Q123">Q123</span>
      <span data-qid-label="Q456">Q456</span>
    `);

    require('../dashboard-mentorship.js');
    await Promise.resolve();
    await Promise.resolve();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(global.fetch).toHaveBeenCalledWith(
      '/portal/qid-labels/',
      expect.objectContaining({ credentials: 'same-origin' })
    );
    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(document.querySelector('#mentorship-settings-skills option').textContent).toBe('Facilitation (Q123)');
    expect(document.querySelector('span[data-skill-qid="Q123"]').textContent).toBe('Facilitation');
    expect(document.querySelector('span[data-qid-label="Q456"]').textContent).toBe('Wikidata Item');
  });

  test('uses formBuilder when jQuery is available and validates empty form', () => {
    const actions = { getData: jest.fn(() => '[]') };
    const fbInstance = { actions };
    const jq = jest.fn(() => ({ formBuilder: jest.fn(() => fbInstance) }));
    jq.fn = { formBuilder: true };
    global.jQuery = jq;
    renderMentorshipDom();
    require('../dashboard-mentorship.js');
    const form = document.getElementById('mentorship-form-create');
    const status = document.getElementById('mentorship-form-builder-status');
    form.dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true }));
    expect(status.textContent).toContain('Add at least one field');
  });

  test('csv download shows message when WebCrypto missing', () => {
    renderMentorshipDom();
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
    renderMentorshipDom(`
      <script id="mentorship-forms-mentor-data" type="application/json">${JSON.stringify(forms)}</script>
      <script id="mentorship-forms-mentee-data" type="application/json">[]</script>
      <script id="mentorship-responses-mentor-data" type="application/json">${JSON.stringify(responses)}</script>
      <script id="mentorship-responses-mentee-data" type="application/json">[]</script>
    `);
    document.getElementById('mentorship-csv-form').innerHTML = '<option value="1">1</option>';
    document.getElementById('mentorship-csv-private-key').value = '-----BEGIN PRIVATE KEY-----abc-----END PRIVATE KEY-----';
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
    window.URL.revokeObjectURL = jest.fn();
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

  test('csv clears private key when selected form changes', async () => {
    jest.resetModules();
    const forms = [
      { id: 1, partner_id: 'p1', created_at: '2024-01-01', public_key_id: 11, public_key_fingerprint: 'abc111', json: [] },
      { id: 2, partner_id: 'p1', created_at: '2024-01-02', public_key_id: 22, public_key_fingerprint: 'def222', json: [] },
    ];
    renderMentorshipDom(`
      <script id="mentorship-forms-mentor-data" type="application/json">${JSON.stringify(forms)}</script>
      <script id="mentorship-forms-mentee-data" type="application/json">[]</script>
      <script id="mentorship-responses-mentor-data" type="application/json">[]</script>
      <script id="mentorship-responses-mentee-data" type="application/json">[]</script>
      <div id="mentorship-csv-required-key"></div>
    `);

    require('../dashboard-mentorship.js');
    const privateKeyInput = document.getElementById('mentorship-csv-private-key');
    const formSelect = document.getElementById('mentorship-csv-form');
    const status = document.getElementById('mentorship-csv-status');

    privateKeyInput.value = '-----BEGIN PRIVATE KEY-----abc-----END PRIVATE KEY-----';
    formSelect.value = '2';
    formSelect.dispatchEvent(new window.Event('change', { bubbles: true }));

    expect(privateKeyInput.value).toBe('');
    expect(status.textContent).toContain('Private key cleared because form changed');
  });

  test('csv blocks export when selected form has mixed key lineage', async () => {
    jest.resetModules();
    const forms = [
      { id: 1, partner_id: 'p1', created_at: '2024-01-01', public_key_id: 11, public_key_fingerprint: 'abc111', json: [{ name: 'field', label: 'Field' }] },
    ];
    const responses = [
      {
        form_id: 1,
        username: 'alice',
        created_at: '2024-01-02',
        encrypted_with_public_key_id: 11,
        encrypted_with_public_key_fingerprint: 'abc111',
        data: { __encrypted__: true, key: 'AA==', nonce: 'AA==', ciphertext: 'AA==' },
      },
      {
        form_id: 1,
        username: 'bob',
        created_at: '2024-01-03',
        encrypted_with_public_key_id: 22,
        encrypted_with_public_key_fingerprint: 'def222',
        data: { __encrypted__: true, key: 'AA==', nonce: 'AA==', ciphertext: 'AA==' },
      },
    ];

    renderMentorshipDom(`
      <script id="mentorship-forms-mentor-data" type="application/json">${JSON.stringify(forms)}</script>
      <script id="mentorship-forms-mentee-data" type="application/json">[]</script>
      <script id="mentorship-responses-mentor-data" type="application/json">${JSON.stringify(responses)}</script>
      <script id="mentorship-responses-mentee-data" type="application/json">[]</script>
      <div id="mentorship-csv-required-key"></div>
    `);

    document.getElementById('mentorship-csv-private-key').value = '-----BEGIN PRIVATE KEY-----abc-----END PRIVATE KEY-----';

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
    window.URL.revokeObjectURL = jest.fn();

    require('../dashboard-mentorship.js');

    const btn = document.getElementById('mentorship-csv-download-btn');
    await btn.click();
    await new Promise((resolve) => setTimeout(resolve, 0));

    const status = document.getElementById('mentorship-csv-status');
    expect(status.textContent).toContain('Export blocked');
    expect(subtle.decrypt).not.toHaveBeenCalled();
  });
});
