// 取り消し理由が空の間は、削除を取り消すボタンを押せないようにする（削除ページの削除ボタンと同じ）
const restoreReasonEle = document.getElementById("restore-reason");
const restoreSubmitEle = document.getElementById("song-restore-submit");

function checkRestoreForm() {
    restoreSubmitEle.disabled = restoreReasonEle.value.trim() === "";
}

// ロックされた曲・URLが重複している曲は、取り消し理由の入力欄が無い
if (restoreReasonEle && restoreSubmitEle) {
    restoreReasonEle.addEventListener("input", checkRestoreForm);
    // ブラウザの戻る・再読み込みで、入力欄の内容が復元された場合にも合わせる
    window.addEventListener("pageshow", checkRestoreForm);
    checkRestoreForm();
}
