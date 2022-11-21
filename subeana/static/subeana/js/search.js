var songjson, songEles;

async function getSong(basedir) {
    res = await fetch(basedir + "/subeana/api/song/?format=json");
    songjson = await res.json();
}


function changefiltertype(filtertype) {
    if (filtertype == 0) {
        console.log(0);
    } else if (filtertype == 1) {
        console.log(1);
    } else if (filtertype == 2) {
        console.log(2);
    }
}


function devinput(filtertype) {
    radioEle = document.getElementsByClassName("filters")[filtertype];
    radioEle.checked = true;
    changefiltertype(filtertype);
}