var type = 0;
var songjson, songEles;

async function getSong(basedir) {
    res = await fetch(basedir + "/subeana/api/song/?format=json");
    songjson = await res.json();

    songEles = document.getElementsByClassName("songs");
}


function changetype(radiotype) {
    categorysecEle = document.getElementById("categorysec");
    songsecEle = document.getElementById("songsec");
    similarsecEle = document.getElementById("similarsec");
    if (radiotype == 0) {
        categorysecEle.style.display = "block";
        songsecEle.style.display = "none";
        similarsecEle.style.display = "block";
    } else if (radiotype == 1) {
        categorysecEle.style.display = "none";
        songsecEle.style.display = "block";
        similarsecEle.style.display = "block";
    } else if (radiotype == 2) {
        categorysecEle.style.display = "none";
        songsecEle.style.display = "none";
        similarsecEle.style.display = "none";
    }

    type = radiotype;
    makeform(radiotype);
}


function devinput(radiotype) {
    radioEle = document.getElementsByClassName("genetype")[radiotype];
    radioEle.checked = true;
    changetype(radiotype);
}


function titleinput(title) {
    titleEle = document.getElementById("title");
    titleEle.value = title;
    for (songEle of songEles) {
        songEle.parentElement.style.display = "none";
    }

    makeform();
}


function searchsong() {
    titleEle = document.getElementById("title");
    title = titleEle.value;
    if (title == "") {
        for (songEle of songEles) {
            songEle.parentElement.style.display = "none";
        }
    } else {
        for (songEle of songEles) {
            if (songEle.id.match(title) == null) {
                songEle.parentElement.style.display = "none";
            } else {
                songEle.parentElement.style.display = "block";
            }
        }
    }

    makeform();
}


function similarinput() {
    similarEle = document.getElementById("similar");
    similarvalueEle = document.getElementById("similarvalue");

    similarvalueEle.innerHTML = similarEle.value;
}


function makeform() {
    submitEle = document.getElementById("submit");
    
    if (type == 0) {
        categoryEle = document.getElementById("category");
        if (categoryEle.value == "選択してください") {
            submitEle.disabled = true;
        } else {
            submitEle.disabled = false;
        }
    } else if (type == 1) {
        titleEle = document.getElementById("title");
        if (titleEle.value == "") {
            submitEle.disabled = true;
        } else {
            song = songjson.find((v) => v.title == titleEle.value);      // jsonから歌詞を検索
            if (song == null) {
                submitEle.disabled = true;
            } else {
                submitEle.disabled = false;
            }
        }

    } else if (type == 2) {
        submitEle.disabled = false;
    }
}

function displayerror(error) {
    toastr.options = {
        "closeButton": false,
        "debug": false,
        "newestOnTop": false,
        "progressBar": true,
        "positionClass": "toast-bottom-right",
        "preventDuplicates": false,
        "onclick": null,
        "timeOut": "10000",
        "extendedTimeOut": "0",
        "showEasing": "swing",
        "hideEasing": "linear",
    }

    toastr.warning(error)
}