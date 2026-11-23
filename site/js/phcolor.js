// pH -> color, following the familiar universal-indicator scale
// (red = acidic, green = neutral, blue/purple = basic). Used only to color
// liquids and decorations; the numbers always come from the Python model.

const PH_STOPS = [
  [0, "#c81d3a"], [1, "#e0302f"], [2, "#ef5a2a"], [3, "#f5821f"], [4, "#f9a81c"],
  [5, "#f2cc1b"], [6, "#b7cf2f"], [7, "#3fb34f"], [8, "#17a38f"], [9, "#2387cf"],
  [10, "#3560c2"], [11, "#5147b0"], [12, "#6a3a9f"], [13, "#5e3089"], [14, "#4a2775"],
];

function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function phColor(pH, alpha = 1) {
  const p = Math.max(0, Math.min(14, pH));
  let i = 0;
  while (i < PH_STOPS.length - 2 && PH_STOPS[i + 1][0] < p) i++;
  const [p0, c0] = PH_STOPS[i], [p1, c1] = PH_STOPS[i + 1];
  const f = (p - p0) / (p1 - p0);
  const a = hexToRgb(c0), b = hexToRgb(c1);
  const mix = a.map((v, k) => Math.round(v + f * (b[k] - v)));
  return alpha === 1 ? `rgb(${mix.join(",")})` : `rgba(${mix.join(",")},${alpha})`;
}

// SVG <stop> list for a gradient running from pH 0 to pH 14.
function phGradientStops() {
  return PH_STOPS.map(([p, c]) => `<stop offset="${(p / 14).toFixed(3)}" stop-color="${c}"/>`).join("");
}

// Linear interpolation in a sorted x array.
function interp(x, xs, ys) {
  if (x <= xs[0]) return ys[0];
  if (x >= xs[xs.length - 1]) return ys[ys.length - 1];
  let lo = 0, hi = xs.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (xs[m] <= x) lo = m; else hi = m; }
  const f = (x - xs[lo]) / (xs[hi] - xs[lo]);
  return ys[lo] + f * (ys[hi] - ys[lo]);
}
