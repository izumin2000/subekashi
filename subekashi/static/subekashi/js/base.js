// 漢字のみおおきく
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
    kanji();
}


// 存在しないページのtoastr
function notfound(){
    toastr.options = {
        "closeButton": false,
        "debug": false,
        "newestOnTop": false,
        "progressBar": true,
        "positionClass": "toast-bottom-right",
        "preventDuplicates": false,
        "onclick": null,
        "timeOut": "3000",
        "extendedTimeOut": "0",
        "showEasing": "swing",
        "hideEasing": "linear",
    }

    toastr.info("このページはまだ存在しません！")
};


// 可変テキストエリア
function autotextarea() {
    let textarea = document.getElementById('lyrics');
    let clientHeight = textarea.clientHeight - 20;
    textarea.style.height = clientHeight + 'px';
    let scrollHeight = textarea.scrollHeight - 20;
    textarea.style.height = scrollHeight + 'px';
}

// ソングページ
function songpage(basedir, song_id) {
    window.location.href = basedir + "/songs/" + song_id;
}

window.onload = function() {
    kanji();
}