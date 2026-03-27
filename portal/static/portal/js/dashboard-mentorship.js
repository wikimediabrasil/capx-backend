(function() {
  var skillNodes = Array.from(document.querySelectorAll('[data-skill-qid]'));
  var qidNodes   = Array.from(document.querySelectorAll('[data-qid-label]'));
  var allNodes   = skillNodes.concat(qidNodes);
  if (!allNodes.length || typeof window.fetch !== 'function') return;

  function applyLabels(labelByQid) {
    skillNodes.forEach(function(node) {
      var qid   = String(node.getAttribute('data-skill-qid') || '').trim();
      var label = labelByQid[qid];
      if (!qid || !label) return;
      if (node.tagName === 'OPTION') {
        node.textContent = label + ' (' + qid + ')';
      } else {
        node.textContent = label;
        node.title = qid;
      }
    });
    qidNodes.forEach(function(node) {
      var qid   = String(node.getAttribute('data-qid-label') || '').trim();
      var label = labelByQid[qid];
      if (!qid || !label) return;
      node.textContent = label;
      node.title = qid;
    });
  }

  function sortSkillOptionsAlphabetically() {
    var skillsSelect = document.getElementById('mentorship-settings-skills');
    if (!skillsSelect) return;
    var options = Array.from(skillsSelect.options);
    options.sort(function(a, b) {
      return (a.textContent || '').localeCompare((b.textContent || ''), undefined, { sensitivity: 'base' });
    });
    options.forEach(function(option) { skillsSelect.appendChild(option); });
  }

  window.fetch('/portal/qid-labels/', {
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    credentials: 'same-origin',
  })
    .then(function(response) {
      if (!response.ok) throw new Error('Unable to load labels');
      return response.json();
    })
    .then(function(payload) {
      applyLabels((payload && payload.labels) || {});
      sortSkillOptionsAlphabetically();
    })
    .catch(function() {
      // Keep QIDs as the fallback when labels are unavailable.
    });
})();

(function() {
  var globalPartnerField = document.getElementById('mentorship-partner-global');
  var formElement = document.getElementById('mentorship-form-create');
  var updateFormElement = document.getElementById('mentorship-form-update');
  var updatePartnerField = document.getElementById('mentorship-form-update-partner');
  var updateTypeField = document.getElementById('mentorship-form-update-type');
  var updateFormIdField = document.getElementById('mentorship-form-update-id');
  var updateJsonField = document.getElementById('mentorship-form-update-json');
  var loadBtn = document.getElementById('mentorship-form-load-btn');
  var builderHost = document.getElementById('mentorship-form-builder');
  var outputField = document.getElementById('mentorship-form-json');
  var statusEl = document.getElementById('mentorship-form-builder-status');
  var partnerField = document.getElementById('mentorship-form-partner');
  var formTypeField = document.getElementById('mentorship-form-type');
  var keyField = document.getElementById('mentorship-form-public-key');
  if (!formElement || !updateFormElement || !builderHost || !outputField || !statusEl || !partnerField || !formTypeField || !keyField || !globalPartnerField || !updatePartnerField || !updateTypeField || !updateFormIdField || !updateJsonField || !loadBtn) return;

  function parseJsonScript(id) {
    var el = document.getElementById(id);
    if (!el) return [];
    try { return JSON.parse(el.textContent || '[]'); } catch (e) { return []; }
  }

  var mentorForms = parseJsonScript('mentorship-forms-mentor-data');
  var menteeForms = parseJsonScript('mentorship-forms-mentee-data');

  function filterPublicKeysByPartner() {
    var selectedPartner = String(globalPartnerField.value || '');
    partnerField.value = selectedPartner;
    updatePartnerField.value = selectedPartner;
    updateTypeField.value = String(formTypeField.value || 'mentor');
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
    repopulateEditForms();
  }

  function currentFormsForType() {
    return String(formTypeField.value || '') === 'mentee' ? menteeForms : mentorForms;
  }

  function repopulateEditForms() {
    var selectedPartner = String(globalPartnerField.value || '');
    var forms = currentFormsForType().filter(function(form) {
      return String(form.partner_id) === selectedPartner;
    });

    updateFormIdField.innerHTML = '';
    forms.forEach(function(form) {
      var opt = document.createElement('option');
      opt.value = String(form.id);
      opt.textContent = 'ID ' + form.id + ' · ' + (form.created_at || '');
      updateFormIdField.appendChild(opt);
    });

    if (!forms.length) {
      var emptyOpt = document.createElement('option');
      emptyOpt.value = '';
      emptyOpt.textContent = 'No forms for this partner/type';
      updateFormIdField.appendChild(emptyOpt);
    }
  }

  function loadSelectedFormIntoBuilder() {
    var selectedFormId = String(updateFormIdField.value || '');
    if (!selectedFormId) {
      statusEl.textContent = 'Select a form to load into the builder.';
      return;
    }
    var formDef = currentFormsForType().find(function(form) {
      return String(form.id) === selectedFormId;
    });
    if (!formDef) {
      statusEl.textContent = 'Selected form was not found.';
      return;
    }
    if (!formBuilderInstance || !formBuilderInstance.actions || typeof formBuilderInstance.actions.setData !== 'function') {
      statusEl.textContent = 'Loading existing forms is unavailable in this browser.';
      return;
    }
    try {
      formBuilderInstance.actions.setData(JSON.stringify(formDef.json || []));
      statusEl.textContent = 'Form loaded. Edit and save updates when ready.';
    } catch (error) {
      statusEl.textContent = 'Unable to load selected form into builder.';
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
    disabledAttrs: ['access', 'className'],
    disableHTMLLabels: true,
    showActionButtons: false,
    editOnAdd: true,
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

  updateFormElement.addEventListener('submit', function(event) {
    try {
      if (!updateFormIdField.value) {
        statusEl.textContent = 'Select a form to update.';
        event.preventDefault();
        return;
      }
      var dataJson = formBuilderInstance.actions.getData('json');
      if (!dataJson || dataJson === '[]') {
        statusEl.textContent = 'Add at least one field to the form before saving updates.';
        event.preventDefault();
        return;
      }
      updatePartnerField.value = String(globalPartnerField.value || '');
      updateTypeField.value = String(formTypeField.value || 'mentor');
      updateJsonField.value = dataJson;
    } catch (error) {
      statusEl.textContent = 'Unable to export JSON from visual builder.';
      event.preventDefault();
    }
  });

  formTypeField.addEventListener('change', function() {
    updateTypeField.value = String(formTypeField.value || 'mentor');
    filterPublicKeysByPartner();
  });
  globalPartnerField.addEventListener('change', filterPublicKeysByPartner);
  loadBtn.addEventListener('click', loadSelectedFormIntoBuilder);
  filterPublicKeysByPartner();
})();

(function() {
  var partnerSelect = document.getElementById('mentorship-partner-global');
  var typeSelect = document.getElementById('mentorship-csv-type');
  var formSelect = document.getElementById('mentorship-csv-form');
  var privateKeyInput = document.getElementById('mentorship-csv-private-key');
  var downloadBtn = document.getElementById('mentorship-csv-download-btn');
  var statusEl = document.getElementById('mentorship-csv-status');
  var summaryEl = document.getElementById('mentorship-csv-summary');
  var respondentsEl = document.getElementById('mentorship-csv-respondents');
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

  var userProfileColumns = [
    { key: 'is_staff', label: 'user_is_staff' },
    { key: 'is_active', label: 'user_is_active' },
    { key: 'date_joined', label: 'user_date_joined' },
    { key: 'last_update', label: 'user_last_update' },
    { key: 'last_login', label: 'user_last_login' },
    { key: 'wikidata_qid', label: 'user_wikidata_qid' },
    { key: 'wiki_alt', label: 'user_wiki_alt' },
    { key: 'territory', label: 'user_territory' },
    { key: 'language', label: 'user_language' },
    { key: 'affiliation', label: 'user_affiliation' },
    { key: 'wikimedia_project', label: 'user_wikimedia_project' },
    { key: 'team', label: 'user_team' },
    { key: 'skills_known_qids', label: 'user_skills_known_qids' },
    { key: 'skills_available_qids', label: 'user_skills_available_qids' },
    { key: 'skills_wanted_qids', label: 'user_skills_wanted_qids' },
    { key: 'is_manager', label: 'user_is_manager' },
    { key: 'badges', label: 'user_badges' },
    { key: 'automated_lets_connect', label: 'user_automated_lets_connect' },
  ];

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

  function stringifyUserLanguage(value) {
    if (!Array.isArray(value)) return stringifyCellValue(value);
    return value.map(function(langItem) {
      if (!langItem || typeof langItem !== 'object') return stringifyCellValue(langItem);
      var name = langItem.name || '';
      var prof = langItem.proficiency || '';
      if (!name && !prof) return '';
      if (!name) return prof;
      if (!prof) return name;
      return name + ' (' + prof + ')';
    }).filter(Boolean).join('; ');
  }

  function getUserProfileCell(row, key) {
    var profile = (row && row.user_profile && typeof row.user_profile === 'object') ? row.user_profile : {};
    var value = profile[key];
    if (key === 'language') return stringifyUserLanguage(value);
    return stringifyCellValue(value);
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
    refreshResponseSummary();
  }

  function refreshResponseSummary() {
    if (!summaryEl && !respondentsEl) return;
    var selectedFormId = String(formSelect.value || '');
    if (!selectedFormId) {
      if (summaryEl) summaryEl.textContent = 'No form selected.';
      if (respondentsEl) respondentsEl.textContent = '';
      return;
    }
    var rows = currentResponses().filter(function(r) { return String(r.form_id) === selectedFormId; });
    if (summaryEl) {
      summaryEl.textContent = 'Responses available: ' + rows.length;
    }
    if (respondentsEl) {
      if (!rows.length) {
        respondentsEl.textContent = 'No respondents yet for this form.';
        return;
      }
      var users = rows.map(function(r) { return String(r.username || '').trim(); }).filter(Boolean);
      var uniqueUsers = Array.from(new Set(users)).sort(function(a, b) { return a.localeCompare(b); });
      respondentsEl.textContent = 'Respondents: ' + uniqueUsers.join(', ');
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
      userProfileColumns.forEach(function(col) {
        header.push(col.label);
      });
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

        userProfileColumns.forEach(function(col) {
          lineParts.push(escapeCSV(getUserProfileCell(currentRow, col.key)));
        });

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
  formSelect.addEventListener('change', refreshResponseSummary);
  downloadBtn.addEventListener('click', function() { handleDownload(); });
  repopulateForms();
})();