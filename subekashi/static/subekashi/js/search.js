var page = 1, songGuesserController;
const FORMQUERYS = 'input:not(#search-button), select'

COOKIE_FORMS = ["songrange", "jokerange", "sort"];
window.addEventListener('load', async function () {
    document.getElementById("keyword").focus();
    document.getElementById("keyword").click();

    renderSearch();

    document.querySelectorAll(FORMQUERYS).forEach((formEle) => {
        formEle.addEventListener('change', () => {
            renderSearch();
        });
    });

    for (cookieForm of COOKIE_FORMS) {
        cookieFormEle = document.getElementById(cookieForm);
        cookieFormEle.addEventListener('change', (event) => {
            setSearchCookie(event);
        });
    };
})

function getInputIds() {
    const inputs = document.querySelectorAll(FORMQUERYS);
    ids = Array.from(inputs).map(input => input.id);
    return ids;
}

function setSearchCookie(e) {
    DETAILS_ID = "isdetail"
    id = e.target.id ? e.target.id : DETAILS_ID;
    if (id == DETAILS_ID) {
        const cookieFormEle = document.getElementById(DETAILS_ID);
        value = cookieFormEle.open ? "False" : "True";
    } else {
        const cookieFormEle = document.getElementById(id);
        value = cookieFormEle.value;
    }
    setCookie(`search_${id}`, value);
}

function getInputIds() {
    const inputs = document.querySelectorAll(FORMQUERYS);
    ids = Array.from(inputs).map(input => input.id);
    return ids;
}

function renderSongGuesser() {
    // 以前のリクエストが存在する場合、そのリクエストをキャンセルする
    if (songGuesserController) {
        songGuesserController.abort();
    }

    songGuesserController = new AbortController();
    imitateTitle = document.getElementById("imitate").value;
    getSongGuessers(imitateTitle, "song-guesser", songGuesserController.signal);
}

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

// TODO ?songrange=で直接GETできるようにする
function songrangeToQuery(songrange) {
    if (songrange == "subeana") {
        return { "issubeana": true };
    } else if (songrange == "xx") {
        return { "issubeana": false };
    };
    return {};
}

function isjokeToQuery(isjoke) {
    if (isjoke == "only") {
        return { "isjoke": true };
    } else if (isjoke == "off") {
        return { "isjoke": false };
    };
    return {};
}

function cleanQuery(query) {
    Object.keys(query).forEach(key => {
        if (query[key] === "") {
            delete query[key];
        }
    })
    
    return query;
}

function formToQuery() {
    query = {};
    formIds = getInputIds();
    checkboxIds = formIds.filter(id => id.startsWith("is"));
    for (formId of formIds) {
        // checkboxなら
        if (checkboxIds.includes(formId)) {
            value = document.getElementById(formId).checked;
            if (!value) {
                continue;
            }
            query[formId] = "True";
            continue;
        }
        value = document.getElementById(formId).value;
        if (formId == "songrange") {
            query = { ...query, ...songrangeToQuery(value) };
            continue;

        }
        if (formId == "jokerange") {
            query = { ...query, ...isjokeToQuery(value) };
            continue;
        }
        query[formId] = value;
    }
    query = cleanQuery(query);
    return query;
}

// queryからURLクエリの文字列に変換 例：{"hoge":1, "isok": true}なら"?hoge=1&isok=True}"
function toQueryString(query) {
    const params = Object.entries(query)
        .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
        .join('&');
    return params ? `?${params}` : '';
}

var SearchController, songCardsEle;
function renderSearch() {
    // 以前のリクエストが存在する場合、そのリクエストをキャンセルする
    if (SearchController) {
        SearchController.abort();
    }

    page = 1;
    songCardsEle = document.getElementById("song-cards");
    while (songCardsEle.firstChild) {
        songCardsEle.removeChild(songCardsEle.firstChild);
    }

    loadingEle = stringToHTML(`<img src="${baseURL()}/static/subekashi/image/loading.gif" id="loading" alt='loading'></img>`);
    songCardsEle.appendChild(loadingEle);

    SearchController = new AbortController();
    search(SearchController.signal, page);
}

async function getsongCards(query) {
    try {
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
        document.getElementById("loading").remove();
    }

    if (!songCards) {
        loadingEle = stringToHTML(`<img src="${baseURL()}/static/subekashi/image/loading.gif" id="loading" alt='loading'></img>`);
        songCardsEle.appendChild(loadingEle);
        return;
    }

    // 検索結果を正しく描画するループを復元
    for (let songCard of songCards) {
        if (signal.aborted) {
            return;
        };

        let songCardEle = stringToHTML(songCard);
        songCardsEle.appendChild(songCardEle);
        await sleep(0.05);
    }

    // #next-page-loadingを監視
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