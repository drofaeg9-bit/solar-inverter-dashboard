    const colours = [
      'var(--flow-grid-colour)', 'var(--flow-inverter-colour)',
      'var(--flow-battery-colour)', 'var(--flow-solar-colour)',
      'var(--flow-home-colour)', 'var(--flow-alert-colour)',
      'var(--flow-generator-colour)'
    ];
    let lastData = null;
    let chartDemoRunning = false;
    let chartDemoCancelRequested = false;
    let demoRegisterRows = null;
    let demoFlowCase = '';
    let demoGeneratorPower = 0;
    let demoPvVoltage = 0;
    let demoPvPower = 0;
    let currentView = 'dashboard';
    let lcdPageIndex = 0;
    const lcdInformationPageCount = 26;
    let lcdEnterNotice = false;
    let refreshInFlight = false;
    let refreshTimer = null;
    let refreshController = null;
    let pageIsActive = true;
    let lastLoggedSiteVisits = null;
    const requestIntervals = [2000, 5000, 10000];
    const hiddenRefreshInterval = 30000;
    const flowAnimationStates = new Map();
    let chartDefinitions = new Map();
    function savedSelections(name) {
      try {
        return new Set(JSON.parse(window.localStorage.getItem(name) || '[]'));
      } catch {
        return new Set();
      }
    }
    function saveSelections(name, selections) {
      try {
        window.localStorage.setItem(name, JSON.stringify([...selections]));
      } catch {
        // The dashboard still works when browser storage is unavailable.
      }
    }
    function savedMap(name) {
      try {
        const value = JSON.parse(window.localStorage.getItem(name) || '{}');
        return new Map(Object.entries(value && typeof value === 'object' ? value : {}));
      } catch {
        return new Map();
      }
    }
    function saveMap(name, values) {
      try {
        window.localStorage.setItem(name, JSON.stringify(Object.fromEntries(values)));
      } catch {
        // Gauge appearance remains stable for the current page when storage is unavailable.
      }
    }
    const chartSelections = savedSelections('inverter-chart-values-v2');
    const dashboardSelections = savedSelections('inverter-dashboard-gauges-v2');
    const chartHistory = new Map();
    const dashboardGaugeRanges = savedMap('inverter-dashboard-gauge-ranges-v2');
    const dashboardGaugeColours = savedMap('inverter-dashboard-gauge-colours-v2');
    const chartWindowSeconds = 120;
    const chartWindowMilliseconds = chartWindowSeconds * 1000;

    function numericValue(value) {
      const parsed = Number.parseFloat(value);
      return Number.isFinite(parsed) ? parsed : null;
    }





































    function renderRegisters(registers) {
      const query = document.querySelector('#search').value.trim().toLowerCase();
      const shown = registers.filter(item =>
        `${item.register} ${localizeDataText(item.group)} ${localizeDataText(item.name)} ${registerVersionDisplay(item, registers)} ${registerInterpretation(item)} ${item.unit}`.toLowerCase().includes(query)
      );
      const available = registers.filter(item => item.available).length;
      document.querySelector('#register-count').textContent =
        t('registerCount', {
          available,
          waiting: registers.length - available,
          shown: shown.length
        });
      document.querySelector('#registers').innerHTML = shown.map(item => {
        const value = numericValue(item.display);
        const bmsFormula = item.register === 413 && item.available ? r413BmsFormula(value) : '';
        const displayValue = registerVersionDisplay(item, registers);
        const interpretation = registerInterpretation({...item, versionDisplay: displayValue});
        return `<tr class="${item.available ? '' : 'unavailable'}">
          <td>R${item.register}</td><td>${localizeDataText(item.group)}</td><td>${localizeDataText(item.name)}</td>
          <td>${localizeDataText(displayValue)} ${item.unit}${bmsFormula ? `<br><small>${bmsFormula}</small>` : ''}${interpretation ? `<small class="register-interpretation">${interpretation}</small>` : ''}</td><td>${item.raw ?? '—'}</td></tr>`;
      }).join('');
    }

    let pendingRegisterRows = null;
    let registerRenderPending = false;
    function scheduleRegisterRender(registers) {
      pendingRegisterRows = registers;
      if (registerRenderPending) return;
      registerRenderPending = true;
      const renderPendingRegisters = () => {
        registerRenderPending = false;
        if (pendingRegisterRows) renderRegisters(pendingRegisterRows);
      };
      if ('requestIdleCallback' in window) {
        window.requestIdleCallback(renderPendingRegisters, {timeout: 750});
      } else {
        window.setTimeout(renderPendingRegisters, 0);
      }
    }

    function formatFileSize(bytes) {
      const value = Number(bytes || 0);
      if (value < 1024) return `${value} B`;
      if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
      if (value < 1024 * 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
      return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GB`;
    }

    function renderRegisterLog(log = {}) {
      const status = document.querySelector('#register-log-status');
      const active = Boolean(log.active);
      status.classList.toggle('active', active && !log.error);
      status.classList.toggle('error-text', Boolean(log.error));
      if (log.error) {
        status.textContent = t('registerLogError', {error: localizeDataText(log.error)});
      } else if (active) {
        status.textContent = t('registerLogActive', {
          filename: log.filename,
          changes: log.changes || 0,
          size: formatFileSize(log.size_bytes)
        });
      } else if (log.available) {
        status.textContent = t('registerLogStopped', {
          filename: log.filename,
          changes: log.changes || 0,
          size: formatFileSize(log.size_bytes)
        });
      } else {
        status.textContent = t('registerLogIdle');
      }
      if (Number.isFinite(Number(log.free_bytes))) {
        status.textContent += ` · ${t('registerLogStorage', {
          free: formatFileSize(log.free_bytes),
          count: log.pruned_files || 0
        })}`;
      }
      if (active && log.physical_button_capture) {
        status.textContent += ` · ${t('registerLogPhysicalCapture', {
          seconds: Number(log.capture_interval_seconds || .5).toLocaleString(
            currentLanguage === 'uk' ? 'uk-UA' : currentLanguage === 'ru' ? 'ru-RU' : 'en-GB'
          )
        })}`;
      }
      document.querySelector('#register-log-start').disabled = active;
      document.querySelector('#register-log-stop').disabled = !active;
      document.querySelector('#register-log-note').disabled = !active;
      document.querySelector('#register-log-mark').disabled = !active;
      document.querySelector('#register-log-download').hidden = !log.available;
      // Poll rate and read mode are now in the modbus debug modal
    }

    async function updateRegisterLog(action, note = '') {
      const buttons = document.querySelectorAll('#register-log-start, #register-log-stop, #register-log-mark');
      buttons.forEach(button => button.disabled = true);
      try {
        const payload = {action, note, language: currentLanguage};
        if (action === 'start') {
          payload.translations = Object.fromEntries(
            Object.entries(DATA_TRANSLATIONS).map(([source, translations]) => [
              source,
              currentLanguage === 'uk' ? source : translations[currentLanguage] ?? source
            ])
          );
        }
        const response = await fetch('/api/register-log', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
        if (lastData) lastData.register_log = result;
        if (action === 'mark') document.querySelector('#register-log-note').value = '';
        renderRegisterLog(result);
      } catch (error) {
        const status = document.querySelector('#register-log-status');
        status.className = 'logger-status error-text';
        status.textContent = t('registerLogRequestError', {error: localizeDataText(error.message)});
        const active = Boolean(lastData?.register_log?.active);
        document.querySelector('#register-log-start').disabled = active;
        document.querySelector('#register-log-stop').disabled = !active;
        document.querySelector('#register-log-mark').disabled = !active;
      }
    }
    function renderCycleStatus(data) {
      const configuredSeconds = (requestIntervals[data.poll_rate_index] ?? 1000) / 1000;
      document.querySelector('#cycle').textContent = data.paused
        ? t('cyclePaused', {cycle: data.cycle_id})
        : t('cycleReads', {
            cycle: data.cycle_id,
            seconds: configuredSeconds.toString(),
            readSeconds: data.read_seconds.toFixed(2),
            reads: data.successful
          });
    }
    function render(data) {
      lastData = data;
      document.querySelector('#identifier').textContent = getDisplayIdentifier(data.identifier);
      const status = document.querySelector('#status');
      status.classList.toggle('online', chartDemoRunning || (data.online && !data.paused));
      status.classList.toggle('paused', !chartDemoRunning && data.paused);
      status.querySelector('.status-label').textContent =
        chartDemoRunning
          ? t('demoMode')
          : data.paused ? t('paused') : data.online ? t('online') : t('offline');
      const appToggle = document.querySelector('#app-toggle');
      appToggle.textContent = data.paused ? t('startMonitoring') : t('stopMonitoring');
      appToggle.classList.toggle('start', data.paused);
      document.querySelector('#updated').textContent =
        t('updated', {time: localizeDataText(data.updated_at)});
      renderCycleStatus(data);
      const totalVisitors = Number(data.site_visits || 0);
      const numberLocale = currentLanguage === 'uk' ? 'uk-UA' : currentLanguage === 'ru' ? 'ru-RU' : 'en-GB';
      document.querySelector('#site-visits').textContent =
        t('visitors', {
          count: totalVisitors.toLocaleString(numberLocale),
          date: data.site_visits_date
        });
      if (lastLoggedSiteVisits !== totalVisitors) {
        const visitDetails = {};
        visitDetails[t('totalVisitorsLabel')] = totalVisitors;
        visitDetails[t('dateLabel')] = data.site_visits_date;
        visitDetails[t('openedLabel')] = new Date().toISOString();
        visitDetails[t('referrerLabel')] = document.referrer || t('direct');
        visitDetails[t('browserLanguageLabel')] = navigator.language;
        visitDetails[t('browserLabel')] = navigator.userAgent;
        visitDetails[t('viewportLabel')] = `${window.innerWidth}x${window.innerHeight}`;
        console.log(t('visitConsole'), visitDetails);
        lastLoggedSiteVisits = totalVisitors;
      }
      // Poll rate and read mode are now in the modbus debug modal
      const error = document.querySelector('#error');
      const connectionError = chartDemoRunning ? '' : data.error;
      error.textContent = connectionError
        ? t('connectionError', {error: localizeDataText(data.error)})
        : '';
      error.classList.toggle('show', Boolean(connectionError));
      renderRegisterLog(data.register_log);
      renderSolarEnergy(data.solar_energy);
      const displayedRegisters = chartDemoRunning && demoRegisterRows ? demoRegisterRows : data.registers;
      scheduleRegisterRender(displayedRegisters);
      renderEnergyFlow(data, displayedRegisters);
      renderLcd(data, displayedRegisters);
      updateChartDefinitions(data);
    }

    async function refresh() {
      if (refreshInFlight) return;
      refreshInFlight = true;
      refreshController = new AbortController();
      try {
        const response = await fetch('/api/state', {
          cache: 'no-store',
          signal: refreshController.signal
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        lastData = data;
        recordChartSamples(data);
        if (!chartDemoRunning) render(data);
      } catch (error) {
        if (error.name === 'AbortError') return;
        if (chartDemoRunning) return;
        const box = document.querySelector('#error');
        box.textContent = t('connectionLost', {error: error.message});
        box.classList.add('show');
      } finally {
        refreshInFlight = false;
        refreshController = null;
        if (!lastData?.paused) {
          scheduleRefresh();
        } else if (refreshTimer !== null) {
          window.clearTimeout(refreshTimer);
          refreshTimer = null;
        }
      }
    }

    function scheduleRefresh(delay = null) {
      if (refreshTimer !== null) window.clearTimeout(refreshTimer);
      refreshTimer = null;
      if (!pageIsActive) return;
      // Poll rate is now in the modbus debug modal, use default if not accessible
      const pollRateSelect = document.querySelector('#modbus-poll-rate');
      const selectedIndex = pollRateSelect ? Number(pollRateSelect.value) : 0;
      const selectedInterval = requestIntervals[selectedIndex] ?? 2000;
      const milliseconds = delay ?? (document.hidden
        ? Math.max(hiddenRefreshInterval, selectedInterval)
        : selectedInterval);
      refreshTimer = window.setTimeout(refresh, milliseconds);
    }

    async function updateSetting(setting, value) {
      await fetch('/api/settings', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({[setting]: value})
      });
      if (setting === 'paused' && value === true) {
        if (refreshTimer !== null) window.clearTimeout(refreshTimer);
        refreshTimer = null;
        refreshController?.abort();
      } else {
        scheduleRefresh(0);
      }
    }

    let registerMapFeedbackTimer = null;
    async function uploadRegisterMap(file) {
      const button = document.querySelector('#register-map-upload-button');
      const input = document.querySelector('#register-map-file');
      if (!file) return;
      if (file.size > 1024 * 1024) {
        button.textContent = t('registerMapFileTooLarge');
        input.value = '';
        registerMapFeedbackTimer = window.setTimeout(() => {
          button.textContent = t('uploadRegisterMap');
          registerMapFeedbackTimer = null;
        }, 5000);
        return;
      }
      if (registerMapFeedbackTimer !== null) window.clearTimeout(registerMapFeedbackTimer);
      button.disabled = true;
      button.textContent = t('registerMapUploading');
      try {
        const response = await fetch('/api/register-map', {
          method: 'POST',
          headers: {'Content-Type': 'text/csv; charset=utf-8'},
          body: file
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
        button.textContent = t('registerMapUploaded', {count: result.count});
        scheduleRefresh(0);
      } catch (error) {
        const message = t('registerMapUploadError', {error: error.message});
        button.textContent = message;
        button.title = message;
      } finally {
        button.disabled = false;
        input.value = '';
        registerMapFeedbackTimer = window.setTimeout(() => {
          button.textContent = t('uploadRegisterMap');
          button.title = t('registerMapHelp');
          registerMapFeedbackTimer = null;
        }, 5000);
      }
    }

    function wait(milliseconds) {
      return new Promise(resolve => setTimeout(resolve, milliseconds));
    }

    function showView(view) {
      currentView = ['dashboard', 'charts', 'lcd'].includes(view) ? view : 'dashboard';
      document.querySelector('#dashboard-view').hidden = currentView !== 'dashboard';
      document.querySelector('#charts-view').hidden = currentView !== 'charts';
      document.querySelector('#lcd-view').hidden = currentView !== 'lcd';
      document.querySelectorAll('.view-tab').forEach(button => {
        const active = button.dataset.view === currentView;
        button.classList.toggle('active', active);
        button.setAttribute('aria-selected', String(active));
        button.tabIndex = active ? 0 : -1;
      });
      if (currentView === 'charts') {
        scheduleChartsViewRender();
      }
      if (currentView === 'lcd' && lastData) {
        renderLcd(lastData, chartDemoRunning && demoRegisterRows ? demoRegisterRows : lastData.registers);
      }
      if (currentView === 'dashboard') renderDashboardValues();
      if (currentView === 'dashboard' && chartDemoRunning && lastData && demoRegisterRows) {
        requestAnimationFrame(() => renderEnergyFlow(lastData, demoRegisterRows));
      }
    }

    async function recordDemoLcdKey(key) {
      if (!chartDemoRunning || !lastData?.register_log?.active) return;
      const page = lcdPageIndex === 0 ? 'LCD' : `P${lcdPageIndex}`;
      try {
        const response = await fetch('/api/register-log', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            action: 'lcd_key',
            key,
            page,
            demo_case: demoFlowCase || 'demoMode'
          })
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
        lastData.register_log = result;
        renderRegisterLog(result);
      } catch (error) {
        const status = document.querySelector('#register-log-status');
        status.className = 'logger-status error-text';
        status.textContent = t('registerLogRequestError', {error: localizeDataText(error.message)});
      }
    }

    function handleLcdKey(key) {
      if (key === 'escape') {
        lcdPageIndex = 0;
        lcdEnterNotice = false;
      } else if (key === 'up') {
        lcdPageIndex = lcdPageIndex <= 1 ? lcdInformationPageCount : lcdPageIndex - 1;
        lcdEnterNotice = false;
      } else if (key === 'down') {
        lcdPageIndex = lcdPageIndex === 0 || lcdPageIndex >= lcdInformationPageCount
          ? 1
          : lcdPageIndex + 1;
        lcdEnterNotice = false;
      } else if (key === 'enter') {
        lcdEnterNotice = true;
      } else {
        return;
      }
      if (lastData) {
        renderLcd(lastData, chartDemoRunning && demoRegisterRows ? demoRegisterRows : lastData.registers);
      }
      void recordDemoLcdKey(key);
    }

    function refreshDisabledButtonHints(root = document) {
      const buttons = root.matches?.('button') ? [root] : root.querySelectorAll?.('button') || [];
      buttons.forEach(button => {
        if (button.disabled) {
          const reason = button.dataset.disabledReason || 'actionUnavailable';
          if (button.dataset.generatedDisabledHint === 'true' || !button.hasAttribute('title')) {
            button.title = t(reason);
            button.dataset.generatedDisabledHint = 'true';
          }
          button.setAttribute('aria-disabled', 'true');
        } else {
          if (button.dataset.generatedDisabledHint === 'true') {
            button.removeAttribute('title');
            delete button.dataset.generatedDisabledHint;
          }
          button.removeAttribute('aria-disabled');
        }
      });
    }

    function applyLanguage(language, save = true) {
      currentLanguage = ['uk', 'ru', 'en'].includes(language) ? language : 'uk';
      document.documentElement.lang = currentLanguage;
      document.querySelectorAll('[data-i18n]').forEach(element => {
        element.textContent = t(element.dataset.i18n);
      });
      document.querySelectorAll('[data-i18n-aria]').forEach(element => {
        element.setAttribute('aria-label', t(element.dataset.i18nAria));
      });
      document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        element.setAttribute('placeholder', t(element.dataset.i18nPlaceholder));
      });
      document.querySelectorAll('[data-i18n-title]').forEach(element => {
        element.setAttribute('title', t(element.dataset.i18nTitle));
      });
      document.querySelectorAll('.language-option').forEach(button => {
        const active = button.dataset.language === currentLanguage;
        button.classList.toggle('active', active);
        button.setAttribute('aria-pressed', String(active));
      });
      refreshDisabledButtonHints();
      document.querySelector('#theme-name').textContent =
        document.documentElement.dataset.theme === 'light' ? t('themeLight') : t('themeDark');
      showView(currentView);
      if (!chartDemoRunning) {
        document.querySelectorAll('.all-data-demo-button').forEach(button => {
          button.textContent = t('runDemo');
        });
      }
      if (save) {
        try {
          window.localStorage.setItem('solar-invertor-language', currentLanguage);
        } catch {
          // Language switching still works when browser storage is unavailable.
        }
      }
      lastLoggedSiteVisits = null;
      if (lastData) {
        document.querySelector('#gauges').innerHTML = '';
        render(lastData);
        renderChartValueList();
        renderGaugePickerList();
        renderChartCards();
        renderDashboardValues();
      } else {
        document.querySelector('#app-toggle').textContent = t('stopMonitoring');
        document.querySelector('#status .status-label').textContent = t('offline');
        document.querySelector('#cycle').textContent = t('cycleInitial');
        document.querySelector('#site-visits').textContent = t('visitorsInitial');
        document.querySelector('#updated').textContent = t('notUpdated');
        renderChartCards();
      }
      requestAnimationFrame(drawAllCharts);
    }

    function initialLanguage() {
      try {
        const savedLanguage = window.localStorage.getItem('solar-invertor-language');
        if (['uk', 'ru', 'en'].includes(savedLanguage)) return savedLanguage;
      } catch {
        // Use Ukrainian when browser storage is unavailable.
      }
      return 'uk';
    }

    function applyTheme(theme, save = true) {
      const selectedTheme = theme === 'light' ? 'light' : 'dark';
      document.documentElement.dataset.theme = selectedTheme;
      document.querySelector('#theme-toggle').checked = selectedTheme === 'light';
      document.querySelector('#theme-name').textContent =
        selectedTheme === 'light' ? t('themeLight') : t('themeDark');
      if (save) {
        try {
          window.localStorage.setItem('inverter-theme', selectedTheme);
        } catch {
          // Theme still changes when browser storage is unavailable.
        }
      }
      if (currentView === 'charts') {
        requestAnimationFrame(() => window.setTimeout(drawAllCharts, 0));
      }
    }

    function initialTheme() {
      try {
        const savedTheme = window.localStorage.getItem('inverter-theme');
        if (savedTheme === 'light' || savedTheme === 'dark') return savedTheme;
      } catch {
        // Fall through to the system preference.
      }
      return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
    }

    function getCustomDeviceName() {
      try {
        return window.localStorage.getItem('custom-device-name') || '';
      } catch {
        return '';
      }
    }

    function saveCustomDeviceName(name) {
      try {
        if (name && name.trim()) {
          window.localStorage.setItem('custom-device-name', name.trim());
        } else {
          window.localStorage.removeItem('custom-device-name');
        }
      } catch {
        // Settings still work when browser storage is unavailable.
      }
    }

    function getDisplayIdentifier(dataIdentifier) {
      const customName = getCustomDeviceName();
      if (customName && customName.trim()) return customName.trim();
      return dataIdentifier || t('unknownDevice');
    }

    // Make functions globally available for app-events.js
    window.getCustomDeviceName = getCustomDeviceName;
    window.saveCustomDeviceName = saveCustomDeviceName;
    window.getDisplayIdentifier = getDisplayIdentifier;

    async function loadLogs() {
      try {
        const response = await fetch('/api/logs');
        const data = await response.json();
        document.querySelector('#logs-content').textContent = data.logs || 'No logs available';
      } catch (error) {
        document.querySelector('#logs-content').textContent = 'Failed to load logs: ' + error;
      }
    }
    window.loadLogs = loadLogs;
    window.renderCycleStatus = renderCycleStatus;

    async function loadModbusDebug() {
      try {
        const response = await fetch('/api/state');
        const data = await response.json();
        const modbusRequests = document.querySelector('#modbus-requests');
        const modbusSuccessful = document.querySelector('#modbus-successful');
        const modbusFailed = document.querySelector('#modbus-failed');
        const modbusCycleSeconds = document.querySelector('#modbus-cycle-seconds');
        const modbusReadSeconds = document.querySelector('#modbus-read-seconds');
        const modbusCycleId = document.querySelector('#modbus-cycle-id');
        const modbusError = document.querySelector('#modbus-error');
        const modbusConnectionMode = document.querySelector('#modbus-connection-mode');

        if (modbusRequests) modbusRequests.textContent = data.requests || '—';
        if (modbusSuccessful) modbusSuccessful.textContent = data.successful || '—';
        if (modbusFailed) modbusFailed.textContent = data.failed || '—';
        if (modbusCycleSeconds) modbusCycleSeconds.textContent = data.cycle_seconds ? data.cycle_seconds.toFixed(2) : '—';
        if (modbusReadSeconds) modbusReadSeconds.textContent = data.read_seconds ? data.read_seconds.toFixed(2) : '—';
        if (modbusCycleId) modbusCycleId.textContent = data.cycle_id || '—';
        if (modbusError) modbusError.textContent = data.error || '—';
        try {
          const connectionMode = window.localStorage.getItem('connection-mode') || 'rtu';
          if (modbusConnectionMode) modbusConnectionMode.textContent = connectionMode === 'rtu' ? 'RTU (Serial)' : 'TCP (Network)';
        } catch {
          if (modbusConnectionMode) modbusConnectionMode.textContent = '—';
        }
      } catch (error) {
        const modbusError = document.querySelector('#modbus-error');
        if (modbusError) modbusError.textContent = 'Failed to load modbus debug: ' + error;
      }
    }
    window.loadModbusDebug = loadModbusDebug;
