// 検索の表示設定が「全て表示」の場合（top.htmlのisShownAllSearch）は、検索画面と同じフォームを表示する
// その場合のみtop.htmlでsearch_form.jsをこのファイルより先に読み込み、FORM_QUERIES・initSearchForm・collectFormQuery・renderFilterStatus・toQueryString・renderSongGuesserを使う
const keywordElement = document.getElementById("keyword");
const isPC = window.innerWidth > 960; 
// 「全て表示」の場合は、表示したフォームの入力欄をsearch_form.jsで選択する
if (keywordElement && isPC && !isShownAllSearch) {
    keywordElement.focus();
    keywordElement.click();
}

if (isShownAllSearch) {
    window.addEventListener('load', function () {
        initSearchForm();
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
    return collectFormQuery((radioEle) => radioEle.defaultChecked ? {} : { [radioEle.name]: radioEle.value });
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

// ニュースの「1つずつ表示」
// setTimeout・setIntervalは非表示のタブで間引かれ、切り替えとアニメーションの順番が崩れるため、requestAnimationFrameで経過時間を数えて切り替える
const newsDisplayEle = document.getElementById('single-news-display');
if (newsDisplayEle) {
    // 前のニュースが上に消え始めてから、次のニュースを下から表示し終えるまでの時間（top.cssのtransitionと合わせる）
    const NEWS_ENTER_DURATION = 2000;
    // 下から表示し終えてから、上に消え始めるまでの時間
    const NEWS_SHOWN_DURATION = 8000;
    const newsEles = Array.from(newsDisplayEle.children);
    const newsDotsEle = document.getElementById('single-news-dots');
    let currentIndex = -1;
    let elapsed = 0;
    let lastTime = null;

    // ニュースが1つの場合は切り替えないため、ボタンを表示しない
    const newsDotEles = newsEles.length > 1 ? newsEles.map((_, index) => {
        const newsDotEle = document.createElement('button');
        newsDotEle.type = 'button';
        newsDotEle.setAttribute('aria-label', `${index + 1}つ目のニュースを表示`);
        newsDotEle.addEventListener('click', () => showNews(index));
        newsDotsEle.appendChild(newsDotEle);
        return newsDotEle;
    }) : [];

    function showNews(index) {
        if (index === currentIndex) return;

        const prevNewsEle = newsEles[currentIndex];
        if (prevNewsEle) {
            prevNewsEle.classList.replace('is-active', 'is-leaving');
        }

        // 上に消えたニュースを下の位置に戻してから、下から表示する
        const newsEle = newsEles[index];
        newsEle.classList.remove('is-leaving');
        void newsEle.offsetWidth;
        newsEle.classList.add('is-active');

        newsDotEles.forEach((newsDotEle, dotIndex) => {
            newsDotEle.style.removeProperty('--progress');
            if (dotIndex === index) {
                newsDotEle.setAttribute('aria-current', 'true');
            } else {
                newsDotEle.removeAttribute('aria-current');
            }
        });

        currentIndex = index;
        elapsed = 0;
    }

    function updateNews(time) {
        // 非表示のタブではrequestAnimationFrameが止まるため、戻ったときに経過時間が飛ばないように1フレームの経過時間に上限を設ける
        if (lastTime !== null) {
            elapsed += Math.min(time - lastTime, 100);
        }
        lastTime = time;

        if (elapsed >= NEWS_ENTER_DURATION + NEWS_SHOWN_DURATION) {
            showNews((currentIndex + 1) % newsEles.length);
        }
        // 進捗は下から表示し終えてから、上に消え始めるまでの間で表示する
        const progress = Math.max(elapsed - NEWS_ENTER_DURATION, 0) / NEWS_SHOWN_DURATION;
        newsDotEles[currentIndex].style.setProperty('--progress', progress);
        requestAnimationFrame(updateNews);
    }

    if (newsEles.length) {
        showNews(0);
    }
    if (newsEles.length > 1) {
        requestAnimationFrame(updateNews);
    }
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
