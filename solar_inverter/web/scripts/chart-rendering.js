    const chartPlots = new Map();
    const chartInteractionStates = new WeakMap();
    const CHART_UPDATE_ANIMATION_MS = 260;
    let modalChartPlot = null;
    let modalChartKey = '';

    function chartSeriesData(history) {
      const ordered = [...history]
        .filter(point => Number.isFinite(point.time) && Number.isFinite(point.value))
        .sort((left, right) => left.time - right.time);
      const unique = [];
      ordered.forEach(point => {
        if (unique.at(-1)?.time === point.time) unique[unique.length - 1] = point;
        else unique.push(point);
      });
      return [
        unique.map(point => point.time / 1000),
        unique.map(point => point.value)
      ];
    }

    function chartPointTime(timestampSeconds) {
      const locale = currentLanguage === 'uk' ? 'uk-UA' : currentLanguage === 'ru' ? 'ru-RU' : 'en-GB';
      const longPeriod = chartWindowSeconds > 86400;
      return new Date(timestampSeconds * 1000).toLocaleString(locale, {
        timeZone: 'Europe/Madrid',
        month: longPeriod ? 'short' : undefined,
        day: longPeriod ? '2-digit' : undefined,
        hour: longPeriod && chartWindowSeconds > 2592000 ? undefined : '2-digit',
        minute: longPeriod && chartWindowSeconds > 2592000 ? undefined : '2-digit',
        second: chartWindowSeconds <= 3600 ? '2-digit' : undefined
      });
    }

    function chartAxisTime(plot, timestampSeconds) {
      const locale = currentLanguage === 'uk' ? 'uk-UA' : currentLanguage === 'ru' ? 'ru-RU' : 'en-GB';
      const visibleSeconds = Math.max(0, Number(plot.scales.x.max) - Number(plot.scales.x.min));
      const options = visibleSeconds <= 3600
        ? {hour: '2-digit', minute: '2-digit', second: '2-digit'}
        : visibleSeconds <= 172800
          ? {day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'}
          : visibleSeconds <= 7776000
            ? {day: '2-digit', month: '2-digit'}
            : {month: '2-digit', year: '2-digit'};
      return new Date(timestampSeconds * 1000).toLocaleString(locale, {
        ...options,
        timeZone: 'Europe/Madrid'
      });
    }

    function constrainedTimeScale(plot, minimum, maximum) {
      const timestamps = plot.data?.[0];
      if (!timestamps?.length || !Number.isFinite(minimum) || !Number.isFinite(maximum)) return null;
      const dataMinimum = timestamps[0];
      const dataMaximum = timestamps.at(-1);
      const dataRange = dataMaximum - dataMinimum;
      const requestedRange = maximum - minimum;
      if (requestedRange >= dataRange) return {min: dataMinimum, max: dataMaximum};
      if (minimum < dataMinimum) return {min: dataMinimum, max: dataMinimum + requestedRange};
      if (maximum > dataMaximum) return {min: dataMaximum - requestedRange, max: dataMaximum};
      return {min: minimum, max: maximum};
    }

    function chartTooltipPlugin(item) {
      let tooltip;
      return {
        hooks: {
          ready: [plot => {
            tooltip = document.createElement('div');
            tooltip.className = 'chart-point-tooltip';
            tooltip.hidden = true;
            plot.over.appendChild(tooltip);
          }],
          setCursor: [plot => {
            const index = plot.cursor.idx;
            if (!tooltip || index === null || index === undefined || !Number.isFinite(plot.data[1][index])) {
              if (tooltip) tooltip.hidden = true;
              return;
            }
            tooltip.hidden = false;
            tooltip.textContent = `${chartPointTime(plot.data[0][index])} · ${Number(plot.data[1][index].toFixed(2))} ${item.unit || ''}`.trim();
            const left = Math.min(plot.bbox.width - tooltip.offsetWidth - 8, Math.max(8, plot.cursor.left + 12));
            const top = Math.min(plot.bbox.height - tooltip.offsetHeight - 8, Math.max(8, plot.cursor.top + 12));
            tooltip.style.transform = `translate(${left}px,${top}px)`;
          }]
        }
      };
    }

    function chartWheelZoomPlugin() {
      let cleanup = () => {};
      return {
        hooks: {
          ready: [plot => {
            chartInteractionStates.set(plot, {
              ready: true,
              updating: false,
              userZoomed: false,
              animationFrame: 0
            });
            const pointers = new Map();
            let pan = null;
            let pinch = null;
            let lastTapAt = 0;
            let suppressNextClick = false;
            const isModal = Boolean(plot.over.closest('#chart-modal-host'));
            plot.over.style.cursor = 'grab';
            if (isModal) plot.over.style.touchAction = 'none';
            const markUserZoomed = () => {
              const state = chartInteractionStates.get(plot);
              if (state) state.userZoomed = true;
            };
            const minimumRange = () => {
              const timestamps = plot.data?.[0] || [];
              const dataRange = Math.max(0, Number(timestamps.at(-1)) - Number(timestamps[0]));
              return Math.max(1, Math.min(30, dataRange / 10 || 1));
            };
            const pointerX = point => {
              const bounds = plot.over.getBoundingClientRect();
              return Math.max(0, Math.min(bounds.width, point.clientX - bounds.left));
            };
            const startPinch = () => {
              const points = [...pointers.values()].slice(0, 2);
              if (points.length < 2) return;
              const [first, second] = points;
              const centreX = (pointerX(first) + pointerX(second)) / 2;
              pinch = {
                distance: Math.max(1, Math.hypot(second.clientX - first.clientX, second.clientY - first.clientY)),
                centreX,
                anchor: plot.posToVal(centreX, 'x'),
                minimum: plot.scales.x.min,
                maximum: plot.scales.x.max,
                moved: false
              };
              pan = null;
            };
            const wheel = event => {
              event.preventDefault();
              const scale = plot.scales.x;
              if (!Number.isFinite(scale.min) || !Number.isFinite(scale.max)) return;
              markUserZoomed();
              const range = scale.max - scale.min;
              if (event.shiftKey || Math.abs(event.deltaX) > Math.abs(event.deltaY)) {
                const shift = range * (event.deltaX || event.deltaY) / 700;
                const nextScale = constrainedTimeScale(plot, scale.min + shift, scale.max + shift);
                if (nextScale) plot.setScale('x', nextScale);
                return;
              }
              const factor = Math.exp(event.deltaY * .0015);
              const anchor = plot.posToVal(event.offsetX, 'x');
              const nextRange = Math.max(minimumRange(), Math.min(chartWindowSeconds, range * factor));
              const ratio = (anchor - scale.min) / range;
              const minimum = anchor - nextRange * ratio;
              const nextScale = constrainedTimeScale(plot, minimum, minimum + nextRange);
              if (nextScale) plot.setScale('x', nextScale);
            };
            const pointerDown = event => {
              if (event.button !== 0 || !Number.isFinite(plot.scales.x.min) || !Number.isFinite(plot.scales.x.max)) return;
              if (event.pointerType === 'touch' && !isModal) return;
              pointers.set(event.pointerId, {clientX: event.clientX, clientY: event.clientY});
              plot.over.setPointerCapture?.(event.pointerId);
              if (pointers.size >= 2) {
                event.preventDefault();
                startPinch();
                plot.over.style.cursor = 'grabbing';
                return;
              }
              pan = {
                pointerId: event.pointerId,
                clientX: event.clientX,
                minimum: plot.scales.x.min,
                maximum: plot.scales.x.max,
                moved: false
              };
              plot.over.style.cursor = 'grabbing';
            };
            const pointerMove = event => {
              if (!pointers.has(event.pointerId)) return;
              pointers.set(event.pointerId, {clientX: event.clientX, clientY: event.clientY});
              if (pointers.size >= 2) {
                event.preventDefault();
                if (!pinch) startPinch();
                const points = [...pointers.values()].slice(0, 2);
                const [first, second] = points;
                const distance = Math.max(1, Math.hypot(second.clientX - first.clientX, second.clientY - first.clientY));
                const centreX = (pointerX(first) + pointerX(second)) / 2;
                if (!pinch || (Math.abs(distance - pinch.distance) < 2 && Math.abs(centreX - pinch.centreX) < 2 && !pinch.moved)) return;
                pinch.moved = true;
                suppressNextClick = true;
                const initialRange = pinch.maximum - pinch.minimum;
                const dataRange = Math.max(0, plot.data[0].at(-1) - plot.data[0][0]);
                const nextRange = Math.max(minimumRange(), Math.min(dataRange, initialRange * pinch.distance / distance));
                const width = Math.max(1, plot.over.clientWidth);
                const minimum = pinch.anchor - nextRange * centreX / width;
                const nextScale = constrainedTimeScale(plot, minimum, minimum + nextRange);
                markUserZoomed();
                if (nextScale) plot.setScale('x', nextScale);
                return;
              }
              if (!pan || event.pointerId !== pan.pointerId) return;
              const deltaPixels = event.clientX - pan.clientX;
              if (Math.abs(deltaPixels) < 2 && !pan.moved) return;
              event.preventDefault();
              pan.moved = true;
              suppressNextClick = true;
              const width = Math.max(1, plot.over.clientWidth);
              const shift = -deltaPixels * (pan.maximum - pan.minimum) / width;
              const nextScale = constrainedTimeScale(
                plot,
                pan.minimum + shift,
                pan.maximum + shift
              );
              markUserZoomed();
              if (nextScale) plot.setScale('x', nextScale);
            };
            const pointerUp = (event, cancelled = false) => {
              if (!pointers.has(event.pointerId)) return;
              const gestureMoved = Boolean(pan?.moved || pinch?.moved);
              plot.over.releasePointerCapture?.(event.pointerId);
              pointers.delete(event.pointerId);
              if (pointers.size === 1) {
                const [pointerId, point] = pointers.entries().next().value;
                pan = {
                  pointerId,
                  clientX: point.clientX,
                  minimum: plot.scales.x.min,
                  maximum: plot.scales.x.max,
                  moved: gestureMoved
                };
                pinch = null;
                return;
              }
              pan = null;
              pinch = null;
              plot.over.style.cursor = 'grab';
              if (!cancelled && event.pointerType === 'touch' && isModal && !gestureMoved) {
                const now = performance.now();
                if (now - lastTapAt < 350) {
                  resetChartZoom(plot);
                  lastTapAt = 0;
                } else lastTapAt = now;
              }
            };
            const suppressGestureClick = event => {
              if (!suppressNextClick) return;
              suppressNextClick = false;
              event.preventDefault();
              event.stopImmediatePropagation();
            };
            const pointerCancel = event => pointerUp(event, true);
            const reset = () => resetChartZoom(plot);
            plot.over.addEventListener('wheel', wheel, {passive: false});
            plot.over.addEventListener('pointerdown', pointerDown);
            plot.over.addEventListener('pointermove', pointerMove, {passive: false});
            plot.over.addEventListener('pointerup', pointerUp);
            plot.over.addEventListener('pointercancel', pointerCancel);
            plot.over.addEventListener('click', suppressGestureClick, true);
            plot.over.addEventListener('dblclick', reset);
            cleanup = () => {
              plot.over.removeEventListener('wheel', wheel);
              plot.over.removeEventListener('pointerdown', pointerDown);
              plot.over.removeEventListener('pointermove', pointerMove);
              plot.over.removeEventListener('pointerup', pointerUp);
              plot.over.removeEventListener('pointercancel', pointerCancel);
              plot.over.removeEventListener('click', suppressGestureClick, true);
              plot.over.removeEventListener('dblclick', reset);
            };
          }],
          destroy: [plot => {
            const state = chartInteractionStates.get(plot);
            if (state?.animationFrame) cancelAnimationFrame(state.animationFrame);
            cleanup();
          }]
        }
      };
    }

    function resetChartZoom(plot = modalChartPlot) {
      if (!plot?.data?.[0]?.length) return;
      const state = chartInteractionStates.get(plot);
      if (state) {
        state.userZoomed = false;
        state.updating = true;
      }
      plot.setScale('x', {min: plot.data[0][0], max: plot.data[0].at(-1)});
      if (state) state.updating = false;
    }

    function applyChartData(plot, data) {
      const state = chartInteractionStates.get(plot);
      if (state) state.updating = true;
      plot.setData(data, !state?.userZoomed);
      if (state) state.updating = false;
    }

    function updateChartData(plot, data) {
      const state = chartInteractionStates.get(plot);
      if (state?.animationFrame) {
        cancelAnimationFrame(state.animationFrame);
        state.animationFrame = 0;
      }
      const previousTimes = plot.data?.[0] || [];
      const previousValues = plot.data?.[1] || [];
      const targetTimes = data?.[0] || [];
      const targetValues = data?.[1] || [];
      const targetIndex = targetTimes.length - 1;
      const previousIndex = previousTimes.length - 1;
      const targetTime = targetTimes[targetIndex];
      const targetValue = targetValues[targetIndex];
      const previousTime = previousTimes[previousIndex];
      const previousValue = previousValues[previousIndex];
      const unchanged = targetTimes.length === previousTimes.length
        && targetTime === previousTime
        && targetValue === previousValue;
      if (unchanged) return;

      const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
      const canAnimate = !document.hidden
        && !reduceMotion
        && targetTimes.length >= 2
        && previousTimes.length >= 1
        && targetTimes.length <= previousTimes.length + 1
        && Number.isFinite(targetTime)
        && Number.isFinite(targetValue)
        && Number.isFinite(previousTime)
        && Number.isFinite(previousValue);
      if (!canAnimate) {
        applyChartData(plot, data);
        return;
      }

      const startedAt = performance.now();
      const leadingTimes = targetTimes.slice(0, -1);
      const leadingValues = targetValues.slice(0, -1);
      const animate = now => {
        const progress = Math.min(1, (now - startedAt) / CHART_UPDATE_ANIMATION_MS);
        const eased = progress * progress * (3 - 2 * progress);
        const frameData = [
          [...leadingTimes, previousTime + (targetTime - previousTime) * eased],
          [...leadingValues, previousValue + (targetValue - previousValue) * eased]
        ];
        applyChartData(plot, frameData);
        if (progress < 1) {
          if (state) state.animationFrame = requestAnimationFrame(animate);
        } else {
          if (state) state.animationFrame = 0;
          applyChartData(plot, data);
        }
      };
      if (state) state.animationFrame = requestAnimationFrame(animate);
      else applyChartData(plot, data);
    }

    function chartOptions(host, item, colour, height) {
      const styles = getComputedStyle(document.documentElement);
      return {
        width: Math.max(220, Math.floor(host.clientWidth || 300)),
        height,
        tzDate: timestamp => new Date(timestamp * 1000),
        padding: [12, 10, 4, 4],
        scales: {x: {time: true}, y: {auto: true}},
        axes: [
          {
            stroke: styles.getPropertyValue('--muted').trim(),
            grid: {stroke: styles.getPropertyValue('--chart-grid-line').trim()},
            space: host.clientWidth < 480 ? 90 : 70,
            values: (plot, ticks) => ticks.map(timestamp => chartAxisTime(plot, timestamp))
          },
          {stroke: styles.getPropertyValue('--muted').trim(), grid: {stroke: styles.getPropertyValue('--chart-grid-line').trim()}, size: 52}
        ],
        cursor: {drag: {x: false, y: false, setScale: false}, focus: {prox: 24}},
        legend: {show: false},
        series: [
          {},
          {label: item.label, value: (_plot, value) => value == null ? '—' : `${Number(value.toFixed(2))} ${item.unit || ''}`.trim(), stroke: colour, width: 2.5, points: {show: false}}
        ],
        plugins: [chartTooltipPlugin(item), chartWheelZoomPlugin()]
      };
    }

    function resolvedChartColour(token) {
      const styles = getComputedStyle(document.documentElement);
      const property = /^var\((--[^)]+)\)$/.exec(token)?.[1];
      return property ? styles.getPropertyValue(property).trim() : token;
    }

    function upsertChart(host, item, history, colour, height = 220) {
      if (typeof uPlot !== 'function') return null;
      const data = chartSeriesData(history);
      let plot = chartPlots.get(host);
      if (!plot) {
        plot = new uPlot(chartOptions(host, item, colour, height), data, host);
        chartPlots.set(host, plot);
      } else {
        updateChartData(plot, data);
        const width = Math.max(260, Math.floor(host.clientWidth || 300));
        if (plot.width !== width || plot.height !== height) plot.setSize({width, height});
      }
      return plot;
    }

    function destroyDetachedCharts() {
      chartPlots.forEach((plot, host) => {
        if (!host.isConnected) {
          plot.destroy();
          chartPlots.delete(host);
        }
      });
    }

    function drawAllCharts() {
      if (document.querySelector('#charts-view').hidden) return;
      destroyDetachedCharts();
      [...visibleChartCanvases].forEach(host => {
        if (!host.isConnected || host.clientWidth <= 0) return;
        const key = host.dataset.chartKey;
        const item = chartDefinitions.get(key);
        if (!item) return;
        const colour = resolvedChartColour(host.dataset.chartColour || colours[0]) || colours[0];
        const history = chartHistory.get(key) || [];
        upsertChart(host, item, history, colour);
        const latest = document.querySelector(`#latest-${key}`);
        if (latest) latest.textContent = history.length
          ? `${Number(history.at(-1).value.toFixed(2))} ${item.unit || ''}`.trim()
          : t('waiting');
      });
      updateModalChart();
    }

    function updateModalChart() {
      const dialog = document.querySelector('#chart-modal');
      if (!dialog?.open || !modalChartKey) return;
      const item = chartDefinitions.get(modalChartKey);
      const host = document.querySelector('#chart-modal-host');
      if (!item || !host || typeof uPlot !== 'function') return;
      const history = chartHistory.get(modalChartKey) || [];
      const colour = resolvedChartColour(dashboardGaugeColour(item) || colours[0]) || colours[0];
      const data = chartSeriesData(history);
      const height = Math.max(320, Math.floor(host.clientHeight || window.innerHeight * .62));
      const width = Math.max(220, Math.floor(host.clientWidth || window.innerWidth * .75));
      if (!modalChartPlot) {
        modalChartPlot = new uPlot({...chartOptions(host, item, colour, height), width}, data, host);
      } else {
        updateChartData(modalChartPlot, data);
        if (modalChartPlot.width !== width || modalChartPlot.height !== height) modalChartPlot.setSize({width, height});
      }
    }

    function openChartModal(key) {
      const item = chartDefinitions.get(key);
      const dialog = document.querySelector('#chart-modal');
      if (!item || !dialog) return;
      modalChartKey = key;
      document.querySelector('#chart-modal-title').textContent = item.label;
      const period = chartPeriodLabel(chartPeriodForItem(item));
      document.querySelector('#chart-modal-detail').textContent =
        `${item.detail} · ${t('chartPeriodValue', {period})}`;
      modalChartPlot?.destroy();
      modalChartPlot = null;
      if (typeof dialog.showModal === 'function') dialog.showModal(); else dialog.setAttribute('open', '');
      requestAnimationFrame(updateModalChart);
    }

    function closeChartModal() {
      const dialog = document.querySelector('#chart-modal');
      modalChartPlot?.destroy();
      modalChartPlot = null;
      modalChartKey = '';
      if (dialog?.open && typeof dialog.close === 'function') dialog.close(); else dialog?.removeAttribute('open');
    }

    let chartDrawPending = false;
    function scheduleVisibleChartDraw() {
      if (chartDrawPending) return;
      chartDrawPending = true;
      requestAnimationFrame(() => {
        chartDrawPending = false;
        drawAllCharts();
      });
    }
