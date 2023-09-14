// 漢字のみ大きく
function kanji() {
    tags = ['p', 'a', 'h1', 'h2', 'li'];
    for (tag of tags) {
        for (p of document.getElementsByTagName(tag)) {
            if (p.className != "nokanji") {
                if (['p', 'a', "li"].includes(tag)) {
                    p.innerHTML = p.innerHTML.replace(/([\u4E00-\u9FFF])/gi,"<font class=kanjipa>$1</font>");
                } else {
                    p.innerHTML = p.innerHTML.replace(/([\u4E00-\u9FFF])/gi,"<font class=kanjih>$1</font>");
                }
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
    if (song.isoriginal) {
        return ![songResult.url, songResult.lyrics].includes("");
    } else {
        return ![songResult.url, songResult.lyrics, songResult.imitate].includes("");
    }
}

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

window.onload = function() {
    kanji();
    getHeader();
}
