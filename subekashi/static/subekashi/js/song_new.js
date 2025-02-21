const TUTORIALS = {
    "new-form-auto": "YouTubeのリンクからタイトル・チャンネル名を自動で取得して登録するフォームです。既に登録してあるURLは登録できません。",
    "youtube-url": "YouTubeのURLを入力してください。<br>「後で見る」を含むプレイリスト内の動画のURLでも大丈夫です。<br>無断転載された動画のURLの記載はお控えください。",
    "is-original": "オリジナル模倣曲・フリースタイル模倣曲の場合はチェックをつけてください。<br>例）<a href='https://youtu.be/XkIKM80-Znc' target='_blank'>∴∴∴∴</a> <a href='https://youtu.be/zDUvoKUOviQ' target='_blank'>天秤にかけて</a>",
    "is-deleted": "アクセスしても視聴できない場合にチェックしてください。<br>限定公開の場合はチェックする必要はありません。",
    "is-joke": "ネタに走っている曲の場合にチェックしてください。<br>ネタ曲かどうかの判断は個人の判断に任せます。",
    "is-inst": "歌詞の無い曲の場合にチェックしてください。<br>例）<a href='https://youtu.be/6-h8cW_Han8' target='_blank'>明日へ降る雨</a> <a href='https://youtu.be/2P62pozC9Zc' target='_blank'>またの御アクセスをお待ちしております。</a>",
    "is-subeana": "すべあな界隈曲の場合はチェックしてください。<br>すべあな界隈曲かどうかの判断は個人の判断に任せます。",
    "new-form-manual": "手動でタイトル・チャンネル名を入力するフォームです。",
    "title": "YouTube上のタイトルや曲名を入力してください。<br>曲によっては複数のタイトルがある場合もあるので、その場合は一般的に知られているタイトルを入力することをオススメします。<span style='font-size: 10px'>将来的に曲の別名を入力できる機能を実装予定です。</span>",
    "channel": "チャンネル名やアーティスト名を入力してください。<br>複数のアーティストが関わっている場合はコンマ(,)で区切って入力してください。<br>複数の名義がある場合は、現在使われている名義・チャンネル名を入力してください。<span style='font-size: 10px'>将来的に名義に関する情報を入力できる機能を実装予定です。</span>",
}

var songJson;
window.addEventListener('load', async function () {
    songJson = await getJson("song");
});


function showTutorial(place) {
    const tutorial = TUTORIALS[place];
    showToast("info", tutorial);
}

// URL入力フォームの入力チェック
const urlEle = document.getElementById('url');
urlEle.addEventListener('input', function () {
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

    // URLがYouTubeのURLでない場合
    if (videoId === null) {
        newFormAutoInfoEle.innerHTML = "<span class='error'>YouTubeの動画URLを入力してください</span>";
        newSubmitAutoEle.disabled = true;
        return;
    }

    const existingSong = songJson.find(song => getYouTubeVideoId(song.url) === videoId);

    // 既に登録されているURLの場合
    if (existingSong) {
        newFormAutoInfoEle.innerHTML = `<span class='error'>このURLは<br>タイトル：${existingSong.title}<br>チャンネル名：${existingSong.channel}<br>として<a href="${baseURL()}/songs/${existingSong.id}" target="_blank">既に登録されています</a></span>`;
        newSubmitAutoEle.disabled = true;
        return;
    }

    // 登録されていないURLの場合
    newFormAutoInfoEle.innerHTML = "<span class='ok'>このURLは登録されていません</span>";
    newSubmitAutoEle.disabled = false;

    newSubmitAutoEle.disabled = urlEle.value == '';
});

// タイトル・チャンネル名入力フォームの入力チェック
const channelEle = document.getElementById('channel');
const titleEle = document.getElementById('title');
const newSubmitManualEle = document.getElementById('new-submit-manual');

function checkManualForm() {
    newSubmitManualEle.disabled = (channelEle.value == '' || titleEle.value == '');
}

channelEle.addEventListener('input', checkManualForm);
titleEle.addEventListener('input', checkManualForm);