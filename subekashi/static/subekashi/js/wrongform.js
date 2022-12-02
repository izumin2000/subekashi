function wrongform() {
    reasonEle = document.getElementById("reason");
    submitEle = document.getElementById("submit");
    if (reasonEle.value == "理由を選択してください") {
        submitEle.disabled = true;
    } else {
        submitEle.disabled = false;
    }
}