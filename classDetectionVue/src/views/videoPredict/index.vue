<template>
	<DemoShell active="video" title="录制视频检测" :status="demoState.material.status" :status-type="statusType">
		<template #actions>
			<el-button @click="chooseVideo">
				<el-icon><FolderOpened /></el-icon>
				视频素材
			</el-button>
			<el-button @click="router.push('/detectionHistory')">
				<el-icon><Tickets /></el-icon>
				检测历史
			</el-button>
			<el-button @click="router.push({ path: '/behaviorStats', query: { source: demoState.material.sourceName } })">
				<el-icon><PieChart /></el-icon>
				行为统计
			</el-button>
			<el-button @click="router.push('/interventionReport')">
				<el-icon><Document /></el-icon>
				检测报告
			</el-button>
			<el-button @click="router.push('/demoSettings')">
				<el-icon><Setting /></el-icon>
				系统设置
			</el-button>
		</template>

		<div class="video-workspace">
			<div class="left-scroll">
				<section class="panel video-panel">
					<div class="video-head">
						<div>
							<h3>视频素材：<span>{{ demoState.material.sourceName }}</span></h3>
							<p>分辨率：{{ demoState.material.resolution }}　　时长：{{ demoState.material.duration }}　　帧率：{{ demoState.material.fps }}</p>
						</div>
					</div>

					<div class="model-row">
						<el-select v-model="kind" placeholder="检测类别" style="width: 190px" @change="loadWeights">
							<el-option v-for="item in kindItems" :key="item.value" :label="item.label" :value="item.value" />
						</el-select>
						<el-select v-model="weight" placeholder="检测模型" style="width: 190px">
							<el-option v-for="item in weightItems" :key="item.value" :label="item.label" :value="item.value" />
						</el-select>
						<el-select v-model="preprocessedDataset" placeholder="预处理素材" style="width: 220px" @change="handlePreprocessedDatasetChange">
							<el-option v-for="item in preprocessedItems" :key="item.value" :label="item.label" :value="item.value" />
						</el-select>
					</div>

					<div class="demo-start-panel">
						<div>
							<strong>演示流程</strong>
							<span>刷新后默认停在“待开始检测”，点击开始检测后再生成处理后标注视频。</span>
						</div>
						<div class="video-actions">
							<el-upload
								ref="uploadRef"
								action="http://localhost:9999/files/upload"
								:show-file-list="false"
								:on-change="handleVideoChange"
								:on-progress="handleVideoUploadProgress"
								:on-success="handleVideoSuccess"
							>
								<el-button>更换视频</el-button>
							</el-upload>
							<el-button type="primary" @click="startDetect">开始检测</el-button>
						</div>
					</div>

					<div class="result-video-layout">
						<div class="result-video-copy">
							<span>比赛展示视频</span>
							<strong>处理后标注结果</strong>
							<p>展示录制课堂视频经过算法识别后的异常行为框、行为标签和风险事件。</p>
						</div>
						<div class="video-frame result-frame">
							<video
								v-if="resultVideoUrl"
								ref="resultVideoRef"
								class="video-content"
								:src="resultVideoUrl"
								controls
								preload="metadata"
								@loadedmetadata="handleVideoMetadata"
								@loadstart="handleVideoLoadStart('result')"
								@loadeddata="handleVideoReady('result')"
								@canplay="handleVideoReady('result')"
								@waiting="handleVideoWaiting('result')"
								@playing="handleVideoReady('result')"
								@error="handleVideoError('result')"
							></video>
							<div v-if="resultVideoUrl && resultVideoState.loading" class="video-loading">
								<el-icon class="is-loading"><Loading /></el-icon>
								<span>{{ resultVideoState.label }}</span>
							</div>
							<div v-if="resultVideoUrl && resultVideoState.error" class="video-error">
								<span>{{ resultVideoState.error }}</span>
								<el-button size="small" @click="reloadVideo('result')">重新加载</el-button>
							</div>
							<div v-if="!resultVideoUrl" class="classroom-placeholder">
								<div class="board"></div>
								<div v-for="student in placeholderStudents" :key="`r${student}`" class="student" :class="`s${student}`"></div>
								<div class="placeholder-copy">
									<strong>等待开始检测</strong>
									<span>已选择课堂录制素材，点击“开始检测”后展示标注结果</span>
								</div>
							</div>
							<div class="detect-chip">
								<el-icon><CircleCheckFilled /></el-icon>
								{{ demoState.material.status }}
							</div>
						</div>
					</div>
					<div v-if="uploadProgressVisible || processProgressVisible" class="progress-grid">
						<div v-if="uploadProgressVisible">
							<span>{{ uploadStatusText }}</span>
							<el-progress :percentage="uploadPercentage" :stroke-width="8" color="#008f87" />
						</div>
						<div v-if="processProgressVisible">
							<span>{{ processStatusText }}</span>
							<el-progress :percentage="demoState.material.progress" :stroke-width="8" color="#008f87" />
						</div>
					</div>
				</section>

				<section class="panel stats-panel">
					<div class="section-head">
						<h3>行为统计 <span>累计人次时长</span></h3>
					</div>
					<div class="stat-grid">
						<div v-for="item in demoState.stats" :key="item.key" class="stat-card" :class="item.tone">
							<span>{{ item.label }}</span>
							<strong>{{ item.duration }}</strong>
							<p>累计占比 {{ item.ratio }}　片段 {{ item.count }}段</p>
							<em>置信度 {{ item.confidence }}</em>
						</div>
					</div>
					<div class="chart-grid">
						<div class="chart-card">
							<h4>人次时长趋势</h4>
							<div id="videoTrendChart" class="chart"></div>
						</div>
						<div class="chart-card">
							<h4>累计行为占比</h4>
							<div id="videoPieChart" class="chart"></div>
						</div>
					</div>
				</section>
			</div>

			<aside class="ai-panel">
				<div class="ai-scroll">
					<div class="ai-title"><span>AI</span> 辅助干预</div>
					<section class="box model-box provider-overview">
						<h3>AI 模型</h3>
						<div class="provider-card">
							<strong>MiniMax</strong>
							<span>使用后端配置的 MinMax API-Key 生成建议和连续追问回复</span>
						</div>
					</section>
					<template v-if="demoState.hasLiveData">
					<section class="event-card">
						<div class="event-head">
							<h3>检测事件 {{ currentEvent.eventId }}</h3>
							<div>
								<el-button link size="small" @click="selectOffset(-1)">上一个</el-button>
								<el-button link size="small" @click="selectOffset(1)">下一个</el-button>
							</div>
						</div>
						<div class="event-alert" :class="currentEvent.riskLevel">
							<div class="alert-icon">
								<el-icon><Reading /></el-icon>
							</div>
							<div>
								<div class="risk-line">
									<strong>{{ behaviorText(currentEvent.behaviorType) }} {{ currentEvent.durationText }}</strong>
									<el-tag :type="riskTagType(currentEvent.riskLevel)">风险等级：{{ riskText(currentEvent.riskLevel) }}</el-tag>
								</div>
								<p>触发原因：{{ currentEvent.reason }}</p>
								<p>置信度：{{ currentEvent.confidence }}　状态：{{ currentEvent.status }}</p>
							</div>
						</div>
					</section>

					<section class="box">
						<div class="box-head">
							<h3>提示词构建预览</h3>
							<el-button link type="primary" @click="router.push('/aiIntervention')">查看详情</el-button>
						</div>
						<p>{{ currentEvent.promptPreview }}</p>
					</section>

					<section class="advice-box">
						<div class="box-head">
							<h3>生成沟通建议</h3>
							<el-button type="primary" size="small" @click="generateAdvice">重新生成</el-button>
						</div>
						<div class="advice-content">
							<el-icon><ChatDotRound /></el-icon>
							<p>{{ currentEvent.advice }}</p>
						</div>
					</section>

					<section class="box chat-box">
						<div class="box-head">
							<h3>连续追问</h3>
							<el-button link type="primary" @click="router.push('/aiIntervention')">完整对话</el-button>
						</div>
						<div class="chat-list">
							<div v-if="!aiChatMessages.length" class="chat-empty">可继续询问“怎么和学生开口”“要不要联系辅导员”等问题。</div>
							<div v-for="(message, index) in aiChatMessages" :key="index" class="chat-message" :class="message.role">
								{{ message.content }}
							</div>
						</div>
						<div class="chat-input-row">
							<el-input v-model="aiChatInput" size="small" placeholder="围绕当前事件继续提问" @keyup.enter="askAiFollowUp" />
							<el-button type="primary" size="small" :loading="aiChatLoading" @click="askAiFollowUp">发送</el-button>
						</div>
					</section>

					<el-button class="export-button" type="primary" @click="exportReport">
						<el-icon><DocumentChecked /></el-icon>
						导出干预报告
					</el-button>
					</template>
					<section v-else class="ai-empty-state">
						<div class="alert-icon">
							<el-icon><Reading /></el-icon>
						</div>
						<h3>等待检测结果</h3>
						<p>请先开始录制视频检测。AI 辅助干预将读取本次检测生成的风险事件、持续时长和触发原因，再生成教师沟通建议。</p>
					</section>
				</div>
			</aside>
		</div>
	</DemoShell>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import type { UploadInstance, UploadProps } from 'element-plus';
import { ChatDotRound, CircleCheckFilled, Document, DocumentChecked, FolderOpened, Loading, PieChart, Reading, Setting, Tickets } from '@element-plus/icons-vue';
import * as echarts from 'echarts';
import DemoShell from '/@/views/demo/components/DemoShell.vue';
import {
	applyAdvice,
	applyProtocolPayload,
	behaviorText,
	buildPrompt,
	currentEvent,
	demoState,
	exportReportText,
	fallbackAdvice,
	formatMinuteSecond,
	normalizeBehavior,
	parseDurationSeconds,
	riskTagType,
	riskText,
	setCurrentEvent,
	updateStatsFromLabels,
	upsertEvent,
} from '/@/views/demo/demoState';
import { normalizeAdviceResult } from '/@/utils/advice';
import request from '/@/utils/request';
import { SocketService } from '/@/utils/socket';
import { useUserInfo } from '/@/stores/userInfo';
import { storeToRefs } from 'pinia';
import { formatDate } from '/@/utils/formatTime';

const router = useRouter();
const stores = useUserInfo();
const { userInfos } = storeToRefs(stores);
const uploadRef = ref<UploadInstance>();
const conf = ref(demoState.settings.confidence);
const kind = ref('class');
const weight = ref(demoState.settings.model);
const kindItems = ref([{ value: 'class', label: '课堂学生行为检测' }]);
const weightItems = ref([{ value: 'yolo_best.pt', label: 'yolo_best.pt' }]);
const lstmWeight = ref('best_lstm.pth');
const preprocessedDataset = ref('sample');
const preprocessedItems = ref<any[]>([{ value: 'sample', label: 'sample', inputVideoUrl: '/flask/sample-video', sourceName: 'input.mp4' }]);
const previewUrl = ref('/flask/sample-video');
const resultVideoUrl = ref('');
const resultVideoRef = ref<HTMLVideoElement>();
const previewVideoState = ref({ loading: false, error: '', label: '正在加载原始视频' });
const resultVideoState = ref({ loading: false, error: '', label: '正在加载标注视频' });
const currentTaskId = ref('');
const streamUrl = ref('');
const uploadPercentage = ref(0);
const uploadStatusText = ref('等待上传');
const uploadProgressVisible = ref(false);
const processProgressVisible = ref(false);
const processStatusText = ref('检测处理中');
const placeholderStudents = Array.from({ length: 12 }, (_, index) => index + 1);
const socketService = new SocketService();
const trendChart = ref<any>(null);
const pieChart = ref<any>(null);
const latestPredictionWindows = ref<any[]>([]);
const latestBehaviorHeatmap = ref<any[]>([]);
const latestVideoDurationSeconds = ref(0);
const latestVideoInfo = ref<any>({});
type AiChatMessage = { role: 'user' | 'assistant'; content: string };
const aiChatInput = ref('');
const aiChatLoading = ref(false);
const aiChatMessages = ref<AiChatMessage[]>([]);
let generatedEventIndex = demoState.events.length + 1;
let taskPollTimer: ReturnType<typeof setInterval> | undefined;
const videoPageStorageKey = 'class-demo-video-predict-state';

const behaviorOrder = ['head_down', 'lie_desk', 'focus', 'other_action', 'phone', 'sleep'];
const behaviorChartColors: Record<string, string> = {
	head_down: '#f2a51a',
	lie_desk: '#ef4f45',
	focus: '#20aa82',
	other_action: '#5b6ee1',
	phone: '#8b5cf6',
	sleep: '#b45309',
};

function cleanVideoUrl(url: string) {
	return String(url || '').replace(/([?&])t=[^&]*&?/g, (match, prefix) => (prefix === '?' ? '?' : '')).replace(/[?&]$/, '');
}

function setPreviewVideoUrl(url: string, cacheKey?: string | number) {
	const next = withCache(url, cacheKey);
	if (previewUrl.value === next) return;
	if (previewUrl.value.startsWith('blob:')) URL.revokeObjectURL(previewUrl.value);
	previewVideoState.value = { loading: Boolean(next), error: '', label: '正在加载原始视频' };
	previewUrl.value = next;
	persistVideoPageState();
}

function setResultVideoUrl(url: string, cacheKey?: string | number) {
	const next = withCache(url, cacheKey);
	if (resultVideoUrl.value === next) return;
	resultVideoState.value = { loading: Boolean(next), error: '', label: '正在加载标注视频' };
	resultVideoUrl.value = next;
	persistVideoPageState();
}

function videoState(slot: 'preview' | 'result') {
	return slot === 'preview' ? previewVideoState.value : resultVideoState.value;
}

function handleVideoLoadStart(slot: 'preview' | 'result') {
	const state = videoState(slot);
	state.loading = true;
	state.error = '';
	state.label = slot === 'preview' ? '正在加载原始视频' : '正在加载标注视频';
}

function handleVideoWaiting(slot: 'preview' | 'result') {
	const state = videoState(slot);
	state.loading = true;
	state.label = '视频缓冲中';
}

function handleVideoReady(slot: 'preview' | 'result') {
	const state = videoState(slot);
	state.loading = false;
	state.error = '';
}

function handleVideoError(slot: 'preview' | 'result') {
	const state = videoState(slot);
	state.loading = false;
	state.error = slot === 'preview' ? '原始视频加载失败' : '标注视频加载失败';
}

function reloadVideo(slot: 'preview' | 'result') {
	const key = Date.now();
	if (slot === 'preview') {
		setPreviewVideoUrl(cleanVideoUrl(previewUrl.value), key);
	} else {
		setResultVideoUrl(cleanVideoUrl(resultVideoUrl.value), key);
		nextTick(() => resultVideoRef.value?.load());
	}
}

function persistVideoPageState() {
	try {
		sessionStorage.setItem(videoPageStorageKey, JSON.stringify({
			previewUrl: previewUrl.value,
			inputVideoUrl: previewUrl.value && !previewUrl.value.startsWith('blob:') ? previewUrl.value : '',
			currentTaskId: currentTaskId.value,
			resultVideoUrl: resultVideoUrl.value,
			preprocessedDataset: preprocessedDataset.value,
			sourceName: demoState.material.sourceName,
			status: demoState.material.status,
			progress: demoState.material.progress,
			confidence: conf.value,
			predictionWindows: latestPredictionWindows.value,
			behaviorHeatmap: latestBehaviorHeatmap.value,
			videoInfo: latestVideoInfo.value,
			videoDurationSeconds: latestVideoDurationSeconds.value,
		}));
	} catch (error) {
		// sessionStorage can be unavailable in restricted browser contexts.
	}
}

function restoreVideoPageState() {
	try {
		const raw = sessionStorage.getItem(videoPageStorageKey);
		if (!raw) return false;
		const state = JSON.parse(raw);
		if (!state || typeof state !== 'object') return false;
		if (state.preprocessedDataset) preprocessedDataset.value = state.preprocessedDataset;
		if (Number(state.confidence)) conf.value = Number(state.confidence);
		if (state.previewUrl) setPreviewVideoUrl(state.previewUrl);
		if (state.currentTaskId) currentTaskId.value = state.currentTaskId;
		if (state.sourceName) demoState.material.sourceName = state.sourceName;
		if (Array.isArray(state.predictionWindows)) latestPredictionWindows.value = state.predictionWindows;
		if (Array.isArray(state.behaviorHeatmap)) latestBehaviorHeatmap.value = state.behaviorHeatmap;
		if (Number(state.videoDurationSeconds) > 0) latestVideoDurationSeconds.value = Number(state.videoDurationSeconds);
		if (currentTaskId.value && Number(state.progress || 0) < 100) {
			if (state.status) demoState.material.status = state.status;
			if (typeof state.progress === 'number') demoState.material.progress = state.progress;
			startTaskPolling(currentTaskId.value);
		} else {
			currentTaskId.value = '';
			setResultVideoUrl('');
			demoState.material.status = '素材已选择';
			demoState.material.progress = 0;
			processProgressVisible.value = false;
		}
		persistVideoPageState();
		return Boolean(state.previewUrl || state.currentTaskId);
	} catch (error) {
		return false;
	}
}

const statusType = computed(() => {
	if (demoState.material.status.includes('完成')) return 'success';
	if (demoState.material.status.includes('检测')) return 'warning';
	return 'success';
});

function activePreprocessedItem() {
	return preprocessedItems.value.find((item) => item.value === preprocessedDataset.value);
}

function videoStem(name: string) {
	const baseName = String(name || '').split(/[\\/]/).pop() || '';
	return baseName.replace(/\.[^.]+$/, '').toLowerCase();
}

function findPreprocessedItemByVideoName(name: string) {
	const stem = videoStem(name);
	if (!stem) return undefined;
	return preprocessedItems.value.find((item) => {
		return String(item.value || '').toLowerCase() === stem || videoStem(item.sourceName || '') === stem;
	});
}

function applyPreprocessedItem(item: any, clearUpload = true) {
	if (!item) return;
	setPreviewVideoUrl(item.inputVideoUrl || '/flask/sample-video');
	setResultVideoUrl('');
	currentTaskId.value = '';
	streamUrl.value = '';
	if (clearUpload) {
		(uploadRef.value as any)?.clearFiles?.();
	}
	demoState.material.sourceName = item.sourceName || `${item.value}.mp4`;
	demoState.material.status = item.hasResultVideo ? '素材已选择，可开始检测' : '素材已选择';
	demoState.material.progress = 0;
	processProgressVisible.value = false;
	persistVideoPageState();
}

function handlePreprocessedDatasetChange() {
	const item = activePreprocessedItem();
	if (!item) return;
	applyPreprocessedItem(item, true);
}

function chooseVideo() {
	(uploadRef.value?.$el as HTMLElement | undefined)?.querySelector('input')?.click();
}

function handleVideoChange(file: any) {
	if (!file?.raw) return;
	const matchedItem = findPreprocessedItemByVideoName(file.name || file.raw?.name || '');
	if (matchedItem) {
		preprocessedDataset.value = matchedItem.value;
		(file as any).matchedPreprocessedDataset = matchedItem.value;
		applyPreprocessedItem(matchedItem, false);
		uploadProgressVisible.value = true;
		uploadStatusText.value = '已匹配本地预处理素材';
		return;
	}
	setPreviewVideoUrl(URL.createObjectURL(file.raw));
	streamUrl.value = '';
	setResultVideoUrl('');
	currentTaskId.value = '';
	uploadProgressVisible.value = true;
	uploadStatusText.value = file.status === 'success' ? '上传完成' : '准备上传';
	demoState.material.sourceName = file.name || demoState.material.sourceName;
	demoState.material.status = '素材已选择';
}

const handleVideoUploadProgress: UploadProps['onProgress'] = (event, file) => {
	const percent = Number(event?.percent ?? file?.percentage ?? 0);
	uploadPercentage.value = Math.min(100, Math.max(0, Math.round(percent)));
	uploadStatusText.value = uploadPercentage.value >= 100 ? '上传完成' : '视频上传中';
	uploadProgressVisible.value = true;
};

const handleVideoSuccess: UploadProps['onSuccess'] = (response, file) => {
	const matchedItem = findPreprocessedItemByVideoName(file.name || (file as any)?.raw?.name || '');
	if (matchedItem) {
		preprocessedDataset.value = matchedItem.value;
		(file as any).matchedPreprocessedDataset = matchedItem.value;
		applyPreprocessedItem(matchedItem, false);
	}
	demoState.material.sourceName = file.name || demoState.material.sourceName;
	demoState.material.status = '素材已上传';
	demoState.material.progress = 0;
	uploadPercentage.value = 100;
	uploadStatusText.value = '上传完成';
	uploadProgressVisible.value = true;
	const uploadedPath = response?.data || response?.url || response?.fileName || file.name;
	(file as any).uploadedPath = uploadedPath;
	ElMessage.success('视频素材上传成功');
};

function withCache(url: string, cacheKey?: string | number) {
	if (!url || url.startsWith('blob:')) return url;
	if (cacheKey === undefined || cacheKey === null || cacheKey === '') return url;
	const clean = cleanVideoUrl(url);
	const separator = clean.includes('?') ? '&' : '?';
	return `${clean}${separator}t=${encodeURIComponent(String(cacheKey))}`;
}

function applyVideoInfo(info: any) {
	if (!info) return;
	latestVideoInfo.value = { ...latestVideoInfo.value, ...info };
	if (info.resolution) demoState.material.resolution = info.resolution;
	if (info.duration) demoState.material.duration = info.duration;
	if (info.fps) demoState.material.fps = info.fps;
	if (Number(info.durationSeconds) > 0) latestVideoDurationSeconds.value = Number(info.durationSeconds);
	persistVideoPageState();
}

function formatClock(seconds: number) {
	const total = Math.max(0, Math.round(seconds || 0));
	const h = Math.floor(total / 3600);
	const m = Math.floor((total % 3600) / 60);
	const s = total % 60;
	return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function handleVideoMetadata(event: Event) {
	const video = event.target as HTMLVideoElement;
	if (!video || !Number.isFinite(video.duration)) return;
	demoState.material.duration = formatClock(video.duration);
	if (video.videoWidth && video.videoHeight) {
		demoState.material.resolution = `${video.videoWidth}×${video.videoHeight}`;
	}
}

function buildQueryParams() {
	const rawFile = (uploadRef.value as any)?.uploadFiles?.[0];
	const inputVideo = rawFile?.response?.data || rawFile?.uploadedPath || rawFile?.name || demoState.material.sourceName;
	const params = new URLSearchParams();
	params.set('username', userInfos.value.userName || 'demo');
	params.set('inputVideo', inputVideo);
	params.set('weight', weight.value || 'class.pt');
	params.set('conf', String(Number(conf.value) / 100));
	params.set('kind', kind.value);
	params.set('startTime', formatDate(new Date(), 'YYYY-mm-dd HH:MM:SS'));
	return params.toString();
}

async function startDetect() {
	const rawFile = (uploadRef.value as any)?.uploadFiles?.[0];
	const matchedDatasetValue = rawFile?.matchedPreprocessedDataset || findPreprocessedItemByVideoName(rawFile?.name || '')?.value;
	if (matchedDatasetValue && matchedDatasetValue !== preprocessedDataset.value) {
		preprocessedDataset.value = matchedDatasetValue;
	}
	const selectedDataset = activePreprocessedItem();
	const inputVideo = matchedDatasetValue
		? (selectedDataset?.inputPath || selectedDataset?.value || matchedDatasetValue)
		: (rawFile?.response?.data || rawFile?.uploadedPath || selectedDataset?.inputPath || preprocessedDataset.value || 'class_sample');
	const sourceName = rawFile?.name || selectedDataset?.sourceName || demoState.material.sourceName || 'class/sample/input.mp4';
	demoState.settings.confidence = conf.value;
	demoState.settings.model = weight.value;
	demoState.material.status = '检测中';
	demoState.material.progress = 0;
	resetTaskView(sourceName);
	processStatusText.value = '检测处理中';
	processProgressVisible.value = true;
	setResultVideoUrl('');
	streamUrl.value = '';
	try {
		const res = await request.post('/flask/videoTasks', {
			username: userInfos.value.userName || 'demo',
			inputVideo,
			sourceName,
			kind: 'class-pipeline',
			startTime: formatDate(new Date(), 'YYYY-mm-dd HH:MM:SS'),
			confThr: Number(conf.value) / 100,
			frameStride: 5,
			weight: weight.value,
			yoloModel: weight.value,
			lstmModel: lstmWeight.value,
			usePrecomputed: true,
			reuseResultVideo: false,
			preprocessedDataset: preprocessedDataset.value || 'sample',
			yoloDevice: 'cpu',
			rtmposeDevice: 'cpu',
			lstmDevice: 'cpu',
		});
		if (res?.code === 0 && res.data?.taskId) {
			currentTaskId.value = res.data.taskId;
			persistVideoPageState();
			startTaskPolling(res.data.taskId);
			ElMessage.success('已启动视频行为识别任务');
		} else {
			throw new Error(res?.message || 'task start failed');
		}
	} catch (error) {
		demoState.material.status = '检测任务启动失败';
		processProgressVisible.value = false;
		ElMessage.error('视频行为识别任务启动失败');
	}
}

function resetTaskView(sourceName: string) {
	if (taskPollTimer) {
		clearInterval(taskPollTimer);
		taskPollTimer = undefined;
	}
	demoState.hasLiveData = true;
	demoState.material.sourceName = sourceName;
	demoState.stats.splice(0, demoState.stats.length, {
		key: 'pending',
		label: '等待算法结果',
		duration: '0秒',
		ratio: '0.0%',
		count: 0,
		confidence: '-',
		tone: 'green',
		value: 0,
	});
	demoState.events.splice(0, demoState.events.length, {
		eventId: 'TASK-PENDING',
		sourceType: 'video',
		sourceName,
		behaviorType: 'none',
		riskLevel: 'normal',
		durationSeconds: 0,
		durationText: '0秒',
		confidence: '-',
		reason: '算法任务正在运行，完成后这里会显示后端生成的预警事件。',
		promptPreview: '等待算法端返回检测事件后生成干预提示词。',
		advice: '等待算法检测结果。',
		status: '检测中',
		createdAt: formatDate(new Date(), 'YYYY-mm-dd HH:MM:SS'),
		provider: demoState.provider,
	});
	demoState.selectedEventId = 'TASK-PENDING';
	latestPredictionWindows.value = [];
	latestBehaviorHeatmap.value = [];
	latestVideoInfo.value = {};
	scheduleChartRefresh();
}

function startTaskPolling(taskId: string) {
	if (taskPollTimer) clearInterval(taskPollTimer);
	taskPollTimer = setInterval(() => pollTask(taskId), 3000);
	pollTask(taskId);
}

function pollTask(taskId: string) {
	request.get(`/flask/videoTasks/${taskId}`).then((res) => {
		if (res?.code !== 0 || !res.data) return;
		const task = res.data;
		applyProtocolPayload(task);
		applyVideoInfo(task.videoInfo);
		updateChartsFromPayload(task);
		if (task.inputVideoUrl && !previewUrl.value.startsWith('blob:')) setPreviewVideoUrl(task.inputVideoUrl);
		if (task.resultVideoUrl) setResultVideoUrl(task.resultVideoUrl, `${taskId}-${task.progress || 0}`);
		if (typeof task.progress === 'number') demoState.material.progress = Math.round(task.progress);
		persistVideoPageState();
		if (task.message) processStatusText.value = task.message;
		if (task.taskStatus === 'done' || task.taskStatus === 'failed') {
			if (taskPollTimer) {
				clearInterval(taskPollTimer);
				taskPollTimer = undefined;
			}
			if (task.taskStatus === 'done') {
				if (!resultVideoUrl.value) setResultVideoUrl(`/flask/videoTasks/${taskId}/result-video`, `${taskId}-done`);
				demoState.material.status = '检测完成';
				demoState.material.progress = 100;
				processProgressVisible.value = false;
				persistVideoPageState();
			} else {
				markTaskFailed(task.message || task.error || '检测失败');
			}
		}
	}).catch(() => {});
}

function loadWeights() {
	request.get('/flask/class-models').then((res) => {
		if (res?.code === 0 && res.data) {
			const data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
			weightItems.value = data.yoloModelItems?.length ? data.yoloModelItems : (data.weight_items || []).filter((item: any) => String(item.value).endsWith('.pt'));
			if (data.lstmModelItems?.length) lstmWeight.value = data.lstmModelItems[0].value;
			if (weightItems.value.length && !weightItems.value.some((item) => item.value === weight.value)) {
				weight.value = weightItems.value[0].value;
			}
		}
	}).catch(() => {
		weightItems.value = [{ value: 'yolo_best.pt', label: 'yolo_best.pt' }];
		lstmWeight.value = 'best_lstm.pth';
	});
}

function loadPreprocessedDatasets() {
	request.get('/flask/class-preprocessed').then((res) => {
		if (res?.code === 0 && Array.isArray(res.data) && res.data.length) {
			preprocessedItems.value = res.data.map((item: any) => ({
				value: item.value,
				label: item.hasResultVideo ? `${item.label}（已有标注视频）` : `${item.label}（CSV）`,
			}));
			if (!preprocessedItems.value.some((item) => item.value === preprocessedDataset.value)) {
				preprocessedDataset.value = preprocessedItems.value[0].value;
			}
		}
	}).catch(() => {
		preprocessedItems.value = [{ value: 'sample', label: 'sample' }];
		preprocessedDataset.value = 'sample';
	});
}

function loadPreprocessedDatasetsV2() {
	request.get('/flask/class-preprocessed').then((res) => {
		if (res?.code === 0 && Array.isArray(res.data) && res.data.length) {
			preprocessedItems.value = res.data.map((item: any) => ({
				value: item.value,
				label: item.hasResultVideo ? `${item.label}（已有标注视频）` : `${item.label}（CSV）`,
				sourceName: item.sourceName,
				inputPath: item.inputPath,
				inputVideoUrl: item.inputVideoUrl,
				resultVideoUrl: item.resultVideoUrl,
				hasResultVideo: item.hasResultVideo,
			}));
			const currentVideoName = (uploadRef.value as any)?.uploadFiles?.[0]?.name || demoState.material.sourceName;
			const matchedItem = findPreprocessedItemByVideoName(currentVideoName);
			if (matchedItem) {
				preprocessedDataset.value = matchedItem.value;
			} else if (!preprocessedItems.value.some((item) => item.value === preprocessedDataset.value)) {
				preprocessedDataset.value = preprocessedItems.value[0].value;
			}
			handlePreprocessedDatasetChange();
			restoreVideoPageState();
		}
	}).catch(() => {
		preprocessedItems.value = [{ value: 'sample', label: 'sample', inputVideoUrl: '/flask/sample-video', sourceName: 'input.mp4' }];
		preprocessedDataset.value = 'sample';
		handlePreprocessedDatasetChange();
		restoreVideoPageState();
	});
}

function markTaskFailed(message: string) {
	demoState.material.status = message;
	processStatusText.value = message;
	processProgressVisible.value = false;
	demoState.stats.splice(0, demoState.stats.length, {
		key: 'failed',
		label: '检测未完成',
		duration: '0秒',
		ratio: '0.0%',
		count: 0,
		confidence: '-',
		tone: 'danger',
		value: 0,
	});
	demoState.events.splice(0, demoState.events.length, {
		eventId: 'TASK-FAILED',
		sourceType: 'video',
		sourceName: demoState.material.sourceName,
		behaviorType: 'none',
		riskLevel: 'normal',
		durationSeconds: 0,
		durationText: '0秒',
		confidence: '-',
		reason: message,
		promptPreview: '算法任务未完成，暂无可生成的干预提示词。',
		advice: '请检查 Flask 算法服务是否已重启、样例视频和模型文件是否存在。',
		status: '检测失败',
		createdAt: formatDate(new Date(), 'YYYY-mm-dd HH:MM:SS'),
		provider: demoState.provider,
	});
	demoState.selectedEventId = 'TASK-FAILED';
	latestPredictionWindows.value = [];
	latestBehaviorHeatmap.value = [];
	latestVideoInfo.value = {};
	scheduleChartRefresh();
}

function selectOffset(offset: number) {
	const currentIndex = demoState.events.findIndex((event) => event.eventId === currentEvent.value.eventId);
	const nextIndex = (currentIndex + offset + demoState.events.length) % demoState.events.length;
	setCurrentEvent(demoState.events[nextIndex].eventId);
}

function socketWarningToEvent(warning: any) {
	const behaviorType = normalizeBehavior(warning.behaviorType || warning.behavior || warning.type || 'none');
	const seconds = Number(warning.durationSeconds || warning.duration || 0);
	return upsertEvent({
		eventId: `EVT-${String(generatedEventIndex++).padStart(3, '0')}`,
		sourceType: 'video',
		sourceName: demoState.material.sourceName,
		behaviorType,
		riskLevel: warning.riskLevel || warning.level || 'normal',
		durationSeconds: seconds,
		durationText: seconds ? formatMinuteSecond(seconds) : (warning.durationText || '0秒'),
		confidence: warning.confidence ? `${warning.confidence}%` : '88.6%',
		reason: warning.reason || `${behaviorText(behaviorType)}达到演示阈值，形成检测事件。`,
		advice: warning.advice || '',
		status: '待跟进',
		provider: demoState.provider,
	});
}

function buildAdviceRequest(extra: Record<string, any> = {}) {
	return {
		riskLevel: currentEvent.value.riskLevel,
		behaviorType: currentEvent.value.behaviorType,
		durationSeconds: currentEvent.value.durationSeconds || parseDurationSeconds(currentEvent.value.durationText),
		durationText: currentEvent.value.durationText,
		reason: currentEvent.value.reason,
		scene: buildPrompt(currentEvent.value),
		provider: demoState.provider,
		...extra,
	};
}

function generateAdvice() {
	request.post('/api/warningRecords/advice', buildAdviceRequest()).then((res) => {
		const result = normalizeAdviceResult(res?.code == 0 ? res.data : null, fallbackAdvice(currentEvent.value));
		applyAdvice(result.advice, demoState.provider);
		aiChatMessages.value = [{ role: 'assistant', content: result.advice }];
		if (result.fallback) {
			ElMessage.warning(result.message || 'MiniMax 暂未返回，已使用本地模板建议');
		} else {
			ElMessage.success(`MiniMax ${result.model || ''} 沟通建议已生成`.trim());
		}
	}).catch(() => {
		const advice = fallbackAdvice(currentEvent.value);
		applyAdvice(advice, demoState.provider);
		aiChatMessages.value = [{ role: 'assistant', content: advice }];
		ElMessage.warning('AI接口暂不可用，已使用本地模板建议');
	});
}

function askAiFollowUp() {
	const question = aiChatInput.value.trim();
	if (!question || aiChatLoading.value) return;
	aiChatMessages.value.push({ role: 'user', content: question });
	aiChatInput.value = '';
	aiChatLoading.value = true;
	request.post('/api/warningRecords/advice', buildAdviceRequest({
		question,
		messages: aiChatMessages.value.slice(0, -1),
	})).then((res) => {
		const result = normalizeAdviceResult(res?.code == 0 ? res.data : null, fallbackAdvice(currentEvent.value));
		aiChatMessages.value.push({ role: 'assistant', content: result.advice });
		if (result.fallback) ElMessage.warning(result.message || 'MiniMax 暂未返回，已使用本地模板回复');
	}).catch(() => {
		aiChatMessages.value.push({ role: 'assistant', content: fallbackAdvice(currentEvent.value) });
		ElMessage.warning('AI接口暂不可用，已使用本地模板回复');
	}).finally(() => {
		aiChatLoading.value = false;
	});
}

function exportReport() {
	const blob = new Blob([exportReportText()], { type: 'text/plain;charset=utf-8' });
	const link = document.createElement('a');
	link.href = URL.createObjectURL(blob);
	link.download = `${currentEvent.value.eventId}-干预报告.txt`;
	link.click();
	URL.revokeObjectURL(link.href);
}

function initCharts() {
	const trendEl = document.getElementById('videoTrendChart');
	const pieEl = document.getElementById('videoPieChart');
	if (trendEl) {
		trendChart.value = echarts.init(trendEl);
		false && trendChart.value.setOption({
			color: ['#ef4f45', '#f2a51a', '#5b6ee1', '#20aa82'],
			tooltip: { trigger: 'axis' },
			legend: { top: 0, right: 8, data: ['趴桌', '持续低头', '玩手机', '专注'] },
			grid: { left: 34, right: 16, top: 42, bottom: 24 },
			xAxis: { type: 'category', boundaryGap: false, data: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00', '28:47'] },
			yAxis: { type: 'value', name: '人次秒' },
			series: [
				{ name: '趴桌', type: 'line', smooth: true, showSymbol: false, data: [0, 2, 1, 3, 5, 4, 2, 1] },
				{ name: '持续低头', type: 'line', smooth: true, showSymbol: false, data: [1, 16, 7, 9, 14, 8, 6, 2] },
				{ name: '玩手机', type: 'line', smooth: true, showSymbol: false, data: [0, 4, 3, 2, 4, 2, 1, 0] },
				{ name: '专注', type: 'line', smooth: true, showSymbol: false, data: [2, 4, 6, 5, 8, 14, 12, 6] },
			],
		});
		updateTrendChartFromMergedWindows();
	}
	if (pieEl) {
		pieChart.value = echarts.init(pieEl);
		updatePieChart();
	}
}

function updateChartsFromPayload(payload: any) {
	if (Array.isArray(payload?.predictionWindows)) {
		latestPredictionWindows.value = payload.predictionWindows;
	}
	if (Array.isArray(payload?.behaviorHeatmap)) {
		latestBehaviorHeatmap.value = payload.behaviorHeatmap;
	}
	if (payload?.videoInfo && typeof payload.videoInfo === 'object') {
		latestVideoInfo.value = { ...latestVideoInfo.value, ...payload.videoInfo };
	}
	if (Number(payload?.videoInfo?.durationSeconds) > 0) {
		latestVideoDurationSeconds.value = Number(payload.videoInfo.durationSeconds);
	}
	persistVideoPageState();
	scheduleChartRefresh();
}

function chartStats() {
	return demoState.stats
		.map((item) => {
			const value = Number(item.value ?? parseDurationSeconds(item.duration));
			return {
				key: item.key,
				label: item.label || behaviorText(item.key),
				value: Number.isFinite(value) ? value : 0,
			};
		})
		.filter((item) => item.value > 0 && item.key !== 'pending' && item.key !== 'failed');
}

function behaviorColor(key: string) {
	return behaviorChartColors[key] || '#64748b';
}

function mergedPredictionWindows(rawWindows: any[]) {
	const grouped = new Map<string, { behaviorType: string; trackId: string; intervals: Array<[number, number]> }>();
	rawWindows.forEach((item) => {
		const behaviorType = String(item.behaviorType || '');
		if (!behaviorType) return;
		const start = Number(item.startSecond || 0);
		let end = Number(item.endSecond || start);
		if (end <= start) end = start + Number(item.durationSeconds || 0);
		if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return;
		const trackId = String(item.trackId ?? item.track_id ?? 'unknown');
		const key = `${trackId}::${behaviorType}`;
		if (!grouped.has(key)) grouped.set(key, { behaviorType, trackId, intervals: [] });
		grouped.get(key)!.intervals.push([start, end]);
	});

	const merged: any[] = [];
	grouped.forEach((group) => {
		const intervals = group.intervals.sort((left, right) => left[0] - right[0]);
		const compact: Array<[number, number]> = [];
		intervals.forEach(([start, end]) => {
			const current = compact[compact.length - 1];
			if (!current || start > current[1] + 0.001) {
				compact.push([start, end]);
			} else {
				current[1] = Math.max(current[1], end);
			}
		});
		compact.forEach(([start, end]) => {
			merged.push({
				trackId: group.trackId,
				behaviorType: group.behaviorType,
				startSecond: start,
				endSecond: end,
				durationSeconds: end - start,
			});
		});
	});
	return merged;
}

function resizeCharts() {
	trendChart.value?.resize();
	pieChart.value?.resize();
}

function scheduleChartRefresh() {
	nextTick(() => {
		window.requestAnimationFrame(() => {
			updateTrendChartFromMergedWindows();
			updatePieChart();
			resizeCharts();
		});
	});
}

function updateTrendChart() {
	if (!trendChart.value) return;
	const windows = mergedPredictionWindows(latestPredictionWindows.value || []);
	const stats = chartStats();
	if (!windows.length) {
		const data = stats.length ? stats : [{ key: 'empty', label: '暂无数据', value: 0 }];
		trendChart.value.setOption({
			color: ['#20aa82'],
			tooltip: { trigger: 'axis' },
			legend: { top: 0, right: 8, data: ['累计时长'] },
			grid: { left: 42, right: 18, top: 42, bottom: 28 },
			xAxis: { type: 'category', boundaryGap: true, data: data.map((item) => item.label) },
			yAxis: { type: 'value', name: '秒' },
			series: [{
				name: '累计时长',
				type: 'bar',
				barMaxWidth: 32,
				data: data.map((item) => Number(item.value.toFixed(1))),
			}],
		}, true);
		return;
	}
	const duration = latestVideoDurationSeconds.value || Math.max(1, ...windows.map((item: any) => Number(item.endSecond || 0)));
	const bucketCount = Math.min(8, Math.max(4, Math.ceil(duration / 5)));
	const bucketSize = duration / bucketCount;
	const xAxis = Array.from({ length: bucketCount }, (_, index) => formatClock(index * bucketSize).slice(3));
	const behaviorOrder = ['head_down', 'lie_desk', 'focus', 'other_action', 'phone', 'sleep'];
	const activeBehaviors = Array.from(new Set([
		...behaviorOrder.filter((key) => stats.some((item) => item.key === key) || windows.some((item: any) => item.behaviorType === key)),
		...stats.map((item) => item.key),
	]));
	const series = activeBehaviors.map((key) => {
		const data = Array.from({ length: bucketCount }, () => 0);
		windows.forEach((item: any) => {
			if (item.behaviorType !== key) return;
			const start = Number(item.startSecond || 0);
			const end = Math.max(start, Number(item.endSecond || start));
			for (let index = 0; index < bucketCount; index += 1) {
				const bucketStart = index * bucketSize;
				const bucketEnd = (index + 1) * bucketSize;
				const overlap = Math.max(0, Math.min(end, bucketEnd) - Math.max(start, bucketStart));
				data[index] += overlap;
			}
		});
		return {
			name: behaviorText(key),
			type: 'line',
			smooth: true,
			showSymbol: false,
			data: data.map((value) => Number(value.toFixed(1))),
		};
	}).filter((item) => item.data.some((value: number) => value > 0));
	if (!series.length && stats.length) {
		latestPredictionWindows.value = [];
		latestBehaviorHeatmap.value = [];
		latestVideoInfo.value = {};
		updateTrendChart();
		return;
	}
	trendChart.value.setOption({
		color: ['#f2a51a', '#ef4f45', '#20aa82', '#5b6ee1', '#8b5cf6', '#b45309'],
		tooltip: { trigger: 'axis' },
		legend: { top: 0, right: 8, data: series.map((item) => item.name) },
		grid: { left: 38, right: 16, top: 42, bottom: 24 },
		xAxis: { type: 'category', boundaryGap: false, data: xAxis },
		yAxis: { type: 'value', name: '人次秒' },
		series,
	}, true);
}

function updateTrendChartFromMergedWindows() {
	if (!trendChart.value) return;
	const windows = mergedPredictionWindows(latestPredictionWindows.value || []);
	const stats = chartStats();
	if (!windows.length) {
		const data = stats.length ? stats : [{ key: 'empty', label: '暂无数据', value: 0 }];
		trendChart.value.setOption({
			color: data.map((item) => behaviorColor(item.key)),
			tooltip: { trigger: 'axis' },
			legend: { top: 0, right: 8, data: ['累计人次秒'] },
			grid: { left: 42, right: 18, top: 42, bottom: 28 },
			xAxis: { type: 'category', boundaryGap: true, data: data.map((item) => item.label) },
			yAxis: { type: 'value', name: '人次秒' },
			series: [{
				name: '累计人次秒',
				type: 'bar',
				barMaxWidth: 32,
				data: data.map((item) => ({
					value: Number(item.value.toFixed(1)),
					itemStyle: { color: behaviorColor(item.key) },
				})),
			}],
		}, true);
		return;
	}
	const duration = latestVideoDurationSeconds.value || Math.max(1, ...windows.map((item: any) => Number(item.endSecond || 0)));
	const bucketCount = Math.min(8, Math.max(4, Math.ceil(duration / 5)));
	const bucketSize = duration / bucketCount;
	const xAxis = Array.from({ length: bucketCount }, (_, index) => formatClock(index * bucketSize).slice(3));
	const activeBehaviors = Array.from(new Set([
		...behaviorOrder.filter((key) => stats.some((item) => item.key === key) || windows.some((item: any) => item.behaviorType === key)),
		...stats.map((item) => item.key),
	]));
	const series = activeBehaviors.map((key) => {
		const data = Array.from({ length: bucketCount }, () => 0);
		windows.forEach((item: any) => {
			if (item.behaviorType !== key) return;
			const start = Number(item.startSecond || 0);
			const end = Math.max(start, Number(item.endSecond || start));
			for (let index = 0; index < bucketCount; index += 1) {
				const bucketStart = index * bucketSize;
				const bucketEnd = (index + 1) * bucketSize;
				const overlap = Math.max(0, Math.min(end, bucketEnd) - Math.max(start, bucketStart));
				data[index] += overlap;
			}
		});
		return {
			name: behaviorText(key),
			type: 'line',
			smooth: true,
			showSymbol: false,
			lineStyle: { color: behaviorColor(key) },
			itemStyle: { color: behaviorColor(key) },
			data: data.map((value) => Number(value.toFixed(1))),
		};
	}).filter((item) => item.data.some((value: number) => value > 0));
	trendChart.value.setOption({
		color: activeBehaviors.map((key) => behaviorColor(key)),
		tooltip: { trigger: 'axis' },
		legend: { top: 0, right: 8, data: series.map((item) => item.name) },
		grid: { left: 42, right: 16, top: 42, bottom: 24 },
		xAxis: { type: 'category', boundaryGap: false, data: xAxis },
		yAxis: { type: 'value', name: '人次秒' },
		series,
	}, true);
}

function updatePieChart() {
	if (!pieChart.value) return;
	const stats = chartStats();
	const hasData = stats.length > 0;
	pieChart.value.setOption({
		color: stats.map((item) => behaviorColor(item.key)),
		tooltip: { trigger: 'item' },
		legend: { show: hasData, orient: 'vertical', right: 0, top: 'middle', itemWidth: 8, itemHeight: 8 },
		series: [{
			type: 'pie',
			radius: ['46%', '70%'],
			center: ['34%', '52%'],
			label: { show: false },
			silent: !hasData,
			data: hasData
				? stats.map((item) => ({ name: item.label, value: item.value, itemStyle: { color: behaviorColor(item.key) } }))
				: [{ name: '暂无数据', value: 1, itemStyle: { color: '#dce8e5' } }],
		}],
	});
}

socketService.on('message', (data: any) => {
	if (currentTaskId.value && data?.taskId && data.taskId !== currentTaskId.value) return;
	applyVideoInfo(data?.videoInfo);
	if (data?.inputVideoUrl && !previewUrl.value.startsWith('blob:')) setPreviewVideoUrl(data.inputVideoUrl);
	if (data?.resultVideoUrl) setResultVideoUrl(data.resultVideoUrl, `${data.taskId || currentTaskId.value || 'socket'}-${data.progress || 0}`);
	if (data?.step) processStatusText.value = data.message || data.step;
	if (data?.taskStatus === 'failed') {
		demoState.material.status = data.message || '检测任务失败';
		ElMessage.error(demoState.material.status);
		return;
	}
	if (data?.protocolVersion === 'classroom-demo-v1' || data?.behaviorStats) {
		applyProtocolPayload(data);
		updateChartsFromPayload(data);
		if (data.completed) {
			demoState.material.status = '检测完成';
		} else if (data.warningState?.warning) {
			demoState.material.status = '检测事件已生成';
			ElMessage.warning(data.warningState.warning.reason || '检测事件已生成');
		}
		return;
	}
	if (data?.warningState?.warning) {
		socketWarningToEvent(data.warningState.warning);
		demoState.material.status = '检测事件已生成';
		ElMessage.warning(currentEvent.value.reason);
	}
	const labels = data?.warningState?.normalizedLabels || data?.labels;
	if (Array.isArray(labels)) {
		updateStatsFromLabels(labels);
		scheduleChartRefresh();
	}
});

socketService.on('progress', (data: any) => {
	if (currentTaskId.value && data?.taskId && data.taskId !== currentTaskId.value) return;
	const percent = Math.min(100, Math.max(0, Math.round(Number(data?.data ?? data) || 0)));
	demoState.material.progress = percent;
	persistVideoPageState();
	processProgressVisible.value = true;
	processStatusText.value = percent >= 100 ? '检测完成' : '检测处理中';
	if (percent >= 100) {
		demoState.material.status = '检测完成';
		setTimeout(() => {
			processProgressVisible.value = false;
			demoState.material.progress = 0;
		}, 1600);
	}
});

onMounted(() => {
	loadWeights();
	loadPreprocessedDatasetsV2();
	nextTick(initCharts);
	window.addEventListener('resize', resizeCharts);
});

onUnmounted(() => {
	if (taskPollTimer) clearInterval(taskPollTimer);
	window.removeEventListener('resize', resizeCharts);
	if (previewUrl.value.startsWith('blob:')) URL.revokeObjectURL(previewUrl.value);
	trendChart.value?.dispose();
	pieChart.value?.dispose();
	socketService.disconnect();
});
</script>

<style scoped lang="scss">
.video-workspace {
	height: 100%;
	display: grid;
	grid-template-columns: minmax(620px, 1fr) minmax(380px, 460px);
	gap: 16px;
	overflow: hidden;
}

.left-scroll,
.ai-scroll {
	min-width: 0;
	height: 100%;
	overflow-y: auto;
	scrollbar-width: thin;
}

.left-scroll {
	padding-right: 2px;
}

.panel,
.ai-panel {
	border-radius: 8px;
	background: rgba(255, 255, 255, 0.97);
	border: 1px solid #dde8e5;
	box-shadow: 0 14px 34px rgba(23, 42, 46, 0.07);
}

.video-panel,
.stats-panel {
	padding: 16px;
}

.stats-panel {
	margin-top: 14px;
}

.video-head {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 16px;
	margin-bottom: 12px;
}

.video-head h3 {
	margin: 0 0 8px;
	font-size: 16px;
}

.video-head h3 span {
	margin-left: 6px;
	color: #2c3c40;
	font-weight: 700;
}

.video-head p {
	margin: 0;
	color: #647276;
	font-size: 13px;
}

.video-actions,
.model-row {
	display: flex;
	align-items: center;
	gap: 12px;
}

.model-row {
	margin-bottom: 12px;
	flex-wrap: wrap;
}

.demo-start-panel {
	margin: 12px 0;
	padding: 14px 16px;
	border-radius: 8px;
	border: 1px solid #dbe9e6;
	background: #f7fbfa;
	display: flex;
	align-items: center;
	justify-content: center;
	gap: 28px;
	text-align: left;
}

.demo-start-panel strong {
	display: block;
	margin-bottom: 4px;
	color: #172327;
	font-size: 16px;
}

.demo-start-panel span {
	color: #647276;
	font-size: 13px;
}

.demo-start-panel .video-actions {
	justify-content: center;
}

.result-video-layout {
	display: grid;
	grid-template-columns: 190px minmax(0, 1fr);
	gap: 12px;
	align-items: stretch;
}

.result-video-copy {
	border-radius: 8px;
	border: 1px solid #dbe9e6;
	background: #f7fbfa;
	padding: 14px;
	display: grid;
	align-content: center;
	gap: 10px;
}

.result-video-copy span {
	color: #008f87;
	font-size: 13px;
	font-weight: 800;
}

.result-video-copy strong {
	color: #1f3337;
	font-size: 20px;
	line-height: 1.3;
}

.result-video-copy p {
	margin: 0;
	color: #647276;
	line-height: 1.7;
	font-size: 13px;
}

.video-frame {
	position: relative;
	height: clamp(330px, 42vh, 450px);
	border-radius: 8px;
	background: #15282d;
	overflow: hidden;
	display: flex;
	align-items: center;
	justify-content: center;
}

.result-frame {
	height: clamp(360px, 48vh, 520px);
}

.video-content {
	width: 100%;
	height: 100%;
	object-fit: contain;
	background: #111d21;
}

.video-loading,
.video-error {
	position: absolute;
	inset: 0;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 10px;
	color: #d7f3ef;
	background: rgba(17, 29, 33, 0.58);
	font-size: 14px;
	z-index: 2;
	pointer-events: none;
}

.video-loading .el-icon {
	font-size: 24px;
}

.video-error {
	background: rgba(17, 29, 33, 0.78);
	color: #ffffff;
	pointer-events: auto;
}

.classroom-placeholder {
	position: relative;
	width: 100%;
	height: 100%;
	background:
		linear-gradient(#e7ece9 0 25%, transparent 25%),
		linear-gradient(#805d45 0 0);
	overflow: hidden;
}

.board {
	position: absolute;
	left: 35%;
	top: 6%;
	width: 30%;
	height: 18%;
	background: #e9efec;
	border: 8px solid #304a48;
}

.student {
	position: absolute;
	width: 80px;
	height: 70px;
	border-radius: 40px 40px 10px 10px;
	background: #2c3b3d;
	box-shadow: 0 36px 0 #c89e73;
}

.student::after {
	content: "";
	position: absolute;
	left: -14px;
	top: 56px;
	width: 110px;
	height: 16px;
	border-radius: 8px;
	background: #d6a87a;
}

.s1 { left: 11%; top: 38%; transform: scale(.72); }
.s2 { left: 25%; top: 36%; transform: scale(.76); }
.s3 { left: 42%; top: 46%; transform: scale(1.18); }
.s4 { left: 60%; top: 38%; transform: scale(.76); }
.s5 { left: 77%; top: 40%; transform: scale(.75); }
.s6 { left: 17%; top: 58%; transform: scale(.92); }
.s7 { left: 34%; top: 62%; transform: scale(1.05); }
.s8 { left: 55%; top: 62%; transform: scale(.96); }
.s9 { left: 72%; top: 61%; transform: scale(.9); }
.s10 { left: 6%; top: 20%; transform: scale(.48); }
.s11 { left: 51%; top: 24%; transform: scale(.48); }
.s12 { left: 84%; top: 22%; transform: scale(.5); }

.detect-label {
	position: absolute;
	padding: 6px 10px;
	border-radius: 6px;
	color: #fff;
	font-size: 13px;
	font-weight: 800;
	border: 2px solid currentColor;
	background: rgba(0, 0, 0, 0.34);
}

.detect-label.danger { left: 45%; top: 38%; color: #ef4f45; }
.detect-label.amber { left: 8%; top: 30%; color: #f2a51a; }
.detect-label.purple { left: 26%; top: 32%; color: #8b5cf6; }

.placeholder-copy {
	position: absolute;
	left: 50%;
	bottom: 16%;
	transform: translateX(-50%);
	display: grid;
	gap: 8px;
	color: #fff;
	text-align: center;
	text-shadow: 0 2px 8px rgba(0, 0, 0, .45);
}

.placeholder-copy strong {
	font-size: 18px;
}

.detect-chip {
	position: absolute;
	left: 14px;
	top: 14px;
	height: 30px;
	padding: 0 12px;
	border-radius: 6px;
	display: inline-flex;
	align-items: center;
	gap: 6px;
	color: #fff;
	background: rgba(12, 36, 39, 0.72);
	font-size: 12px;
	font-weight: 700;
}

.progress-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 14px;
	margin-top: 12px;
	color: #647276;
}

.section-head h3,
.chart-card h4,
.box h3,
.advice-box h3 {
	margin: 0;
}

.section-head span {
	margin-left: 8px;
	color: #75858a;
	font-size: 13px;
	font-weight: 400;
}

.stat-grid {
	display: grid;
	grid-template-columns: repeat(5, minmax(120px, 1fr));
	gap: 12px;
	margin-top: 14px;
}

.stat-card {
	min-height: 118px;
	padding: 14px;
	border-radius: 8px;
	border: 1px solid;
	background: #fff;
}

.stat-card span {
	display: block;
	color: #4b5c61;
	font-weight: 700;
}

.stat-card strong {
	display: block;
	margin: 12px 0 8px;
	font-size: 23px;
	line-height: 1.05;
}

.stat-card p,
.stat-card em {
	display: block;
	margin: 0 0 6px;
	color: #5d6d72;
	font-size: 12px;
	font-style: normal;
}

.stat-card.danger { border-color: #f4d6d2; background: #fff4f2; }
.stat-card.warm { border-color: #f3dfbd; background: #fff8ed; }
.stat-card.amber { border-color: #eee2c7; background: #fffaf0; }
.stat-card.purple { border-color: #e4d8f7; background: #faf6ff; }
.stat-card.green { border-color: #d7eadf; background: #f4fbf7; }

.chart-grid {
	display: grid;
	grid-template-columns: minmax(0, 1.65fr) minmax(240px, .95fr);
	gap: 14px;
	margin-top: 14px;
}

.chart-card {
	padding: 14px;
	border-radius: 8px;
	border: 1px solid #e0e9e7;
	background: #fff;
}

.chart-card h4 {
	font-size: 15px;
	margin-bottom: 8px;
}

.chart {
	height: 220px;
}

.ai-panel {
	min-width: 0;
	overflow: hidden;
}

.ai-scroll {
	padding: 18px;
}

.ai-title {
	margin-bottom: 12px;
	font-size: 22px;
	font-weight: 800;
}

.ai-title span {
	color: #008f87;
}

.event-card,
.box,
.advice-box {
	border-radius: 8px;
	border: 1px solid #e0e9e7;
	background: #fff;
	padding: 14px;
}

.ai-empty-state {
	min-height: 300px;
	border-radius: 8px;
	border: 1px dashed #c9ddd8;
	background: #f7fbfa;
	padding: 28px 18px;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	text-align: center;
	gap: 12px;
	color: #52686b;
}

.ai-empty-state h3,
.ai-empty-state p {
	margin: 0;
}

.ai-empty-state p {
	max-width: 320px;
	line-height: 1.7;
}

.ai-empty-state .alert-icon {
	background: #008f87;
}

.event-head,
.box-head {
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: 10px;
	margin-bottom: 12px;
}

.event-head h3 {
	margin: 0;
}

.event-alert {
	display: grid;
	grid-template-columns: 76px minmax(0, 1fr);
	gap: 18px;
	padding: 18px;
	border-radius: 8px;
	background: linear-gradient(135deg, #fff0ee 0%, #fff8f7 100%);
	border: 1px solid #f2d4d0;
}

.event-alert.medium {
	background: linear-gradient(135deg, #fff8ec 0%, #fffdf6 100%);
	border-color: #f0dfbd;
}

.event-alert.low,
.event-alert.normal {
	background: linear-gradient(135deg, #effaf6 0%, #fbfffd 100%);
	border-color: #cdebe4;
}

.alert-icon {
	width: 64px;
	height: 64px;
	border-radius: 50%;
	background: #ef4f45;
	color: #fff;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 34px;
}

.event-alert.medium .alert-icon {
	background: #f2a51a;
}

.event-alert.low .alert-icon,
.event-alert.normal .alert-icon {
	background: #008f87;
}

.risk-line {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
	margin-bottom: 8px;
}

.risk-line strong {
	font-size: 20px;
}

.event-alert p,
.box p,
.advice-content p {
	margin: 7px 0 0;
	color: #516166;
	line-height: 1.75;
	font-size: 13px;
}

.box,
.advice-box {
	margin-top: 12px;
}

.model-box {
	border-left: 0;
	border-right: 0;
	border-radius: 0;
	padding-left: 0;
	padding-right: 0;
}

.provider-card {
	display: grid;
	gap: 6px;
	padding: 12px;
	border-radius: 8px;
	background: #f7fbfa;
	border: 1px solid #dbe9e6;
}

.provider-card strong {
	color: #0b766f;
	font-size: 16px;
}

.provider-card span,
.chat-empty {
	color: #66787d;
	font-size: 13px;
	line-height: 1.6;
}

.advice-box {
	background: #f1fbf8;
	border-color: #cdebe4;
}

.chat-list {
	display: grid;
	gap: 8px;
	max-height: 210px;
	overflow-y: auto;
	padding-right: 2px;
}

.chat-message {
	width: fit-content;
	max-width: 92%;
	padding: 9px 11px;
	border-radius: 8px;
	line-height: 1.6;
	font-size: 13px;
	background: #f7fbfa;
	color: #34464a;
	border: 1px solid #e0e9e7;
}

.chat-message.user {
	justify-self: end;
	background: #008f87;
	color: #fff;
	border-color: #008f87;
}

.chat-input-row {
	display: grid;
	grid-template-columns: minmax(0, 1fr) auto;
	gap: 8px;
	margin-top: 10px;
}

.advice-content {
	display: grid;
	grid-template-columns: 28px minmax(0, 1fr);
	gap: 10px;
	align-items: flex-start;
}

.advice-content .el-icon {
	margin-top: 4px;
	color: #008f87;
	font-size: 22px;
}

.export-button {
	width: 100%;
	height: 52px;
	margin-top: 18px;
	border: 0;
	border-radius: 8px;
	font-size: 17px;
	font-weight: 800;
	background: linear-gradient(135deg, #008f87 0%, #00a99d 100%);
	box-shadow: 0 14px 24px rgba(0, 143, 135, 0.22);
}

.left-scroll::-webkit-scrollbar,
.ai-scroll::-webkit-scrollbar {
	width: 8px;
}

.left-scroll::-webkit-scrollbar-thumb,
.ai-scroll::-webkit-scrollbar-thumb {
	background: #c8d7d3;
	border-radius: 999px;
}

@media (max-width: 1260px) {
	.video-workspace {
		grid-template-columns: minmax(430px, 1fr) minmax(320px, 360px);
	}

	.stat-grid {
		grid-template-columns: repeat(3, 1fr);
	}

	.chart-grid {
		grid-template-columns: 1fr;
	}
}

@media (max-width: 980px) {
	.video-workspace {
		height: auto;
		grid-template-columns: 1fr;
		overflow: visible;
	}

	.result-video-layout {
		grid-template-columns: 1fr;
	}

	.demo-start-panel {
		flex-direction: column;
		align-items: stretch;
		gap: 12px;
		text-align: center;
	}

	.left-scroll,
	.ai-scroll {
		height: auto;
		overflow: visible;
	}
}
</style>
