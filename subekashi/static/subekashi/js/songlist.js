function songpage(basedir, song_id) {
    window.location.href = basedir + "/songs/" + song_id;
}

function changecss() {
    cardrightEles = document.getElementsByClassName("cardright");
    for (cardrightEle of cardrightEles) {
        if (window.innerWidth < 840) {
            cardrightEle.style.display = "none";
        } else {
            cardrightEle.style.display = "block";
        }
    }
    songcardEles = document.getElementsByClassName("songcard");
    for (songcardEle of songcardEles) {
        if (window.innerWidth < 840) {
            songcardEle.style.padding = "0 15px";
        } else {
            songcardEle.style.padding = "15px 0px 15px 0px";
        }
    }
}

window.addEventListener('load', changecss);

window.addEventListener('DOMContentLoaded', function(){
    window.addEventListener('resize', changecss, false);
});