var isfirstget = true;

async function isExistSong(basedir) {
    if (isfirstget) {
        res = await fetch(basedir + "/api/song/?format=json");
        songjson = await res.json();
        isfirstget = false;
    }

    formtitle = document.getElementById("title").value
    formchannel = document.getElementById("channel").value
    
    // 重複していないか検索
    song = null
    for (i of songjson) {
        if ((formchannel == i.channel) && (formtitle == i.title)) {
            song = i;
        }
    }
    console.log(song);    
    if (song != null) {     // 記事があった場合
        toastr.options = {
            "closeButton": true,
            "debug": false,
            "newestOnTop": false,
            "progressBar": true,
            "positionClass": "toast-bottom-right",
            "preventDuplicates": false,
            "onclick": null,
            "timeOut": "10000",
            "extendedTimeOut": "0",
            "showEasing": "swing",
            "hideEasing": "linear",
        }
        
        lack_columns = [];
        if (song.channel) {
            lack_columns.push("作者");
        }
        if (song.url) {
            lack_columns.push("URL");
        }
        if (song.imitate) {
            lack_columns.push("模倣");
        } else {
            if (song.isoriginal) {
                lack_columns.push("模倣");
            }
        }
        if (song.lyrics) {
            lack_columns.push("歌詞");
        }
        if ((lack_columns.length == 4) || (song.channel == "全てあなたの所為です。")) {
            toastr.warning(song.channel + "の" + song.title + "の情報は全て登録済です。")
        } else if (lack_columns.length > 0) {
            toastr.warning(song.title + "の情報のうち、" + lack_columns.join("・") + "の情報は既に登録済です。")
        }
    }
};


function newform() {
    titleValue = document.getElementById("title").value;
    channelValue = document.getElementById("channel").value;
    // appendimitateDisalbe = document.getElementById("appendimitate").disabled;
    submitEle = document.getElementById("submit");
    if ((titleValue != "") && (channelValue != "") && !(appendimitateDisalbe)) {
        submitEle.disabled = false;
    } else {
        submitEle.disabled = true;
    }  
}


function appendimitatef() {
    imitateEle = document.getElementById("imitate");
    imitateimitatedivEle = document.getElementById("imitateimitatediv");
    if (imitateEle.value == "模倣曲模倣") {
        imitateimitatedivEle.style.display = "block";
    } else {
        imitateimitatedivEle.style.display = "none";
    }
}


function deleteimitatef() {
    imitatesEle = document.getElementById("imitates");
    
    var lastEle = imitatesEle.lastElementChild;
    while (lastEle.id != ("imitateimitatediv" + String(imitateNums - 1))) {
        imitatesEle.lastElementChild.remove();
       var lastEle = imitatesEle.lastElementChild;
    }

    if (imitateNums) {
        imitatebrEle = document.createElement("br");
        imitateEle.appendChild(imitatebrEle);
    }

    imitateNums -= 1;

    appendimitateEle = document.getElementById("appendimitate");
    appendimitateEle.innerText = "模倣" + String(imitateNums + 1) + "の追加";
    appendimitateEle.disabled = false;

    deleteimitateEle = document.getElementById("deleteimitate");
    deleteimitateEle.innerText = "模倣" + String(imitateNums) + "の削除";

    if (imitateNums == 1) {
        deleteimitateEle.style.display = "none";
    } else {
        deleteimitateEle.style.display = "inline-block";
    }

    imitatenumsEle = document.getElementById("imitatenums");
    imitatenumsEle.value = imitateNums;
}


function titleinput(title) {
    titleEle = document.getElementById("title");
    titleEle.value = title;
    for (songEle of songEles) {
        songEle.parentElement.style.display = "none";
    }

    makeform();
}


function searchsong() {
    titleEle = document.getElementById("title");
    title = titleEle.value;
    if (title == "") {
        for (songEle of songEles) {
            songEle.parentElement.style.display = "none";
        }
    } else {
        for (songEle of songEles) {
            if (songEle.id.match(title) == null) {
                songEle.parentElement.style.display = "none";
            } else {
                songEle.parentElement.style.display = "block";
            }
        }
    }

    makeform();
}