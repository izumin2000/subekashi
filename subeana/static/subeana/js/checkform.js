var isfirstget = true;
var isfirstinfo = true;
var imitateNums = 1;

async function checksong(basedir) {
    if (isfirstget) {
        res = await fetch(basedir + "/subeana/api/song/?format=json");
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
            "timeOut": "5000",
            "extendedTimeOut": "0",
            "showEasing": "swing",
            "hideEasing": "linear",
        }
        
        if (song.lyrics == "") {
            toastr.info(song.title + "の記事は登録済ですが、歌詞が登録されていません")
        } else {
            toastr.info(song.title + "の歌詞は登録済です。")
        }
        if (isfirstinfo) {
            toastr.info("送信ボタンを押すと元の記事を上書きします")
            isfirstinfo = false
        }
    }
};


function checkform(imitateNumAt) {
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
            imitateimitateEle.setAttribute("oninput" ,"checkform(0)");

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
    console.log((titleValue != "") , (channelValue != "") , !(appendimitateDisalbe));
    if ((titleValue != "") && (channelValue != "") && !(appendimitateDisalbe)) {
        submitEle.disabled = false;
    } else {
        submitEle.disabled = true;
    }  
}


function appendimitatef() {
    imitateNums += 1;

    imitatelabelEle = document.createElement("label");
    imitatelabelEle.innerHTML = "模倣曲" + imitateNums + "*";
    
    imitateselectEle = document.createElement("select");
    imitateselectEle.id = "imitate" + imitateNums;
    imitateselectEle.name = "imitate" + imitateNums;
    imitateselectEle.setAttribute("oninput", "checkform(" + imitateNums + ")");
    imitateselectEle.innerHTML = "<option>選択してください</option><option>原曲</option><option>.模倣</option><option>..模倣</option><option>教育模倣</option><option>アブジェ模倣</option><option>...模倣</option><option>表裏模倣</option><option>名の無い星が空に堕ちたら模倣</option><option>エヌ模倣</option><option>オリジナル模倣</option><option>模倣曲模倣</option>";

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
    appendimitateEle.innerText = "模倣曲" + String(imitateNums + 1) + "の追加";
    appendimitateEle.disabled = true;
    deleteimitateEle = document.getElementById("deleteimitate");
    deleteimitateEle.innerText = "模倣曲" + String(imitateNums) + "の削除";

    if (imitateNums == 1) {
        deleteimitateEle.style.display = "none";
    } else {
        deleteimitateEle.style.display = "inline-block";   
    }

    checkform(imitateNums);
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
    appendimitateEle.innerText = "模倣曲" + String(imitateNums + 1) + "の追加";
    appendimitateEle.disabled = false;

    deleteimitateEle = document.getElementById("deleteimitate");
    deleteimitateEle.innerText = "模倣曲" + String(imitateNums) + "の削除";

    if (imitateNums == 1) {
        deleteimitateEle.style.display = "none";
    } else {
        deleteimitateEle.style.display = "inline-block";
    }
}