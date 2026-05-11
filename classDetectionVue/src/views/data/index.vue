<template>
	<div class="demo-dashboard layout-padding">
		<div class="demo-page layout-padding-auto layout-padding-view">
			<section class="hero-panel">
				<div>
					<p class="eyebrow">职业技能大赛演示版</p>
					<h1>课堂行为检测演示工作台</h1>
					<p class="summary">围绕录制视频与图片素材完成行为识别、风险研判和AI辅助干预建议展示，不涉及学生实名追踪。</p>
				</div>
				<div class="hero-actions">
					<el-button type="primary" @click="$router.push('/videoPredict')">录制视频检测</el-button>
					<el-button @click="$router.push('/imgPredict')">图片检测</el-button>
				</div>
			</section>

			<section class="metric-grid">
				<div class="metric-card">
					<span>视频素材数</span>
					<strong>{{ stats.videoCount }}</strong>
					<p>已保存的视频检测记录</p>
				</div>
				<div class="metric-card">
					<span>检测事件数</span>
					<strong>{{ stats.eventCount }}</strong>
					<p>由异常行为触发的研判事件</p>
				</div>
				<div class="metric-card accent">
					<span>AI建议数</span>
					<strong>{{ stats.adviceCount }}</strong>
					<p>已生成教师沟通建议</p>
				</div>
				<div class="metric-card warm">
					<span>干预报告数</span>
					<strong>{{ stats.reportCount }}</strong>
					<p>可用于演示闭环汇报</p>
				</div>
			</section>

			<section class="workspace-grid">
				<div class="analysis-panel">
					<div class="panel-title">
						<div>
							<span>行为统计</span>
							<h3>检测事件分布</h3>
						</div>
						<el-tag type="success">演示数据汇总</el-tag>
					</div>
					<div ref="behaviorChartRef" class="chart"></div>
				</div>

				<div class="analysis-panel">
					<div class="panel-title">
						<div>
							<span>近五日趋势</span>
							<h3>AI干预建议生成</h3>
						</div>
						<el-tag>非诊断建议</el-tag>
					</div>
					<div ref="trendChartRef" class="chart"></div>
				</div>
			</section>

			<section class="record-panel">
				<div class="panel-title">
					<div>
						<span>最近检测结果</span>
						<h3>AI辅助干预记录</h3>
					</div>
					<el-button text type="primary" @click="$router.push('/warningRecord')">查看全部</el-button>
				</div>
				<el-table :data="latestWarnings" style="width: 100%">
					<el-table-column prop="detectionType" label="来源" width="110" align="center">
						<template #default="scope">{{ sourceText(scope.row.detectionType) }}</template>
					</el-table-column>
					<el-table-column prop="riskLevel" label="风险研判" width="120" align="center">
						<template #default="scope">
							<el-tag :type="riskTagType(scope.row.riskLevel)">{{ riskText(scope.row.riskLevel) }}</el-tag>
						</template>
					</el-table-column>
					<el-table-column prop="behaviorType" label="检测行为" width="120" align="center">
						<template #default="scope">{{ behaviorText(scope.row.behaviorType) }}</template>
					</el-table-column>
					<el-table-column prop="reason" label="事件摘要" show-overflow-tooltip />
					<el-table-column prop="advice" label="AI沟通建议" show-overflow-tooltip />
					<el-table-column prop="triggerTime" label="生成时间" width="180" align="center" />
				</el-table>
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue';
import request from '/@/utils/request';
import { ElMessage } from 'element-plus';
import * as echarts from 'echarts';

const warnings = ref<any[]>([]);
const videos = ref<any[]>([]);
const trendChartRef = ref<HTMLElement | null>(null);
const behaviorChartRef = ref<HTMLElement | null>(null);

const stats = reactive({
	videoCount: 0,
	eventCount: 0,
	adviceCount: 0,
	reportCount: 0,
});

const latestWarnings = computed(() => warnings.value.slice(0, 6));

const behaviorText = (behavior: string) => ({ sleep: '疑似睡觉', lie_desk: '趴桌', head_down: '持续低头', phone: '玩手机' } as any)[behavior] || behavior || '课堂行为';
const riskText = (risk: string) => ({ high: '高风险', medium: '中风险', low: '低风险', normal: '正常' } as any)[risk] || '正常';
const sourceText = (source: string) => ({ video: '视频素材', image: '图片素材', camera: '摄像头' } as any)[source] || '检测素材';
const riskTagType = (risk: string) => ({ high: 'danger', medium: 'warning', low: 'info', normal: 'success' } as any)[risk] || 'success';

const getDashboardData = async () => {
	try {
		const [warningRes, videoRes] = await Promise.all([
			request.get('/api/warningRecords/all'),
			request.get('/api/videoRecords/all'),
		]);
		if (warningRes.code == 0) {
			warnings.value = (warningRes.data || []).sort((a: any, b: any) => (b.triggerTime || '').localeCompare(a.triggerTime || ''));
		} else {
			ElMessage.error(warningRes.msg);
		}
		if (videoRes.code == 0) {
			videos.value = videoRes.data || [];
		}
		updateStats();
		nextTick(drawCharts);
	} catch (error) {
		ElMessage.error('演示数据加载失败');
	}
};

const updateStats = () => {
	stats.videoCount = videos.value.length;
	stats.eventCount = warnings.value.length;
	stats.adviceCount = warnings.value.filter((item) => item.advice).length;
	stats.reportCount = warnings.value.filter((item) => item.status === '已处理' || item.advice).length;
};

const drawCharts = () => {
	drawBehaviorChart();
	drawTrendChart();
};

const drawBehaviorChart = () => {
	if (!behaviorChartRef.value) return;
	const chart = echarts.init(behaviorChartRef.value);
	const behaviorCount = new Map<string, number>();
	warnings.value.forEach((item: any) => {
		const behavior = item.behaviorType || 'unknown';
		behaviorCount.set(behavior, (behaviorCount.get(behavior) || 0) + 1);
	});
	const data = Array.from(behaviorCount.entries()).map(([name, value]) => ({ name: behaviorText(name), value }));
	chart.setOption({
		color: ['#2aa79b', '#f5b85f', '#ef7f72', '#7aa7ff'],
		tooltip: { trigger: 'item' },
		legend: { bottom: 0 },
		series: [{
			name: '检测事件',
			type: 'pie',
			radius: ['45%', '68%'],
			center: ['50%', '45%'],
			data: data.length ? data : [{ name: '暂无事件', value: 1 }],
			label: { formatter: '{b}' },
		}],
	});
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
		color: ['#2aa79b'],
		tooltip: { trigger: 'axis' },
		grid: { left: 36, right: 18, top: 20, bottom: 36 },
		xAxis: { type: 'category', data: days.map((day) => day.slice(5)), boundaryGap: false },
		yAxis: { type: 'value', minInterval: 1 },
		series: [{ name: 'AI建议', type: 'line', smooth: true, areaStyle: { opacity: 0.12 }, data: days.map((day) => dayMap.get(day)) }],
	});
};

onMounted(getDashboardData);
</script>

<style scoped lang="scss">
.demo-dashboard {
	width: 100%;
	min-height: 100%;
	background: #f5f8f7;
	color: #1f2f35;
}

.demo-page {
	padding: 20px;
	background:
		linear-gradient(180deg, rgba(240, 250, 247, 0.94) 0%, rgba(248, 250, 249, 1) 100%);
}

.hero-panel,
.metric-card,
.analysis-panel,
.record-panel {
	background: rgba(255, 255, 255, 0.94);
	border: 1px solid #e4eeeb;
	border-radius: 8px;
	box-shadow: 0 14px 34px rgba(42, 69, 77, 0.08);
}

.hero-panel {
	min-height: 160px;
	padding: 26px 30px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 24px;
	background: linear-gradient(135deg, #f8fffd 0%, #edf8f5 100%);
}

.eyebrow,
.panel-title span,
.metric-card span {
	margin: 0 0 8px;
	color: #2aa79b;
	font-size: 13px;
	font-weight: 700;
}

h1 {
	margin: 0;
	font-size: 30px;
	letter-spacing: 0;
}

.summary {
	max-width: 680px;
	margin: 12px 0 0;
	color: #64777d;
	line-height: 1.8;
}

.hero-actions {
	display: flex;
	gap: 12px;
	flex-shrink: 0;
}

.metric-grid {
	display: grid;
	grid-template-columns: repeat(4, minmax(160px, 1fr));
	gap: 16px;
	margin: 18px 0;
}

.metric-card {
	padding: 20px;
}

.metric-card strong {
	display: block;
	font-size: 32px;
	margin: 8px 0;
}

.metric-card p {
	margin: 0;
	color: #819197;
}

.metric-card.accent strong { color: #2aa79b; }
.metric-card.warm strong { color: #ef8f62; }

.workspace-grid {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 18px;
	margin-bottom: 18px;
}

.analysis-panel,
.record-panel {
	padding: 20px;
}

.panel-title {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	gap: 16px;
	margin-bottom: 14px;
}

.panel-title h3 {
	margin: 0;
	font-size: 18px;
}

.chart {
	width: 100%;
	height: 310px;
}

@media (max-width: 1100px) {
	.hero-panel,
	.hero-actions {
		align-items: flex-start;
		flex-direction: column;
	}

	.metric-grid,
	.workspace-grid {
		grid-template-columns: 1fr;
	}
}
</style>
