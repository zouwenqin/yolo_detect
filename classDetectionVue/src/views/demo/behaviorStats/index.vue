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

			<section v-if="false" class="panel summary-panel">
				<div class="section-title">
					<div>
						<h3>行为时长概览</h3>
						<p>按当前检测历史汇总行为持续时间、占比和预警次数。</p>
					</div>
				</div>
				<div class="metric-grid">
					<div v-for="item in displayStats" :key="item.key" class="metric-card" :class="item.tone">
						<span>{{ item.label }}</span>
						<strong>{{ item.duration }}</strong>
						<p>占比 {{ item.ratio }} · {{ item.count }} 次</p>
					</div>
				</div>
			</section>

			<div class="chart-layout">
				<section class="panel spatial-panel">
					<div class="section-title compact">
						<h3>整段空间热力图</h3>
						<p>汇总整段视频中的行为空间分布，颜色越集中表示该区域异常持续越久。</p>
					</div>
					<div class="spatial-title">
						<h3>行为空间热力图</h3>
						<p>基于头部、肩背等关键点累计生成，不显示单帧文本标注，减少对学生姿态和环境的遮挡。</p>
					</div>
					<div class="spatial-body">
					<div class="spatial-map" :style="spatialMapStyle">
						<video
							v-if="currentSpatialVideoUrl"
							ref="spatialVideoRef"
							class="spatial-video"
							:src="currentSpatialVideoUrl"
							muted
							playsinline
							preload="metadata"
							@loadedmetadata="resetSpatialVideoFrame"
						></video>
						<div class="video-shade"></div>
						<div class="map-grid"></div>
						<div
							v-for="(item, index) in currentHeatmapAlerts"
							:key="item.key"
							class="alert-badge"
							:class="`risk-${item.risk}`"
							:style="alertBadgeStyle(item, index)"
							:title="alertTooltip(item)"
						>
							<span class="alert-badge__id">ID {{ item.trackId }}</span>
							<strong>{{ formatDurationDisplay(item.seconds) }}</strong>
							<em>{{ item.label }}</em>
						</div>
						<div v-if="!currentHeatmapAlerts.length" class="map-empty">暂无异常行为空间数据</div>
					</div>
						<aside class="heatmap-alerts">
							<div class="alerts-head">
								<strong>异常行为 Top</strong>
								<span>{{ currentHeatmapAlerts.length }} 项</span>
							</div>
							<div v-if="!currentHeatmapAlerts.length" class="alert-empty">整段视频暂无重点异常</div>
							<div
								v-for="item in currentHeatmapAlerts"
								:key="item.key"
								class="alert-item"
								:class="`risk-${item.risk}`"
							>
								<span class="alert-id">ID {{ item.trackId }} · {{ item.label }}</span>
								<strong>{{ formatDurationDisplay(item.seconds) }}</strong>
								<em>{{ item.riskText }}</em>
							</div>
						</aside>
					</div>
					<div class="spatial-legend">
						<span><i class="legend-normal"></i>正常/短暂</span>
						<span><i class="legend-medium"></i>持续低头</span>
						<span><i class="legend-high"></i>趴桌/高风险</span>
						<span><i class="legend-cumulative"></i>累积越深表示持续越久</span>
					</div>
				</section>
				<section class="panel pie-panel">
					<div class="section-title compact">
						<h3>行为占比</h3>
						<p>仅统计当前选中检测历史对应的行为结构。</p>
					</div>
					<div id="statsPieChart" class="pie-chart"></div>
				</section>
			</div>

			<section v-if="false" class="panel heat-panel">
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
import { behaviorText, clearDemoDetectionState, demoState, displaySourceName, filterWarningRecordsByHistories, normalizeBehavior, parseDurationSeconds, riskText, sourceNameKey, syncWarningRecords } from '/@/views/demo/demoState';
import request from '/@/utils/request';

type HistoryOption = {
	key: string;
	value: string;
	label: string;
	inputVideo: string;
	inputVideoUrl?: string;
	datasetValue: string;
	sourceKey: string;
	startTime: string;
	warningCount: number;
	isCurrent?: boolean;
	resultVideoUrl?: string;
};

type ChartStat = {
	key: string;
	label: string;
	value: number;
	count: number;
};

type SpatialPoint = {
	trackId?: string | number;
	behaviorType: string;
	behaviorName?: string;
	riskLevel?: string;
	anchorType?: string;
	x: number;
	y: number;
	value: number;
	confidence?: number;
	score?: number;
	startSecond?: number;
	endSecond?: number;
	timeSecond?: number;
};

type TimeBucket = {
	time: string;
	start: number;
	end: number;
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
const currentBehaviorHeatmap = ref<SpatialPoint[]>([]);
const spatialVideoRef = ref<HTMLVideoElement>();
const currentSpatialVideoUrl = ref('');
const selectedVideoDurationSeconds = ref(0);
const selectedVideoAspectRatio = ref('16 / 9');

const videoPageStorageKey = 'class-demo-video-predict-state';
const bucketCount = 8;
const sourceOptions = computed<HistoryOption[]>(() => {
	const options = new Map<string, HistoryOption>();
	const addOption = (source: any, row: any = {}, isCurrent = false) => {
		const label = displaySourceName(source);
		const key = sourceNameKey(source);
		if (!key || options.has(key)) return;
		const datasetValue = inferDatasetValue(source, row);
		const sourceText = String(source || row.inputVideo || row.sourceName || row.fileName || '');
		const isPreprocessed = Boolean(row.preprocessedDataset || row.weight?.includes?.('class/precomputed') || /[\\/]class[\\/]input[\\/]/i.test(sourceText));
		options.set(key, {
			key,
			value: key,
			label,
			inputVideo: String(source || ''),
			inputVideoUrl: row.inputVideoUrl || (isPreprocessed ? preprocessedInputVideoUrl(datasetValue) : ''),
			datasetValue,
			sourceKey: key,
			startTime: isCurrent ? '当前检测' : (row.startTime || ''),
			warningCount: warningsForSource(source).length,
			isCurrent,
			resultVideoUrl: row.resultVideoUrl || '',
		});
	};
	if (!videoRecords.value.length && !demoState.hasLiveData && !hasCurrentLiveStats(demoState.material.sourceName)) {
		return [];
	}
	const savedState = readVideoPageState();
	if (savedState?.sourceName && (videoRecords.value.length || demoState.hasLiveData)) {
		addOption(savedState.sourceName, {
			startTime: '最近检测',
			preprocessedDataset: savedState.preprocessedDataset,
			inputVideo: savedState.sourceName,
			inputVideoUrl: savedState.inputVideoUrl || (!String(savedState.previewUrl || '').startsWith('blob:') ? savedState.previewUrl : '') || (savedState.currentTaskId ? `/flask/videoTasks/${savedState.currentTaskId}/input-video` : ''),
			resultVideoUrl: savedState.resultVideoUrl,
		}, true);
	}
	uniqueLatestRecords(videoRecords.value).forEach((row) => addOption(row.inputVideo || row.sourceName || row.fileName, row));
	if (demoState.hasLiveData || hasCurrentLiveStats(demoState.material.sourceName)) {
		addOption(demoState.material.sourceName, { startTime: '当前检测' }, true);
	}
	return Array.from(options.values());
});

const selectedOption = computed(() => sourceOptions.value.find((item) => item.value === selectedSource.value) || sourceOptions.value[0]);
const selectedLabel = computed(() => selectedOption.value?.label || displaySourceName(demoState.material.sourceName));
const statsStatus = computed(() => `${sourceOptions.value.length} 个历史可切换`);
const selectedWarnings = computed(() => selectedOption.value ? warningsForSource(selectedOption.value.inputVideo || selectedOption.value.label) : []);
const timeBuckets = computed(() => buildTimeBuckets(currentPredictionWindows.value, selectedWarnings.value));
const heatSegments = computed(() => timeBuckets.value);
const displayStats = computed(() => buildDisplayStats());
const spatialHotspots = computed(() => normalizeSpatialHotspots(aggregateSpatialPoints(currentBehaviorHeatmap.value, true)));
const currentHeatmapAlerts = computed(() => buildCurrentHeatmapAlerts(currentBehaviorHeatmap.value));
const spatialLegend = computed(() => {
	const keys = Array.from(new Set(spatialHotspots.value.map((item) => item.behaviorType)));
	return keys.map((key) => ({ key, label: behaviorText(key) }));
});
const spatialMapStyle = computed(() => ({ aspectRatio: selectedVideoAspectRatio.value }));

function recordSource(row: any) {
	return row?.inputVideo || row?.sourceName || row?.fileName || '';
}

function inferDatasetValue(source: any, row: any = {}) {
	const raw = String(source || row.inputVideo || row.sourceName || row.fileName || '').replace(/\\/g, '/');
	if (row.preprocessedDataset) return String(row.preprocessedDataset);
	const pathMatch = raw.match(/\/class\/(?:input|output)\/([^/]+)/i) || raw.match(/\/(?:input|output)\/([^/]+)/i);
	if (pathMatch?.[1]) return pathMatch[1];
	const name = displaySourceName(raw || row.label || '').trim();
	return name.replace(/\.[^.]+$/, '') || '';
}

function readVideoPageState() {
	try {
		const raw = sessionStorage.getItem(videoPageStorageKey);
		const state = raw ? JSON.parse(raw) : null;
		return state && typeof state === 'object' ? state : null;
	} catch (error) {
		return null;
	}
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
	if (currentPredictionWindows.value.length || currentBehaviorHeatmap.value.length) {
		demoState.material.sourceName = option.label;
	} else if (warningsForSource(source).length || !hasCurrentLiveStats(source)) {
		syncWarningRecords(warningRecords.value, source);
	} else {
		demoState.material.sourceName = option.label;
	}
	refreshCharts();
}

async function loadPredictionWindowsForSelected(option: HistoryOption) {
	currentPredictionWindows.value = [];
	currentBehaviorHeatmap.value = [];
	selectedVideoDurationSeconds.value = option.isCurrent ? parseClockSeconds(demoState.material.duration) : 0;
	selectedVideoAspectRatio.value = aspectRatioFromResolution(demoState.material.resolution) || '16 / 9';
	currentSpatialVideoUrl.value = option.inputVideoUrl || option.resultVideoUrl || preprocessedResultVideoUrl(option.datasetValue);
	try {
		const raw = sessionStorage.getItem(videoPageStorageKey);
		const state = raw ? JSON.parse(raw) : null;
		if (state && stateMatchesOption(state, option)) {
			if (Array.isArray(state.predictionWindows)) currentPredictionWindows.value = state.predictionWindows;
			if (Array.isArray(state.behaviorHeatmap)) currentBehaviorHeatmap.value = state.behaviorHeatmap;
			if (Number(state.videoDurationSeconds) > 0) selectedVideoDurationSeconds.value = Number(state.videoDurationSeconds);
			if (state.inputVideoUrl) currentSpatialVideoUrl.value = state.inputVideoUrl;
			else if (state.currentTaskId) currentSpatialVideoUrl.value = `/flask/videoTasks/${state.currentTaskId}/input-video`;
			else if (state.resultVideoUrl && !currentSpatialVideoUrl.value) currentSpatialVideoUrl.value = state.resultVideoUrl;
			applyVideoInfoForHeatmap(state.videoInfo);
			if (!currentPredictionWindows.value.length && state.currentTaskId) {
				const res = await request.get(`/flask/videoTasks/${state.currentTaskId}`);
				if (res?.code === 0 && res.data) {
					if (Array.isArray(res.data.predictionWindows)) currentPredictionWindows.value = res.data.predictionWindows;
					if (Array.isArray(res.data.behaviorHeatmap)) currentBehaviorHeatmap.value = res.data.behaviorHeatmap;
					if (Number(res.data.videoInfo?.durationSeconds) > 0) selectedVideoDurationSeconds.value = Number(res.data.videoInfo.durationSeconds);
					if (res.data.inputVideoUrl) currentSpatialVideoUrl.value = res.data.inputVideoUrl;
					else if (res.data.resultVideoUrl && !currentSpatialVideoUrl.value) currentSpatialVideoUrl.value = res.data.resultVideoUrl;
					applyVideoInfoForHeatmap(res.data.videoInfo);
				}
			}
		}
	} catch (error) {
		currentPredictionWindows.value = [];
		currentBehaviorHeatmap.value = [];
	}
	if ((!currentPredictionWindows.value.length || !currentBehaviorHeatmap.value.length || !hasTimedHeatmap(currentBehaviorHeatmap.value)) && option.datasetValue) {
		try {
			const res = await request.get(`/flask/class-preprocessed/${encodeURIComponent(option.datasetValue)}/predictions`);
			const data = res?.code === 0 ? res.data : null;
			if (Array.isArray(data?.predictionWindows)) currentPredictionWindows.value = data.predictionWindows;
			if (Array.isArray(data?.behaviorHeatmap)) currentBehaviorHeatmap.value = data.behaviorHeatmap;
			if (Number(data?.videoInfo?.durationSeconds) > 0) selectedVideoDurationSeconds.value = Number(data.videoInfo.durationSeconds);
			if (data?.inputVideoUrl) currentSpatialVideoUrl.value = data.inputVideoUrl;
			else if (!currentSpatialVideoUrl.value) currentSpatialVideoUrl.value = preprocessedInputVideoUrl(option.datasetValue) || preprocessedResultVideoUrl(option.datasetValue);
			applyVideoInfoForHeatmap(data?.videoInfo);
		} catch (error) {
			// The Flask service may need a restart to expose the new detail endpoint.
		}
	}
	await resetSpatialVideoFrame();
}

function stateMatchesOption(state: any, option: HistoryOption) {
	const stateDataset = String(state?.preprocessedDataset || '');
	const optionSource = option.inputVideo || option.label;
	return sourceMatches(state?.sourceName || '', optionSource)
		|| Boolean(stateDataset && option.datasetValue && stateDataset === option.datasetValue)
		|| Boolean(stateDataset && sourceNameKey(`${stateDataset}.mp4`) === sourceNameKey(optionSource));
}

function hasTimedHeatmap(points: SpatialPoint[]) {
	return points.some((item) => Number.isFinite(Number(item.startSecond ?? item.timeSecond)));
}

function preprocessedResultVideoUrl(dataset = '') {
	return dataset ? `/flask/class-preprocessed/${encodeURIComponent(dataset)}/result-video` : '';
}

function preprocessedInputVideoUrl(dataset = '') {
	return dataset ? `/flask/class-preprocessed/${encodeURIComponent(dataset)}/input-video` : '';
}

function applyVideoInfoForHeatmap(videoInfo: any = {}) {
	const ratio = aspectRatioFromVideoInfo(videoInfo);
	if (ratio) selectedVideoAspectRatio.value = ratio;
	if (Number(videoInfo?.durationSeconds) > 0) selectedVideoDurationSeconds.value = Number(videoInfo.durationSeconds);
}

function aspectRatioFromVideoInfo(videoInfo: any = {}) {
	const width = Number(videoInfo?.width || 0);
	const height = Number(videoInfo?.height || 0);
	if (width > 0 && height > 0) return `${width} / ${height}`;
	return aspectRatioFromResolution(videoInfo?.resolution || '');
}

function aspectRatioFromResolution(text = '') {
	const match = String(text || '').match(/(\d+(?:\.\d+)?)\D+(\d+(?:\.\d+)?)/);
	if (!match) return '';
	const width = Number(match[1]);
	const height = Number(match[2]);
	return width > 0 && height > 0 ? `${width} / ${height}` : '';
}

async function resetSpatialVideoFrame() {
	await nextTick();
	const video = spatialVideoRef.value;
	if (!video) return;
	try {
		if ((video.currentTime || 0) > 0.2) video.currentTime = 0;
		video.pause();
	} catch (error) {
		// Some browsers reject seeking before metadata is ready; loadedmetadata will retry.
	}
}

function buildDisplayStats() {
	const stats = chartStatsWithCount();
	if (!stats.length) return demoState.stats;
	const total = stats.reduce((sum, item) => sum + item.value, 0) || 1;
	return stats.map((item) => ({
		key: item.key,
		label: item.label,
		duration: formatDurationDisplay(item.value),
		ratio: `${(item.value / total * 100).toFixed(1)}%`,
		count: item.count,
		confidence: '-',
		tone: behaviorTone(item.key),
		value: item.value,
	}));
}

function chartStats() {
	return chartStatsWithCount().map(({ key, label, value }) => ({ key, label, value }));
}

function chartStatsWithCount(): ChartStat[] {
	const fromWindows = windowBehaviorStats(currentPredictionWindows.value);
	if (fromWindows.length) return fromWindows;
	const fromBuckets = aggregateBuckets(timeBuckets.value);
	if (fromBuckets.length) return fromBuckets;
	return demoState.stats
		.map((item) => {
			const value = Number(item.value ?? parseDurationSeconds(item.duration));
			return {
				key: item.key,
				label: item.label || behaviorText(item.key),
				value: Number.isFinite(value) ? value : 0,
				count: Number(item.count || 0),
			};
		})
		.filter((item) => item.value > 0 && !['pending', 'empty', 'failed'].includes(item.key));
}

function windowBehaviorStats(windows: any[]): ChartStat[] {
	const grouped = new Map<string, { behaviorType: string; intervals: Array<[number, number]> }>();
	(windows || []).forEach((item) => {
		const behaviorType = normalizeBehavior(item.behaviorType || item.behaviorName || item.rawLabel || 'none');
		if (!behaviorType || behaviorType === 'none') return;
		const start = Math.max(0, Number(item.startSecond || 0));
		let end = Number(item.endSecond || 0);
		if (end <= start) end = start + Number(item.durationSeconds || 0);
		if (end <= start) return;
		const trackId = item.trackId ?? item.track_id ?? 'track';
		const groupKey = `${trackId}::${behaviorType}`;
		if (!grouped.has(groupKey)) grouped.set(groupKey, { behaviorType, intervals: [] });
		grouped.get(groupKey)!.intervals.push([start, end]);
	});

	const totals = new Map<string, { value: number; count: number }>();
	grouped.forEach((item) => {
		const merged = mergeIntervals(item.intervals);
		const duration = merged.reduce((sum, [start, end]) => sum + Math.max(0, end - start), 0);
		const current = totals.get(item.behaviorType) || { value: 0, count: 0 };
		current.value += duration;
		current.count += merged.length;
		totals.set(item.behaviorType, current);
	});

	return Array.from(totals.entries())
		.filter(([, item]) => item.value > 0)
		.map(([key, item]) => ({ key, label: behaviorText(key), value: item.value, count: item.count }))
		.sort((a, b) => b.value - a.value);
}

function mergeIntervals(intervals: Array<[number, number]>) {
	const merged: Array<[number, number]> = [];
	intervals
		.slice()
		.sort((a, b) => a[0] - b[0])
		.forEach(([start, end]) => {
			if (!merged.length || start > merged[merged.length - 1][1]) {
				merged.push([start, end]);
			} else {
				merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], end);
			}
		});
	return merged;
}

function aggregateBuckets(buckets: TimeBucket[]): ChartStat[] {
	const totals = new Map<string, number>();
	buckets.forEach((bucket) => {
		Object.entries(bucket.data).forEach(([key, value]) => {
			totals.set(key, (totals.get(key) || 0) + Number(value || 0));
		});
	});
	return Array.from(totals.entries())
		.filter(([, value]) => value > 0)
		.map(([key, value]) => ({ key, label: behaviorText(key), value, count: buckets.filter((bucket) => Number(bucket.data[key] || 0) > 0).length }));
}

function buildTimeBuckets(windows: any[], warnings: any[]): TimeBucket[] {
	if (Array.isArray(windows) && windows.length) return buildPredictionTimeBuckets(windows);
	const duration = inferVideoDuration(windows, warnings);
	const bucketSize = duration / bucketCount;
	const buckets = Array.from({ length: bucketCount }, (_, index) => createBucket(index, bucketSize));
	const placedWarnings = placeWarningsOnTimeline(warnings, duration);
	placedWarnings.forEach((item) => addWindowToBuckets(buckets, item, bucketSize));
	return buckets.map(finalizeBucket);
}

function buildPredictionTimeBuckets(windows: any[]): TimeBucket[] {
	const normalized = normalizeTimelineWindows(windows);
	const duration = inferVideoDuration(windows, []);
	if (!normalized.length) {
		const bucket = createBucket(0, Math.max(duration, 1));
		return [finalizeBucket(bucket)];
	}
	const step = inferTimelineStep(normalized, duration);
	const buckets: TimeBucket[] = [];
	for (let start = 0; start < duration; start += step) {
		const end = Math.min(duration, start + step);
		buckets.push({
			time: `${formatClockShort(start)}-${formatClockShort(end)}`,
			start,
			end,
			level: 'normal',
			score: 0,
			total: 0,
			behaviorName: '无事件',
			data: {},
		});
	}
	normalized.forEach((item) => addWindowToBuckets(buckets, item, step));
	return mergeAdjacentBuckets(buckets.map(finalizeBucket));
}

function normalizeTimelineWindows(windows: any[]) {
	return (windows || [])
		.map((item) => {
			const start = Math.max(0, Number(item.startSecond || 0));
			let end = Number(item.endSecond || 0);
			if (end <= start) end = start + Number(item.durationSeconds || 0);
			return {
				behaviorType: normalizeBehavior(item.behaviorType || item.behaviorName || item.rawLabel || 'none'),
				riskLevel: behaviorRiskLevel(item.behaviorType || item.behaviorName || item.rawLabel),
				start,
				end,
			};
		})
		.filter((item) => item.end > item.start && item.behaviorType && item.behaviorType !== 'none');
}

function inferTimelineStep(windows: Array<{ start: number; end: number }>, duration: number) {
	const starts = Array.from(new Set(windows.map((item) => Number(item.start.toFixed(2))))).sort((a, b) => a - b);
	const gaps = starts.slice(1).map((value, index) => value - starts[index]).filter((value) => value > 0.05).sort((a, b) => a - b);
	const medianGap = gaps.length ? gaps[Math.floor(gaps.length / 2)] : 1;
	return Math.max(0.5, Math.min(5, medianGap || Math.max(1, duration / 60)));
}

function mergeAdjacentBuckets(buckets: TimeBucket[]) {
	const merged: TimeBucket[] = [];
	buckets.forEach((bucket) => {
		const last = merged[merged.length - 1];
		if (last && last.behaviorName === bucket.behaviorName && last.level === bucket.level) {
			last.end = bucket.end;
			last.time = `${formatClockShort(last.start)}-${formatClockShort(last.end)}`;
			last.total += bucket.total;
			last.score += bucket.score;
			Object.entries(bucket.data).forEach(([key, value]) => {
				last.data[key] = (last.data[key] || 0) + value;
			});
			return;
		}
		merged.push({ ...bucket, data: { ...bucket.data } });
	});
	return merged;
}

function createBucket(index: number, bucketSize: number): TimeBucket {
	const start = index * bucketSize;
	const end = (index + 1) * bucketSize;
	return {
		time: `${formatClockShort(start)}-${formatClockShort(end)}`,
		start,
		end,
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
		const bucketStart = Number.isFinite(bucket.start) ? bucket.start : index * bucketSize;
		const bucketEnd = Number.isFinite(bucket.end) ? bucket.end : (index + 1) * bucketSize;
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
	const warningMax = Math.max(0, ...warnings.map((item) => Number(item.durationSeconds || 0) || parseDurationSeconds(item.durationText || '')));
	const currentFallback = selectedOption.value?.isCurrent ? parseClockSeconds(demoState.material.duration) : 0;
	return Math.max(60, warningMax || currentFallback || 60);
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

function formatDurationDisplay(seconds: number) {
	const safe = Math.max(0, Math.round(seconds || 0));
	if (safe >= 60) return `${Math.floor(safe / 60)}分${String(safe % 60).padStart(2, '0')}秒`;
	return `${safe}秒`;
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

function behaviorTone(key: string) {
	const risk = behaviorRiskLevel(key);
	if (risk === 'high') return 'danger';
	if (risk === 'medium') return key === 'phone' ? 'purple' : 'warm';
	if (key === 'focus') return 'green';
	if (key === 'other_action') return 'purple';
	return 'amber';
}

function aggregateSpatialPoints(points: SpatialPoint[], cumulative: boolean) {
	const cellSize = cumulative ? 0.028 : 0.018;
	const grouped = new Map<string, SpatialPoint>();
	points.forEach((item) => {
		const x = Math.min(1, Math.max(0, Number(item.x || 0)));
		const y = Math.min(1, Math.max(0, Number(item.y || 0)));
		const behaviorType = normalizeBehavior(item.behaviorType || item.behaviorName || 'other_action');
		const key = `${item.trackId || 'unknown'}-${behaviorType}-${Math.round(x / cellSize)}-${Math.round(y / cellSize)}`;
		const prev = grouped.get(key);
		const value = Number(item.value || 0);
		if (!prev) {
			grouped.set(key, { ...item, x, y, behaviorType, value });
			return;
		}
		const total = Number(prev.value || 0) + value;
		prev.x = total ? (Number(prev.x || 0) * Number(prev.value || 0) + x * value) / total : x;
		prev.y = total ? (Number(prev.y || 0) * Number(prev.value || 0) + y * value) / total : y;
		prev.value = total;
		prev.startSecond = Math.min(Number(prev.startSecond ?? item.startSecond ?? 0), Number(item.startSecond ?? prev.startSecond ?? 0));
		prev.endSecond = Math.max(Number(prev.endSecond ?? item.endSecond ?? 0), Number(item.endSecond ?? prev.endSecond ?? 0));
	});
	return Array.from(grouped.values());
}

function normalizeSpatialHotspots(points: SpatialPoint[]) {
	const maxValue = Math.max(1, ...points.map((item) => Number(item.value || 0)));
	return points
		.filter((item) => Number.isFinite(Number(item.x)) && Number.isFinite(Number(item.y)) && Number(item.value || 0) > 0)
		.sort((a, b) => Number(b.value || 0) - Number(a.value || 0))
		.slice(0, 180)
		.map((item) => ({
			...item,
			behaviorType: normalizeBehavior(item.behaviorType || item.behaviorName || 'other_action'),
			x: Math.min(1, Math.max(0, Number(item.x || 0))),
			y: Math.min(1, Math.max(0, Number(item.y || 0))),
			intensity: Math.sqrt(Number(item.value || 0) / maxValue),
		}));
}

function hotspotStyle(item: SpatialPoint & { intensity?: number }) {
	const intensity = Math.max(0.12, Number(item.intensity || 0));
	const key = normalizeBehavior(item.behaviorType || '');
	const base = key === 'lie_desk' || key === 'sleep' ? 22 : 14;
	const range = key === 'lie_desk' || key === 'sleep' ? 46 : 32;
	const size = Math.round(base + intensity * range);
	const alpha = Math.min(0.52, 0.16 + intensity * 0.34);
	return {
		left: `${Math.min(98, Math.max(2, item.x * 100))}%`,
		top: `${Math.min(96, Math.max(4, item.y * 100))}%`,
		width: `${size}px`,
		height: `${size}px`,
		marginLeft: `${-size / 2}px`,
		marginTop: `${-size / 2}px`,
		opacity: String(alpha),
	};
}

function buildCurrentHeatmapAlerts(points: Array<SpatialPoint & { intensity?: number }>) {
	const grouped = new Map<string, any>();
	points
		.filter((item) => ['medium', 'high'].includes(behaviorRiskLevel(item.behaviorType)))
		.forEach((item) => {
			const key = `${item.trackId || 'unknown'}-${normalizeBehavior(item.behaviorType)}`;
			const value = Number(item.value || 0);
			const start = Number(item.startSecond ?? item.timeSecond ?? 0);
			let end = Number(item.endSecond ?? item.timeSecond ?? item.startSecond ?? 0);
			if (end <= start) end = start + 1;
			const prev = grouped.get(key);
			if (!prev) {
				grouped.set(key, {
					key,
					trackId: item.trackId || '未知',
					label: behaviorText(item.behaviorType),
					risk: behaviorRiskLevel(item.behaviorType),
					riskText: riskText(behaviorRiskLevel(item.behaviorType)),
					value,
					x: Number(item.x || 0),
					y: Number(item.y || 0),
					weight: value,
					start,
					end,
					intervals: [[start, end]],
				});
				return;
			}
			const totalWeight = Number(prev.weight || 0) + value;
			prev.x = totalWeight ? (Number(prev.x || 0) * Number(prev.weight || 0) + Number(item.x || 0) * value) / totalWeight : Number(item.x || 0);
			prev.y = totalWeight ? (Number(prev.y || 0) * Number(prev.weight || 0) + Number(item.y || 0) * value) / totalWeight : Number(item.y || 0);
			prev.weight = totalWeight;
			prev.value += value;
			prev.start = Math.min(prev.start, start);
			prev.end = Math.max(prev.end, end);
			prev.intervals.push([start, end]);
		});
	return Array.from(grouped.values())
		.map((item) => ({ ...item, seconds: mergeIntervalSeconds(item.intervals) }))
		.sort((a, b) => riskWeight(b.risk) - riskWeight(a.risk) || b.seconds - a.seconds || b.value - a.value)
		.slice(0, 5);
}

function mergeIntervalSeconds(intervals: number[][] = []) {
	const sorted = intervals
		.map(([start, end]) => [Math.max(0, Number(start || 0)), Math.max(0, Number(end || start || 0))])
		.filter(([start, end]) => end > start)
		.sort((a, b) => a[0] - b[0]);
	let total = 0;
	let current: number[] | null = null;
	sorted.forEach(([start, end]) => {
		if (!current || start > current[1]) {
			if (current) total += current[1] - current[0];
			current = [start, end];
		} else {
			current[1] = Math.max(current[1], end);
		}
	});
	if (current) total += current[1] - current[0];
	return Math.max(1, Math.round(total));
}

function alertBadgeStyle(item: { x: number; y: number; risk: string }, index = 0) {
	const offsets = [
		{ x: 0, y: -8 },
		{ x: -7, y: -7 },
		{ x: 7, y: -7 },
		{ x: -8, y: 5 },
		{ x: 8, y: 5 },
	];
	const offset = offsets[index % offsets.length];
	return {
		left: `${Math.min(92, Math.max(8, Number(item.x || 0) * 100 + offset.x))}%`,
		top: `${Math.min(88, Math.max(8, Number(item.y || 0) * 100 + offset.y))}%`,
		'--alert-color': item.risk === 'high' ? '#dc2626' : '#2563eb',
	};
}

function alertTooltip(item: { trackId: any; label: string; seconds: number }) {
	return `ID ${item.trackId} · ${item.label} · ${formatDurationDisplay(item.seconds)}`;
}

function markerStyle(item: { x: number; y: number }) {
	return {
		left: `${Math.min(98, Math.max(2, Number(item.x || 0) * 100))}%`,
		top: `${Math.min(96, Math.max(4, Number(item.y || 0) * 100))}%`,
	};
}

function heatmapTooltip(item: SpatialPoint) {
	const label = behaviorText(item.behaviorType);
	const track = item.trackId ? `ID ${item.trackId} · ` : '';
	const start = formatClockShort(Number(item.startSecond ?? item.timeSecond ?? 0));
	const end = formatClockShort(Number(item.endSecond ?? item.timeSecond ?? item.startSecond ?? 0));
	return `${track}${label} · ${start}-${end}`;
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
		xAxis: { type: 'category', data: buckets.map((item) => item.time), axisLabel: { interval: 'auto', rotate: 22 } },
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
		if (!videoRecords.value.length) {
			warningRecords.value = [];
			currentPredictionWindows.value = [];
			currentBehaviorHeatmap.value = [];
			currentSpatialVideoUrl.value = '';
			selectedSource.value = '';
			sessionStorage.removeItem(videoPageStorageKey);
			clearDemoDetectionState();
			refreshCharts();
			return;
		}
		warningRecords.value = filterWarningRecordsByHistories(warningRecords.value, videoRecords.value);
		if (!warningRecords.value.length) {
			clearDemoDetectionState();
		}
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
		currentBehaviorHeatmap.value.length,
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
	margin-top: 0;
}

.pie-chart {
	height: 330px;
}

.spatial-panel > .section-title {
	display: none;
}

.spatial-title {
	margin-bottom: 14px;
}

.spatial-title h3 {
	margin: 0 0 6px;
	font-size: 18px;
}

.spatial-title p {
	margin: 0;
	color: #6b7b80;
	line-height: 1.6;
}

.spatial-body {
	display: grid;
	grid-template-columns: minmax(0, 1fr) 210px;
	gap: 12px;
	align-items: stretch;
}

.spatial-map {
	position: relative;
	min-height: 360px;
	max-height: 520px;
	overflow: hidden;
	border-radius: 8px;
	border: 1px solid #d1dde2;
	background: #101b20;
	box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .04);
}

.spatial-video,
.video-shade {
	position: absolute;
	inset: 0;
	width: 100%;
	height: 100%;
}

.spatial-video {
	object-fit: contain;
	background: #111d21;
	filter: saturate(.88) contrast(.92) brightness(.72);
}

.video-shade {
	background:
		linear-gradient(90deg, rgba(255, 255, 255, .05) 1px, transparent 1px),
		linear-gradient(0deg, rgba(255, 255, 255, .05) 1px, transparent 1px),
		radial-gradient(circle at center, transparent 52%, rgba(8, 18, 22, .32));
	background-size: 8.333% 100%, 100% 14.285%, 100% 100%;
	pointer-events: none;
	z-index: 1;
}

.map-grid {
	position: absolute;
	inset: 0;
	border: 1px solid rgba(255, 255, 255, .14);
	border-radius: 8px;
	pointer-events: none;
	z-index: 2;
}

.alert-badge {
	position: absolute;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	min-width: 58px;
	padding: 6px 8px 7px;
	gap: 1px;
	border-radius: 8px;
	border: 1px solid rgba(255, 255, 255, .7);
	background: color-mix(in srgb, var(--alert-color, #2563eb) 76%, transparent);
	color: #fff;
	font-size: 12px;
	font-weight: 800;
	text-align: center;
	text-shadow: 0 1px 2px rgba(0, 0, 0, .34);
	box-shadow: 0 0 0 1px rgba(8, 18, 22, .16), 0 10px 24px rgba(0, 0, 0, .16);
	transform: translate(-50%, -100%);
	z-index: 4;
	pointer-events: auto;
}

.alert-badge::after {
	content: '';
	position: absolute;
	left: 50%;
	bottom: -6px;
	width: 10px;
	height: 10px;
	background: var(--alert-color, #2563eb);
	border-right: 1px solid rgba(255, 255, 255, .65);
	border-bottom: 1px solid rgba(255, 255, 255, .65);
	transform: translateX(-50%) rotate(45deg);
}

.alert-badge.risk-high {
	box-shadow: 0 0 0 1px rgba(127, 29, 29, .28), 0 0 20px rgba(220, 38, 38, .28);
}

.alert-badge__id,
.alert-badge em {
	font-size: 10px;
	font-style: normal;
	font-weight: 700;
	opacity: .92;
}

.alert-badge strong {
	font-size: 18px;
	line-height: 1.1;
	letter-spacing: 0;
}

.hotspot {
	position: absolute;
	display: grid;
	place-items: center;
	border-radius: 50%;
	color: #fff;
	font-size: 0;
	font-weight: 700;
	transform: translateZ(0);
	background:
		radial-gradient(circle, rgba(244, 63, 94, .78) 0 16%, rgba(251, 146, 60, .5) 36%, rgba(250, 204, 21, .28) 54%, rgba(14, 165, 233, .16) 78%, rgba(14, 165, 233, 0) 100%);
	filter: blur(1px) saturate(1.08);
	mix-blend-mode: screen;
	z-index: 3;
	pointer-events: auto;
}

.hotspot.risk-medium {
	background:
		radial-gradient(circle, rgba(251, 191, 36, .72) 0 17%, rgba(250, 204, 21, .36) 47%, rgba(34, 211, 238, .14) 76%, rgba(34, 211, 238, 0) 100%);
}

.hotspot.risk-low {
	background:
		radial-gradient(circle, rgba(34, 197, 94, .45) 0 18%, rgba(45, 212, 191, .2) 52%, rgba(59, 130, 246, 0) 100%);
}

.hotspot.behavior-lie_desk,
.hotspot.behavior-sleep {
	background:
		radial-gradient(circle, rgba(126, 34, 206, .7) 0 16%, rgba(168, 85, 247, .42) 40%, rgba(59, 130, 246, .18) 72%, rgba(59, 130, 246, 0) 100%);
}

.hotspot span {
	display: none;
}

.hotspot:hover {
	z-index: 3;
	opacity: .72 !important;
	mix-blend-mode: normal;
	filter: blur(0) saturate(1.1);
}

.student-marker {
	display: none !important;
	position: absolute;
	width: 46px;
	height: 38px;
	margin: -19px 0 0 -23px;
	border: 2px dashed rgba(251, 191, 36, .9);
	border-radius: 8px;
	z-index: 4;
	pointer-events: none;
}

.student-marker.risk-high {
	border-color: rgba(239, 68, 68, .95);
	box-shadow: 0 0 0 1px rgba(239, 68, 68, .28), 0 0 18px rgba(239, 68, 68, .2);
}

.student-marker span {
	position: absolute;
	top: -12px;
	right: -10px;
	display: grid;
	place-items: center;
	width: 20px;
	height: 20px;
	border-radius: 999px;
	background: #ef4444;
	color: #fff;
	font-size: 12px;
	font-weight: 800;
}

.map-empty {
	position: absolute;
	inset: 0;
	display: grid;
	place-items: center;
	color: #789095;
	font-weight: 700;
	z-index: 4;
}

.heatmap-alerts {
	min-height: 100%;
	padding: 12px;
	border: 1px solid #dbe8e5;
	border-radius: 8px;
	background: #fbfefd;
	overflow: hidden;
}

.alerts-head {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 10px;
}

.alerts-head strong {
	font-size: 15px;
	color: #18353a;
}

.alerts-head span,
.alert-empty {
	color: #789095;
	font-size: 12px;
}

.alert-item {
	width: 100%;
	margin: 0 0 8px;
	padding: 10px;
	border: 1px solid #f2dfbd;
	border-radius: 8px;
	background: #fffaf0;
	text-align: left;
}

.alert-item.risk-high {
	border-color: #f3c4bd;
	background: #fff4f2;
}

.alert-id,
.alert-item em {
	display: block;
	color: #667b80;
	font-size: 12px;
	font-style: normal;
}

.alert-item strong {
	display: block;
	margin: 4px 0;
	color: #15363b;
}

.spatial-legend {
	display: flex;
	flex-wrap: wrap;
	gap: 12px 18px;
	margin-top: 12px;
	color: #53686d;
}

.spatial-legend span {
	display: inline-flex;
	align-items: center;
	gap: 6px;
}

.spatial-legend i {
	width: 10px;
	height: 10px;
	border-radius: 50%;
}

.legend-normal { background: #22c55e; }
.legend-medium { background: #facc15; }
.legend-high { background: #ef4444; }
.legend-cumulative { background: #7e22ce; }

.heat-panel {
	margin-top: 16px;
}

.heat-row {
	display: flex;
	gap: 8px;
	overflow-x: auto;
	padding-bottom: 4px;
	scrollbar-width: thin;
}

.heat-segment {
	flex: 0 0 124px;
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

	.spatial-body {
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
