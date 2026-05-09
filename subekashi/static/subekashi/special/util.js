// スペシャルデザインボタンを表示
function add_special_button() {
    var defaultDummybuttonsEle = document.getElementsByClassName("dummybuttons")[0];
    const designedDummybuttonsEle =
    `
    <div class="dummybuttons">
        <a>
            <div class="dummybutton" onclick="special()"><i class="fas fa-magic"></i><p>スペシャルデザイン</p></div>
        </a>
        <a href="./history/">
            <div class="dummybutton"><i class="fas fa-history"></i><p>編集履歴</p></div>
        </a>
    </div>
    `
    defaultDummybuttonsEle.innerHTML = stringToHTML(designedDummybuttonsEle).innerHTML;
}


// 歌詞をドットフォントに変更 
function dot_lyrics() {
    const lyricsEle = document.getElementById('lyrics');
    lyricsEle.style.fontFamily = "'k8x12s', sans-serif, Meiryo";
}


// 雨を降らす
// 雨の初期化
const canvas = document.createElement('canvas');
let ctx;
function initRain() {
    document.body.appendChild(canvas);
    ctx = canvas.getContext('2d');
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    // 初期化
    createRain();
    animateRain();
}

// 設定値（調整可能）
let rainCount = 64; // 雨の本数
let rainAngle = Math.PI / -32; // 雨の角度（ラジアン）
let rainSpeed = 48; // 雨のスピード

// キャンバスサイズの初期化とリサイズ対応
function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}

// 雨粒クラス
class Raindrop {
    constructor() {
        this.reset(true);
    }

    reset(initial = false) {
        const angleOffset = Math.tan(rainAngle);
        const overshoot = canvas.height * angleOffset;
        const marginX = Math.abs(overshoot);

        // xを画面の左外から右外までの範囲にランダム配置
        this.x = Math.random() * (canvas.width + marginX * 2) - marginX;
        this.y = initial ? Math.random() * canvas.height : -Math.random() * canvas.height;
        this.length = 50 + Math.random() * 30;
        this.speedX = rainSpeed * Math.tan(rainAngle);
        this.speedY = rainSpeed;
    }

    update() {
        this.x += this.speedX;
        this.y += this.speedY;

        // 画面外に出たらリセット
        if (this.y > canvas.height || this.x > canvas.width + 100 || this.x < -100) {
            this.reset();
        }
    }

    draw() {
        ctx.beginPath();
        ctx.moveTo(this.x, this.y);
        ctx.lineTo(
            this.x + this.length * Math.sin(rainAngle),
            this.y + this.length * Math.cos(rainAngle)
        );
        ctx.strokeStyle = '#777';
        ctx.lineWidth = 2;
        ctx.stroke();
    }
}

// 雨粒の生成
let raindrops = [];
function createRain() {
    raindrops = [];
    for (let i = 0; i < rainCount; i++) {
        raindrops.push(new Raindrop());
    }
}

// アニメーションループ
function animateRain() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let drop of raindrops) {
        drop.update();
        drop.draw();
    }
    requestAnimationFrame(animateRain);
}

function kyouiku() {
  const lyricsEl = document.getElementById('lyrics');
  lyricsEl.style.display = 'none';

  const existing = document.getElementById('kyouiku-stage');
  if (existing) existing.remove();

  const lines = lyricsEl.innerHTML
    .split(/<br\s*\/?>/i)
    .map(l => l.replace(/<[^>]+>/g, '').trim())
    .filter(l => l);

  // フォントサイズを vw 比率で定義（画面幅の何%か）
  const KEYFRAMES_VW = [
    { s: 0.00, fontVw: 30, opacity: 0 },  // 画面幅の30%
    { s: 0.10, fontVw: 26, opacity: 1 },
    { s: 0.30, fontVw: 15, opacity: 1 },
    { s: 0.50, fontVw: 7, opacity: 1 },
    { s: 0.70, fontVw: 3.5, opacity: 1 },
    { s: 0.85, fontVw: 1.8, opacity: 1 },
    { s: 1.00, fontVw: 0.6, opacity: 0 },
  ];

  const STEP_PER_LINE = 400;  // 200 → 400
  const LINE_DURATION = 600;
  const TOTAL_HEIGHT = lines.length * STEP_PER_LINE + LINE_DURATION + 300;

  const stageEl = document.createElement('div');
  stageEl.id = 'kyouiku-stage';
  stageEl.style.cssText =
    `width: 100%; height: ${TOTAL_HEIGHT}px; position: relative;`;
  lyricsEl.insertAdjacentElement('afterend', stageEl);

  if (!document.getElementById('kyouiku-style')) {
    const style = document.createElement('style');
    style.id = 'kyouiku-style';
    style.textContent = `
      .kyouiku-line {
        position: fixed;
        top: 50vh;
        left: 50%;
        transform: translateX(-50%) translateY(-50%);
        white-space: nowrap;
        letter-spacing: 0.12em;
        line-height: 1;
        opacity: 0;
        color: #fff;
        pointer-events: none;
        z-index: 9999;
      }
    `;
    document.head.appendChild(style);
  }

  const lineEls = lines.map(text => {
    const el = document.createElement('div');
    el.className = 'kyouiku-line';
    el.textContent = text;
    document.body.appendChild(el);
    return el;
  });

  function lerp(a, b, t) { return a + (b - a) * t; }
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
  function ease(t) { return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t; }

  // vw比率 → px に変換したキーフレームを生成
  function buildKeyframes() {
    const vw = window.innerWidth;
    return KEYFRAMES_VW.map(kf => ({
      s: kf.s,
      font: vw * kf.fontVw / 100,
      opacity: kf.opacity,
    }));
  }

  function sampleKeyframes(kfs, s) {
    if (s <= kfs[0].s) return { ...kfs[0] };
    const last = kfs[kfs.length - 1];
    if (s >= last.s) return { ...last };
    for (let i = 0; i < kfs.length - 1; i++) {
      const a = kfs[i], b = kfs[i + 1];
      if (s >= a.s && s <= b.s) {
        const t = ease((s - a.s) / (b.s - a.s));
        return {
          font: lerp(a.font, b.font, t),
          opacity: lerp(a.opacity, b.opacity, t),
        };
      }
    }
  }

  function update() {
    const kfs = buildKeyframes();  // 毎フレーム現在のvwで計算
    const stageTop = stageEl.getBoundingClientRect().top + window.scrollY;
    const scrollInStage = window.scrollY - stageTop + window.innerHeight / 2;

    lineEls.forEach((el, i) => {
      const start = i * STEP_PER_LINE;
      const end = start + LINE_DURATION;

      if (scrollInStage <= start || scrollInStage >= end) {
        el.style.opacity = '0';
        return;
      }

      const s = clamp((scrollInStage - start) / LINE_DURATION, 0, 1);
      const kf = sampleKeyframes(kfs, s);

      el.style.fontSize = kf.font + 'px';
      el.style.opacity = clamp(kf.opacity, 0, 1);
      el.style.color = '#fff';
    });
  }

  window.addEventListener('scroll', update, { passive: true });

  // リサイズ時も再計算（フォントサイズが追従する）
  window.addEventListener('resize', update, { passive: true });

  update();
}