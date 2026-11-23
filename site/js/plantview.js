// Animated plant view: tanks in series, liquid colored by the SIMULATED pH,
// reagent valves opening and closing, probe readings, and a timeline you can
// play or scrub. It only displays simulation results (from api.simulation).

let PV_COUNT = 0;

function createPlantView(container, data, opts = {}) {
  const uid = "pv" + (++PV_COUNT);
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const state = { data: null, i: 0, playing: false, raf: 0, last: 0 };
  const duration = opts.seconds || 14;          // seconds to play the whole run

  function layout(n) {
    const tankW = 150, gap = 92, left = 120;
    const W = left + n * tankW + (n - 1) * gap + 190;
    const xs = Array.from({ length: n }, (_, k) => left + k * (tankW + gap));
    return { W, H: 372, tankW, xs, top: 104, bottom: 262, level: 132, pipeY: 240,
             sparkTop: 296, sparkBottom: 352 };
  }

  function build(d) {
    const n = d.pH.length;
    const L = layout(n);
    const tanks = L.xs.map((x, k) => {
      const cx = x + L.tankW / 2, shaftX = x + L.tankW - 38;
      const valveX = x + 34;
      return `
      <g class="pv-tank">
        <clipPath id="${uid}-clip${k}"><path d="M${x + 3} ${L.top} V${L.bottom - 14} a12 12 0 0 0 12 12 H${x + L.tankW - 15} a12 12 0 0 0 12 -12 V${L.top}Z"/></clipPath>
        <g clip-path="url(#${uid}-clip${k})">
          <rect id="${uid}-liq${k}" x="${x}" y="${L.level}" width="${L.tankW}" height="${L.bottom - L.level}"/>
          <path id="${uid}-wave${k}" class="pv-wave" d="${wave(x - 60, L.level, L.tankW + 120)}"/>
          ${[0, 1, 2, 3].map((b) => `<circle class="pv-bubble" style="animation-delay:${-b * 0.9 - k * 0.4}s" cx="${x + 22 + b * 27}" cy="${L.bottom - 8}" r="${2 + (b % 2)}"/>`).join("")}
        </g>
        <path class="pv-vessel" d="M${x} ${L.top - 8} V${L.bottom - 12} a14 14 0 0 0 14 14 H${x + L.tankW - 14} a14 14 0 0 0 14 -14 V${L.top - 8}"/>
        <line class="pv-shaft" x1="${shaftX}" y1="${L.top - 26}" x2="${shaftX}" y2="${L.bottom - 26}"/>
        <ellipse class="pv-impeller" cx="${shaftX}" cy="${L.bottom - 26}" rx="18" ry="4.5" style="animation-delay:${-k * 0.3}s"/>
        <rect x="${cx - 52}" y="${L.level + 26}" width="84" height="54" rx="10" class="pv-display"/>
        <text id="${uid}-ph${k}" class="pv-ph" x="${cx - 10}" y="${L.level + 62}" text-anchor="middle">7.00</text>
        <text class="pv-phlabel" x="${cx - 10}" y="${L.level + 74}" text-anchor="middle">pH</text>
        <text id="${uid}-sp${k}" class="pv-small pv-strong" x="${cx - 10}" y="${L.bottom + 22}" text-anchor="middle">Stage ${k + 1} · SP 7</text>
        <!-- reagent line, valve and flow -->
        <path class="pv-pipe thin" d="M${valveX} 26 V${L.top - 8}"/>
        <path id="${uid}-flow${k}" class="pv-flow" d="M${valveX} 26 V${L.level}" />
        <path class="pv-valve" d="M${valveX - 10} 52 L${valveX + 10} 66 V52 L${valveX - 10} 66Z"/>
        <rect x="${valveX + 16}" y="48" width="42" height="6" rx="3" class="pv-meter-bg"/>
        <rect id="${uid}-vbar${k}" x="${valveX + 16}" y="48" width="0" height="6" rx="3" class="pv-meter"/>
        <text id="${uid}-vtxt${k}" class="pv-small" x="${valveX + 16}" y="70">valve 0%</text>
        <text class="pv-small" x="${valveX - 4}" y="18">NaOH</text>
        <!-- probe -->
        <path class="pv-signal" d="M${x + L.tankW} ${L.top + 30} H${x + L.tankW + 22}"/>
        <circle class="pv-bubble-i" cx="${x + L.tankW + 36}" cy="${L.top + 30}" r="15"/>
        <text class="pv-tag" x="${x + L.tankW + 36}" y="${L.top + 34}" text-anchor="middle">AT</text>
        <text id="${uid}-meas${k}" class="pv-small" x="${x + L.tankW + 36}" y="${L.top + 62}" text-anchor="middle">7.0</text>
      </g>`;
    }).join("");

    const pipes = L.xs.slice(0, -1).map((x, k) =>
      `<path class="pv-pipe" d="M${x + L.tankW} ${L.pipeY} H${L.xs[k + 1]}"/>
       <path id="${uid}-pflow${k}" class="pv-flow wide" d="M${x + L.tankW} ${L.pipeY} H${L.xs[k + 1]}"/>`).join("");
    const lastX = L.xs[n - 1] + L.tankW;
    const sparkL = 120, sparkR = L.W - 24;

    container.innerHTML = `
      <div class="pv">
        <svg class="pv-svg" style="max-width:${Math.round(L.W * 1.55)}px" viewBox="0 0 ${L.W} ${L.H}" role="img" aria-label="Animated plant: tank pH colored by the simulated value">
          <defs>
            <linearGradient id="${uid}-phgrad" x1="0" y1="${L.sparkBottom}" x2="0" y2="${L.sparkTop}" gradientUnits="userSpaceOnUse">${phGradientStops()}</linearGradient>
          </defs>
          <path class="pv-pipe" d="M8 ${L.pipeY} H${L.xs[0]}"/>
          <path class="pv-flow wide" style="stroke:${phColor(2)}" d="M8 ${L.pipeY} H${L.xs[0]}"/>
          <text class="pv-small pv-strong" x="8" y="${L.pipeY - 30}">Influent</text>
          <text id="${uid}-inph" class="pv-small" x="8" y="${L.pipeY - 16}">HCl</text>
          ${pipes}
          ${tanks}
          <path class="pv-pipe" d="M${lastX} ${L.pipeY} H${L.W - 8}"/>
          <path id="${uid}-eflow" class="pv-flow wide" d="M${lastX} ${L.pipeY} H${L.W - 8}"/>
          <text class="pv-small pv-strong" x="${lastX + 24}" y="${L.pipeY - 46}">Effluent</text>
          <text id="${uid}-eph" class="pv-effph" x="${lastX + 24}" y="${L.pipeY - 18}">pH 7.00</text>
          <g id="${uid}-badge" transform="translate(${lastX + 24}, ${L.pipeY + 16})">
            <rect width="96" height="22" rx="11" class="pv-badge-bg"/>
            <text id="${uid}-badgetxt" x="48" y="15" text-anchor="middle" class="pv-badge-text">in spec</text>
          </g>
          <!-- timeline: final-tank pH, colored by pH, spec band 6-9 -->
          <text class="pv-small" x="8" y="${L.sparkTop + 12}">Final tank</text>
          <text class="pv-small" x="8" y="${L.sparkTop + 26}">pH vs time</text>
          <rect x="${sparkL}" y="${L.sparkTop}" width="${sparkR - sparkL}" height="${L.sparkBottom - L.sparkTop}" rx="6" class="pv-spark-bg"/>
          <rect id="${uid}-band" x="${sparkL}" width="${sparkR - sparkL}" class="pv-spark-band"/>
          <path id="${uid}-spark" fill="none" stroke="url(#${uid}-phgrad)" stroke-width="2.5" stroke-linejoin="round"/>
          <g id="${uid}-dist"></g>
          <line id="${uid}-head" y1="${L.sparkTop - 4}" y2="${L.sparkBottom + 4}" class="pv-head"/>
          <circle id="${uid}-headdot" r="5" class="pv-headdot"/>
          <rect id="${uid}-hit" x="${sparkL}" y="${L.sparkTop - 6}" width="${sparkR - sparkL}" height="${L.sparkBottom - L.sparkTop + 12}" fill="transparent" style="cursor:pointer"/>
        </svg>
        <div class="pv-controls">
          <button type="button" class="pv-play" aria-label="Play">${ICON_PLAY}</button>
          <input type="range" class="pv-scrub" min="0" max="${d.t.length - 1}" value="0" aria-label="Time">
          <span class="pv-time">t = 0.0 min</span>
        </div>
      </div>`;

    const q = (id) => container.querySelector("#" + uid + "-" + id);
    state.L = L; state.n = n; state.sparkL = sparkL; state.sparkR = sparkR;
    state.refs = {
      liq: [...Array(n)].map((_, k) => q("liq" + k)), wave: [...Array(n)].map((_, k) => q("wave" + k)),
      ph: [...Array(n)].map((_, k) => q("ph" + k)), sp: [...Array(n)].map((_, k) => q("sp" + k)),
      flow: [...Array(n)].map((_, k) => q("flow" + k)), vbar: [...Array(n)].map((_, k) => q("vbar" + k)),
      vtxt: [...Array(n)].map((_, k) => q("vtxt" + k)), meas: [...Array(n)].map((_, k) => q("meas" + k)),
      pflow: [...Array(n - 1)].map((_, k) => q("pflow" + k)),
      eflow: q("eflow"), eph: q("eph"), badge: q("badge"), badgetxt: q("badgetxt"),
      spark: q("spark"), band: q("band"), head: q("head"), headdot: q("headdot"), hit: q("hit"), dist: q("dist"),
      inph: q("inph"),
      play: container.querySelector(".pv-play"), scrub: container.querySelector(".pv-scrub"),
      time: container.querySelector(".pv-time"),
    };
    const r = state.refs;
    r.play.addEventListener("click", () => (state.playing ? pause() : play()));
    r.scrub.addEventListener("input", () => { pause(); show(Number(r.scrub.value)); });
    r.hit.addEventListener("click", (ev) => {
      const box = r.hit.getBoundingClientRect();
      const f = (ev.clientX - box.left) / box.width;
      pause(); show(Math.round(f * (state.data.t.length - 1)));
    });
  }

  function wave(x0, y, width) {
    let d = `M${x0} ${y}`;
    for (let x = x0; x < x0 + width; x += 30) d += ` q7.5 -4 15 0 t15 0`;
    return d + ` V${y + 400} H${x0} Z`;
  }

  const sx = (i) => state.sparkL + (state.sparkR - state.sparkL) * i / (state.data.t.length - 1);
  const sy = (pH) => state.L.sparkBottom - (state.L.sparkBottom - state.L.sparkTop) * Math.max(0, Math.min(14, pH)) / 14;

  function setData(d) {
    pause();
    if (!state.data || state.data.pH.length !== d.pH.length) build(d);
    state.data = d;
    const r = state.refs, n = d.pH.length, last = d.pH[n - 1];
    r.scrub.max = d.t.length - 1;
    r.spark.setAttribute("d", last.map((p, i) => `${i ? "L" : "M"}${sx(i).toFixed(1)} ${sy(p).toFixed(1)}`).join(" "));
    r.band.setAttribute("y", sy(9)); r.band.setAttribute("height", sy(6) - sy(9));
    const tEnd = d.t[d.t.length - 1];
    r.dist.innerHTML = (d.disturbances || []).filter((x) => x.t !== null && x.t <= tEnd).map((x) => {
      const X = state.sparkL + (state.sparkR - state.sparkL) * x.t / tEnd;
      return `<line x1="${X}" x2="${X}" y1="${state.L.sparkTop}" y2="${state.L.sparkBottom}" class="pv-dist"/>`;
    }).join("");
    if (r.inph) r.inph.textContent = d.influent ? `pH ${d.influent.toFixed(1)}` : "acidic";
    show(0);
    if (opts.autoplay && !reduceMotion) play();
  }

  function show(i) {
    const d = state.data, r = state.refs;
    state.i = i;
    for (let k = 0; k < state.n; k++) {
      const p = d.pH[k][i];
      const col = phColor(p);
      r.liq[k].setAttribute("fill", col); r.wave[k].setAttribute("fill", col);
      r.ph[k].textContent = p.toFixed(2);
      r.sp[k].textContent = `Stage ${k + 1} · SP ${d.SP[k][i]}`;
      r.meas[k].textContent = d.pH_measured[k][i].toFixed(2);
      const frac = Math.max(0, Math.min(1, d.FR[k][i] / d.FR_max[k]));
      r.vbar[k].setAttribute("width", (42 * frac).toFixed(1));
      r.vbar[k].classList.toggle("sat", frac > 0.995 || frac < 0.005);
      r.vtxt[k].textContent = `valve ${Math.round(100 * frac)}%`;
      r.flow[k].style.opacity = (0.15 + 0.85 * frac).toFixed(2);
      if (k < state.n - 1) r.pflow[k].style.stroke = col;
    }
    const pe = d.pH[state.n - 1][i];
    r.eflow.style.stroke = phColor(pe);
    r.eph.textContent = `pH ${pe.toFixed(2)}`;
    r.eph.setAttribute("fill", phColor(pe));
    const ok = pe >= 6 && pe <= 9;
    r.badge.classList.toggle("bad", !ok);
    r.badgetxt.textContent = ok ? "✓ in spec 6–9" : "✗ out of spec";
    const X = sx(i);
    r.head.setAttribute("x1", X); r.head.setAttribute("x2", X);
    r.headdot.setAttribute("cx", X); r.headdot.setAttribute("cy", sy(pe));
    r.headdot.setAttribute("fill", phColor(pe));
    r.scrub.value = i;
    r.time.textContent = `t = ${d.t[i].toFixed(1)} min`;
  }

  function frame(ts) {
    if (!state.playing) return;
    const len = state.data.t.length;
    state.pos += (Math.max(0, ts - state.last) / 1000) * len / duration;   // samples per second
    state.last = ts;
    if (state.pos >= len) state.pos = 0;                          // loop
    const i = Math.floor(state.pos);
    if (i !== state.i) show(i);
    state.raf = requestAnimationFrame(frame);
  }
  function play() {
    if (!state.data || state.playing) return;
    state.playing = true; state.last = performance.now(); state.pos = state.i;
    state.refs.play.innerHTML = ICON_PAUSE; state.refs.play.setAttribute("aria-label", "Pause");
    state.raf = requestAnimationFrame(frame);
  }
  function pause() {
    state.playing = false; cancelAnimationFrame(state.raf);
    if (state.refs) { state.refs.play.innerHTML = ICON_PLAY; state.refs.play.setAttribute("aria-label", "Play"); }
  }

  if (data) setData(data);
  return { setData, play, pause };
}

const ICON_PLAY = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M7 4.5v15l13-7.5z"/></svg>';
const ICON_PAUSE = '<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4.5" width="4" height="15" rx="1"/><rect x="14" y="4.5" width="4" height="15" rx="1"/></svg>';
