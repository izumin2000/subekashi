var songjson, songEles;

async function getSong(baseURL) {
    if (!songEles) {
        res = await fetch(baseURL + "/api/song/?format=json");
        songjson = await res.json();
        songEles = document.getElementsByClassName("songcard");
    }
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
        categoryId = 0
    } else if (imitateimitateEle) {
        if (imitateimitateEle.value) {
            category = imitateimitateEle.value
            category_find = songjson.find((v) => v.title == category)
            if (category_find) {
                categoryId = String(category_find.id);
            } else {
                categoryId = -1        // 模倣曲模倣が見つからない場合
            }
        } else {
            categoryId = 0
        }
    } else {
        category_find = songjson.find((v) => v.title == category)
        if (category_find) {
            categoryId = String(category_find.id);
        } else {
            categoryId = 0
        }
    }

    for (songEle of songEles) {
        
        channel = document.getElementById("channel").value;
        title = document.getElementById("title").value;
        lyrics = document.getElementById("lyrics").value;
        styledisplay = "block";
        if (channel && (songjson[i]["channel"].match(channel) == null)) {
            styledisplay = "none";
        }
        if (title && (songjson[i]["title"].match(title) == null)) {
            styledisplay = "none";
        }
        if (lyrics && (songjson[i]["lyrics"].match(lyrics) == null)) {
            styledisplay = "none";
        }

        if (!songjson[i]["imitate"].split(",").includes(categoryId) && categoryId) {
            styledisplay = "none";
        }
        
        if (categoryId == -1) {        // 模倣曲模倣が見つからない場合
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
        
        if (filtrtEles[3].checked) {
            if (!songjson[i]["isoriginal"]) {
                styledisplay = "none";
            }
        }
        
        if (filtrtEles[4].checked) {
            if (!songjson[i]["isjoke"]) {
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
    if (filtertype >= 3) {
        radioEle.checked = !radioEle.checked;
    } else {
        radioEle.checked = true;
    }
    searchsong();
}


function checkboxinput(filtertype) {
    if (filtertype == 3) {
        checkboxEle = document.getElementById("original");
    } else if (filtertype == 4) {
        checkboxEle = document.getElementById("joke");
    }
    checkboxEle.checked = !checkboxEle.checked;
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