// フォームの切り替え等はsearch_form.jsで行う
var page = 1;
const COOKIE_FORMS = ["songrange", "jokerange", "sort"];

window.addEventListener('load', async function () {
    renderSearch();

    document.querySelectorAll(FORM_QUERIES).forEach((formEle) => {
        formEle.addEventListener('change', async () => {
            if (COOKIE_FORMS.includes(formEle.name)) {
                // is_saved_selectがonの場合のみcookieに保存
                const cookies = getCookie();
                const isSavedSelect = cookies['is_saved_select'] || 'on';
                if (isSavedSelect === 'on') {
                    await saveCookieToBackend(formEle.name, formEle.value);
                }
            }
            renderSearch();
        });
    });
});

// cookie formの内容をバックエンドに伝える
async function saveCookieToBackend(name, value) {
    const url = `${baseURL()}/songs/`;
    const csrfToken = await getCSRF();
    const formData = new FormData();
    formData.append(name, value);

    await fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken
        },
        body: formData,
        cache: 'no-cache',
        credentials: 'same-origin'
    }).catch(() => {});
}

document.getElementById("search-button").addEventListener("click", renderSearch);

function songGuesserClick(id) {
    imitateEle = document.getElementById("imitate");
    imitateEle.value = "";

    renderSongGuesser();
    imitateEle.value = id;
    renderSearch();
}

function categoryClick(song) {
    imitateEle = document.getElementById("imitate");
    imitateEle.value = song.id;
    renderSearch();
}

var SearchController, songCardsEle;
function renderSearch() {
    if (SearchController) {
        SearchController.abort();
    }

    renderFilterStatus();

    page = 1;
    songCardsEle = document.getElementById("song-cards");
    while (songCardsEle.firstChild) {
        songCardsEle.removeChild(songCardsEle.firstChild);
    }

    loadingEle = stringToHTML(`<span class="loading"></span>`);
    songCardsEle.appendChild(loadingEle);

    SearchController = new AbortController();
    search(SearchController.signal, page);
}

async function getsongCards(query) {
    try {
        query["is_limited"] = "False";
        const songCards = await exponentialBackoff(`html/song_cards${toQueryString(query)}`, "search", renderSearch);
        return songCards;
    } catch(error) {
        return error;
    }
}

async function search(signal, page) {
    query = formToQuery();
    query["page"] = page;

    const songCards = await getsongCards(query);

    if (page == 1) {
        loadingEle.remove();
    }

    if (!songCards) {
        loadingEle = stringToHTML(`<span class="loading"></span>`);
        songCardsEle.appendChild(loadingEle);
        return;
    }

    for (let songCard of songCards) {
        if (signal.aborted) {
            return;
        };

        let songCardEle = stringToHTML(songCard);
        songCardsEle.appendChild(songCardEle);
        await sleep(0.05);
    }

    const loadingElement = document.getElementById('next-page-loading');
    if (loadingElement) {
        observer.observe(loadingElement);
    }
}

// #next-page-loadingが映ったら次のページを表示
const observer = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            paging();
        }
    })
}, { threshold: 1.0 })

// 2ページ目以降を表示
function paging() {
    page++;
    document.getElementById("next-page-loading").remove();
    search(SearchController.signal, page);
}
