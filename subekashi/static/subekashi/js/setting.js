function setSetting() {
    if (Object.keys(getCookie()).length == 2) {
        var songrangeEle = document.getElementById("songrange");
        var jokerangeEle = document.getElementById("jokerange");
        songrangeEle.value = getCookie().songrange;
        jokerangeEle.value = getCookie().jokerange;
    } else {
        songrange();
        jokerange();
    }
}

function songrange() {
    var songrangeEle = document.getElementById("songrange");
    setCookie("songrange", songrangeEle.value)
}

function jokerange() {
    var jokerangeEle = document.getElementById("jokerange");
    setCookie("jokerange", jokerangeEle.value)
}