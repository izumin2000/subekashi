const statsChartCanvas = document.getElementById("stats-chart");
if (statsChartCanvas) {
    const monthlyStats = JSON.parse(document.getElementById("monthly-stats-data").textContent);
    const highlightedMonth = JSON.parse(document.getElementById("highlighted-month-data").textContent);
    const labels = monthlyStats.map(row => `${row.year}/${row.month}`);

    const BAR_COLOR = "rgba(54, 162, 235, 0.5)";
    // year・month両方指定時はグラフ側はmonthを無視してその年全体を表示するため、
    // 選択していた月の棒だけ色を変えて元のフィルターとの対応が分かるようにする（コードレビュー指摘対応）
    const HIGHLIGHT_BAR_COLOR = "rgba(34, 197, 94, 0.8)";
    // 累積グラフ(折れ線)の線・ポイントの色・サイズ（#1107）
    const LINE_COLOR = "rgba(255, 255, 255, 0.8)";
    const POINT_RADIUS = 3;
    // 丸の拡大は期間(年月)を具体的に指定した時のみ、全てのポイントに適用する
    const HIGHLIGHTED_POINT_RADIUS = 6;

    // 棒(bar)の色・折れ線のポイント色はどちらも「該当月だけハイライト色、それ以外は通常色」で
    // 共通のため、1つのヘルパーに集約する（コードレビュー指摘対応: 同じ式が2箇所に重複していた）
    function colorForMonth(row) {
        return row.month === highlightedMonth ? HIGHLIGHT_BAR_COLOR : BAR_COLOR;
    }

    const SERIES_LABELS = {
        song_count: "曲数",
        total_view: "総再生回数",
        total_like: "総高評価数",
        total_authors: "総作者数",
        total_imitateds: "総模倣曲関係数",
    };

    function getSelectedValue(name, fallback) {
        const checked = document.querySelector(`input[name="${name}"]:checked`);
        return checked ? checked.value : fallback;
    }

    let chart = null;

    function renderChart() {
        const seriesKey = getSelectedValue("chart-series", "song_count");
        const chartMode = getSelectedValue("chart-mode", "monthly");
        // 累積値(<key>)と月ごとの差分(<key>_delta)はサーバー側で計算済み
        const dataKey = chartMode === "monthly" ? `${seriesKey}_delta` : seriesKey;

        const isBar = chartMode === "monthly";

        const dataset = {
            label: SERIES_LABELS[seriesKey],
            data: monthlyStats.map(row => row[dataKey]),
        };
        if (isBar) {
            dataset.backgroundColor = monthlyStats.map(colorForMonth);
        } else {
            // 累積グラフ(折れ線)は線を白系にし、期間(年月)を具体的に指定した時のみ
            // 全てのポイントを大きくしつつ、該当月のポイントだけ棒グラフと同じ緑系色にする（#1107）
            dataset.borderColor = LINE_COLOR;
            dataset.pointBackgroundColor = monthlyStats.map(colorForMonth);
            const pointRadius = highlightedMonth !== null ? HIGHLIGHTED_POINT_RADIUS : POINT_RADIUS;
            dataset.pointRadius = pointRadius;
            dataset.pointHoverRadius = pointRadius + 2;
        }

        if (chart) {
            chart.destroy();
        }
        chart = new Chart(statsChartCanvas, {
            type: isBar ? "bar" : "line",
            data: {
                labels: labels,
                datasets: [dataset],
            },
            options: {
                responsive: true,
                interaction: { mode: "index", intersect: false },
                plugins: { legend: { display: false } },
            },
        });
    }

    renderChart();

    // Chart.jsの組み込みresponsive自動追従は、コンテナが一度縮小した後に再び拡大した際、
    // canvasのサイズが元に戻らない不具合があるため（#1110）、自前でコンテナのサイズ変化を
    // 監視し、明示的にresize()を呼び出すことで追従させる。Chart.js自身の内部処理と
    // 同一フレーム内で競合すると古いサイズに巻き戻されるため、rAFを2回はさんで
    // 内部処理が完全に収まった後に呼び出す（options.resizeDelayでは今回の問題は
    // 解消しないことを確認済み。縮小方向は追従するが拡大方向のみ追従しないという
    // 非対称な不具合のため、単純なデバウンスでは直らない）
    //
    // resizeScheduledは、ドラッグ操作等でResizeObserverが連続発火した際に
    // 二重rAFコールバックが多重に積み上がるのを防ぐガード（コードレビュー指摘対応）。
    // chart?.resize()は、将来renderChartの非同期化等でこのコールバック実行時に
    // chartが未生成/破棄済みになるケースに備えた防御的な書き方（コードレビュー指摘対応）。
    // このスクリプトはフルページロードの度に1回だけ実行される前提のため、
    // ResizeObserverのdisconnect()は行っていない
    let resizeScheduled = false;
    new ResizeObserver(() => {
        if (resizeScheduled) {
            return;
        }
        resizeScheduled = true;
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                chart?.resize();
                resizeScheduled = false;
            });
        });
    }).observe(document.getElementById("stats-chart-wrapper"));

    // グラフ表示設定(chart-mode/chart-series)はsongrange/year/month用のformとは別扱いのため、
    // ページ全体の再読み込みを挟むと消えてしまう。選択変更時にcookieへ保存しておき、
    // 次回アクセス時にサーバー側(StatsView)がcookieを読んで初期状態に反映する（#1111）
    const CHART_SETTING_COOKIE_NAMES = {
        "chart-mode": "stats_chart_mode",
        "chart-series": "stats_chart_series",
    };
    const CHART_SETTING_COOKIE_MAX_AGE = 60 * 60 * 24 * 365; // 1年（サーバー側のLONG_TERM_COOKIE_AGEと合わせる）

    document.querySelectorAll('input[name="chart-mode"], input[name="chart-series"]').forEach(radio => {
        radio.addEventListener("change", () => {
            if (radio.checked) {
                const cookieName = CHART_SETTING_COOKIE_NAMES[radio.name];
                document.cookie = `${cookieName}=${radio.value}; path=/; max-age=${CHART_SETTING_COOKIE_MAX_AGE}; samesite=lax`;
                renderChart();
            }
        });
    });
}
