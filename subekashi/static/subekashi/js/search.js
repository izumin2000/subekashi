var page = 1;


isFormDirty = false;        // フォームに変更があったかを検知
COOKIE_FORMS = ["songrange", "jokerange", "sort"];
window.addEventListener('load', async function () {
    renderSearch();

    document.querySelectorAll('input:not(#menu), select').forEach((formEle) => {
        formEle.addEventListener('change', () => {
            isFormDirty = true;
            renderSearch();
        });
    });

    for (cookieForm of COOKIE_FORMS) {
        cookieFormEle = document.getElementById(cookieForm);
        cookieFormEle.addEventListener('change', (event) => {
            setSearchCookie(event);
        });
    };
});


function getInputIds() {
    const inputs = document.querySelectorAll('input, select');
    ids = Array.from(inputs).map(input => input.id);
    return ids;
};


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
    console.log(id, value);
    setCookie(`search_${id}`, value);
};


function getInputIds() {
    const inputs = document.querySelectorAll('input, select');
    ids = Array.from(inputs).map(input => input.id);
    return ids;
};


function keywordToQuery() {
    return {}
};


function songrangeToQuery(songrange) {
    if (songrange == "subeana") {
        return { "issubeana": true };
    } else if (songrange == "xx") {
        return { "issubeana": false };
    };
    return {};
};


function isjokeToQuery(isjoke) {
    if (isjoke == "only") {
        return { "isjoke": true };
    } else if (isjoke == "off") {
        return { "isjoke": false };
    };
    return {};
};


function cleanQuery(query) {
    Object.keys(query).forEach(key => {
        if (query[key] === "") {
            delete query[key];
        }
    });
    
    return query;
};


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
        if (formId == "keyword") {
            query = { ...query, ...keywordToQuery(value) };
            continue;
        }
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
    query["page"] = page;
    return query;
};


// queryからURLクエリの文字列に変換 例：{"hoge":1, "isok": true}なら"?hoge=1&isok=True}"
function toQueryString(query) {
    const params = Object.entries(query)
        .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
        .join('&');
    return params ? `?${params}` : '';
};


function paging() {
    page++;
    document.getElementById("loading").remove();
    search(SearchController.signal, page);
};


// #loadingが映ったらpagingを実行
const observer = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            paging();
        };
    });
}, { threshold: 1.0 });


var SearchController;
function renderSearch() {
    // 以前のリクエストが存在する場合、そのリクエストをキャンセルする
    if (SearchController) {
        SearchController.abort();
    };

    SearchController = new AbortController();
    search(SearchController.signal, page);
};


async function search(signal, page) {
    var songCardsEle = document.getElementById("song-cards");
    while ((songCardsEle.firstChild) && (page == 1)) {
        songCardsEle.removeChild(songCardsEle.firstChild);
    }

    try {
        query = formToQuery();
        query["page"] = page;
        songCards = await getJson(`html/song_cards${toQueryString(query)}`);
        for (songCard of songCards) {
            // キャンセルが要求されているか確認
            if (signal.aborted) {
                return;
            };

            songCardEle = stringToHTML(songCard);
            songCardsEle = document.getElementById("song-cards");
            songCardsEle.appendChild(songCardEle);
            await sleep(0.05);
        }

        // #loadingを監視
        const loadingElement = document.querySelector('#loading');
        if (loadingElement) {
            observer.observe(loadingElement);
        };
    } catch (error) {
        console.error(error);
    };
};