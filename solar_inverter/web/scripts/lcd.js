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
      const measuredGridPower = numberValue([84, 437, 436]);
      const frequency = numberValue([83, 435]);
      const outputCurrent = numberValue([90, 539]);
      const outputVoltage = numberValue([89, 537]);
      const outputFrequency = numberValue([91, 538]);
      const secondaryOutputVoltage = numberValue([537, 89]);
      const secondaryOutputFrequency = numberValue([538, 91]);
      const pvVoltage = numberValue([151, 154]);
      const pvCurrent = sumValues([152, 155]);
      const pvPower = numberValue([161]) ?? sumValues([153, 156]);
      const dailyPvEnergy = numberValue([157]);
      const inverterLoad = numberValue([94]);
      const inverterFanSpeedReading = numberValue([801]);
      const inverterFanSpeed = Number.isFinite(inverterFanSpeedReading)
        ? Math.max(0, Math.min(100, inverterFanSpeedReading))
        : null;
      const gridLowVoltageThreshold = numberValue([16655]);
      const loadPower = numberValue([92]);
      const apparentLoadPower = numberValue([93]);
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
        && batteryActiveValue > batteryActivityThreshold;
      const measuredBatteryDischarging = Number.isFinite(batteryActiveValue)
        && batteryActiveValue < -batteryActivityThreshold;
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
      setMeasure('#lcd-ac2-voltage', secondaryOutputVoltage);
      setMeasure('#lcd-ac2-frequency', secondaryOutputFrequency, 2);
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

      const pages = [
        {
          code: 'LCD', title: t('mainDisplay'),
          label1: t('batteryVoltage'), value1: reading(batteryVoltage, 'V'),
          label2: t('acOutputCurrent'), value2: reading(outputCurrent, 'A', 2), help: t('lcdMainPageHelp')
        },
        {
          code: 'P1', title: t('dailyPvEnergy'),
          label1: registerLabel(157, t('dailyPvEnergy')), value1: reading(numberValue([157]), 'kWh'),
          label2: '', value2: '', help: t('lcdP1Help')
        },
        {
          code: 'P2', title: t('totalPvEnergy'),
          label1: registerLabel(158, t('totalPvEnergy')), value1: reading(numberValue([158]), 'kWh'),
          label2: '', value2: '', help: t('lcdP2Help')
        },
        {
          code: 'P3', title: t('batteryState'),
          label1: registerLabel(137, t('batteryVoltage')), value1: reading(numberValue([137]), 'V'),
          label2: registerLabel(138, t('batteryCurrent')), value2: reading(numberValue([138]), 'A'), help: t('lcdP3Help')
        },
        {
          code: 'P4', title: t('batteryState'),
          label1: registerLabel(140, t('batteryTemperature')), value1: reading(numberValue([140]), '°C'),
          label2: registerLabel(139, t('batterySoc')), value2: reading(numberValue([139]), '%', 0), help: t('lcdP4Help')
        },
        {
          code: 'P5', title: t('availableCapacity'),
          label1: registerLabel(409, t('availableCapacity')), value1: reading(numberValue([409]), 'Ah', 2),
          label2: registerLabel(408, t('possibleBatteryHealth')), value2: reading(numberValue([408]), '%', 0), help: t('lcdP5Help')
        },
        {
          code: 'P6', title: t('maxChargeVoltage'),
          label1: registerLabel(411, t('maxChargeVoltage')), value1: reading(numberValue([411]), 'V'),
          label2: registerLabel(415, t('lowSocThreshold')), value2: reading(numberValue([415]), '%', 0), help: t('lcdP6Help')
        },
        {
          code: 'P7', title: t('currentLimit'),
          label1: registerLabel(413, t('currentLimit')), value1: Number.isFinite(numberValue([413]))
            ? `${reading(numberValue([413]), 'A')} · ${r413BmsFormula(numberValue([413]))}`
            : t('noData'),
          label2: registerLabel(412, t('maxChargeCurrent')), value2: reading(numberValue([412]), 'A'), help: t('lcdP7Help')
        },
        {
          code: 'P8', title: t('deviceInformation'),
          label1: registerLabel([17, 18], t('protocolVersion')), value1: versionValue(17, 18),
          label2: registerLabel([27, 28], t('deviceConfiguration')), value2: versionValue(27, 28), help: t('lcdP8Help')
        },
        {
          code: 'P9', title: localizeDataText('Загальна потужність PV'),
          label1: registerLabel(161, localizeDataText('Загальна потужність PV')), value1: reading(numberValue([161]), 'W', 0),
          label2: registerLabel(95, localizeDataText('Навантаження мережі, фаза A')), value2: reading(numberValue([95]), 'W', 0), help: t('lcdP9Help')
        },
        {
          code: 'P10', title: 'PV1 / PV2',
          label1: registerLabel(159, localizeDataText('Струм заряджання від PV1')), value1: reading(numberValue([159]), 'A'),
          label2: registerLabel(160, localizeDataText('Струм заряджання від PV2')), value2: reading(numberValue([160]), 'A'), help: t('lcdP10Help')
        },
        {
          code: 'P11', title: 'PV1 / PV2',
          label1: registerLabel(159, localizeDataText('Струм заряджання від PV1')), value1: reading(numberValue([159]), 'A'),
          label2: registerLabel(160, localizeDataText('Струм заряджання від PV2')), value2: reading(numberValue([160]), 'A'), help: t('lcdV131Help')
        },
        {
          code: 'P12', title: localizeDataText('Енергія PV за місяць'),
          label1: registerLabel(162, localizeDataText('Енергія PV за місяць')), value1: reading(numberValue([162]), 'kWh'),
          label2: registerLabel(163, localizeDataText('Енергія PV за рік')), value2: reading(numberValue([163]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P13', title: t('generator'),
          label1: registerLabel(85, localizeDataText('Напруга генератора, фаза A')), value1: reading(numberValue([85]), 'V'),
          label2: registerLabel(88, localizeDataText('Потужність генератора, фаза A')), value2: reading(numberValue([88]), 'W', 0), help: t('lcdV131Help')
        },
        {
          code: 'P14', title: t('generator'),
          label1: registerLabel(86, localizeDataText('Струм генератора, фаза A')), value1: reading(numberValue([86]), 'A', 2),
          label2: registerLabel(87, localizeDataText('Частота генератора, фаза A')), value2: reading(numberValue([87]), 'Hz', 2), help: t('lcdV131Help')
        },
        {
          code: 'P15', title: localizeDataText('Загальна енергія заряджання'),
          label1: registerLabel(164, localizeDataText('Енергія заряджання за день')), value1: reading(numberValue([164]), 'kWh'),
          label2: registerLabel(167, localizeDataText('Загальна енергія заряджання')), value2: reading(numberValue([167]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P16', title: localizeDataText('Загальна енергія розряджання'),
          label1: registerLabel(168, localizeDataText('Енергія розряджання за день')), value1: reading(numberValue([168]), 'kWh'),
          label2: registerLabel(171, localizeDataText('Загальна енергія розряджання')), value2: reading(numberValue([171]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P17', title: localizeDataText('Загальна енергія навантаження'),
          label1: registerLabel(176, localizeDataText('Енергія навантаження за день')), value1: reading(numberValue([176]), 'kWh'),
          label2: registerLabel(179, localizeDataText('Загальна енергія навантаження')), value2: reading(numberValue([179]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P18', title: localizeDataText('Загальна енергія віддачі в мережу'),
          label1: registerLabel(180, localizeDataText('Енергія віддачі в мережу за день')), value1: reading(numberValue([180]), 'kWh'),
          label2: registerLabel(183, localizeDataText('Загальна енергія віддачі в мережу')), value2: reading(numberValue([183]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P19', title: localizeDataText('Загальна енергія споживання з мережі'),
          label1: registerLabel(184, localizeDataText('Енергія споживання з мережі за день')), value1: reading(numberValue([184]), 'kWh'),
          label2: registerLabel(187, localizeDataText('Загальна енергія споживання з мережі')), value2: reading(numberValue([187]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P20', title: localizeDataText('Енергія заряджання за місяць'),
          label1: registerLabel(165, localizeDataText('Енергія заряджання за місяць')), value1: reading(numberValue([165]), 'kWh'),
          label2: registerLabel(166, localizeDataText('Енергія заряджання за рік')), value2: reading(numberValue([166]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P21', title: localizeDataText('Енергія розряджання за місяць'),
          label1: registerLabel(169, localizeDataText('Енергія розряджання за місяць')), value1: reading(numberValue([169]), 'kWh'),
          label2: registerLabel(170, localizeDataText('Енергія розряджання за рік')), value2: reading(numberValue([170]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P22', title: localizeDataText('Енергія навантаження за місяць'),
          label1: registerLabel(177, localizeDataText('Енергія навантаження за місяць')), value1: reading(numberValue([177]), 'kWh'),
          label2: registerLabel(178, localizeDataText('Енергія навантаження за рік')), value2: reading(numberValue([178]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P23', title: localizeDataText('Енергія віддачі в мережу за місяць'),
          label1: registerLabel(181, localizeDataText('Енергія віддачі в мережу за місяць')), value1: reading(numberValue([181]), 'kWh'),
          label2: registerLabel(182, localizeDataText('Енергія віддачі в мережу за рік')), value2: reading(numberValue([182]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P24', title: localizeDataText('Енергія споживання з мережі за місяць'),
          label1: registerLabel(185, localizeDataText('Енергія споживання з мережі за місяць')), value1: reading(numberValue([185]), 'kWh'),
          label2: registerLabel(186, localizeDataText('Енергія споживання з мережі за рік')), value2: reading(numberValue([186]), 'kWh'), help: t('lcdV131Help')
        },
        {
          code: 'P25', title: localizeDataText('Потужність навантаження на виході, фаза A'),
          label1: registerLabel(188, localizeDataText('Потужність навантаження на виході, фаза A')), value1: reading(numberValue([188]), 'W', 0),
          label2: registerLabel(189, localizeDataText('Потужність навантаження на виході, фаза B')), value2: reading(numberValue([189]), 'W', 0), help: t('lcdV131Help')
        },
        {
          code: 'P26', title: localizeDataText('Температура PV2'),
          label1: registerLabel(190, localizeDataText('Потужність навантаження на виході, фаза C')), value1: reading(numberValue([190]), 'W', 0),
          label2: registerLabel(823, localizeDataText('Температура PV2')), value2: reading(numberValue([823]), '°C'), help: t('lcdV131Help')
        }
      ].slice(0, 11);
      const page = pages[lcdPageIndex] || pages[0];
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
