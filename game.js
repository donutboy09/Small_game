(() => {
  "use strict";

  const COLS = 20;
  const ROWS = 20;
  const LOGICAL = 480;
  const CELL = LOGICAL / COLS;

  const BASE_STEP = 140;
  const MIN_STEP = 66;
  const STEP_GAIN = 2.2;
  const COMBO_WINDOW = 2600;
  const MAX_COMBO = 5;
  const GOLDEN_LIFE = 6500;

  const canvas = document.getElementById("game");
  const ctx = canvas.getContext("2d");
  const scoreEl = document.getElementById("score");
  const bestEl = document.getElementById("best");
  const comboEl = document.getElementById("combo");
  const overlay = document.getElementById("overlay");
  const overlayText = document.getElementById("overlay-text");
  const startBtn = document.getElementById("start-btn");
  const touchPad = document.getElementById("touch-pad");

  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = LOGICAL * dpr;
  canvas.height = LOGICAL * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const BEST_KEY = "neon-snake-best";

  let state = "ready";
  let snake = [];
  let prevSnake = [];
  let direction = { x: 1, y: 0 };
  let pendingDirs = [];
  let accumulator = 0;
  let stepInterval = BASE_STEP;
  let score = 0;
  let combo = 1;
  let comboTimer = 0;
  let food = null;
  let golden = null;
  let goldenTimer = 9000;
  let particles = [];
  let shake = 0;
  let lastTime = performance.now();
  let best = Number(localStorage.getItem(BEST_KEY) || 0);
  let muted = false;
  let audioCtx = null;

  bestEl.textContent = best;

  function clamp(v, a, b) {
    return Math.max(a, Math.min(b, v));
  }

  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  function ensureAudio() {
    if (muted) return;
    if (!audioCtx) {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      audioCtx = new Ctx();
    }
    if (audioCtx.state === "suspended") audioCtx.resume();
  }

  function beep(freq, dur = 0.08, type = "square", vol = 0.045) {
    if (muted || !audioCtx) return;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    const t = audioCtx.currentTime;
    gain.gain.setValueAtTime(vol, t);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start(t);
    osc.stop(t + dur + 0.02);
  }

  function freeCells() {
    const occupied = new Set();
    snake.forEach((s) => occupied.add(s.x + "," + s.y));
    if (food) occupied.add(food.x + "," + food.y);
    if (golden) occupied.add(golden.x + "," + golden.y);
    const cells = [];
    for (let y = 0; y < ROWS; y++) {
      for (let x = 0; x < COLS; x++) {
        if (!occupied.has(x + "," + y)) cells.push({ x, y });
      }
    }
    return cells;
  }

  function spawnFood() {
    const cells = freeCells();
    if (!cells.length) return null;
    const c = cells[(Math.random() * cells.length) | 0];
    return { x: c.x, y: c.y, born: performance.now() };
  }

  function spawnGolden() {
    const cells = freeCells();
    if (!cells.length) return;
    const c = cells[(Math.random() * cells.length) | 0];
    golden = { x: c.x, y: c.y, life: GOLDEN_LIFE, max: GOLDEN_LIFE };
  }

  function resetGame() {
    snake = [
      { x: 8, y: 10 },
      { x: 7, y: 10 },
      { x: 6, y: 10 },
    ];
    prevSnake = snake.map((s) => ({ ...s }));
    direction = { x: 1, y: 0 };
    pendingDirs = [];
    accumulator = 0;
    stepInterval = BASE_STEP;
    score = 0;
    combo = 1;
    comboTimer = 0;
    particles = [];
    shake = 0;
    golden = null;
    goldenTimer = 8000 + Math.random() * 6000;
    food = spawnFood();
    updateHud();
  }

  function updateHud() {
    scoreEl.textContent = score;
    bestEl.textContent = best;
    comboEl.textContent = "x" + combo;
    comboEl.style.color = combo > 1 ? "#ffd166" : "#8ea2c6";
  }

  function showOverlay(title, text, btnLabel) {
    overlay.querySelector(".title").textContent = title;
    overlayText.textContent = text;
    startBtn.textContent = btnLabel;
    overlay.classList.remove("hidden");
  }

  function hideOverlay() {
    overlay.classList.add("hidden");
  }

  function startGame() {
    ensureAudio();
    resetGame();
    state = "running";
    lastTime = performance.now();
    hideOverlay();
  }

  function gameOver() {
    state = "over";
    if (score > best) {
      best = score;
      localStorage.setItem(BEST_KEY, String(best));
    }
    updateHud();
    shake = 14;
    beep(160, 0.3, "sawtooth", 0.07);
    setTimeout(() => beep(90, 0.4, "sawtooth", 0.06), 120);
    showOverlay("游戏结束", `本局得分 ${score} · 最高分 ${best}`, "再来一局");
  }

  function togglePause() {
    if (state === "running") {
      state = "paused";
      showOverlay("已暂停", "喘口气，随时继续", "继续游戏");
    } else if (state === "paused") {
      state = "running";
      lastTime = performance.now();
      hideOverlay();
    }
  }

  function setDirection(x, y) {
    const last = pendingDirs.length ? pendingDirs[pendingDirs.length - 1] : direction;
    if (last.x === -x && last.y === -y) return;
    if (last.x === x && last.y === y) return;
    if (pendingDirs.length < 2) pendingDirs.push({ x, y });
  }

  function burst(gx, gy, color, count) {
    const cx = (gx + 0.5) * CELL;
    const cy = (gy + 0.5) * CELL;
    for (let i = 0; i < count; i++) {
      const a = Math.random() * Math.PI * 2;
      const sp = 40 + Math.random() * 190;
      particles.push({
        x: cx,
        y: cy,
        vx: Math.cos(a) * sp,
        vy: Math.sin(a) * sp,
        life: 420 + Math.random() * 320,
        max: 740,
        size: 1.6 + Math.random() * 3.2,
        color,
      });
    }
  }

  function step() {
    if (pendingDirs.length) direction = pendingDirs.shift();

    prevSnake = snake.map((s) => ({ ...s }));

    const head = snake[0];
    const nx = head.x + direction.x;
    const ny = head.y + direction.y;

    if (nx < 0 || ny < 0 || nx >= COLS || ny >= ROWS) {
      gameOver();
      return;
    }

    const willGrow = (food && food.x === nx && food.y === ny) ||
      (golden && golden.x === nx && golden.y === ny);

    const body = willGrow ? snake : snake.slice(0, snake.length - 1);
    for (let i = 0; i < body.length; i++) {
      if (body[i].x === nx && body[i].y === ny) {
        gameOver();
        return;
      }
    }

    snake.unshift({ x: nx, y: ny });

    if (food && food.x === nx && food.y === ny) {
      score += 10 * combo;
      combo = Math.min(combo + 1, MAX_COMBO);
      comboTimer = COMBO_WINDOW;
      stepInterval = Math.max(MIN_STEP, stepInterval - STEP_GAIN);
      burst(nx, ny, "255,61,129", 16);
      shake = Math.min(shake + 5, 12);
      beep(520 + combo * 60, 0.09, "square", 0.05);
      food = spawnFood();
      if (!golden && Math.random() < 0.22) spawnGolden();
      updateHud();
    } else if (golden && golden.x === nx && golden.y === ny) {
      score += 50 * combo;
      combo = Math.min(combo + 1, MAX_COMBO);
      comboTimer = COMBO_WINDOW;
      burst(nx, ny, "255,209,102", 26);
      shake = Math.min(shake + 9, 16);
      beep(880, 0.12, "triangle", 0.06);
      setTimeout(() => beep(1180, 0.14, "triangle", 0.05), 90);
      golden = null;
      goldenTimer = 8000 + Math.random() * 7000;
      updateHud();
    } else {
      snake.pop();
    }
  }

  function update(dt) {
    if (comboTimer > 0) {
      comboTimer -= dt;
      if (comboTimer <= 0 && combo !== 1) {
        combo = 1;
        updateHud();
      }
    }

    if (golden) {
      golden.life -= dt;
      if (golden.life <= 0) golden = null;
    } else {
      goldenTimer -= dt;
      if (goldenTimer <= 0) spawnGolden();
    }

    accumulator += dt;
    let guard = 0;
    while (accumulator >= stepInterval && state === "running" && guard++ < 5) {
      accumulator -= stepInterval;
      step();
    }
    if (state !== "running") accumulator = 0;

    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.life -= dt;
      if (p.life <= 0) {
        particles.splice(i, 1);
        continue;
      }
      p.x += (p.vx * dt) / 1000;
      p.y += (p.vy * dt) / 1000;
      p.vx *= 0.96;
      p.vy *= 0.96;
    }

    if (shake > 0) shake = Math.max(0, shake - dt * 0.05);
  }

  function roundRect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function drawBackground(now) {
    ctx.fillStyle = "#0e1526";
    ctx.fillRect(0, 0, LOGICAL, LOGICAL);

    ctx.save();
    ctx.strokeStyle = "rgba(255,255,255,0.035)";
    ctx.lineWidth = 1;
    for (let i = 1; i < COLS; i++) {
      ctx.beginPath();
      ctx.moveTo(i * CELL, 0);
      ctx.lineTo(i * CELL, LOGICAL);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, i * CELL);
      ctx.lineTo(LOGICAL, i * CELL);
      ctx.stroke();
    }
    ctx.restore();

    const g = ctx.createRadialGradient(LOGICAL / 2, LOGICAL / 2, 40, LOGICAL / 2, LOGICAL / 2, LOGICAL * 0.75);
    g.addColorStop(0, "rgba(123,92,255,0.05)");
    g.addColorStop(1, "rgba(0,0,0,0.25)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, LOGICAL, LOGICAL);
  }

  function drawFood(now) {
    if (food) {
      const cx = (food.x + 0.5) * CELL;
      const cy = (food.y + 0.5) * CELL;
      const pulse = 1 + Math.sin(now / 180) * 0.12;
      const r = CELL * 0.3 * pulse;

      ctx.save();
      ctx.shadowColor = "rgba(255,61,129,0.9)";
      ctx.shadowBlur = 22;
      const grad = ctx.createRadialGradient(cx - r * 0.3, cy - r * 0.3, 1, cx, cy, r);
      grad.addColorStop(0, "#ffd0e2");
      grad.addColorStop(0.5, "#ff3d81");
      grad.addColorStop(1, "#c2185b");
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      ctx.strokeStyle = "rgba(255,255,255,0.55)";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(cx, cy, r + 4 + Math.sin(now / 300) * 2, 0, Math.PI * 2);
      ctx.stroke();
    }

    if (golden) {
      const cx = (golden.x + 0.5) * CELL;
      const cy = (golden.y + 0.5) * CELL;
      const pulse = 1 + Math.sin(now / 120) * 0.15;
      const r = CELL * 0.34 * pulse;
      const t = golden.life / golden.max;

      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(now / 500);
      ctx.shadowColor = "rgba(255,209,102,0.95)";
      ctx.shadowBlur = 26;
      const grad = ctx.createRadialGradient(0, 0, 1, 0, 0, r);
      grad.addColorStop(0, "#fff6d6");
      grad.addColorStop(0.6, "#ffd166");
      grad.addColorStop(1, "#f4a300");
      ctx.fillStyle = grad;
      ctx.beginPath();
      for (let i = 0; i < 8; i++) {
        const ang = (i / 8) * Math.PI * 2;
        const rad = i % 2 === 0 ? r : r * 0.55;
        const px = Math.cos(ang) * rad;
        const py = Math.sin(ang) * rad;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.fill();
      ctx.restore();

      ctx.strokeStyle = "rgba(255,209,102,0.85)";
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      ctx.arc(cx, cy, CELL * 0.46, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * t);
      ctx.stroke();
    }
  }

  function snakePoints(alpha) {
    const pts = [];
    for (let i = 0; i < snake.length; i++) {
      const cur = snake[i];
      const prev = prevSnake[i] || prevSnake[prevSnake.length - 1] || cur;
      pts.push({
        x: (lerp(prev.x, cur.x, alpha) + 0.5) * CELL,
        y: (lerp(prev.y, cur.y, alpha) + 0.5) * CELL,
      });
    }
    return pts;
  }

  function drawSnake(alpha) {
    const pts = snakePoints(alpha);
    const n = pts.length;
    if (!n) return;

    ctx.save();
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    for (let i = n - 1; i >= 1; i--) {
      const t = i / Math.max(n - 1, 1);
      const w = CELL * (0.82 - 0.36 * t);
      const hue = lerp(168, 262, t);
      ctx.strokeStyle = `hsl(${hue}, 92%, ${lerp(60, 52, t)}%)`;
      ctx.shadowColor = `hsla(${hue}, 95%, 60%, 0.85)`;
      ctx.shadowBlur = 14;
      ctx.lineWidth = w;
      ctx.beginPath();
      ctx.moveTo(pts[i].x, pts[i].y);
      ctx.lineTo(pts[i - 1].x, pts[i - 1].y);
      ctx.stroke();
    }

    const head = pts[0];
    ctx.shadowColor = "rgba(53,240,200,0.95)";
    ctx.shadowBlur = 20;
    ctx.fillStyle = "#9dfff0";
    ctx.beginPath();
    ctx.arc(head.x, head.y, CELL * 0.44, 0, Math.PI * 2);
    ctx.fill();

    const ang = Math.atan2(direction.y, direction.x);
    const eyeFwd = CELL * 0.16;
    const eyeSide = CELL * 0.18;
    const perp = ang + Math.PI / 2;
    const ex = head.x + Math.cos(ang) * eyeFwd;
    const ey = head.y + Math.sin(ang) * eyeFwd;

    ctx.shadowBlur = 0;
    ctx.fillStyle = "#06251f";
    for (const s of [-1, 1]) {
      ctx.beginPath();
      ctx.arc(ex + Math.cos(perp) * eyeSide * s, ey + Math.sin(perp) * eyeSide * s, CELL * 0.09, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  function drawParticles() {
    ctx.save();
    for (const p of particles) {
      const a = clamp(p.life / p.max, 0, 1);
      ctx.fillStyle = `rgba(${p.color},${a})`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size * a, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  function render(now) {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, LOGICAL, LOGICAL);

    ctx.save();
    if (shake > 0.3) {
      ctx.translate((Math.random() - 0.5) * shake, (Math.random() - 0.5) * shake);
    }

    drawBackground(now);
    drawFood(now);

    const alpha = state === "running" ? clamp(accumulator / stepInterval, 0, 1) : 1;
    drawSnake(alpha);
    drawParticles();

    ctx.restore();
  }

  function loop(now) {
    const dt = Math.min(now - lastTime, 60);
    lastTime = now;
    if (state === "running") update(dt);
    else if (shake > 0) shake = Math.max(0, shake - dt * 0.05);
    render(now);
    requestAnimationFrame(loop);
  }

  const keyMap = {
    ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0],
    w: [0, -1], s: [0, 1], a: [-1, 0], d: [1, 0],
    W: [0, -1], S: [0, 1], A: [-1, 0], D: [1, 0],
  };

  window.addEventListener("keydown", (e) => {
    if (e.key === " " || e.key === "Spacebar") {
      e.preventDefault();
      if (state === "ready" || state === "over") startGame();
      else togglePause();
      return;
    }
    if (e.key === "r" || e.key === "R") {
      startGame();
      return;
    }
    if (e.key === "m" || e.key === "M") {
      muted = !muted;
      if (!muted) ensureAudio();
      return;
    }
    if (state !== "running") return;
    const dir = keyMap[e.key];
    if (dir) {
      e.preventDefault();
      setDirection(dir[0], dir[1]);
    }
  });

  startBtn.addEventListener("click", () => {
    if (state === "paused") togglePause();
    else startGame();
  });

  touchPad.addEventListener("pointerdown", (e) => {
    const btn = e.target.closest("[data-dir]");
    if (!btn || state !== "running") return;
    const map = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
    const d = map[btn.dataset.dir];
    if (d) setDirection(d[0], d[1]);
  });

  let touchStart = null;
  canvas.addEventListener("pointerdown", (e) => {
    touchStart = { x: e.clientX, y: e.clientY };
  });
  canvas.addEventListener("pointerup", (e) => {
    if (!touchStart || state !== "running") {
      touchStart = null;
      return;
    }
    const dx = e.clientX - touchStart.x;
    const dy = e.clientY - touchStart.y;
    touchStart = null;
    if (Math.hypot(dx, dy) < 22) return;
    if (Math.abs(dx) > Math.abs(dy)) setDirection(dx > 0 ? 1 : -1, 0);
    else setDirection(0, dy > 0 ? 1 : -1);
  });

  document.addEventListener("visibilitychange", () => {
    if (document.hidden && state === "running") togglePause();
  });

  resetGame();
  state = "ready";
  showOverlay("霓虹贪吃蛇", "方向键 / WASD 控制 · 连击得分翻倍 · 追金色星标拿大分", "开始游戏");
  requestAnimationFrame(loop);
})();
