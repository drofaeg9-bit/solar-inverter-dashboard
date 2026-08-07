    let inverterFanAnimation = null;
    let inverterFanAnimationRotor = null;
    const INVERTER_FAN_MAX_ROTATION_MS = 225;
    function updateInverterFanAnimation(fanRow, normalizedSpeed, forceMotion = false) {
      const rotor = fanRow?.querySelector('.energy-inverter-fan-rotor');
      const shouldRotate = normalizedSpeed > 0
        && (forceMotion || !window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
      fanRow?.classList.toggle('active', normalizedSpeed > 0);
      if (!rotor) return;

      if (typeof rotor.animate !== 'function') {
        fanRow.classList.add('css-animation-fallback');
        if (normalizedSpeed > 0) {
          rotor.style.animationDuration = `${(22.5 / normalizedSpeed).toFixed(3)}s`;
        }
        rotor.style.animationPlayState = shouldRotate ? 'running' : 'paused';
        return;
      }
      fanRow.classList.remove('css-animation-fallback');
      if (!inverterFanAnimation || inverterFanAnimationRotor !== rotor) {
        inverterFanAnimation?.cancel();
        inverterFanAnimationRotor = rotor;
        inverterFanAnimation = rotor.animate(
          [{transform: 'rotate(0deg)'}, {transform: 'rotate(360deg)'}],
          {duration: INVERTER_FAN_MAX_ROTATION_MS, iterations: Infinity}
        );
        inverterFanAnimation.pause();
      }
      if (!shouldRotate) {
        inverterFanAnimation.pause();
        return;
      }

      const playbackRate = normalizedSpeed / 100;
      if (inverterFanAnimation.playState === 'paused') {
        inverterFanAnimation.playbackRate = playbackRate;
        inverterFanAnimation.play();
      } else if (typeof inverterFanAnimation.updatePlaybackRate === 'function') {
        inverterFanAnimation.updatePlaybackRate(playbackRate);
      } else {
        inverterFanAnimation.playbackRate = playbackRate;
      }
    }

    function formatSolarEnergy(kilowattHours) {
      if (kilowattHours === null || kilowattHours === undefined || kilowattHours === '') return t('noData');
      const value = Number(kilowattHours);
      if (!Number.isFinite(value)) return t('noData');
      const locale = currentLanguage === 'uk' ? 'uk-UA' : currentLanguage === 'ru' ? 'ru-RU' : 'en-GB';
      if (value < 1) return `${Math.round(value * 1000).toLocaleString(locale)} Wh`;
      if (value < 1000) return `${value.toLocaleString(locale, {maximumFractionDigits: 2})} kWh`;
      return `${(value / 1000).toLocaleString(locale, {maximumFractionDigits: 2})} MWh`;
    }
    function renderSolarEnergy(summary = {}) {
      const values = {
        '#solar-energy-today': summary.today_kwh,
        '#solar-energy-week': summary.week_kwh,
        '#solar-energy-month': summary.month_kwh,
        '#solar-energy-year': summary.year_kwh
      };
      Object.entries(values).forEach(([selector, value]) => {
        const element = document.querySelector(selector);
        if (element) element.textContent = formatSolarEnergy(value);
      });
      const error = document.querySelector('#solar-energy-error');
      if (error) {
        error.textContent = summary.error ? localizeDataText(summary.error) : '';
        error.hidden = !summary.error;
      }
    }
    function renderEnergyFlow(data, registers = data.registers || []) {
      const byNumber = new Map(registers.map(register => [register.register, register]));
      const firstRegister = numbers => numbers
        .map(number => byNumber.get(number))
        .find(register => register?.available);
      const numberValue = numbers => {
        const register = firstRegister(numbers);
        return register ? numericValue(register.display) : null;
      };
      const summedValue = numbers => {
        const values = numbers
          .map(number => byNumber.get(number))
          .filter(register => register?.available)
          .map(register => numericValue(register.display))
          .filter(Number.isFinite);
        return values.length ? values.reduce((sum, value) => sum + value, 0) : null;
      };
      const registerText = (sources, fallbackNumbers = []) => {
        const actualNumbers = sources
          .flat()
          .map(source => typeof source === 'number' ? source : source?.register)
          .filter(Number.isFinite);
        const numbers = actualNumbers.length ? actualNumbers : fallbackNumbers;
        return [...new Set(numbers)].map(number => `R${number}`).join(' · ') || '—';
      };
      const reading = (value, unit, digits = 0) =>
        Number.isFinite(value) ? `${Number(value.toFixed(digits))} ${unit}` : t('noData');
      const modeDetails = (source, modes) => {
        const raw = Number(source?.raw);
        if (!source?.available || !Number.isFinite(raw) || raw === 65535) {
          return {label: '—', description: ''};
        }
        return modes[raw] || {label: `#${raw}`, description: ''};
      };
      const setText = (selector, value) => {
        const element = document.querySelector(selector);
        if (element && element.textContent !== value) element.textContent = value;
      };
      const setModeText = (selector, definitionSelector, mode) => {
        const fullLabel = String(mode.label ?? '\u2014');
        const displayLabel = Array.from(fullLabel).slice(0, 3).join('');
        const description = mode.description ? t(mode.description) : '';
        setText(definitionSelector, description);
        const element = document.querySelector(selector);
        if (element) {
          if (mode.icon) {
            element.textContent = '';
            element.dataset.sourceIcon = mode.icon;
            element.classList.add('energy-source-icon');
          } else {
            delete element.dataset.sourceIcon;
            element.classList.remove('energy-source-icon');
            if (element.textContent !== displayLabel) element.textContent = displayLabel;
          }
          element.setAttribute('aria-label', fullLabel);
          element.title = [fullLabel, description].filter(Boolean).join(' \u2014 ');
        }
      };
      const setFlow = (selector, enabled, reverse, watts) => {
        const connector = document.querySelector(selector);
        if (!connector) return;
        const now = performance.now();
        const previous = flowAnimationStates.get(selector) || {
          active: false,
          reverse: false,
          lastConfirmedAt: 0
        };
        const confirmedActive = Boolean(enabled);
        const selectedRate = Number(document.querySelector('#modbus-poll-rate')?.value) ?? 0;
        const holdMilliseconds = Math.max(750, (requestIntervals[selectedRate] ?? 2000) * 1.25);
        const temporarilyMissing = !confirmedActive && !Number.isFinite(watts);
        const active = confirmedActive || (
          temporarilyMissing
          && previous.active
          && now - previous.lastConfirmedAt <= holdMilliseconds
        );
        const directionReversed = confirmedActive ? Boolean(reverse) : previous.reverse;

        // Set the speed only when a flow starts. Updating animation-duration on
        // every Modbus cycle restarts the CSS animation and causes visible flicker.
        if (active && !previous.active) {
          const strength = Number.isFinite(watts) ? Math.abs(watts) : 0;
          const duration = Math.max(.55, Math.min(2.2, 2.2 - strength / 5000 * 1.5));
          connector.style.setProperty('--flow-duration', `${duration.toFixed(2)}s`);
        }
        if (connector.classList.contains('active') !== active) {
          connector.classList.toggle('active', active);
        }
        if (connector.classList.contains('reverse') !== directionReversed) {
          connector.classList.toggle('reverse', directionReversed);
        }
        flowAnimationStates.set(selector, {
          active,
          reverse: directionReversed,
          lastConfirmedAt: confirmedActive ? now : previous.lastConfirmedAt
        });
      };

      const gridVoltageSource = firstRegister([89]);
      const gridCurrentSource = firstRegister([82, 434]);
      const gridPowerSource = firstRegister([84, 437, 436]);
      const gridModeSource = firstRegister([325, 67]);
      const pvVoltageSource = firstRegister([151, 154]);
      const pvPowerSource = firstRegister([153, 156]);
      const loadPowerSource = firstRegister([92]);
      const inverterLoadSource = firstRegister([94]);
      const inverterFanSpeedSource = firstRegister([801]);
      const outputVoltageSource = firstRegister([537]);
      const outputCurrentSource = firstRegister([90]);
      const batteryVoltageSource = firstRegister([129, 137, 404, 342]);
      const batteryCurrentSource = firstRegister([130]);
      const batterySocSource = firstRegister([339]);
      const batteryPowerSource = firstRegister([134]);
      const inverterPrioritySource = firstRegister([529, 323, 16643]);
      const inverterAcModeSource = firstRegister([530, 321, 16644]);
      const inverterChargeModeSource = firstRegister([324, 16645]);
      const inverterStateSource = firstRegister([325, 67]);
      const gridVoltage = gridVoltageSource ? numericValue(gridVoltageSource.display) : null;
      const measuredGridCurrent = gridCurrentSource ? numericValue(gridCurrentSource.display) : null;
      const measuredGridPower = gridPowerSource ? numericValue(gridPowerSource.display) : null;
      const pvVoltage = chartDemoRunning && Number.isFinite(demoPvVoltage)
        ? demoPvVoltage
        : numberValue([151, 154]);
      const pvPower = chartDemoRunning && Number.isFinite(demoPvPower)
        ? demoPvPower
        : summedValue([153, 156]);
      const measuredPvCurrent = summedValue([152, 155]);
      const pvCurrent = Number.isFinite(measuredPvCurrent)
        ? Math.abs(measuredPvCurrent)
        : Number.isFinite(pvVoltage) && Math.abs(pvVoltage) > .1 && Number.isFinite(pvPower)
          ? Math.abs(pvPower / pvVoltage)
          : null;
      const loadPowerReading = loadPowerSource ? numericValue(loadPowerSource.display) : null;
      const measuredLoadPower = Number.isFinite(loadPowerReading) ? loadPowerReading : null;
      const inverterLoad = inverterLoadSource ? numericValue(inverterLoadSource.display) : null;
      const inverterFanSpeed = inverterFanSpeedSource ? numericValue(inverterFanSpeedSource.display) : null;
      const outputVoltage = outputVoltageSource ? numericValue(outputVoltageSource.display) : null;
      const outputCurrent = outputCurrentSource ? numericValue(outputCurrentSource.display) : null;
      const batteryVoltage = batteryVoltageSource ? numericValue(batteryVoltageSource.display) : null;
      const batteryCurrentReading = batteryCurrentSource ? numericValue(batteryCurrentSource.display) : null;
      const batteryCurrent = Number.isFinite(batteryCurrentReading) ? batteryCurrentReading : null;
      const batterySoc = batterySocSource ? numericValue(batterySocSource.display) : null;
      const batteryPowerReading = batteryPowerSource ? numericValue(batteryPowerSource.display) : null;
      const calculatedBatteryPower = Number.isFinite(batteryVoltage) && Number.isFinite(batteryCurrent)
        ? batteryVoltage * batteryCurrent
        : null;
      // R130 defines direction: positive charge, negative discharge. R134 supplies
      // the preferred magnitude so both battery values always use the same sign.
      const batteryPower = Number.isFinite(batteryPowerReading)
        ? Number.isFinite(batteryCurrent) && Math.abs(batteryCurrent) >= .3
          ? Math.sign(batteryCurrent) * Math.abs(batteryPowerReading)
          : batteryPowerReading
        : calculatedBatteryPower;
      const batteryActive = (Number.isFinite(batteryCurrent) && Math.abs(batteryCurrent) >= .3)
        || (Number.isFinite(batteryPower) && Math.abs(batteryPower) > 20);
      const batteryCharging = batteryActive && (Number.isFinite(batteryCurrent) && Math.abs(batteryCurrent) >= .3
        ? batteryCurrent > 0
        : batteryPower > 0);
      const batteryDischarging = batteryActive && (Number.isFinite(batteryCurrent) && Math.abs(batteryCurrent) >= .3
        ? batteryCurrent < 0
        : batteryPower < 0);
      const pvActive = Number.isFinite(pvPower) && pvPower > 20;
      const solarDataVisible = pvActive;
      const pvReceiving = false;
      const gridVoltagePresent = Number.isFinite(gridVoltage) && Math.abs(gridVoltage) > .5;
      // R81 is physical mains input. R89 is inverter/load output and remains
      // available while the house is powered from PV or battery.
      const gridAvailable = gridVoltagePresent;
      const loadPower = Number.isFinite(measuredLoadPower) ? Math.max(0, measuredLoadPower) : null;
      const batteryChargePower = batteryCharging && Number.isFinite(batteryPower) ? Math.abs(batteryPower) : 0;
      const batteryDischargePower = batteryDischarging && Number.isFinite(batteryPower) ? Math.abs(batteryPower) : 0;
      const calculatedGridPower = chartDemoRunning
        ? gridAvailable && Number.isFinite(pvPower) && Number.isFinite(loadPower)
          ? loadPower + batteryChargePower - pvPower - batteryDischargePower
          : gridAvailable ? null : 0
        : gridAvailable && batteryCharging && Number.isFinite(loadPower)
          ? loadPower + batteryChargePower
        : gridAvailable && Number.isFinite(measuredGridPower)
          ? Math.abs(measuredGridPower)
          : gridAvailable && Number.isFinite(loadPower)
            ? Math.max(0, loadPower + batteryChargePower - Math.max(0, pvPower || 0))
            : null;
      // Grid is a one-way source. Surplus energy is never represented as grid export.
      const gridPower = Number.isFinite(calculatedGridPower) ? Math.max(0, calculatedGridPower) : null;
      const gridCurrent = gridAvailable && Number.isFinite(measuredGridCurrent)
        ? Math.abs(measuredGridCurrent)
        : Number.isFinite(gridPower) && Number.isFinite(gridVoltage) && Math.abs(gridVoltage) > .1
          ? Math.abs(gridPower / gridVoltage)
          : null;
      const generatorPower = chartDemoRunning && Number.isFinite(demoGeneratorPower)
        ? demoGeneratorPower
        : null;
      const generatorActive = Number.isFinite(generatorPower) && generatorPower > 20;
      const generatorVoltage = generatorActive ? 230 : null;
      const generatorCurrent = generatorActive && Number.isFinite(generatorVoltage)
        ? generatorPower / generatorVoltage
        : null;
      const batteryPowerSources = batteryPowerSource
        ? [batteryPowerSource]
        : [batteryVoltageSource, batteryCurrentSource];
      const gridRegisterSources = gridAvailable && batteryCharging && Number.isFinite(loadPower)
        ? [loadPowerSource, batteryPowerSources, gridVoltageSource, gridModeSource]
        : Number.isFinite(gridPower)
        ? [gridPowerSource, gridCurrentSource, gridVoltageSource, gridModeSource]
        : gridAvailable ? [gridModeSource, gridVoltageSource] : [gridModeSource];

      const homeActive = Number.isFinite(loadPower) && loadPower > 20;
      const gridFlowActive = gridAvailable && Number.isFinite(gridPower) && gridPower > 20;
      const displayedGridVoltage = gridFlowActive && Number.isFinite(gridVoltage)
        ? Math.abs(gridVoltage)
        : 0;
      const displayedHouseVoltage = Number.isFinite(outputVoltage) ? Math.abs(outputVoltage) : null;
      const displayedGridPower = gridAvailable && Number.isFinite(gridPower) ? Math.abs(gridPower) : 0;
      const displayedGridCurrent = gridAvailable && Number.isFinite(gridCurrent) ? Math.abs(gridCurrent) : 0;
      const inverterActive = chartDemoRunning || data.online || pvActive || homeActive || batteryActive;
      const inverterOutputPriority = modeDetails(inverterPrioritySource, {
        0: {label: 'GPB', description: 'modeGpbShort'},
        1: {label: 'PGB', description: 'modePgbShort'},
        2: {label: 'PBG', description: 'modePbgShort'},
        3: {label: 'MKS', description: 'modeMksShort'}
      });
      const inverterState = Number(inverterStateSource?.raw);
      const inverterInputMode = !inverterActive
        ? {label: '—', description: ''}
        : inverterState === 3 && gridAvailable
          ? {label: t('grid'), description: 'modeGridInputShort', icon: 'grid'}
          : inverterState === 4 && pvActive
            ? {label: 'PV', description: 'modeSolarShort', icon: 'pv'}
            : inverterState === 5 && batteryDischarging
              ? {label: t('battery'), description: 'modeBatteryInputShort', icon: 'battery'}
              : inverterState === 6 && generatorActive
                ? {label: t('generator'), description: 'modeGeneratorInputShort', icon: 'generator'}
                : gridAvailable
                  ? {label: t('grid'), description: 'modeGridInputShort', icon: 'grid'}
                  : pvActive
                    ? {label: 'PV', description: 'modeSolarShort', icon: 'pv'}
                    : batteryDischarging
                      ? {label: t('battery'), description: 'modeBatteryInputShort', icon: 'battery'}
                      : {label: '—', description: ''};
      const inverterBatteryMode = modeDetails(inverterChargeModeSource, {
        0: {label: 'PNG', description: 'modePngShort'},
        1: {label: 'OPV', description: 'modeOpvShort'},
        2: {label: 'PVF', description: 'modePvfShort'}
      });

      setText('#energy-flow-status', chartDemoRunning
        ? t(demoFlowCase || 'demoMode')
        : data.online ? t('online') : t('offline'));
      setText('#energy-solar-registers', chartDemoRunning
        ? t('demoMode')
        : registerText([pvVoltageSource, pvPowerSource], [151, 153, 154, 156]));
      setText('#energy-inverter-registers', registerText(
        [inverterLoadSource, inverterFanSpeedSource, inverterPrioritySource, inverterStateSource, inverterChargeModeSource],
        [94, 801, 529, 325, 324]
      ));
      setText('#energy-home-registers', registerText(
        [outputCurrentSource, loadPowerSource, outputVoltageSource],
        [90, 92, 537]
      ));
      setText('#energy-battery-registers', registerText(
        [batteryVoltageSource, batteryCurrentSource, batteryPowerSources, batterySocSource],
        [129, 130, 134, 339]
      ));
      setText('#energy-grid-registers', registerText(gridRegisterSources, [84, 82, 89, 325]));
      setText('#energy-generator-registers', generatorActive ? t('demoMode') : '—');
      DashboardRenderers.energyCard({
        nodeSelector: '#energy-solar-node',
        active: pvActive,
        valuesSelector: '.energy-solar-values',
        valuesVisible: solarDataVisible,
        values: {
          '#energy-solar-voltage': Number.isFinite(pvVoltage) ? reading(Math.abs(pvVoltage), 'V', 1) : '— V',
          '#energy-solar-power': Number.isFinite(pvPower) ? reading(Math.abs(pvPower), 'W') : '— W',
          '#energy-solar-current': Number.isFinite(pvCurrent) ? reading(pvCurrent, 'A', 1) : '— A'
        },
        directionSelector: '#energy-solar-direction',
        direction: !solarDataVisible
          ? t('notConnected')
          : pvActive
            ? pvReceiving ? t('receiving') : t('supplying')
            : t('batteryIdle')
      });
      DashboardRenderers.energyCard({
        nodeSelector: '#energy-generator-node',
        active: generatorActive,
        valuesSelector: '.energy-generator-values',
        valuesVisible: generatorActive,
        values: {
          '#energy-generator-power': generatorActive ? reading(generatorPower, 'W') : '— W',
          '#energy-generator-current': generatorActive ? reading(generatorCurrent, 'A', 1) : '— A',
          '#energy-generator-voltage': generatorActive ? reading(generatorVoltage, 'V', 1) : '— V'
        },
        directionSelector: '#energy-generator-direction',
        direction: generatorActive ? t('supplying') : t('notConnected')
      });
      const normalizedFanSpeed = Number.isFinite(inverterFanSpeed)
        ? Math.max(0, Math.min(100, inverterFanSpeed))
        : 0;
      DashboardRenderers.energyCard({
        nodeSelector: '#energy-inverter-node',
        active: inverterActive,
        values: {
          '#energy-inverter-load': Number.isFinite(inverterLoad) ? reading(inverterLoad, '%', 1) : '— %',
          '#energy-inverter-fan-speed': Number.isFinite(inverterFanSpeed) ? reading(normalizedFanSpeed, '%', 1) : '— %'
        }
      });
      const inverterFanRow = document.querySelector('#energy-inverter-fan-row');
      updateInverterFanAnimation(inverterFanRow, normalizedFanSpeed, chartDemoRunning);
      setModeText('#energy-inverter-ac-mode', '#energy-inverter-ac-definition', inverterOutputPriority);
      setModeText('#energy-inverter-input-mode', '#energy-inverter-input-definition', inverterInputMode);
      setModeText('#energy-inverter-charge-mode', '#energy-inverter-charge-definition', inverterBatteryMode);
      DashboardRenderers.energyCard({
        nodeSelector: '#energy-home-node',
        active: homeActive,
        values: {
          '#energy-home-current': Number.isFinite(outputCurrent) ? reading(Math.abs(outputCurrent), 'A', 2) : '— A',
          '#energy-home-voltage': Number.isFinite(displayedHouseVoltage) ? reading(displayedHouseVoltage, 'V', 1) : '— V',
          '#energy-home-power': Number.isFinite(loadPower) ? reading(loadPower, 'W') : '— W'
        },
        directionSelector: '#energy-home-direction',
        direction: homeActive ? t('consuming') : t('batteryIdle')
      });
      DashboardRenderers.energyCard({
        nodeSelector: '#energy-grid-node',
        active: gridAvailable,
        values: {
          '#energy-grid-power': reading(displayedGridPower, 'W'),
          '#energy-grid-current': reading(displayedGridCurrent, 'A', 2),
          '#energy-grid-voltage': reading(displayedGridVoltage, 'V', 1)
        },
        directionSelector: '#energy-grid-direction',
        direction: gridFlowActive ? t('gridSupplying') : gridAvailable ? t('gridReady') : t('offline')
      });
      DashboardRenderers.energyCard({
        nodeSelector: '#energy-battery-node',
        active: Number.isFinite(batteryVoltage) || Number.isFinite(batterySoc),
        values: {
          '#energy-battery-current': Number.isFinite(batteryCurrent) ? reading(batteryCurrent, 'A', 1) : '— A',
          '#energy-battery-power': Number.isFinite(batteryPower) ? reading(batteryPower, 'W') : '— W',
          '#energy-battery-voltage': Number.isFinite(batteryVoltage) ? reading(batteryVoltage, 'V', 1) : '— V'
        },
        directionSelector: '#energy-battery-direction',
        direction: batteryActive
          ? batteryCharging
            ? t('charging')
            : batteryDischarging ? t('discharging') : t('batteryIdle')
          : t('batteryIdle')
      });
      const batteryIcon = document.querySelector('#energy-battery-icon');
      const batteryLevel = Number.isFinite(batterySoc)
        ? Math.max(0, Math.min(100, batterySoc))
        : 0;
      batteryIcon?.style.setProperty('--battery-level', `${batteryLevel}%`);
      setText('#energy-battery-percent', Number.isFinite(batterySoc) ? `${Math.round(batteryLevel)}%` : '—');
      batteryIcon?.setAttribute(
        'aria-label',
        Number.isFinite(batterySoc) ? `${t('battery')} ${Math.round(batteryLevel)}%` : `${t('battery')} ${t('noData')}`
      );
      // PV is a one-way source and can only supply the inverter.
      setFlow('#energy-pv-flow', pvActive && inverterActive && !pvReceiving, false, pvPower);
      document.querySelector('#energy-pv-flow')?.classList.toggle('disconnected', !pvActive);
      // Home is deliberately one-way: it can consume energy but never supply it.
      setFlow('#energy-home-flow', inverterActive && homeActive, false, loadPower);
      // Generator is a one-way source: animation always travels toward the inverter.
      setFlow(
        '#energy-generator-flow',
        generatorActive && inverterActive,
        true,
        generatorActive ? generatorPower : 0
      );
      document.querySelector('#energy-generator-flow')?.classList.toggle('disconnected', !generatorActive);
      // Grid is a one-way source: animation always travels upward toward the inverter.
      setFlow(
        '#energy-grid-flow',
        gridFlowActive && inverterActive,
        true,
        gridFlowActive ? gridPower : 0
      );
      // Battery and inverter exchange energy in both directions.
      setFlow('#energy-battery-flow', batteryActive && inverterActive, batteryCharging, batteryPower);

      const status = document.querySelector('#energy-flow-status');
      status?.classList.toggle('active', inverterActive);
    }
