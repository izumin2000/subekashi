async function setscore(id, score) {
    res = await fetch(
        baseURL() + "/api/ai/" + id + "/?format=json",
        {
            method: "PUT",
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(
                {
                    "score": score,
                }
            )
        }
    );
}


function devInput(id, score) {
    for (s = 1; s <= 5; s++) {
        radioEle = document.getElementById(String(id) + String(s));
        radioEle.checked = false;
    }
    radioEle = document.getElementById(String(id) + String(score));
    radioEle.checked = true;
    setscore(id, score);
}


function copygood() {
    checkgoodEles = document.getElementsByClassName("lyricdiv");
    copytext = ""
    for (checkgoodEle of checkgoodEles) {
        isbest = checkgoodEle.children[1].children[0].checked;
        if (isbest) {
            copytext += checkgoodEle.children[0].innerText + "\n";
        }
    }
    
    copyresultEle = document.getElementById("copyresult");
    if (Boolean(navigator.clipboard)) {
        navigator.clipboard.writeText(copytext);
        copyresultEle.innerText = "コピーしました。"
    } else {
        copyresultEle.innerText = "エラーが発生しました。"
    }
}