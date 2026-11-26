async function loadDnsOverview() {
    const status = document.getElementById("snapshot-time");

    try {
	const response = await fetch( "/api/dns/blocking-rates?limit=1");

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const snapshots = await response.json();

        if (snapshots.length === 0) {
            status.textContent = "No DNS snapshots available.";
            return;
        }

        const latest = snapshots[0];

        document.getElementById("total-queries").textContent =
            latest.total_queries.toLocaleString();

        document.getElementById("blocked-queries").textContent =
            latest.blocked_queries.toLocaleString();

        document.getElementById("block-percentage").textContent =
            latest.block_percentage === null
                ? "N/A"
                : `${latest.block_percentage.toFixed(2)}%`;

     const collectedAt = new Date(latest.collected_at_utc);

	const ageMinutes = (Date.now() - collectedAt.getTime()) / 60000;

	let freshness;

	if (ageMinutes < 0) {
    	freshness = "CLOCK ERROR";
	} else if (ageMinutes < 10) {
	    freshness = "FRESH";
	} else if (ageMinutes <= 15) {
    		freshness = "DELAYED";
	} else {
    freshness = "STALE";
}

	status.textContent = `Last collected: ${collectedAt.toLocaleString()} | ${freshness}`;

    } catch (error) {
        console.error("Failed to load DNS statistics:", error);

        status.textContent = "Unable to load DNS statistics.";
    }
}

loadDnsOverview();

async function loadBlockingChart() {
    const status = document.getElementById("chart-status");

    try {
         // Request snapshots from the previous 24 hours.
	const end = new Date();
	const start = new Date(end.getTime() - 24 * 60 * 60 * 1000);

	const params = new URLSearchParams({
        start_utc: start.toISOString(),
         end_utc: end.toISOString()
});

const response = await fetch(
    `/api/dns/history?${params.toString()}`
);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const snapshots = await response.json();

        if (snapshots.length === 0) {
            status.textContent = "No historical data available.";
            return;
        }


        const labels = snapshots.map(snapshot =>
            new Date(snapshot.collected_at_utc).toLocaleTimeString(
                [], { hour: "2-digit", minute: "2-digit" }
            )
        );

        const rates = snapshots.map(snapshot =>
            snapshot.block_percentage
        );

        const canvas = document.getElementById("blocking-chart");

        const existingChart = Chart.getChart(canvas);

	if (existingChart) {
    	existingChart.destroy();}

	new Chart(canvas, {
            type: "line",
            data: {
                labels: labels,
                datasets: [{
                    label: "Blocking Rate (%)",
                    data: rates,
                    borderColor: "#d6a75d",
                    backgroundColor: "rgba(214, 167, 93, 0.08)",
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    tension: 0.15,
                    fill: true,
                    spanGaps: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: "#939b98",
                            maxTicksLimit: 10
                        },
                        grid: {
                            color: "#303536"
                        }
                    },
                    y: {
                        ticks: {
                            color: "#939b98",
                            callback: value => `${value}%`
                        },
                        grid: {
                            color: "#303536"
                        }
                    }
                }
            }
        });

            status.textContent =
                 `Last 24 hours · ${snapshots.length} snapshots · Browser local time`;
    } catch (error) {
        console.error("Failed to load blocking chart:", error);
        status.textContent = "Unable to load historical data.";
    }
}

loadBlockingChart();


loadDnsHeatmap();

setInterval(() => {
    loadDnsOverview();
    loadBlockingChart();
    loadDnsHeatmap();
}, 60 * 1000);
