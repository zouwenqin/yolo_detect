<template>
	<DemoShell active="stats" title="行为统计" :status="statsStatus" status-type="success">
		<div class="stats-page" v-loading="loading">
			<section class="panel source-panel">
				<div class="section-title source-title">
					<div>
						<h3>统计视频</h3>
						<p>当前统计：{{ selectedLabel }}</p>
					</div>
					<div class="source-switch">
						<el-select v-model="selectedSource" filterable placeholder="选择检测历史" @change="handleSourceChange">
							<el-option v-for="item in sourceOptions" :key="item.key" :label="item.label" :value="item.value">
								<div class="source-option">
									<strong>{{ item.label }}</strong>
									<span>{{ item.warningCount }} 条预警 · {{ item.startTime || '当前视频' }}</span>
								</div>
							</el-option>
						</el-select>
						<el-button @click="router.push('/detectionHistory')">检测历史</el-button>
					</div>
				</div>
				<div class="history-strip">
					<button
						v-for="item in sourceOptions"
						:key="`history-${item.key}`"
						class="history-item"
						:class="{ active: item.value === selectedSource }"
						type="button"
						@click="selectSource(item.value)"
					>
						<strong>{{ item.label }}</strong>
						<span>{{ item.startTime || '当前检测' }} · {{ item.warningCount }} 条预警</span>
					</button>
				</div>
			</section>

			<section class="panel summary-panel">
				<div class="section-title">
					<div>
						<h3>行为时长概览</h3>
						<p>按当前检测历史汇总行为持续时间、占比和预警次数。</p>
					</div>
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
						<p>按视频时间段聚合当前检测历史中的行为持续时间。</p>
					</div>
					<div id="statsTrendChart" class="trend-chart"></div>
				</section>
				<section class="panel pie-panel">
					<div class="section-title compact">
						<h3>行为占比</h3>
						<p>仅统计当前选中检测历史对应的行为结构。</p>
					</div>
					<div id="statsPieChart" class="pie-chart"></div>
				</section>
			</div>

			<section class="panel heat-panel">
				<div class="section-title compact">
					<h3>视频时间段热力条</h3>
					<p>基于视频内时间段聚合预警强度，颜色越深表示风险越高。</p>
				</div>
				<div class="heat-row">
					<div v-for="(item, index) in heatSegments" :key="`${item.time}-${item.level}-${index}`" class="heat-segment" :class="item.level">
						<span>{{ item.time }}</span>
						<em>{{ item.behaviorName }}</em>
					</div>
				</div>
				<div class="legend">
					<span><i class="normal"></i>无</span>
					<span><i class="low"></i>低</span>
					<span><i class="medium"></i>中</span>
					<span><i class="high"></i>高</span>
				</div>
			</section>
		</div>
	</DemoShell>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import * as echarts from 'echarts';
import DemoShell from '/@/views/demo/components/DemoShell.vue';
import { behaviorText, demoState, displaySourceName, normalizeBehavior, parseDurationSeconds, sourceNameKey, syncWarningRecords } from '/@/views/demo/demoState';
import request from '/@/utils/request';

type HistoryOption = {
	key: string;
	value: string;
	label: string;
	inputVideo: string;
	sourceKey: string;
	startTime: string;
	warningCount: number;
	isCurrent?: boolean;
};

type TimeBucket = {
	time: string;
	level: 'normal' | 'low' | 'medium' | 'high';
	score: number;
	total: number;
	behaviorName: string;
	data: Record<string, number>;
};

const router = useRouter();
const route = useRoute();
const trendChart = ref<any>(null);
const pieChart = ref<any>(null);
const loading = ref(false);
const selectedSource = ref('');
const videoRecords = ref<any[]>([]);
const warningRecords = ref<any[]>([]);
const currentPredictionWindows = ref<any[]>([]);
const selectedVideoDurationSeconds = ref(0);

const videoPageStorageKey = 'class-demo-video-predict-state';
const bucketCount = 8;
const behaviorChartColors: Record<string, string> = {
	head_down: '#f2a51a',
	lie_desk: '#ef4f45',
	focus: '#20aa82',
	other_action: '#5b6ee1',
	phone: '#8b5cf6',
	sleep: '#b45309',
	empty: '#dce8e5',
};

const sourceOptions = computed<HistoryOption[]>(() => {
	const options = new Map<string, HistoryOption>();
	const addOption = (source: any, row: any = {}, isCurrent = false) => {
		const label = displaySourceName(source);
		const key = sourceNameKey(source);
		if (!key || options.has(key)) return;
		options.set(key, {
			key,
			value: key,
			label,
			inputVideo: String(source || ''),
			sourceKey: key,
			startTime: isCurrent ? '当前检测' : (row.startTime || ''),
			warningCount: warningsForSource(source).length,
			isCurrent,
		});
	};
	uniqueLatestRecords(videoRecords.value).forEach((row) => addOption(row.inputVideo || row.sourceName || row.fileName, row));
	addOption(demoState.material.sourceName, { startTime: '当前检测' }, true);
	return Array.from(options.values());
});

const selectedOption = computed(() => sourceOptions.value.find((item) => item.value === selectedSource.value) || sourceOptions.value[0]);
const selectedLabel = computed(() => selectedOption.value?.label || displaySourceName(demoState.material.sourceName));
const statsStatus = computed(() => `${sourceOptions.value.length} 个历史可切换`);
const selectedWarnings = computed(() => selectedOption.value ? warningsForSource(selectedOption.value.inputVideo || selectedOption.value.label) : []);
const timeBuckets = computed(() => buildTimeBuckets(currentPredictionWindows.value, selectedWarnings.value));
const heatSegments = computed(() => timeBuckets.value);

function recordSource(row: any) {
	return row?.inputVideo || row?.sourceName || row?.fileName || '';
}

function recordTime(row: any) {
	const time = Date.parse(String(row?.startTime || row?.triggerTime || row?.createdAt || '').replace(/-/g, '/'));
	return Number.isFinite(time) ? time : Number(row?.id || 0);
}

function uniqueLatestRecords(records: any[]) {
	const groups = new Map<string, any>();
	[...records].sort((a, b) => recordTime(b) - recordTime(a)).forEach((row) => {
		const key = sourceNameKey(recordSource(row));
		if (key && !groups.has(key)) groups.set(key, row);
	});
	return Array.from(groups.values());
}

function warningSourceKey(record: any) {
	return sourceNameKey(record?.videoSource || record?.sourceName || record?.fileName || '');
}

function sourceMatches(left: any, right: any) {
	const leftKey = typeof left === 'string' ? sourceNameKey(left) : warningSourceKey(left);
	const rightKey = typeof right === 'string' ? sourceNameKey(right) : sourceNameKey(recordSource(right));
	return Boolean(leftKey && rightKey && (leftKey === rightKey || leftKey.includes(rightKey) || rightKey.includes(leftKey)));
}

function warningsForSource(source: any) {
	return warningRecords.value.filter((record) => sourceMatches(record, source));
}

function hasCurrentLiveStats(source: string) {
	return sourceMatches(demoState.material.sourceName, source)
		&& demoState.stats.some((item) => !['pending', 'empty'].includes(item.key) && Number(item.value || 0) > 0);
}

async function selectSource(value: string) {
	selectedSource.value = value;
	await handleSourceChange();
}

async function handleSourceChange() {
	const option = selectedOption.value;
	router.replace({ path: '/behaviorStats', query: option?.inputVideo ? { source: option.inputVideo } : {} });
	await applySelectedSource();
}

async function applySelectedSource() {
	const option = selectedOption.value || sourceOptions.value[0];
	if (!option) return;
	selectedSource.value = option.value;
	await loadPredictionWindowsForSelected(option);
	const source = option.inputVideo || option.label;
	if (warningsForSource(source).length || !hasCurrentLiveStats(source)) {
		syncWarningRecords(warningRecords.value, source);
	} else {
		demoState.material.sourceName = option.label;
	}
	refreshCharts();
}

async function loadPredictionWindowsForSelected(option: HistoryOption) {
	currentPredictionWindows.value = [];
	selectedVideoDurationSeconds.value = parseClockSeconds(demoState.material.duration);
	try {
		const raw = sessionStorage.getItem(videoPageStorageKey);
		const state = raw ? JSON.parse(raw) : null;
		if (state && sourceMatches(state.sourceName || '', option.inputVideo || option.label)) {
			if (Array.isArray(state.predictionWindows)) currentPredictionWindows.value = state.predictionWindows;
			if (Number(state.videoDurationSeconds) > 0) selectedVideoDurationSeconds.value = Number(state.videoDurationSeconds);
			if (!currentPredictionWindows.value.length && state.currentTaskId) {
				const res = await request.get(`/flask/videoTasks/${state.currentTaskId}`);
				if (res?.code === 0 && res.data) {
					if (Array.isArray(res.data.predictionWindows)) currentPredictionWindows.value = res.data.predictionWindows;
					if (Number(res.data.videoInfo?.durationSeconds) > 0) selectedVideoDurationSeconds.value = Number(res.data.videoInfo.durationSeconds);
				}
			}
		}
	} catch (error) {
		currentPredictionWindows.value = [];
	}
}

function chartStats() {
	const fromBuckets = aggregateBuckets(timeBuckets.value);
	if (fromBuckets.length) return fromBuckets;
	return demoState.stats
		.map((item) => {
			const value = Number(item.value ?? parseDurationSeconds(item.duration));
			return {
				key: item.key,
				label: item.label || behaviorText(item.key),
				value: Number.isFinite(value) ? value : 0,
			};
		})
		.filter((item) => item.value > 0 && !['pending', 'empty', 'failed'].includes(item.key));
}

function aggregateBuckets(buckets: TimeBucket[]) {
	const totals = new Map<string, number>();
	buckets.forEach((bucket) => {
		Object.entries(bucket.data).forEach(([key, value]) => {
			totals.set(key, (totals.get(key) || 0) + Number(value || 0));
		});
	});
	return Array.from(totals.entries())
		.filter(([, value]) => value > 0)
		.map(([key, value]) => ({ key, label: behaviorText(key), value }));
}

function buildTimeBuckets(windows: any[], warnings: any[]): TimeBucket[] {
	const duration = inferVideoDuration(windows, warnings);
	const bucketSize = duration / bucketCount;
	const buckets = Array.from({ length: bucketCount }, (_, index) => createBucket(index, bucketSize));
	if (Array.isArray(windows) && windows.length) {
		windows.forEach((item) => addWindowToBuckets(buckets, {
			behaviorType: normalizeBehavior(item.behaviorType || item.behaviorName || item.rawLabel || 'none'),
			riskLevel: behaviorRiskLevel(item.behaviorType || item.behaviorName),
			start: Number(item.startSecond || 0),
			end: Number(item.endSecond || 0) || Number(item.startSecond || 0) + Number(item.durationSeconds || 0),
		}, bucketSize));
	} else {
		const placedWarnings = placeWarningsOnTimeline(warnings, duration);
		placedWarnings.forEach((item) => addWindowToBuckets(buckets, item, bucketSize));
	}
	return buckets.map(finalizeBucket);
}

function createBucket(index: number, bucketSize: number): TimeBucket {
	const start = index * bucketSize;
	const end = (index + 1) * bucketSize;
	return {
		time: `${formatClockShort(start)}-${formatClockShort(end)}`,
		level: 'normal',
		score: 0,
		total: 0,
		behaviorName: '无事件',
		data: {},
	};
}

function addWindowToBuckets(buckets: TimeBucket[], item: any, bucketSize: number) {
	const start = Math.max(0, Number(item.start || 0));
	const end = Math.max(start, Number(item.end || start));
	if (end <= start) return;
	const key = normalizeBehavior(item.behaviorType || 'none');
	const weight = riskWeight(item.riskLevel || behaviorRiskLevel(key));
	buckets.forEach((bucket, index) => {
		const bucketStart = index * bucketSize;
		const bucketEnd = (index + 1) * bucketSize;
		const overlap = Math.max(0, Math.min(end, bucketEnd) - Math.max(start, bucketStart));
		if (overlap <= 0) return;
		bucket.data[key] = (bucket.data[key] || 0) + overlap;
		bucket.total += overlap;
		bucket.score += overlap * weight;
	});
}

function placeWarningsOnTimeline(warnings: any[], duration: number) {
	const sorted = [...warnings].sort((a, b) => recordTime(a) - recordTime(b));
	const times = sorted.map((item) => recordTime(item)).filter((time) => time > 0);
	const minTime = times.length ? Math.min(...times) : 0;
	const maxTime = times.length ? Math.max(...times) : 0;
	const hasTimeSpread = maxTime - minTime > 60 * 1000;
	return sorted.map((record, index) => {
		const seconds = Math.max(1, Number(record.durationSeconds || 0) || parseDurationSeconds(record.durationText || ''));
		const center = hasTimeSpread
			? ((recordTime(record) - minTime) / Math.max(1, maxTime - minTime)) * duration
			: ((index + 0.5) / Math.max(1, sorted.length)) * duration;
		const start = Math.max(0, center - seconds / 2);
		return {
			behaviorType: normalizeBehavior(record.behaviorType || record.behaviorName || record.type || 'none'),
			riskLevel: record.riskLevel || behaviorRiskLevel(record.behaviorType),
			start,
			end: Math.min(duration, start + seconds),
		};
	});
}

function finalizeBucket(bucket: TimeBucket) {
	const dominant = Object.entries(bucket.data).sort((a, b) => b[1] - a[1])[0];
	const averageScore = bucket.total ? bucket.score / bucket.total : 0;
	return {
		...bucket,
		level: scoreLevel(averageScore),
		behaviorName: dominant ? behaviorText(dominant[0]) : '无事件',
	};
}

function inferVideoDuration(windows: any[], warnings: any[]) {
	const windowEnd = Math.max(0, ...windows.map((item) => Number(item.endSecond || 0)));
	if (windowEnd > 0) return windowEnd;
	if (selectedVideoDurationSeconds.value > 0) return selectedVideoDurationSeconds.value;
	const warningTotal = warnings.reduce((sum, item) => sum + (Number(item.durationSeconds || 0) || parseDurationSeconds(item.durationText || '')), 0);
	return Math.max(60, warningTotal || parseClockSeconds(demoState.material.duration) || 60);
}

function parseClockSeconds(text = '') {
	const match = String(text || '').match(/^(?:(\d+):)?(\d{1,2}):(\d{1,2})$/);
	if (!match) return 0;
	return Number(match[1] || 0) * 3600 + Number(match[2] || 0) * 60 + Number(match[3] || 0);
}

function formatClockShort(seconds: number) {
	const safe = Math.max(0, Math.round(seconds || 0));
	const m = Math.floor(safe / 60);
	const s = safe % 60;
	return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function behaviorRiskLevel(behaviorType: any) {
	const key = normalizeBehavior(String(behaviorType || ''));
	if (key === 'lie_desk' || key === 'sleep') return 'high';
	if (key === 'head_down' || key === 'phone') return 'medium';
	if (key === 'focus' || key === 'other_action') return 'low';
	return 'low';
}

function riskWeight(level: any) {
	const raw = String(level || '').toLowerCase();
	if (raw === 'high' || raw.includes('高')) return 3;
	if (raw === 'medium' || raw.includes('中')) return 2;
	if (raw === 'low' || raw.includes('低')) return 1;
	return 1;
}

function scoreLevel(score: number): TimeBucket['level'] {
	if (score >= 2.4) return 'high';
	if (score >= 1.5) return 'medium';
	if (score > 0) return 'low';
	return 'normal';
}

function behaviorColor(key: string) {
	return behaviorChartColors[key] || '#64748b';
}

function refreshCharts() {
	nextTick(() => {
		window.requestAnimationFrame(() => {
			updateTrendChart();
			updatePieChart();
			resizeCharts();
		});
	});
}

function initCharts() {
	const trendEl = document.getElementById('statsTrendChart');
	const pieEl = document.getElementById('statsPieChart');
	if (trendEl) {
		echarts.getInstanceByDom(trendEl)?.dispose();
		trendChart.value = echarts.init(trendEl);
	}
	if (pieEl) {
		echarts.getInstanceByDom(pieEl)?.dispose();
		pieChart.value = echarts.init(pieEl);
	}
	refreshCharts();
}

function updateTrendChart() {
	if (!trendChart.value) return;
	const buckets = timeBuckets.value;
	const behaviorKeys = Array.from(new Set(buckets.flatMap((bucket) => Object.keys(bucket.data))));
	const hasData = behaviorKeys.length > 0;
	trendChart.value.clear();
	trendChart.value.setOption({
		color: behaviorKeys.map((key) => behaviorColor(key)),
		tooltip: { trigger: 'axis', valueFormatter: (value: number) => `${Number(value || 0).toFixed(1)} 秒` },
		legend: { show: hasData, top: 0, right: 8, itemWidth: 10, itemHeight: 8 },
		grid: { left: 42, right: 24, top: 48, bottom: 42 },
		xAxis: { type: 'category', data: buckets.map((item) => item.time), axisLabel: { interval: 0, rotate: 22 } },
		yAxis: { type: 'value', name: '秒' },
		series: hasData
			? behaviorKeys.map((key) => ({
				name: behaviorText(key),
				type: 'bar',
				stack: 'duration',
				barMaxWidth: 34,
				data: buckets.map((bucket) => Number((bucket.data[key] || 0).toFixed(1))),
			}))
			: [{ name: '暂无统计数据', type: 'bar', barMaxWidth: 34, data: buckets.map(() => 0), itemStyle: { color: '#dce8e5' } }],
	}, true);
}

function updatePieChart() {
	if (!pieChart.value) return;
	const stats = chartStats();
	const hasData = stats.length > 0;
	pieChart.value.clear();
	pieChart.value.setOption({
		color: stats.map((item) => behaviorColor(item.key)),
		tooltip: { trigger: 'item' },
		legend: { show: hasData, bottom: 0, itemWidth: 8, itemHeight: 8 },
		series: [{
			type: 'pie',
			radius: ['48%', '72%'],
			center: ['50%', '44%'],
			label: { show: false },
			silent: !hasData,
			data: hasData
				? stats.map((item) => ({ name: item.label, value: item.value, itemStyle: { color: behaviorColor(item.key) } }))
				: [{ name: '暂无统计数据', value: 1, itemStyle: { color: '#dce8e5' } }],
		}],
	}, true);
}

function resizeCharts() {
	trendChart.value?.resize();
	pieChart.value?.resize();
}

async function loadPageData() {
	loading.value = true;
	try {
		const [warningRes, videoRes] = await Promise.all([
			request.get('/api/warningRecords/all'),
			request.get('/api/videoRecords/all'),
		]);
		warningRecords.value = warningRes?.code == 0 && Array.isArray(warningRes.data) ? warningRes.data : [];
		videoRecords.value = videoRes?.code == 0 && Array.isArray(videoRes.data) ? videoRes.data : [];
		const routeSource = typeof route.query.source === 'string' ? route.query.source : '';
		const routeKey = routeSource ? sourceNameKey(routeSource) : '';
		const matched = sourceOptions.value.find((item) => item.value === routeSource || item.sourceKey === routeKey);
		selectedSource.value = matched?.value || sourceOptions.value[0]?.value || '';
		await applySelectedSource();
	} finally {
		loading.value = false;
	}
}

watch(
	() => [
		selectedSource.value,
		demoState.stats.map((item) => `${item.key}:${item.value}:${item.count}`).join('|'),
		currentPredictionWindows.value.length,
		selectedWarnings.value.length,
	].join('|'),
	refreshCharts
);

onMounted(async () => {
	await loadPageData();
	nextTick(initCharts);
	window.addEventListener('resize', resizeCharts);
});
onUnmounted(() => {
	window.removeEventListener('resize', resizeCharts);
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

.source-panel {
	margin-bottom: 16px;
}

.section-title {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 16px;
	margin-bottom: 14px;
}

.source-title {
	align-items: center;
	margin-bottom: 0;
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

.source-switch {
	display: grid;
	grid-template-columns: minmax(260px, 360px) auto;
	gap: 10px;
	align-items: center;
}

.source-option {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
}

.source-option strong {
	min-width: 0;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.source-option span {
	color: #7a8a90;
	font-size: 12px;
	white-space: nowrap;
}

.history-strip {
	display: flex;
	gap: 8px;
	margin-top: 14px;
	padding-bottom: 2px;
	overflow-x: auto;
	scrollbar-width: thin;
}

.history-item {
	min-width: 180px;
	max-width: 240px;
	border: 1px solid #d8e8e4;
	background: #f8fbfa;
	border-radius: 8px;
	padding: 10px 12px;
	text-align: left;
	cursor: pointer;
}

.history-item.active {
	border-color: #00a99d;
	background: #eaf8f5;
	box-shadow: 0 8px 18px rgba(0, 143, 135, .14);
}

.history-item strong,
.history-item span {
	display: block;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.history-item strong {
	color: #173337;
	font-size: 14px;
}

.history-item span {
	margin-top: 4px;
	color: #718388;
	font-size: 12px;
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
	grid-template-columns: repeat(8, minmax(92px, 1fr));
	gap: 8px;
}

.heat-segment {
	height: 78px;
	border-radius: 8px;
	display: flex;
	flex-direction: column;
	align-items: flex-start;
	justify-content: flex-end;
	padding: 10px;
	color: #fff;
	font-weight: 700;
}

.heat-segment span,
.heat-segment em {
	max-width: 100%;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.heat-segment em {
	margin-top: 4px;
	font-style: normal;
	font-size: 12px;
	opacity: .9;
}

.heat-segment.normal { background: #b8d8d3; color: #24474b; }
.heat-segment.low { background: #7ccfc4; }
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

.legend .normal { background: #b8d8d3; }
.legend .low { background: #7ccfc4; }
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

@media (max-width: 760px) {
	.section-title,
	.source-title,
	.source-switch {
		grid-template-columns: 1fr;
		display: grid;
	}

	.metric-grid,
	.heat-row {
		grid-template-columns: 1fr;
	}
}
</style>
