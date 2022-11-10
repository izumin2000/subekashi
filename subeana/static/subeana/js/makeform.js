var radiotype = true;


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
    return 1;
}

function devinput(radiotype) {
    radioEle = document.getElementsByClassName("genetype")[radiotype];
    radioEle.checked = true;
    changetype(radiotype);
}

function makeform() {
    return 1;

}