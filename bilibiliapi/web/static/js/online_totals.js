document.addEventListener("DOMContentLoaded", async () => {
    const onlineTotalItems = document.querySelectorAll(".online-total");
    const maxOnlineTotalRequests = 20;

    const requestItems = Array.from(onlineTotalItems).slice(0, maxOnlineTotalRequests);
    const skippedItems = Array.from(onlineTotalItems).slice(maxOnlineTotalRequests);

    skippedItems.forEach(item => {
        item.textContent = "未请求";
    });

    const videos = requestItems.map(item => ({
        bvid: item.dataset.bvid,
        cid: Number(item.dataset.cid),
        aid: Number(item.dataset.aid),
    }));

    try {
        const response = await fetch("/api/online-totals", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(videos),
        });

        const data = await response.json();

        const countMap = {};
        data.forEach(item => {
            countMap[item.bvid] = item.count;
        });

        requestItems.forEach(item => {
            const count = countMap[item.dataset.bvid];

            if (count === null || count === undefined) {
                item.textContent = "未获取";
            } else {
                item.textContent = count.toLocaleString();
            }
        });
    } catch (error) {
        requestItems.forEach(item => {
            item.textContent = "请求失败";
        });
    }
});
