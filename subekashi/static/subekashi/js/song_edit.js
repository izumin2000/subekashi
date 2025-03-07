var imitateIdList = [], songGuesserController, song_id;

// 初期化
const lyricsEle = document.getElementById("lyrics")
async function init() {
    song_id = window.location.pathname.split("/")[2];
    await checkTitleChannelForm();
    await checkUrlForm();
    await initImitateList();
    checkButton();
};
window.addEventListener('load', init);

// 模倣リストの末尾にsongを追加
function appendImitateList(song) {
    const imitateStr = `
    <div id="imitate-${song.id}">
        <p>
            <span class='channel'>
                <i class='fas fa-user-circle'></i>
                ${song.channel}
            </span>
            <i class='fas fa-music'></i>
            ${song.title}
            <span onclick="deleteImitate(${song.id})">
                <i class='far fa-trash-alt'></i>
            </span>
        </p>
    </div>
    `;

    var imitateListEle = document.getElementById('imitate-list');
    imitateListEle.appendChild(stringToHTML(imitateStr));
}

// 読み込み時に模倣一覧を描画
var imitateEle = document.getElementById("imitate");
async function initImitateList() {
    if (!imitateEle.value) {
        return;
    }
    
    const imitateSongList = await exponentialBackoff(`song/?imitate=${song_id}`, "init", initImitateList);
    if (!imitateSongList) {
        return;
    }

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
    var imitateSong = await exponentialBackoff(`song/${id}`, "imitate", songGuesserClick);
    if (!imitateSong) {
        return;
    }

    appendImitate(imitateSong);
    renderSongGuesser();
};

// タイトルとチャンネルの入力チェック
const titleEle = document.getElementById('title');
const channelEle = document.getElementById('channel');
var isTitleChannelValid = false;
async function checkTitleChannelForm() {
    const songEditInfoTitleChannelEle = document.getElementById('song-edit-info-title-channel');

    // タイトルとチャンネル名が空の場合
    if (titleEle.value === '' || channelEle.value === '') {
        songEditInfoTitleChannelEle.innerHTML = "<span class='error'><i class='fas fa-ban error'></i>タイトルとチャンネル名を入力してください</span>";
        isTitleChannelValid = false;
        return;
    }

    // 以下の条件はvalid
    isTitleChannelValid = true;
    const titleChannelResponse = await exponentialBackoff(`song/?title_exact=${titleEle.value}&channel_exact=${channelEle.value}`, "tiltechannel", checkTitleChannelForm);
    if (!titleChannelResponse) {
        return;
    }

    const existingSong = titleChannelResponse.filter(song => song.id != song_id)[0];

    // 既に登録されている曲の場合
    if (existingSong) {
        const isMultipleSongURL = existingSong.url.includes(',');
        const existingSongURL = isMultipleSongURL ? existingSong.url.split(",")[0] : existingSong.url;

        songEditInfoTitleChannelEle.innerHTML = `<span class="warning"><i class="fas fa-exclamation-triangle warning"></i>
        タイトル・チャンネル名ともに一致している曲が<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">見つかりました。</a><br>
        song ID：<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">${existingSong.id}</a><br>
        登録されているURL：<a href="${existingSongURL}" target="_blank">${existingSongURL}</a>${isMultipleSongURL ? 'など' : ''}<br>
        既に登録されている曲と登録しようとしている曲が別の曲に限り、登録することができます。<br>
        この記事を削除したい場合は、<a href="${baseURL()}/songs/${song_id}/delete?reason=${existingSong.id} と重複しています。" target="_blank">こちら</a>をクリックしてください。
        </span>`;
        return;
    }
    
    // タイトルの前後にスペースが含まれている場合
    if (titleEle.value != titleEle.value.trim()) {
        songEditInfoTitleChannelEle.innerHTML = `<span class="info"><i class='fas fa-info-circle info'></i>タイトルにスペースが含まれています。<br>意図して入力していない場合、削除してください。</span>`;
        return;
    }
    
    // チャンネル名の前後にスペースが含まれている場合
    if (channelEle.value != channelEle.value.trim()) {
        songEditInfoTitleChannelEle.innerHTML = `<span class="info"><i class='fas fa-info-circle info'></i>チャンネル名にスペースが含まれています。<br>意図して入力していない場合、削除してください。</span>`;
        return;
    }

    // タイトル・チャンネル名の前後にスペースが含まれていない場合
    songEditInfoTitleChannelEle.innerHTML = "<span class='ok'><i class='fas fa-check-circle ok'></i>登録可能な状態です</span>";
}
channelEle.addEventListener('input', checkTitleChannelForm);
titleEle.addEventListener('input', checkTitleChannelForm);

// URLの入力チェック
const urlEle = document.getElementById('url');
var isUrlValid = true;
async function checkUrlForm() {
    const songEditInfoUrlEle = document.getElementById('song-edit-info-url');

    // URLが空の場合
    if (urlEle.value === '') {
        songEditInfoUrlEle.innerHTML = "";
        return;
    }

    for (url of urlEle.value.split(',')) {
        // urlでない場合
        if (!url.match(/^(https?|ftp):\/\/[^\s/$.?#].[^\s]*$/)) {
            songEditInfoUrlEle.innerHTML = "<span class='error'><i class='fas fa-ban error'></i>入力形式が正しくありません</span>";
            isUrlValid = false;
            return;
        }

        // URLのフォーマット
        url = url.replace("https://www.google.com/url?q=", "");
        url = url.replace("https://www.", "https://");
        url = url.replace("https://twitter.com", "https://x.com");
        url = formatYouTubeURL(url);

        const urlResponse = await exponentialBackoff(`song/?url=${url}`, "url", checkUrlForm);
        if (!urlResponse) {
            return;
        }

        const existingSong = urlResponse.filter(song => song.id != song_id)[0];

        // 既に登録されているURLの場合
        if (existingSong) {
            songEditInfoUrlEle.innerHTML = `<span class='error'><i class='fas fa-ban error'></i>このURLは<br>
            song ID：<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">${existingSong.id}</a><br>
            タイトル：${existingSong.title}<br>
            チャンネル名：${existingSong.channel}<br>
            として<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">既に登録されています</a><br>
            この記事を削除したい場合は、<a href="${baseURL()}/songs/${song_id}/delete?reason=${existingSong.id} と重複しています。" target="_blank">こちら</a>をクリックしてください。
            </span>`;
            isUrlValid = false;
            return;
        }
    }
    isUrlValid = true;
    songEditInfoUrlEle.innerHTML = "<span class='ok'><i class='fas fa-check-circle ok'></i>登録可能な状態です</span>";
}
urlEle.addEventListener('input', checkUrlForm);

// 登録ボタン
function checkButton() {
    // ボタンのdisabledの変更
    const songEditSubmitEle = document.getElementById('song-edit-submit');
    songEditSubmitEle.disabled = !(isTitleChannelValid && isUrlValid)

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
    if (!is_original && is_subeana && (imitateEle.value == "") && (channelEle.value != "全てあなたの所為です。")) {
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
document.querySelectorAll('input, textarea').forEach(input => input.addEventListener('input', checkButton));

// 模倣検索フォームにてエンターの入力を防ぐ
imitateTitleEle.addEventListener("keydown", function (event) {
    if (event.key === "Enter") {
        event.preventDefault(); // Enterキーの動作を無効化
    }
});

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