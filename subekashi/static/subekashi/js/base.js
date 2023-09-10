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

	const target_elm = document.getElementById("imiN_header");
	target_elm.append(...header);

    } catch ( error ) {
	console.error(error);

	const p = document.createElement("p");
	p.textContent = "ヘッダーを読み込めませんでした。再読み込みをお試しください。";
	const target_elm = document.getElementById("imiN_header");
	target_elm.append(p);
    }
}

window.onload = function() {
    kanji();
    getHeader();
}
