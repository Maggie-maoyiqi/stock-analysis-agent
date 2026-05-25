function rangeOf(values) {
  const filtered = values.filter((value) => typeof value === "number" && Number.isFinite(value));
  const min = filtered.length ? Math.min(...filtered) : 0;
  const max = filtered.length ? Math.max(...filtered) : 1;
  return { min, max: max === min ? min + 1 : max };
}

function scale(value, min, max, size) {
  return size - ((value - min) / (max - min || 1)) * size;
}

function buildPolyline(values, min, max, width, height) {
  return values
    .map((value, index) => {
      if (typeof value !== "number" || Number.isNaN(value)) return null;
      const x = (index / Math.max(values.length - 1, 1)) * width;
      const y = scale(value, min, max, height);
      return `${x},${y}`;
    })
    .filter(Boolean)
    .join(" ");
}

function LineChart({ chart }) {
  const width = 520;
  const height = 220;
  const values = chart.series.flatMap((serie) => serie.values);
  const { min, max } = rangeOf(values);
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg" role="img" aria-label={chart.title}>
      {chart.series.map((serie) => (
        <polyline
          key={serie.name}
          fill="none"
          stroke={serie.color || "#2563eb"}
          strokeWidth="2.5"
          points={buildPolyline(serie.values, min, max, width, height)}
        />
      ))}
    </svg>
  );
}

function BarChart({ chart }) {
  const width = 520;
  const height = 220;
  const values = chart.series[0]?.values || [];
  const { max } = rangeOf(values);
  const barWidth = width / Math.max(values.length, 1);
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg" role="img" aria-label={chart.title}>
      {values.map((value, index) => {
        const scaledHeight = (value / (max || 1)) * (height - 10);
        const x = index * barWidth + 8;
        const y = height - scaledHeight;
        return (
          <rect
            key={`${chart.id}-${index}`}
            x={x}
            y={y}
            width={Math.max(barWidth - 16, 8)}
            height={scaledHeight}
            rx="6"
            fill={chart.series[0]?.color || "#0f766e"}
          />
        );
      })}
    </svg>
  );
}

function RadarChart({ chart }) {
  const size = 280;
  const center = size / 2;
  const radius = 100;
  const points = chart.values.map((value, index) => {
    const angle = (-Math.PI / 2) + (index / chart.values.length) * Math.PI * 2;
    const scaled = (value / 100) * radius;
    return [center + Math.cos(angle) * scaled, center + Math.sin(angle) * scaled];
  });
  const polygon = points.map(([x, y]) => `${x},${y}`).join(" ");
  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="chart-svg chart-radar" role="img" aria-label={chart.title}>
      {[0.25, 0.5, 0.75, 1].map((ratio) => (
        <circle key={ratio} cx={center} cy={center} r={radius * ratio} fill="none" stroke="rgba(37,99,235,0.15)" />
      ))}
      {chart.indicators.map((indicator, index) => {
        const angle = (-Math.PI / 2) + (index / chart.indicators.length) * Math.PI * 2;
        const x = center + Math.cos(angle) * (radius + 18);
        const y = center + Math.sin(angle) * (radius + 18);
        return (
          <text key={indicator} x={x} y={y} textAnchor="middle" className="chart-label">
            {indicator}
          </text>
        );
      })}
      <polygon points={polygon} fill="rgba(37,99,235,0.25)" stroke="#2563eb" strokeWidth="2" />
    </svg>
  );
}

function CandlestickChart({ chart }) {
  const width = 520;
  const height = 240;
  const values = chart.candles.flatMap((item) => [item.high, item.low]);
  const { min, max } = rangeOf(values);
  const candleWidth = width / Math.max(chart.candles.length, 1);
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg" role="img" aria-label={chart.title}>
      {chart.candles.map((candle, index) => {
        const x = index * candleWidth + candleWidth / 2;
        const highY = scale(candle.high, min, max, height);
        const lowY = scale(candle.low, min, max, height);
        const openY = scale(candle.open, min, max, height);
        const closeY = scale(candle.close, min, max, height);
        const isUp = candle.close >= candle.open;
        return (
          <g key={`${chart.id}-${index}`}>
            <line x1={x} x2={x} y1={highY} y2={lowY} stroke={isUp ? "#0f766e" : "#dc2626"} strokeWidth="1.2" />
            <rect
              x={x - Math.max(candleWidth * 0.25, 1.5)}
              y={Math.min(openY, closeY)}
              width={Math.max(candleWidth * 0.5, 3)}
              height={Math.max(Math.abs(closeY - openY), 1.5)}
              fill={isUp ? "#0f766e" : "#dc2626"}
              opacity="0.8"
            />
          </g>
        );
      })}
      {chart.lines?.map((line) => (
        <polyline
          key={line.name}
          fill="none"
          stroke={line.color}
          strokeWidth="2"
          points={buildPolyline(line.values, min, max, width, height)}
        />
      ))}
    </svg>
  );
}

export default function ChartRenderer({ charts = [] }) {
  if (!charts.length) return null;
  return (
    <div className="chart-grid">
      {charts.map((chart) => (
        <section className="chart-card" key={chart.id}>
          <div className="chart-card-header">
            <h3>{chart.title}</h3>
          </div>
          {chart.type === "line" ? <LineChart chart={chart} /> : null}
          {chart.type === "bar" ? <BarChart chart={chart} /> : null}
          {chart.type === "radar" ? <RadarChart chart={chart} /> : null}
          {chart.type === "candlestick" ? <CandlestickChart chart={chart} /> : null}
        </section>
      ))}
    </div>
  );
}
