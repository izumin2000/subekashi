function add_special_button() {
    var defaultDummybuttonsEle = document.getElementsByClassName("dummybuttons")[0];
    const designedDummybuttonsEle =
    `
    <div class="dummybuttons">
        <a>
            <div class="dummybutton" onclick="special()"><i class="fas fa-magic"></i><p>スペシャルデザイン</p></div>
        </a>
    </div>
    `
    defaultDummybuttonsEle.innerHTML = stringToHTML(designedDummybuttonsEle).innerHTML;
}

function dot_lyrics() {
    // ドットフォントの読み込み
    const link = document.createElement('link');
    link.href = 'https://fonts.googleapis.com/css2?family=DotGothic16&display=swap';
    link.rel = 'stylesheet';
    document.head.appendChild(link);

    // フォントの変更
    link.onload = () => {
        const lyricsEle = document.getElementById('lyrics');
        lyricsEle.style.fontFamily = "'DotGothic16', sans-serif, Meiryo";
    };
}