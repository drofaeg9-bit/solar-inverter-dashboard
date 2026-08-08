    const DASHBOARD_GAUGES_PER_PAGE = 12;
    let dashboardGaugePage = 0;

    function niceGaugeLimit(value) {
      const positive = Math.max(1, Math.abs(value));
      const magnitude = 10 ** Math.floor(Math.log10(positive));
      const normalized = positive / magnitude;
      const step = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
      return step * magnitude;
    }
    function dashboardGaugeBounds(item) {
      if (Number.isFinite(item.minimum) && Number.isFinite(item.maximum) && item.maximum > item.minimum) {
        return {minimum: item.minimum, maximum: item.maximum};
      }
      const matchingMeter = chartDefinitions.get(`meter-${item.register}`);
      if (matchingMeter && Number.isFinite(matchingMeter.minimum) && Number.isFinite(matchingMeter.maximum)) {
        return {minimum: matchingMeter.minimum, maximum: matchingMeter.maximum};
      }
      if (item.unit === '%') return {minimum: 0, maximum: 100};

      const value = Number.isFinite(item.value) ? item.value : 0;
      const previousRange = dashboardGaugeRanges.get(item.key);
      if (previousRange && value >= previousRange.minimum && value <= previousRange.maximum) return previousRange;

      const range = value < 0
        ? {minimum: -niceGaugeLimit(Math.abs(value) * 1.2), maximum: niceGaugeLimit(Math.abs(value) * 1.2)}
        : {minimum: 0, maximum: niceGaugeLimit(Math.max(100, value * 1.2))};
      dashboardGaugeRanges.set(item.key, range);
      saveMap('inverter-dashboard-gauge-ranges-v2', dashboardGaugeRanges);
      return range;
    }
    function diagramGaugeColour(item) {
      const text = `${item.category || ''} ${item.label || ''} ${item.detail || ''}`.toLocaleLowerCase();
      if (/(pv|solar|соняч|солнеч)/u.test(text)) return 'var(--flow-solar-colour)';
      if (/(генератор|generator)/u.test(text)) return 'var(--flow-generator-colour)';
      if (/(батар|акумулятор|аккумулятор|battery|bms|заряд|charge|discharg)/u.test(text)) return 'var(--flow-battery-colour)';
      if (/(мереж|сеть|grid|mains)/u.test(text)) return 'var(--flow-grid-colour)';
      if (/(навантаж|нагруз|load|home|дім|дом)/u.test(text)) return 'var(--flow-home-colour)';
      if (/(інвертор|инвертор|inverter|вихід|выход|output|вентилят|fan)/u.test(text)) return 'var(--flow-inverter-colour)';
      return null;
    }
    function dashboardGaugeColour(item) {
      const diagramColour = diagramGaugeColour(item);
      if (diagramColour) return diagramColour;
      const key = item.key;
      const saved = dashboardGaugeColours.get(key);
      if (colours.includes(saved)) return saved;
      const activeColours = [...dashboardSelections]
        .filter(selectedKey => selectedKey !== key)
        .map(selectedKey => dashboardGaugeColours.get(selectedKey));
      const colour = colours.reduce((best, candidate) => {
        const uses = activeColours.filter(value => value === candidate).length;
        const bestUses = activeColours.filter(value => value === best).length;
        return uses < bestUses ? candidate : best;
      }, colours[0]);
      dashboardGaugeColours.set(key, colour);
      saveMap('inverter-dashboard-gauge-colours-v2', dashboardGaugeColours);
      return colour;
    }
    function chartColour(item, index = 0) {
      return diagramGaugeColour(item) || colours[index % colours.length];
    }
    function dashboardGaugeItems() {
      return [...dashboardSelections]
        .filter(key => chartDefinitions.has(key))
        .map(key => {
          const item = chartDefinitions.get(key);
          const bounds = showsSpeedometer(item) ? dashboardGaugeBounds(item) : {};
          return {...item, ...bounds, colour: dashboardGaugeColour(item)};
        });
    }
    function showsSpeedometer(item) {
      if (!Number.isFinite(item.value)) return false;
      return String(item.unit || '').trim().length > 0;
    }
    function dashboardGaugeSignature(gauges) {
      return `${currentLanguage}|${dashboardGaugePage}|${gauges.map(gauge =>
        `${gauge.key}:${gauge.label}:${gauge.detail}:${gauge.interpretation || ''}:${gauge.unit}:${gauge.minimum}:${gauge.maximum}:${gauge.colour}:${showsSpeedometer(gauge)}`).join('|')}`;
    }
    function dashboardGaugePaginationMarkup(pageCount) {
      if (pageCount <= 1) return '';
      return `<nav class="dashboard-pagination" aria-label="${t('dashboardPagination')}">
        <button type="button" data-dashboard-page="previous" ${dashboardGaugePage === 0 ? 'disabled' : ''}>${t('previousPage')}</button>
        <span>${t('chartPageSummary', {page: dashboardGaugePage + 1, pages: pageCount})}</span>
        <button type="button" data-dashboard-page="next" ${dashboardGaugePage === pageCount - 1 ? 'disabled' : ''}>${t('nextPage')}</button>
      </nav>`;
    }
    function changeDashboardGaugePage(direction) {
      dashboardGaugePage += direction === 'next' ? 1 : -1;
      renderDashboardValues();
    }
    function renderDashboardValues() {
      if (document.querySelector('#dashboard-view').hidden) return;
      const gauges = dashboardGaugeItems();
      const toolbar = document.querySelector('#dashboard-gauge-toolbar');
      const paginationHost = document.querySelector('#dashboard-pagination-host');
      toolbar.hidden = gauges.length === 0;
      if (!gauges.length) {
        dashboardGaugePage = 0;
        paginationHost.replaceChildren();
        const host = document.querySelector('#gauges');
        host.classList.add('empty-dashboard');
        host.innerHTML = addGaugeMarkup(true);
        host.dataset.keys = `${currentLanguage}|empty`;
        return;
      }
      const pageCount = Math.ceil(gauges.length / DASHBOARD_GAUGES_PER_PAGE);
      dashboardGaugePage = Math.max(0, Math.min(dashboardGaugePage, pageCount - 1));
      paginationHost.innerHTML = dashboardGaugePaginationMarkup(pageCount);
      const pageStart = dashboardGaugePage * DASHBOARD_GAUGES_PER_PAGE;
      renderGauges(gauges.slice(pageStart, pageStart + DASHBOARD_GAUGES_PER_PAGE), pageCount);
    }
    function scaleNumber(value, range) {
      if (Math.abs(value) >= 1000) {
        const compact = value / 1000;
        return `${Number(compact.toFixed(compact % 1 ? 1 : 0))}k`;
      }
      const decimals = range <= 20 ? 1 : 0;
      return Number(value.toFixed(decimals)).toString();
    }
    function scaleMarkup(meter) {
      const centreX = 120;
      const centreY = 120;
      const range = meter.maximum - meter.minimum;
      let markup = '';

      for (let index = 0; index <= 20; index += 1) {
        const angle = Math.PI + (Math.PI * index / 20);
        const major = index % 5 === 0;
        const outerRadius = 106;
        const innerRadius = major ? 94 : 99;
        const x1 = centreX + Math.cos(angle) * innerRadius;
        const y1 = centreY + Math.sin(angle) * innerRadius;
        const x2 = centreX + Math.cos(angle) * outerRadius;
        const y2 = centreY + Math.sin(angle) * outerRadius;
        markup += `<line class="tick${major ? ' major' : ''}" x1="${x1.toFixed(2)}" y1="${y1.toFixed(2)}" x2="${x2.toFixed(2)}" y2="${y2.toFixed(2)}"/>`;

        if (major) {
          const labelRadius = 81;
          const labelX = centreX + Math.cos(angle) * labelRadius;
          const labelY = centreY + Math.sin(angle) * labelRadius;
          const value = meter.minimum + range * index / 20;
          markup += `<text class="scale-label" x="${labelX.toFixed(2)}" y="${labelY.toFixed(2)}">${scaleNumber(value, range)}</text>`;
        }
      }
      return markup;
    }
    function addGaugeMarkup(empty = false) {
      return `<button class="add-gauge-card" type="button" data-open-gauge-picker aria-label="${t('addGauge')}">
        <span class="add-gauge-plus">+</span>
        <span class="add-gauge-label">${empty ? t('emptyDashboard') : t('addGauge')}</span>
      </button>`;
    }
    function gaugeMarkup(meter) {
      const showSpeedometer = showsSpeedometer(meter);
      return DashboardRenderers.gaugeCard({
        meter,
        label: localizeApiField(meter, 'label'),
        showSpeedometer,
        scale: showSpeedometer ? scaleMarkup(meter) : '',
        translations: {
          drag: t('dragGauge'),
          remove: t('removeDashboard')
        }
      });
    }
    function renderGauges(meters, pageCount) {
      const host = document.querySelector('#gauges');
      host.classList.remove('empty-dashboard');
      const signature = dashboardGaugeSignature(meters);
      if (host.dataset.keys !== signature) {
        host.dataset.keys = signature;
        host.innerHTML = meters.map(gaugeMarkup).join('')
          + addGaugeMarkup()
          + dashboardGaugePaginationMarkup(pageCount);
      }
      meters.forEach(meter => {
        const card = host.querySelector(`[data-dashboard-key="${meter.key}"]`);
        if (!card) return;
        const hasValue = Number.isFinite(meter.value);
        const value = hasValue ? meter.value : 0;
        const ratio = hasValue ? Math.max(0, Math.min(1, (value - meter.minimum) / (meter.maximum - meter.minimum))) : 0;
        const needleTransform = `rotate(${-90 + ratio * 180}deg)`;
        const progressOffset = `${283 * (1 - ratio)}`;
        const valueText = hasValue
          ? meter.displayValue || Number(value.toFixed(2)).toString()
          : '—';
        const needle = card.querySelector('.needle');
        const progress = card.querySelector('.progress');
        const valueElement = card.querySelector('.value');
        const sourceElement = card.querySelector('.source');

        if (needle && needle.style.transform !== needleTransform) needle.style.transform = needleTransform;
        if (progress && progress.style.strokeDashoffset !== progressOffset) progress.style.strokeDashoffset = progressOffset;
        if (valueElement.textContent !== valueText) valueElement.textContent = valueText;
        const localizedSource = meter.available === false ? t('noData') : localizeApiField(meter, 'source') || meter.detail;
        if (sourceElement.textContent !== localizedSource) sourceElement.textContent = localizedSource;

      });
    }
