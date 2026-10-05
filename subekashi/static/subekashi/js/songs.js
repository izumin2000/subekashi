var page = 1, songGuesserController;
const FORM_QUERIES = '#search-forms input';
const COOKIE_FORMS = ["songrange", "jokerange", "sort"];
// YouTube関連のフィルタ・並び替え（lib/query_utils.pyのYOUTUBE_FILTERS・YOUTUBE_SORTS）
const YOUTUBE_QUERIES = JSON.parse(document.getElementById("youtube-queries").textContent);

window.addEventListener('load', async function () {
    const searchFormName = document.querySelector('input[name="search-form"]:checked').value;
    focusSearchForm(searchFormName);
    scrollToSearchFormRadio(searchFormName, "auto");
    updateSearchFormRadiosScrollEnd();
    document.getElementById("search-form-radios").addEventListener('scroll', updateSearchFormRadiosScrollEnd);
    window.addEventListener('resize', updateSearchFormRadiosScrollEnd);

    restoreFormValuesFromCookies();
    renderSearch();

    document.querySelectorAll('input[name="search-form"]').forEach((radioEle) => {
        radioEle.addEventListener('change', () => {
            showSearchForm(radioEle.value);
            focusSearchForm(radioEle.value);
            setSearchFormRadiosExpanded(false);
            scrollToSearchFormRadio(radioEle.value, "smooth");
        });
    });

    document.getElementById("search-form-radios-toggle").addEventListener('click', () => {
        const isExpanded = !document.getElementById("search-form-radios").classList.contains("expanded");
        setSearchFormRadiosExpanded(isExpanded);
        if (!isExpanded) {
            scrollToSearchFormRadio(document.querySelector('input[name="search-form"]:checked').value, "auto");
        }
    });

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

window.addEventListener('pageshow', function (event) {
    if (event.persisted) {
        restoreFormValuesFromCookies();
        renderFilterStatus();
    }
});

// 他のページからブラウザバックしたとき、cookie formの内容をcookieの値に反映する
function restoreFormValuesFromCookies() {
    const cookies = getCookie();
    const isSavedSelect = cookies['is_saved_select'] || 'on';

    // is_saved_selectがoffの場合はcookieから復元しない
    if (isSavedSelect === 'off') {
        return;
    }

    // URLクエリで明示的に指定されている項目は、そちらを優先しcookieでの上書きは行わない
    const urlParams = new URLSearchParams(window.location.search);

    const cookieFormMappings = [
        { cookieName: 'search_songrange', filter: 'songrange', queryKeys: ['songrange', 'is_subeana'] },
        { cookieName: 'search_jokerange', filter: 'jokerange', queryKeys: ['jokerange', 'is_joke'] },
        { cookieName: 'search_sort', filter: 'sort', queryKeys: ['sort'] }
    ];

    cookieFormMappings.forEach(({ cookieName, filter, queryKeys }) => {
        if (queryKeys.some((key) => urlParams.has(key))) {
            return;
        }

        const cookieValue = cookies[cookieName];
        if (cookieValue) {
            setFormValue(filter, cookieValue);
        }
    });
}

// フィルタの値に該当するラジオボタンを選択する
function setFormValue(filter, value) {
    const radioEle = Array.from(document.querySelectorAll(`#search-forms input[name="${filter}"]`)).find((ele) => ele.value === value);
    if (radioEle) {
        radioEle.checked = true;
    }
}

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

// ラジオボタンで選択されたフォームのみを表示する
function showSearchForm(formName) {
    document.querySelectorAll(".search-form").forEach((searchFormEle) => {
        searchFormEle.hidden = searchFormEle.id !== `search-form-${formName}`;
    });
}

// 一部の行を隠しているラジオボタンを全て表示する
function setSearchFormRadiosExpanded(isExpanded) {
    document.getElementById("search-form-radios").classList.toggle("expanded", isExpanded);
    const toggleEle = document.getElementById("search-form-radios-toggle");
    toggleEle.setAttribute("aria-expanded", isExpanded);
    toggleEle.querySelector("i").className = isExpanded ? "fas fa-angle-up" : "fas fa-angle-down";
    toggleEle.querySelector("span").textContent = isExpanded ? "閉じる" : "全て表示";
    updateSearchFormRadiosScrollEnd();
}

// 一番下までスクロールした場合は下端のぼかしを外す
function updateSearchFormRadiosScrollEnd() {
    const radiosEle = document.getElementById("search-form-radios");
    const isScrollEnd = radiosEle.scrollTop + radiosEle.clientHeight >= radiosEle.scrollHeight - 1;
    radiosEle.classList.toggle("scroll-end", isScrollEnd);
}

// 選択したラジオボタンが隠れている行にある場合、その行が先頭に来るようにスクロールする
function scrollToSearchFormRadio(formName, behavior) {
    const radiosEle = document.getElementById("search-form-radios");
    const labelRect = document.querySelector(`label[for="search-form-radio-${formName}"]`).getBoundingClientRect();
    const radiosRect = radiosEle.getBoundingClientRect();
    const paddingTop = parseFloat(getComputedStyle(radiosEle).paddingTop);
    const isVisible = labelRect.top >= radiosRect.top + paddingTop - 0.5 && labelRect.bottom <= radiosRect.bottom + 0.5;
    if (!isVisible) {
        radiosEle.scrollBy({ top: labelRect.top - radiosRect.top - paddingTop, behavior });
    }
}

// PCの場合のみ、表示したフォームの最初のテキスト入力欄を選択する
function focusSearchForm(formName) {
    const isPC = window.innerWidth > 960;
    if (!isPC) {
        return;
    }

    const textEle = document.querySelector(`#search-form-${formName} input[type=text]`);
    if (textEle) {
        textEle.focus();
    }
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

document.getElementById("imitate").addEventListener("input", renderSongGuesser);
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

function songrangeToQuery(songrange) {
    if (songrange == "subeana") {
        return { "is_subeana": true };
    } else if (songrange == "xx") {
        return { "is_subeana": false };
    };
    return {};
}

function isjokeToQuery(isjoke) {
    if (isjoke == "only") {
        return { "is_joke": true };
    } else if (isjoke == "off") {
        return { "is_joke": false };
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
    let query = {};
    const mediatypes = [];
    for (const formEle of document.querySelectorAll(FORM_QUERIES)) {
        if (formEle.id.startsWith("media-")) {
            if (formEle.checked) {
                mediatypes.push(formEle.id.split("-")[1]);
            }
            continue;
        }
        if (formEle.type == "radio" && !formEle.checked) {
            continue;
        }
        if (formEle.name == "songrange") {
            query = { ...query, ...songrangeToQuery(formEle.value) };
            continue;
        }
        if (formEle.name == "jokerange") {
            query = { ...query, ...isjokeToQuery(formEle.value) };
            continue;
        }
        query[formEle.name] = formEle.value;
    }
    query.mediatypes = mediatypes.join(",");
    query = cleanQuery(query);
    return query;
}

// フォームの値がデフォルト値から変更されているか
function isFilteredForm(formEle) {
    if (formEle.type == "checkbox") {
        return formEle.checked;
    }
    // ラジオボタンは先頭の選択肢(全て)以外が選択されているか
    if (formEle.type == "radio") {
        return formEle.checked && formEle !== document.querySelector(`#search-forms input[name="${formEle.name}"]`);
    }
    return formEle.value !== "";
}

// YouTube関連のフィルタ/並び替えによって自動で適用されるフィルタの案内を表示する
// 判定はlib/song_filterset.pyのSongFilter.qs・lib/query_utils.pyのhas_*_filter_or_sort / has_upload_time_sortと揃える
function renderOverrideInfos(query) {
    const sort = query.sort;
    const overrides = {
        "media": (YOUTUBE_QUERIES.filters.some((key) => key in query) || YOUTUBE_QUERIES.sorts.includes(sort)) && !("mediatypes" in query),
        "view": ("view_lte" in query || ["view", "-view"].includes(sort)) && !("view_gte" in query),
        "like": ("like_lte" in query || ["like", "-like"].includes(sort)) && !("like_gte" in query),
        "upload_time": ["upload_time", "-upload_time"].includes(sort),
    };

    for (const [name, isOverridden] of Object.entries(overrides)) {
        document.getElementById(`${name}-override-info`).hidden = !isOverridden;
    }
}

// フィルタが有効なフォームのラジオボタンにバッジを表示する（並び替えは除く）
function renderFilterStatus() {
    renderOverrideInfos(formToQuery());

    document.querySelectorAll(".search-form:not(#search-form-sort)").forEach((searchFormEle) => {
        const isFiltered = Array.from(searchFormEle.querySelectorAll('input, select')).some(isFilteredForm) ||
            Array.from(searchFormEle.querySelectorAll('.override-info')).some((infoEle) => !infoEle.hidden);
        const formName = searchFormEle.id.replace("search-form-", "");
        document.querySelector(`label[for="search-form-radio-${formName}"]`).classList.toggle("filtered", isFiltered);
    });
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
