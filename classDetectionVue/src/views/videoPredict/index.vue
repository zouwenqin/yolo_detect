<template>
	<DemoShell active="video" title="录制视频检测" :status="demoState.material.status" :status-type="statusType">
		<template #actions>
			<el-button @click="chooseVideo">
				<el-icon><FolderOpened /></el-icon>
				视频素材
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

					<div class="model-row">
						<el-select v-model="kind" placeholder="检测类别" style="width: 190px" @change="loadWeights">
							<el-option v-for="item in kindItems" :key="item.value" :label="item.label" :value="item.value" />
						</el-select>
						<el-select v-model="weight" placeholder="检测模型" style="width: 190px">
							<el-option v-for="item in weightItems" :key="item.value" :label="item.label" :value="item.value" />
						</el-select>
						<div class="confidence-control">
							<span>置信度阈值</span>
							<el-slider v-model="conf" :format-tooltip="(value) => value / 100" />
						</div>
					</div>

					<div class="video-frame">
						<img v-if="streamUrl" class="video-content" :src="streamUrl" />
						<video v-else-if="previewUrl" class="video-content" :src="previewUrl" controls preload="metadata"></video>
						<div v-else class="classroom-placeholder">
							<div class="board"></div>
							<div v-for="student in placeholderStudents" :key="student" class="student" :class="`s${student}`"></div>
							<div class="detect-label danger">连续趴桌 15m03s</div>
							<div class="detect-label amber">持续低头 8m12s</div>
							<div class="detect-label purple">玩手机 2m45s</div>
							<div class="placeholder-copy">
								<strong>上传课堂录制视频</strong>
								<span>未上传时展示检测框示意，上传后使用原生播放器预览</span>
							</div>
						</div>
						<div class="detect-chip">
							<el-icon><CircleCheckFilled /></el-icon>
							{{ demoState.material.status }}
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
						<h3>行为统计 <span>基于整段视频</span></h3>
					</div>
					<div class="stat-grid">
						<div v-for="item in demoState.stats" :key="item.key" class="stat-card" :class="item.tone">
							<span>{{ item.label }}</span>
							<strong>{{ item.duration }}</strong>
							<p>占比 {{ item.ratio }}　事件 {{ item.count }}次</p>
							<em>置信度 {{ item.confidence }}</em>
						</div>
					</div>
					<div class="chart-grid">
						<div class="chart-card">
							<h4>行为时长趋势</h4>
							<div id="videoTrendChart" class="chart"></div>
						</div>
						<div class="chart-card">
							<h4>行为占比</h4>
							<div id="videoPieChart" class="chart"></div>
						</div>
					</div>
				</section>
			</div>

			<aside class="ai-panel">
				<div class="ai-scroll">
					<div class="ai-title"><span>AI</span> 辅助干预</div>
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

					<section class="box model-box">
						<h3>模型选择</h3>
						<el-radio-group v-model="demoState.provider">
							<el-radio-button label="qwen">阿里千问</el-radio-button>
							<el-radio-button label="kimi">Kimi</el-radio-button>
						</el-radio-group>
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

					<el-button class="export-button" type="primary" @click="exportReport">
						<el-icon><DocumentChecked /></el-icon>
						导出干预报告
					</el-button>
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
import { ChatDotRound, CircleCheckFilled, Document, DocumentChecked, FolderOpened, Reading, Setting } from '@element-plus/icons-vue';
import * as echarts from 'echarts';
import DemoShell from '/@/views/demo/components/DemoShell.vue';
import {
	applyAdvice,
	behaviorText,
	buildPrompt,
	currentEvent,
	demoState,
	exportReportText,
	fallbackAdvice,
	formatMinuteSecond,
	normalizeBehavior,
	riskTagType,
	riskText,
	setCurrentEvent,
	updateStatsFromLabels,
	upsertEvent,
} from '/@/views/demo/demoState';
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
const weightItems = ref([{ value: 'class.pt', label: 'class.pt' }]);
const previewUrl = ref('');
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
let generatedEventIndex = demoState.events.length + 1;

const statusType = computed(() => {
	if (demoState.material.status.includes('完成')) return 'success';
	if (demoState.material.status.includes('检测')) return 'warning';
	return 'success';
});

function chooseVideo() {
	(uploadRef.value?.$el as HTMLElement | undefined)?.querySelector('input')?.click();
}

function handleVideoChange(file: any) {
	if (!file?.raw) return;
	if (previewUrl.value) URL.revokeObjectURL(previewUrl.value);
	previewUrl.value = URL.createObjectURL(file.raw);
	streamUrl.value = '';
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

function startDetect() {
	const hasVideo = previewUrl.value || (uploadRef.value as any)?.uploadFiles?.length;
	if (!hasVideo) {
		ElMessage.warning('请先上传或选择录制视频素材');
		return;
	}
	demoState.settings.confidence = conf.value;
	demoState.settings.model = weight.value;
	demoState.material.status = '检测中';
	demoState.material.progress = 0;
	processStatusText.value = '检测处理中';
	processProgressVisible.value = true;
	streamUrl.value = `http://127.0.0.1:5000/predictVideo?${buildQueryParams()}`;
	ElMessage.success('正在加载视频检测流');
}

function loadWeights() {
	request.get('/api/flask/file_names').then((res) => {
		if (res?.code === 0 && res.data) {
			const data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
			weightItems.value = (data.weight_items || []).filter((item: any) => String(item.value).includes(kind.value));
			if (weightItems.value.length && !weightItems.value.some((item) => item.value === weight.value)) {
				weight.value = weightItems.value[0].value;
			}
		}
	}).catch(() => {
		weightItems.value = [{ value: 'class.pt', label: 'class.pt' }];
	});
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
		durationText: seconds ? formatMinuteSecond(seconds) : (warning.durationText || '0秒'),
		confidence: warning.confidence ? `${warning.confidence}%` : '88.6%',
		reason: warning.reason || `${behaviorText(behaviorType)}达到演示阈值，形成检测事件。`,
		advice: warning.advice || '',
		status: '待跟进',
		provider: demoState.provider,
	});
}

function generateAdvice() {
	request.post('/api/warningRecords/advice', {
		riskLevel: currentEvent.value.riskLevel,
		behaviorType: currentEvent.value.behaviorType,
		durationText: currentEvent.value.durationText,
		reason: currentEvent.value.reason,
		scene: buildPrompt(currentEvent.value),
		provider: demoState.provider,
	}).then((res) => {
		const advice = res?.code === 0 ? (res.data || fallbackAdvice(currentEvent.value)) : fallbackAdvice(currentEvent.value);
		applyAdvice(advice, demoState.provider);
		ElMessage.success('AI沟通建议已生成');
	}).catch(() => {
		applyAdvice(fallbackAdvice(currentEvent.value), demoState.provider);
		ElMessage.warning('AI接口暂不可用，已使用本地模板建议');
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
		trendChart.value.setOption({
			color: ['#ef4f45', '#f2a51a', '#5b6ee1', '#20aa82'],
			tooltip: { trigger: 'axis' },
			legend: { top: 0, right: 8, data: ['趴桌', '持续低头', '玩手机', '专注'] },
			grid: { left: 34, right: 16, top: 42, bottom: 24 },
			xAxis: { type: 'category', boundaryGap: false, data: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00', '28:47'] },
			yAxis: { type: 'value', name: '分钟' },
			series: [
				{ name: '趴桌', type: 'line', smooth: true, showSymbol: false, data: [0, 2, 1, 3, 5, 4, 2, 1] },
				{ name: '持续低头', type: 'line', smooth: true, showSymbol: false, data: [1, 16, 7, 9, 14, 8, 6, 2] },
				{ name: '玩手机', type: 'line', smooth: true, showSymbol: false, data: [0, 4, 3, 2, 4, 2, 1, 0] },
				{ name: '专注', type: 'line', smooth: true, showSymbol: false, data: [2, 4, 6, 5, 8, 14, 12, 6] },
			],
		});
	}
	if (pieEl) {
		pieChart.value = echarts.init(pieEl);
		updatePieChart();
	}
}

function updatePieChart() {
	if (!pieChart.value) return;
	pieChart.value.setOption({
		color: ['#20aa82', '#f2a51a', '#ef4f45', '#8b5cf6', '#5b6ee1'],
		tooltip: { trigger: 'item' },
		legend: { orient: 'vertical', right: 0, top: 'middle', itemWidth: 8, itemHeight: 8 },
		series: [{
			type: 'pie',
			radius: ['46%', '70%'],
			center: ['34%', '52%'],
			label: { show: false },
			data: demoState.stats.map((item) => ({ name: item.label, value: item.value })),
		}],
	});
}

socketService.on('message', (data: any) => {
	if (data?.warningState?.warning) {
		socketWarningToEvent(data.warningState.warning);
		demoState.material.status = '检测事件已生成';
		ElMessage.warning(currentEvent.value.reason);
	}
	const labels = data?.warningState?.normalizedLabels || data?.labels;
	if (Array.isArray(labels)) {
		updateStatsFromLabels(labels);
		updatePieChart();
	}
});

socketService.on('progress', (data: any) => {
	const percent = Math.min(100, Math.max(0, Math.round(Number(data?.data ?? data) || 0)));
	demoState.material.progress = percent;
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
	nextTick(initCharts);
});

onUnmounted(() => {
	if (previewUrl.value) URL.revokeObjectURL(previewUrl.value);
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

.confidence-control {
	width: 260px;
	display: grid;
	grid-template-columns: 78px 1fr;
	align-items: center;
	gap: 10px;
	color: #647276;
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

.video-content {
	width: 100%;
	height: 100%;
	object-fit: contain;
	background: #111d21;
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

.advice-box {
	background: #f1fbf8;
	border-color: #cdebe4;
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

	.left-scroll,
	.ai-scroll {
		height: auto;
		overflow: visible;
	}
}
</style>
