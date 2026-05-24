<template>
	<div class="competition-page layout-padding">
		<div class="competition-content layout-padding-auto layout-padding-view">
			<section class="page-header">
				<div>
					<p class="eyebrow">图片素材检测</p>
					<h1>课堂图片行为识别</h1>
					<p>上传课堂图片素材，识别行为分布，并将异常行为转化为AI辅助干预建议。</p>
				</div>
				<div class="header-status">
					<span>{{ state.detectStatus }}</span>
					<strong>{{ state.predictionResult.label.length }}</strong>
				</div>
			</section>

			<section class="toolbar-panel">
				<el-select v-model="kind" placeholder="检测种类" size="large" style="width: 190px" @change="getData">
					<el-option v-for="item in state.kind_items" :key="item.value" :label="item.label" :value="item.value" />
				</el-select>
				<el-select v-model="weight" placeholder="检测模型" size="large" style="width: 190px">
					<el-option v-for="item in state.weight_items" :key="item.value" :label="item.label" :value="item.value" />
				</el-select>
				<div class="confidence-control">
					<span>置信度阈值</span>
					<el-slider v-model="conf" :format-tooltip="formatTooltip" />
				</div>
				<el-button type="primary" @click="upData">开始检测</el-button>
			</section>

			<div class="main-grid">
				<section class="image-workspace">
					<div class="section-title">
						<div>
							<span>图片检测区</span>
							<h3>上传/检测结果</h3>
						</div>
						<el-tag :type="state.predictionResult.label.length ? 'success' : 'info'">{{ state.detectStatus }}</el-tag>
					</div>
					<el-upload
						v-model="state.img"
						ref="uploadFile"
						class="image-uploader"
						action="http://localhost:9999/files/upload"
						:show-file-list="false"
						:on-success="handleAvatarSuccessone"
					>
						<img v-if="imageUrl" :src="imageUrl" class="preview-image" />
						<div v-else class="image-placeholder">
							<el-icon><Plus /></el-icon>
							<strong>上传课堂图片素材</strong>
							<span>检测结果图会在此处展示</span>
						</div>
					</el-upload>
				</section>

				<section class="stats-panel">
					<div class="section-title">
						<div>
							<span>行为统计</span>
							<h3>图片检测结果</h3>
						</div>
					</div>
					<div class="summary-row">
						<div>
							<span>检测目标</span>
							<strong>{{ state.predictionResult.label.length }}</strong>
						</div>
						<div>
							<span>最高置信度</span>
							<strong>{{ maxConfidence }}%</strong>
						</div>
						<div>
							<span>平均置信度</span>
							<strong>{{ avgConfidence }}%</strong>
						</div>
					</div>
					<div class="behavior-list">
						<div v-for="item in behaviorCountList" :key="item.name">
							<span>{{ item.name }}</span>
							<strong>{{ item.count }}</strong>
						</div>
					</div>
					<div class="chart-grid">
						<div id="barChart" class="chart-item"></div>
						<div id="pieChart" class="chart-item"></div>
					</div>
				</section>

				<aside class="intervention-panel">
					<div class="section-title">
						<div>
							<span>创新亮点</span>
							<h3>AI 辅助干预模块</h3>
						</div>
						<el-tag type="success" effect="plain">MiniMax</el-tag>
					</div>
					<div class="event-card">
						<div class="event-id">{{ state.event.eventId }}</div>
						<div class="risk-line">
							<span>{{ behaviorText(state.event.behaviorType) }}</span>
							<el-tag :type="riskTagType(state.event.riskLevel)">{{ riskText(state.event.riskLevel) }}</el-tag>
						</div>
						<p>{{ state.event.reason }}</p>
					</div>
					<div class="prompt-box">
						<div class="box-title">Prompt 构建</div>
						<p>{{ state.event.promptPreview }}</p>
					</div>
					<div class="advice-box">
						<div class="box-title">报表展示</div>
						<p>{{ state.event.advice }}</p>
					</div>
					<div class="intervention-actions">
						<el-button type="primary" @click="generateAdvice">生成沟通建议</el-button>
						<el-button @click="exportReport">导出干预报告</el-button>
					</div>
				</aside>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts" name="imgPredict">
import { computed, reactive, ref, onMounted, nextTick } from 'vue';
import type { UploadInstance, UploadProps } from 'element-plus';
import { ElMessage } from 'element-plus';
import request from '/@/utils/request';
import { normalizeAdviceResult } from '/@/utils/advice';
import { Plus } from '@element-plus/icons-vue';
import { useUserInfo } from '/@/stores/userInfo';
import { storeToRefs } from 'pinia';
import { formatDate } from '/@/utils/formatTime';
import * as echarts from 'echarts';

const imageUrl = ref('');
const conf = ref(50);
const weight = ref('');
const kind = ref('class');
const uploadFile = ref<UploadInstance>();
const stores = useUserInfo();
const { userInfos } = storeToRefs(stores);
const behaviorList = ['举手', '阅读', '写作', '玩手机', '低头', '靠桌子', '趴桌', '睡觉'];
const focusList = ['举手', '阅读', '写作'];
const defaultAdvice = '当前图片素材未形成明显异常行为事件。教师可结合课堂背景继续观察整体专注状态，若类似行为在多段素材中重复出现，再进行温和沟通。';

const state = reactive({
	weight_items: [] as any[],
	kind_items: [{ value: 'class', label: '课堂学生行为检测' }],
	img: '',
	detectStatus: '等待上传素材',
	provider: 'minmax',
	predictionResult: {
		label: [] as string[],
		confidence: '',
		allTime: '',
	},
	event: {
		eventId: '检测事件 #01',
		sourceType: 'image',
		behaviorType: 'none',
		riskLevel: 'normal',
		durationText: '图片单帧',
		reason: '尚未检测到需要研判的图片行为事件',
		promptPreview: '检测事件 #01，等待图片检测结果生成Prompt。',
		advice: defaultAdvice,
		provider: 'minmax',
	},
	form: {
		username: '',
		inputImg: null as any,
		weight: '',
		conf: null as any,
		kind: '',
		startTime: '',
	},
});

const providerText = computed(() => 'MiniMax');
const behaviorText = (behavior: string) => ({ sleep: '疑似睡觉', lie_desk: '趴桌', head_down: '持续低头', phone: '玩手机', focus: '课堂专注', none: '暂无事件' } as any)[behavior] || behavior || '课堂行为';
const riskText = (risk: string) => ({ high: '高风险', medium: '中风险', low: '低风险', normal: '正常' } as any)[risk] || '正常';
const riskTagType = (risk: string) => ({ high: 'danger', medium: 'warning', low: 'info', normal: 'success' } as any)[risk] || 'success';
const formatTooltip = (val: number) => val / 100;

const handleAvatarSuccessone: UploadProps['onSuccess'] = (response, uploadFile) => {
	imageUrl.value = URL.createObjectURL(uploadFile.raw!);
	state.img = response.data;
	state.detectStatus = '素材已上传';
	ElMessage.success('图片素材上传成功');
};

const getData = () => {
	request.get('/api/flask/file_names').then((res) => {
		if (res.code == 0) {
			const data = JSON.parse(res.data);
			state.weight_items = data.weight_items.filter((item: any) => item.value.includes(kind.value));
			if (state.weight_items.length && !state.weight_items.some((item: any) => item.value === weight.value)) {
				weight.value = state.weight_items[0].value;
			}
		} else {
			ElMessage.error(res.msg);
		}
	});
};

const normalizeBehavior = (label: string) => {
	if (['靠桌子', '靠桌', '趴桌', '趴桌子'].includes(label)) return 'lie_desk';
	if (['睡觉', '睡眠'].includes(label)) return 'sleep';
	if (label === '低头') return 'head_down';
	if (label === '玩手机') return 'phone';
	return label;
};

const buildPrompt = () => `${state.event.eventId}，检测到${behaviorText(state.event.behaviorType)}，风险等级${riskText(state.event.riskLevel)}，请生成教师沟通建议。`;

const createEventFromLabels = (labels: string[]) => {
	const normalized = labels.map(normalizeBehavior);
	let behaviorType = 'focus';
	let riskLevel = 'normal';
	let reason = '图片素材中主要为课堂专注行为，可作为正常检测样例展示。';
	if (normalized.includes('sleep') || normalized.includes('lie_desk')) {
		behaviorType = normalized.includes('sleep') ? 'sleep' : 'lie_desk';
		riskLevel = 'high';
		reason = `图片素材中检测到${behaviorText(behaviorType)}行为，建议生成教师沟通建议。`;
	} else if (normalized.includes('head_down')) {
		behaviorType = 'head_down';
		riskLevel = 'medium';
		reason = '图片素材中检测到持续低头相关行为，可作为中风险课堂状态进行研判。';
	} else if (normalized.includes('phone')) {
		behaviorType = 'phone';
		riskLevel = 'low';
		reason = '图片素材中检测到玩手机行为，可作为课堂异常行为进行记录。';
	}
	state.event = {
		eventId: '检测事件 #01',
		sourceType: 'image',
		behaviorType,
		riskLevel,
		durationText: '图片单帧',
		reason,
		promptPreview: '',
		advice: riskLevel === 'normal' ? defaultAdvice : '点击“生成沟通建议”后，将展示由AI生成的教师沟通建议。',
		provider: state.provider,
	};
	state.event.promptPreview = buildPrompt();
};

function getBehaviorStats(labels: string[]) {
	const counts = behaviorList.map((type) => labels.filter((label) => label === type).length);
	const total = counts.reduce((a, b) => a + b, 0);
	const percents = counts.map((count) => total ? `${((count / total) * 100).toFixed(1)}%` : '0%');
	return { counts, percents, total };
}

function getFocusStats(labels: string[]) {
	const focusCount = labels.filter((label) => focusList.includes(label)).length;
	const unfocusCount = labels.length - focusCount;
	const total = labels.length;
	return [
		{ value: focusCount, name: '专注', percent: total ? `${((focusCount / total) * 100).toFixed(1)}%` : '0%' },
		{ value: unfocusCount, name: '需关注', percent: total ? `${((unfocusCount / total) * 100).toFixed(1)}%` : '0%' },
	];
}

function renderCharts(labels: string[]) {
	const { counts } = getBehaviorStats(labels);
	const barEl = document.getElementById('barChart');
	const pieEl = document.getElementById('pieChart');
	if (!barEl || !pieEl) return;
	const barChart = echarts.init(barEl);
	barChart.setOption({
		color: ['#2aa79b'],
		tooltip: { trigger: 'axis' },
		grid: { left: 36, right: 10, bottom: 36, top: 20 },
		xAxis: { data: behaviorList, axisLabel: { interval: 0, fontSize: 11 } },
		yAxis: { type: 'value', minInterval: 1 },
		series: [{ name: '数量', type: 'bar', barWidth: 18, data: counts, itemStyle: { borderRadius: [6, 6, 0, 0] } }],
	});

	const pieChart = echarts.init(pieEl);
	const pieData = getFocusStats(labels);
	pieChart.setOption({
		color: ['#2aa79b', '#ef8f62'],
		tooltip: { trigger: 'item' },
		legend: { bottom: 0 },
		series: [{
			name: '课堂状态',
			type: 'pie',
			radius: ['45%', '68%'],
			center: ['50%', '42%'],
			data: pieData.map((item) => ({ value: item.value, name: `${item.name} ${item.percent}` })),
		}],
	});
}

const upData = () => {
	if (!state.img) {
		ElMessage.warning('请先上传课堂图片素材');
		return;
	}
	state.detectStatus = '检测中';
	state.form.weight = weight.value;
	state.form.conf = Number(conf.value) / 100;
	state.form.username = userInfos.value.userName;
	state.form.inputImg = state.img;
	state.form.kind = kind.value;
	state.form.startTime = formatDate(new Date(), 'YYYY-mm-dd HH:MM:SS');
	request.post('/api/flask/predict', state.form).then(async (res) => {
		if (res.code == 0) {
			try {
				const data = JSON.parse(res.data);
				const labels = typeof data.label === 'string' ? JSON.parse(data.label) : data.label;
				state.predictionResult.label = Array.isArray(labels) ? labels.map((item: string) => item.replace(/\\u([\dA-Fa-f]{4})/g, (_, code) => String.fromCharCode(parseInt(code, 16)))) : [];
				state.predictionResult.confidence = data.confidence;
				state.predictionResult.allTime = data.allTime;
				if (data.outImg) imageUrl.value = data.outImg;
				createEventFromLabels(state.predictionResult.label);
				await nextTick();
				renderCharts(state.predictionResult.label);
				state.detectStatus = '检测完成';
				ElMessage.success('图片检测完成');
			} catch (error) {
				state.detectStatus = '解析失败';
				ElMessage.error('检测结果解析失败');
			}
		} else {
			state.detectStatus = '检测失败';
			ElMessage.error(res.msg);
		}
	});
};

const generateAdvice = () => {
	request.post('/api/warningRecords/advice', {
		riskLevel: state.event.riskLevel,
		behaviorType: state.event.behaviorType,
		durationSeconds: 0,
		reason: state.event.reason,
		scene: `课堂图片检测，使用${providerText.value}生成教师沟通建议`,
	}).then((res) => {
		if (res.code == 0) {
			const result = normalizeAdviceResult(res.data, defaultAdvice);
			state.event.advice = result.advice;
			saveInterventionRecord();
			if (result.fallback) {
				ElMessage.warning(result.message || 'MiniMax 暂未返回，已使用本地模板');
			} else {
				ElMessage.success(`MiniMax ${result.model || ''} 辅助干预建议已生成`.trim());
			}
		} else {
			state.event.advice = defaultAdvice;
			ElMessage.warning('建议接口不可用，已使用本地模板');
		}
	}).catch(() => {
		state.event.advice = defaultAdvice;
		ElMessage.warning('建议接口不可用，已使用本地模板');
	});
};

const saveInterventionRecord = () => {
	if (state.event.riskLevel === 'normal') return;
	request.post('/api/warningRecords', {
		videoSource: state.img,
		detectionType: 'image',
		riskLevel: state.event.riskLevel,
		behaviorType: state.event.behaviorType,
		durationSeconds: 0,
		triggerTime: formatDate(new Date(), 'YYYY-mm-dd HH:MM:SS'),
		reason: state.event.reason,
		advice: state.event.advice,
		status: '未处理',
		username: userInfos.value.userName,
	});
};

const exportReport = () => {
	const content = [
		'课堂图片行为检测与AI辅助干预报告',
		`检测来源：图片素材`,
		`检测事件：${state.event.eventId}`,
		`行为类型：${behaviorText(state.event.behaviorType)}`,
		`风险研判：${riskText(state.event.riskLevel)}`,
		`事件摘要：${state.event.reason}`,
		`Prompt：${state.event.promptPreview}`,
		`AI建议：${state.event.advice}`,
	].join('\n');
	const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
	const link = document.createElement('a');
	link.href = URL.createObjectURL(blob);
	link.download = `${state.event.eventId.replace(/\s/g, '')}-图片干预报告.txt`;
	link.click();
	URL.revokeObjectURL(link.href);
};

const behaviorCountList = computed(() => {
	return behaviorList
		.map((type) => ({ name: type, count: state.predictionResult.label.filter((label) => label === type).length }))
		.filter((item) => item.count > 0);
});

const confidenceNumbers = computed(() => {
	const raw = state.predictionResult.confidence;
	if (!raw) return [];
	return String(raw).replace(/\[|\]|"|%/g, '').split(',').map(Number).filter((num) => !Number.isNaN(num));
});

const maxConfidence = computed(() => confidenceNumbers.value.length ? Math.max(...confidenceNumbers.value).toFixed(2) : '--');
const avgConfidence = computed(() => confidenceNumbers.value.length ? (confidenceNumbers.value.reduce((a, b) => a + b, 0) / confidenceNumbers.value.length).toFixed(2) : '--');

onMounted(getData);
</script>

<style scoped lang="scss">
.competition-page {
	width: 100%;
	min-height: 100%;
	background: #f5f8f7;
	color: #1f2f35;
}

.competition-content {
	padding: 20px;
	background: linear-gradient(180deg, #f7fbfa 0%, #f4f7f6 100%);
}

.page-header,
.toolbar-panel,
.image-workspace,
.stats-panel,
.intervention-panel {
	background: rgba(255, 255, 255, 0.96);
	border: 1px solid #e3eeeb;
	border-radius: 8px;
	box-shadow: 0 14px 34px rgba(42, 69, 77, 0.08);
}

.page-header {
	display: flex;
	justify-content: space-between;
	align-items: center;
	gap: 20px;
	padding: 24px 28px;
	margin-bottom: 16px;
}

.page-header h1 {
	margin: 0;
	font-size: 28px;
}

.page-header p {
	margin: 10px 0 0;
	color: #66787d;
}

.eyebrow,
.section-title span,
.box-title {
	color: #2aa79b;
	font-size: 13px;
	font-weight: 700;
	margin-bottom: 7px;
}

.header-status {
	min-width: 140px;
	padding: 14px 16px;
	border-radius: 8px;
	background: #edf8f5;
	display: flex;
	justify-content: space-between;
	color: #2d625c;
}

.toolbar-panel {
	display: flex;
	align-items: center;
	gap: 14px;
	padding: 14px;
	margin-bottom: 16px;
	flex-wrap: wrap;
}

.confidence-control {
	width: 260px;
	display: grid;
	grid-template-columns: 74px 1fr;
	align-items: center;
	gap: 10px;
	color: #66787d;
}

.main-grid {
	display: grid;
	grid-template-columns: minmax(360px, 1fr) minmax(360px, 0.85fr) 360px;
	gap: 16px;
}

.image-workspace,
.stats-panel,
.intervention-panel {
	padding: 18px;
}

.section-title {
	display: flex;
	justify-content: space-between;
	align-items: flex-start;
	gap: 14px;
	margin-bottom: 14px;
}

.section-title h3 {
	margin: 0;
	font-size: 18px;
}

.image-uploader {
	width: 100%;
	height: 610px;
	display: block;
}

:deep(.image-uploader .el-upload) {
	width: 100%;
	height: 100%;
}

.preview-image,
.image-placeholder {
	width: 100%;
	height: 100%;
	border-radius: 8px;
}

.preview-image {
	object-fit: contain;
	background: #172326;
}

.image-placeholder {
	border: 1px dashed #c8d8d4;
	background: #f7faf9;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 10px;
	color: #60737a;
}

.image-placeholder .el-icon {
	font-size: 36px;
	color: #2aa79b;
}

.summary-row {
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	gap: 10px;
}

.summary-row div,
.behavior-list div {
	padding: 12px;
	border-radius: 8px;
	background: #f7faf9;
	display: flex;
	justify-content: space-between;
}

.summary-row span,
.behavior-list span {
	color: #66787d;
}

.behavior-list {
	display: grid;
	grid-template-columns: repeat(2, 1fr);
	gap: 10px;
	margin: 14px 0;
	min-height: 92px;
}

.chart-grid {
	display: grid;
	grid-template-columns: 1fr;
	gap: 12px;
}

.chart-item {
	height: 210px;
	background: #fbfdfc;
	border-radius: 8px;
}

.event-card {
	padding: 16px;
	border-radius: 8px;
	background: linear-gradient(135deg, #f7fffd 0%, #fff8f5 100%);
	border: 1px solid #e4eeeb;
}

.event-id {
	color: #2aa79b;
	font-weight: 700;
	margin-bottom: 10px;
}

.risk-line {
	display: flex;
	align-items: center;
	justify-content: space-between;
	font-size: 18px;
	font-weight: 700;
}

.event-card p,
.prompt-box p,
.advice-box p {
	margin: 10px 0 0;
	line-height: 1.8;
	color: #60737a;
}

.prompt-box,
.advice-box {
	margin-top: 14px;
	padding: 14px;
	border-radius: 8px;
	background: #f7faf9;
	border: 1px solid #e7efec;
}

.intervention-actions {
	display: grid;
	grid-template-columns: 1fr 1fr;
	gap: 10px;
	margin-top: 14px;
}

@media (max-width: 1280px) {
	.main-grid {
		grid-template-columns: 1fr;
	}
}
</style>
