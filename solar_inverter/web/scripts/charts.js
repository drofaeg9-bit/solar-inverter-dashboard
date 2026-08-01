    const VALUE_LIST_RENDER_LIMIT = 80;
    const CHARTS_PER_PAGE = 12;
    let chartPage = 0;
    let chartsViewRenderPending = false;
    const chartCanvasLayouts = new WeakMap();
    const visibleChartCanvases = new Set();
    const chartResizeObserver = typeof ResizeObserver === 'function'
      ? new ResizeObserver(entries => {
          entries.forEach(entry => {
            chartCanvasLayouts.set(entry.target, {
              width: entry.contentRect.width,
              height: entry.contentRect.height
            });
          });
          scheduleVisibleChartDraw();
        })
      : null;
    const chartVisibilityObserver = typeof IntersectionObserver === 'function'
      ? new IntersectionObserver(entries => {
          entries.forEach(entry => {
            if (entry.isIntersecting) visibleChartCanvases.add(entry.target);
            else visibleChartCanvases.delete(entry.target);
          });
          scheduleVisibleChartDraw();
        }, {rootMargin: '1000px 0px'})
      : null;

    function observeRenderedCharts() {
      chartResizeObserver?.disconnect();
      chartVisibilityObserver?.disconnect();
      visibleChartCanvases.clear();
      document.querySelectorAll('canvas[data-chart-key]').forEach(canvas => {
        if (chartResizeObserver) chartResizeObserver.observe(canvas);
        else chartCanvasLayouts.set(canvas, {width: 300, height: 220});
        if (chartVisibilityObserver) chartVisibilityObserver.observe(canvas);
        else visibleChartCanvases.add(canvas);
      });
    }

    function collectChartDefinitions(data) {
      const definitions = new Map();
      const registerCategories = new Map(
        data.registers.map(register => [register.register, String(register.group || '')])
      );
      data.meters.forEach(meter => {
        const value = meter.available !== false && Number.isFinite(meter.value) ? meter.value : null;
        const bmsFormula = meter.register === 413 ? r413BmsFormula(value) : '';
        definitions.set(`meter-${meter.register}`, {
          key: `meter-${meter.register}`,
          register: meter.register,
          label: localizeDataText(meter.label),
          detail: `${t('gaugeDetail', {
            unit: meter.unit || t('unitValue'),
            register: meter.register
          })}${bmsFormula ? ` · ${bmsFormula}` : ''}`,
          unit: meter.unit,
          value,
          minimum: meter.minimum,
          maximum: meter.maximum,
          available: meter.available ?? !String(meter.source || '').toLowerCase().includes('mbpoll'),
          category: registerCategories.get(meter.register) || '',
          source: bmsFormula ? `R413 · ${bmsFormula}` : localizeDataText(meter.source)
        });
      });
      data.registers.forEach(register => {
        const value = numericValue(register.display);
        if (value === null) return;
        const bmsFormula = register.register === 413 && register.available ? r413BmsFormula(value) : '';
        const interpretation = registerInterpretation(register);
        const isPercentage = register.unit === '%';
        const chartValue = isPercentage ? Math.max(0, Math.min(100, value)) : value;
        definitions.set(`register-${register.register}`, {
          key: `register-${register.register}`,
          register: register.register,
          label: localizeDataText(register.name),
          detail: `R${register.register} · ${localizeDataText(register.group)}${bmsFormula ? ` · ${bmsFormula}` : ''}`,
          unit: register.unit,
          scale: Number(register.scale) || 1,
          signed: Boolean(register.signed),
          value: chartValue,
          minimum: isPercentage ? 0 : null,
          maximum: isPercentage ? 100 : null,
          available: register.available,
          category: String(register.group || ''),
          interpretation,
          source: register.available
            ? `R${register.register}${bmsFormula ? ` · ${bmsFormula}` : ''}`
            : t('noData')
        });
      });
      return definitions;
    }
    function updateGaugeSelectionActions() {
      const allSelected = chartDefinitions.size > 0 && [...chartDefinitions.keys()].every(key =>
        dashboardSelections.has(key) && chartSelections.has(key)
      );
      const noSelection = dashboardSelections.size === 0 && chartSelections.size === 0;
      const selectAllDisabled = chartDefinitions.size === 0 || allSelected;
      const setDisabled = (selector, disabled) => {
        const button = document.querySelector(selector);
        if (button.disabled !== disabled) button.disabled = disabled;
      };
      setDisabled('#select-all-gauges', selectAllDisabled);
      setDisabled('#chart-select-all', selectAllDisabled);
      setDisabled('#clear-all-gauges', noSelection);
      setDisabled('#chart-clear-all', noSelection);
    }
    function renderChartValueList() {
      if (document.querySelector('#charts-view').hidden) return;
      const host = document.querySelector('#chart-value-list');
      const query = document.querySelector('#chart-search').value.trim().toLowerCase();
      const matchingItems = [...chartDefinitions.values()].filter(item =>
        `${item.label} ${item.detail} ${item.interpretation || ''} ${item.unit}`.toLowerCase().includes(query)
      );
      const items = matchingItems.slice(0, VALUE_LIST_RENDER_LIMIT);
      const hiddenCount = matchingItems.length - items.length;
      const signature = `${currentLanguage}|${query}|${items.map(item =>
        `${item.key}:${item.label}:${item.detail}:${item.interpretation || ''}:${item.unit}:${chartSelections.has(item.key)}:${dashboardSelections.has(item.key)}`).join('|')}`;
      if (host.dataset.signature === signature) {
        updateGaugeSelectionActions();
        return;
      }
      host.dataset.signature = signature;
      host.innerHTML = items.map(item => `<div class="value-option">
        <div class="value-name">${item.label}<small>${item.detail}${item.interpretation ? `<br>${item.interpretation}` : ''}</small></div>
        <div class="value-targets">
          <label><input type="checkbox" data-value-key="${item.key}" ${chartSelections.has(item.key) && dashboardSelections.has(item.key) ? 'checked' : ''}> ${t('dashboardChart')}</label>
        </div>
      </div>`).join('') + (hiddenCount > 0
        ? `<div class="value-list-limit">${t('moreValuesAvailable', {count: hiddenCount})}</div>`
        : '');
      updateGaugeSelectionActions();
    }
    function renderGaugePickerList() {
      if (!document.querySelector('#gauge-picker').open) return;
      const host = document.querySelector('#gauge-picker-list');
      const query = document.querySelector('#gauge-picker-search').value.trim().toLowerCase();
      const matchingItems = [...chartDefinitions.values()].filter(item =>
        `${item.label} ${item.detail} ${item.interpretation || ''} ${item.unit}`.toLowerCase().includes(query)
      );
      const items = matchingItems.slice(0, VALUE_LIST_RENDER_LIMIT);
      const hiddenCount = matchingItems.length - items.length;
      const signature = `${currentLanguage}|${query}|${items.map(item =>
        `${item.key}:${item.label}:${item.detail}:${item.interpretation || ''}:${item.unit}:${dashboardSelections.has(item.key)}`).join('|')}`;
      if (host.dataset.signature === signature) {
        updateGaugeSelectionActions();
        return;
      }
      host.dataset.signature = signature;
      host.innerHTML = items.map(item => `<label class="gauge-picker-option">
        <input type="checkbox" data-picker-value-key="${item.key}" ${dashboardSelections.has(item.key) ? 'checked' : ''}>
        <span class="gauge-picker-name">${item.label}<small>${item.detail}${item.unit ? ` · ${item.unit}` : ''}${item.interpretation ? `<br>${item.interpretation}` : ''}</small></span>
      </label>`).join('') + (hiddenCount > 0
        ? `<div class="value-list-limit">${t('moreValuesAvailable', {count: hiddenCount})}</div>`
        : '');
      updateGaugeSelectionActions();
    }
    let gaugeSelectionRenderPending = false;
    function renderGaugeSelectionChanges() {
      if (gaugeSelectionRenderPending) return;
      gaugeSelectionRenderPending = true;
      updateGaugeSelectionActions();
      requestAnimationFrame(() => window.setTimeout(() => {
        gaugeSelectionRenderPending = false;
        saveSelections('inverter-dashboard-gauges-v2', dashboardSelections);
        saveSelections('inverter-chart-values-v2', chartSelections);
        if (!document.querySelector('#dashboard-view').hidden) renderDashboardValues();
        if (!document.querySelector('#charts-view').hidden) {
          renderChartValueList();
          renderChartCards();
        }
        if (document.querySelector('#gauge-picker').open) renderGaugePickerList();
      }, 0));
    }
    function selectAllGaugeSelections() {
      chartDefinitions.forEach((_item, key) => {
        if (!dashboardSelections.has(key) || !chartSelections.has(key)) chartHistory.set(key, []);
        dashboardSelections.add(key);
        chartSelections.add(key);
      });
      renderGaugeSelectionChanges();
    }
    function clearGaugeSelections() {
      dashboardSelections.clear();
      chartSelections.clear();
      chartHistory.clear();
      renderGaugeSelectionChanges();
    }
    function openGaugePicker() {
      const picker = document.querySelector('#gauge-picker');
      // Rebuild from the original server labels on every open so the dialog
      // can never retain labels produced for a previously selected language.
      if (lastData) chartDefinitions = collectChartDefinitions(lastData);
      if (typeof picker.showModal === 'function') picker.showModal();
      else picker.setAttribute('open', '');
      requestAnimationFrame(() => window.setTimeout(() => {
        renderGaugePickerList();
        document.querySelector('#gauge-picker-search').focus({preventScroll: true});
      }, 0));
    }
    function updateChartDefinitions(data) {
      const next = collectChartDefinitions(data);
      const definitionSignature = definitions => [...definitions.values()].map(item =>
        `${item.key}:${item.label}:${item.detail}:${item.interpretation || ''}:${item.unit}:${item.minimum}:${item.maximum}`
      ).join('|');
      const oldSignature = definitionSignature(chartDefinitions);
      const nextSignature = definitionSignature(next);
      chartDefinitions = next;
      if (oldSignature !== nextSignature) {
        renderChartValueList();
        renderGaugePickerList();
        renderChartCards();
      }
      if (!chartDemoRunning) renderDashboardValues();
    }
    function renderChartCards() {
      if (document.querySelector('#charts-view').hidden) return;
      const grid = document.querySelector('#chart-grid');
      const selected = [...chartSelections].filter(key => chartDefinitions.has(key));
      document.querySelector('#chart-demo-button').disabled = false;
      document.querySelector('#chart-selection-count').textContent =
        selected.length ? t('selectedSummary', {count: selected.length}) : t('noValuesSelected');

      if (!selected.length) {
        chartPage = 0;
        grid.dataset.signature = `${currentLanguage}|empty`;
        grid.innerHTML = `<div class="chart-empty">${t('selectValues')}</div>`;
        observeRenderedCharts();
        return;
      }

      const pageCount = Math.ceil(selected.length / CHARTS_PER_PAGE);
      chartPage = Math.max(0, Math.min(chartPage, pageCount - 1));
      const pageStart = chartPage * CHARTS_PER_PAGE;
      const pageItems = selected.slice(pageStart, pageStart + CHARTS_PER_PAGE);
      const signature = `${currentLanguage}|${chartPage}|${selected.length}|${pageItems.map(key => {
        const item = chartDefinitions.get(key);
        return `${key}:${item.label}:${item.detail}:${item.interpretation || ''}:${item.unit}`;
      }).join('|')}`;
      if (grid.dataset.signature === signature) {
        scheduleVisibleChartDraw();
        return;
      }
      grid.dataset.signature = signature;
      const pagination = pageCount > 1 ? `<nav class="chart-pagination" aria-label="${t('chartPagination')}">
        <button type="button" data-chart-page="previous" ${chartPage === 0 ? 'disabled' : ''}>${t('previousPage')}</button>
        <span>${t('chartPageSummary', {page: chartPage + 1, pages: pageCount})}</span>
        <button type="button" data-chart-page="next" ${chartPage === pageCount - 1 ? 'disabled' : ''}>${t('nextPage')}</button>
      </nav>` : '';
      grid.innerHTML = pagination + pageItems.map((key, pageIndex) => {
        const item = chartDefinitions.get(key);
        const index = pageStart + pageIndex;
        const colour = dashboardGaugeColour(item) || colours[index % colours.length];
        return `<article class="chart-card" style="--accent:${colour}">
          <div class="chart-card-head">
            <h3 title="${item.label}">${item.label}</h3>
            <div class="chart-latest" id="latest-${key}">—</div>
          </div>
          <div class="muted">${item.detail}</div>
          ${item.interpretation ? `<div class="chart-interpretation">${item.interpretation}</div>` : ''}
          <canvas id="chart-${key}" data-chart-key="${key}" data-chart-colour="${colour}" aria-label="${t('chartAria', {label: item.label})}"></canvas>
        </article>`;
      }).join('');
      observeRenderedCharts();
    }
    function changeChartPage(direction) {
      chartPage += direction === 'next' ? 1 : -1;
      renderChartCards();
    }
    function scheduleChartsViewRender() {
      if (chartsViewRenderPending) return;
      chartsViewRenderPending = true;
      requestAnimationFrame(() => window.setTimeout(() => {
        chartsViewRenderPending = false;
        if (document.querySelector('#charts-view').hidden) return;
        renderChartValueList();
        renderChartCards();
      }, 0));
    }
    function recordChartSamples(data) {
      updateChartDefinitions(data);
      if (chartDemoRunning) {
        if (!document.querySelector('#charts-view').hidden) drawAllCharts();
        return;
      }
      const now = Date.now();
      chartSelections.forEach(key => {
        const item = chartDefinitions.get(key);
        if (!item || item.available === false || !Number.isFinite(item.value)) return;
        const history = chartHistory.get(key) || [];
        history.push({time: now, value: item.value});
        trimChartHistory(history, now);
        chartHistory.set(key, history);
      });
      if (!document.querySelector('#charts-view').hidden) drawAllCharts();
    }
    function interpolate(start, end, ratio) {
      return start + (end - start) * Math.max(0, Math.min(1, ratio));
    }
    function realisticDemoScenario(elapsedSeconds) {
      const second = elapsedSeconds % chartWindowSeconds;
      const ripple = Math.sin(second * .37);
      let gridAvailable = true;
      let pvVoltage;
      let pvPower;
      let loadPower;
      let batteryCurrent;
      let batterySoc;
      let statusCode;
      let outputPriority;
      let chargingPriority;
      let caseKey;
      let generatorPower = 0;

      if (second < 20) {
        // PV supplies the home and charges the battery; surplus production is curtailed.
        gridAvailable = false;
        pvVoltage = 326 + ripple * 4;
        pvPower = 7200 + Math.sin(second * .21) * 260;
        loadPower = 2500 + Math.sin(second * .29) * 140;
        batteryCurrent = 42 + ripple * 1.5;
        batterySoc = 72 + second * .08;
        statusCode = 4;
        outputPriority = 2;
        chargingPriority = 1;
        caseKey = 'demoSolarChargeExport';
      } else if (second < 40) {
        // Grid supplies the home and charges the battery.
        pvVoltage = 0;
        pvPower = 0;
        loadPower = 2900 + ripple * 130;
        batteryCurrent = 18 + ripple;
        batterySoc = 73.6 + (second - 20) * .05;
        statusCode = 3;
        outputPriority = 0;
        chargingPriority = 0;
        caseKey = 'demoGridHome';
      } else if (second < 60) {
        // With PV and AC input unavailable, the battery supplies the home.
        gridAvailable = false;
        pvVoltage = 0;
        pvPower = 0;
        loadPower = 2300 + Math.sin(second * .31) * 160;
        batteryCurrent = -loadPower / 51.8;
        batterySoc = 74.4 - (second - 40) * .09;
        statusCode = 5;
        outputPriority = 0;
        chargingPriority = 2;
        caseKey = 'demoBatteryHome';
      } else if (second < 80) {
        // Solar supplies the home; surplus production is curtailed and the battery remains idle.
        gridAvailable = false;
        pvVoltage = 324 + ripple * 3;
        pvPower = 5600 + ripple * 220;
        loadPower = 2700 + Math.sin(second * .27) * 130;
        batteryCurrent = ripple * .08;
        batterySoc = 72.6;
        statusCode = 4;
        outputPriority = 2;
        chargingPriority = 1;
        caseKey = 'demoSolarExport';
      } else if (second < 100) {
        // The generator is a one-way source that supplies the inverter and home.
        gridAvailable = false;
        pvVoltage = 0;
        pvPower = 0;
        loadPower = 2800 + Math.sin(second * .25) * 120;
        batteryCurrent = 0;
        batterySoc = 72.5;
        statusCode = 6;
        outputPriority = 3;
        chargingPriority = 0;
        generatorPower = 3400 + ripple * 180;
        caseKey = 'demoGeneratorHome';
      } else {
        // With AC input unavailable, solar and battery jointly supply the home.
        gridAvailable = false;
        pvVoltage = 320 + ripple * 3;
        pvPower = 1500 + ripple * 120;
        loadPower = 2500 + Math.sin(second * .25) * 120;
        batteryCurrent = -(20 + ripple);
        batterySoc = 72.5 - (second - 100) * .07;
        statusCode = 4;
        outputPriority = 2;
        chargingPriority = 1;
        caseKey = 'demoMixedSources';
      }

      const gridVoltage = gridAvailable ? 230 + Math.sin(second * .19) * 1.4 : 0;
      const gridFrequency = gridAvailable ? 50 + Math.sin(second * .17) * .025 : 0;
      const batteryVoltage = 52.1 + (batterySoc - 75) * .09 + batteryCurrent * .018;
      const batteryTemperature = 29.5 + Math.abs(batteryCurrent) * .055 + Math.sin(second * .08) * .3;
      const batteryPower = batteryVoltage * batteryCurrent;
      const fanSpeed = Math.min(100, Math.max(0,
        second / chartWindowSeconds * 100
      ));
      const powerFactor = .86;
      const apparentLoadPower = loadPower / powerFactor;
      const gridPower = Math.max(0,
        loadPower + Math.max(0, batteryPower) - Math.max(0, pvPower) - Math.max(0, -batteryPower)
      );
      const inputMode = generatorPower > 20 ? 2 : 0;
      const generatorVoltage = generatorPower > 20 ? 230 : 0;
      const generatorCurrent = generatorVoltage > 0 ? generatorPower / generatorVoltage : 0;
      const pvChargingCurrent = pvPower > loadPower ? Math.max(0, batteryCurrent) : 0;
      const energyProgress = second / chartWindowSeconds;
      return {
        elapsedSeconds: second,
        statusCode,
        caseKey,
        generatorPower,
        pvVoltage,
        pvPower,
        values: new Map([
          // TTN-INV external Modbus map V1.31. Public R numbers are the
          // workbook's zero-based addresses plus one.
          [1, 0x5454], [2, 0x4e2d], [3, 0x494e], [4, 0x562d], [5, 0x4445],
          [6, 0x4d4f], [7, 0x2d30], [8, 0x3030], [9, 0x3031], [10, 0],
          [17, 1], [18, 31], [27, 1], [28, 31], [58, 0x0100],
          [65, 0x0131], [66, 1], [67, statusCode],
          [68, gridAvailable ? 0x0262 : 0x0220],
          [69, gridAvailable ? 0x0233 : 0x0330],
          [70, 0], [71, 0], [72, 0], [73, 0], [74, 0],
          [75, 65535], [76, 65535], [77, 1], [78, 8224], [79, 65535], [80, 1],
          [81, gridVoltage], [82, gridVoltage > 0 ? gridPower / gridVoltage : 0],
          [83, gridFrequency], [84, gridPower],
          [85, generatorVoltage], [86, generatorCurrent], [87, generatorVoltage > 0 ? 50 : 0],
          [88, generatorPower],
          [89, 230 + Math.sin(second * .13) * .8], [90, loadPower / 230], [91, 50],
          [92, loadPower], [93, apparentLoadPower], [94, loadPower / 120], [95, gridPower],
          [129, batteryVoltage], [130, batteryCurrent],
          [131, 0], [132, 0],
          [133, batterySoc], [134, batteryPower],
          [135, 0], [136, 0],
          [137, batteryVoltage], [138, batteryCurrent], [139, batterySoc],
          [140, batteryTemperature + .6], [141, 57.1],
          [142, 170], [143, 128], [144, 1], [145, 1], [146, 0], [147, 0],
          [148, 0], [149, 0], [150, 0],
          [151, pvVoltage], [152, pvVoltage > 0 ? pvPower / pvVoltage : 0],
          [153, pvPower], [154, 0], [155, 0], [156, 0],
          [157, 8.4 + energyProgress], [158, 1820.7 + energyProgress],
          [159, pvChargingCurrent], [160, 0], [161, pvPower],
          [162, 428.6 + energyProgress], [163, 3420.4 + energyProgress],
          [164, 4.2 + energyProgress], [165, 96.3 + energyProgress],
          [166, 812.5 + energyProgress], [167, 6432.8 + energyProgress],
          [168, 3.1 + energyProgress], [169, 71.8 + energyProgress],
          [170, 605.7 + energyProgress], [171, 4890.4 + energyProgress],
          [172, 7.8 + energyProgress], [173, 181.6 + energyProgress],
          [174, 1530.2 + energyProgress], [175, 12270.5 + energyProgress],
          [176, 6.9 + energyProgress], [177, 162.4 + energyProgress],
          [178, 1378.1 + energyProgress], [179, 11042.7 + energyProgress],
          [180, 1.2 + energyProgress], [181, 28.5 + energyProgress],
          [182, 241.8 + energyProgress], [183, 1920.6 + energyProgress],
          [184, 2.8 + energyProgress], [185, 65.7 + energyProgress],
          [186, 558.4 + energyProgress], [187, 4471.2 + energyProgress],
          [188, loadPower], [189, 0], [190, 0],
          [321, inputMode], [322, 0], [323, outputPriority], [324, chargingPriority], [325, statusCode],
          [337, 2], [339, batterySoc],
          [341, 47.5], [342, batteryVoltage],
          [343, Math.max(0, -batteryCurrent)], [344, Math.max(0, batteryCurrent)],
          [345, 61], [346, 48], [349, 48], [350, 2],
          [375, batteryCurrent > 1 ? 1 : batteryCurrent < -1 ? 0 : 3],
          [376, 57.1], [377, 54.4], [378, 80], [379, 80], [383, 58.4],
          [384, 2], [385, 2], [386, 30],
          [401, 1], [402, 1], [403, 8306],
          [404, batteryVoltage], [405, batteryCurrent],
          [406, batteryTemperature + .6], [407, batterySoc], [408, 100],
          [409, 128], [410, 170], [411, 57.1], [412, 80], [413, 120],
          [414, 20], [415, 10], [416, 48], [417, 57.6], [418, 0], [419, 0],
          [433, gridVoltage], [434, gridVoltage > 0 ? gridPower / gridVoltage : 0],
          [435, gridFrequency], [436, gridPower], [437, gridPower],
          [448, 0], [449, 840], [450, 0], [451, 9630],
          [452, 1], [453, 18420], [454, 3], [455, 42100],
          [529, outputPriority], [530, inputMode],
          [537, 230], [538, 50], [539, loadPower / 230], [541, loadPower],
          [542, apparentLoadPower], [545, loadPower / 120],
          [801, fanSpeed], [802, fanSpeed > 0 ? 1 : 0],
          [817, 34.2 + pvPower / 12000], [818, 46.2], [819, 38.1],
          [820, 36.8], [821, 27.4], [822, batteryTemperature],
          [823, 31.5 + pvPower / 10000],
          [16641, 2], [16642, 0],
          [16643, outputPriority], [16644, inputMode], [16645, chargingPriority],
          [16646, 60], [16647, 10], [16648, 0],
          [16649, 44], [16650, 42], [16651, 56.4], [16652, 54],
          [16653, 46], [16654, 52], [16655, 154], [16656, 264]
        ])
      };
    }
    function demoSolarEnergySummary(elapsedSeconds) {
      // The 120-second demo represents a compressed 12-hour operating window.
      const boundedSeconds = Math.max(0, Math.min(chartWindowSeconds, elapsedSeconds));
      const simulatedSecondsPerDemoSecond = 360;
      const integrationStep = .25;
      let generatedKwh = 0;
      for (let second = 0; second < boundedSeconds; second += integrationStep) {
        const step = Math.min(integrationStep, boundedSeconds - second);
        const pvPower = realisticDemoScenario(second + step / 2).pvPower;
        generatedKwh += Math.max(0, Number(pvPower) || 0)
          * step * simulatedSecondsPerDemoSecond / 3_600_000;
      }
      return {
        today_kwh: generatedKwh,
        week_kwh: 93.8 + generatedKwh,
        month_kwh: 428.6 + generatedKwh,
        year_kwh: 3420.4 + generatedKwh,
        error: ''
      };
    }
    function demoRawValue(register, value) {
      const scale = Number(register.scale) || 1;
      let raw = Math.round(value / scale);
      if (register.signed && raw < 0) raw += 65536;
      return Math.max(0, Math.min(65534, raw));
    }
    function demoDisplayValue(value, scale) {
      if (scale === .01) return value.toFixed(2);
      if (scale === .1) return value.toFixed(1);
      if (scale === 1) return Math.round(value).toString();
      return Number(value.toFixed(3)).toString();
    }
    function demoFallbackValue(register, elapsedSeconds) {
      const registerNumber = Number(register.register) || 0;
      const scale = Number(register.scale) || 1;
      const text = `${register.group || ''} ${register.name || ''} ${register.unit || ''}`.toLocaleLowerCase();
      const phase = Math.sin(elapsedSeconds * .12 + registerNumber * .37);
      const wave = (base, amplitude) => base + phase * amplitude;

      if (String(register.unit || '').trim() === '%') return Math.max(0, Math.min(100, wave(65, 12)));
      if (/(status|state|mode|priority|alarm|fault|warning|enable|switch|стан|режим|пріоритет|состояни|приоритет|авар|помил|ошиб)/u.test(text)) {
        return registerNumber % 4;
      }
      if (/(°c|температур|temperature)/u.test(text)) return wave(29, 2.5);
      if (/(hz|герц|частот|frequency)/u.test(text)) return wave(50, .04);
      if (/(kwh|квт·год|квтч)/u.test(text)) return 125 + registerNumber % 600 + elapsedSeconds / 120;
      if (/(wh|ват.*год)/u.test(text)) return 1200 + registerNumber % 5000 + elapsedSeconds * 2;
      if (/(kw|квт)/u.test(text)) return wave(2.4, .35);
      if (/(w|ват)/u.test(text)) return Math.max(0, wave(1800 + registerNumber % 900, 180));
      if (/(volt|вольт|\bv\b)/u.test(text)) {
        if (/(battery|bms|батар|акумулятор|аккумулятор)/u.test(text)) return wave(52.4, .35);
        if (/(pv|solar|соняч|солнеч)/u.test(text)) return wave(320, 4);
        return wave(230, 1.2);
      }
      if (/(amp|ампер|\ba\b)/u.test(text)) return wave(8, 1.4);
      if (/(rpm|об\/хв|об\/мин)/u.test(text)) return Math.max(0, wave(1400, 180));
      return scale * (10 + registerNumber % 90) + phase * scale;
    }
    function applyDemoEnergyFrame(scenario) {
      demoFlowCase = scenario.caseKey;
      demoGeneratorPower = scenario.generatorPower;
      demoPvVoltage = scenario.pvVoltage;
      demoPvPower = scenario.pvPower;
      demoRegisterRows = lastData ? lastData.registers.map(register => {
        const scenarioValue = scenario.values.get(register.register);
        const value = Number.isFinite(scenarioValue)
          ? scenarioValue
          : demoFallbackValue(register, scenario.elapsedSeconds);
        const display = demoDisplayValue(value, Number(register.scale) || 1);
        return {
          ...register,
          display,
          raw: demoRawValue(register, value),
          available: true
        };
      }) : [];
      if (lastData) {
        if (!document.querySelector('#dashboard-view').hidden) {
          renderEnergyFlow(lastData, demoRegisterRows);
        } else {
          const demoFanSpeed = Number(scenario.values.get(801));
          updateInverterFanAnimation(
            document.querySelector('#energy-inverter-fan-row'),
            Number.isFinite(demoFanSpeed) ? Math.max(0, Math.min(100, demoFanSpeed)) : 0,
            true
          );
        }
        if (!document.querySelector('#lcd-view').hidden) {
          renderLcd(lastData, demoRegisterRows);
        }
      }
    }
    function trimChartHistory(history, currentTime) {
      const oldestAllowed = currentTime - chartWindowMilliseconds;
      while (history.length && history[0].time < oldestAllowed) history.shift();
    }
    function formatChartTime(timestamp) {
      const locale = currentLanguage === 'uk' ? 'uk-UA' : currentLanguage === 'ru' ? 'ru-RU' : 'en-GB';
      return new Date(timestamp).toLocaleTimeString(locale, {
        timeZone: 'Europe/Madrid',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    }
    async function fillChartExampleData() {
      if (chartDemoRunning) {
        chartDemoCancelRequested = true;
        return;
      }

      const selected = [...chartSelections].filter(key => chartDefinitions.has(key));
      const registerKeys = [...chartDefinitions.keys()].filter(key => key.startsWith('register-'));
      const meterKeys = [...chartDefinitions.keys()].filter(key => key.startsWith('meter-'));
      const demoKeys = [...new Set([...registerKeys, ...meterKeys, ...selected])];
      if (!demoKeys.length) return;

      const buttons = document.querySelectorAll('.all-data-demo-button');
      const setButtonState = (text, disabled = false) => buttons.forEach(button => {
        button.textContent = text;
        button.disabled = disabled;
      });
      const synchronizeDemoDefinitions = scenario => {
        const demoRegistersByNumber = new Map(
          (demoRegisterRows || []).map(register => [register.register, register])
        );
        registerKeys.forEach(key => {
          const item = chartDefinitions.get(key);
          if (!item) return;
          const scenarioValue = scenario.values.get(item.register);
          item.value = Number.isFinite(scenarioValue)
            ? scenarioValue
            : demoFallbackValue(item, scenario.elapsedSeconds);
          item.available = true;
          const demoRegister = demoRegistersByNumber.get(item.register);
          item.interpretation = demoRegister ? registerInterpretation(demoRegister) : '';
          item.source = `R${item.register} · ${t('demoMode')}`;
        });
        meterKeys.forEach(key => {
          const item = chartDefinitions.get(key);
          if (!item) return;
          const registerItem = chartDefinitions.get(key.replace('meter-', 'register-'));
          const scenarioValue = scenario.values.get(item.register);
          if (Number.isFinite(scenarioValue)) item.value = scenarioValue;
          else if (registerItem) item.value = registerItem.value;
          else item.value = demoFallbackValue(item, scenario.elapsedSeconds);
          item.available = true;
          item.source = `R${item.register} · ${t('demoMode')}`;
          if (registerItem) registerItem.value = item.value;
        });
      };
      chartDemoRunning = true;
      chartDemoCancelRequested = false;
      document.documentElement.classList.add('demo-energy-flow');
      demoKeys.forEach(key => chartHistory.set(key, []));
      const initialScenario = realisticDemoScenario(0);
      applyDemoEnergyFrame(initialScenario);
      if (lastData) render(lastData);
      synchronizeDemoDefinitions(initialScenario);
      if (!document.querySelector('#dashboard-view').hidden) renderDashboardValues();
      drawAllCharts();

      try {
        const demoStartedAt = Date.now();
        while (Date.now() - demoStartedAt < chartWindowMilliseconds) {
          const elapsedBeforeWait = Math.floor((Date.now() - demoStartedAt) / 1000);
          setButtonState(t('stopDemo', {
            elapsed: elapsedBeforeWait,
            seconds: chartWindowSeconds,
            count: registerKeys.length
          }));
          const selectedIndex = Number(document.querySelector('#poll-rate').value);
          await wait(requestIntervals[selectedIndex] ?? 2000);
          if (chartDemoCancelRequested) break;

          const now = Date.now();
          const elapsedSeconds = Math.min(
            chartWindowSeconds - .001,
            (now - demoStartedAt) / 1000
          );
          const scenario = realisticDemoScenario(elapsedSeconds);
          applyDemoEnergyFrame(scenario);
          synchronizeDemoDefinitions(scenario);
          registerKeys.forEach(key => {
            const item = chartDefinitions.get(key);
            if (!item) return;
            const history = chartHistory.get(key) || [];
            history.push({time: now, value: item.value});
            trimChartHistory(history, now);
            chartHistory.set(key, history);
          });
          meterKeys.forEach(key => {
            const item = chartDefinitions.get(key);
            if (!item) return;
            const history = chartHistory.get(key) || [];
            history.push({time: now, value: item.value});
            trimChartHistory(history, now);
            chartHistory.set(key, history);
          });
          const elapsed = Math.min(
            chartWindowSeconds,
            Math.floor((now - demoStartedAt) / 1000)
          );
          setButtonState(t('stopDemo', {
            elapsed,
            seconds: chartWindowSeconds,
            count: registerKeys.length
          }));
          if (!document.querySelector('#dashboard-view').hidden) {
            renderDashboardValues();
            scheduleRegisterRender(demoRegisterRows);
            renderSolarEnergy(demoSolarEnergySummary(elapsedSeconds));
          }
          if (!document.querySelector('#charts-view').hidden) scheduleVisibleChartDraw();
        }
      } finally {
        chartDemoRunning = false;
        chartDemoCancelRequested = false;
        document.documentElement.classList.remove('demo-energy-flow');
        demoRegisterRows = null;
        demoFlowCase = '';
        demoGeneratorPower = 0;
        demoPvVoltage = 0;
        demoPvPower = 0;
        setButtonState(t('runDemo'));
        if (lastData) {
          recordChartSamples(lastData);
          render(lastData);
        }
      }
    }
