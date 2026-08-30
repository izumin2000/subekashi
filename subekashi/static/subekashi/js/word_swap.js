// 作成結果（ai_result.html）の単語クリック入れ替え機能
(function () {
    let activePopup = null;

    function closeActivePopup() {
        if (activePopup) {
            activePopup.remove();
            activePopup = null;
        }
    }

    async function fetchCandidates(word, hinshi, katsuyou) {
        const params = new URLSearchParams({ word: word, hinshi: hinshi, katsuyou: katsuyou });
        try {
            const res = await fetch(baseURL() + "/api/word/candidates/?" + params.toString());
            // res.ok=falseは候補が0件（正常系のレスポンス）とは別物で、
            // スロットル（429）やサーバーエラーの可能性があるため、
            // 呼び出し元が「候補なし」と誤解しないようnull（通信エラー扱い）を返す
            if (!res.ok) return null;
            const data = await res.json();
            return data.candidates || [];
        } catch (e) {
            return null;
        }
    }

    async function postSwap(baseId, tokenIndex, candidate) {
        const csrf = await getCSRF();
        try {
            return await fetch(baseURL() + "/api/ai/swap/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrf
                },
                body: JSON.stringify({
                    base_id: baseId,
                    token_index: tokenIndex,
                    candidate: candidate
                })
            });
        } catch (e) {
            return null;
        }
    }

    // janomeは文脈依存の統計的トークナイザのため、候補語を入れた新しい歌詞を
    // 再トークナイズすると周辺のトークン境界が変わることが理論上あり得る。
    // data-token-indexだけを使い回すとズレて意図しない単語を壊しかねないため、
    // サーバーが返す再トークナイズ済みのtokensを使って行のDOMを丸ごと作り直す
    function renderLyricTokens(lyricEle, aiId, tokens, swappedSurfaces) {
        lyricEle.dataset.aiId = aiId;
        lyricEle.innerHTML = "";

        tokens.forEach(function (token) {
            if (!token.is_replaceable) {
                const fixed = document.createElement("span");
                fixed.className = "word-token-fixed";
                fixed.textContent = token.surface;
                lyricEle.appendChild(fixed);
                return;
            }

            const wrap = document.createElement("span");
            wrap.className = "word-token-wrap";

            const span = document.createElement("span");
            span.className = "word-token";
            if (swappedSurfaces.has(token.surface)) {
                span.classList.add("word-token-swapped");
            }
            span.setAttribute("role", "button");
            span.setAttribute("tabindex", "0");
            span.dataset.aiId = aiId;
            span.dataset.tokenIndex = token.index;
            span.dataset.word = token.surface;
            span.dataset.hinshi = token.hinshi;
            span.dataset.katsuyou = token.katsuyou;
            span.textContent = token.surface;

            wrap.appendChild(span);
            lyricEle.appendChild(wrap);
        });
    }

    function openCandidatePopup(tokenEle, candidates) {
        closeActivePopup();

        const popup = document.createElement("div");
        popup.className = "word-candidate-popup";

        candidates.forEach(function (candidate) {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.textContent = candidate;
            btn.addEventListener("click", async function (event) {
                event.stopPropagation();

                const res = await postSwap(
                    tokenEle.dataset.aiId,
                    tokenEle.dataset.tokenIndex,
                    candidate
                );
                closeActivePopup();
                if (res && res.ok) {
                    const data = await res.json();
                    const lyricEle = tokenEle.closest(".lyric");

                    if (lyricEle && Array.isArray(data.tokens)) {
                        // 今回入れ替えた単語（および同じ行で過去に入れ替えた単語）を
                        // 引き続き「入れ替え済み」として色分け表示するため、
                        // 行ごとに入れ替え済みの表記を記憶しておく
                        if (!lyricEle._swappedSurfaces) {
                            lyricEle._swappedSurfaces = new Set();
                        }
                        lyricEle._swappedSurfaces.add(candidate);
                        renderLyricTokens(lyricEle, data.id, data.tokens, lyricEle._swappedSurfaces);
                    } else {
                        // tokensが無い場合のフォールバック（最低限の見た目更新のみ）
                        tokenEle.textContent = candidate;
                        tokenEle.classList.add("word-token-swapped");
                        if (lyricEle) lyricEle.dataset.aiId = data.id;
                    }

                    showToast("ok", "入れ替えた歌詞を保存しました。");
                } else {
                    showToast("error", "入れ替えに失敗しました。");
                }
            });
            popup.appendChild(btn);
        });

        // role="button"を持つtokenEleの子要素にせず、兄弟要素として
        // 挿入する（インタラクティブ要素の入れ子を避けるため）
        tokenEle.parentElement.appendChild(popup);
        activePopup = popup;
    }

    async function onWordTokenActivate(tokenEle) {
        if (activePopup && activePopup.parentElement === tokenEle.parentElement) {
            closeActivePopup();
            return;
        }

        const word = tokenEle.dataset.word;
        const hinshi = tokenEle.dataset.hinshi;
        const katsuyou = tokenEle.dataset.katsuyou;
        const candidates = await fetchCandidates(word, hinshi, katsuyou);

        if (candidates === null) {
            showToast("error", "通信エラーが発生しました。");
            return;
        }

        if (candidates.length === 0) {
            showToast("info", "入れ替え候補が見つかりませんでした。");
            return;
        }

        openCandidatePopup(tokenEle, candidates);
    }

    document.addEventListener("click", function (event) {
        const tokenEle = event.target.closest(".word-token");
        if (tokenEle) {
            onWordTokenActivate(tokenEle);
            return;
        }
        if (!event.target.closest(".word-candidate-popup")) {
            closeActivePopup();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key !== "Enter" && event.key !== " ") return;
        const tokenEle = event.target.closest(".word-token");
        if (!tokenEle) return;
        event.preventDefault();
        onWordTokenActivate(tokenEle);
    });
})();
