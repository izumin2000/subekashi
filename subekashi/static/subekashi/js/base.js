// 漢字のみ大きく
function kanji() {
    var query = ":not(:empty):not(.staticSize):not(.buttona):is(p, a, h1, h2, li, textarea, input, button, summary)";
    var elms = document.querySelectorAll(query);

    // Params.
    var every_kanji_seq_re = /[\u2E80-\u2FDF々〇〻\u3400-\u9FFF\uF900-\uFAFF\u{20000}-\u{3FFFF}]+/gu;
    var kanji_size = "150%";
    // console.assert(/^[0-9]+%$/.test(kanji_size), "kanji_size Syntax");
    
    // Enlarge every kanji sequence.
    for ( let charEle of elms ) {
        var new_font_size = `font-size: ${kanji_size}`;
        var newCharEle = charEle.innerHTML.replaceAll(every_kanji_seq_re, `<span style="${new_font_size}">$&</span>`);
        charEle.innerHTML = newCharEle
    }
}


// メニューの切り替え
var isMain = true;
var menuarticleEle = document.getElementById("menuarticle");
var imicomHeaderEle = document.getElementById("imiN_header");

function menu() {
    // imicomHeaderEle.classList.toggle("hide");

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
        const res = await fetch("https://script.google.com/macros/s/AKfycbx-0xNDgYC2FEtislBFe4afGaX0DbRTuSwHMUZH2380R34up5SV-D4eKRNls0f6keG5ow/exec");
        if ( ! res.ok ) {
            throw new RuntimeError(`getHeader: Response: ${res.status}`);
        }

        const resJson = await res.json();
        const resHeaddata = resJson[0].headdata;

        const devEle = document.createElement("div");
        devEle.innerHTML = resHeaddata;
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

    document.getElementsByClassName("fault")[0].remove();
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
    kanji();
    getHeader();
}
