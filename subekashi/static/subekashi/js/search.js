var songJson, songResult, subeanaSongs, songEles;

async function firstLoad(baseURL, query) {
    res = await fetch(baseURL + "/api/song/?format=json");
    songJson = await res.json();
    subeanaSongs = songJson.filter(song => song.channel == "全てあなたの所為です。");
    songEles = document.getElementsByClassName("songcard");

    query = query.split(",")
    document.getElementById("title").value = query[0];
    document.getElementById("channel").value = query[1];
    document.getElementById("lyrics").value = query[2];
    if (query[3] != "") {
        devInput(Number(query[3]));
    }

    document.getElementById("loading").style.display = "none";
    document.getElementById("searchform").style.display = "block";

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
    songResult = songJson.concat();
    channelValue = document.getElementById("channel").value;
    titleValue = document.getElementById("title").value;
    lyricsValue = document.getElementById("lyrics").value;

    filterEles = Array.from(document.getElementsByClassName("filters")).filter(filterEle => filterEle.checked);
    filterL = (filterEles.map(filterEle => filterEle.value));

    categoryValue = document.getElementById("category").value;
    if (categoryValue != "全ての模倣") {
        categoryId = subeanaSongs.filter(song => song.title == categoryValue.slice(0, -2)).map(song => song.id)[0];
        songResult = songFilter("imitate", String(categoryId));
    }

    titleValue = titleValue.replace(/\//g, "╱");

    songResult = songFilter("channel", channelValue);
    songResult = songFilter("title", titleValue);
    songResult = songFilter("lyrics", lyricsValue);
    
    if (filterL.includes("1")) {
        songResult = songResult.filter(song => !isCompleted(song));
    }
    if (filterL.includes("2")) {
        songResult = songResult.filter(song => song.isdraft);
    }
    if (filterL.includes("3")) {
        songResult = songResult.filter(song => song.isoriginal);
    }
    if (filterL.includes("4")) {
        songResult = songResult.filter(song => song.isjoke);
    }

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
    if (filtertype >= 3) {
        radioEle.checked = !radioEle.checked;
    } else {
        radioEle.checked = true;
    }
    searchSong();
}