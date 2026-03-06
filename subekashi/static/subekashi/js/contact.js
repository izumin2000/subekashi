// バリデーション
function checkButton() {
    const contentSubmitEle = document.getElementById("content-submit");
    const contentInfoEle = document.getElementById("contact-info");
    const detailtEle = document.getElementById("detail");
    
    // 選択肢か詳細が空なら
    if ((categoryEle.value == "") || (detailtEle.value.trim() == "")) {
        contentSubmitEle.disabled = true;
        contentInfoEle.innerHTML = `<span class="error">選択肢と詳細を入力してください。</span>`
        return;
    }
    
    // validなら
    contentSubmitEle.disabled = false;
    contentInfoEle.innerHTML = `<span class="ok">送信できる状態です。</span>`
}


document.querySelectorAll('input, textarea, select').forEach(input => input.addEventListener('input', checkButton));