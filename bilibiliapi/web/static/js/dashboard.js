document.addEventListener("DOMContentLoaded", () => {
    setupThemeToggle();
    setupRankingTable();
});

function setupThemeToggle() {
    const button = document.getElementById("themeToggle");
    const savedTheme = localStorage.getItem("dashboardTheme");
    const initialTheme = savedTheme || "light";

    applyTheme(initialTheme, button);

    button?.addEventListener("click", () => {
        const currentTheme = document.documentElement.dataset.theme === "dark"
            ? "dark"
            : "light";
        const nextTheme = currentTheme === "dark" ? "light" : "dark";
        localStorage.setItem("dashboardTheme", nextTheme);
        applyTheme(nextTheme, button);
    });
}

function applyTheme(theme, button) {
    if (theme === "dark") {
        document.documentElement.dataset.theme = "dark";
        if (button) {
            button.setAttribute("aria-pressed", "true");
            button.setAttribute("aria-label", "切换浅色模式");
            button.setAttribute("title", "切换浅色模式");
        }
        return;
    }

    document.documentElement.dataset.theme = "light";
    if (button) {
        button.setAttribute("aria-pressed", "false");
        button.setAttribute("aria-label", "切换深色模式");
        button.setAttribute("title", "切换深色模式");
    }
}

function setupRankingTable() {
    const table = document.getElementById("rankingTable");
    if (!table) {
        return;
    }

    const tbody = table.querySelector("tbody");
    const rows = Array.from(tbody.querySelectorAll("[data-video-row]"));
    const searchInput = document.getElementById("videoSearch");
    const categoryFilter = document.getElementById("categoryFilter");
    const sortMode = document.getElementById("sortMode");
    const visibleVideoCount = document.getElementById("visibleVideoCount");

    populateCategoryFilter(rows, categoryFilter);

    const applyControls = () => {
        const keyword = normalizeText(searchInput?.value || "");
        const category = categoryFilter?.value || "";
        const mode = sortMode?.value || "ranking";

        rows.forEach(row => {
            const text = normalizeText([
                row.dataset.title,
                row.dataset.up,
                row.dataset.category,
            ].join(" "));
            const matchesKeyword = !keyword || text.includes(keyword);
            const matchesCategory = !category || row.dataset.category === category;

            row.classList.toggle("is-hidden", !(matchesKeyword && matchesCategory));
        });

        const sortedRows = [...rows].sort((left, right) => {
            if (mode === "ranking") {
                return getSortValue(left, mode) - getSortValue(right, mode);
            }
            return getSortValue(right, mode) - getSortValue(left, mode);
        });

        sortedRows.forEach(row => tbody.appendChild(row));
        updateRanks(sortedRows, mode);
        updateVisibleCount(rows, visibleVideoCount);
    };

    [searchInput, categoryFilter, sortMode].forEach(control => {
        control?.addEventListener("input", applyControls);
        control?.addEventListener("change", applyControls);
    });

    document.addEventListener("onlineTotalsUpdated", () => {
        applyControls();
        refreshOnlineRanking();
    });

    applyControls();
}

function populateCategoryFilter(rows, select) {
    if (!select) {
        return;
    }

    const categories = [...new Set(rows.map(row => row.dataset.category).filter(Boolean))]
        .sort((left, right) => left.localeCompare(right, "zh-CN"));

    categories.forEach(category => {
        const option = document.createElement("option");
        option.value = category;
        option.textContent = category;
        select.appendChild(option);
    });
}

function getSortValue(row, mode) {
    if (mode === "views") {
        return Number(row.dataset.views || 0);
    }

    if (mode === "rankingScore") {
        return Number(row.dataset.rankingScore || 0);
    }

    if (mode === "likes") {
        return Number(row.dataset.likes || 0);
    }

    if (mode === "comments") {
        return Number(row.dataset.comments || 0);
    }

    if (mode === "favorites") {
        return Number(row.dataset.favorites || 0);
    }

    if (mode === "online") {
        return Number(row.dataset.online || 0);
    }

    if (mode === "heat") {
        return Number(row.dataset.heat || 0);
    }

    return Number(row.dataset.ranking || 999999);
}

function updateRanks(rows, mode) {
    let visibleRank = 1;
    rows.forEach(row => {
        const rankCell = row.querySelector(".rank-cell");
        if (!rankCell) {
            return;
        }

        if (row.classList.contains("is-hidden")) {
            rankCell.textContent = "-";
            return;
        }

        rankCell.textContent = mode === "ranking"
            ? row.dataset.ranking || visibleRank
            : visibleRank;
        visibleRank += 1;
    });
}

function updateVisibleCount(rows, target) {
    if (!target) {
        return;
    }

    const count = rows.filter(row => !row.classList.contains("is-hidden")).length;
    target.textContent = `${count} 个结果`;
}

async function refreshOnlineRanking() {
    const list = document.getElementById("onlineRankingList");
    const timeLabel = document.getElementById("onlineRankingTime");
    if (!list) {
        return;
    }

    try {
        const response = await fetch("/api/online-ranking?limit=8");
        if (!response.ok) {
            throw new Error("在线排行接口失败");
        }

        const items = await response.json();
        list.innerHTML = "";

        if (items.length === 0) {
            const emptyItem = document.createElement("li");
            emptyItem.className = "muted";
            emptyItem.textContent = "暂无在线人数快照。";
            list.appendChild(emptyItem);
            return;
        }

        if (timeLabel) {
            timeLabel.textContent = items[0]["在线人数抓取时间"] || "最近快照";
        }

        items.forEach(item => {
            const listItem = document.createElement("li");
            const link = document.createElement("a");
            link.href = item["视频链接"] || "#";
            link.target = "_blank";
            link.rel = "noreferrer";
            link.textContent = item["视频标题"] || item.bvid || "未命名视频";

            const count = document.createElement("strong");
            count.textContent = formatNumber(item["在线人数"]);

            listItem.append(link, count);
            list.appendChild(listItem);
        });
    } catch (error) {
        list.innerHTML = '<li class="muted">在线排行读取失败。</li>';
    }
}

function normalizeText(text) {
    return String(text || "").trim().toLowerCase();
}

function formatNumber(value) {
    return Number(value || 0).toLocaleString("zh-CN");
}
