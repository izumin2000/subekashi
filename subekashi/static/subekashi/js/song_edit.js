var songJson, imitateList = []

// 初期化
var songJson;
async function init() {
    songJson = await getJson("song");
};
window.addEventListener('load', init);

// ビューに渡すimitateカラムの値を#imitateにセット
function setImitate() {
    imitateEle = document.getElementById("imitate");
    imitateEle.value = imitateList.join();
}

// 模倣一覧からimitateIdを削除
function deleteImitate(imitateId) {
    imitateEle = document.getElementById(`imitate-${imitateId}`);
    imitateEle.remove();
    imitateList = imitateList.filter(id => id != imitateId);        // imitateListからimitateIdを削除
    setImitate();       // imitateListの内容を#imitateにセット
}

// 模倣一覧にsongを追加
function appendImitate(song) {
    // #imitate-listにsongの情報を追加
    imitateStr = `
    <div id="imitate-${ song.id }">
        <p>
            <span class='channel'>
                <i class='fas fa-user-circle'></i>
                ${ song.channel }
            </span>
            <i class='fas fa-music'></i>
            ${ song.title }
            <span onclick="deleteImitate(${ song.id })">
                <i class='far fa-trash-alt'></i>
            </span>
        </p>
    </div>
    `

    imitateListEle = document.getElementById('imitate-list');
    imitateListEle.appendChild(stringToHTML(imitateStr));

    imitateList.push(song.id);      // imitateListにsong.idを追加
    setImitate();       // imitateListの内容を#imitateにセット
}

// すべあな原曲から選択
function categoryClick(song) {
    appendImitate(song);
}

// すべあな原曲以外からから選択する際の検索
function renderSongGuesser() {
    // 以前のリクエストが存在する場合、そのリクエストをキャンセルする
    if (songGuesserController) {
        songGuesserController.abort();
    }

    songGuesserController = new AbortController();
    imitateTitle = document.getElementById("imitate-title").value;
    getSongGuessers(imitateTitle, "song-guesser", songGuesserController.signal);
}

// すべあな原曲以外からから選択
function songGuesserClick(id) {
    document.getElementById("imitate-title").value = "";
    imitateSong = songJson.find(song => song.id == id);
    appendImitate(imitateSong);
    renderSongGuesser();
};

// フォームに変更があったかを検知
var isFormDirty = false;
document.querySelectorAll('input, textarea').forEach((input) => {
    input.addEventListener('change', () => {
        isFormDirty = true;
    });
});

// ページを離れる前に警告を表示
window.addEventListener('beforeunload', (event) => {
    if (isFormDirty) {
        event.preventDefault();
    }
});

// フォームが送信される際にisFormDirtyをリセット
document.querySelector('form').addEventListener('submit', (event) => {
    isFormDirty = false;
});