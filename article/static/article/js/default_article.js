// 本文の画像をクリック（タップ）すると画面いっぱいに表示する（#1303）
const imageViewerEle = document.getElementById("image-viewer");
const imageViewerImgEle = document.getElementById("image-viewer-img");

document.getElementById("article-text").addEventListener("click", (event) => {
    const imgEle = event.target.closest("img");
    // リンクの中の画像は、リンク先への移動を妨げないよう対象外にする
    if (!imgEle || imgEle.closest("a")) {
        return;
    }

    imageViewerImgEle.src = imgEle.currentSrc || imgEle.src;
    imageViewerImgEle.alt = imgEle.alt;
    imageViewerEle.showModal();
});

// 画像・背景・閉じるボタンのどこをクリックしても閉じる（Escキーはdialogが標準で閉じる）
imageViewerEle.addEventListener("click", () => imageViewerEle.close());
