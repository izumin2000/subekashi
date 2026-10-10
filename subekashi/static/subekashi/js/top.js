// 検索の表示設定が「全て表示」の場合は、検索画面と同じフォーム（search_form.js）を表示する
const isShownAllSearch = document.getElementById("search-forms") !== null;

const keywordElement = document.getElementById("keyword");
const isPC = window.innerWidth > 960; 
// 「全て表示」の場合は、表示したフォームの入力欄をsearch_form.jsで選択する
if (keywordElement && isPC && !isShownAllSearch) {
    keywordElement.focus();
    keywordElement.click();
}

if (isShownAllSearch) {
    window.addEventListener('load', function () {
        renderFilterStatus();
        document.querySelectorAll(FORM_QUERIES).forEach((formEle) => {
            formEle.addEventListener('change', renderFilterStatus);
        });
    });

    // 入力したフィルタで検索画面を開く
    document.getElementById("search-form").addEventListener('submit', (event) => {
        event.preventDefault();
        location.href = event.target.action + toQueryString(formToSongsQuery());
    });
}

// フォームの値を検索画面のURLクエリに変換する
// ラジオボタンは表示時から選択を変更した場合のみ含める（並び替え・界隈曲・ネタ曲は表示時にcookieの値が選択されており、含めなくても検索画面で同じ値が選択されるため）
function formToSongsQuery() {
    const query = {};
    const mediatypes = [];
    for (const formEle of document.querySelectorAll(FORM_QUERIES)) {
        if (formEle.id.startsWith("media-")) {
            if (formEle.checked) {
                mediatypes.push(formEle.id.split("-")[1]);
            }
            continue;
        }
        if (formEle.type == "radio") {
            if (formEle.checked && !formEle.defaultChecked) {
                query[formEle.name] = formEle.value;
            }
            continue;
        }
        query[formEle.name] = formEle.value;
    }
    query.mediatypes = mediatypes.join(",");
    return cleanQuery(query);
}

function songGuesserClick(id) {
    const imitateEle = document.getElementById("imitate");
    imitateEle.value = "";

    renderSongGuesser();
    imitateEle.value = id;
    renderFilterStatus();
}

function categoryClick(song) {
    document.getElementById("imitate").value = song.id;
    renderFilterStatus();
}

const newsDisplayEle = document.getElementById('single-news-display');
if (newsDisplayEle) {
    const newsArreyEle = document.createElement("div");
    newsArreyEle.innerHTML = newsDisplayEle.innerHTML;
    const newsEles = newsArreyEle.children;
    let currentIndex = 0;

    function showNews(newsEle_) {
        if(!newsEle_) return;

        const newsEle = newsEle_.cloneNode(true)
        newsDisplayEle.innerHTML = '';
        newsDisplayEle.appendChild(newsEle);
        const height = newsEle.clientHeight;
        newsDisplayEle.style.height = `${height}px`;

        setTimeout(() => {
            newsEle.style.opacity = '1';
            newsEle.style.transform = 'translateY(0px)';
        }, 1000);

        setTimeout(() => {
            newsEle.style.opacity = '0';
            newsEle.style.transform = 'translateY(-50px)';
        }, 10000);

        setTimeout(() => {
            newsEle.style.transform = 'translateY(50px)';
        }, 11000);
    }

    function showNextNews() {
        showNews(newsEles[currentIndex % newsEles.length])
        currentIndex++;
    }

    showNextNews();
    setInterval(showNextNews, 11000);
}


if (isShownAd) {
    async function setad(view, click) {
        const csrf = await getCSRF();
        await fetch(
            baseURL() + "/api/ad/" + adId + "/?format=json",
            {
                method: "PUT",
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrf
                },
                body: JSON.stringify(
                    {
                        "view": view,
                        "click": click,
                    }
                ),
                credentials: 'include',
            }
        )
    };

    let onceView = false;
    window.addEventListener('scroll', async function () {
        const target_position = document.querySelector('#ad').getBoundingClientRect().top;
            if (target_position <= window.innerHeight && onceView !== true) {
                onceView = true;
                await setad(adView + 1, adClick);
            }
        }
    );

    let onceClick = false;
    function onYouTubeIframeAPIReady() {
        var player = new YT.Player('player', {
            events: {
                'onStateChange': onPlayerStateChange
            }
        });

        async function onPlayerStateChange(event) {
            if ((event.data == YT.PlayerState.PLAYING) && (onceClick !== true)) {
                await setad(adView + 1, adClick + 1);
                onceClick = true;
            }
        }
    }
}
