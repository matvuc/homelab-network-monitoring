"use strict";

const HEATMAP_METRICS = {
    blocking_rate: {
        field: "avg_block_percentage",
        label: "Average blocking rate",
        thresholds: [13, 14.5, 16],
        unit: "%",
        decimals: 2
    },

    query_volume: {
        field: "avg_rolling_queries",
        label: "Average rolling query volume",
        thresholds: [50000, 56000, 63000],
        unit: " queries",
        decimals: 2
    },

    snapshot_count: {
        field: "snapshot_count",
        label: "Stored snapshot count",
        thresholds: [4, 7, 10],
        unit: " snapshots",
        decimals: 0
    }
};

function getHeatmapLevel(value, metric) {
    const config = HEATMAP_METRICS[metric];

    if (!config) {
        throw new Error("Unknown heatmap metric");
    }

    if (!Number.isFinite(value) || value < 0) {
        return null;
    }

    if (value === 0) {
        return 0;
    }

    let level = 1;

    for (const threshold of config.thresholds) {
        if (value >= threshold) {
            level++;
        }
    }

    return level;
}


function createHeatmapCell(hour, metric, date, localHour) {
    const cell = document.createElement("button");

    cell.type = "button";
    cell.className = "heatmap-cell";
    cell.dataset.key = hour
        ? hour.hour_start_utc
        : `${date}:${localHour}:na`;

    const detail = formatHeatmapDetail(
        hour, metric, date, localHour
    );

    const showDetail = () => {
        document.getElementById("heatmap-grid")
            .dataset.inspectedKey = cell.dataset.key;
        document.getElementById("heatmap-detail").textContent =
            detail;
    };

    cell.addEventListener("mouseenter", showDetail);
    cell.addEventListener("focus", showDetail);
    cell.addEventListener("click", showDetail);


    const timeLabel =
        `${date} ${String(localHour).padStart(2, "0")}:00`;

    if (!hour) {
        cell.classList.add("heatmap-not-applicable");
        cell.setAttribute(
            "aria-label",
            detail
        );
        return cell;
    }

    const config = HEATMAP_METRICS[metric];
    const value = hour[config.field];
    const level = getHeatmapLevel(value, metric);

    if (hour.status === "future") {
        cell.classList.add("heatmap-future");
    } else if (
        hour.status === "missing" ||
        hour.snapshot_count === 0
    ) {
        cell.classList.add("heatmap-missing");
    } else if (level === null) {
        cell.classList.add("heatmap-undefined");
    } else {
        cell.classList.add(`heatmap-level-${level}`);
    }

    if (hour.status === "current") {
        cell.classList.add("heatmap-current");
    }

    cell.dataset.hour = hour.hour_start_utc;

    cell.setAttribute(
        "aria-label",
        detail
    );

    return cell;
}


function renderHeatmap(data, metric) {
    const grid = document.getElementById("heatmap-grid");
    const fragment = document.createDocumentFragment();

    const hoursByPosition = new Map();

    for (const hour of data.hours) {
        const key = `${hour.local_date}:${hour.local_hour}`;

        if (!hoursByPosition.has(key)) {
            hoursByPosition.set(key, []);
        }

        hoursByPosition.get(key).push(hour);
    }

    function addLabel(text, className) {
        const label = document.createElement("span");
        label.className = className;
        label.textContent = text;
        fragment.appendChild(label);
    }

    addLabel("", "heatmap-label");

    for (let hour = 0; hour < 24; hour++) {
        addLabel(
            hour % 6 === 0
                ? String(hour).padStart(2, "0")
                : "",
            "heatmap-label heatmap-hour-label"
        );
    }

    for (const date of data.dates) {
        addLabel(date.slice(5), "heatmap-label");

        for (let hour = 0; hour < 24; hour++) {
            const entries =
                hoursByPosition.get(`${date}:${hour}`) || [];

            if (entries.length > 1) {
                const wrapper = document.createElement("div");
                wrapper.className = "heatmap-repeated";

                for (const entry of entries) {
                    wrapper.appendChild(
                        createHeatmapCell(entry, metric, date, hour)
                    );
                }

                fragment.appendChild(wrapper);
            } else {
                fragment.appendChild(
                    createHeatmapCell(
                        entries[0], metric, date, hour
                    )
                );
            }
        }
    }

    const focusedKey = grid.contains(document.activeElement)
        ? document.activeElement.dataset.key
        : null;

    const inspectedKey = grid.dataset.inspectedKey;

    grid.replaceChildren(fragment);

    const cells = Array.from(
        grid.querySelectorAll(".heatmap-cell")
    );

    const inspectedCell = cells.find(
        cell => cell.dataset.key === inspectedKey
    );

    document.getElementById("heatmap-detail").textContent =
        inspectedCell
            ? inspectedCell.getAttribute("aria-label")
            : "Select an hourly cell to inspect its data.";

    if (!inspectedCell) {
        delete grid.dataset.inspectedKey;
    }

    const focusedCell = cells.find(
        cell => cell.dataset.key === focusedKey
    );

    if (focusedCell) {
        focusedCell.focus({ preventScroll: true });
    } else if (focusedKey) {
        document.getElementById("heatmap-metric")
            .focus({ preventScroll: true });
    }
    renderHeatmapLegend(metric);
}


async function fetchHeatmapData() {
    const response = await fetch("/api/dns/heatmap", {
        cache: "no-store"
    });

    if (!response.ok) {
        throw new Error(
            `Heatmap request failed: HTTP ${response.status}`
        );
    }

    return await response.json();
}


let heatmapData = null;

function setHeatmapData(data) {
    heatmapData = data;

    const metric = document.getElementById("heatmap-metric").value;

    renderHeatmap(heatmapData, metric);
}

document.getElementById("heatmap-metric").addEventListener(
    "change",
    function () {
        if (heatmapData !== null) {
            delete document.getElementById("heatmap-grid")
                .dataset.inspectedKey;
            renderHeatmap(heatmapData, this.value);
            document.getElementById("heatmap-detail").textContent =
                "Select an hourly cell to inspect its data.";

        }
    }
);


function renderHeatmapLegend(metric) {
    const legend = document.getElementById("heatmap-legend");
    const config = HEATMAP_METRICS[metric];
    const [low, mid, high] = config.thresholds;

    const format = value =>
        value.toLocaleString("en-US") +
        (metric === "blocking_rate" ? "%" : "");

    const items = [
        ["heatmap-level-0", "Zero"],
        ["heatmap-level-1", `>0 to <${format(low)}`],
        ["heatmap-level-2", `${format(low)} to <${format(mid)}`],
        ["heatmap-level-3", `${format(mid)} to <${format(high)}`],
        ["heatmap-level-4", `${format(high)}+`],
        ["heatmap-missing", "No snapshots"],
        ["heatmap-undefined", "Undefined"],
        ["heatmap-future", "Future"],
        ["heatmap-not-applicable", "N/A"],
        ["heatmap-current", "Current hour"]
    ];

    const fragment = document.createDocumentFragment();

    for (const [className, label] of items) {
        const item = document.createElement("span");
        item.className = "heatmap-legend-item";

        const swatch = document.createElement("span");
        swatch.className = `heatmap-legend-swatch ${className}`;
        swatch.setAttribute("aria-hidden", "true");

        const text = document.createElement("span");
        text.textContent = label;

        item.append(swatch, text);
        fragment.appendChild(item);
    }

    legend.replaceChildren(fragment);
}


function formatHeatmapDetail(hour, metric, date, localHour) {
    const time =
        `${date} ${String(localHour).padStart(2, "0")}:00`;

    if (!hour) {
        return `${time} | N/A — nonexistent local hour due to daylight saving time.`;
    }

    const config = HEATMAP_METRICS[metric];
    const value = hour[config.field];
    const timestamp = `${time} UTC${hour.utc_offset}`;

    if (hour.status === "future") {
        return `${timestamp} | Future hour — data not available yet.`;
    }

    if (hour.snapshot_count === 0) {
        const status = hour.status === "current"
            ? "Current hour — no snapshots yet"
            : "Missing data";

        return `${timestamp} | ${status} | 0 snapshots`;
    }

    const formattedValue = Number.isFinite(value)
        ? value.toLocaleString("en-US", {
            minimumFractionDigits: config.decimals,
            maximumFractionDigits: config.decimals
        }) + config.unit
        : "Undefined";

    let quality = hour.status === "current"
        ? "Current / partial hour"
        : hour.snapshot_count < 12
            ? "Partial sampling"
            : "Observed";

    if (metric === "blocking_rate") {
        quality += ` | ${hour.valid_blocking_samples} valid blocking samples`;
    }

    return `${timestamp} | ${config.label}: ${formattedValue} | ${hour.snapshot_count} stored snapshots | ${quality}`;
}


let heatmapRefreshInProgress = false;

async function loadDnsHeatmap() {
    if (heatmapRefreshInProgress) {
        return;
    }

    heatmapRefreshInProgress = true;

    const status = document.getElementById("heatmap-status");

    try {
        const data = await fetchHeatmapData();

        setHeatmapData(data);

        status.classList.remove("is-error");
        status.textContent =
            "Updated: " +
            new Date(data.generated_at_utc).toLocaleString(
                "en-US", {
                    timeZone: "America/Chicago",
                    timeZoneName: "short"
                }
            );

    } catch (error) {
        console.error("Failed to load DNS heatmap:", error);

        status.classList.add("is-error");

        status.textContent = heatmapData !== null
            ? "STALE — refresh failed. Showing last successful data."
            : "Unable to load heatmap data.";

    } finally {
        heatmapRefreshInProgress = false;
    }
}
