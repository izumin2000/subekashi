// 生成結果（ai_result.html）の単語クリック入れ替え機能
(function () {
    let activePopup = null;

    function closeActivePopup() {
        if (activePopup) {
            activePopup.remove();
            activePopup = null;
        }
    }

    async function fetchCandidates(word, hinshi) {
        const params = new URLSearchParams({ word: word, hinshi: hinshi });
        try {
            const res = await fetch(baseURL() + "/api/word/candidates/?" + params.toString());
            if (!res.ok) return [];
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
                    tokenEle.textContent = candidate;
                    tokenEle.classList.add("word-token-swapped");
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
        const candidates = await fetchCandidates(word, hinshi);

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
