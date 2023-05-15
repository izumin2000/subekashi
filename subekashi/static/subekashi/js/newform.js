var isfirstget = true;
var imitateNums = 1;

async function isExistSong(basedir) {
    if (isfirstget) {
        res = await fetch(basedir + "/api/song/?format=json");
        songjson = await res.json();
        isfirstget = false;
    }

    formtitle = document.getElementById("title").value
    song = songjson.find((v) => v.title == formtitle);      // jsonから歌詞を検索
    
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
            toastr.warning(song.title + "の情報は全て登録済です。")
        } else if (lack_columns.length > 0) {
            toastr.warning(song.title + "の情報のうち、" + lack_columns.join("・") + "の情報は既に登録済です。")
        }
    }
};


function newform(imitateNumAt) {
    appendimitateEle = document.getElementById("appendimitate");

    // 模倣曲模倣がvalidか確認
    imitateimitatevalid = true;
    imitateimitateexist = false;
    for (let i = 1; i <= imitateNums + 1; i++) {
        imitateimitateEle = document.getElementById("imitateimitate" + i);
        if (imitateimitateEle != null) {
            imitateimitateexist = true;
            if (imitateimitateEle.value == "") {
                appendimitateEle.disabled = true;
                imitateimitatevalid = false;
            }
        }
    }
    if (imitateimitatevalid && imitateimitateexist) {
        appendimitateEle.disabled = false;
    }

    // 模倣曲模倣の曲名をinputするformの表示・非表示の切り替え
    if (imitateNumAt != 0) {      // 模倣曲模倣の入力の場合はこのブロックを実行しない
        imitateValue = document.getElementById("imitate" + imitateNumAt).value;
        if (imitateValue == "模倣曲模倣") {
            imitateimitateEle = document.createElement("input");
            imitateimitateEle.type = "text";
            imitateimitateEle.placeholder = "曲名";
            imitateimitateEle.id = "imitateimitate" + imitateNumAt;
            imitateimitateEle.name = "imitateimitate" + imitateNumAt;
            imitateimitateEle.setAttribute("oninput" ,"newform(0)");

            imitateimitatedevEle = document.getElementById("imitateimitatediv" + imitateNumAt);
            imitateimitatedevEle.appendChild(imitateimitateEle);

            appendimitateEle.disabled = true;
        } else {
            imitateimitatedevEle = document.getElementById("imitateimitatediv" + imitateNumAt);
            imitateValueId = document.getElementById("imitateimitate" + imitateNumAt);
            if (imitateValueId) {
                imitateimitatedevEle.removeChild(imitateValueId);
            }

            if (imitateValue == "選択してください") {
                appendimitateEle.disabled = true;
            } else {
                appendimitateEle.disabled = false;
            }
        }
    }

    // form全体がvalidか確認
    titleValue = document.getElementById("title").value;
    channelValue = document.getElementById("channel").value;
    appendimitateDisalbe = document.getElementById("appendimitate").disabled;
    submitEle = document.getElementById("submit");
    if ((titleValue != "") && (channelValue != "") && !(appendimitateDisalbe)) {
        submitEle.disabled = false;
    } else {
        submitEle.disabled = true;
    }  
}


function appendimitatef() {
    imitateNums += 1;

    imitatelabelEle = document.createElement("label");
    imitatelabelEle.innerHTML = "模倣" + imitateNums + "*";
    
    imitateselectEle = document.createElement("select");
    imitateselectEle.id = "imitate" + imitateNums;
    imitateselectEle.name = "imitate" + imitateNums;
    imitateselectEle.setAttribute("oninput", "newform(" + imitateNums + ")");
    imitateselectEle.innerHTML = "<option>選択してください</option><option>.模倣</option><option>..模倣</option><option>教育模倣</option><option>アブジェ模倣</option><option>...模倣</option><option>表\/裏模倣</option><option>名の無い星が空に堕ちたら模倣</option><option>エヌ模倣</option><option>K²模倣</option><option>オリジナル模倣</option><option>模倣曲模倣</option>";

    imitatedivEle = document.createElement("div");
    imitatedivEle.setAttribute("class", "imitateimitatediv");
    imitatedivEle.id = "imitateimitatediv" + imitateNums;
    
    imitatebrEle = document.createElement("br");

    imitateEle = document.getElementById("imitates");
    imitateEle.appendChild(imitatelabelEle);
    imitateEle.appendChild(imitateselectEle);
    imitateEle.appendChild(imitatedivEle);
    imitateEle.appendChild(imitatebrEle);

    appendimitateEle = document.getElementById("appendimitate");
    appendimitateEle.innerText = "模倣" + String(imitateNums + 1) + "の追加";
    appendimitateEle.disabled = true;
    deleteimitateEle = document.getElementById("deleteimitate");
    deleteimitateEle.innerText = "模倣" + String(imitateNums) + "の削除";

    if (imitateNums == 1) {
        deleteimitateEle.style.display = "none";
    } else {
        deleteimitateEle.style.display = "inline-block";   
    }

    newform(imitateNums);
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