var songjson, songEles;

async function getSong(basedir) {
    res = await fetch(basedir + "/subeana/api/song/?format=json");
    songjson = await res.json();
        songEles = document.getElementsByClassName("songcard");
}

function searchsong() {
    searchEle = document.getElementById("search");
    search = searchEle.value;
    id = 0;
    nothit = true;
    for (songEle of songEles) {
        styledisplay = "none";
        if (!search) {
            styledisplay = "block";
            nothit = false;
        }
        if (songjson[id]["title"].match(search) != null) {
            styledisplay = "block";
            nothit = false;
        }
        if (songjson[id]["channel"].match(search) != null) {
            styledisplay = "block";
            nothit = false;
        }
        if (songjson[id]["lyrics"].match(search) != null) {
            styledisplay = "block";
            nothit = false;
        }
        
        songEle.style.display = styledisplay;

        notfoundEle = document.getElementById("notfound")       
        if (nothit) {
            notfoundEle.style.display = "block";
        } else {
            notfoundEle.style.display = "none";
        }
        id++;
    }
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