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
  var cancelEditBtn = document.getElementById('mentorship-form-cancel-edit-btn');
  var createSaveBtn = document.getElementById('mentorship-form-save-btn');
  var updateSaveBtn = document.getElementById('mentorship-form-update-btn');
  var editModeNote = document.getElementById('mentorship-form-edit-mode-note');
  var builderHost = document.getElementById('mentorship-form-builder');
  var outputField = document.getElementById('mentorship-form-json');
  var statusEl = document.getElementById('mentorship-form-builder-status');
  var languageControls = document.getElementById('mentorship-form-language-controls');
  var languagesField = document.getElementById('mentorship-form-languages');
  var languageSearchField = document.getElementById('mentorship-form-language-search');
  var languageChips = document.getElementById('mentorship-form-language-chips');
  var languageSuggestions = document.getElementById('mentorship-form-language-suggestions');
  var editorLanguageField = document.getElementById('mentorship-form-editor-language');
  var partnerField = document.getElementById('mentorship-form-partner');
  var formTypeField = document.getElementById('mentorship-form-type');
  var keyField = document.getElementById('mentorship-form-public-key');
  if (!formElement || !updateFormElement || !builderHost || !outputField || !statusEl || !languageControls || !languagesField || !languageSearchField || !languageChips || !languageSuggestions || !editorLanguageField || !partnerField || !formTypeField || !keyField || !globalPartnerField || !updatePartnerField || !updateTypeField || !updateFormIdField || !updateJsonField || !loadBtn) return;

  var isEditingExistingForm = false;
  var languageSchemas = { en: [] };
  var activeEditorLanguage = 'en';
  var languageSearchOpen = false;

  function setEditMode(active) {
    isEditingExistingForm = !!active;

    formTypeField.disabled = isEditingExistingForm;
    keyField.disabled = isEditingExistingForm;

    if (createSaveBtn) {
      createSaveBtn.style.display = isEditingExistingForm ? 'none' : '';
      createSaveBtn.disabled = isEditingExistingForm;
    }
    if (updateSaveBtn) {
      updateSaveBtn.style.display = isEditingExistingForm ? '' : 'none';
      updateSaveBtn.disabled = !isEditingExistingForm;
    }
    if (cancelEditBtn) {
      cancelEditBtn.style.display = isEditingExistingForm ? '' : 'none';
    }
    if (editModeNote) {
      editModeNote.style.display = isEditingExistingForm ? '' : 'none';
    }
  }

  function parseJsonScript(id) {
    var el = document.getElementById(id);
    if (!el) return [];
    try { return JSON.parse(el.textContent || '[]'); } catch (e) { return []; }
  }

  var mentorForms = parseJsonScript('mentorship-forms-mentor-data');
  var menteeForms = parseJsonScript('mentorship-forms-mentee-data');

  function cloneSchema(schema) {
    return JSON.parse(JSON.stringify(Array.isArray(schema) ? schema : []));
  }

  function getTranslatedValue(translations, language, fallback) {
    if (!Array.isArray(translations)) return fallback;
    var match = translations.find(function(translation) {
      return translation && String(translation.lang || '') === language;
    });
    return match && typeof match.value === 'string' ? match.value : fallback;
  }

  function schemaWithoutTranslations(schema) {
    return cloneSchema(schema).map(function(field) {
      delete field['label-translations'];
      if (Array.isArray(field.values)) {
        field.values = field.values.map(function(option) {
          delete option['label-translations'];
          return option;
        });
      }
      return field;
    });
  }

  function findSchemaField(schema, field, index) {
    var fieldName = String(field && field.name || '').trim();
    if (fieldName) {
      return schema.find(function(candidate) {
        return candidate && String(candidate.name || '').trim() === fieldName;
      }) || null;
    }
    return schema[index] || null;
  }

  function findSchemaOption(options, option, index) {
    if (option && option.value != null) {
      return options.find(function(candidate) {
        return candidate && candidate.value != null && String(candidate.value) === String(option.value);
      }) || null;
    }
    return options[index] || null;
  }

  function schemaForLanguage(baseSchema, translatedSchema) {
    return baseSchema.map(function(field, index) {
      var translatedField = findSchemaField(translatedSchema, field, index);
      var localizedField = cloneSchema([field])[0];
      if (translatedField && typeof translatedField.label === 'string') {
        localizedField.label = translatedField.label;
      }
      delete localizedField['label-translations'];

      if (Array.isArray(field.values)) {
        localizedField.values = field.values.map(function(option, optionIndex) {
          var translatedOption = translatedField && Array.isArray(translatedField.values)
            ? findSchemaOption(translatedField.values, option, optionIndex)
            : null;
          var localizedOption = Object.assign({}, option);
          if (translatedOption && typeof translatedOption.label === 'string') {
            localizedOption.label = translatedOption.label;
          }
          delete localizedOption['label-translations'];
          return localizedOption;
        });
      }
      return localizedField;
    });
  }

  function readLanguageSchemas(schema) {
    var baseSchema = schemaWithoutTranslations(schema);
    var languages = ['en'];
    function addLanguage(language) {
      var code = String(language || '').trim();
      if (code && languages.indexOf(code) === -1) languages.push(code);
    }

    (Array.isArray(schema) ? schema : []).forEach(function(field) {
      (Array.isArray(field && field['label-translations']) ? field['label-translations'] : [])
        .forEach(function(translation) { addLanguage(translation && translation.lang); });
      (Array.isArray(field && field.values) ? field.values : []).forEach(function(option) {
        (Array.isArray(option && option['label-translations']) ? option['label-translations'] : [])
          .forEach(function(translation) { addLanguage(translation && translation.lang); });
      });
    });

    var result = { en: baseSchema };
    languages.slice(1).forEach(function(language) {
      result[language] = baseSchema.map(function(field, index) {
        var originalField = findSchemaField(Array.isArray(schema) ? schema : [], field, index) || {};
        var translatedField = Object.assign({}, field);
        translatedField.label = getTranslatedValue(
          originalField['label-translations'],
          language,
          field.label
        );
        if (Array.isArray(field.values)) {
          translatedField.values = field.values.map(function(option, index) {
            var originalOption = Array.isArray(originalField.values)
              ? findSchemaOption(originalField.values, option, index) || {}
              : {};
            var translatedOption = Object.assign({}, option);
            translatedOption.label = getTranslatedValue(
              originalOption['label-translations'],
              language,
              option.label
            );
            return translatedOption;
          });
        }
        return translatedField;
      });
    });
    return result;
  }

  function ensureLanguageOption(language) {
    if (Array.from(languagesField.options).some(function(option) { return option.value === language; })) return;
    var option = document.createElement('option');
    option.value = language;
    option.textContent = language;
    languagesField.appendChild(option);
  }

  function selectedLanguages() {
    var languages = Array.from(languagesField.selectedOptions).map(function(option) { return option.value; });
    if (languages.indexOf('en') === -1) {
      var englishOption = Array.from(languagesField.options).find(function(option) { return option.value === 'en'; });
      if (englishOption) englishOption.selected = true;
      languages.unshift('en');
    }
    return languages;
  }

  function selectedLanguageSet() {
    return new Set(selectedLanguages());
  }

  function renderLanguageSuggestions() {
    var query = String(languageSearchField.value || '').trim().toLocaleLowerCase();
    var selected = selectedLanguageSet();
    languageSuggestions.innerHTML = '';
    Array.from(languagesField.options).forEach(function(option) {
      if (selected.has(option.value)) return;
      if (query && option.textContent.toLocaleLowerCase().indexOf(query) === -1) return;
      var suggestion = document.createElement('button');
      suggestion.type = 'button';
      suggestion.setAttribute('role', 'option');
      suggestion.setAttribute('aria-selected', 'false');
      suggestion.textContent = option.textContent;
      suggestion.style.display = 'block';
      suggestion.style.width = '100%';
      suggestion.style.padding = '8px 10px';
      suggestion.style.border = '0';
      suggestion.style.borderRadius = '5px';
      suggestion.style.background = 'transparent';
      suggestion.style.textAlign = 'left';
      suggestion.addEventListener('mouseenter', function() {
        suggestion.style.background = '#f1f5f9';
      });
      suggestion.addEventListener('mouseleave', function() {
        suggestion.style.background = 'transparent';
      });
      suggestion.addEventListener('click', function() {
        option.selected = true;
        languagesField.dispatchEvent(new Event('change', { bubbles: true }));
        languageSearchField.value = '';
        languageSearchField.focus();
      });
      languageSuggestions.appendChild(suggestion);
    });
    languageSuggestions.hidden = !languageSearchOpen || languageSuggestions.children.length === 0;
    languageSearchField.setAttribute('aria-expanded', String(!languageSuggestions.hidden));
  }

  function renderLanguageChips() {
    var selected = selectedLanguageSet();
    languageChips.innerHTML = '';
    Array.from(languagesField.options).forEach(function(option) {
      if (!selected.has(option.value)) return;
      var chip = document.createElement('span');
      chip.className = 'chip';
      chip.style.margin = '0';
      chip.appendChild(document.createTextNode(option.textContent));
      if (option.value !== 'en') {
        var removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.setAttribute('aria-label', 'Remove ' + option.textContent);
        removeButton.textContent = '×';
        removeButton.style.padding = '0';
        removeButton.style.border = '0';
        removeButton.style.background = 'transparent';
        removeButton.style.color = 'inherit';
        removeButton.style.fontSize = '16px';
        removeButton.style.lineHeight = '12px';
        removeButton.addEventListener('click', function() {
          option.selected = false;
          languagesField.dispatchEvent(new Event('change', { bubbles: true }));
        });
        chip.appendChild(removeButton);
      }
      languageChips.appendChild(chip);
    });
    renderLanguageSuggestions();
  }

  function updateEditorLanguageOptions(languages) {
    editorLanguageField.innerHTML = '';
    languages.forEach(function(language) {
      var option = Array.from(languagesField.options).find(function(candidate) {
        return candidate.value === language;
      });
      var editorOption = document.createElement('option');
      editorOption.value = language;
      editorOption.textContent = option ? option.textContent : language;
      editorLanguageField.appendChild(editorOption);
    });
    if (languages.indexOf(activeEditorLanguage) === -1) activeEditorLanguage = 'en';
    editorLanguageField.value = activeEditorLanguage;
    languageControls.hidden = false;
  }

  function findTranslatedField(schema, field, index) {
    return findSchemaField(schema, field, index);
  }

  function captureEditorSchema() {
    try {
      var currentSchema = JSON.parse(formBuilderInstance.actions.getData('json'));
      if (!Array.isArray(currentSchema)) throw new Error('Form schema must be a list of fields.');
      languageSchemas[activeEditorLanguage] = schemaWithoutTranslations(currentSchema);
      return true;
    } catch (error) {
      statusEl.textContent = 'Unable to save the current language labels from the builder.';
      return false;
    }
  }

  function hasSameFormStructure(firstSchema, secondSchema) {
    function nonLabelSchema(schema) {
      return schema.map(function(field) {
        var normalizedField = Object.assign({}, field);
        delete normalizedField.label;
        delete normalizedField['label-translations'];
        if (Array.isArray(field.values)) {
          normalizedField.values = field.values.map(function(option) {
            var normalizedOption = Object.assign({}, option);
            delete normalizedOption.label;
            delete normalizedOption['label-translations'];
            return normalizedOption;
          });
        }
        return normalizedField;
      });
    }
    return JSON.stringify(nonLabelSchema(firstSchema)) === JSON.stringify(nonLabelSchema(secondSchema));
  }

  function setBuilderLanguage(language) {
    var baseSchema = languageSchemas.en || [];
    var translatedSchema = languageSchemas[language] || baseSchema;
    activeEditorLanguage = language;
    formBuilderInstance.actions.setData(JSON.stringify(
      schemaForLanguage(baseSchema, translatedSchema)
    ));
  }

  function buildSchemaWithTranslations() {
    if (!captureEditorSchema()) throw new Error('Unable to capture translated form labels.');
    var languages = selectedLanguages();
    var baseSchema = languageSchemas.en || [];
    var reservedResponseField = '__form_language';
    if (baseSchema.some(function(field) {
      return String(field.name || '').trim().replace(/\[\]$/, '') === reservedResponseField;
    })) {
      throw new Error('The field name "__form_language" is reserved for response language metadata.');
    }
    if (activeEditorLanguage !== 'en' && !hasSameFormStructure(baseSchema, languageSchemas[activeEditorLanguage] || [])) {
      throw new Error('Switch to English to change the form structure or field settings; other languages can only edit labels and option names.');
    }
    return baseSchema.map(function(field, index) {
      var savedField = Object.assign({}, field);
      delete savedField['label-translations'];
      var translatedFields = languages.slice(1).map(function(language) {
        var localizedField = findTranslatedField(languageSchemas[language] || [], field, index);
        return {
          lang: language,
          value: localizedField && typeof localizedField.label === 'string'
            ? localizedField.label
            : String(field.label || ''),
        };
      });
      if (translatedFields.length) savedField['label-translations'] = translatedFields;

      if (Array.isArray(field.values)) {
        savedField.values = field.values.map(function(option, optionIndex) {
          var localizedOptions = languages.slice(1).map(function(language) {
            var localizedField = findTranslatedField(languageSchemas[language] || [], field, index);
            var localizedOption = localizedField && Array.isArray(localizedField.values)
              ? findSchemaOption(localizedField.values, option, optionIndex)
              : null;
            return {
              lang: language,
              value: localizedOption && typeof localizedOption.label === 'string'
                ? localizedOption.label
                : String(option.label || ''),
            };
          });
          var savedOption = Object.assign({}, option);
          delete savedOption['label-translations'];
          if (localizedOptions.length) savedOption['label-translations'] = localizedOptions;
          return savedOption;
        });
      }
      return savedField;
    });
  }

  function restoreLanguageSchema(schema) {
    languageSchemas = readLanguageSchemas(schema);
    Object.keys(languageSchemas).forEach(ensureLanguageOption);
    Array.from(languagesField.options).forEach(function(option) {
      option.selected = Object.prototype.hasOwnProperty.call(languageSchemas, option.value);
    });
    activeEditorLanguage = 'en';
    updateEditorLanguageOptions(selectedLanguages());
    renderLanguageChips();
    formBuilderInstance.actions.setData(JSON.stringify(languageSchemas.en || []));
  }

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
    var selectedType = String(formTypeField.value || 'mentor');
    var forms = currentFormsForType().filter(function(form) {
      return String(form.partner_id) === selectedPartner;
    });

    var previousValue = String(updateFormIdField.value || '');
    updateFormIdField.innerHTML = '';
    forms.forEach(function(form) {
      var opt = document.createElement('option');
      opt.value = String(form.id);
      opt.textContent = 'ID ' + form.id + ' · ' + (form.created_at || '');
      opt.dataset.formType = selectedType;
      updateFormIdField.appendChild(opt);
    });

    if (!forms.length) {
      var emptyOpt = document.createElement('option');
      emptyOpt.value = '';
      emptyOpt.textContent = 'No forms for this partner/type';
      updateFormIdField.appendChild(emptyOpt);
      updateFormIdField.value = '';
      return;
    }

    if (previousValue && Array.from(updateFormIdField.options).some(function(option) { return option.value === previousValue; })) {
      updateFormIdField.value = previousValue;
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
      var selectedOption = updateFormIdField.selectedOptions && updateFormIdField.selectedOptions[0];
      var selectedFormType = String((selectedOption && selectedOption.dataset.formType) || formTypeField.value || 'mentor');
      restoreLanguageSchema(formDef.json || []);
      formTypeField.value = selectedFormType;
      updateTypeField.value = selectedFormType;
      setEditMode(true);
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
  languageControls.hidden = false;
  updateEditorLanguageOptions(selectedLanguages());
  renderLanguageChips();

  languageSearchField.addEventListener('focus', function() {
    languageSearchOpen = true;
    renderLanguageSuggestions();
  });
  languageSearchField.addEventListener('input', function() {
    languageSearchOpen = true;
    renderLanguageSuggestions();
  });
  languageSearchField.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
      languageSearchOpen = false;
      languageSuggestions.hidden = true;
      languageSearchField.setAttribute('aria-expanded', 'false');
      return;
    }
    if (event.key === 'Enter' && !languageSuggestions.hidden) {
      var firstSuggestion = languageSuggestions.querySelector('[role="option"]');
      if (firstSuggestion) {
        event.preventDefault();
        firstSuggestion.click();
      }
    }
  });
  document.addEventListener('click', function(event) {
    if (!document.getElementById('mentorship-form-language-picker').contains(event.target) &&
        !languageSuggestions.contains(event.target)) {
      languageSearchOpen = false;
      languageSuggestions.hidden = true;
      languageSearchField.setAttribute('aria-expanded', 'false');
    }
  });

  languagesField.addEventListener('change', function() {
    if (!captureEditorSchema()) return;
    var languages = selectedLanguages();
    renderLanguageChips();
    languages.forEach(function(language) {
      if (!languageSchemas[language]) languageSchemas[language] = cloneSchema(languageSchemas.en || []);
    });
    Object.keys(languageSchemas).forEach(function(language) {
      if (languages.indexOf(language) === -1) delete languageSchemas[language];
    });
    updateEditorLanguageOptions(languages);
    setBuilderLanguage(activeEditorLanguage);
  });

  editorLanguageField.addEventListener('change', function() {
    if (!captureEditorSchema()) return;
    setBuilderLanguage(String(editorLanguageField.value || 'en'));
  });

  formElement.addEventListener('submit', function(event) {
    if (isEditingExistingForm) {
      statusEl.textContent = 'Finish or cancel current edit before creating a new form.';
      event.preventDefault();
      return;
    }
    try {
      var dataJson = JSON.stringify(buildSchemaWithTranslations());
      if (!dataJson || dataJson === '[]') {
        statusEl.textContent = 'Add at least one field to the form before saving.';
        event.preventDefault();
        return;
      }
      outputField.value = dataJson;
    } catch (error) {
      statusEl.textContent = error && error.message ? error.message : 'Unable to export JSON from visual builder.';
      event.preventDefault();
    }
  });

  updateFormElement.addEventListener('submit', function(event) {
    if (!isEditingExistingForm) {
      statusEl.textContent = 'Load an existing form before saving updates.';
      event.preventDefault();
      return;
    }
    try {
      if (!updateFormIdField.value) {
        statusEl.textContent = 'Select a form to update.';
        event.preventDefault();
        return;
      }
      var dataJson = JSON.stringify(buildSchemaWithTranslations());
      if (!dataJson || dataJson === '[]') {
        statusEl.textContent = 'Add at least one field to the form before saving updates.';
        event.preventDefault();
        return;
      }
      updatePartnerField.value = String(globalPartnerField.value || '');
      updateTypeField.value = String(formTypeField.value || 'mentor');
      updateJsonField.value = dataJson;
    } catch (error) {
      statusEl.textContent = error && error.message ? error.message : 'Unable to export JSON from visual builder.';
      event.preventDefault();
    }
  });

  formTypeField.addEventListener('change', function() {
    updateTypeField.value = String(formTypeField.value || 'mentor');
    setEditMode(false);
    filterPublicKeysByPartner();
  });
  globalPartnerField.addEventListener('change', function() {
    setEditMode(false);
    filterPublicKeysByPartner();
  });
  loadBtn.addEventListener('click', loadSelectedFormIntoBuilder);
  if (cancelEditBtn) {
    cancelEditBtn.addEventListener('click', function() {
      setEditMode(false);
      statusEl.textContent = 'Edit mode cancelled. You can create a new form now.';
    });
  }
  setEditMode(false);
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
  var requiredKeyEl = document.getElementById('mentorship-csv-required-key');
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
  var responseLanguageKey = '__form_language';

  function currentForms() {
    return typeSelect.value === 'mentor' ? mentorForms : menteeForms;
  }

  function currentResponses() {
    return typeSelect.value === 'mentor' ? mentorResponses : menteeResponses;
  }

  function formatKeyLabel(meta) {
    if (!meta || (!meta.keyId && !meta.fingerprint)) {
      return 'Unknown key';
    }
    var parts = [];
    if (meta.keyId) parts.push('Key #' + meta.keyId);
    if (meta.fingerprint) parts.push('fp ' + meta.fingerprint);
    if (meta.createdAt) parts.push(String(meta.createdAt).slice(0, 10));
    return parts.join(' | ');
  }

  function getFormKeyMeta(formDefinition) {
    return {
      keyId: formDefinition && formDefinition.public_key_id != null ? String(formDefinition.public_key_id) : '',
      fingerprint: formDefinition && formDefinition.public_key_fingerprint ? String(formDefinition.public_key_fingerprint) : '',
      createdAt: formDefinition && formDefinition.public_key_created_at ? String(formDefinition.public_key_created_at) : '',
    };
  }

  function getRowKeyMeta(row, formDefinition) {
    return {
      keyId: row && row.encrypted_with_public_key_id != null
        ? String(row.encrypted_with_public_key_id)
        : row && row.public_key_id != null
          ? String(row.public_key_id)
          : (formDefinition && formDefinition.public_key_id != null ? String(formDefinition.public_key_id) : ''),
      fingerprint: row && row.encrypted_with_public_key_fingerprint
        ? String(row.encrypted_with_public_key_fingerprint)
        : row && row.public_key_fingerprint
          ? String(row.public_key_fingerprint)
          : (formDefinition && formDefinition.public_key_fingerprint ? String(formDefinition.public_key_fingerprint) : ''),
      createdAt: row && row.encrypted_with_public_key_created_at
        ? String(row.encrypted_with_public_key_created_at)
        : row && row.public_key_created_at
          ? String(row.public_key_created_at)
          : (formDefinition && formDefinition.public_key_created_at ? String(formDefinition.public_key_created_at) : ''),
    };
  }

  function maybeResetPrivateKey(reason) {
    if (!privateKeyInput.value || !privateKeyInput.value.trim()) return;
    privateKeyInput.value = '';
    if (statusEl && reason) {
      statusEl.textContent = reason;
    }
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

  function repopulateForms(options) {
    var opts = options || {};
    var pid = String(partnerSelect.value || '');
    var forms = currentForms().filter(function(f) { return String(f.partner_id) === pid; });
    formSelect.innerHTML = '';
    forms.forEach(function(f) {
      var opt = document.createElement('option');
      opt.value = String(f.id);
      opt.textContent = 'ID ' + f.id + ' · ' + (f.created_at || '') + ' · ' + formatKeyLabel(getFormKeyMeta(f));
      formSelect.appendChild(opt);
    });
    if (!forms.length) {
      var emptyOpt = document.createElement('option');
      emptyOpt.value = '';
      emptyOpt.textContent = 'No forms for this partner/type';
      formSelect.appendChild(emptyOpt);
    }
    if (opts.resetPrivateKey) {
      maybeResetPrivateKey(opts.resetReason || 'Private key cleared because context changed. Paste the key for the selected form.');
    }
    refreshResponseSummary();
  }

  function refreshResponseSummary() {
    if (!summaryEl && !respondentsEl && !requiredKeyEl) return;
    var selectedFormId = String(formSelect.value || '');
    if (!selectedFormId) {
      if (summaryEl) summaryEl.textContent = 'No form selected.';
      if (respondentsEl) respondentsEl.textContent = '';
      if (requiredKeyEl) requiredKeyEl.textContent = 'Required private key: select a form to see the key details.';
      return;
    }
    var selectedForm = getSelectedFormDefinition(selectedFormId);
    var selectedFormMeta = getFormKeyMeta(selectedForm);
    var rows = currentResponses().filter(function(r) { return String(r.form_id) === selectedFormId; });
    if (summaryEl) {
      summaryEl.textContent = 'Responses available: ' + rows.length;
    }
    if (requiredKeyEl) {
      requiredKeyEl.textContent = 'Required private key: ' + formatKeyLabel(selectedFormMeta) + '.';
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
      var selectedFormMeta = getFormKeyMeta(selectedForm);
      var baselineMeta = rows.length ? getRowKeyMeta(rows[0], selectedForm) : selectedFormMeta;

      var hasMixedKeys = rows.some(function(row) {
        var rowMeta = getRowKeyMeta(row, selectedForm);
        if (baselineMeta.keyId && rowMeta.keyId && baselineMeta.keyId !== rowMeta.keyId) return true;
        if (baselineMeta.fingerprint && rowMeta.fingerprint && baselineMeta.fingerprint !== rowMeta.fingerprint) return true;
        return false;
      });

      if (hasMixedKeys) {
        statusEl.textContent = 'Export blocked: responses for this form were encrypted with multiple keys. Split by key lineage before downloading CSV.';
        return;
      }

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
          if (key === responseLanguageKey) return;
          if (!dynamicKeySet[key]) {
            dynamicKeySet[key] = true;
            dynamicKeys.push(key);
          }
        });
      }

      var header = ['username', 'created_at', 'encrypted_with_public_key_id', 'encrypted_with_public_key_fingerprint', 'response_language'];
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
        var rowKeyMeta = getRowKeyMeta(currentRow, selectedForm);
        var lineParts = [
          escapeCSV(currentRow.username),
          escapeCSV(currentRow.created_at),
          escapeCSV(rowKeyMeta.keyId),
          escapeCSV(rowKeyMeta.fingerprint),
          escapeCSV(currentObject[responseLanguageKey]),
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
      statusEl.textContent = rows.length + ' response(s) decrypted and exported with key ' + formatKeyLabel(baselineMeta) + '.';
    } catch (e) {
      statusEl.textContent = 'Unable to decrypt responses with this private key. Confirm the key shown in "Required private key".';
    }
  }

  partnerSelect.addEventListener('change', function() {
    repopulateForms({
      resetPrivateKey: true,
      resetReason: 'Private key cleared because partner changed. Paste the key for the selected partner/form.',
    });
  });
  typeSelect.addEventListener('change', function() {
    repopulateForms({
      resetPrivateKey: true,
      resetReason: 'Private key cleared because response type changed. Paste the key for the selected form.',
    });
  });
  formSelect.addEventListener('change', function() {
    maybeResetPrivateKey('Private key cleared because form changed. Paste the key required by this form.');
    refreshResponseSummary();
  });
  downloadBtn.addEventListener('click', function() { handleDownload(); });
  repopulateForms();
})();