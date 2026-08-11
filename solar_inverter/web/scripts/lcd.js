    function renderLcd(data, registers = data.registers || []) {
      const byNumber = new Map(registers.map(register => [register.register, register]));
      const firstRegister = numbers => numbers
        .map(number => byNumber.get(number))
        .find(register => register?.available);
      const numberValue = numbers => {
        const register = firstRegister(numbers);
        return registerNumericValue(register);
      };
      const registerLabel = (numbers, label) => `R${[].concat(numbers).join(' / R')} · ${label}`;
      const interpretedValue = numbers => [].concat(numbers).map(number => {
        const register = byNumber.get(number);
        if (!register?.available) return null;
        const meaning = registerInterpretation(register);
        return `R${number}: ${meaning || localizeDataText(register.display)}`;
      }).filter(Boolean).join(' · ') || t('noData');
      const versionValue = (majorRegister, minorRegister) => {
        const register = byNumber.get(majorRegister) || byNumber.get(minorRegister);
        return register
          ? registerVersionDisplay(register, registers)
          : t('noData');
      };
      const reading = (value, unit, digits = 1) =>
        Number.isFinite(value) ? `${value.toFixed(digits)} ${unit}`.trim() : t('noData');
      const setText = (selector, value) => {
        const element = document.querySelector(selector);
        if (element) element.textContent = value;
      };
      const setMeasure = (selector, value, digits = 1) => {
        const element = document.querySelector(selector);
        if (!element) return;
        const displayValue = Number.isFinite(value) ? value.toFixed(digits) : '—';
        element.textContent = displayValue;
        element.classList.toggle('lcd-digits-long', displayValue.length >= 6);
        element.classList.toggle('lcd-digits-extra-long', displayValue.length >= 8);
      };
      const sumValues = numbers => {
        const values = numbers.map(number => registerNumericValue(byNumber.get(number))).filter(Number.isFinite);
        return values.length ? values.reduce((total, value) => total + value, 0) : null;
      };

      const gridVoltage = numberValue([81, 433]);
      const gridCurrent = numberValue([82, 434]);
      const measuredGridPower = numberValue([84, 436]);
      const frequency = numberValue([83, 435]);
      const outputCurrent = numberValue([90, 539]);
      const outputVoltage = numberValue([537, 89]);
      const outputFrequency = numberValue([91, 538]);
      const pv1Power = numberValue([153]);
      const pv2Power = numberValue([156]);
      const pvVoltage = numberValue([609]) ?? (Number.isFinite(pv2Power) && (!Number.isFinite(pv1Power) || pv2Power > pv1Power)
        ? numberValue([154, 151]) : numberValue([151, 154]));
      const pvCurrent = sumValues([152, 155]);
      const pvPower = numberValue([161]) ?? sumValues([153, 156]);
      const dailyPvEnergy = numberValue([157]);
      const inverterLoad = numberValue([545, 94]);
      const inverterFanSpeedReading = numberValue([801]);
      const inverterFanSpeed = Number.isFinite(inverterFanSpeedReading)
        ? Math.max(0, Math.min(100, inverterFanSpeedReading))
        : null;
      const gridLowVoltageThreshold = numberValue([16655]);
      const loadPower = numberValue([541, 92, 188]);
      const apparentLoadPower = numberValue([542, 93]);
      const batteryVoltage = numberValue([129, 137, 404, 342]);
      const batteryCurrent = numberValue([130]);
      const measuredBatterySoc = numberValue([133, 139, 339, 407]);
      const batteryPowerReading = numberValue([134]);
      const batteryTemperature = numberValue([140, 406]);
      const inverterTemperature = numberValue([818]);
      const maximumChargeVoltage = numberValue([141, 411, 16651, 376, 377]);
      const currentLimit = numberValue([413]);
      const lowSocThreshold = numberValue([415]);
      const statusRegister = firstRegister([67, 325]);
      const terminalStateSource = firstRegister([68]);
      const flowStateSource = firstRegister([69]);
      const liveMeasurementsFresh = chartDemoRunning || Boolean(data.online);
      const terminalState = liveMeasurementsFresh ? decodeEnergyTerminalState(terminalStateSource) : null;
      const flowState = liveMeasurementsFresh ? decodeEnergyFlowState(flowStateSource) : null;
      const inverterState = liveMeasurementsFresh ? decodeBoundedRegister(statusRegister, 10) : null;
      const flowSuppressed = [0, 1, 7, 8, 10].includes(inverterState);
      const batterySoc = effectiveBatterySoc(measuredBatterySoc, terminalState);
      const statusText = statusRegister
        ? registerInterpretation(statusRegister) || localizeDataText(statusRegister.display)
        : t('noData');
      const calculatedBatteryPower = Number.isFinite(batteryVoltage) && Number.isFinite(batteryCurrent)
        ? batteryVoltage * batteryCurrent
        : null;
      const batteryPower = Number.isFinite(batteryPowerReading)
        ? Number.isFinite(batteryCurrent) && Math.abs(batteryCurrent) >= .3
          ? Math.sign(batteryCurrent) * Math.abs(batteryPowerReading)
          : batteryPowerReading
        : calculatedBatteryPower;
      const batteryDirectionFromCurrent = Number.isFinite(batteryCurrent) && Math.abs(batteryCurrent) >= .3;
      const batteryActiveValue = batteryDirectionFromCurrent
        ? batteryCurrent
        : batteryPower;
      const batteryActivityThreshold = batteryDirectionFromCurrent ? .3 : 20;
      const batteryConnected = terminalState
        ? terminalState.battery !== 0
        : Number.isFinite(batteryVoltage) && batteryVoltage > 20;
      const measuredBatteryCharging = Number.isFinite(batteryActiveValue)
        && batteryActiveValue < -batteryActivityThreshold;
      const measuredBatteryDischarging = Number.isFinite(batteryActiveValue)
        && batteryActiveValue > batteryActivityThreshold;
      const batteryCharging = liveMeasurementsFresh && !flowSuppressed && batteryConnected && (flowState
        ? flowState.rectifierToBattery && !flowState.batteryToInverter
        : terminalState ? terminalState.battery === 3 : measuredBatteryCharging);
      const batteryDischarging = liveMeasurementsFresh && !flowSuppressed && batteryConnected && (flowState
        ? flowState.batteryToInverter
        : terminalState ? terminalState.battery === 2 : measuredBatteryDischarging);
      const batteryState = !batteryConnected
        ? t('notConnected')
        : terminalState?.battery === 1
          ? t('batteryLow')
          : terminalState?.battery === 4
            ? t('batteryFull')
            : batteryCharging
              ? t('charging')
              : batteryDischarging ? t('discharging') : t('batteryIdle');
      const lcdGridVoltagePresent = Number.isFinite(gridVoltage) && Math.abs(gridVoltage) > .5;
      const gridConnected = liveMeasurementsFresh && (terminalState
        ? terminalState.grid !== 0
        : lcdGridVoltagePresent);
      const gridNormal = terminalState ? terminalState.grid === 2 : gridConnected;
      const pvConnected = liveMeasurementsFresh && (terminalState
        ? terminalState.pv1 !== 0 || terminalState.pv2 !== 0
        : Number.isFinite(pvVoltage) && Math.abs(pvVoltage) > .5);
      const pvNormal = terminalState
        ? terminalState.pv1 === 2 || terminalState.pv2 === 2
        : pvConnected;
      const outputConnected = liveMeasurementsFresh && (terminalState ? terminalState.output !== 0 : true);
      const outputCanSupply = terminalState ? terminalState.output === 1 : outputConnected;
      const gridFlowActive = !flowSuppressed && gridConnected && gridNormal && (flowState
        ? flowState.gridToRectifier || flowState.gridToLoad || flowState.rectifierToGrid
        : Number.isFinite(measuredGridPower) && Math.abs(measuredGridPower) > 20);
      const pvFlowActive = !flowSuppressed && pvConnected && pvNormal && (flowState
        ? flowState.pvToRectifier
        : Number.isFinite(pvPower) && pvPower > 20);
      const loadFlowActive = !flowSuppressed && outputConnected && outputCanSupply && (flowState
        ? flowState.gridToLoad || flowState.generatorToLoad || flowState.inverterToMainOutput || flowState.inverterToSecondaryOutput
        : Number.isFinite(loadPower) && loadPower > 20);
      const displayedGridVoltage = gridConnected && Number.isFinite(gridVoltage) ? gridVoltage : 0;
      const displayedGridCurrent = gridConnected && Number.isFinite(gridCurrent) ? gridCurrent : 0;
      const displayedGridFrequency = gridConnected && Number.isFinite(frequency) ? frequency : 0;
      const gridPower = !gridConnected
        ? 0
        : batteryCharging && Number.isFinite(loadPower)
          ? loadPower + Math.abs(batteryPower || 0)
          : measuredGridPower;

      setText('#lcd-mode', chartDemoRunning ? t('demoMode') : data.online ? t('online') : t('offline'));
      setText('#lcd-grid', reading(gridPower, 'W', 0));
      setText('#lcd-grid-voltage', reading(displayedGridVoltage, 'V'));
      setText('#lcd-grid-current', reading(displayedGridCurrent, 'A', 2));
      setText('#lcd-grid-power', reading(gridPower, 'W', 0));
      setText('#lcd-frequency', reading(displayedGridFrequency, 'Hz', 2));
      setText('#lcd-ac-output-current', reading(outputCurrent, 'A', 2));
      setText('#lcd-inverter-load', reading(inverterLoad, '%', 1));
      setText('#lcd-inverter-fan-speed', reading(inverterFanSpeed, '%', 1));
      setText('#lcd-load-power', reading(loadPower, 'W', 0));
      setText('#lcd-apparent-load-power', reading(apparentLoadPower, 'VA', 0));
      setText('#lcd-grid-low-voltage-threshold', reading(gridLowVoltageThreshold, 'V', 0));
      setText('#lcd-battery-voltage', reading(batteryVoltage, 'V'));
      setText('#lcd-battery-current', reading(batteryCurrent, 'A'));
      setText('#lcd-battery-power', reading(batteryPower, 'W', 0));
      setText('#lcd-soc', reading(batterySoc, '%', 0));
      setText('#lcd-temperature', reading(inverterTemperature, '°C'));
      setText('#lcd-charge-voltage', reading(maximumChargeVoltage, 'V'));
      setText('#lcd-current-limit', Number.isFinite(currentLimit)
        ? `${reading(currentLimit, 'A')} · ${r413BmsFormula(currentLimit)}`
        : t('noData'));
      setText('#lcd-low-soc-threshold', reading(lowSocThreshold, '%', 0));
      setText('#lcd-load', reading(loadPower, 'W', 0));
      setText('#lcd-power', reading(apparentLoadPower, 'VA', 0));
      setText('#lcd-battery-state', batteryState);
      setText('#lcd-system-status', statusText);
      setText('#lcd-status-line', `${data.identifier || t('unknownDevice')} · ${t('updated', {time: data.updated_at})}`);
      setMeasure('#lcd-battery-voltage', batteryVoltage);
      setMeasure('#lcd-charge-voltage', maximumChargeVoltage);
      setMeasure('#lcd-battery-current', batteryCurrent);
      setMeasure('#lcd-soc', batterySoc, 0);
      setMeasure('#lcd-grid-voltage', displayedGridVoltage);
      setMeasure('#lcd-frequency', displayedGridFrequency, 2);
      setMeasure('#lcd-ac2-voltage', batteryVoltage);
      setMeasure('#lcd-ac2-frequency', batteryCurrent, 2);
      setMeasure('#lcd-output-voltage', outputVoltage);
      setMeasure('#lcd-output-frequency', outputFrequency, 2);
      setMeasure('#lcd-pv-voltage', pvVoltage);
      setMeasure('#lcd-pv-current', pvCurrent, 2);
      setMeasure('#lcd-pv-power', pvPower, 0);
      setMeasure('#lcd-pv-day-energy', dailyPvEnergy);
      const clampedSoc = Number.isFinite(batterySoc) ? Math.max(0, Math.min(100, batterySoc)) : 0;
      const lcdDisplay = document.querySelector('#lcd-device-display');
      lcdDisplay?.style.setProperty('--lcd-soc', clampedSoc);
      lcdDisplay?.style.setProperty('--lcd-soc-scale', clampedSoc / 100);

      const kilowattReading = (value, unit) =>
        Number.isFinite(value) ? reading(value / 1000, unit, 2) : t('noData');
      const chargerCurrent = sumValues([159, 160]);
      const dischargingCurrent = Number.isFinite(batteryCurrent) && batteryCurrent > 0
        ? Math.abs(batteryCurrent)
        : 0;
      const pages = [
        {
          code: 'LCD', title: t('mainDisplay'),
          label1: registerLabel(81, t('gridVoltage')), value1: reading(gridVoltage, 'V'),
          label2: registerLabel([537, 89], t('acOutputVoltage')), value2: reading(outputVoltage, 'V'), help: t('lcdMainPageHelp')
        },
        {
          code: 'P1', title: t('frequency'),
          label1: registerLabel(83, t('gridFrequency')), value1: reading(frequency, 'Hz', 2),
          label2: registerLabel([538, 91], t('acOutputFrequency')), value2: reading(outputFrequency, 'Hz', 2), help: t('lcdP1Help')
        },
        {
          code: 'P2', title: t('batteryVoltage'),
          label1: registerLabel([129, 137], t('batteryVoltage')), value1: reading(batteryVoltage, 'V'),
          label2: registerLabel([537, 89], t('acOutputVoltage')), value2: reading(outputVoltage, 'V'), help: t('lcdP2Help')
        },
        {
          code: 'P3', title: t('inverterLoad'),
          label1: registerLabel([129, 137], t('batteryVoltage')), value1: reading(batteryVoltage, 'V'),
          label2: registerLabel([545, 94], t('inverterLoad')), value2: reading(inverterLoad, '%', 1), help: t('lcdP3Help')
        },
        {
          code: 'P4', title: t('apparentLoadPower'),
          label1: registerLabel([129, 137], t('batteryVoltage')), value1: reading(batteryVoltage, 'V'),
          label2: registerLabel([542, 93], t('apparentLoadPower')), value2: kilowattReading(numberValue([542, 93]), 'kVA'), help: t('lcdP4Help')
        },
        {
          code: 'P5', title: t('loadPower'),
          label1: registerLabel([129, 137], t('batteryVoltage')), value1: reading(batteryVoltage, 'V'),
          label2: registerLabel([541, 92], t('loadPower')), value2: kilowattReading(numberValue([541, 92]), 'kW'), help: t('lcdP5Help')
        },
        {
          code: 'P6', title: t('pvPower'),
          label1: registerLabel(151, t('pvVoltage')), value1: reading(numberValue([151]), 'V'),
          label2: registerLabel(153, t('pvPower')), value2: kilowattReading(numberValue([153]), 'kW'), help: t('lcdP6Help')
        },
        {
          code: 'P7', title: t('chargerCurrent'),
          label1: registerLabel([159, 160], t('chargerCurrent')), value1: reading(chargerCurrent, 'A', 1),
          label2: registerLabel(130, t('dcDischargingCurrent')), value2: reading(dischargingCurrent, 'A', 1), help: t('lcdP7Help')
        },
        {
          code: 'P8', title: t('dailyPvEnergy'),
          label1: registerLabel(157, t('dailyPvEnergy')), value1: reading(numberValue([157]), 'kWh'),
          label2: '', value2: '', help: t('lcdP8Help')
        },
        {
          code: 'P9', title: t('monthlyPvEnergy'),
          label1: registerLabel(162, t('monthlyPvEnergy')), value1: reading(numberValue([162]), 'kWh'),
          label2: '', value2: '', help: t('lcdP9Help')
        },
        {
          code: 'P10', title: t('yearlyPvEnergy'),
          label1: registerLabel(163, t('yearlyPvEnergy')), value1: reading(numberValue([163]), 'kWh'),
          label2: '', value2: '', help: t('lcdP10Help')
        }
      ];
      const page = pages[lcdPageIndex] || pages[0];
      const manualLabels = {
        LCD: ['INPUT', 'OUTPUT'], P1: ['INPUT', 'OUTPUT'], P2: ['BATT', 'OUTPUT'],
        P3: ['BATT', 'LOAD'], P4: ['BATT', 'LOAD'], P5: ['BATT', 'LOAD'],
        P6: ['PV1', 'PV1 CHARGE'], P7: ['CHARGER', 'DC DISCHG'],
        P8: ['PV ENERGY', 'TODAY'], P9: ['PV ENERGY', 'MONTH'], P10: ['PV ENERGY', 'YEAR']
      };
      const [manualLeftLabel, manualRightLabel] = manualLabels[page.code] || manualLabels.LCD;
      setText('#lcd-manual-left-label', manualLeftLabel);
      setText('#lcd-manual-left-value', page.value1);
      setText('#lcd-manual-right-label', manualRightLabel);
      setText('#lcd-manual-right-value', page.value2 || '—');
      setText('#lcd-page-code', page.code);
      setText('#lcd-page-title', page.title);
      setText('#lcd-page-label-1', page.label1);
      setText('#lcd-page-value-1', page.value1);
      setText('#lcd-page-label-2', page.label2);
      setText('#lcd-page-value-2', page.value2);
      setText('#lcd-page-description', lcdEnterNotice ? t('settingsReadOnly') : page.help);
      document.querySelector('#lcd-page-reading-2').hidden = !page.label2;

      const active = (selector, enabled) =>
        document.querySelector(selector)?.classList.toggle('active', Boolean(enabled));
      active('#lcd-grid-node', gridConnected);
      active('#lcd-grid-arrow', gridFlowActive);
      active('#lcd-inverter-node', liveMeasurementsFresh && !flowSuppressed);
      active('#lcd-load-node', pvFlowActive);
      active('#lcd-load-arrow', loadFlowActive);
      active('#lcd-ac-output-card', outputConnected && Number.isFinite(outputCurrent) && outputCurrent > .05);
      active('#lcd-battery-card', liveMeasurementsFresh && batteryConnected);
      active('#lcd-soc-card', Number.isFinite(batterySoc));
    }
