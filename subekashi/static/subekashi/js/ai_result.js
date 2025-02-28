// 評価された点数を送信
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

// 最高の行をコピー
function copyBest() {
    // コピーするテキストを抽選
    const aiInstEles = document.getElementsByClassName("ai-ins");
    copyText = ""
    for (const aiInstEle of aiInstEles) {
        isBest = aiInstEle.children[1].children[8].checked;
        if (isBest) {
            copyText += aiInstEle.children[0].innerText + "\n";
        }
    }
    
    // コピーできない環境なら
    if (!Boolean(navigator.clipboard)) {
        showToast("error", "エラーが発生しました。");
        return;
    }

    // 最高評価の歌詞が無いのなら
    if (!copyText) {
        showToast("warning", "コピーする行がありません。");
        return;
    }

    // コピー処理
    navigator.clipboard.writeText(copyText);
    showToast("ok", "コピーしました。");
}

showToast("ok", "歌詞を生成しました。");