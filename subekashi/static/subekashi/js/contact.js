// 選択肢が掲載拒否かどうかの処理
const contenttype = document.getElementById("contact-type");
const replyEle = document.getElementById("reply");
contenttype.addEventListener("change", function () {
    const replyLabelEle = document.getElementById("reply-label");

    // 掲載拒否ならラベルに*を追加して入力必須にし、トーストを表示する。
    if (contenttype.value == "掲載拒否") {
        replyLabelEle.innerHTML = `連絡先<i class="fas fa-info-circle" onclick="showTutorial('reply')"></i><sup>*</sup>`;
        replyEle.required = true;
    } else {
        replyLabelEle.innerHTML = `連絡先<i class="fas fa-info-circle" onclick="showTutorial('reply')"></i>`;
        replyEle.required = false;
    }
});

// バリデーション
function checkButton() {
    const contentSubmitEle = document.getElementById("content-submit");
    const contentInfoEle = document.getElementById("contact-info");
    const detailtEle = document.getElementById("detail");

    // 選択肢が掲載拒否の場合、連絡先が空かどうか
    if ((contenttype.value == "掲載拒否") && (replyEle.value == "")) {
        contentSubmitEle.disabled = true;
        contentInfoEle.innerHTML = `<span class="error">本人のアカウントかどうかの確認のため、連絡先の項目が必須になります。</span>`;
        return;
    }
    
    // 選択肢か詳細が空なら
    if ((contenttype.value == "") || (detailtEle.value == "")) {
        contentSubmitEle.disabled = true;
        contentInfoEle.innerHTML = `<span class="error">選択肢と詳細を入力してください。</span>`
        return;
    }
    
    // validなら
    contentSubmitEle.disabled = false;
    contentInfoEle.innerHTML = `<span class="ok">送信できる状態です。</span>`
}


document.querySelectorAll('input, textarea, select').forEach(input => input.addEventListener('input', checkButton));
