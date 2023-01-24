// メニューの切り替え
function menu() {
    var isMenu = document.getElementById("menuarticle").style.display
    console.log(isMenu)
    if (isMenu != "block") {
        document.getElementById("mainarticle").style.display = "none";
        document.getElementById("menuicon").innerHTML = "<i class='fas fa-times'></i>";
        document.getElementById("menuarticle").style.display = "block";
        document.getElementsByTagName("main")[0].style.background = "linear-gradient(90deg, #eee, #eee, calc(40vw + 160px), #BB002D)";
    } else {
        document.getElementById("mainarticle").style.display = "block";
        document.getElementById("menuicon").innerHTML = "<i class='fas 	fas fa-bars'></i>";
        document.getElementById("menuarticle").style.display = "none";
        document.getElementsByTagName("main")[0].style.background = ""
    }
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


// コピーのtoastr
function copyCode(text) {
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

    if (Boolean(navigator.clipboard)) {
        navigator.clipboard.writeText(text);
        toastr.success(text + " をコピーしました！")
    } else {
        toastr.warning("この機能はセキュリティの関係上、HTTPS環境上でしか動作しません。")
    }
}