var songjson, songEles;

async function getSong(basedir) {
    res = await fetch(basedir + "/subeana/api/song/?format=json");
    songjson = await res.json();
        songEles = document.getElementsByClassName("songcard");
}

function categoryform() {
    categoryEle = document.getElementById("category");
    if (categoryEle.value == "模倣曲模倣") {
        categorysecEle = document.getElementById("categorysec");
        
        imitateimitateEle = document.createElement("input");
        imitateimitateEle.type = "text";
        imitateimitateEle.placeholder = "曲名";
        imitateimitateEle.id = "imitateimitate";
        imitateimitateEle.name = "imitateimitate";
        imitateimitateEle.setAttribute("oninput" ,"searchsong()");
        
        categorysecEle.appendChild(imitateimitateEle);
    } else {
        imitateimitateEle = document.getElementById("imitateimitate");
        if (imitateimitateEle) {
            categorysecEle.removeChild(imitateimitateEle);
        }
    }
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
    imitateimitateEle = document.getElementById("imitateimitate");
    if (category == "全ての") {
        category_id = 0
    } else if (imitateimitateEle) {
        if (imitateimitateEle.value) {
            category = imitateimitateEle.value
            category_find = songjson.find((v) => v.title == category)
            if (category_find) {
                category_id = String(category_find.id);
            } else {
                category_id = -1        // 模倣曲模倣が見つからない場合
            }
        } else {
            category_id = 0
        }
    } else {
        category_find = songjson.find((v) => v.title == category)
        if (category_find) {
            category_id = String(category_find.id);
        } else {
            category_id = 0
        }
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
        
        if (category_id == -1) {        // 模倣曲模倣が見つからない場合
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

function categoryinput(category) {
    if (category == "オリジナル") {
        searchEle = document.getElementById("search");
        searchEle.value = "全てあなたの所為です。";
    } else {
        categoryEle = document.getElementById("category");
        categoryEle.value = category + "模倣";
    }
    searchsong();
}