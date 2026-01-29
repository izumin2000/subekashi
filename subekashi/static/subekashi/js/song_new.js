// 初期化
const urlEle = document.getElementById('url');
async function init() {
    urlEle.focus();     // #urlにカーソルをあわせる
    await checkAutoForm();
    await checkManualForm();
};
window.addEventListener('load', init);

// チェックボックスの同期
document.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
    checkbox.addEventListener('change', function() {
        const syncGroup = this.getAttribute('data-sync');
        document.querySelectorAll(`input[data-sync="${syncGroup}"]`).forEach(cb => {
            cb.checked = this.checked;
        });
    });
});

// URL入力フォームの入力チェック
async function checkAutoForm() {
    const newSubmitAutoEle = document.getElementById('new-submit-auto');
    const newFormAutoInfoEle = document.getElementById('new-form-auto-info');
    const inputUrlEle = urlEle.value;
    const videoId = getYouTubeId(inputUrlEle);
    newSubmitAutoEle.disabled = true;

    const loadingEle = `<img src="${baseURL()}/static/subekashi/image/loading.gif" id="loading" alt='loading'></img>`
    newFormAutoInfoEle.innerHTML = loadingEle;

    // URLが空の場合
    if (inputUrlEle === '') {
        newFormAutoInfoEle.innerHTML = "";
        return;
    }

    // URLが複数の場合
    if (inputUrlEle.includes(",")) {
        newFormAutoInfoEle.innerHTML = "<span class='error'><i class='fas fa-ban error'></i>複数のURLを入力することはできません</span>";
        return;
    }

    // URLがYouTubeのURLでない場合
    if (videoId === null) {
        newFormAutoInfoEle.innerHTML = "<span class='error'><i class='fas fa-ban error'></i>YouTubeの動画URLを入力してください</span>";
        return;
    }
    
    const existingSongsRes = await exponentialBackoff(`song/?url=${videoId}`, "url", checkAutoForm);
    
    if (existingSongsRes == undefined) {
        return;
    }
    const existingSongs = existingSongsRes.result;

    // 既に登録されているURLの場合
    if (existingSongs.length) {
        const existingSong = existingSongs[0];
        const infoHTML = isLack(existingSong) 
        ?
        `<span class="info"><i class="fas fa-info-circle info"></i>このURLは<br>
        song ID：<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">${existingSong.id}</a><br>
        タイトル：${existingSong.title}<br>
        チャンネル名：${existingSong.channel}<br>
        として<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">既に登録されています</a>がまだ未完成です</span>`
        :
        `<span class='error'><i class='fas fa-ban error'></i>このURLは<br>
        song ID：<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">${existingSong.id}</a><br>
        タイトル：${existingSong.title}<br>
        チャンネル名：${existingSong.channel}<br>
        として<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">既に登録されています</a></span>`;
        newFormAutoInfoEle.innerHTML = infoHTML; 
        return;
    }

    // 登録されていないURLの場合
    newFormAutoInfoEle.innerHTML = "<span class='ok'><i class='fas fa-check-circle ok'></i>登録可能です</span>";
    newSubmitAutoEle.disabled = false;

    newSubmitAutoEle.disabled = urlEle.value == '';
};

urlEle.addEventListener('input', checkAutoForm)

// タイトル・チャンネル名入力フォームの入力チェック
var channelEle = document.getElementById('channel');
var titleEle = document.getElementById('title');
async function checkManualForm() {
    const channelEle = document.getElementById('channel');
    const titleEle = document.getElementById('title');
    const newFormAutoManualEle = document.getElementById('new-form-manual-info');

    const loadingEle = `<img src="${baseURL()}/static/subekashi/image/loading.gif" id="loading" alt='loading'></img>`
    newFormAutoManualEle.innerHTML = loadingEle;

    // 作者が空白の場合
    if (channelEle.value === '' || channelEle.value.trim() === '') {
        newFormAutoManualEle.innerHTML = "<span class='error'><i class='fas fa-ban error'></i>作者は空白にできません</span>";
        document.getElementById('new-submit-manual').disabled = true;
        return;
    }

    // タイトルが空の場合
    if (titleEle.value === '' || titleEle.value.trim() === '') {
        newFormAutoManualEle.innerHTML = "<span class='error'><i class='fas fa-ban error'></i>タイトルは空白にできません</span>";
        document.getElementById('new-submit-manual').disabled = true;
        return;
    }
    
    document.getElementById('new-submit-manual').disabled = false;

    const existingSongsRes = await exponentialBackoff(`song/?title_exact=${titleEle.value}&channel_exact=${channelEle.value}`, "titlechannel", checkManualForm);
    
    if (existingSongsRes == undefined) {
        return;
    }
    const existingSongs = existingSongsRes.result;

    // 既に登録されている曲の場合
    if (existingSongs.length) {
        const existingSong = existingSongs[0];
        const isMultipleSongURL = existingSong.url.includes(',');
        const existingSongURL = isMultipleSongURL ? existingSong.url.split(",")[0] : existingSong.url;
        const InnerURL = existingSongURL ? `登録されているURL：<a href="${existingSongURL}" target="_blank">${existingSongURL}</a>${isMultipleSongURL ? 'など' : ''}<br>` : ""
        const infoHTML = isLack(existingSong)
        ?
        `<span class="info"><i class="fas fa-info-circle info"></i>
        未完成である曲が<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">見つかりました。</a><br>
        song ID：<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">${existingSong.id}</a><br>
        ${InnerURL}
        同じ曲の場合、代わりにこちらの記事を編集してください。`
        :
        `<span class="warning"><i class="fas fa-exclamation-triangle warning"></i>
        タイトル・チャンネル名ともに一致している曲が<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">見つかりました。</a><br>
        song ID：<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">${existingSong.id}</a><br>
        ${InnerURL}
        既に登録されている曲と登録しようとしている曲が別の曲に限り、登録することができます。</span>`;

        newFormAutoManualEle.innerHTML = infoHTML;
        return;
    }
    
    // タイトルにスペースが含まれている場合
    if (titleEle.value != titleEle.value.trim()) {
        newFormAutoManualEle.innerHTML = `<span class="info"><i class='fas fa-info-circle info'></i>タイトルにスペースが含まれています。<br>意図して入力していない場合、削除してください。</span>`;
        return;
    }

    // チャンネル名にスペースが含まれている場合
    if (channelEle.value != channelEle.value.trim()) {
        newFormAutoManualEle.innerHTML = `<span class="info"><i class='fas fa-info-circle info'></i>チャンネル名にスペースが含まれています。<br>意図して入力していない場合、削除してください。</span>`;
        return;
    }

    // 登録されていない曲の場合
    newFormAutoManualEle.innerHTML = `<span class='ok'><i class='fas fa-check-circle ok'></i>登録可能です</span>`;
}

channelEle.addEventListener('input', checkManualForm);
titleEle.addEventListener('input', checkManualForm);

// ページから戻ってきたときの処理
window.addEventListener("pageshow", function () {
    init();
});
