// ホスト名+ドメインの取得
function baseURL() {
    var currentURL = window.location.href;
    var protocolAndDomain = currentURL.split("//")[0] + "//" + currentURL.split("/")[2];
    return protocolAndDomain;
}


// メニューの切り替え
var isMain = true;
var menuarticleEle = document.getElementById("menuarticle");
var imicomHeaderEle = document.getElementById("imiN_header");
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

// Song APIの取得
var isGetSongJson = false;
var songJson;
async function getSongJson() {
    if (isGetSongJson) {
        return songJson;
    }

    res = await fetch(baseURL() + "/api/song/?format=json");
    songJson = await res.json();
    isGetSongJson = true;
    return songJson;
}


function sleep(s) {
    return new Promise(resolve => setTimeout(resolve, s*1000));
}

function appendSongGuesser(song, toEle) { 
    songGuesser = `<div class="song-guesser" onclick="clickSong('${song.id}')">
        <p><span class="channel"><i class="fas fa-user-circle"></i>${song.channel}</span> 
        <i class="fas fa-music"></i> ${song.title}</p> 
    </div>`;
    songGuesserEle = new DOMParser().parseFromString(songGuesser, "text/html").body.firstElementChild; 
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

    songJson = await getSongJson();
    try {
        songJson = await getSongJson();
        songStack = songJson.filter(song => song.title.includes(text)).concat(songJson.filter(song => song.channel.includes(text)));

        for (const song of songStack) {
            // キャンセルが要求されているか確認
            if (signal.aborted) {
                throw new Error("Operation aborted");
            }

            appendSongGuesser(song, toEle);
            await sleep(0.05);
        }
    } catch (error) {
    }
}

// グローバルヘッダーの取得
async function getHeader() {
    try {
        const res = await fetch("https://script.google.com/macros/s/AKfycbx6kVTjsvQ5bChKtRMp1KCRr56NkkhFlOXhYv3a_1HK-q8UJTgIvFzI1TTpzIWGbpY6/exec?type=full");
        const text = await res.text();
        if ( ! res.ok ) {
            throw new RuntimeError(`getHeader: Response: ${res.status}`);
        }
        
        const devEle = document.createElement("div");
        devEle.innerHTML = text;
        const imicomEle = devEle.children;
        imicomHeaderEle.append(...imicomEle);
    } catch ( error ) {
        console.error(error);

        const p = document.createElement("p");
        p.textContent = "ヘッダーを読み込めませんでした。再読み込みをお試しください。";
        imicomHeaderEle.append(p);
    }

    const headerEle = document.getElementsByTagName("header")[0];
    headerEle.style.top = `-${imicomHeaderEle.clientHeight + 5}px`;

    
    var imiN_listEles = document.getElementsByClassName("imiN_list")[0].children;
    Array.from(imiN_listEles).forEach(function(imiN_listEle) {
        imiN_listEle.children[0].className = "sansfont";
        imiN_listEle.children[0].style = "color: #000; font-size: 16px;"
    })

    var faultEle = document.getElementsByClassName("fault")[0].children[0];
    faultEle.style = "color: #FFF; font-size: 16px";
    
    var imiN_header_innerEle = document.getElementsByClassName("imiN_header_inner")[0];
    imiN_header_innerEle.style = "padding-left: 0"

    var imiN_noticeEle = document.getElementsByClassName("imiN_notice")[0].childNodes[2];
    imiN_noticeEle.style = "color: #777"
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


// cookieの同意
function agree(isagree) {
    agreeEle = document.getElementById("agreement");
    if (isagree) {
        setCookie("agree", "yes");
        agreeEle.style = "display: none";
    }
    if (getCookie().agree == undefined) {
        agreeEle.style = "display: block";
    }
}


// 読み込み時の実行
window.onload = function() {
    getHeader();
    agree(false);
}
