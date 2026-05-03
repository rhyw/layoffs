/**
 * Dashboard charts initialization.
 * Fetches real data from the /api/stats/ endpoint.
 */
document.addEventListener('DOMContentLoaded', async function () {
    if (typeof Chart === 'undefined') return;

    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const gridColor = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)';
    const textColor = isDark ? '#a0a0b0' : '#555566';

    const chartDefaults = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: { color: textColor, font: { size: 12 } }
            }
        },
        scales: {
            x: {
                grid: { color: gridColor },
                ticks: { color: textColor }
            },
            y: {
                grid: { color: gridColor },
                ticks: { color: textColor }
            }
        }
    };

    // Fetch stats data
    let statsData = { by_month: [], by_industry: [] };
    try {
        const res = await fetch('/api/stats/');
        statsData = await res.json();
    } catch (e) {
        console.warn('Failed to fetch stats:', e);
    }

    // Layoffs Over Time (Line Chart)
    const timeCanvas = document.getElementById('chart-layoffs-over-time');
    if (timeCanvas && statsData.by_month) {
        new Chart(timeCanvas, {
            type: 'line',
            data: {
                labels: statsData.by_month.map(d => {
                    const parts = (d.month || '').split('-');
                    return parts.length >= 2 ? `${parts[0]}/${parts[1]}` : d.month;
                }),
                datasets: [{
                    label: 'Jobs Lost',
                    data: statsData.by_month.map(d => d.total || 0),
                    borderColor: '#7c3aed',
                    backgroundColor: 'rgba(124, 58, 237, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3,
                }]
            },
            options: {
                ...chartDefaults,
                plugins: {
                    ...chartDefaults.plugins,
                    legend: { display: false }
                }
            }
        });
    }

    // By Industry (Doughnut Chart)
    const industryCanvas = document.getElementById('chart-by-industry');
    if (industryCanvas && statsData.by_industry) {
        const colors = [
            '#7c3aed', '#3b82f6', '#22c55e', '#f59e0b',
            '#ef4444', '#ec4899', '#14b8a6', '#f97316'
        ];
        new Chart(industryCanvas, {
            type: 'doughnut',
            data: {
                labels: statsData.by_industry.map(d => d.industry || 'Unknown'),
                datasets: [{
                    data: statsData.by_industry.map(d => d.total || 0),
                    backgroundColor: colors.slice(0, statsData.by_industry.length),
                }]
            },
            options: {
                ...chartDefaults,
                cutout: '65%',
                plugins: {
                    ...chartDefaults.plugins,
                    legend: { position: 'right' }
                }
            }
        });
    }

    // Top Companies (Horizontal Bar) - fetch from API
    const companiesCanvas = document.getElementById('chart-top-companies');
    if (companiesCanvas) {
        try {
            const res = await fetch('/api/layoffs/?ordering=-headcount&verified=true&_=' + Date.now());
            const data = await res.json();
            const results = (data.results || data).slice(0, 10);

            new Chart(companiesCanvas, {
                type: 'bar',
                data: {
                    labels: results.map(d => d.company),
                    datasets: [{
                        label: 'Jobs Lost',
                        data: results.map(d => d.headcount || 0),
                        backgroundColor: 'rgba(124, 58, 237, 0.7)',
                        borderColor: '#7c3aed',
                        borderWidth: 1,
                    }]
                },
                options: {
                    ...chartDefaults,
                    indexAxis: 'y',
                    plugins: {
                        ...chartDefaults.plugins,
                        legend: { display: false }
                    }
                }
            });
        } catch (e) {
            console.warn('Failed to fetch top companies:', e);
        }
    }
});
