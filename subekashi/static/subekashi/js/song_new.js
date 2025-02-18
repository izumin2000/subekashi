const TUTORIALS = {
    'new-form-auto': "YouTubeのリンクからタイトル・チャンネル名を自動で取得するフォームです。",
    'new-form-manual': "手動でタイトル・チャンネル名を入力するフォームです。",
}

function showTutorial(place) {
    const tutorial = TUTORIALS[place];
    showToast('info', tutorial);
}