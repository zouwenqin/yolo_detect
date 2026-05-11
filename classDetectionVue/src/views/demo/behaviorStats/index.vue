<template>
	<DemoShell active="stats" title="行为统计" status="统计已生成">
		<div class="stats-page">
			<section class="panel summary-panel">
				<div class="section-title">
					<h3>行为时长概览</h3>
					<p>统计维度为整段录制视频，重点展示异常行为占比与趋势。</p>
				</div>
				<div class="metric-grid">
					<div v-for="item in demoState.stats" :key="item.key" class="metric-card" :class="item.tone">
						<span>{{ item.label }}</span>
						<strong>{{ item.duration }}</strong>
						<p>占比 {{ item.ratio }} · {{ item.count }} 次</p>
					</div>
				</div>
			</section>

			<div class="chart-layout">
				<section class="panel trend-panel">
					<div class="section-title compact">
						<h3>行为时长趋势</h3>
						<p>按视频时间段聚合展示。</p>
					</div>
					<div id="statsTrendChart" class="trend-chart"></div>
				</section>
				<section class="panel pie-panel">
					<div class="section-title compact">
						<h3>行为占比</h3>
						<p>异常与专注行为的结构占比。</p>
					</div>
					<div id="statsPieChart" class="pie-chart"></div>
				</section>
			</div>

			<section class="panel heat-panel">
				<div class="section-title compact">
					<h3>视频时间段热力条</h3>
					<p>颜色越深表示该时间段异常行为越集中。</p>
				</div>
				<div class="heat-row">
					<div v-for="item in heatSegments" :key="item.time" class="heat-segment" :class="item.level">
						<span>{{ item.time }}</span>
					</div>
				</div>
				<div class="legend">
					<span><i class="low"></i>低</span>
					<span><i class="medium"></i>中</span>
					<span><i class="high"></i>高</span>
				</div>
			</section>
		</div>
	</DemoShell>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue';
import * as echarts from 'echarts';
import DemoShell from '/@/views/demo/components/DemoShell.vue';
import { demoState } from '/@/views/demo/demoState';

const trendChart = ref<any>(null);
const pieChart = ref<any>(null);
const heatSegments = [
	{ time: '00:00', level: 'low' },
	{ time: '04:00', level: 'high' },
	{ time: '08:00', level: 'medium' },
	{ time: '12:00', level: 'medium' },
	{ time: '16:00', level: 'high' },
	{ time: '20:00', level: 'low' },
	{ time: '24:00', level: 'medium' },
	{ time: '28:47', level: 'low' },
];

function initCharts() {
	const trendEl = document.getElementById('statsTrendChart');
	const pieEl = document.getElementById('statsPieChart');
	if (trendEl) {
		trendChart.value = echarts.init(trendEl);
		trendChart.value.setOption({
			color: ['#ef4f45', '#f2a51a', '#5b6ee1', '#20aa82'],
			tooltip: { trigger: 'axis' },
			legend: { right: 16, top: 4, data: ['趴桌', '持续低头', '玩手机', '专注'] },
			grid: { left: 42, right: 24, top: 48, bottom: 30 },
			xAxis: { type: 'category', boundaryGap: false, data: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00', '28:47'] },
			yAxis: { type: 'value', name: '分钟' },
			series: [
				{ name: '趴桌', type: 'line', smooth: true, areaStyle: { opacity: .08 }, data: [0, 2, 1, 4, 6, 3, 2, 0] },
				{ name: '持续低头', type: 'line', smooth: true, areaStyle: { opacity: .08 }, data: [1, 16, 8, 9, 14, 7, 6, 2] },
				{ name: '玩手机', type: 'line', smooth: true, data: [0, 4, 3, 2, 4, 3, 1, 0] },
				{ name: '专注', type: 'line', smooth: true, data: [3, 5, 8, 7, 9, 16, 13, 8] },
			],
		});
	}
	if (pieEl) {
		pieChart.value = echarts.init(pieEl);
		pieChart.value.setOption({
			color: ['#ef4f45', '#f2a51a', '#5b6ee1', '#8b5cf6', '#20aa82'],
			tooltip: { trigger: 'item' },
			legend: { bottom: 0, itemWidth: 8, itemHeight: 8 },
			series: [{
				type: 'pie',
				radius: ['48%', '72%'],
				center: ['50%', '44%'],
				label: { show: false },
				data: demoState.stats.map((item) => ({ name: item.label, value: item.value })),
			}],
		});
	}
}

onMounted(() => nextTick(initCharts));
onUnmounted(() => {
	trendChart.value?.dispose();
	pieChart.value?.dispose();
});
</script>

<style scoped lang="scss">
.stats-page {
	height: 100%;
	overflow-y: auto;
	padding-right: 2px;
	scrollbar-width: thin;
}

.panel {
	border-radius: 8px;
	background: rgba(255, 255, 255, .97);
	border: 1px solid #dde8e5;
	box-shadow: 0 14px 34px rgba(23, 42, 46, .07);
	padding: 16px;
}

.section-title {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 16px;
	margin-bottom: 14px;
}

.section-title.compact {
	display: block;
}

.section-title h3 {
	margin: 0 0 6px;
	font-size: 18px;
}

.section-title p {
	margin: 0;
	color: #6b7b80;
	line-height: 1.6;
}

.metric-grid {
	display: grid;
	grid-template-columns: repeat(5, minmax(140px, 1fr));
	gap: 12px;
}

.metric-card {
	min-height: 118px;
	padding: 16px;
	border-radius: 8px;
	border: 1px solid;
}

.metric-card span {
	color: #4b5c61;
	font-weight: 700;
}

.metric-card strong {
	display: block;
	margin: 14px 0 10px;
	font-size: 25px;
	line-height: 1;
}

.metric-card p {
	margin: 0;
	color: #617176;
	font-size: 13px;
}

.danger { border-color: #f4d6d2; background: #fff4f2; }
.warm { border-color: #f3dfbd; background: #fff8ed; }
.amber { border-color: #eee2c7; background: #fffaf0; }
.purple { border-color: #e4d8f7; background: #faf6ff; }
.green { border-color: #d7eadf; background: #f4fbf7; }

.chart-layout {
	display: grid;
	grid-template-columns: minmax(0, 1.55fr) minmax(320px, .85fr);
	gap: 16px;
	margin-top: 16px;
}

.trend-chart,
.pie-chart {
	height: 330px;
}

.heat-panel {
	margin-top: 16px;
}

.heat-row {
	display: grid;
	grid-template-columns: repeat(8, 1fr);
	gap: 8px;
}

.heat-segment {
	height: 72px;
	border-radius: 8px;
	display: flex;
	align-items: flex-end;
	padding: 10px;
	color: #fff;
	font-weight: 700;
}

.heat-segment.low { background: #9bd6cd; }
.heat-segment.medium { background: #f2bd5b; }
.heat-segment.high { background: #ef6c61; }

.legend {
	display: flex;
	gap: 18px;
	margin-top: 12px;
	color: #6b7b80;
}

.legend i {
	display: inline-block;
	width: 10px;
	height: 10px;
	margin-right: 6px;
	border-radius: 50%;
}

.legend .low { background: #9bd6cd; }
.legend .medium { background: #f2bd5b; }
.legend .high { background: #ef6c61; }

@media (max-width: 1120px) {
	.metric-grid {
		grid-template-columns: repeat(3, 1fr);
	}

	.chart-layout {
		grid-template-columns: 1fr;
	}
}
</style>
