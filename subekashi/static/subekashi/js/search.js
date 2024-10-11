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


REMOVES = ["menu"]
function getInputIds() {
    const inputs = document.querySelectorAll('input');
    ids = Array.from(inputs).map(input => input.id);
    ids = ids.filter(id => !REMOVES.includes(id))
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


function formToQuery() {
    query = {};
    form_ids = getInputIds();
    for (form_id of form_ids) {
        value = document.getElementById(form_id).value;
        checkbox_ids = form_ids.filter(id => id.startsWith("is"));
        if (checkbox_ids.includes(form_id)) {
            value = document.getElementById(form_id).checked;
            if (!value) {
                continue;
            }
            value = "True";
        }
        if (form_id == "keyword") {
            query = { ...query, ...keywordToQuery(value) };
        }
        if (form_id == "songrange") {
            query = { ...query, ...songrangeToQuery(value) };
        }
        if (form_id == "isjoke") {
            query = { ...query, ...isjokeToQuery(value) };
        }

        if (value !== "") {
            query[form_id] = value;
        }
    }
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
        observer.observe(loadingElement);
    } catch (error) {
        console.error(error)
    }
}