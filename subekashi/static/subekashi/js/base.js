// ホスト名+ドメインの取得
function baseURL() {
    var currentURL = window.location.href;
    var protocolAndDomain = currentURL.split("//")[0] + "//" + currentURL.split("/")[2];
    return protocolAndDomain;
}

// 可変テキストエリア
document.querySelectorAll('textarea').forEach((textarea) => {
    textarea.oninput = function () {
        let clientHeight = textarea.clientHeight;
        textarea.style.height = clientHeight + 'px';
        let scrollHeight = textarea.scrollHeight;
        textarea.style.height = scrollHeight + 'px';
    };
});

// DRFのAPIの取得
async function getJson(path) {
    const res = await fetch(`${baseURL()}/api/${path}`, { cache: "reload" });
    return await res.json();
}

const abortControllers = {};
async function exponentialBackoff(path, from = "default") {
    const MAX_RETRY_COUNT = 5;

    // 以前のリクエストがあればキャンセル
    if (abortControllers[from]) {
        abortControllers[from].abort();
    }

    // 新しいAbortControllerを作成
    const controller = new AbortController();
    abortControllers[from] = controller;

    for (let retry = 1; retry <= MAX_RETRY_COUNT; retry++) {
        try {
            const res = await fetch(`${baseURL()}/api/${path}`, {
                cache: "reload",
                signal: controller.signal // キャンセル可能にする
            });

            if (!res.ok) {
                throw new Error(`HTTP error! Status: ${res.status}`);
            }

            return await res.json();
        } catch (error) {
            // キャンセルされた場合は終了
            if (controller.signal.aborted) {
                return;
            }

            if (retry < MAX_RETRY_COUNT) {
                await sleep(0.2 * 2 ** retry);
            } else {
                throw error;
            }
        }
    }
}

// s秒間プログラムを停止 awaitが必須
function sleep(s) {
    return new Promise(resolve => setTimeout(resolve, s*1000));
}

// 文字列からHTML要素に変換
function stringToHTML(string, multi=false) {
    const devEle = document.createElement("div");
    devEle.innerHTML = string;
    htmls = devEle.children; 

    if (multi) {
        return htmls;
    }

    return htmls[0];
}

// トーストを動的に表示する関数
async function showToast(icon, text) {
    try {
        const response = await fetch(`/api/html/toast?icon=${encodeURIComponent(icon)}&text=${encodeURIComponent(text)}`);
        if (!response.ok) throw new Error('Failed to fetch toast');

        const data = await response.json();
        const toastHTML = stringToHTML(data.toast);

        const toastContainerEle = document.getElementById('toast-container');
        toastContainerEle.appendChild(toastHTML);
    } catch (error) {
        console.error('Error showing toast:', error);
    }
}

// song guesserの表示
function appendSongGuesser(songGuesser, toEle) {
    var songGuesserEle = stringToHTML(songGuesser);
    toEle.appendChild(songGuesserEle)
}

var songGuesserController;
async function getSongGuessers(text, to, signal) {
    var toEle = document.getElementById(to);
    while (toEle.firstChild) {
        toEle.removeChild(toEle.firstChild);
    }

    if (text == "") {
        return;
    }

    try {
        const songGuessers = await getJson(`html/song_guessers?guesser=${text}`);
        for (var songGuesser of songGuessers) {
            // キャンセルが要求されているか確認
            if (signal.aborted) {
                return;
            }
            
            appendSongGuesser(songGuesser, toEle);
            await sleep(0.05);
        }
    } catch (error) {
        console.error(error)
    }
}

// グローバルヘッダーの取得
var globalHeaderEle, globalItemEles;
async function getGlobalHeader() {
    try {
        var globalHeaderRes = await fetch("https://global-header.imicom.workers.dev/");
    } catch ( error ) {
        document.getElementById("pc-global-items-wrapper").innerHTML = "<p>界隈グローバルヘッダーエラー</p>";
        document.getElementById("sp-global-items-wrapper").innerHTML = "<p>界隈グローバルヘッダーエラー</p>";
        return;
    }

    var globalHeaderText = await globalHeaderRes.text();
    globalHeaderEle = stringToHTML(globalHeaderText)
    globalItemEles = Array.from(globalHeaderEle.getElementsByClassName("imiN_list")[0].children)
    .slice(1, -1)
    .map(itemEle => formatGlobalHeaderItem(itemEle));
    setGlobalHeader("pc");
    setGlobalHeader("sp");
}

function formatGlobalHeaderItem(itemEle) {
    var aTag = itemEle.closest('a');

    var spOnly = itemEle.querySelector('span.sp_only');
    var pcOnly = itemEle.querySelector('span.pc_only');

    if (spOnly && pcOnly) {
        aTag.innerText = pcOnly.innerHTML;
    } else {
        aTag.innerText = itemEle.innerText;
    }

    return itemEle;
}

function setGlobalHeader(type) {
    var globalItemsWrapperEle = document.getElementById(`${type}-global-items-wrapper`);
    globalItemsWrapperEle.firstChild.remove();
    globalItemsWrapperEle.firstChild.remove();
    globalItemEles.forEach(globalItemEle => {
        globalItemsWrapperEle.appendChild(globalItemEle.cloneNode(true));
    });
    var imiNNews = globalHeaderEle.getElementsByClassName("imiN_news")[0].children[0].innerText;
    document.getElementById(`${type}-global-news`).innerText = imiNNews;
    var imiNNotice1 = globalHeaderEle.getElementsByClassName("imiN_notice")[0].children[0].innerHTML.replace("<br>", "")
    document.getElementsByClassName(`${type}-global-notice`)[0].innerText = imiNNotice1;
    var imiNNotice2 = globalHeaderEle.getElementsByClassName("imiN_notice")[0].children[1].innerHTML.replace("<br>", "")
    document.getElementsByClassName(`${type}-global-notice`)[1].innerText = imiNNotice2;
}

// #sp_menuの切り替え
var isSpMenuOpen = false;
document.getElementById("toggle-tab-bar").addEventListener("click", function () {
    const menuEle = document.getElementById("sp_menu");

    if (isSpMenuOpen) {
        menuEle.style.animation = "slideDown 0.3s forwards";
        menuEle.addEventListener("animationend", function hideMenu() {
            menuEle.style.display = "none";
            menuEle.removeEventListener("animationend", hideMenu);
        });
        isSpMenuOpen = false;
    } else {
        menuEle.style.display = "flex";
        menuEle.style.animation = "slideUp 0.3s forwards";
        isSpMenuOpen = true;
    }
});

document.body.addEventListener('click', (event) => {
    const menuEle = document.getElementById("sp_menu");
    if (event.target.closest('#sp_menu')) {
        return;
    }

    if (event.target.closest('#toggle-tab-bar')) {
        return;
    }

    if (!isSpMenuOpen) {
        return;
    }

    menuEle.style.display = "none";
    isSpMenuOpen = false;
});

// tab_barをページ一番下までスクロールしたら非表示
document.addEventListener("DOMContentLoaded", () => {
    const tabBarEle = document.getElementById("tab_bar");

    const isScrollable = document.documentElement.scrollHeight > window.innerHeight;
    if (!isScrollable) {
        tabBarEle.setAttribute("class", "tab_bar_suspend");
    }

    // スクロール時のイベントを設定
    window.addEventListener("scroll", () => {
        const scrollPosition = window.scrollY + window.innerHeight;
        const bottomPosition = document.documentElement.scrollHeight;

        // 一番下までスクロールされた場合は非表示、そうでない場合は表示
        if ((scrollPosition >= bottomPosition - 1) && !isSpMenuOpen) {
            tabBarEle.setAttribute("class", "tab_bar_suspend");
        } else {
            tabBarEle.removeAttribute("class", "tab_bar_suspend");
        }
    });
});

// CSRFの取得
async function getCSRF() {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; csrftoken=`);
    if (parts.length === 2) {
        csrf = parts.pop().split(';').shift()
        return csrf;
    }
}

// クッキーの保存
function setCookie(name, json) {
    let expire = '';
    let period = '';
    cookies = name + '=' + JSON.stringify(json) + ';';
    cookies += 'path=/ ;';

    period = 360;        //保存日数
    expire = new Date();
    expire.setTime(expire.getTime() + 1000 * 3600 * 24 * period);
    expire.toUTCString();
    cookies += 'expires=' + expire + ';';

    document.cookie = cookies;
};

// クッキーの取得
function getCookie() {
    var cookieDict = {};
    var cookies = document.cookie.split("; ");
    
    if (document.cookie != '') cookies.forEach(function(cookie) {
        var parts = cookie.split("=");
        var name = decodeURIComponent(parts[0]);
        var value = decodeURIComponent(parts[1].replace(/"/g, ''));
        cookieDict[name] = value;
    });
    
    return cookieDict;
}

// 読み込み時の実行
window.onload = function() {
    getGlobalHeader();
}

// フォントのキャッシュ
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open('font-cache').then((cache) => {
            return cache.addAll([
                '../GenZenGothicKaiC.woff2',
                '../NotoSansJP-VariableFont_wght.woff2'
            ]);
        })
    );
});

self.addEventListener('fetch', (event) => {
    url = event.request.url;
    if (url.includes('GenZenGothicKaiC.woff2') || url.includes('../NotoSansJP-VariableFont_wght.woff2')) {
        event.respondWith(
            caches.match(event.request).then((response) => {
                return response || fetch(event.request);
            })
        );
    }
});

// YouTubeのURLから動画IDを取得
function getYouTubeId(url) {
    const regex = /(?:https?:\/\/)?(?:www\.|m\.)?(?:youtube\.com\/.*[?&]v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
    const match = url.match(regex);
    return match ? match[1] : null;
}

// YouTubeのURLから動画IDを取得
function formatYouTubeURL(url) {
    const youtube_id = getYouTubeId(url)
    if (!youtube_id) {
        return url;
    }

    return `https://youtu.be/${youtube_id}`
}

// チュートリアルトーストの表示
const TUTORIALS = {
    "new-form-auto": "YouTubeのリンクからタイトル・チャンネル名を自動で取得して登録するフォームです。既に登録してあるURLは登録できません。",
    "youtube-url": "YouTubeのURLを入力してください。<br>「後で見る」を含むプレイリスト内の動画のURLでも大丈夫です。<br>無断転載された動画のURLの記載はお控えください。",
    "is-original": "オリジナル模倣曲・フリースタイル模倣曲の場合はチェックをつけてください。<br>例）<a href='https://youtu.be/XkIKM80-Znc' target='_blank'>∴∴∴∴</a> <a href='https://youtu.be/zDUvoKUOviQ' target='_blank'>天秤にかけて</a>",
    "is-deleted": "アクセスしても視聴できない場合にチェックしてください。<br>限定公開の場合はチェックする必要はありません。",
    "is-joke": "ネタに走っている曲の場合にチェックしてください。<br>ネタ曲かどうかの判断は個人の判断に任せます。",
    "is-inst": "歌詞の無い曲の場合にチェックしてください。<br>例）<a href='https://youtu.be/6-h8cW_Han8' target='_blank'>明日へ降る雨</a> <a href='https://youtu.be/2P62pozC9Zc' target='_blank'>またの御アクセスをお待ちしております。</a>",
    "is-subeana": "すべあな界隈曲の場合はチェックしてください。<br>すべあな界隈曲かどうかの判断は個人の判断に任せます。",
    "new-form-manual": "手動でタイトル・チャンネル名を入力するフォームです。",
    "title": "YouTube上のタイトルや曲名を入力してください。<br>曲によっては複数のタイトルがある場合もあるので、その場合は一般的に知られているタイトルを入力することをオススメします。<span style='font-size: 10px'>将来的に曲の別名を入力できる機能を実装予定です。</span>",
    "channel": "チャンネル名やアーティスト名を入力してください。<br>複数のアーティストが関わっている場合はコンマ(,)で区切って入力してください。<br>複数の名義がある場合は、現在使われている名義・チャンネル名を入力してください。<span style='font-size: 10px'>将来的に名義に関する情報を入力できる機能を実装予定です。</span>",
    "url": "URLを入力してください。<br>半角コンマ(,)で区切ることで複数のURLを登録することができます。<br>転載動画のURLの記載はお控えください。",
    "imitate": "模倣元・オマージュ元・歌詞の引用元・アレンジ元の曲を入力してください。<br>全てあなたの所為です。の曲を選択するときは上部のボタンから、それ以外の曲を選択するときは下部の入力欄から検索することで選択できます。<br>入力欄に模倣曲のタイトルを入力してもヒットしない場合はまず、その模倣曲を情報を登録してください。<br>模倣曲は複数曲選択できます。",
    "lyrics": "歌詞を入力してください。<br>インスト曲の場合は入力は不要です。<br>形式は特に決まっていませんが、できるだけMVと同じように記述してくれると助かります。",
    "is-draft": "下書きとして投稿したい場合はチェックしてください。<br>入力途中だけど投稿したいときに利用してください。<br>下書きした内容は誰でも閲覧できる状態になります。",
    "delete": "開発者に記事の削除依頼を送ります。<br>実際に削除の対応をするまでに時間がかかる場合があります。",
    "reply": "返信が必要な場合ここに、X(旧：Twitter)のアカウントID、もしくはDiscordのユーザーID、もしくはメールアドレスを入力してください。<br>掲載拒否のお問い合わせの場合入力が必須です。",
}

function showTutorial(place) {
    const tutorial = TUTORIALS[place];
    showToast("info", tutorial);
}