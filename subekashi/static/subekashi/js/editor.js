window.addEventListener("DOMContentLoaded", () => {
    // 開いたときに編集前と編集後の差分を表示する（読み込み時に全ての履歴の差分を求めないようにする）
    document.querySelectorAll(".history_details").forEach(details => {
        details.addEventListener("toggle", () => showDiff(details), { once: true });
    });

    // 読み込み時に最初のdetailを展開
    const firstDetail = document.querySelector("details");
    if (firstDetail) firstDetail.open = true;

    // セルの値をコピー
	document.querySelectorAll(".change_table_wrapper td").forEach(cell => {
		cell.addEventListener("click", async () => {
			const text = cell.innerText.trim();
			try {
				navigator.clipboard.writeText(text);
				showToast("ok", "コピーしました。");
			} catch (err) {
                showToast("error", "エラーが発生しました。");
			}
		});
	});
});


// historyを更新するリロード
function reloadPage() {
    const newUrl = location.pathname + '?reload=' + Date.now();
    history.replaceState(null, '', newUrl); // 履歴を増やさずURLだけ更新
    location.reload();
}


// 全部のdetailを開け閉め
var is_open = true;
function openAll() {
    document.querySelectorAll("details").forEach(d => {
        d.open = is_open;
    });
    is_open = !is_open;
}

// 差分を求める編集前と編集後の要素数の積の上限。超える場合は共通する先頭と末尾以外を全て変更されたものとする
const DIFF_MAX_CELLS = 1000000;
// 削除された行と追加された行で共通する文字の割合がこれ以上なら、組にして文字単位で比べる
const DIFF_LINE_SIMILARITY = 0.5;
// 削除された行と組にする追加された行を探す範囲（行数）
const DIFF_PAIR_WINDOW = 10;


// 配列aとbの差分を、最長共通部分列から["equal"|"delete"|"insert", 要素]の配列で返す
function diffSequence(a, b) {
    let start = 0;
    while (start < a.length && start < b.length && a[start] === b[start]) start++;
    let endA = a.length;
    let endB = b.length;
    while (endA > start && endB > start && a[endA - 1] === b[endB - 1]) {
        endA--;
        endB--;
    }

    const ops = a.slice(0, start).map(item => ["equal", item]);
    const midA = a.slice(start, endA);
    const midB = b.slice(start, endB);
    const n = midA.length;
    const m = midB.length;
    let i = 0;
    let j = 0;
    if (n * m <= DIFF_MAX_CELLS) {
        // lcs[i * width + j]はmidA[i:]とmidB[j:]の最長共通部分列の長さ
        const width = m + 1;
        const lcs = new Uint16Array((n + 1) * width);
        for (let x = n - 1; x >= 0; x--) {
            for (let y = m - 1; y >= 0; y--) {
                lcs[x * width + y] = midA[x] === midB[y]
                    ? lcs[(x + 1) * width + y + 1] + 1
                    : Math.max(lcs[(x + 1) * width + y], lcs[x * width + y + 1]);
            }
        }
        while (i < n && j < m) {
            if (midA[i] === midB[j]) {
                ops.push(["equal", midA[i]]);
                i++;
                j++;
            } else if (lcs[(i + 1) * width + j] >= lcs[i * width + j + 1]) {
                ops.push(["delete", midA[i]]);
                i++;
            } else {
                ops.push(["insert", midB[j]]);
                j++;
            }
        }
    }
    midA.slice(i).forEach(item => ops.push(["delete", item]));
    midB.slice(j).forEach(item => ops.push(["insert", item]));
    a.slice(endA).forEach(item => ops.push(["equal", item]));
    return ops;
}


// partsの末尾と変更の有無が同じなら連結する
function pushPart(parts, text, isChanged) {
    const last = parts[parts.length - 1];
    if (last && last.isChanged === isChanged) {
        last.text += text;
    } else {
        parts.push({ text, isChanged });
    }
}


// 行どうしの文字単位の差分を、編集前と編集後のpartsで返す。共通する文字が少ない場合はnullを返す
function diffLine(before, after) {
    const beforeChars = Array.from(before);
    const afterChars = Array.from(after);
    const threshold = (beforeChars.length + afterChars.length) * DIFF_LINE_SIMILARITY;
    // 共通する文字は短い方の行の文字数以下のため、長さが大きく違う行は差分を求めずにnullを返す
    if (Math.min(beforeChars.length, afterChars.length) * 2 < threshold) {
        return null;
    }

    const ops = diffSequence(beforeChars, afterChars);
    const equalCount = ops.filter(([type]) => type === "equal").length;
    if (equalCount * 2 < threshold) {
        return null;
    }

    const beforeParts = [];
    const afterParts = [];
    for (const [type, char] of ops) {
        if (type !== "insert") pushPart(beforeParts, char, type === "delete");
        if (type !== "delete") pushPart(afterParts, char, type === "insert");
    }
    return [beforeParts, afterParts];
}


// 編集前と編集後の文字列の差分を、それぞれ行ごとのpartsの配列で返す
// 行単位で比べ、続けて削除・追加された行は似ている行どうしを前から順に組にして文字単位で比べる
function diffText(before, after) {
    const toLines = text => text === "" ? [] : text.split("\n");
    const beforeLines = [];
    const afterLines = [];
    let deletedLines = [];
    let insertedLines = [];
    const flush = () => {
        let k = 0;
        for (const deletedLine of deletedLines) {
            let pairIndex = k;
            let pair = null;
            for (; pairIndex < Math.min(insertedLines.length, k + DIFF_PAIR_WINDOW); pairIndex++) {
                pair = diffLine(deletedLine, insertedLines[pairIndex]);
                if (pair) break;
            }
            if (!pair) {
                beforeLines.push([{ text: deletedLine, isChanged: true }]);
                continue;
            }
            for (; k < pairIndex; k++) afterLines.push([{ text: insertedLines[k], isChanged: true }]);
            beforeLines.push(pair[0]);
            afterLines.push(pair[1]);
            k++;
        }
        for (; k < insertedLines.length; k++) afterLines.push([{ text: insertedLines[k], isChanged: true }]);
        deletedLines = [];
        insertedLines = [];
    };

    for (const [type, line] of diffSequence(toLines(before), toLines(after))) {
        if (type === "delete") {
            deletedLines.push(line);
        } else if (type === "insert") {
            insertedLines.push(line);
        } else {
            flush();
            beforeLines.push([{ text: line, isChanged: false }]);
            afterLines.push([{ text: line, isChanged: false }]);
        }
    }
    flush();
    return [beforeLines, afterLines];
}


// linebreaksbrで改行を<br>にしたセルの文字列を取り出す
function getCellText(cell) {
    return Array.from(cell.childNodes, node => node.nodeName === "BR" ? "\n" : node.textContent).join("");
}


// 行ごとのpartsでセルの中身を置き換える。変更された部分はtagName（del・ins）で囲む
function renderDiffLines(cell, lines, tagName) {
    cell.replaceChildren();
    lines.forEach((parts, index) => {
        if (index > 0) cell.append(document.createElement("br"));
        for (const { text, isChanged } of parts) {
            if (!isChanged) {
                cell.append(text);
                continue;
            }
            const mark = document.createElement(tagName);
            mark.textContent = text;
            // 空の行の削除・追加は記号で示す
            if (text === "") mark.classList.add("diff-blank");
            cell.append(mark);
        }
    });
}


// details内の編集前と編集後のセルに差分を表示する
function showDiff(details) {
    details.querySelectorAll(".diff-table tbody tr").forEach(row => {
        if (row.cells.length !== 3) return;
        const [, beforeCell, afterCell] = row.cells;
        const [beforeLines, afterLines] = diffText(getCellText(beforeCell), getCellText(afterCell));
        renderDiffLines(beforeCell, beforeLines, "del");
        renderDiffLines(afterCell, afterLines, "ins");
    });
}


document.getElementById("history-reload").addEventListener("click", reloadPage);
document.getElementById("history-open-all").addEventListener("click", openAll);