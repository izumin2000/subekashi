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
    let clientHeight = textarea.clientHeight - 20;
    textarea.style.height = clientHeight + 'px';
    let scrollHeight = textarea.scrollHeight - 20;
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
    if (!song.isoriginal && !song.issubeana) {
        columnL.push(song.imitate);
    }
    if (!song.isinst) {
        columnL.push(song.lyrics);
    }
    return !columnL.includes("");
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

    var faultEle = document.getElementsByClassName("fault")[0]
    faultEle.style = "background-color: #FFF"
    var imiN_listEle = document.getElementsByClassName("imiN_list")[0]
    console.log(imiN_listEle);
    imiN_listEle.childNodes[0].style = "font-color: #000"
    var imicomInnerEle = imicomHeaderEle.children[2].children[0]
    imicomInnerEle.classList.add("imiN_headerOverwrite");
    imicomInnerEle.textContent = "イミコミュメニュー";
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
    let cookies = '';
    let cookieArray = new Array();
    let result = {};

    cookies = document.cookie;

    if (cookies) {
        cookieArray = cookies.split('; ');

        cookieArray.forEach(data => {
            data = data.split('=');

            if (data[0].trim() !== 'csrftoken') {
                result[data[0]] = JSON.parse(data[1]);
            }
        });
    }
    return result;
}


// 読み込み時の実行
window.onload = function() {
    getHeader();
}
