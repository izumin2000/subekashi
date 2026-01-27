var imitateIdList = [], songGuesserController, song_id;

// TODO 1回のexponentialBackoffで済ませる
// 初期化
const lyricsEle = document.getElementById("lyrics")
async function init() {
    openDeleteDetails();
    song_id = window.location.pathname.split("/")[2];
    await checkTitleAuthorForm();
    await checkUrlForm();
    await initImitateList();
    checkButton();
    checkDeleteForm();
};
window.addEventListener('load', init);


function openDeleteDetails() {
  const params = new URLSearchParams(window.location.search);

  if (params.has('reason')) {
    const details = document.getElementById('delete-details');
    if (details) {
      details.open = true;
    }
  }
}

// TODO checkValidityを利用
// TODO 改行でもvalidになる不具合の修正
function checkDeleteForm() {
    const reasonValue = document.getElementById("reason").value;
    const deleteEle = document.getElementById("delete-submit");
    deleteEle.disabled = reasonValue == "";
}

document.getElementById('reason').addEventListener('input', checkDeleteForm)

// 模倣リストの末尾にsongを追加
function appendImitateList(song) {
    const tmpl = document.getElementById("imitate-item-template");
    const clone = tmpl.content.cloneNode(true);

    clone.querySelector(".imitate-item").id = `imitate-${song.id}`;
    clone.querySelector(".author-name").textContent = getAuthorText(song);
    clone.querySelector(".title").textContent = song.title;

    const deleteBtn = clone.querySelector(".delete-btn");
    deleteBtn.dataset.id = song.id;

    deleteBtn.addEventListener("click", () => {
        deleteImitate(song.id);
    });

    document.getElementById("imitate-list").appendChild(clone);
}

// 読み込み時に模倣一覧を描画
var imitateEle = document.getElementById("imitate");
async function initImitateList() {
    if (!imitateEle.value) {
        return;
    }
    
    const imitateSongListRes = await exponentialBackoff(`song/?imitated=${song_id}`, "init", initImitateList);

    if (!imitateSongListRes) {
        return;
    }
    const imitateSongList = imitateSongListRes.result;

    imitateIdList = imitateEle.value.split(",");
    for (const imitateSong of imitateSongList) {
        appendImitateList(imitateSong);
    }
}

// ビューに渡すimitateカラムの値を#imitateにセット
function setImitate() {
    imitateEle.value = imitateIdList.join();
    checkButton();
}

// 模倣一覧からimitateIdを削除
function deleteImitate(imitateId) {
    document.getElementById(`imitate-${imitateId}`).remove();
    imitateIdList = imitateIdList.filter(id => id != imitateId);        // imitateIdListからimitateIdを削除
    setImitate();       // imitateIdListの内容を#imitateにセット
}

// 模倣一覧にsongを追加
function appendImitate(song) {
    appendImitateList(song)
    imitateIdList.push(song.id);      // imitateIdListにsong.idを追加
    setImitate();       // imitateIdListの内容を#imitateにセット
}

// すべあな原曲から選択
function categoryClick(song) {
    appendImitate(song);
}

// すべあな原曲以外からから選択する際の検索
const imitateTitleEle = document.getElementById("imitate-title");
function renderSongGuesser() {
    // 以前のリクエストが存在する場合、そのリクエストをキャンセルする
    if (songGuesserController) {
        songGuesserController.abort();
    }

    const imitateTitle = imitateTitleEle.value;
    songGuesserController = new AbortController();
    getSongGuessers(imitateTitle, "song-guesser", songGuesserController.signal, renderSongGuesser);
}

// すべあな原曲以外からから選択
async function songGuesserClick(id) {
    imitateTitleEle.value = "";

    if (id == song_id) {
        showToast("error", "編集する曲の模倣曲に、その曲自身を登録することはできません。");
        renderSongGuesser();
        return;
    }
    var imitateSongRes = await exponentialBackoff(`song/${id}`, "imitate", songGuesserClick);
    if (!imitateSongRes) {
        return;
    }

    appendImitate(imitateSongRes);
    renderSongGuesser();
};

// タイトルと作者の入力チェック
const titleEle = document.getElementById('title');
const authorsEle = document.getElementById('authors');
var isTitleAuthorValid = false;
async function checkTitleAuthorForm() {
    isTitleAuthorValid = false;
    checkButton();
    const songEditInfoTitleAuthorsEle = document.getElementById('song-edit-info-title-authors');

    const loadingEle = `<img src="${baseURL()}/static/subekashi/image/loading.gif" id="loading" alt='loading'></img>`
    songEditInfoTitleAuthorsEle.innerHTML = loadingEle;

    // タイトルと作者が空の場合
    if (titleEle.value === '' || authorsEle.value === '') {
        songEditInfoTitleAuthorsEle.innerHTML = "<span class='error'><i class='fas fa-ban error'></i>タイトルと作者を入力してください</span>";
        return;
    }

    // 以下の条件はvalid
    isTitleAuthorValid = true;
    checkButton();
    const existingSongsRes = await exponentialBackoff(`song/?title_exact=${titleEle.value}&author_exact=${authorsEle.value}`, "titleauthor", checkTitleAuthorForm);
    
    if (existingSongsRes == undefined) {
        return;
    }
    const existingSongs = existingSongsRes.result;

    const existingSong = existingSongs?.filter(song => song.id != song_id)[0];

    // 既に登録されている曲の場合
    // TODO checkUrlFormを参考にリファクタリングする
    if (existingSong) {
        const isMultipleSongURL = existingSong.url.includes(',');
        const existingSongURL = isMultipleSongURL ? existingSong.url.split(",")[0] : existingSong.url;
        const infoHTML = isLack(existingSong)
        ?
        `<span class="info"><i class="fas fa-info-circle info"></i>
        未完成である曲が<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">見つかりました。</a><br>
        song ID：<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">${existingSong.id}</a><br>
        登録されているURL：<a href="${existingSongURL}" target="_blank">${existingSongURL}</a>${isMultipleSongURL ? 'など' : ''}<br>
        この記事を削除したい場合は、<a href="${baseURL()}/songs/${song_id}/delete?reason=${baseURL()}/songs/${existingSong.id} と重複しています。" target="_blank">こちら</a>をクリックしてください。
        </span>`
        :
        `<span class="warning"><i class="fas fa-exclamation-triangle warning"></i>
        タイトル・作者ともに一致している曲が<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">見つかりました。</a><br>
        song ID：<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">${existingSong.id}</a><br>
        登録されているURL：<a href="${existingSongURL}" target="_blank">${existingSongURL}</a>${isMultipleSongURL ? 'など' : ''}<br>
        既に登録されている曲と登録しようとしている曲が別の曲に限り、登録することができます。<br>
        この記事を削除したい場合は、<a href="${baseURL()}/songs/${song_id}/delete?reason=${baseURL()}/songs/${existingSong.id} と重複しています。" target="_blank">こちら</a>をクリックしてください。
        </span>`;

        songEditInfoTitleAuthorsEle.innerHTML = infoHTML;
        return;
    }

    // タイトルの前後にスペースが含まれている場合
    if (titleEle.value != titleEle.value.trim()) {
        songEditInfoTitleAuthorsEle.innerHTML = `<span class="info"><i class='fas fa-info-circle info'></i>タイトルにスペースが含まれています。<br>意図して入力していない場合、削除してください。</span>`;
        return;
    }

    // 作者の前後にスペースが含まれている場合
    if (authorsEle.value != authorsEle.value.trim()) {
        songEditInfoTitleAuthorsEle.innerHTML = `<span class="info"><i class='fas fa-info-circle info'></i>作者にスペースが含まれています。<br>意図して入力していない場合、削除してください。</span>`;
        return;
    }

    // タイトル・作者の前後にスペースが含まれていない場合
    songEditInfoTitleAuthorsEle.innerHTML = "<span class='ok'><i class='fas fa-check-circle ok'></i>登録可能な状態です</span>";
}
authorsEle.addEventListener('input', checkTitleAuthorForm);
titleEle.addEventListener('input', checkTitleAuthorForm);

// URLの入力チェック
const urlEle = document.getElementById('url');
var isUrlValid = true;
async function checkUrlForm() {
    isUrlValid = false;
    checkButton();
    const songEditInfoUrlEle = document.getElementById('song-edit-info-url');

    const loadingEle = `<img src="${baseURL()}/static/subekashi/image/loading.gif" id="loading" alt='loading'></img>`
    songEditInfoUrlEle.innerHTML = loadingEle;

    // URLが空の場合
    if (urlEle.value === '') {
        songEditInfoUrlEle.innerHTML = "";
        isUrlValid = true;
        checkButton();
        return;
    }

    for (url of urlEle.value.split(',')) {
        // urlでない場合
        if (!url.match(/^(https?|ftp):\/\/[^\s/$.?#].[^\s]*$/)) {
            songEditInfoUrlEle.innerHTML = "<span class='error'><i class='fas fa-ban error'></i>入力形式が正しくありません</span>";
            return;
        }

        // URLのフォーマット
        url = url.replace("https://www.google.com/url?q=", "");
        url = url.replace("https://www.", "https://");
        url = url.replace("https://twitter.com", "https://x.com");
        url = formatYouTubeURL(url);

        const existingSongsRes = await exponentialBackoff(
            `song/?url=${encodeURIComponent(url)}`,
            'url',
            checkUrlForm
        );
        if (!existingSongsRes) return;

        const existingSongs = existingSongsRes.result;
        const existingSong = existingSongs.find(song => song.id != song_id);
        
        // 自身以外のurlが重複していなかったら
        if (!existingSong) {
            isUrlValid = true;
            checkButton();
            songEditInfoUrlEle.innerHTML = "<span class='ok'><i class='fas fa-check-circle ok'></i>登録可能な状態です</span>";
            return;
        }

        // 曲のurlが重複していたら
        const base = baseURL();
        const songId = existingSong.id;
        const title = escapeHtml(existingSong.title);
        const author = escapeHtml(getAuthorText(existingSong));

        const songLink = `${base}/songs/${songId}`;
        const deleteReason = encodeURIComponent(`${songLink} と重複しています。`);
        const deleteLink = `${base}/songs/${song_id}/delete?reason=${deleteReason}`;

        const isIncomplete = isLack(existingSong);
        const infoHTML = `
        <span class="error">
            <i class="fas fa-ban error"></i>
            このURLは<br>
            song ID：<a href="${songLink}" target="_blank">${songId}</a><br>
            タイトル：${title}<br>
            作者：${author}<br>
            として
            <a href="${songLink}" target="_blank">既に登録されています</a>
            ${isIncomplete ? "がまだ未完成です。" : "。"}<br>
            この記事を削除したい場合、<br>
            <a href="${deleteLink}" target="_blank"><i class="error far fa-trash-alt"></i>削除申請</a>
            を行ってくださいください。
        </span>
        `;

        songEditInfoUrlEle.innerHTML = infoHTML;
        return;
    }
}
urlEle.addEventListener('input', checkUrlForm);

// 登録ボタン
function checkButton() {
    // ボタンのdisabledの変更
    const songEditSubmitEle = document.getElementById('song-edit-submit');
    songEditSubmitEle.disabled = !(isTitleAuthorValid && isUrlValid)

    // 未完成に関する変数の定義
    var message = "";
    var is_lack = false;
    
    // URLの未完成
    if (!document.getElementById("is-deleted").checked && (urlEle.value == "")) {
        message += "<li>「非公開/削除済み」にチェックをつけるか、URLを入力してください。</li>"
        is_lack = true;
    }
    
    // 模倣の未完成
    const is_original = document.getElementById("is-original").checked;
    const is_subeana = document.getElementById("is-subeana").checked;
    if (!is_original && is_subeana && (imitateEle.value == "") && (authorsEle.value != "全てあなたの所為です。")) {
        message += "<li>「オリジナル模倣」にチェックをつけるか、模倣曲を1曲以上登録してください。</li>"
        is_lack = true;
    }

    // 歌詞の未完成
    if (!document.getElementById("is-inst").checked && (lyricsEle.value == "")) {
        message += "<li>「インスト」にチェックをつけるか、歌詞を入力してください。</li>"
        is_lack = true;
    }
    
    // 登録ボタンの下のメッセージ
    document.getElementById('song-edit-info-submit').innerHTML = is_lack ? `<span class='info'>
    <i class='fas fa-info-circle info'></i>
    記事を完成させるためには、以下の入力を行ってください。<ul>${message}</ul>
    </span>` : ``;
}
document.querySelectorAll('input[type="checkbox"], textarea').forEach(input => input.addEventListener('input', checkButton));
checkButton();

// 模倣検索フォームにてエンターの入力を防ぐ
imitateTitleEle.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        event.preventDefault(); // Enterキーの動作を無効化
    }
});

// フォームに変更があったかを検知
var isFormDirty = false;
document.querySelectorAll('input:not([type="submit"]), textarea').forEach((input) => {
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

// 送信ボタンは戻る処理の対象外なのでisFormDirtyをfalseにする
document.querySelectorAll('form').forEach((form) => {
    form.addEventListener('submit', (event) => {
        isFormDirty = false;
    });
});