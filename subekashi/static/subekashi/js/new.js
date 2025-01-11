var songJson, songResult, imitateList = [], isGetQuery = false;


window.addEventListener('load', async function () {
    songJson = await getJson("song");
    const currentUrl = window.location.href;
    const url = new URL(currentUrl);
    const id = url.searchParams.get('id');
    if (id) {
        songResult = songJson.filter(song => song.id == id)[0];
        document.getElementById("title").value = songResult.title;
        document.getElementById("channel").value = songResult.channel;
        fillForm();
        setSubmitButton("_", "_");
    }

    isGetQuery = Boolean(id)
    checkExist();
});

// TODO requiredを利用
function setSubmitButton(titleValue, channelValue) {
    submitEle = document.getElementById("newsubmit");
    if ((titleValue == "") || (channelValue == "")) {
        submitEle.disabled = true;
    } else {
        submitEle.disabled = false;
    }
}

// TODO checkValidityを利用
document.getElementById('reason').addEventListener('input', () => {
    reasonValue = document.getElementById("reason").value;
    deleteEle = document.getElementById("deletesubmit");

    if (!songResult) {
        return;
    }

    deleteEle.disabled = (reasonValue == "") || (songResult.length == 0);
})

function checkExist() {
    titleValue = document.getElementById("title").value;
    document.getElementById("titleDelete").value = titleValue;
    channelValue = document.getElementById("channel").value;
    document.getElementById("channelDelete").value = channelValue;
    isExistEle = document.getElementById("isExist");
    fillFormButtonEle = document.getElementById("fillFormButton");

    if ((titleValue != "") && (channelValue != "")) {
        channelValue = channelValue.replace(/\//g, "╱");
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

function deleteImitate(imitateId) {
    imitateEle = document.getElementById(`imitate-${imitateId}`);
    imitateEle.remove();
    imitateList = imitateList.filter(id => id != imitateId);
    setImitates();
}

function appendImitate(song) {
    imitate = `
    <div id="imitate-${ song.id }">
        <p>
            <span class='channel'>
                <i class='fas fa-user-circle'></i>
                ${ song.channel }
            </span>
            <i class='fas fa-music'></i>
            ${ song.title }
            <span class='deleteSong' onclick="deleteImitate(${ song.id })">
                <i class='far fa-trash-alt'></i>
                <a>削除</a>
            </span>
        </p>
    </div>
    `

    imitatelistsEle = document.getElementById('imitatelists');
    imitatelistsEle.appendChild(stringToHTML(imitate));

    if (imitateList.length == 0) {
        imitateList[0] = song.id;
    } else {
        imitateList.push(song.id);
    }

    setImitates();
}

function categoryClick(song) {
    appendImitate(song);
}

function renderSongGuesser() {
    // 以前のリクエストが存在する場合、そのリクエストをキャンセルする
    if (songGuesserController) {
        songGuesserController.abort();
    }

    songGuesserController = new AbortController();
    imitateTitle = document.getElementById("imitateTitle").value;
    getSongGuessers(imitateTitle, "song-guesser", songGuesserController.signal);
}

function songGuesserClick(id) {
    document.getElementById("imitateTitle").value = "";
    renderSongGuesser();
    imitateSong = songJson.filter(song => song.id == id)[0];
    appendImitate(imitateSong);
};

// フォームに変更があったかを検知
isFormDirty = false;
document.querySelectorAll('input, textarea:not(#reason)').forEach((input) => {
    input.addEventListener('change', () => {
        isFormDirty = true;
    });
});

// ページを離れる前に警告を表示
window.addEventListener('beforeunload', (event) => {
    if (isFormDirty) {
        event.preventDefault();
    }
});

// フォームが送信される際にisFormDirtyをリセット
document.querySelector('form').addEventListener('submit', (event) => {
    isFormDirty = false;
});