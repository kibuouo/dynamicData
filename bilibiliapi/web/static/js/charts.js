document.addEventListener("DOMContentLoaded", () => {
    const chartElements = [
        document.getElementById("categoryViewsChart"),
        document.getElementById("categoryCountChart"),
        document.getElementById("likeScatterChart"),
        document.getElementById("rankingScoreChart"),
    ].filter(Boolean);

    if (!window.echarts) {
        chartElements.forEach(element => {
            showChartMessage(element, "ECharts 加载失败，请检查网络或 CDN 地址。");
        });
        return;
    }

    loadChartData()
        .then(({ categories, videos, rankingVideos }) => {
            const charts = [
                renderCategoryViewsChart(categories),
                renderCategoryCountChart(categories),
                renderLikeScatterChart(videos),
                renderRankingScoreChart(rankingVideos),
            ].filter(Boolean);

            window.addEventListener("resize", () => {
                charts.forEach(chart => chart.resize());
            });
        })
        .catch(() => {
            chartElements.forEach(element => {
                showChartMessage(element, "图表数据读取失败，请先确认 Flask 服务和数据库正常。");
            });
        });
});

async function loadChartData() {
    const [summaryResponse, videosResponse, rankingResponse] = await Promise.all([
        fetch("/api/summary"),
        fetch("/api/videos?limit=80"),
        fetch("/api/ranking?limit=80"),
    ]);

    if (!summaryResponse.ok || !videosResponse.ok || !rankingResponse.ok) {
        throw new Error("读取图表接口失败");
    }

    const summaryData = await summaryResponse.json();
    const videos = await videosResponse.json();
    const rankingData = await rankingResponse.json();

    return {
        categories: summaryData.categories || [],
        videos,
        rankingVideos: rankingData.videos || [],
    };
}

function renderCategoryViewsChart(categories) {
    const element = document.getElementById("categoryViewsChart");
    if (!element) {
        return null;
    }

    if (categories.length === 0) {
        showChartMessage(element, "暂无分区播放量数据");
        return null;
    }

    const chart = echarts.init(element);
    chart.setOption({
        color: ["#00a1d6"],
        tooltip: {
            trigger: "axis",
            axisPointer: { type: "shadow" },
            formatter: params => {
                const item = params[0];
                return `${escapeHtml(item.name)}<br>播放量：${formatNumber(item.value)}`;
            },
        },
        grid: {
            left: 84,
            right: 28,
            top: 24,
            bottom: 28,
        },
        xAxis: {
            type: "value",
            axisLabel: {
                color: "#6b7280",
                formatter: formatShortNumber,
            },
            splitLine: {
                lineStyle: { color: "#edf1f5" },
            },
        },
        yAxis: {
            type: "category",
            inverse: true,
            data: categories.map(item => item.category || "未分类"),
            axisLabel: { color: "#374151" },
            axisTick: { show: false },
            axisLine: { show: false },
        },
        series: [
            {
                name: "播放量",
                type: "bar",
                barWidth: 16,
                data: categories.map(item => Number(item.total_views || 0)),
                itemStyle: {
                    borderRadius: [0, 8, 8, 0],
                    color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                        { offset: 0, color: "#44c7f4" },
                        { offset: 1, color: "#008ec4" },
                    ]),
                },
            },
        ],
    });

    return chart;
}

function renderCategoryCountChart(categories) {
    const element = document.getElementById("categoryCountChart");
    if (!element) {
        return null;
    }

    if (categories.length === 0) {
        showChartMessage(element, "暂无分区视频数量数据");
        return null;
    }

    const chart = echarts.init(element);
    chart.setOption({
        tooltip: {
            trigger: "item",
            formatter: params => {
                return `${escapeHtml(params.name)}<br>视频数：${formatNumber(params.value)}<br>占比：${params.percent}%`;
            },
        },
        legend: {
            bottom: 0,
            left: "center",
            icon: "circle",
            textStyle: { color: "#6b7280" },
        },
        series: [
            {
                name: "视频数量",
                type: "pie",
                radius: ["45%", "68%"],
                center: ["50%", "44%"],
                avoidLabelOverlap: true,
                label: {
                    color: "#374151",
                    formatter: "{b}",
                },
                data: categories.map(item => ({
                    name: item.category || "未分类",
                    value: Number(item.video_count || 0),
                })),
            },
        ],
    });

    return chart;
}

function renderLikeScatterChart(videos) {
    const element = document.getElementById("likeScatterChart");
    if (!element) {
        return null;
    }

    const points = videos
        .map(video => ({
            title: video["视频标题"] || "未命名视频",
            views: Number(video["播放量"] || 0),
            likes: Number(video["点赞数"] || 0),
        }))
        .filter(video => video.views > 0 && video.likes > 0);

    if (points.length === 0) {
        showChartMessage(element, "暂无播放量和点赞数据");
        return null;
    }

    const chart = echarts.init(element);
    chart.setOption({
        color: ["#ff7f9f"],
        tooltip: {
            trigger: "item",
            formatter: params => {
                const point = params.data;
                return [
                    escapeHtml(point[2]),
                    `播放量：${formatNumber(point[0])}`,
                    `点赞数：${formatNumber(point[1])}`,
                ].join("<br>");
            },
        },
        grid: {
            left: 56,
            right: 24,
            top: 24,
            bottom: 46,
        },
        xAxis: {
            type: "value",
            name: "播放量",
            nameLocation: "middle",
            nameGap: 30,
            axisLabel: {
                color: "#6b7280",
                formatter: formatShortNumber,
            },
            splitLine: {
                lineStyle: { color: "#edf1f5" },
            },
        },
        yAxis: {
            type: "value",
            name: "点赞数",
            axisLabel: {
                color: "#6b7280",
                formatter: formatShortNumber,
            },
            splitLine: {
                lineStyle: { color: "#edf1f5" },
            },
        },
        series: [
            {
                name: "视频",
                type: "scatter",
                symbolSize: value => Math.max(8, Math.min(24, Math.sqrt(value[1]) / 20)),
                data: points.map(point => [point.views, point.likes, point.title]),
            },
        ],
    });

    return chart;
}

function renderRankingScoreChart(videos) {
    const element = document.getElementById("rankingScoreChart");
    if (!element) {
        return null;
    }

    const points = videos
        .map(video => ({
            title: video["视频标题"] || video.bvid || "未命名视频",
            views: Number(video["播放量"] || 0),
            score: Number(video["榜单分数"] || 0),
            rank: Number(video["榜单排名"] || 0),
        }))
        .filter(video => video.views > 0 && video.score > 0);

    if (points.length === 0) {
        showChartMessage(element, "暂无榜单分数数据");
        return null;
    }

    const chart = echarts.init(element);
    chart.setOption({
        color: ["#7c3aed"],
        tooltip: {
            trigger: "item",
            formatter: params => {
                const point = params.data;
                return [
                    escapeHtml(point[3]),
                    `榜单排名：${point[2]}`,
                    `榜单分数：${formatNumber(point[1])}`,
                    `播放量：${formatNumber(point[0])}`,
                ].join("<br>");
            },
        },
        grid: {
            left: 64,
            right: 24,
            top: 24,
            bottom: 46,
        },
        xAxis: {
            type: "value",
            name: "播放量",
            nameLocation: "middle",
            nameGap: 30,
            axisLabel: {
                color: "#64748b",
                formatter: formatShortNumber,
            },
            splitLine: {
                lineStyle: { color: "#edf1f5" },
            },
        },
        yAxis: {
            type: "value",
            name: "榜单分数",
            axisLabel: {
                color: "#64748b",
                formatter: formatShortNumber,
            },
            splitLine: {
                lineStyle: { color: "#edf1f5" },
            },
        },
        series: [
            {
                name: "榜单视频",
                type: "scatter",
                symbolSize: value => Math.max(8, Math.min(24, 28 - Math.sqrt(value[2] || 1))),
                data: points.map(point => [point.views, point.score, point.rank, point.title]),
            },
        ],
    });

    return chart;
}

function showChartMessage(element, message) {
    element.classList.add("chart-message");
    element.textContent = message;
}

function formatNumber(value) {
    return Number(value || 0).toLocaleString("zh-CN");
}

function formatShortNumber(value) {
    const number = Number(value || 0);

    if (number >= 100000000) {
        return `${(number / 100000000).toFixed(1)}亿`;
    }

    if (number >= 10000) {
        return `${(number / 10000).toFixed(1)}万`;
    }

    return number.toLocaleString("zh-CN");
}

function escapeHtml(text) {
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
