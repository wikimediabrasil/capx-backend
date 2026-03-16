(function() {
  var translatableSkillNodes = Array.from(document.querySelectorAll('[data-skill-qid]'));
  if (!translatableSkillNodes.length || typeof window.fetch !== 'function') return;

  function applySkillLabels(labelByQid) {
    translatableSkillNodes.forEach(function(node) {
      var qid = String(node.getAttribute('data-skill-qid') || '').trim();
      if (!qid) return;

      var label = labelByQid[qid];
      if (!label) return;

      if (node.tagName === 'OPTION') {
        node.textContent = label + ' (' + qid + ')';
        return;
      }

      node.textContent = label;
      node.title = qid;
    });
  }

  window.fetch('/translating/?lang=mul&fallback=en', {
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    credentials: 'same-origin',
  })
    .then(function(response) {
      if (!response.ok) {
        throw new Error('Unable to load skill labels');
      }
      return response.json();
    })
    .then(function(payload) {
      var labelByQid = {};
      var results = Array.isArray(payload && payload.results) ? payload.results : [];

      results.forEach(function(item) {
        var qid = String((item && item.qid) || '').trim();
        if (!qid) return;

        var label = item.label || item.fallback_label || '';
        if (label) {
          labelByQid[qid] = label;
        }
      });

      applySkillLabels(labelByQid);
    })
    .catch(function() {
      // Keep QIDs as the fallback when translations are unavailable.
    });
})();

(function() {
  var formElement = document.getElementById('mentorship-form-create');
  var builderHost = document.getElementById('mentorship-form-builder');
  var outputField = document.getElementById('mentorship-form-json');
  var statusEl = document.getElementById('mentorship-form-builder-status');
  var partnerField = document.getElementById('mentorship-form-partner');
  var keyField = document.getElementById('mentorship-form-public-key');
  if (!formElement || !builderHost || !outputField || !statusEl || !partnerField || !keyField) return;

  function filterPublicKeysByPartner() {
    var selectedPartner = String(partnerField.value || '');
    var firstVisible = null;
    Array.from(keyField.options).forEach(function(option) {
      var visible = String(option.dataset.partnerId || '') === selectedPartner;
      option.hidden = !visible;
      if (visible && !firstVisible) firstVisible = option;
    });
    if (!keyField.selectedOptions.length || keyField.selectedOptions[0].hidden) {
      if (firstVisible) {
        keyField.value = firstVisible.value;
      } else {
        keyField.value = '';
      }
    }
    if (!firstVisible) {
      statusEl.textContent = 'Create a public key for this partner before saving a form.';
    }
  }

  var jq = globalThis.jQuery;
  if (!jq || !jq.fn || !jq.fn.formBuilder) {
    outputField.style.display = '';
    statusEl.textContent = 'Visual builder unavailable. Fill the JSON manually.';
    return;
  }

  var formBuilderInstance = jq(builderHost).formBuilder({
    disableFields: ['autocomplete', 'hidden', 'file', 'button'],
    showActionButtons: false,
  });

  formElement.addEventListener('submit', function(event) {
    try {
      var dataJson = formBuilderInstance.actions.getData('json');
      if (!dataJson || dataJson === '[]') {
        statusEl.textContent = 'Add at least one field to the form before saving.';
        event.preventDefault();
        return;
      }
      outputField.value = dataJson;
    } catch (error) {
      statusEl.textContent = 'Unable to export JSON from visual builder.';
      event.preventDefault();
    }
  });

  partnerField.addEventListener('change', filterPublicKeysByPartner);
  filterPublicKeysByPartner();
})();

(function() {
  var partnerSelect = document.getElementById('mentorship-csv-partner');
  var typeSelect = document.getElementById('mentorship-csv-type');
  var formSelect = document.getElementById('mentorship-csv-form');
  var privateKeyInput = document.getElementById('mentorship-csv-private-key');
  var downloadBtn = document.getElementById('mentorship-csv-download-btn');
  var statusEl = document.getElementById('mentorship-csv-status');
  if (!partnerSelect || !typeSelect || !formSelect || !privateKeyInput || !downloadBtn || !statusEl) return;

  function parseJsonScript(id) {
    var el = document.getElementById(id);
    if (!el) return [];
    try { return JSON.parse(el.textContent || '[]'); } catch (e) { return []; }
  }

  var mentorForms = parseJsonScript('mentorship-forms-mentor-data');
  var menteeForms = parseJsonScript('mentorship-forms-mentee-data');
  var mentorResponses = parseJsonScript('mentorship-responses-mentor-data');
  var menteeResponses = parseJsonScript('mentorship-responses-mentee-data');

  function currentForms() {
    return typeSelect.value === 'mentor' ? mentorForms : menteeForms;
  }

  function currentResponses() {
    return typeSelect.value === 'mentor' ? mentorResponses : menteeResponses;
  }

  function getSelectedFormDefinition(formId) {
    var forms = currentForms();
    for (var i = 0; i < forms.length; i++) {
      if (String(forms[i].id) === String(formId)) return forms[i];
    }
    return null;
  }

  function normalizeFieldKey(key) {
    var s = String(key || '');
    if (s.endsWith('[]')) return s.slice(0, -2);
    return s;
  }

  function toObjectValue(value) {
    if (value == null) return {};
    if (typeof value === 'object' && !Array.isArray(value)) return value;
    if (typeof value !== 'string') return { value: value };
    try {
      var parsed = JSON.parse(value);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return parsed;
      return { value: parsed };
    } catch (error) {
      return { value: value };
    }
  }

  function stringifyCellValue(value) {
    if (Array.isArray(value)) return value.join('; ');
    if (value && typeof value === 'object') return JSON.stringify(value);
    return value == null ? '' : String(value);
  }

  function buildSchemaFieldMap(formDefinition) {
    var schema = (formDefinition && formDefinition.json) || [];
    var map = {};
    if (!Array.isArray(schema)) return map;
    schema.forEach(function(field) {
      var key = normalizeFieldKey(field && field.name);
      if (!key) return;
      var label = (field && field.label) ? String(field.label).trim() : key;
      map[key] = label || key;
    });
    return map;
  }

  function repopulateForms() {
    var pid = String(partnerSelect.value || '');
    var forms = currentForms().filter(function(f) { return String(f.partner_id) === pid; });
    formSelect.innerHTML = '';
    forms.forEach(function(f) {
      var opt = document.createElement('option');
      opt.value = String(f.id);
      opt.textContent = 'ID ' + f.id + ' · ' + (f.created_at || '');
      formSelect.appendChild(opt);
    });
    if (!forms.length) {
      var emptyOpt = document.createElement('option');
      emptyOpt.value = '';
      emptyOpt.textContent = 'No forms for this partner/type';
      formSelect.appendChild(emptyOpt);
    }
  }

  function b64ToBytes(base64) {
    var binary = atob(base64);
    var len = binary.length;
    var bytes = new Uint8Array(len);
    for (var i = 0; i < len; i++) bytes[i] = binary.charCodeAt(i);
    return bytes;
  }

  function pemToArrayBuffer(pem) {
    var clean = (pem || '')
      .replace('-----BEGIN PRIVATE KEY-----', '')
      .replace('-----END PRIVATE KEY-----', '')
      .replace(/\s+/g, '');
    return b64ToBytes(clean).buffer;
  }

  async function importPrivateKey(pem) {
    return await window.crypto.subtle.importKey(
      'pkcs8',
      pemToArrayBuffer(pem),
      { name: 'RSA-OAEP', hash: 'SHA-256' },
      false,
      ['decrypt']
    );
  }

  async function decryptPayload(recordData, privateKey) {
    var payload = (typeof recordData === 'string') ? JSON.parse(recordData) : recordData;
    if (!payload || payload.__encrypted__ !== true) return recordData;

    var encryptedKey = b64ToBytes(payload.key);
    var nonce = b64ToBytes(payload.nonce);
    var ciphertext = b64ToBytes(payload.ciphertext);

    var aesRawKey = await window.crypto.subtle.decrypt(
      { name: 'RSA-OAEP' },
      privateKey,
      encryptedKey
    );
    var aesKey = await window.crypto.subtle.importKey(
      'raw',
      aesRawKey,
      { name: 'AES-GCM' },
      false,
      ['decrypt']
    );
    var plainBuffer = await window.crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: nonce },
      aesKey,
      ciphertext
    );
    return new TextDecoder().decode(plainBuffer);
  }

  function escapeCSV(value) {
    var s = String(value == null ? '' : value).replace(/"/g, '""');
    return '"' + s + '"';
  }

  function downloadCSV(lines, fileName) {
    var csv = lines.join('\r\n');
    var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    setTimeout(function() { URL.revokeObjectURL(url); a.remove(); }, 0);
  }

  async function handleDownload() {
    if (!window.crypto || !window.crypto.subtle) {
      statusEl.textContent = 'WebCrypto is not available in this browser.';
      return;
    }
    var formId = String(formSelect.value || '');
    if (!formId) {
      statusEl.textContent = 'Select a form first.';
      return;
    }
    var privatePem = privateKeyInput.value.trim();
    if (!privatePem) {
      statusEl.textContent = 'Paste a private key in PEM format.';
      return;
    }

    statusEl.textContent = 'Decrypting responses...';

    try {
      var privateKey = await importPrivateKey(privatePem);
      var rows = currentResponses().filter(function(r) { return String(r.form_id) === formId; });
      var selectedForm = getSelectedFormDefinition(formId);
      var schemaFieldMap = buildSchemaFieldMap(selectedForm);
      var decryptedObjects = [];
      var dynamicKeys = Object.keys(schemaFieldMap);
      var dynamicKeySet = {};
      dynamicKeys.forEach(function(key) { dynamicKeySet[key] = true; });

      for (var i = 0; i < rows.length; i++) {
        var row = rows[i];
        var decrypted = await decryptPayload(row.data, privateKey);
        var responseObject = toObjectValue(decrypted);
        decryptedObjects.push(responseObject);

        Object.keys(responseObject).forEach(function(rawKey) {
          var key = normalizeFieldKey(rawKey);
          if (!dynamicKeySet[key]) {
            dynamicKeySet[key] = true;
            dynamicKeys.push(key);
          }
        });
      }

      var header = ['username', 'created_at'];
      dynamicKeys.forEach(function(key) {
        header.push(schemaFieldMap[key] || key);
      });
      var lines = [header.map(escapeCSV).join(',')];

      for (var j = 0; j < rows.length; j++) {
        var currentRow = rows[j];
        var currentObject = decryptedObjects[j] || {};
        var lineParts = [
          escapeCSV(currentRow.username),
          escapeCSV(currentRow.created_at),
        ];

        dynamicKeys.forEach(function(key) {
          var value = currentObject[key];
          lineParts.push(escapeCSV(stringifyCellValue(value)));
        });

        lines.push(lineParts.join(','));
      }

      var fileName = 'mentorship-' + typeSelect.value + '-form-' + formId + '.csv';
      downloadCSV(lines, fileName);
      statusEl.textContent = rows.length + ' response(s) decrypted and exported.';
    } catch (e) {
      statusEl.textContent = 'Unable to decrypt responses with this private key.';
    }
  }

  partnerSelect.addEventListener('change', repopulateForms);
  typeSelect.addEventListener('change', repopulateForms);
  downloadBtn.addEventListener('click', function() { handleDownload(); });
  repopulateForms();
})();