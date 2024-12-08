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

// songが情報不足ではないかどうか
function isCompleted(song) {
    if (song.isdraft) {
        return false;
    }
    if (song.channel == "全てあなたの所為です。") {
        return true;
    }
    columnL = [];
    if (!song.isdeleted) {
        columnL.push(song.url);
    }
    if (!song.isoriginal && song.issubeana) {
        columnL.push(song.imitate);
    }
    if (!song.isinst) {
        columnL.push(song.lyrics);
    }
    return !columnL.includes("");
}

var jsonDatas = {}
async function getJson(path) {
    if (jsonDatas[path]) {
        return jsonDatas[path];
    }

    res = await fetch(`${baseURL()}/api/${path}`);
    json = await res.json();

    if (!path.includes("?")) {
        jsonDatas[path] = json;
    }

    return json;
}

function sleep(s) {
    return new Promise(resolve => setTimeout(resolve, s*1000));
}

function stringToHTML(string, multi=false) {
    const devEle = document.createElement("div");
    devEle.innerHTML = string;
    htmls = devEle.children; 

    if (multi) {
        return htmls;
    }

    return htmls[0];
}

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
        songGuessers = await getJson(`html/song_guessers?guesser=${text}`);
        for (songGuesser of songGuessers) {
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
        var globalHeaderRes = await fetch("https://script.google.com/macros/s/AKfycbx6kVTjsvQ5bChKtRMp1KCRr56NkkhFlOXhYv3a_1HK-q8UJTgIvFzI1TTpzIWGbpY6/exec?type=full");
    } catch ( error ) {
        document.getElementById("pc-global-items-wrapper").innerHTML = "<p>界隈グローバルヘッダーエラー</p>";
        document.getElementById("sp-global-items-wrapper").innerHTML = "<p>界隈グローバルヘッダーエラー</p>";
        return;
    }

    var globalHeaderText = await globalHeaderRes.text();
    globalHeaderEle = stringToHTML(globalHeaderText, true)[1]
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
