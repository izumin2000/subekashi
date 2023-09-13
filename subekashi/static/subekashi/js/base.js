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
const menuarticle = document.getElementById("menuarticle");
const imiN_header = document.getElementById("imiN_header");

function menu() {
    // imiN_header.classList.toggle("hide");

    menuarticle.classList.toggle("shown");

    /* XXX(Tpaefawzen): IDK why `menuicon` could not be global const;
     * it is <i> element and toggling did not change its actual list of
     * classes.  Therefore I am declaring here.
     * OBTW `menuarticle` worked even it is declared globally.
     */
    const menuicon    = document.getElementById("menuicon");
    menuicon.classList.toggle("fa-bars");
    menuicon.classList.toggle("fa-times");

    isMain = ! isMain;
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
    /**
     * @global imiN_header
     */

    const url_to_get_header = "https://script.google.com/macros/s/AKfycbx-0xNDgYC2FEtislBFe4afGaX0DbRTuSwHMUZH2380R34up5SV-D4eKRNls0f6keG5ow/exec";

    try {
	const res = await fetch(url_to_get_header);
	if ( ! res.ok ) {
	    throw new RuntimeError(`getHeader: Response: ${res.status}`);
	}

	const res_json = await res.json();
	const imindata = res_json[0].headdata;

	const div_to_header = document.createElement("div");
	div_to_header.innerHTML = imindata;
	const header = div_to_header.children;

	imiN_header.append(...header);

    } catch ( error ) {
	console.error(error);

	const p = document.createElement("p");
	p.textContent = "ヘッダーを読み込めませんでした。再読み込みをお試しください。";
	imiN_header.append(p);
    }

    const header = document.getElementsByTagName("header")[0];
    header.style.top = `-${imiN_header.clientHeight}px`;
}

window.onload = function() {
    kanji();
    getHeader();
}
