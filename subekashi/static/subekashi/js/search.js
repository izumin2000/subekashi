var page = 1;


// フォームに変更があったかを検知
isFormDirty = false;
window.addEventListener('load', async function () {
    renderSearch();
    document.querySelectorAll('input:not(#menu), select').forEach((form) => {
        form.addEventListener('change', () => {
            isFormDirty = true;
            renderSearch();
        });
    });
    // TODO cookieの読み込み
});


IGNORE_INPUTS = ["menu"]
function getInputIds() {
    const inputs = document.querySelectorAll('input, select');
    ids = Array.from(inputs).map(input => input.id);
    ids = ids.filter(id => !IGNORE_INPUTS.includes(id))
    return ids;
}


// TODO 実装
function keywordToQuery(keyword) {
    return {};
}


function songrangeToQuery(songrange) {
    if (songrange == "subeana") {
        return { "issubeana": true };
    } else if (songrange == "xx") {
        return { "issubeana": false };
    };
    return {}
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
    });
    
    return query;
}


function formToQuery() {
    query = {};
    form_ids = getInputIds();
    checkbox_ids = form_ids.filter(id => id.startsWith("is"));
    for (form_id of form_ids) {
        // checkboxなら
        if (checkbox_ids.includes(form_id)) {
            value = document.getElementById(form_id).checked;
            if (!value) {
                continue;
            }
            query[form_id] = "True";
            continue
        }
        value = document.getElementById(form_id).value;
        if (form_id == "keyword") {
            query = { ...query, ...keywordToQuery(value) };
            continue
        }
        if (form_id == "songrange") {
            query = { ...query, ...songrangeToQuery(value) };
            continue

        }
        if (form_id == "jokerange") {
            query = { ...query, ...isjokeToQuery(value) };
            continue
        }
        query[form_id] = value;
    }
    query = cleanQuery(query);
    query["page"] = page;
    return query;
}


// queryからURLクエリの文字列に変換 例：{"hoge":1, "isok": true}なら"?hoge=1&isok=True}"
function toQueryString(query) {
    const params = Object.entries(query)
        .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
        .join('&');
    return params ? `?${params}` : '';
}


function paging() {
    page++;
    document.getElementById("loading").remove();
    search(SearchController.signal, page);
}

// #loadingが映ったらpagingを実行
const observer = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            paging();
        }
    });
}, { threshold: 1.0 });


var SearchController;
function renderSearch() {
    // 以前のリクエストが存在する場合、そのリクエストをキャンセルする
    if (SearchController) {
        SearchController.abort();
    }

    SearchController = new AbortController();
    search(SearchController.signal, page);
}


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
            }

            songCardEle = stringToHTML(songCard);
            songCardsEle = document.getElementById("song-cards");
            songCardsEle.appendChild(songCardEle)        
            await sleep(0.05);
        }

        // #loadingを監視
        const loadingElement = document.querySelector('#loading');
        if (loadingElement) {
            observer.observe(loadingElement);
        }
    } catch (error) {
        console.error(error)
    }
}