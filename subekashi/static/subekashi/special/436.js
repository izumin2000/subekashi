function special() {
    'use strict';

    // 二重実行の防止
    if (document.getElementById('x-special-style')) return;

    // ---- 設定 ----------------------------------------------------------
    // 画面に映っているとき、レイアウトを適用しない歌詞
    const EXCLUDE_LINES = [
        '朽ちた。',
        '果てた。',
        '死んで、',
        '消えた。',
        '正義を騙る紛い物が！',
    ];
    // 歌詞全体の入れ物を特定するための歌詞の1行目(自動検出に使用)
    const FIRST_LINE = '縁の中で漂っていた';
    // 歌詞要素のセレクタが分かっている場合はここに書く(空なら自動検出)
    const LYRICS_SELECTOR = '';
    // --------------------------------------------------------------------

    const CLS = 'x-custom-layout';      // 通常レイアウト
    const CLS_EX = 'x-special-layout';  // 除外歌詞が映っているとき
    const TARGET_CLS = 'x-lyrics-target';
    const squash = (s) => s.replace(/\s+/g, '');

    const main = document.querySelector('main');
    if (!main) return console.warn('[layout] <main> が見つかりません');

    // main内の全テキストを「空白除去した文字列」+「元の位置への対応表」にする
    const walker = document.createTreeWalker(main, NodeFilter.SHOW_TEXT, {
        acceptNode: (n) =>
            /^(SCRIPT|STYLE|NOSCRIPT)$/.test(n.parentElement?.tagName || '')
                ? NodeFilter.FILTER_REJECT
                : NodeFilter.FILTER_ACCEPT,
    });
    let flat = '';
    const map = [];
    for (let n; (n = walker.nextNode());) {
        const s = n.nodeValue;
        for (let i = 0; i < s.length; i++) {
            if (/\s/.test(s[i])) continue;
            flat += s[i];
            map.push([n, i]);
        }
    }

    // 除外したい歌詞の範囲(Range)を探す
    const needle = squash(EXCLUDE_LINES.join(''));
    const idx = flat.indexOf(needle);
    if (idx < 0) return console.warn('[layout] 除外対象の歌詞が見つかりません');
    const [sn, si] = map[idx];
    const [en, ei] = map[idx + needle.length - 1];
    const range = document.createRange();
    range.setStart(sn, si);
    range.setEnd(en, ei + 1);

    // 歌詞要素を特定
    let lyricsEl = LYRICS_SELECTOR ? document.querySelector(LYRICS_SELECTOR) : null;
    if (!lyricsEl) {
        let el = range.commonAncestorContainer;
        if (el.nodeType !== 1) el = el.parentElement;
        while (el && el !== main && !squash(el.textContent).includes(FIRST_LINE)) {
            el = el.parentElement;
        }
        lyricsEl = el;
    }
    if (!lyricsEl || lyricsEl === main) {
        return console.warn('[layout] 歌詞要素を特定できません。LYRICS_SELECTOR を設定してください');
    }
    lyricsEl.classList.add(TARGET_CLS);

    // スタイル
    const style = document.createElement('style');
    style.id = 'x-special-style';
    style.textContent = `
    /* 通常レイアウト */
    html.${CLS} { background-color: #fff !important; }
    html.${CLS} main table,
    html.${CLS} main table * { color: #000 !important; }
    html.${CLS} main a,
    html.${CLS} a > .icon-p { text-decoration-color: #000 !important; }
    html.${CLS} .${TARGET_CLS},
    html.${CLS} .${TARGET_CLS} * { color: #000 !important; }

    /* 除外歌詞が画面に映っているとき */
    html.${CLS_EX} { background-color: #000 !important; }
    html.${CLS_EX} .${TARGET_CLS},
    html.${CLS_EX} .${TARGET_CLS} * { color: #fff !important; }

    /* 行の高さはどちらでも共通 */
    .${TARGET_CLS},
    .${TARGET_CLS} * { line-height: 150px !important; }
  `;
    document.head.appendChild(style);

    // 除外歌詞が画面内にあるかどうかで ON/OFF を切り替える
    const root = document.documentElement;
    let enabled = null;

    const update = () => {
        const r = range.getBoundingClientRect();
        const visible = r.bottom > 0 && r.top < window.innerHeight;
        const next = !visible;
        if (next === enabled) return;

        // 行の高さはどちらのモードでも同じなので、切り替えてもレイアウトは動かない
        root.classList.toggle(CLS, next);
        root.classList.toggle(CLS_EX, !next);
        enabled = next;
    };

    let ticking = false;
    const onChange = () => {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(() => {
            ticking = false;
            update();
        });
    };

    document.addEventListener('scroll', onChange, { passive: true, capture: true });
    window.addEventListener('resize', onChange);
    update();
}

document.addEventListener("DOMContentLoaded", () => {
    add_special_button();
});