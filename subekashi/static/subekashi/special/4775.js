var timer;
function autoScroll(element, speed, direction) {
    let scrollTop = element.scrollTop;
    const interval = 6;
    const scrollDirection = direction === 'up' ? -1 : 1;

    timer = setInterval(() => {
        scrollTop += scrollDirection;
        element.scrollTop = scrollTop;

        // 上方向：scrollTopが0以下で停止
        if (scrollDirection === -1 && element.scrollTop <= 0) {
            clearInterval(timer);
        }
        // 下方向：スクロールが末尾に到達したら停止
        if (scrollDirection === 1 && element.scrollTop + element.clientHeight >= element.scrollHeight) {
            clearInterval(timer);
        }
    }, speed * interval);
}


function changeLyricsDesign() {
    const lyricsEle = document.getElementById("lyrics");
    lyricsEle.style.lineHeight = '300px';
    lyricsEle.style.fontSize = '36px';
    lyricsEle.innerText = `
        携帯ゲーム機の、
        蓋は消えたけど。
        ただ崩れてく此の夢は、
        溶けて無くなる。
        夜明けの時間は、
        もう進まない。
        ただ呼ぶだけの雨粒は、
        盲言の如く。
        それは不可逆的な理を、
        生み出した終焉。
        戯れに欠いた現実は、
        枯れてゆくのでした。




        手のひらで描いた、
        円は質すけど。
        枯れてゆく心を見つめ、
        冷たくなるの。
        霞んた頭蓋の、
        外に出かけて。
        捻れた現実を少しずつ、
        受けれてゆく。
        それは不可逆的な理を、
        生み出した終焉。
        戯れに欠いた現実は、
        全て歌詞の所為です。










        それは不可逆的な理を、
        生み出した終焉。
        戯れに欠いた現実は、
        全て■■の所為です。
        潜在空間に、
        見つめられたのか。


    `
}


let currentPlayController = null;
var defaultDummybuttonsEle = document.getElementsByClassName("dummybuttons")[0];
async function play() {
    // 前の処理があれば中止
    if (currentPlayController) {
        currentPlayController.abort();
    }

    // 停止ボタンに変更
    const stopEle = `
    <div class="dummybuttons">
        <a>
            <div class="dummybutton" onclick="stop()"><i class="fas fa-stop"></i><p>停止</p></div>
        </a>
    </div>
    `;
    defaultDummybuttonsEle.innerHTML = stringToHTML(stopEle).innerHTML;
    defaultDummybuttonsEle.style.position = "sticky";
    defaultDummybuttonsEle.style.top = "15px";
    defaultDummybuttonsEle.style.zIndex = '9999';
    defaultDummybuttonsEle.style.opacity = '0.5';

    // 新しいAbortControllerを作成
    const controller = new AbortController();
    const signal = controller.signal;
    currentPlayController = controller;

    changeLyricsDesign();
    const BEAT_TIME = 60 * 4 / 132;

    const audio = new Audio(`${baseURL()}/static/subekashi/special/4775.mp3`);
    audio.play();
    signal.addEventListener('abort', () => {
        audio.pause();
        audio.currentTime = 0;
    });

    try {
        await sleepWithAbort(5.5* BEAT_TIME, signal);
        const scrollingContainer = document.getElementsByTagName("html")[0];
        window.scrollTo(0, 0);
        autoScroll(scrollingContainer, 2, 'down');

        await sleepWithAbort(19.5 * BEAT_TIME, signal);
        showToast("ok", "ーー・ ".repeat(16));

        await sleepWithAbort(6 * BEAT_TIME, signal);
        showToast("info", "ーー・ ・・・ー ".repeat(4));

        await sleepWithAbort(3 * BEAT_TIME, signal);
        showToast("ok", "ーー・ ".repeat(9));

        await sleepWithAbort(3.5 * BEAT_TIME, signal);
        showToast("info", "ーー・ ・・・ー ".repeat(3));

        await sleepWithAbort(19.5 * BEAT_TIME, signal);
        for (let i = 0; i < 10; i++) {
            if (signal.aborted) break;
            showToast("warning", "ーー・ ーー・ ーー・ ・・・ー ーー・ ーー・ ・・・ー");
            await sleepWithAbort(2.625 * BEAT_TIME, signal);
        }
        await sleepWithAbort(16 * BEAT_TIME, signal);
        stop();
    } catch (e) {
        if (e.name !== 'AbortError') {
            console.error('play aborted with error:', e);
        }
    }
}

function stop() {
    playEle = `
        < div class="dummybuttons" >
            <a>
                <div class="dummybutton" onclick="play()"><i class="fas fa-play"></i><p>再生</p></div>
            </a>
        </ >
    `
    defaultDummybuttonsEle.innerHTML = stringToHTML(playEle).innerHTML;

    clearInterval(timer);
    if (currentPlayController) {
        currentPlayController.abort();
        currentPlayController = null;
    }
}

// Abort対応sleep
function sleepWithAbort(seconds, signal) {
    return new Promise((resolve, reject) => {
        const timeout = setTimeout(resolve, seconds * 1000);
        signal.addEventListener('abort', () => {
            clearTimeout(timeout);
            reject(new DOMException('Aborted', 'AbortError'));
        });
    });
}

document.addEventListener("DOMContentLoaded", () => {
    const designedDummybuttonsEle =
    `
    <div class="dummybuttons">
        <a>
            <div class="dummybutton" onclick="play()"><i class="fas fa-play"></i><p>再生</p></div>
        </a>
    </div>
    `
    defaultDummybuttonsEle.innerHTML = stringToHTML(designedDummybuttonsEle).innerHTML;
});