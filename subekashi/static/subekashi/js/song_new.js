// 初期化
var songJson;
async function init() {
    songJson = await getJson("song");
    checkAutoForm();
    checkManualForm();
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
const urlEle = document.getElementById('url');
function checkAutoForm() {
    const newSubmitAutoEle = document.getElementById('new-submit-auto');
    const newFormAutoInfoEle = document.getElementById('new-form-auto-info');
    const inputUrlEle = urlEle.value;
    const videoId = getYouTubeVideoId(inputUrlEle);

    // URLが空の場合
    if (inputUrlEle === '') {
        newFormAutoInfoEle.innerHTML = "";
        newSubmitAutoEle.disabled = true;
        return;
    }

    // URLが複数の場合
    if (inputUrlEle.includes(",")) {
        newFormAutoInfoEle.innerHTML = "<span class='error'><i class='fas fa-ban error'></i>複数のURLを入力することはできません</span>";
        newSubmitAutoEle.disabled = true;
        return;
    }

    // URLがYouTubeのURLでない場合
    if (videoId === null) {
        newFormAutoInfoEle.innerHTML = "<span class='error'><i class='fas fa-ban error'></i>YouTubeの動画URLを入力してください</span>";
        newSubmitAutoEle.disabled = true;
        return;
    }

    const existingSong = songJson.find(song => getYouTubeVideoId(song.url) === videoId);

    // 既に登録されているURLの場合
    if (existingSong) {
        newFormAutoInfoEle.innerHTML = `<span class='error'><i class='fas fa-ban error'></i>このURLは<br>
        song ID：<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">${existingSong.id}</a><br>
        タイトル：${existingSong.title}<br>
        チャンネル名：${existingSong.channel}<br>
        として<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">既に登録されています</a></span>`;
        newSubmitAutoEle.disabled = true;
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
function checkManualForm() {
    const channelEle = document.getElementById('channel');
    const titleEle = document.getElementById('title');

    // どちらかが空の場合
    if (channelEle.value === '' || titleEle.value === '') {
        document.getElementById('new-form-manual-info').innerHTML = "";
        document.getElementById('new-submit-manual').disabled = true;
        return;
    }
    
    document.getElementById('new-submit-manual').disabled = false;

    const existingSong = songJson.find(song => song.title === titleEle.value && song.channel === channelEle.value);
    // 既に登録されている曲の場合
    if (existingSong) {
        const isMultipleSongURL = existingSong.url.includes(',');
        const existingSongURL = isMultipleSongURL ? existingSong.url.split(",")[0] : existingSong.url;

        document.getElementById('new-form-manual-info').innerHTML = `<span class="warning"><i class="fas fa-exclamation-triangle warning"></i>
        タイトル・チャンネル名ともに一致している曲が<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">見つかりました。</a><br>
        song ID：<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">${existingSong.id}</a><br>
        登録されているURL：<a href="${existingSongURL}" target="_blank">${existingSongURL}</a>${isMultipleSongURL ? 'など' : ''}<br>
        既に登録されている曲と登録しようとしている曲が別の曲に限り、登録することができます。</span>`;
        return;
    }
    
    // タイトルにスペースが含まれている場合
    if (titleEle.value != titleEle.value.trim()) {
        document.getElementById('new-form-manual-info').innerHTML = `<span class="info"><i class='fas fa-info-circle info'></i>タイトルにスペースが含まれています。<br>意図して入力していない場合、削除してください。</span>`;
        return;
    }

    // チャンネル名にスペースが含まれている場合
    if (channelEle.value != channelEle.value.trim()) {
        document.getElementById('new-form-manual-info').innerHTML = `<span class="info"><i class='fas fa-info-circle info'></i>チャンネル名にスペースが含まれています。<br>意図して入力していない場合、削除してください。</span>`;
        return;
    }

    // 登録されていない曲の場合
    document.getElementById('new-form-manual-info').innerHTML = `<span class='ok'><i class='fas fa-check-circle ok'></i>登録可能です</span>`;
}

channelEle.addEventListener('input', checkManualForm);
titleEle.addEventListener('input', checkManualForm);

// ページから戻ってきたときの処理
window.addEventListener("pageshow", function () {
    init();
});
