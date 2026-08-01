const DashboardRenderers = (() => {
  function setText(selector, value) {
    const element = document.querySelector(selector);
    if (element && element.textContent !== value) element.textContent = value;
  }

  function energyCard({
    nodeSelector,
    active,
    values = {},
    valuesSelector = null,
    valuesVisible = null,
    directionSelector = null,
    direction = null
  }) {
    document.querySelector(nodeSelector)?.classList.toggle('active', Boolean(active));
    Object.entries(values).forEach(([selector, value]) => setText(selector, value));
    if (valuesSelector && valuesVisible !== null) {
      const valuesElement = document.querySelector(valuesSelector);
      if (valuesElement) valuesElement.hidden = !valuesVisible;
    }
    if (directionSelector && direction !== null) setText(directionSelector, direction);
  }

  function gaugeCard({meter, label, showSpeedometer, scale, translations}) {
    return `<article class="gauge-card${showSpeedometer ? '' : ' no-speedometer'}" draggable="true" data-dashboard-key="${meter.key}" style="--accent:${meter.colour}">
      <div class="gauge-actions">
        <button class="drag-handle" type="button" draggable="false" title="${translations.drag}" aria-label="${translations.drag}">⠿</button>
        <button class="remove-value" type="button" draggable="false" data-remove-dashboard="${meter.key}" title="${translations.remove}" aria-label="${translations.remove}">×</button>
      </div>
      <div class="gauge-heading">
        <div class="gauge-title">${label}</div>
        <span class="gauge-number">R${meter.register}</span>
      </div>
      ${showSpeedometer ? `<svg viewBox="0 0 240 145" role="img" aria-label="${label}">
        <path class="track" d="M20 120 A100 100 0 0 1 220 120"/>
        <path class="progress" d="M20 120 A100 100 0 0 1 220 120"/>
        ${scale}
        <line class="needle" x1="120" y1="120" x2="120" y2="33"/>
        <circle class="hub" cx="120" cy="120" r="7"/>
      </svg>` : ''}
      <div class="reading"><span class="value">—</span><span class="unit">${meter.unit}</span></div>
      ${meter.interpretation ? `<div class="gauge-interpretation">${meter.interpretation}</div>` : ''}
      <div class="source">${meter.detail}</div>
    </article>`;
  }

  return Object.freeze({energyCard, gaugeCard});
})();
