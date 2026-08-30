const statsChartCanvas = document.getElementById("stats-chart");
if (statsChartCanvas) {
    const monthlyStats = JSON.parse(document.getElementById("monthly-stats-data").textContent);
    const labels = monthlyStats.map(row => `${row.year}/${row.month}`);

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

        if (chart) {
            chart.destroy();
        }
        chart = new Chart(statsChartCanvas, {
            type: chartMode === "monthly" ? "bar" : "line",
            data: {
                labels: labels,
                datasets: [{
                    label: SERIES_LABELS[seriesKey],
                    data: monthlyStats.map(row => row[dataKey]),
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
