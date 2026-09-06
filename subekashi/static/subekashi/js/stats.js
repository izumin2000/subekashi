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
        const backgroundColor = isBar
            ? monthlyStats.map(row => row.month === highlightedMonth ? HIGHLIGHT_BAR_COLOR : BAR_COLOR)
            : BAR_COLOR;

        const dataset = {
            label: SERIES_LABELS[seriesKey],
            data: monthlyStats.map(row => row[dataKey]),
            backgroundColor: backgroundColor,
        };
        if (!isBar) {
            // 累積グラフ(折れ線)は線を白系にし、期間(年月)を具体的に指定した時のみ
            // 全てのポイントを大きくしつつ、該当月のポイントだけ棒グラフと同じ緑系色にする（#1107）
            dataset.borderColor = LINE_COLOR;
            dataset.pointBackgroundColor = monthlyStats.map(row => row.month === highlightedMonth ? HIGHLIGHT_BAR_COLOR : BAR_COLOR);
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

    document.querySelectorAll('input[name="chart-mode"], input[name="chart-series"]').forEach(radio => {
        radio.addEventListener("change", () => {
            if (radio.checked) {
                renderChart();
            }
        });
    });
}
