    const disabledButtonObserver = new MutationObserver(mutations => {
      mutations.forEach(mutation => refreshDisabledButtonHints(mutation.target));
    });
    disabledButtonObserver.observe(document.body, {
      attributes: true,
      attributeFilter: ['disabled'],
      subtree: true
    });

    applyTheme(initialTheme(), false);
    applyLanguage(initialLanguage(), false);

    document.querySelector('#poll-rate').addEventListener('change', event => {
      const pollRateIndex = Number(event.target.value);
      if (lastData) {
        lastData.poll_rate_index = pollRateIndex;
        renderCycleStatus(lastData);
      }
      updateSetting('poll_rate_index', pollRateIndex);
    });
    document.querySelector('#read-mode').addEventListener('change', event =>
      updateSetting('read_mode', event.target.value));
    document.querySelector('#demo-button').addEventListener('click', fillChartExampleData);
    document.querySelector('#chart-demo-button').addEventListener('click', fillChartExampleData);
    document.querySelector('#manage-values-button').addEventListener('click', openGaugePicker);
    document.querySelector('#register-log-start').addEventListener('click', () => updateRegisterLog('start'));
    document.querySelector('#register-log-stop').addEventListener('click', () => updateRegisterLog('stop'));
    document.querySelector('#register-log-mark').addEventListener('click', () =>
      updateRegisterLog('mark', document.querySelector('#register-log-note').value));
    document.querySelector('#register-log-note').addEventListener('keydown', event => {
      if (event.key === 'Enter') updateRegisterLog('mark', event.currentTarget.value);
    });
    document.querySelector('#register-map-upload-button').addEventListener('click', () =>
      document.querySelector('#register-map-file').click());
    document.querySelector('#register-map-file').addEventListener('change', event =>
      void uploadRegisterMap(event.currentTarget.files?.[0]));
    document.querySelector('#search').addEventListener('input', () =>
      demoRegisterRows
        ? renderRegisters(demoRegisterRows)
        : lastData && renderRegisters(lastData.registers));
    document.querySelector('.view-tabs').addEventListener('click', event => {
      const tab = event.target.closest('.view-tab[data-view]');
      if (tab) showView(tab.dataset.view);
    });
    document.querySelector('.view-tabs').addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      const tabs = [...event.currentTarget.querySelectorAll('.view-tab[data-view]')];
      const currentIndex = Math.max(0, tabs.indexOf(document.activeElement));
      const nextIndex = event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? tabs.length - 1
          : (currentIndex + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
      event.preventDefault();
      tabs[nextIndex].focus();
      showView(tabs[nextIndex].dataset.view);
    });
    document.querySelector('.lcd-controls').addEventListener('click', event => {
      const button = event.target.closest('[data-lcd-key]');
      if (button) handleLcdKey(button.dataset.lcdKey);
    });
    window.addEventListener('keydown', event => {
      if (currentView !== 'lcd' || event.target?.closest?.('input, select, textarea')) return;
      const key = ({Escape:'escape', ArrowUp:'up', ArrowDown:'down', Enter:'enter'})[event.key];
      if (!key) return;
      event.preventDefault();
      handleLcdKey(key);
    });
    document.querySelector('#app-toggle').addEventListener('click', async event => {
      if (!lastData) return;
      const toggleButton = event.currentTarget;
      const paused = !lastData.paused;
      lastData.paused = paused;
      render(lastData);
      toggleButton.disabled = true;
      try {
        await updateSetting('paused', paused);
      } finally {
        toggleButton.disabled = false;
      }
    });
    document.querySelector('#theme-toggle').addEventListener('change', event =>
      applyTheme(event.target.checked ? 'light' : 'dark'));
    document.querySelector('.language-switch').addEventListener('click', event => {
      const button = event.target.closest('button[data-language]');
      if (button) applyLanguage(button.dataset.language);
    });
    document.querySelector('#chart-search').addEventListener('input', renderChartValueList);
    document.querySelector('#chart-select-all').addEventListener('click', selectAllGaugeSelections);
    document.querySelector('#chart-clear-all').addEventListener('click', clearGaugeSelections);
    document.querySelector('#chart-grid').addEventListener('click', event => {
      const pageButton = event.target.closest('button[data-chart-page]');
      if (pageButton && !pageButton.disabled) changeChartPage(pageButton.dataset.chartPage);
    });
    document.querySelector('#dashboard-clear-gauges').addEventListener('click', clearGaugeSelections);
    document.querySelector('#chart-value-list').addEventListener('change', event => {
      const checkbox = event.target.closest('input[data-value-key]');
      if (!checkbox) return;
      const key = checkbox.dataset.valueKey;
      if (checkbox.checked) {
        dashboardSelections.add(key);
        chartSelections.add(key);
        chartHistory.set(key, []);
      } else {
        dashboardSelections.delete(key);
        chartSelections.delete(key);
        chartHistory.delete(key);
      }
      saveSelections('inverter-dashboard-gauges-v2', dashboardSelections);
      saveSelections('inverter-chart-values-v2', chartSelections);
      renderDashboardValues();
      renderChartCards();
      renderGaugePickerList();
    });
    document.querySelector('#gauge-picker-search').addEventListener('input', renderGaugePickerList);
    document.querySelector('#select-all-gauges').addEventListener('click', selectAllGaugeSelections);
    document.querySelector('#clear-all-gauges').addEventListener('click', clearGaugeSelections);
    document.querySelector('#gauge-picker-list').addEventListener('change', event => {
      const checkbox = event.target.closest('input[data-picker-value-key]');
      if (!checkbox) return;
      const key = checkbox.dataset.pickerValueKey;
      if (checkbox.checked) {
        dashboardSelections.add(key);
        chartSelections.add(key);
        chartHistory.set(key, []);
      } else {
        dashboardSelections.delete(key);
        chartSelections.delete(key);
        chartHistory.delete(key);
      }
      saveSelections('inverter-dashboard-gauges-v2', dashboardSelections);
      saveSelections('inverter-chart-values-v2', chartSelections);
      renderDashboardValues();
      renderChartCards();
      renderChartValueList();
    });
    document.querySelector('[data-close-gauge-picker]').addEventListener('click', () =>
      document.querySelector('#gauge-picker').close());
    document.querySelector('#gauge-picker').addEventListener('click', event => {
      if (event.target === event.currentTarget) event.currentTarget.close();
    });
    const gaugeHost = document.querySelector('#gauges');
    const dashboardGaugeToolbar = document.querySelector('#dashboard-gauge-toolbar');
    let draggedGauge = null;
    let pointerDraggedGauge = null;
    let pointerDragHandle = null;

    function saveDashboardOrderFromCards() {
      const orderedKeys = [...gaugeHost.querySelectorAll('[data-dashboard-key]')]
        .map(card => card.dataset.dashboardKey)
        .filter(key => dashboardSelections.has(key));
      const visibleKeys = new Set(orderedKeys);
      const remainingKeys = [...dashboardSelections].filter(key => !visibleKeys.has(key));
      const insertionIndex = Math.min(
        dashboardGaugePage * DASHBOARD_GAUGES_PER_PAGE,
        remainingKeys.length
      );
      remainingKeys.splice(insertionIndex, 0, ...orderedKeys);
      dashboardSelections.clear();
      remainingKeys.forEach(key => dashboardSelections.add(key));
      saveSelections('inverter-dashboard-gauges-v2', dashboardSelections);
      renderDashboardValues();
    }

    function placeGaugeAtPointer(card, target, clientX, clientY) {
      gaugeHost.querySelectorAll('.drag-target').forEach(item => item.classList.remove('drag-target'));
      if (!target || target === card || !gaugeHost.contains(target)) return;
      target.classList.add('drag-target');
      const bounds = target.getBoundingClientRect();
      const cardBounds = card.getBoundingClientRect();
      const sameRow = Math.abs(bounds.top - cardBounds.top) < bounds.height / 2;
      const placeAfter = sameRow
        ? clientX > bounds.left + bounds.width / 2
        : clientY > bounds.top + bounds.height / 2;
      target[placeAfter ? 'after' : 'before'](card);
    }

    gaugeHost.addEventListener('dragstart', event => {
      const card = event.target.closest('.gauge-card[data-dashboard-key]');
      if (!card) return;
      draggedGauge = card;
      card.classList.add('dragging');
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', card.dataset.dashboardKey);
    });
    gaugeHost.addEventListener('dragover', event => {
      if (!draggedGauge) return;
      event.preventDefault();
      const target = event.target.closest('.gauge-card[data-dashboard-key]');
      placeGaugeAtPointer(draggedGauge, target, event.clientX, event.clientY);
    });
    gaugeHost.addEventListener('drop', event => {
      if (!draggedGauge) return;
      event.preventDefault();
      saveDashboardOrderFromCards();
    });
    gaugeHost.addEventListener('dragend', () => {
      gaugeHost.querySelectorAll('.dragging, .drag-target').forEach(card =>
        card.classList.remove('dragging', 'drag-target'));
      draggedGauge = null;
    });

    gaugeHost.addEventListener('pointerdown', event => {
      const handle = event.target.closest('.drag-handle');
      if (!handle || event.button !== 0 || event.isPrimary === false) return;
      const card = handle.closest('.gauge-card[data-dashboard-key]');
      if (!card) return;
      event.preventDefault();
      pointerDraggedGauge = card;
      pointerDragHandle = handle;
      card.classList.add('pointer-dragging');
      handle.setPointerCapture(event.pointerId);
    });

    gaugeHost.addEventListener('pointermove', event => {
      if (!pointerDraggedGauge || !pointerDragHandle) return;
      event.preventDefault();
      if (event.clientY < 70) window.scrollBy(0, -14);
      if (event.clientY > window.innerHeight - 70) window.scrollBy(0, 14);

      const previousVisibility = pointerDraggedGauge.style.visibility;
      pointerDraggedGauge.style.visibility = 'hidden';
      const elementBelow = document.elementFromPoint(event.clientX, event.clientY);
      pointerDraggedGauge.style.visibility = previousVisibility;
      const target = elementBelow?.closest('.gauge-card[data-dashboard-key]') || null;
      placeGaugeAtPointer(pointerDraggedGauge, target, event.clientX, event.clientY);
    });

    function finishPointerGaugeDrag(event) {
      if (!pointerDraggedGauge) return;
      if (pointerDragHandle?.hasPointerCapture(event.pointerId)) {
        pointerDragHandle.releasePointerCapture(event.pointerId);
      }
      pointerDraggedGauge.classList.remove('pointer-dragging');
      gaugeHost.querySelectorAll('.drag-target').forEach(card => card.classList.remove('drag-target'));
      pointerDraggedGauge = null;
      pointerDragHandle = null;
      saveDashboardOrderFromCards();
    }

    gaugeHost.addEventListener('pointerup', finishPointerGaugeDrag);
    gaugeHost.addEventListener('pointercancel', finishPointerGaugeDrag);

    function handleDashboardPaginationClick(event) {
      const pageButton = event.target.closest('button[data-dashboard-page]');
      if (pageButton && !pageButton.disabled) {
        changeDashboardGaugePage(pageButton.dataset.dashboardPage);
        return true;
      }
      return false;
    }
    dashboardGaugeToolbar.addEventListener('click', handleDashboardPaginationClick);

    gaugeHost.addEventListener('click', event => {
      if (handleDashboardPaginationClick(event)) return;
      if (event.target.closest('[data-open-gauge-picker]')) {
        openGaugePicker();
        return;
      }
      const button = event.target.closest('button[data-remove-dashboard]');
      if (!button) return;
      const key = button.dataset.removeDashboard;
      dashboardSelections.delete(key);
      chartSelections.delete(key);
      chartHistory.delete(key);
      saveSelections('inverter-dashboard-gauges-v2', dashboardSelections);
      saveSelections('inverter-chart-values-v2', chartSelections);
      renderDashboardValues();
      renderChartCards();
      renderChartValueList();
      renderGaugePickerList();
    });
    window.addEventListener('resize', scheduleVisibleChartDraw);
    window.addEventListener('scroll', () => {
      if (!document.querySelector('#charts-view').hidden) scheduleVisibleChartDraw();
    }, {passive: true});
    document.addEventListener('visibilitychange', () => {
      if (!pageIsActive || lastData?.paused) return;
      scheduleRefresh(document.hidden ? null : 0);
    });
    window.addEventListener('pagehide', () => {
      pageIsActive = false;
      if (refreshTimer !== null) window.clearTimeout(refreshTimer);
      refreshTimer = null;
      refreshController?.abort();
    });
    window.addEventListener('pageshow', event => {
      if (!event.persisted) return;
      pageIsActive = true;
      if (!lastData?.paused) scheduleRefresh(0);
    });
    const initialData = window.__INITIAL_STATE__ ?? null;
    if (initialData) {
      lastData = initialData;
      render(initialData);
      recordChartSamples(initialData);
      if (!initialData.paused) {
        window.addEventListener('load', () => scheduleRefresh(), {once: true});
      }
    } else {
      refresh();
    }
    document.documentElement.classList.remove('booting');
