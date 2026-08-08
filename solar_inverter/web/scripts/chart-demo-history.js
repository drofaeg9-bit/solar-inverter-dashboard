    function synchronizeDemoChartDefinitions(scenario) {
      const demoRegistersByNumber = new Map(
        (demoRegisterRows || []).map(register => [register.register, register])
      );
      chartDefinitions.forEach(item => {
        const scenarioValue = scenario.values.get(item.register);
        const matchingRegister = demoRegistersByNumber.get(item.register);
        item.value = Number.isFinite(scenarioValue)
          ? scenarioValue
          : demoFallbackValue(item, scenario.elapsedSeconds);
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

    function seedDemoHistory(period = window.chartPeriod || 'realtime') {
      const windowSeconds = getPeriodWindowSeconds(period);
      if (period === 'realtime') return;
      const pointCounts = {day: 288, week: 336, month: 360, year: 365};
      const pointCount = pointCounts[period] || 288;
      const now = Date.now();
      timelineDefinitions().forEach(item => {
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
          history.push({time: now - (windowSeconds - ratio * windowSeconds) * 1000, value});
          previousValue = value;
        }
        chartHistory.set(item.key, history);
        item.value = history.at(-1)?.value ?? item.value;
      });
    }
