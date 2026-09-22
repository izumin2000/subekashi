const keywordElement = document.getElementById("keyword");
const isPC = window.innerWidth > 960; 
if (keywordElement && isPC) {
    keywordElement.focus();
    keywordElement.click();
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
