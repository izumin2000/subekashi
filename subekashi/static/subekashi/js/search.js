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

const KEY_ALIAS = {
    ":" : ["：", "=", "＝"],
    "title": ["Title", "t", "T", "タイトル"],
    "channel": ["Channel", "c", "C", "チャンネル名"],
    "lyrics": ["Lyrics", "l", "L", "歌詞"],
    "url": ["URL", "Url", "u", "U", "link", "Link"],
    "songrange": ["SongRange", "Songrange", "SR", "sr", "界隈曲の種類", "種類"],
    "jokerange": ["JokeRange", "Jokerange", "JR", "jr", "ネタ曲", "ネタ"],
    "sort": ["Sort", "s", "S", "並び替え", "ソート"],
    "islack": ["IsLack", "isLack", "Islack", "ir", "IR", "作成途中"],
    "isdraft": ["IsDraft", "isDraft", "Isdraft", "id", "ID", "作成途中"], 
    "isoriginal": ["IsOriginal", "isOriginal", "Isoriginal", "io", "IO", "オリジナル模倣曲", "オリジナル模倣", "オリジナル"],
    "isinst": ["IsInst", "isInst", "Isinst", "ii", "II", "インスト曲", "インスト"]
}

// TODO スラッシュコマンドの実装
function clean_keyword(query) {
    for (let key in KEY_ALIAS) {
        KEY_ALIAS[key].forEach(KEY_ALIAS => {
            const regex = new RegExp(`\\b${KEY_ALIAS}\\b`, 'g'); // 単語全体に一致
            query = query.replace(regex, key);
        });
    }
    return query;
}


function keywordToQuery(keyword) {
    // TODO コマンドの処理
    return { "keyword" : keyword }
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

    SearchController = new AbortController();
    search(SearchController.signal, page);
}

var retry = 0;
async function search(signal, page) {
    loadingEle = stringToHTML(`<img src="${baseURL()}/static/subekashi/image/loading.gif" id="loading" alt='loading'></img>`)
    songCardsEle.appendChild(loadingEle)

    try {
        query = formToQuery();
        query["page"] = page;
        let songCards = await getJson(`html/song_cards${toQueryString(query)}`);
        document.getElementById("loading").remove();
        for (let songCard of songCards) {
            // キャンセルが要求されているか確認
            if (signal.aborted) {
                return;
            };

            let songCardEle = stringToHTML(songCard);
            songCardsEle.appendChild(songCardEle);
            await sleep(0.05);
        }

        // #loadingを監視
        const loadingElement = document.querySelector('#loading');
        if (loadingElement) {
            observer.observe(loadingElement);
        }

        retry = 0;
    } catch (error) {
        if (retry < 6) {
            await sleep(0.2 * 2 ** (retry + 1));
            renderSearch();
            retry++;
            return;
        }

        const errorStr = "<p class='warning'><i class='warning fas fa-exclamation-triangle'></i>エラーが発生しました。検索ボタンをもう一度押すか再読み込みしてください。</p>";
        const errorEle = stringToHTML(errorStr);
        songCardsEle.appendChild(errorEle);
        retry = 0;
    }
}

// #loadingが映ったら次のページを表示
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
    document.getElementById("loading").remove();
    search(SearchController.signal, page);
}