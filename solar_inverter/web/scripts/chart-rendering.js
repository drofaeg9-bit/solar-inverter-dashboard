    function drawChart(canvas, item, history, colour, layout, palette) {
      const {width, height, pixelRatio} = layout;
      const bitmapWidth = Math.round(width * pixelRatio);
      const bitmapHeight = Math.round(height * pixelRatio);
      if (canvas.width !== bitmapWidth) canvas.width = bitmapWidth;
      if (canvas.height !== bitmapHeight) canvas.height = bitmapHeight;
      const context = canvas.getContext('2d');
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
      context.clearRect(0, 0, width, height);
      const {mutedColour, gridColour} = palette;

      const compactChart = width < 420;
      const padding = {
        left: compactChart ? 42 : 48,
        right: compactChart ? 8 : 14,
        top: 16,
        bottom: 28
      };
      const plotWidth = width - padding.left - padding.right;
      const plotHeight = height - padding.top - padding.bottom;
      const values = history.map(point => point.value);
      const hasConfiguredRange = Number.isFinite(item.minimum) && Number.isFinite(item.maximum)
        && item.maximum > item.minimum;
      let minimum = hasConfiguredRange ? item.minimum : values.length ? Math.min(...values) : 0;
      let maximum = hasConfiguredRange ? item.maximum : values.length ? Math.max(...values) : 1;
      if (!hasConfiguredRange && minimum === maximum) {
        const margin = Math.abs(minimum) * .08 || 1;
        minimum -= margin;
        maximum += margin;
      } else if (!hasConfiguredRange) {
        const margin = (maximum - minimum) * .1;
        minimum -= margin;
        maximum += margin;
      }

      context.font = '10px system-ui';
      context.fillStyle = mutedColour;
      context.strokeStyle = gridColour;
      context.lineWidth = 1.5;
      for (let line = 0; line <= 4; line += 1) {
        const ratio = line / 4;
        const y = padding.top + plotHeight * ratio;
        context.beginPath();
        context.moveTo(padding.left, y);
        context.lineTo(width - padding.right, y);
        context.stroke();
        const label = maximum - (maximum - minimum) * ratio;
        context.fillText(Number(label.toFixed(2)).toString(), 3, y + 3);
      }

      const endTime = history.length ? history.at(-1).time : Date.now();
      const startTime = endTime - chartWindowMilliseconds;
      const timeTickCount = width < 340 ? 2 : 3;
      for (let tick = 0; tick <= timeTickCount; tick += 1) {
        const ratio = tick / timeTickCount;
        const x = padding.left + plotWidth * ratio;
        context.beginPath();
        context.moveTo(x, padding.top);
        context.lineTo(x, padding.top + plotHeight);
        context.stroke();
        context.fillStyle = mutedColour;
        context.textAlign = tick === 0 ? 'left' : tick === timeTickCount ? 'right' : 'center';
        context.fillText(
          formatChartTime(startTime + (endTime - startTime) * ratio),
          x,
          height - 7
        );
      }

      if (history.length) {
        context.strokeStyle = colour;
        context.lineWidth = 3;
        context.lineJoin = 'round';
        context.lineCap = 'round';
        context.beginPath();
        history.forEach((point, index) => {
          const timeRatio = Math.max(
            0,
            Math.min(1, (point.time - startTime) / chartWindowMilliseconds)
          );
          const x = padding.left + plotWidth * timeRatio;
          const y = padding.top + plotHeight * (maximum - point.value) / (maximum - minimum);
          if (index === 0) context.moveTo(x, y); else context.lineTo(x, y);
        });
        context.stroke();
      }

      const latest = document.querySelector(`#latest-${item.key}`);
      if (latest) latest.textContent = history.length
        ? `${Number(history.at(-1).value.toFixed(2))} ${item.unit}`.trim()
        : t('waiting');
    }
    function drawAllCharts() {
      if (document.querySelector('#charts-view').hidden) return;
      const pixelRatio = window.devicePixelRatio || 1;
      const jobs = [...visibleChartCanvases]
        .map(canvas => ({canvas, layout: chartCanvasLayouts.get(canvas)}))
        .filter(({canvas, layout}) => canvas.isConnected
          && layout && layout.width > 0 && layout.height > 0);
      const themeStyles = window.getComputedStyle(document.documentElement);
      const palette = {
        mutedColour: themeStyles.getPropertyValue('--muted').trim(),
        gridColour: themeStyles.getPropertyValue('--chart-grid-line').trim()
      };
      jobs.forEach(({canvas, layout}) => {
        const key = canvas.dataset.chartKey;
        const item = chartDefinitions.get(key);
        const colourToken = canvas.dataset.chartColour || colours[0];
        const customProperty = /^var\((--[^)]+)\)$/.exec(colourToken)?.[1];
        const chartColour = customProperty
          ? themeStyles.getPropertyValue(customProperty).trim()
          : colourToken;
        if (item) drawChart(
          canvas,
          item,
          chartHistory.get(key) || [],
          chartColour || colours[0],
          {width: Math.max(1, layout.width), height: layout.height || 220, pixelRatio},
          palette
        );
      });
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
