<template>
	<div class="system-predict-container layout-padding">
		<div class="system-predict-padding layout-padding-auto layout-padding-view">
			<div class="header">
				<div class="kind">
					<el-select v-model="kind" placeholder="请选择检测种类" size="large" style="width: 180px" @change="getData">
						<el-option v-for="item in state.kind_items" :key="item.value" :label="item.label"
							:value="item.value" />
					</el-select>
				</div>
				<div class="weight">
					<el-select v-model="weight" placeholder="请选择模型" size="large" style="margin-left: 20px;width: 180px">
						<el-option v-for="item in state.weight_items" :key="item.value" :label="item.label"
							:value="item.value" />
					</el-select>
				</div>
				<div class="conf" style="margin-left: 20px;display: flex; flex-direction: row;">
					<div
						style="font-size: 14px;margin-right: 20px;display: flex;justify-content: start;align-items: center;color: #909399;">
						设置最小置信度阈值</div>
					<el-slider v-model="conf" :format-tooltip="formatTooltip" style="width: 280px;" />
				</div>
				<div class="button-section" style="margin-left: 20px">
					<el-button type="primary" @click="start" class="predict-button">开始录制</el-button>
				</div>
                <div class="button-section" style="margin-left: 20px">
					<el-button type="primary" @click="stop" class="predict-button">结束录制</el-button>
				</div>
				<div class="demo-progress" v-if="state.isShow">
					<el-progress :text-inside="true" :stroke-width="20" :percentage=state.percentage style="width: 380px;">
						<span>{{ state.type_text }} {{ state.percentage }}%</span>
					</el-progress>
				</div>
			</div>
			<div class="cards" ref="cardsContainer">
				<img v-if="state.cameraisShow" class="video" :src="state.video_path">
				<div id="focusLineChart" class="focus-line-chart"></div>
				<div class="warning-panel">
					<div class="warning-title">课堂心理风险实时预警</div>
					<div class="risk-badge" :class="'risk-' + state.warningState.riskLevel">{{ riskText(state.warningState.riskLevel) }}</div>
					<div class="warning-row">
						<span>触发原因</span>
						<strong>{{ state.warningState.reason || '暂无异常行为达到预警阈值' }}</strong>
					</div>
					<div class="duration-grid">
						<div v-for="item in durationItems" :key="item.key">
							<label>{{ item.label }}</label>
							<b>{{ item.value }}s</b>
						</div>
					</div>
					<div class="advice-box">
						<div class="advice-title">教师干预建议</div>
						<p>{{ state.latestAdvice || '检测到持续异常行为后，将自动生成非诊断性的关怀建议。' }}</p>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>


<script setup lang="ts">
import { computed, reactive, ref, onMounted, nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import request from '/@/utils/request';
import { useUserInfo } from '/@/stores/userInfo';
import { storeToRefs } from 'pinia';
import type { UploadInstance, UploadProps } from 'element-plus';
import { SocketService } from '/@/utils/socket';
import { formatDate } from '/@/utils/formatTime';
import * as echarts from 'echarts';

const stores = useUserInfo();
const conf = ref('');
const kind = ref('');
const weight = ref('');
const { userInfos } = storeToRefs(stores);

const state = reactive({
	weight_items: [] as any,
	kind_items: [
		{
			value: 'class',
			label: '课堂学生行为检测',
		},
	],
	data: {} as any,
	video_path: '',
	type_text: "正在保存",
	percentage: 50,
	isShow: false,
	cameraisShow: false,
	latestAdvice: '',
	warningState: {
		riskLevel: 'normal',
		reason: '',
		durations: {
			sleep: 0,
			lie_desk: 0,
			head_down: 0,
			phone: 0,
		},
		warning: null as any,
	},
	form: {
		username: '',
		weight: '',
		conf: null as any,
		kind: '',
		startTime: ''
	},
});

const socketService = new SocketService();

const focusLineChart = ref<any>(null);
const focusData = ref<number[]>([]);
const unfocusData = ref<number[]>([]);
const timeData = ref<string[]>([]);

function initFocusLineChart() {
	focusLineChart.value = echarts.init(document.getElementById('focusLineChart') as HTMLElement);
	focusLineChart.value.setOption({
		title: { text: '专注度实时曲线', left: 'center', top: 10, textStyle: { fontSize: 16, fontWeight: 'bold' }, bottom: 20 },
		tooltip: { trigger: 'axis' },
		legend: { data: ['专注度', '非专注度'], top: 40 },
		grid: { left: 40, right: 20, bottom: 40, top: 70 },
		xAxis: { type: 'category', data: timeData.value, boundaryGap: false },
		yAxis: { type: 'value', min: 0, max: 1, axisLabel: { formatter: '{value}' } },
		series: [
			{
				name: '专注度',
				type: 'line',
				data: focusData.value,
				smooth: true,
				symbol: 'circle',
				showSymbol: false,
				lineStyle: { width: 3, color: '#1976d2' },
				itemStyle: { color: '#1976d2' }
			},
			{
				name: '非专注度',
				type: 'line',
				data: unfocusData.value,
				smooth: true,
				symbol: 'circle',
				showSymbol: false,
				lineStyle: { width: 3, color: '#ff7043' },
				itemStyle: { color: '#ff7043' }
			}
		]
	});
}

function updateFocusLineChart(focus: number, unfocus: number) {
	const now = new Date();
	const label = now.toLocaleTimeString().slice(3, 8); // 只显示分:秒
	timeData.value.push(label);
	focusData.value.push(focus);
	unfocusData.value.push(unfocus);
	if (timeData.value.length > 20) {
		timeData.value.shift();
		focusData.value.shift();
		unfocusData.value.shift();
	}
	if (!focusLineChart.value) return;
	focusLineChart.value.setOption({
		xAxis: { data: timeData.value },
		series: [
			{ data: focusData.value },
			{ data: unfocusData.value }
		]
	});
}

function onFrameDetect(labels: string[]) {
	const focusList = ['hand-raising', 'reading', 'writing', 'raise_hand', 'read', 'write'];
	const total = labels.length;
	const focusCount = labels.filter(l => focusList.includes(l)).length;
	const unfocusCount = total - focusCount;
	const focusRatio = total ? focusCount / total : 0;
	const unfocusRatio = total ? unfocusCount / total : 0;
	updateFocusLineChart(focusRatio, unfocusRatio);
}

socketService.on('message', (data) => {
	if (data && data.warningState) {
		state.warningState = data.warningState;
		if (data.warningState.warning) {
			state.latestAdvice = data.warningState.warning.advice || '';
			ElMessage.warning(data.warningState.warning.reason || '课堂异常行为达到预警阈值');
		}
	}
	if (data && data.labels && Array.isArray(data.labels)) {
		onFrameDetect(data.warningState?.normalizedLabels || data.labels);
	} else if (data && data.data) {
		ElMessage.success(data.data);
	}
});

const riskText = (risk: string) => {
	const map: any = {
		normal: '正常',
		low: '低风险',
		medium: '中风险',
		high: '高风险',
	};
	return map[risk] || '正常';
};

const durationItems = computed(() => {
	const durations = state.warningState.durations || {} as any;
	return [
		{ key: 'sleep', label: '睡觉', value: durations.sleep || 0 },
		{ key: 'lie_desk', label: '趴桌', value: durations.lie_desk || 0 },
		{ key: 'head_down', label: '低头', value: durations.head_down || 0 },
		{ key: 'phone', label: '手机', value: durations.phone || 0 },
	];
});

const formatTooltip = (val: number) => {
	return val / 100
}

socketService.on('progress', (data) => {
	state.percentage = parseInt(data);
	if (parseInt(data) < 100) {
		state.isShow = true;
	} else {
		//两秒后隐藏进度条
		ElMessage.success("保存成功！");
		setTimeout(() => {
			state.isShow = false;
			state.percentage = 0;
		}, 2000);
	}
	console.log('Received message:', data);
});

const getData = () => {
	request.get('/api/flask/file_names').then((res) => {
		if (res.code == 0) {
			res.data = JSON.parse(res.data);
			state.weight_items = res.data.weight_items.filter(item => item.value.includes(kind.value));
		} else {
			ElMessage.error(res.msg);
		}
	});
};


const start = () => {
	state.form.weight = weight.value;
	state.form.kind = kind.value;
	state.form.conf = (parseFloat(conf.value)/100);
	state.form.username = userInfos.value.userName;
	state.form.startTime = formatDate(new Date(), 'YYYY-mm-dd HH:MM:SS');
	console.log(state.form);
	const queryParams = new URLSearchParams(state.form).toString();
	state.cameraisShow = true
	state.video_path = `/flask/predictCamera?${queryParams}`;
};

const stop = () => {
	request.get('/flask/stopCamera').then((res) => {
		if (res.code == 0) {
			res.data = JSON.parse(res.data);
			console.log(res.data);
			state.weight_items = res.data.weight_items;
		} else {
			ElMessage.error(res.msg);
		}
	});
	state.cameraisShow = false
};

onMounted(() => {
	getData();
	nextTick(() => {
		initFocusLineChart();
	});
});
</script>

<style scoped lang="scss">
.system-predict-container {
	width: 100%;
	height: 100%;
	display: flex;
	flex-direction: column;
	// background: radial-gradient(circle, #d3e3f1 0%, #ffffff 100%);

	.system-predict-padding {
		padding: 15px;
		background: radial-gradient(circle, #d3e3f1 0%, #ffffff 100%);

		.el-table {
			flex: 1;
		}
	}
}

.header {
	width: 100%;
	height: 5%;
	display: flex;
	justify-content: start;
	align-items: center;
	font-size: 20px;
}

.cards {
	width: 100%;
	height: 95%;
	border-radius: 5px;
	margin-top: 15px;
	padding: 0px;
	overflow: hidden;
	display: flex;
	justify-content: center;
	align-items: center;
	background: radial-gradient(circle, #d3e3f1 0%, #ffffff 100%);
	/* 防止视频溢出 */
}

.video {
	width: 100%;
	max-height: 100%;
	/* 限制视频最大高度不超过父元素高度 */
	height: auto;
	object-fit: contain;
}

.button-section {
	display: flex;
	justify-content: center;
}

.predict-button {
	width: 100%;
	/* 按钮宽度填满 */
}

.demo-progress .el-progress--line {
	margin-left: 20px;
	width: 600px;
}

.focus-line-chart {
	width: 480px;
	height: 360px;
	margin-left: 32px;
	background: #fff;
	border-radius: 8px;
	box-shadow: 0 2px 12px 0 rgba(0,0,0,0.08);
	display: flex;
	align-items: center;
	justify-content: center;
}

.warning-panel {
	width: 360px;
	min-height: 360px;
	margin-left: 24px;
	padding: 18px;
	background: #fff;
	border-radius: 8px;
	box-shadow: 0 2px 12px 0 rgba(0,0,0,0.08);
	color: #303133;
}

.warning-title {
	font-size: 18px;
	font-weight: 700;
	margin-bottom: 12px;
}

.risk-badge {
	display: inline-flex;
	align-items: center;
	height: 32px;
	padding: 0 14px;
	border-radius: 16px;
	font-weight: 700;
	margin-bottom: 14px;
}

.risk-normal { background: #ecf5ff; color: #409eff; }
.risk-low { background: #f4f4f5; color: #606266; }
.risk-medium { background: #fdf6ec; color: #e6a23c; }
.risk-high { background: #fef0f0; color: #f56c6c; }

.warning-row {
	display: flex;
	flex-direction: column;
	gap: 6px;
	font-size: 14px;
	margin-bottom: 14px;
}

.warning-row span,
.duration-grid label {
	color: #909399;
}

.duration-grid {
	display: grid;
	grid-template-columns: repeat(2, 1fr);
	gap: 10px;
	margin-bottom: 14px;
}

.duration-grid div {
	padding: 10px;
	background: #f7f9fc;
	border-radius: 8px;
	display: flex;
	justify-content: space-between;
}

.advice-box {
	padding: 12px;
	background: #f7f9fc;
	border-radius: 8px;
	line-height: 1.7;
}

.advice-title {
	font-weight: 700;
	margin-bottom: 6px;
}

.advice-box p {
	margin: 0;
}
</style>
