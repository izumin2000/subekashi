// 漢字のみおおきく
function kanji() {
    tags = ['p', 'a', 'h1', 'h2'];
    for (tag of tags) {
        for (p of document.getElementsByTagName(tag)) {
            if (p.className != "nokanji") {
                if (['p', 'a'].includes(tag)) {
                    p.innerHTML = p.innerHTML.replace(/([\u4E00-\u9FFF])/gi,"<font class=kanjipa>$1</font>");
                } else {
                    p.innerHTML = p.innerHTML.replace(/([\u4E00-\u9FFF])/gi,"<font class=kanjih>$1</font>");
                }
            }
        }
    }
}


// メニューの切り替え
function menu() {
    var isMenu = document.getElementById("menuarticle").style.display
    if (isMenu != "block") {
        document.getElementById("mainarticle").style.display = "none";
        document.getElementById("menuicon").innerHTML = "<i class='fas fa-times'></i>";
        document.getElementById("menuarticle").style.display = "block";
        document.getElementsByTagName("main")[0].style.background = "linear-gradient(180deg, #000, #000, 70vh, #005)";
    } else {
        document.getElementById("mainarticle").style.display = "block";
        document.getElementById("menuicon").innerHTML = "<i class='fas 	fas fa-bars'></i>";
        document.getElementById("menuarticle").style.display = "none";
        document.getElementsByTagName("main")[0].style.background = ""
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