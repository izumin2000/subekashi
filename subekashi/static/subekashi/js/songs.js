var page = 1, songGuesserController;
const FORMQUERYS = 'input:not(#search-button), select'
const COOKIE_FORMS = ["songrange", "jokerange", "sort"];

window.addEventListener('load', async function () {
    document.getElementById("keyword").focus();
    document.getElementById("keyword").click();

    restoreFormValuesFromCookies();
    renderSearch();

    document.querySelectorAll(FORMQUERYS).forEach((formEle) => {
        formEle.addEventListener('change', async () => {
            if (COOKIE_FORMS.includes(formEle.id)) {
                await saveCookieToBackend(formEle.id, formEle.value);
            }
            renderSearch();
        });
    });

    const detailsEle = document.getElementById("isdetail");
    if (detailsEle) {
        detailsEle.addEventListener('toggle', async (event) => {
            const value = event.target.open ? "True" : "False";
            await saveCookieToBackend("isdetail", value);
        });
    }
});

window.addEventListener('pageshow', function (event) {
    if (event.persisted) {
        restoreFormValuesFromCookies();
    }
});

// 他のページからブラウザバックしたとき、cookie formの内容をcookieの値に反映する
function restoreFormValuesFromCookies() {
    const cookies = getCookie();
    const cookieFormMappings = [
        { cookieName: 'search_isdetail', elementId: 'isdetail', isDetailsElement: true },
        { cookieName: 'search_songrange', elementId: 'songrange' },
        { cookieName: 'search_jokerange', elementId: 'jokerange' },
        { cookieName: 'search_sort', elementId: 'sort' }
    ];

    cookieFormMappings.forEach(({ cookieName, elementId, isDetailsElement }) => {
        const cookieValue = cookies[cookieName];
        if (cookieValue) {
            const element = document.getElementById(elementId);
            if (element) {
                if (isDetailsElement) {
                    element.open = (cookieValue === 'True');
                } else if (element.value !== cookieValue) {
                    element.value = cookieValue;
                }
            }
        }
    });
}

// cookie formの内容をバックエンドに伝える
async function saveCookieToBackend(name, value) {
    const paramMap = {
        "isdetail": "isdetail",
        "songrange": "issubeana",
        "jokerange": "isjoke",
        "sort": "sort"
    };
    const param = paramMap[name];
    if (param) {
        const url = `${baseURL()}/songs/?${param}=${encodeURIComponent(value)}`;
        await fetch(url, {
            method: 'GET',
            cache: 'no-cache',
            credentials: 'same-origin'
        }).catch(() => {});
    }
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
        if (formId.startsWith("media-"))
        {
            /**@type {string} */
            const media = formId.split("-")[1]
            const checked = document.getElementById(formId).checked;
            query.mediatypes ??= "";
            if(checked){
                query.mediatypes += (query.mediatypes.length===0 ? "" : ",") + media;
            }
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