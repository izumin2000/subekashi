var songjson, songEles;

async function getSong(basedir) {
    res = await fetch(basedir + "/subeana/api/song/?format=json");
    songjson = await res.json();
        songEles = document.getElementsByClassName("songcard");
}

function searchsong() {
    searchEle = document.getElementById("search");
    search = searchEle.value;
    i = 0;

    filtrtEles = document.getElementsByClassName("filters")
    filtertype = 0
    for (filtrtEle of filtrtEles) {
        if (filtrtEle.checked) {
            break
        }
        filtertype++;
    }

    categoryEle = document.getElementById("category");
    category = categoryEle.value.slice(0, -2);
    if (category == "全ての") {
        category_id = 0
    } else {
        category_id = String(songjson.find((v) => v.title == category).id);
    }

    for (songEle of songEles) {
        styledisplay = "none";

        if (!search) {
            styledisplay = "block";
        }
        if (songjson[i]["title"].match(search) != null) {
            styledisplay = "block";
        }
        if (songjson[i]["channel"].match(search) != null) {
            styledisplay = "block";
        }
        if (songjson[i]["lyrics"].match(search) != null) {
            styledisplay = "block";
        }

        if (!songjson[i]["imitate"].split(",").includes(category_id) && category_id) {
            styledisplay = "none";
        }
        
        if (filtertype == 1) {
            if (((songjson[i]["url"] != "") && (songjson[i]["lyrics"] != "")) || (songjson[i]["channel"] == "")) {
                styledisplay = "none";
            } 
        } else if (filtertype == 2) {
            if (songjson[i]["channel"] != "") {
                styledisplay = "none";
            }
        }
        songEle.style.display = styledisplay;
        i++;
    }

    notfoundEle = document.getElementById("notfound")       
    nothit = true;
    for (songEle of songEles) {
        if (songEle.style.display == "block") {
            nothit = false;
            break
        }
    }
    if (nothit) {
        notfoundEle.style.display = "block";
    } else {
        notfoundEle.style.display = "none";
    }
}


function devinput(filtertype) {
    radioEle = document.getElementsByClassName("filters")[filtertype];
    radioEle.checked = true;
    searchsong();
}