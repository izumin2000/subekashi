var songJson, songResult, songGuessEles, imitateList = [], isGetQuery = false;

async function firstLoad(songId) {
    res = await fetch(baseURL() + "/api/song/?format=json");
    songJson = await res.json();

    if (songId != "None") {
        songResult = songJson.filter(song => song.id == songId)[0];
        document.getElementById("title").value = songResult.title;
        document.getElementById("channel").value = songResult.channel;
        fillForm();
        setSubmitButton("_", "_");
        document.getElementById("songid").value = Number(songId);
    }
    
    songGuessEles = document.getElementsByClassName("songGuess");
    isGetQuery = songId != "None"
    autotextarea();
    checkExist();
}


function setSubmitButton(titleValue, channelValue) {
    submitEle = document.getElementById("newsubmit");
    if ((titleValue == "") || (channelValue == "")) {
        submitEle.disabled = true;
    } else {
        submitEle.disabled = false;
    }
}


function setDeleteButton() {
    reasonValue = document.getElementById("reason").value;
    deleteEle = document.getElementById("deletesubmit");
    if (songResult) {
        if ((reasonValue == "") || (songResult.length == 0)) {
            deleteEle.disabled = true;
        } else {
            deleteEle.disabled = false;
        }
    } else {
        deleteEle.disabled = true;
    }
}


function checkExist() {
    titleValue = document.getElementById("title").value;
    document.getElementById("titleDelete").value = titleValue;
    channelValue = document.getElementById("channel").value;
    document.getElementById("channelDelete").value = channelValue;
    isExistEle = document.getElementById("isExist");
    fillFormButtonEle = document.getElementById("fillFormButton");

    if ((titleValue != "") && (channelValue != "")) {
        titleValue = titleValue.replace(/\//g, "╱");
        songResult = songJson.filter(song => song.title == titleValue).filter(song => song.channel == channelValue);
        if (songResult.length == 0) {
            isExistEle.innerHTML = "<span class='ok'>この曲は登録されていません。</span>";
            fillFormButtonEle.style.display = "none";
        } else {
            songResult = songResult[0];
            if (isCompleted(songResult)) {
                isExistEle.innerHTML = "<span class='error'>この曲の記事は作成済みです。</span>";
                fillFormButtonEle.style.display = "block";
            } else {
                isExistEle.innerHTML = "<span class='warning'>この曲の記事は作成途中です。</span>";
                fillFormButtonEle.style.display = "block";
            }
        }
    } else {
        isExistEle.innerHTML = "";
        fillFormButtonEle.style.display = "none";
    }
    
    if (isGetQuery) {
        isExistEle.innerHTML = "<span class='warning'>曲の記事の上書きをしています。</span>";
        fillFormButtonEle.style.display = "none";
    }

    setSubmitButton(titleValue, channelValue);
    setDeleteButton();
};


function fillForm() {
    if (songResult.url == "非公開") {
        document.getElementById("isdeleted").checked = true;
    } else {
        document.getElementById("url").value = songResult.url;
    }
    for (imitateId of imitateList) {
        deleteImitate(imitateId);
    }
    if (songResult.imitate) {
        for (imitateId of songResult.imitate.split(",")) {
            song = songJson.filter(song => song.id == imitateId)[0];
            appendImitate(song);
        }
    }
    document.getElementById("lyrics").value = songResult.lyrics;
    document.getElementById("isorginal").checked = songResult.isoriginal;
    document.getElementById("isjoke").checked = songResult.isjoke;
    document.getElementById("isinst").checked = songResult.isinst;
    document.getElementById("issubeana").checked = songResult.issubeana;
    document.getElementById("isdraft").checked = songResult.isdraft;
    document.getElementById("isdeleted").checked = songResult.isdeleted;
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


function appendCategory(categoryId) {
    subeanaSongs = songJson.filter(song => song.channel == "全てあなたの所為です。");
    appendImitate(subeanaSongs[categoryId]);
}


function appendSong(id) {
    subeanaSongs = songJson.filter(song => song.id == id);
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
            if (songGuessEle.dataset.title.includes(imitateTitleValue)) {
                songGuessEle.style.display = "block";
            } else {
                songGuessEle.style.display = "none";
            }
        }
    }
}

// フォームに変更があったかを検知
isFormDirty = false;
document.querySelectorAll('input, textarea').forEach((input) => {
    input.addEventListener('change', () => {
        isFormDirty = true;
    });
});

// フォームが送信される際にisFormDirtyをリセット
document.querySelector('form').addEventListener('submit', (event) => {
    isFormDirty = false;
});

// ページを離れる前に警告を表示
window.addEventListener('beforeunload', (event) => {
    if (isFormDirty) {
        event.preventDefault();
    }
});