var songJson, songResult, subeanaSongs, songEles;
var isLoaded = false;

async function firstLoad(query) {
    res = await fetch(baseURL() + "/api/song/?format=json");
    songJson = await res.json();
    subeanaSongs = songJson.filter(song => song.channel == "全てあなたの所為です。");
    songEles = document.getElementsByClassName("songcard");

    query = query.split(",")
    if (query[0]) ddocument.getElementById("title").value = query[0];
    if (query[1]) ddocument.getElementById("channel").value = query[1];
    if (query[2]) document.getElementById("lyrics").value = query[2];

    radioEles = document.getElementsByClassName("filters");
    for (radioEle of radioEles) {
        if (radioEle.value != "issubeana") {
            radioEle.checked = false;
        }
    }
    if (query[3] != "") {
        radioEles[Number(query[3])].checked = true;
    }

    isLoaded = true;
    searchSong();
}


function songFilter(key, value) {
    if (value) {
        songResult = songResult.filter(song => Boolean(song[key]));
        songResult = songResult.filter(song => song[key].match(value));
    }
    return songResult;
}


function searchSong() {
    if (!isLoaded) {
        return
    }

    songResult = songJson.concat();
    channelValue = document.getElementById("channel").value;
    titleValue = document.getElementById("title").value;
    lyricsValue = document.getElementById("lyrics").value;

    filterEles = Array.from(document.getElementsByClassName("filters")).filter(filterEle => filterEle.checked);
    filterL = (filterEles.map(filterEle => filterEle.value));

    // issubeanaとisxxが両方選択されている場合は無視
    if (filterL.includes("issubeana") && filterL.includes("isxx")) {
        filterL.splice(filterL.indexOf("issubeana"), 1);
        filterL.splice(filterL.indexOf("isxx"), 1);
    }

    categoryValue = document.getElementById("category").value;
    if (categoryValue != "全ての模倣") {
        categoryId = subeanaSongs.filter(song => song.title == categoryValue.slice(0, -2)).map(song => song.id)[0];
        songResult = songFilter("imitate", String(categoryId));
    }

    titleValue = titleValue.replace(/\//g, "╱");

    songResult = songFilter("channel", channelValue);
    songResult = songFilter("title", titleValue);
    songResult = songFilter("lyrics", lyricsValue);
    
    const filters = {
        "isCompleted": song => !isCompleted(song),
        "isoriginal": song => song.isoriginal,
        "isjoke": song => song.isjoke,
        "isinst": song => song.isinst,
        "issubeana": song => song.issubeana,
        "isxx": song => !song.issubeana,
    };
    
    filterL.forEach(filter => {
        if(filters[filter]) songResult = songResult.filter(filters[filter]);
    });

    songResultId = songResult.map(song => song.id);
    Array.from(songEles).map(songEle => songEle.style.display = "none");
    songResultId.map(songId => document.getElementById("song" + songId).style.display = "block");

    notfoundEle = document.getElementById("notfound");     
    if (songResult.length) {
        notfoundEle.style.display = "none";
    } else {
        notfoundEle.style.display = "block";
    }
}


function devInput(filtertype) {
    radioEle = document.getElementsByClassName("filters")[filtertype];
    radioEle.checked = !radioEle.checked;
    searchSong();
}