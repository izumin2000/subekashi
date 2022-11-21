function songpage(basedir, song_id) {
    window.location.href = basedir + "/subeana/songs/" + song_id;
}

function songlack(basedir, song_id) {
    window.location.href = basedir + "/subeana/edit?id=" + song_id;
}

function changecss() {
    cardrightEles = document.getElementsByClassName("cardright");
    for (cardrightEle of cardrightEles) {
        if (window.innerWidth < 800) {
            cardrightEle.style.display = "none";
        } else {
            cardrightEle.style.display = "block";
        }
    }
    songcardEles = document.getElementsByClassName("songcard");
    for (songcardEle of songcardEles) {
        if (window.innerWidth < 800) {
            songcardEle.style.padding = "20px 0 90px 0";
        } else {
            songcardEle.style.padding = "15px 0 10px 0";
        }
    }
}

window.addEventListener('load', changecss);

window.addEventListener('DOMContentLoaded', function(){
    window.addEventListener('resize', changecss, false);
});