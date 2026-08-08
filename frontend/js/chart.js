/**
 * ECharts 图表模块
 * 负责热度柱状图的初始化和更新
 */
const ChartManager = {
    chart: null,

    init(chartDomId) {
        const dom = document.getElementById(chartDomId);
        if (!dom) return;

        this.chart = echarts.init(dom, 'dark');
        this._setEmpty();

        // 响应式
        window.addEventListener('resize', () => {
            if (this.chart) this.chart.resize();
        });
    },

    _setEmpty() {
        if (!this.chart) return;
        this.chart.setOption({
            title: { text: '等待数据...', left: 'center', top: 'center',
                     textStyle: { color: '#8899aa', fontSize: 14 } },
            xAxis: { show: false },
            yAxis: { show: false },
            series: [],
        });
    },

    updateFromStats(statsData) {
        if (!this.chart) return;

        const zones = statsData.zones || statsData;
        const items = Object.values(zones);
        if (!items.length) {
            this._setEmpty();
            return;
        }

        items.sort((a, b) => (b.heat_score || 0) - (a.heat_score || 0));
        const labels = items.map(z => z.zone_label || z.zone_id);
        const scores = items.map(z => z.heat_score || 0);
        const visits = items.map(z => z.visit_count || 0);
        const dwells = items.map(z => z.total_dwell_seconds || 0);

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                formatter: function(params) {
                    const i = params[0].dataIndex;
                    return `${params[0].name}<br/>
                        热度分: <b>${scores[i].toFixed(1)}</b><br/>
                        到访: ${visits[i]} 人次<br/>
                        总停留: ${dwells[i].toFixed(0)} 秒`;
                }
            },
            grid: { left: 8, right: 20, top: 10, bottom: 30 },
            xAxis: {
                type: 'category', data: labels,
                axisLabel: { color: '#8899aa', fontSize: 10, rotate: labels.length > 5 ? 30 : 0 },
                axisLine: { lineStyle: { color: '#2a3f55' } },
            },
            yAxis: {
                type: 'value', name: '热度分',
                nameTextStyle: { color: '#8899aa', fontSize: 10 },
                axisLabel: { color: '#8899aa' },
                splitLine: { lineStyle: { color: '#2a3f55', type: 'dashed' } },
            },
            series: [{
                type: 'bar',
                data: scores.map(v => ({
                    value: v,
                    itemStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: '#4da6ff' },
                            { offset: 1, color: '#1a4a80' },
                        ]),
                        borderRadius: [6, 6, 0, 0],
                    },
                })),
                barWidth: '55%',
            }],
        };
        this.chart.setOption(option, true);
    },

    showHeatmap(data) {
        // 热力图预留（远期），当前用柱状图
        this.updateFromStats(data);
    },
};
