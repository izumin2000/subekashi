// 読み込み時に最初のdetailを展開
window.addEventListener("DOMContentLoaded", () => {
    const firstDetail = document.querySelector("details");
    firstDetail.open = true;
});

// historyを更新するリロード
function reloadPage() {
    const newUrl = location.pathname + '?reload=' + Date.now();
    history.replaceState(null, '', newUrl); // 履歴を増やさずURLだけ更新
    location.reload();
}

// 全部のdetailを開け閉め
var is_open = true;
function openAll() {
    document.querySelectorAll("details").forEach(d => {
        d.open = is_open;
    });
    is_open = !is_open;
}