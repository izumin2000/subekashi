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
function menu() {
    if (isMain) {
        document.getElementById("menuicon").innerHTML = "<i class='fas fa-times'></i>";
        document.getElementById("menuarticle").style.display = "block";
        document.getElementById("menuarticle").style.position = "fixed";
        isMain = false;
    } else {
        document.getElementById("menuicon").innerHTML = "<i class='fas 	fas fa-bars'></i>";
        document.getElementById("menuarticle").style.display = "none";
        document.getElementById("menuarticle").style.position = "static";
        isMain = true;
    }
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
    res = await fetch("https://script.google.com/macros/s/AKfycbx-0xNDgYC2FEtislBFe4afGaX0DbRTuSwHMUZH2380R34up5SV-D4eKRNls0f6keG5ow/exec");
    resJson = await res.json();
    var imindata = resJson[0].headdata;
    document.getElementById("imiN_header").innerHTML = imindata;
    globalHeaderEles = document.getElementsByClassName("imiN_list")[0];
    // globalHeaderEles.children[0].remove();
    // globalHeaderEles.children[2].remove();
}

window.onload = function() {
    kanji();
    getHeader();
}