window.addEventListener("DOMContentLoaded", () => {
    // 読み込み時に最初のdetailを展開
    const firstDetail = document.querySelector("details");
    firstDetail.open = true;

    // セルの値をコピー
	document.querySelectorAll(".change_table_wrapper td").forEach(cell => {
		cell.addEventListener("click", async () => {
			const text = cell.innerText.trim();
			try {
				navigator.clipboard.writeText(text);
				showToast("ok", "コピーしました。");
			} catch (err) {
                showToast("error", "エラーが発生しました。");
			}
		});
	});
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