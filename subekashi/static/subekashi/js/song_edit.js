var songJson, imitateList = [], songGuesserController, song_id;

// 初期化
var songJson;
async function init() {
    songJson = await getJson("song");
    song_id = window.location.pathname.split("/")[2];
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

// タイトルとチャンネルの入力チェック
const titleEle = document.getElementById('title');
const channelEle = document.getElementById('channel');
var isTitleChannelValid = false;
function checkTitleChannelForm() {
    const songEditSubmitEle = document.getElementById('song-edit-submit');
    const songEditInfoTitleChannelEle = document.getElementById('song-edit-info-title-channel');

    // タイトルとチャンネル名が空の場合
    if (titleEle.value === '' || channelEle.value === '') {
        songEditInfoTitleChannelEle.innerHTML = "<span class='error'>タイトルとチャンネル名を入力してください</span>";
        isTitleChannelValid = false;
        return;
    }

    const existingSong = songJson.find(song => song.title === titleEle.value && song.channel === channelEle.value);
    const song_id = window.location.pathname.split("/")[2];
    // 既に登録されている曲の場合
    if (existingSong && existingSong.id != song_id) {
        const isMultipleSongURL = existingSong.url.includes(',');
        const existingSongURL = isMultipleSongURL ? existingSong.url.split(",")[0] : existingSong.url;

        songEditInfoTitleChannelEle.innerHTML = `<span class="warning">
        タイトル・チャンネル名ともに一致している曲が<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">見つかりました。</a><br>
        song ID：<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">${existingSong.id}</a><br>
        登録されているURL：<a href="${existingSongURL}" target="_blank">${existingSongURL}</a>${isMultipleSongURL ? 'など' : ''}<br>
        既に登録されている曲と登録しようとしている曲が別の曲に限り、登録することができます。<br>
        この記事を削除したい場合は、<a href="${baseURL()}/songs/${song_id}/delete?reason=song ID：${existingSong.id}と被っています。" target="_blank">こちら</a>をクリックしてください。
        </span>`;
        isTitleChannelValid = false;
        return;
    }

    // タイトルにスペースが含まれている場合
    if (titleEle.value != titleEle.value.trim()) {
        songEditInfoTitleChannelEle.innerHTML = `<span class="info">タイトルにスペースが含まれています。<br>意図して入力していない場合、削除してください。</span>`;
    }

    // チャンネル名にスペースが含まれている場合
    if (channelEle.value != channelEle.value.trim()) {
        songEditInfoTitleChannelEle.innerHTML = `<span class="info">チャンネル名にスペースが含まれています。<br>意図して入力していない場合、削除してください。</span>`;
    }

    // タイトルとチャンネル名が入力されている場合
    songEditInfoTitleChannelEle.innerHTML = "";
    isTitleChannelValid = true;
}
channelEle.addEventListener('input', checkTitleChannelForm);
titleEle.addEventListener('input', checkTitleChannelForm);

// URLの入力チェック
const urlEle = document.getElementById('url');
var isUrlValid = true;
function checkUrlForm() {
    const songEditInfoUrlEle = document.getElementById('song-edit-info-url');

    for (url of urlEle.value.split(',')) {
        // urlでない場合
        if (!url.match(/^(https?|ftp):\/\/[^\s/$.?#].[^\s]*$/)) {
            songEditInfoUrlEle.innerHTML = "<span class='error'>入力形式が正しくありません</span>";
            isUrlValid = false;
            return;
        }

        const existingSong = songJson.find(song => (song.url.includes(url)) && (song.id != song_id));
        // 既に登録されているURLの場合
        if (existingSong) {
            songEditInfoUrlEle.innerHTML = `<span class='error'>このURLは<br>
            song ID：<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">${existingSong.id}</a><br>
            タイトル：${existingSong.title}<br>
            チャンネル名：${existingSong.channel}<br>
            として<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">既に登録されています</a><br>
            この記事を削除したい場合は、<a href="${baseURL()}/songs/${song_id}/delete?reason=song ID：${existingSong.id}と被っています。" target="_blank">こちら</a>をクリックしてください。
            </span>`;
            isUrlValid = false;
            return;
        }
    }
    isUrlValid = true;
    songEditInfoUrlEle.innerHTML = "";
}
urlEle.addEventListener('input', checkUrlForm);

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