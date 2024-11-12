// ホスト名+ドメインの取得
function baseURL() {
    var currentURL = window.location.href;
    var protocolAndDomain = currentURL.split("//")[0] + "//" + currentURL.split("/")[2];
    return protocolAndDomain;
}


// メニューの切り替え
var isMain = true;
var menuarticleEle = document.getElementById("menuarticle");
function menu() {
    menuarticleEle.classList.toggle("shown");
    const menuiconEle = document.getElementById("menuicon");
    menuiconEle.classList.toggle("fa-bars");
    menuiconEle.classList.toggle("fa-times");

    isMain =! isMain;
}


// 可変テキストエリア
function autotextarea() {
    let textarea = document.getElementById('lyrics');
    let clientHeight = textarea.clientHeight;
    textarea.style.height = clientHeight + 'px';
    let scrollHeight = textarea.scrollHeight;
    textarea.style.height = scrollHeight + 'px';
}


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
    songGuesserEle = stringToHTML(songGuesser);
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
var globalHeaderWrapperEle = document.getElementById("global_header_wrapper");
async function getHeader() {
    try {
        const globalHeaderRes = await fetch("https://script.google.com/macros/s/AKfycbx6kVTjsvQ5bChKtRMp1KCRr56NkkhFlOXhYv3a_1HK-q8UJTgIvFzI1TTpzIWGbpY6/exec?type=full");
        if (!globalHeaderRes.ok) {
            throw new RuntimeError(`getHeader: Response: ${globalHeaderRes.status}`);
        }
        var globalHeaderText = await globalHeaderRes.text();
        var globalHeaderEle = stringToHTML(globalHeaderText, true)[1]
    } catch ( error ) {
        globalHeaderEle.innerHTML = "グローバルヘッダーエラー";
    }


    globalHeaderWrapperEle.firstChild.remove();
    globalHeaderWrapperEle.firstChild.remove();
    const globalHeaderItemEles = Array.from(globalHeaderEle.getElementsByClassName("imiN_list")[0].children).slice(1, -1);
    for (var globalHeaderItemEle of globalHeaderItemEles) {
        const aTag = globalHeaderItemEle.closest('a');

        const spOnly = globalHeaderItemEle.querySelector('span.sp_only');
        const pcOnly = globalHeaderItemEle.querySelector('span.pc_only');

        if (spOnly && pcOnly) {
            aTag.innerText = pcOnly.innerHTML;
        } else {
            aTag.innerText = globalHeaderItemEle.innerText;
        }
        globalHeaderWrapperEle.appendChild(globalHeaderItemEle);
    }

    console.log(globalHeaderEle)
    var imiNNews = globalHeaderEle.getElementsByClassName("imiN_news")[0].children[0].innerText;
    document.getElementById("global_news").innerText = imiNNews;
    var imiN_notice1 = globalHeaderEle.getElementsByClassName("imiN_notice")[0].children[0].innerHTML.replace("<br>", "")
    document.getElementsByClassName("global_notice")[0].innerText = imiN_notice1;
    var imiN_notice2 = globalHeaderEle.getElementsByClassName("imiN_notice")[0].children[1].innerHTML.replace("<br>", "")
    document.getElementsByClassName("global_notice")[1].innerText = imiN_notice2;
}


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
    getHeader();
}
