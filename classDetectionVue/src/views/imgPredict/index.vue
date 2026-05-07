<template>
	<div class="system-predict-container layout-padding">
		<div class="system-predict-padding layout-padding-auto layout-padding-view">
			<div class="header">
				<div class="weight">
					<el-select v-model="kind" placeholder="请选择检测种类" size="large" style="width: 200px" @change="getData">
						<el-option v-for="item in state.kind_items" :key="item.value" :label="item.label"
							:value="item.value" />
					</el-select>
				</div>
				<div class="weight">
					<el-select v-model="weight" placeholder="请选择模型" size="large" style="margin-left: 20px;width: 200px">
						<el-option v-for="item in state.weight_items" :key="item.value" :label="item.label"
							:value="item.value" />
					</el-select>
				</div>
				<div class="conf" style="margin-left: 20px;display: flex; flex-direction: row;">
					<div
						style="font-size: 14px;margin-right: 20px;display: flex;justify-content: start;align-items: center;color: #909399;">
						设置最小置信度阈值</div>
					<el-slider v-model="conf" :format-tooltip="formatTooltip" style="width: 300px;" />
				</div>
				<div class="button-section" style="margin-left: 20px">
					<el-button type="primary" @click="upData" class="predict-button">开始预测</el-button>
				</div>
			</div>
  
			<div class="main-content">
  <!-- 左边：图片 -->
  <el-card class="card image-section">
    <el-upload v-model="state.img" ref="uploadFile" class="avatar-uploader"
      action="http://localhost:9999/files/upload" :show-file-list="false"
      :on-success="handleAvatarSuccessone">
      <img v-if="imageUrl" :src="imageUrl" class="avatar" />
      <el-icon v-else class="avatar-uploader-icon">
        <Plus />
      </el-icon>
    </el-upload>
  </el-card>

  <!-- 右边：预测卡片 + 图表 -->
  <div class="right-section">
    <el-card class="result-section" v-if="state.predictionResult.label && state.predictionResult.label.length > 0 ">
      <div class="bottom">
        <div style="display: flex; align-items: center; flex-wrap: wrap; margin-bottom: 12px;">
          <span style="font-weight: bold; margin-right: 12px;">识别结果：</span>
          <div style="display: flex; flex-wrap: wrap; gap: 24px;">
            <span v-for="item in behaviorCountList" :key="item.name" style="font-size: 16px;">
              <span style="font-weight: 500; color: #1976d2;">{{ item.name }}</span>
              <span style="font-weight: bold; color: #333;">{{ item.count }}人</span>
            </span>
          </div>
        </div>
        <div style="margin-bottom: 8px;">
          <span style="font-weight: bold;">预测概率：</span>
          <span style="margin-right: 12px;">最高 {{ maxConfidence }}%</span>
          <span style="margin-right: 12px;">最低 {{ minConfidence }}%</span>
          <span>平均 {{ avgConfidence }}%</span>
        </div>
        <div><span style="font-weight: bold;">总时间：</span>{{ state.predictionResult.allTime }}</div>
      </div>
    </el-card>
    <div class="charts-section">
      <div id="barChart" class="chart-item"></div>
      <div id="pieChart" class="chart-item"></div>
    </div>
  </div>
</div>




	  </div>
	</div>
  </template>
  

<script setup lang="ts" name="personal">
import { reactive, ref, onMounted, nextTick, computed } from 'vue';
import type { UploadInstance, UploadProps } from 'element-plus';
import { ElMessage } from 'element-plus';
import request from '/@/utils/request';
import { Plus } from '@element-plus/icons-vue';
import { useUserInfo } from '/@/stores/userInfo';
import { storeToRefs } from 'pinia';
import { formatDate } from '/@/utils/formatTime';
import axios from 'axios';
import * as echarts from 'echarts';

const imageUrl = ref('');
const conf = ref('');
const weight = ref('');
const kind = ref('');
const uploadFile = ref<UploadInstance>();
const stores = useUserInfo();
const { userInfos } = storeToRefs(stores);
const testlabelList = ['Powdery Mildew', 'Downy Mildew', 'Healthy', 'Black Spot', 'Healthy'];
const behaviorList = ['举手', '阅读', '写作', '玩手机', '低头', '靠桌子'];
const focusList = ['举手', '阅读', '写作'];

const state = reactive({
	weight_items: [] as any,
	kind_items: [
	{
			value: 'class',
			label: '课堂学生行为检测',
		},
	],
	img: '',
	predictionResult: {
		label: [] as string[],
		confidence: '',
		allTime: '',
	},
	form: {
		username: '',
		inputImg: null as any,
		weight: '',
		conf: null as any,
		kind: '',
		startTime: ''
	},
});

const formatTooltip = (val: number) => {
	return val / 100
}

const handleAvatarSuccessone: UploadProps['onSuccess'] = (response, uploadFile) => {
	imageUrl.value = URL.createObjectURL(uploadFile.raw!);
	state.img = response.data;
};

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

function getBehaviorStats(labels: string[]) {
	const counts = behaviorList.map(type => labels.filter(l => l === type).length);
	const total = counts.reduce((a, b) => a + b, 0);
	const percents = counts.map(count => total ? ((count / total) * 100).toFixed(1) + '%' : '0%');
	return { counts, percents, total };
}

function getFocusStats(labels: string[]) {
	const focusCount = labels.filter(l => focusList.includes(l)).length;
	const unfocusCount = labels.length - focusCount;
	const total = labels.length;
	return [
		{ value: focusCount, name: '专注：', percent: total ? ((focusCount / total) * 100).toFixed(1) + '%' : '0%' },
		{ value: unfocusCount, name: '非专注：', percent: total ? ((unfocusCount / total) * 100).toFixed(1) + '%' : '0%' }
	];
}

function renderCharts(labels: string[]) {
	// 柱状图
	const { counts, percents } = getBehaviorStats(labels);
	const barChart = echarts.init(document.getElementById('barChart') as HTMLElement);
	barChart.setOption({
		title: {
			text: '行为统计柱状图',
			left: 'center',
			top: 10,
			textStyle: { fontSize: 18, fontWeight: 'bold', color: '#333' },
			bottom: 20
		},
		tooltip: {
			trigger: 'axis',
			axisPointer: { type: 'shadow' }
		},
		grid: { left: 60, right: 10, bottom: 40, top: 50 },
		xAxis: {
			data: behaviorList,
			axisLabel: {
				fontWeight: 'bold',
				fontSize: 10,
				color: '#333',
				interval: 0
			},
			axisLine: { lineStyle: { color: '#aaa' } }
		},
		yAxis: {
			axisLabel: { fontWeight: 'bold', fontSize: 14, color: '#333' },
			splitLine: { show: false }
		},
		series: [{
			name: '数量',
			type: 'bar',
			barWidth: 32,
			barCategoryGap: '45%',
			data: counts,
			itemStyle: {
				borderRadius: [8, 8, 0, 0],
				color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
					{ offset: 0, color: '#4f8cff' },
					{ offset: 1, color: '#a0cfff' }
				]),
				shadowColor: 'rgba(79,140,255,0.3)',
				shadowBlur: 10
			},
			emphasis: {
				itemStyle: {
					color: '#ffb74d'
				}
			},
			label: {
				show: true,
				position: 'top',
				fontWeight: 'bold',
				fontSize: 10,
				color: '#222',
				backgroundColor: 'rgba(255,255,255,0.8)',
				borderRadius: 4,
				padding: [2, 6],
				formatter: (params: any) => `${params.value} (${percents[params.dataIndex]})`
			}
		}]
	});

	// 饼状图
	const pieData = getFocusStats(labels);
	const pieChart = echarts.init(document.getElementById('pieChart') as HTMLElement);
	const focusCount = pieData[0].value;
	const unfocusCount = pieData[1].value;

	pieChart.setOption({
		title: {
			text: '专注度饼状图',
			left: 'center',
			top: 10,
			textStyle: { fontSize: 18, fontWeight: 'bold', color: '#333' },
			bottom: 20
		},
		tooltip: {
			trigger: 'item',
			formatter: '{b}<br/>数量: {c}'
		},
		legend: {
			orient: 'vertical',
			right: 10,
			top: 40,
			textStyle: { fontWeight: 'bold', fontSize: 14 }
		},
		series: [{
			name: '专注度',
			type: 'pie',
			radius: ['50%', '70%'],
			center: ['50%', '60%'],
			avoidLabelOverlap: false,
			itemStyle: {
				borderRadius: 10,
				borderColor: '#fff',
				borderWidth: 3,
				shadowColor: 'rgba(0,0,0,0.1)',
				shadowBlur: 10
			},
			color: [
				new echarts.graphic.LinearGradient(0, 0, 1, 1, [
					{ offset: 0, color: '#4fc3f7' },
					{ offset: 1, color: '#1976d2' }
				]),
				new echarts.graphic.LinearGradient(0, 0, 1, 1, [
					{ offset: 0, color: '#ffd54f' },
					{ offset: 1, color: '#ff7043' }
				])
			],
			label: {
				show: true,
				position: 'inside',
				fontWeight: 'bold',
				fontSize: 12,
				color: '#000',
				formatter: '{b}{c}'
			},
			labelLine: {
				show: true,
				length: 18,
				length2: 12,
				lineStyle: { color: '#888' }
			},
			data: pieData.map(item => ({
				value: item.value,
				name: `${item.name} (${item.percent})`
			})),
			graphic: {
				type: 'text',
				left: 'center',
				top: 'center',
				style: {
					text: `专注: ${focusCount}非专注: ${unfocusCount}`,
					textAlign: 'center',
					fill: '#333',
					fontSize: 16,
					fontWeight: 'bold'
				}
			}
		}]
	});
}

const upData = () => {
	state.form.weight = weight.value;
	state.form.conf = (parseFloat(conf.value) / 100);
	state.form.username = userInfos.value.userName;
	state.form.inputImg = state.img;
	state.form.kind = kind.value;
	state.form.startTime = formatDate(new Date(), 'YYYY-mm-dd HH:MM:SS');
	console.log(state.form);
	request.post('/api/flask/predict', state.form).then(async (res) => {
		if (res.code == 0) {
			try {
				res.data = JSON.parse(res.data);
				if (typeof res.data.label === 'string') {
					res.data.label = JSON.parse(res.data.label);
				}
				if (Array.isArray(res.data.label)) {
					state.predictionResult.label = res.data.label.map(item => item.replace(/\\u([\dA-Fa-f]{4})/g, (_, code) =>
						String.fromCharCode(parseInt(code, 16))
					));
				} else {
					console.error("res.data.label 不是数组:", res.data.label);
				}
				state.predictionResult.confidence = res.data.confidence;
				state.predictionResult.allTime = res.data.allTime;
				if (res.data.outImg) {
					imageUrl.value = res.data.outImg;
				} else {
					imageUrl.value = imageUrl.value;
				}
				await nextTick();
				renderCharts(state.predictionResult.label);
				console.log(state.predictionResult);
			} catch (error) {
				console.error('解析 JSON 时出错:', error);
			}
			ElMessage.success('预测成功！');
		} else {
			ElMessage.error(res.msg);
		}
	});
};

// 统计每类人数
const behaviorCountList = computed(() => {
	return behaviorList
		.map((type, idx) => ({ name: type, count: state.predictionResult.label.filter(l => l === type).length }))
		.filter(item => item.count > 0);
});
// 概率处理
const maxConfidence = computed(() => {
	if (!state.predictionResult.confidence) return '--';
	let arr = state.predictionResult.confidence;
	if (typeof arr === 'string') {
		const arrNum: number[] = arr.replace(/\[|\]|"|%/g, '').split(',').map(Number).filter(n => !isNaN(n));
		return arrNum.length ? Math.max(...arrNum).toFixed(2) : '--';
	}
	if (Array.isArray(arr)) {
		const arrNum: number[] = (arr as number[]).filter((n: any) => typeof n === 'number' && !isNaN(n));
		return arrNum.length ? Math.max(...arrNum).toFixed(2) : '--';
	}
	return '--';
});
const minConfidence = computed(() => {
	if (!state.predictionResult.confidence) return '--';
	let arr = state.predictionResult.confidence;
	if (typeof arr === 'string') {
		const arrNum: number[] = arr.replace(/\[|\]|"|%/g, '').split(',').map(Number).filter(n => !isNaN(n));
		return arrNum.length ? Math.min(...arrNum).toFixed(2) : '--';
	}
	if (Array.isArray(arr)) {
		const arrNum: number[] = (arr as number[]).filter((n: any) => typeof n === 'number' && !isNaN(n));
		return arrNum.length ? Math.min(...arrNum).toFixed(2) : '--';
	}
	return '--';
});
const avgConfidence = computed(() => {
	if (!state.predictionResult.confidence) return '--';
	let arr = state.predictionResult.confidence;
	if (typeof arr === 'string') {
		const arrNum: number[] = arr.replace(/\[|\]|"|%/g, '').split(',').map(Number).filter(n => !isNaN(n));
		return arrNum.length ? (arrNum.reduce((a, b) => a + b, 0) / arrNum.length).toFixed(2) : '--';
	}
	if (Array.isArray(arr)) {
		const arrNum: number[] = (arr as number[]).filter((n: any) => typeof n === 'number' && !isNaN(n));
		return arrNum.length ? (arrNum.reduce((a, b) => a + b, 0) / arrNum.length).toFixed(2) : '--';
	}
	return '--';
});

onMounted(() => {
	getData();
});
</script>

<style scoped lang="scss">
.system-predict-container {
	width: 100%;
	height: 100%;
	display: flex;
	flex-direction: column;

	.system-predict-padding {
		padding: 15px;
		height: 100%;
	}
	
}

.header {
	width: 100%;
	display: flex;
	justify-content: start;
	align-items: center;
	font-size: 20px;
	margin-bottom: 20px;
	padding: 0 20px;
}

.main-content {
	display: flex;
	gap: 20px;
	height: calc(100vh - 120px);
	padding: 0 20px;
	overflow: hidden;
}

/* 左侧图片区域 */
.image-section {
	width: 50%;
	height: 100%;
	background: #fff;
	border-radius: 8px;
	box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
	overflow: hidden;
}

.avatar-uploader {
	width: 100%;
	height: 100%;
	display: flex;
	justify-content: center;
	align-items: center;
	padding: 20px;
}

.avatar-uploader .avatar {
	width: 800px;
	height: 600px;
	object-fit: contain;
	display: block;
}

.el-icon.avatar-uploader-icon {
	font-size: 28px;
	color: #8c939d;
	width: 800px;
	height: 600px;
	display: flex;
	justify-content: center;
	align-items: center;
	border: 1px dashed #d9d9d9;
	border-radius: 6px;
}

/* 右侧内容区域 */
.right-section {
	width: 50%;
	height: 100%;
	display: flex;
	flex-direction: column;
	gap: 20px;
}

/* 预测结果卡片 */
.result-section {
	min-height: 120px;
	max-height: 160px;
	background: #fff;
	border-radius: 8px;
	box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
	padding: 20px;
	overflow-y: auto;
}

.result-section .bottom {
	display: flex;
	flex-direction: column;
	gap: 15px;
	font-size: 16px;
	color: #333;
}

/* 图表区域 */
.charts-section {
	display: flex;
	flex-direction: row;
	justify-content: space-between;
	align-items: flex-start;
	gap: 8px;
}

.chart-item {
	flex: 1;
	height: 300px;
}

/* 按钮样式 */
.button-section {
	margin-left: 20px;
}

.predict-button {
	min-width: 120px;
}

/* 确保卡片内容溢出时可以滚动 */
.el-card__body {
	height: 100%;
	padding: 0 !important;
	display: flex;
	flex-direction: column;
}

:deep(.el-card__body) {
	height: 100%;
	padding: 0 !important;
	display: flex;
	flex-direction: column;
}
</style>
