// 検索フォーム（components/search_form.html）の操作。検索画面とトップ画面の検索で共通
// 関数・定数はページのJS（songs.js・top.js）から使うため、ページのJSより先に読み込む
// ページのJSでは、ここにある関数と同じ名前の関数を定義しない
// base.jsのgetCookie・getSongGuessersを使う。また、ページのJSでsongGuesserClick・categoryClickを定義する（base.jsのクリックのイベントから呼ばれる）
var songGuesserController;
const FORM_QUERIES = '#search-forms input';

window.addEventListener('DOMContentLoaded', function () {
    // 画面幅の変更やフォントの読み込みでラジオボタンの行数が変わった場合に、全て表示するボタンの表示と下端のぼかしを更新する
    // ボタンの表示が遅れて切り替わらないよう、loadを待たずに監視する
    new ResizeObserver(() => {
        updateSearchFormRadiosToggle();
        updateSearchFormRadiosScrollEnd();
    }).observe(document.getElementById("search-form-radios"));

    document.getElementById("imitate").addEventListener("input", renderSongGuesser);
});

// フォームの選択をcookie・ブラウザが復元した状態に合わせ、操作のイベントを登録する
// ページのJSのloadで、フォームの値を使う処理（検索・バッジの表示）より先に呼ぶ
function initSearchForm() {
    restoreFormValuesFromCookies();
    syncSearchForm();
    focusSearchForm(getSearchFormName());
    document.getElementById("search-form-radios").addEventListener('scroll', updateSearchFormRadiosScrollEnd);

    document.querySelectorAll('input[name="search-form"]').forEach((radioEle) => {
        radioEle.addEventListener('change', () => {
            showSearchForm(radioEle.value);
            // キーボードでラジオボタンを選択している場合は、続けて選択できるようフォーカスを移さない
            if (!radioEle.matches(':focus-visible')) {
                focusSearchForm(radioEle.value);
            }
            setSearchFormRadiosExpanded(false);
            scrollToSearchFormRadio(radioEle.value, "smooth");
        });
    });

    document.getElementById("search-form-radios-toggle").addEventListener('click', () => {
        const isExpanded = !document.getElementById("search-form-radios").classList.contains("expanded");
        setSearchFormRadiosExpanded(isExpanded);
        if (!isExpanded) {
            scrollToSearchFormRadio(getSearchFormName(), "auto");
        }
    });
}

window.addEventListener('pageshow', function (event) {
    if (event.persisted) {
        restoreFormValuesFromCookies();
        syncSearchForm();
        renderFilterStatus();
    }
});

// 選択されているフォームのラジオボタンの値（テンプレートで必ず1つ選択されるが、選択されていない場合はキーワードとする）
function getSearchFormName() {
    const radioEle = document.querySelector('input[name="search-form"]:checked');
    return radioEle ? radioEle.value : "keyword";
}

// 選択されているラジオボタンのフォームを表示する
// ブラウザバック時はブラウザがラジオボタンの選択状態を復元するため、サーバーが表示したフォームとずれないようにする
function syncSearchForm() {
    const searchFormName = getSearchFormName();
    showSearchForm(searchFormName);
    scrollToSearchFormRadio(searchFormName, "auto");
    updateSearchFormRadiosScrollEnd();
}

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
    const radioEle = Array.from(document.querySelectorAll(FORM_QUERIES)).find((ele) => ele.name === filter && ele.value === value);
    if (radioEle) {
        radioEle.checked = true;
    }
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

// ラジオボタンが縦にはみ出る場合のみ、全て表示するボタンを表示する
// 展開中ははみ出るかどうかを判定できないため、一時的に折りたたんだ状態にして判定する
function updateSearchFormRadiosToggle() {
    const radiosEle = document.getElementById("search-form-radios");
    const isExpanded = radiosEle.classList.contains("expanded");
    radiosEle.classList.remove("expanded");
    const isOverflow = radiosEle.scrollHeight > radiosEle.clientHeight + 1;
    radiosEle.classList.toggle("expanded", isExpanded);
    document.getElementById("search-form-radios-toggle").hidden = !isOverflow;
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
    const imitateTitle = document.getElementById("imitate").value;
    getSongGuessers(imitateTitle, "song-guesser", songGuesserController.signal, renderSongGuesser);
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

// フォームの値をクエリに変換する
// 選択されているラジオボタンは、radioToQuery(ラジオボタン)が返すクエリに変換する（検索画面とトップ画面で変換が異なるため）
function collectFormQuery(radioToQuery) {
    let query = {};
    const mediatypes = [];
    for (const formEle of document.querySelectorAll(FORM_QUERIES)) {
        if (formEle.id.startsWith("media-")) {
            if (formEle.checked) {
                mediatypes.push(formEle.id.split("-")[1]);
            }
            continue;
        }
        if (formEle.type == "radio") {
            if (formEle.checked) {
                query = { ...query, ...radioToQuery(formEle) };
            }
            continue;
        }
        query[formEle.name] = formEle.value;
    }
    query.mediatypes = mediatypes.join(",");
    query = cleanQuery(query);
    return query;
}

// フォームの値を曲のAPI（html/song_cards）のクエリに変換する
function formToQuery() {
    return collectFormQuery((radioEle) => {
        if (radioEle.name == "songrange") {
            return songrangeToQuery(radioEle.value);
        }
        if (radioEle.name == "jokerange") {
            return isjokeToQuery(radioEle.value);
        }
        return { [radioEle.name]: radioEle.value };
    });
}

// フォームの値がデフォルト値から変更されているか
function isFilteredForm(formEle) {
    if (formEle.type == "checkbox") {
        return formEle.checked;
    }
    // ラジオボタンはデフォルト値(data-default、指定なし)以外が選択されているか
    if (formEle.type == "radio") {
        return formEle.checked && !formEle.hasAttribute("data-default");
    }
    return formEle.value !== "";
}

// YouTube関連のフィルタ/並び替えによって自動で適用されるフィルタの案内を表示する
// 判定はlib/song_filterset.pyのSongFilter.qs・lib/query_utils.pyのhas_*_filter_or_sort / has_upload_time_sortと揃える
function renderOverrideInfos(query) {
    // YouTube関連のフィルタ・並び替え（lib/query_utils.pyのYOUTUBE_FILTERS・YOUTUBE_SORTS）
    const youtubeQueries = JSON.parse(document.getElementById("youtube-queries").textContent);
    const sort = query.sort;
    const overrides = {
        "media": (youtubeQueries.filters.some((key) => key in query) || youtubeQueries.sorts.includes(sort)) && !("mediatypes" in query),
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
