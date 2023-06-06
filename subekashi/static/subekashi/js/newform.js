var songsRes, songGuessEles, imitateList = [];

async function firstLoad(basedir) {
    res = await fetch(basedir + "/api/song/?format=json");
    songsRes = await res.json();
    songGuessEles = document.getElementsByClassName("songGuess");
}


function setSubmitButton(isAvailable) {
    submitEle = document.getElementById("submit");
    submitEle.disabled = !isAvailable;
}


function checkExist() {
    titleValue = document.getElementById("title").value;
    channelValue = document.getElementById("channel").value;
    isExistEle = document.getElementById("isExist");
    fillFormButtonEle = document.getElementById("fillFormButton");
    
    song = songsRes.filter(song => song.title == titleValue).filter(song => song.channel == channelValue)
    if (song == []) {
        isExistEle.innerHTML = "<span id='ok'>この曲は登録されていません。</span>";
        fillFormButtonEle.style.display = "none";
    } else {
        song = song[0];
        if (("" in [song.url, song.lyrics, song.imitate]) || (song.isdraft) || (song.channel != "全てあなたの所為です。")) {
            isExistEle.innerHTML = "<span id=warning'>この曲の記事は作成途中です。</span>";
            fillFormButtonEle.style.display = "block";
        } else {
            isExistEle.innerHTML = "<span id=error'>この曲の記事は作成済みです。</span>";
            fillFormButtonEle.style.display = "none";
        }
    }
};


function fillForm () {
    urlEle = document.getElementById("url");
	urlEle.value = songsRes.url;
	document.getElementById("imitates").value = songsRes.imitate;
	document.getElementById("lyrics").value = songsRes.lyrics;
	document.getElementById("isorginal").checked = songsRes.isoriginal;
	document.getElementById("isjapanese").checked = songsRes.isjapanese;
	document.getElementById("isjoke").checked = songsRes.isjoke;
    if (urlEle.value == "削除済み") {
        document.getElementById("isdeleted").checked = true;
    }
}


function setImitates() {
    imitatesEle = document.getElementById("imitates");
    imitatesEle.value = imitateList.join();
}


function deleteImitate(id) {
    imitateEle = document.getElementById(`imitate${id}`);
    imitateEle.remove();
    imitateList = imitateList.filter(i => i != id);
    setImitates();
}


function appendImitate(song) {
    imitateEle = document.createElement('div');
    imitateInnerEle = `\
    <p>\
    <span class='channel'>\
        <i class='fas fa-user-circle'></i>\
        ${ song.channel }\
    </span>\
    <i class='fas fa-music'></i>\
    ${ song.title }\
    <span class='deleteSong' onclick="deleteImitate('${ song.id }')">\
        <i class='far fa-trash-alt'></i>\
        <a>削除</a>\
    </span>\
    </p>`
    imitateEle.innerHTML = imitateInnerEle;
    imitateEle.id = `imitate${song.id}`;
    imitatelistsEle = document.getElementById('imitatelists');
    imitatelistsEle.appendChild(imitateEle);

    if (imitateList.length == 0) {
        imitateList[0] = song.id;
    } else {
        imitateList.push(song.id);
    }

    setImitates();
}


function appendCategory(category_id) {
    subeanaSongs = songsRes.filter(song => song.channel == "全てあなたの所為です。");
    appendImitate(subeanaSongs[category_id]);
}


function appendSong(id) {
    subeanaSongs = songsRes.filter(song => song.id == id);
    appendImitate(subeanaSongs[0]);
    titleEle = document.getElementById("imitateTitle");
    titleEle.value = "";
}

function clickSong(id) {
    imitateTitleValue = document.getElementById("imitateTitle").value;
    imitateTitleValue.value = "";
    for (songGuessEle of songGuessEles) {
        songGuessEle.style.display = "none";
    }
    appendSong(id);
}


function searchSong() {
    imitateTitleValue = document.getElementById("imitateTitle").value;
    if (imitateTitleValue == "") {
        for (songGuessEle of songGuessEles) {
            songGuessEle.style.display = "none";
        }
    } else {
        for (songGuessEle of songGuessEles) {
            if (songGuessEle.id.match(imitateTitleValue) == null) {
                songGuessEle.style.display = "none";
            } else {
                songGuessEle.style.display = "block";
            }
        }
    }
}