<template>
	<div class="dashboard-container layout-padding">
		<div class="dashboard-content layout-padding-auto layout-padding-view">
			<div class="stats-grid">
				<div class="stat-card">
					<span>今日预警</span>
					<strong>{{ stats.todayWarnings }}</strong>
				</div>
				<div class="stat-card danger">
					<span>高风险预警</span>
					<strong>{{ stats.highWarnings }}</strong>
				</div>
				<div class="stat-card">
					<span>待处理</span>
					<strong>{{ stats.pendingWarnings }}</strong>
				</div>
				<div class="stat-card">
					<span>主要异常行为</span>
					<strong>{{ stats.topBehavior }}</strong>
				</div>
			</div>

			<div class="charts-row">
				<div class="chart-card">
					<div class="chart-title">最近五天预警趋势</div>
					<div ref="trendChartRef" class="chart"></div>
				</div>
				<div class="chart-card">
					<div class="chart-title">异常行为分布</div>
					<div ref="behaviorChartRef" class="chart"></div>
				</div>
			</div>

			<div class="latest-card">
				<div class="chart-title">最近预警</div>
				<el-table :data="latestWarnings" style="width: 100%">
					<el-table-column prop="riskLevel" label="等级" width="100" align="center">
						<template #default="scope">
							<el-tag :type="riskTagType(scope.row.riskLevel)">{{ riskText(scope.row.riskLevel) }}</el-tag>
						</template>
					</el-table-column>
					<el-table-column prop="behaviorType" label="行为" width="110" align="center">
						<template #default="scope">{{ behaviorText(scope.row.behaviorType) }}</template>
					</el-table-column>
					<el-table-column prop="reason" label="触发原因" show-overflow-tooltip />
					<el-table-column prop="advice" label="教师建议" show-overflow-tooltip />
					<el-table-column prop="triggerTime" label="触发时间" width="180" align="center" />
				</el-table>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue';
import request from '/@/utils/request';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';

const warnings = ref<any[]>([]);
const trendChartRef = ref<HTMLElement | null>(null);
const behaviorChartRef = ref<HTMLElement | null>(null);

const behaviorText = (behavior: string) => ({ sleep: '睡觉', lie_desk: '趴桌', head_down: '低头', phone: '玩手机' } as any)[behavior] || behavior || '暂无';
const riskText = (risk: string) => ({ high: '高风险', medium: '中风险', low: '低风险', normal: '正常' } as any)[risk] || '正常';
const riskTagType = (risk: string) => ({ high: 'danger', medium: 'warning', low: 'info', normal: 'success' } as any)[risk] || 'success';

const stats = reactive({
	todayWarnings: 0,
	highWarnings: 0,
	pendingWarnings: 0,
	topBehavior: '暂无',
});

const latestWarnings = computed(() => warnings.value.slice(0, 6));

const getWarningData = () => {
	request.get('/api/warningRecords/all').then((res) => {
		if (res.code == 0) {
			warnings.value = (res.data || []).sort((a: any, b: any) => (b.triggerTime || '').localeCompare(a.triggerTime || ''));
			updateStats();
			nextTick(drawCharts);
		} else {
			ElMessage.error(res.msg);
		}
	});
};

const updateStats = () => {
	const today = new Date();
	const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
	const behaviorCount = new Map<string, number>();
	stats.todayWarnings = warnings.value.filter((item: any) => (item.triggerTime || '').startsWith(todayStr)).length;
	stats.highWarnings = warnings.value.filter((item: any) => item.riskLevel === 'high').length;
	stats.pendingWarnings = warnings.value.filter((item: any) => (item.status || '未处理') === '未处理').length;
	warnings.value.forEach((item: any) => {
		const behavior = item.behaviorType || 'unknown';
		behaviorCount.set(behavior, (behaviorCount.get(behavior) || 0) + 1);
	});
	let topBehavior = '';
	let topCount = 0;
	behaviorCount.forEach((count, behavior) => {
		if (count > topCount) {
			topCount = count;
			topBehavior = behavior;
		}
	});
	stats.topBehavior = topBehavior ? behaviorText(topBehavior) : '暂无';
};

const drawCharts = () => {
	drawTrendChart();
	drawBehaviorChart();
};

const drawTrendChart = () => {
	if (!trendChartRef.value) return;
	const chart = echarts.init(trendChartRef.value);
	const dayMap = new Map<string, number>();
	const now = new Date();
	for (let i = 4; i >= 0; i--) {
		const date = new Date();
		date.setDate(now.getDate() - i);
		const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
		dayMap.set(key, 0);
	}
	warnings.value.forEach((item: any) => {
		const day = (item.triggerTime || '').split(' ')[0];
		if (dayMap.has(day)) dayMap.set(day, (dayMap.get(day) || 0) + 1);
	});
	const days = Array.from(dayMap.keys());
	chart.setOption({
		tooltip: { trigger: 'axis' },
		xAxis: { type: 'category', data: days.map((day) => day.slice(5)) },
		yAxis: { type: 'value' },
		series: [{ name: '预警数', type: 'line', smooth: true, data: days.map((day) => dayMap.get(day)), itemStyle: { color: '#409eff' } }],
	});
};

const drawBehaviorChart = () => {
	if (!behaviorChartRef.value) return;
	const chart = echarts.init(behaviorChartRef.value);
	const behaviorCount = new Map<string, number>();
	warnings.value.forEach((item: any) => {
		const behavior = item.behaviorType || 'unknown';
		behaviorCount.set(behavior, (behaviorCount.get(behavior) || 0) + 1);
	});
	chart.setOption({
		tooltip: { trigger: 'item' },
		series: [{
			name: '异常行为',
			type: 'pie',
			radius: ['42%', '68%'],
			data: Array.from(behaviorCount.entries()).map(([name, value]) => ({ name: behaviorText(name), value })),
		}],
	});
};

onMounted(() => {
	getWarningData();
});
</script>

<style scoped lang="scss">
.dashboard-container {
	width: 100%;
	height: 100%;
}

.dashboard-content {
	padding: 18px;
	background: #f6f8fb;
}

.stats-grid {
	display: grid;
	grid-template-columns: repeat(4, minmax(160px, 1fr));
	gap: 16px;
	margin-bottom: 18px;
}

.stat-card,
.chart-card,
.latest-card {
	background: #fff;
	border-radius: 8px;
	box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.stat-card {
	padding: 18px;
	display: flex;
	flex-direction: column;
	gap: 10px;
}

.stat-card span {
	color: #909399;
}

.stat-card strong {
	font-size: 28px;
	color: #303133;
}

.stat-card.danger strong {
	color: #f56c6c;
}

.charts-row {
	display: grid;
	grid-template-columns: repeat(2, minmax(320px, 1fr));
	gap: 18px;
	margin-bottom: 18px;
}

.chart-card,
.latest-card {
	padding: 18px;
}

.chart-title {
	font-size: 18px;
	font-weight: 700;
	margin-bottom: 12px;
	color: #303133;
}

.chart {
	width: 100%;
	height: 340px;
}

@media (max-width: 900px) {
	.stats-grid,
	.charts-row {
		grid-template-columns: 1fr;
	}
}
</style>
