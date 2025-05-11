// スペシャルデザインボタンを表示
function add_special_button() {
    var defaultDummybuttonsEle = document.getElementsByClassName("dummybuttons")[0];
    const designedDummybuttonsEle =
    `
    <div class="dummybuttons">
        <a>
            <div class="dummybutton" onclick="special()"><i class="fas fa-magic"></i><p>スペシャルデザイン</p></div>
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