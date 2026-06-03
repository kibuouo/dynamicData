document.addEventListener("DOMContentLoaded", () => {
    setupThemeToggle();
    setupRefreshDataButton();
    setupRankingTable();
    setupVideoPreview();
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

function setupRefreshDataButton() {
    const button = document.getElementById("refreshDataButton");
    const status = document.getElementById("refreshDataStatus");
    if (!button) {
        return;
    }

    const originalText = button.textContent.trim();

    button.addEventListener("click", async () => {
        button.disabled = true;
        button.textContent = "更新中...";
        if (status) {
            status.textContent = "正在抓取最新数据，请稍等。";
        }

        try {
            const response = await fetch("/api/refresh-data", {
                method: "POST",
            });
            const result = await response.json();

            if (!response.ok || !result.success) {
                throw new Error(result.message || "数据更新失败");
            }

            if (status) {
                status.textContent = "更新完成，正在刷新页面。";
            }
            window.location.reload();
        } catch (error) {
            button.disabled = false;
            button.textContent = originalText;
            if (status) {
                status.textContent = error.message || "数据更新失败，请稍后重试。";
            }
        }
    });
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

function setupVideoPreview() {
    const preview = createVideoPreview();
    const showDelay = 500;
    let activeLink = null;
    let showTimer = null;

    document.body.appendChild(preview.element);

    document.addEventListener("pointerover", event => {
        const link = findVideoPreviewLink(event.target);
        if (!link || link === activeLink) {
            return;
        }

        clearTimeout(showTimer);
        hideVideoPreview(preview);
        activeLink = link;
        moveVideoPreview(preview.element, event);

        showTimer = setTimeout(() => {
            if (activeLink !== link) {
                return;
            }

            fillVideoPreview(preview, link);
            fitVideoPreviewFrame(preview);
            preview.element.classList.add("is-visible");
            preview.element.setAttribute("aria-hidden", "false");
        }, showDelay);
    });

    document.addEventListener("pointermove", event => {
        if (activeLink) {
            moveVideoPreview(preview.element, event);
        }
    });

    document.addEventListener("pointerout", event => {
        if (!activeLink || activeLink.contains(event.relatedTarget)) {
            return;
        }

        clearTimeout(showTimer);
        activeLink = null;
        hideVideoPreview(preview);
    });

    window.addEventListener("resize", () => fitVideoPreviewFrame(preview));
}

function createVideoPreview() {
    const element = document.createElement("aside");
    element.className = "video-preview";
    element.setAttribute("aria-hidden", "true");

    const frameWrap = document.createElement("div");
    frameWrap.className = "video-preview-frame-wrap";

    const frame = document.createElement("iframe");
    frame.className = "video-preview-frame";
    frame.title = "Bilibili video page preview";
    frame.loading = "lazy";
    frame.referrerPolicy = "no-referrer";
    frame.allow = "autoplay 'none'";
    frame.sandbox = "allow-scripts allow-same-origin allow-forms allow-popups";
    frameWrap.appendChild(frame);

    const cover = document.createElement("img");
    cover.className = "video-preview-cover";
    cover.alt = "";
    cover.loading = "lazy";

    const title = document.createElement("strong");
    title.className = "video-preview-title";

    const meta = document.createElement("span");
    meta.className = "video-preview-meta";

    const stats = document.createElement("span");
    stats.className = "video-preview-stats";

    const hint = document.createElement("span");
    hint.className = "video-preview-hint";
    hint.textContent = "Real Bilibili page preview. If blocked, open the title link.";

    element.append(frameWrap, cover, title, meta, stats, hint);
    return { element, frameWrap, frame, cover, title, meta, stats };
}

function fillVideoPreview(preview, link) {
    const row = link.closest("[data-video-row]");
    const coverUrl = row?.dataset.cover || "";
    const pageUrl = buildMutedPreviewUrl(link.href || "");

    if (pageUrl && preview.frame.src !== pageUrl) {
        preview.frame.src = pageUrl;
    }
    preview.frame.hidden = !pageUrl;
    preview.frameWrap.hidden = !pageUrl;
    preview.cover.src = coverUrl;
    preview.cover.hidden = !coverUrl;
    preview.title.textContent = row?.dataset.title || link.textContent.trim() || "Untitled video";
    preview.meta.textContent = [
        row?.dataset.up || "-",
        row?.dataset.category || "-",
    ].join(" / ");
    preview.stats.textContent = [
        `Views ${formatNumber(row?.dataset.views)}`,
        `Likes ${formatNumber(row?.dataset.likes)}`,
        `Online ${formatNumber(row?.dataset.online)}`,
    ].join(" · ");
}

function hideVideoPreview(preview) {
    preview.element.classList.remove("is-visible");
    preview.element.setAttribute("aria-hidden", "true");
    preview.frame.src = "about:blank";
    preview.frame.hidden = true;
    preview.frameWrap.hidden = true;
}

function buildMutedPreviewUrl(url) {
    try {
        const previewUrl = new URL(url, window.location.href);
        previewUrl.searchParams.set("autoplay", "0");
        previewUrl.searchParams.set("muted", "1");
        return previewUrl.href;
    } catch (error) {
        return url;
    }
}

function findVideoPreviewLink(target) {
    const link = target.closest?.("a[href]");
    if (!link || !isBilibiliVideoUrl(link.href)) {
        return null;
    }

    return link;
}

function isBilibiliVideoUrl(url) {
    try {
        const parsedUrl = new URL(url, window.location.href);
        return parsedUrl.hostname.endsWith("bilibili.com")
            && parsedUrl.pathname.startsWith("/video/");
    } catch (error) {
        return false;
    }
}

function fitVideoPreviewFrame(preview) {
    const sourceWidth = 1280;
    const sourceHeight = 720;
    const padding = 20;
    const scale = Math.max(0.28, Math.min(0.46, (preview.element.clientWidth - padding) / sourceWidth));

    preview.element.style.setProperty("--preview-scale", String(scale));
    preview.frameWrap.style.height = `${Math.round(sourceHeight * scale)}px`;
}

function moveVideoPreview(element, event) {
    const gap = 16;
    const rect = element.getBoundingClientRect();
    let left = event.clientX + gap;
    let top = event.clientY + gap;

    if (left + rect.width > window.innerWidth - gap) {
        left = event.clientX - rect.width - gap;
    }

    if (top + rect.height > window.innerHeight - gap) {
        top = window.innerHeight - rect.height - gap;
    }

    element.style.left = `${Math.max(gap, left)}px`;
    element.style.top = `${Math.max(gap, top)}px`;
}
