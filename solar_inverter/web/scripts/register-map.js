    function mapMessage(key, replacements = {}) {
      const message = document.querySelector('#register-map-message');
      if (message) message.textContent = t(key, replacements);
    }

    function renderRegisterMap(data) {
      const rows = document.querySelector('#register-map-rows');
      const count = document.querySelector('#fast-poll-count');
      if (!rows || !count) return;
      const selected = new Set(fastPollSelection());
      const scanButton = document.querySelector('#register-map-scan');
      if (scanButton) {
        const scanning = data.read_mode === 'scan';
        scanButton.dataset.scanning = String(scanning);
        scanButton.textContent = t(scanning ? 'stopRegisterMapScan' : 'scanRegisterMap');
      }
      count.textContent = String(selected.size);
      const query = document.querySelector('#register-map-search')?.value.trim().toLowerCase() || '';
      const registers = [...(data.registers || [])]
        // Show every address proven by the full inverter scan, even before the
        // current process has obtained a fresh value for it.
        .filter(register => register.supported || selected.has(Number(register.register)))
        .sort((left, right) => Number(right.register) - Number(left.register))
        .sort((left, right) => Number(selected.has(Number(right.register))) - Number(selected.has(Number(left.register))))
        .filter(register => `${register.register} ${localizeApiField(register, 'group')} ${localizeApiField(register, 'name')} ${register.unit}`.toLowerCase().includes(query));
      rows.replaceChildren(...registers.map(register => {
        const number = Number(register.register);
        const row = document.createElement('tr');
        row.className = selected.has(number) ? 'fast-poll' : '';
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = selected.has(number);
        checkbox.dataset.mapSelect = String(number);
        const edit = document.createElement('button');
        edit.type = 'button'; edit.dataset.mapEdit = String(number); edit.textContent = t('edit');
        const cell = value => { const td = document.createElement('td'); td.textContent = value; return td; };
        const selectCell = document.createElement('td'); selectCell.append(checkbox);
        const actionCell = document.createElement('td'); actionCell.append(edit);
        row.append(selectCell, cell(`R${number}`), cell(localizeApiField(register, 'group')), cell(localizeApiField(register, 'name')), cell(register.unit || '—'), actionCell);
        return row;
      }));
    }

    function updateRegisterMapSelection(register, selected) {
      const selection = fastPollSelection();
      const next = selected ? [...selection, register] : selection.filter(item => item !== register);
      setFastPollSelection(next);
      mapMessage(selected ? 'fastPollAdded' : 'fastPollRemoved', {register: `R${register}`});
      if (lastData) renderRegisterMap(lastData);
    }

    document.querySelector('#register-map-search').addEventListener('input', () => {
      if (lastData) renderRegisterMap(lastData);
    });
    document.querySelector('#register-map-rows').addEventListener('change', event => {
      const input = event.target.closest('[data-map-select]');
      if (input) updateRegisterMapSelection(Number(input.dataset.mapSelect), input.checked);
    });
    document.querySelector('#register-map-rows').addEventListener('click', event => {
      const button = event.target.closest('[data-map-edit]');
      if (!button || !lastData) return;
      const register = lastData.registers.find(item => Number(item.register) === Number(button.dataset.mapEdit));
      if (!register) return;
      const group = window.prompt(t('registerMapEditGroup'), localizeApiField(register, 'group'));
      if (group === null) return;
      const name = window.prompt(t('registerMapEditName'), localizeApiField(register, 'name'));
      if (name === null) return;
      const unit = window.prompt(t('registerMapEditUnit'), register.unit || '');
      if (unit === null) return;
      void saveManualRegisterValue(Number(register.register), {group, name, unit}).catch(error => mapMessage('registerMapSaveError', {error: error.message}));
    });
    document.querySelector('#register-map-add-button').addEventListener('click', () => {
      const input = document.querySelector('#register-map-add');
      const match = String(input.value || '').trim().match(/^R?(\d+)$/i);
      const register = match ? Number(match[1]) : NaN;
      if (!lastData?.registers.some(item => Number(item.register) === register)) {
        mapMessage('registerMapUnknown');
        return;
      }
      input.value = '';
      updateRegisterMapSelection(register, true);
    });
    document.querySelector('#register-map-add').addEventListener('keydown', event => {
      if (event.key === 'Enter') { event.preventDefault(); document.querySelector('#register-map-add-button').click(); }
    });
    document.querySelector('#register-map-reset').addEventListener('click', () => {
      setFastPollSelection(defaultFastPollSelection());
      mapMessage('fastPollReset');
      if (lastData) renderRegisterMap(lastData);
    });
    document.querySelector('#register-map-scan').addEventListener('click', async event => {
      const button = event.currentTarget;
      const stopping = button.dataset.scanning === 'true' || lastData?.read_mode === 'scan';
      button.disabled = true;
      try {
        await updateSetting('read_mode', stopping ? 'fast' : 'scan');
        button.dataset.scanning = String(!stopping);
        button.textContent = t(stopping ? 'scanRegisterMap' : 'stopRegisterMapScan');
        mapMessage(stopping ? 'registerMapScanStopped' : 'registerMapScanning');
      } catch (error) {
        mapMessage('registerMapScanError', {error: error.message});
      } finally {
        button.disabled = false;
      }
    });
