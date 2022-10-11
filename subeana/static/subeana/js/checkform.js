var isfirstget = true;
var isfirstinfo = true;
var imitateNum = 1;

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


function checkimitateimitate(imitateNum) {
    formimitate = document.getElementById("imitate" + imitateNum).value;
    if (formimitate == "模倣曲模倣") {
        imitateimitateEle = document.createElement("input");
        imitateimitateEle.type = "text";
        imitateimitateEle.placeholder = "曲名";
        imitateimitateEle.id = "imitateimitate" + imitateNum;
        imitateimitateEle.name = "imitateimitate" + imitateNum;
        imitateimitateEle.onclick = "checkimitateimitatecheck(" + imitateNum + ")";

        imitateimitatedevEle = document.getElementById("imitateimitatediv" + imitateNum);
        imitateimitatedevEle.appendChild(imitateimitateEle);
    } else {
        imitateimitatedevEle = document.getElementById("imitateimitatediv" + imitateNum);
        formimitateId = document.getElementById("imitateimitate" + imitateNum);
        if (formimitateId) {
            imitateimitatedevEle.removeChild(formimitateId);
        }
    }
}

function appendimitatef() {
    imitateNum += 1;

    imitatelabelEle = document.createElement("label");
    imitatelabelEle.innerHTML = "模倣曲" + imitateNum + "*";
    
    imitateselectEle = document.createElement("select");
    imitateselectEle.id = "imitate" + imitateNum;
    imitateselectEle.name = "imitate" + imitateNum;
    imitateselectEle.setAttribute("oninput", "checkform(); checkimitateimitate(" + imitateNum + ");");
    imitateselectEle.innerHTML = "<option>選択してください</option><option>原曲</option><option>.模倣</option><option>..模倣</option><option>教育模倣</option><option>アブジェ模倣</option><option>...模倣</option><option>表裏模倣</option><option>名の無い星が空に堕ちたら模倣</option><option>エヌ模倣</option><option>オリジナル模倣</option><option>模倣曲模倣</option>";

    imitatedivEle = document.createElement("div");
    imitatedivEle.setAttribute("class", "imitateimitatediv");
    imitatedivEle.id = "imitateimitatediv" + imitateNum;
    
    imitatebrEle = document.createElement("br");

    imitateEle = document.getElementById("imitates");
    imitateEle.appendChild(imitatelabelEle);
    imitateEle.appendChild(imitateselectEle);
    imitateEle.appendChild(imitatedivEle);
    imitateEle.appendChild(imitatebrEle);

    appendimitateEle = document.getElementById("appendimitate");
    appendimitateEle.innerText = "模倣曲" + String(imitateNum + 1) + "の追加";
    appendimitateEle.disabled = true;
    deleteimitateEle = document.getElementById("deleteimitate");
    deleteimitateEle.innerText = "模倣曲" + String(imitateNum) + "の削除";

    if (imitateNum == 1) {
        deleteimitateEle.style.display = "none";
    } else {
        deleteimitateEle.style.display = "inline-block";   
    }
}

function deleteimitatef() {
    imitatesEle = document.getElementById("imitates");
    
    var lastEle = imitatesEle.lastElementChild;
    while (lastEle.id != ("imitateimitatediv" + String(imitateNum - 1))) {
        imitatesEle.lastElementChild.remove();
       var lastEle = imitatesEle.lastElementChild;
    }

    if (imitateNum) {
        imitatebrEle = document.createElement("br");
        imitateEle.appendChild(imitatebrEle);
    }

    imitateNum -= 1;

    appendimitateEle = document.getElementById("appendimitate");
    appendimitateEle.innerText = "模倣曲" + String(imitateNum + 1) + "の追加";
    appendimitateEle.disabled = false;

    deleteimitateEle = document.getElementById("deleteimitate");
    deleteimitateEle.innerText = "模倣曲" + String(imitateNum) + "の削除";

    if (imitateNum == 1) {
        deleteimitateEle.style.display = "none";
    } else {
        deleteimitateEle.style.display = "inline-block";
    }
}

function checkform() {
    formchannel = document.getElementById("channel").value;
    appendimitateEle = document.getElementById("appendimitate");
    formimitate = document.getElementById("imitate" + imitateNum).value;
    formsubmit = document.getElementById("submit");

    if (formimitate == "選択してください") {
        appendimitateEle.disabled = true;
    } else {
        appendimitateEle.disabled = false;
    }

    if ((formchannel != "") && (formimitate != "選択してください")) {
        formsubmit.disabled = false;
    } else {
        formsubmit.disabled = true;
    }
}