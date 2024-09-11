async function setScore(id, score) {
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


function copyBest() {
    aiInstEles = document.getElementsByClassName("ai-ins");
    copyText = ""
    for (aiInstEle of aiInstEles) {
        isBest = aiInstEle.children[1].children[8].checked;
        if (isBest) {
            copyText += aiInstEle.children[0].innerText + "\n";
        }
    }
    
    copyMessageEle = document.getElementById("copy-message");
    if (!copyText) {
        copyMessageEle.innerHTML = '<span class="warning">コピーする行がありません。</span>'
    } else if (Boolean(navigator.clipboard)) {
        navigator.clipboard.writeText(copyText);
        copyMessageEle.innerHTML = '<span class="ok">コピーしました。</span>'
    } else {
        copyMessageEle.innerHTML = '<span class="error">エラーが発生しました。</span>'
    }
}