// 漢字のみ大きく
function kanji() {
    tags = ['p', 'a', 'h1', 'h2', 'li', 'textarea', 'input', 'button', 'summary'];
    for (tag of tags) {
        for (charEle of document.getElementsByTagName(tag)) {
            if ((!charEle.classList.contains('staticSize') && (!charEle.classList.contains('buttona')) && (charEle != null))) {
                var computedStyle = window.getComputedStyle(charEle);
                var fontSize = computedStyle.getPropertyValue('font-size');
                var FontSize = parseFloat(fontSize);
                var sizeUnit = fontSize.replace(FontSize.toString(), "");
                var newStyle = `font-size: ${parseInt(FontSize * 1.5)}${sizeUnit}`;
                var newCharEle = charEle.innerHTML.replace(/([\u4E00-\u9FFF])/gi,`<span style="${newStyle}">$1</span>`);
                charEle.innerHTML = newCharEle
            }
        }
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
    let result = new Array();

    cookies = document.cookie;

    if(cookies){
        cookieArray = cookies.split(';');
        
        cookieArray.forEach(data => {
            data = data.split('=');
            result[data[0]] = JSON.parse(data[1]);
        });
    }
    return result;
}

// 読み込み時の実行
window.onload = function() {
    kanji();
    getHeader();
}
