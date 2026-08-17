    function dashboardDefinitionData(data) {
      if (!chartDemoRunning || !demoRegisterRows?.length) return data;

      const demoMeters = new Map((data.meters || []).map(meter => [Number(meter.register), {...meter}]));
      demoRegisterRows.forEach(reading => {
        const register = Number(reading.register);
        const value = registerNumericValue(reading);
        const existingMeter = demoMeters.get(register);
        if (existingMeter) {
          existingMeter.value = Number.isFinite(value) ? value : 0;
          existingMeter.available = Number.isFinite(value);
          existingMeter.source = `R${register}`;
          existingMeter.source_source = `R${register}`;
          return;
        }
        demoMeters.set(register, {
          register,
          label: reading.name,
          label_source: reading.name_source || reading.name,
          minimum: null,
          maximum: null,
          unit: reading.unit,
          value: Number.isFinite(value) ? value : 0,
          source: `R${register}`,
          source_source: `R${register}`,
          available: Number.isFinite(value),
        });
      });
      return {...data, registers: demoRegisterRows, meters: [...demoMeters.values()]};
    }

    function synchronizeDemoChartDefinitions(scenario) {
      const demoRegistersByNumber = new Map(
        (demoRegisterRows || []).map(register => [register.register, register])
      );
      chartDefinitions.forEach(item => {
        const scenarioValue = scenario.values.get(item.register);
        const matchingRegister = demoRegistersByNumber.get(item.register);
        const requestedValue = Number.isFinite(scenarioValue)
          ? scenarioValue
          : demoFallbackValue(item, scenario.elapsedSeconds);
        const demoReading = matchingRegister
          || demoRegisterReading(item, requestedValue);
        item.value = demoReading.value;
        item.available = true;
        item.source = `R${item.register} · ${t('demoMode')}`;
        if (matchingRegister) {
          item.displayValue = registerVersionDisplay(matchingRegister, demoRegisterRows);
          item.interpretation = registerInterpretation({...matchingRegister, versionDisplay: item.displayValue});
        }
      });
    }

    function seededDemoRandom(seed) {
      let state = seed >>> 0;
      return () => {
        state = (state * 1664525 + 1013904223) >>> 0;
        return state / 4294967296;
      };
    }

    function seedDemoHistory() {
      const pointCounts = {day: 288, week: 336, month: 360, year: 365, lifetime: 365};
      const now = Date.now();
      timelineDefinitions().forEach(item => {
        const itemPeriod = chartPeriodForItem(item);
        if (itemPeriod === 'realtime') return;
        const windowSeconds = getPeriodWindowSeconds(itemPeriod);
        const demoWindowSeconds = Number.isFinite(windowSeconds) ? windowSeconds : 315360000;
        const pointCount = pointCounts[itemPeriod] || 288;
        const random = seededDemoRandom((Number(item.register) || 1) * 2654435761 + pointCount);
        const history = [];
        let previousValue = null;
        for (let index = 0; index < pointCount; index += 1) {
          const ratio = index / (pointCount - 1);
          const scenario = realisticDemoScenario(ratio * 119.999);
          const base = scenario.values.get(item.register);
          const baseline = Number.isFinite(base) ? base : demoFallbackValue(item, ratio * 120);
          const scale = Number(item.scale) || 1;
          const jitter = random() * Math.max(Math.abs(baseline) * .00002, scale * .02);
          let value = baseline + jitter;
          if (/^(?:k?wh)$/i.test(String(item.unit || '')) && previousValue !== null) {
            value = Math.max(value, previousValue + random() * scale * .01);
          }
          if (item.unit === '%') value = Math.max(0, Math.min(100, value));
          value = demoRegisterReading(item, value).value;
          history.push({time: now - (demoWindowSeconds - ratio * demoWindowSeconds) * 1000, value});
          previousValue = value;
        }
        chartHistory.set(item.key, history);
        item.value = history.at(-1)?.value ?? item.value;
      });
    }
