const statsChartCanvas = document.getElementById("stats-chart");
if (statsChartCanvas) {
    const monthlyStats = JSON.parse(document.getElementById("monthly-stats-data").textContent);
    const highlightedMonth = JSON.parse(document.getElementById("highlighted-month-data").textContent);
    const labels = monthlyStats.map(row => `${row.year}/${row.month}`);

    const BAR_COLOR = "rgba(54, 162, 235, 0.5)";
    // year・month両方指定時はグラフ側はmonthを無視してその年全体を表示するため、
    // 選択していた月の棒だけ色を変えて元のフィルターとの対応が分かるようにする（コードレビュー指摘対応）
    const HIGHLIGHT_BAR_COLOR = "rgba(255, 99, 132, 0.7)";

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

        if (chart) {
            chart.destroy();
        }
        chart = new Chart(statsChartCanvas, {
            type: isBar ? "bar" : "line",
            data: {
                labels: labels,
                datasets: [{
                    label: SERIES_LABELS[seriesKey],
                    data: monthlyStats.map(row => row[dataKey]),
                    backgroundColor: backgroundColor,
                }],
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
