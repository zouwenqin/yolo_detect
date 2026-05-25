<template>
	<DemoShell active="report" title="教师跟进记录" :status="selectedClue ? '记录可导出' : '等待检测结果'">
		<div class="report-page">
			<DetectionSourceSelector v-model="selectedSource" :records="warningRecords" :history-records="videoRecords" @change="handleSourceChange" />

			<section class="panel report-preview">
				<div class="report-header">
					<div>
						<span>课堂异常行为检测与教师跟进记录</span>
						<h2>{{ demoState.material.sourceName }}</h2>
					</div>
					<div class="report-meta">
						<p>生成时间：{{ reportDate }}</p>
						<p>用途：教师沟通辅助</p>
					</div>
				</div>

				<template v-if="selectedClue">
					<div class="overview-grid">
						<div>
							<span>异常线索</span>
							<strong>{{ focusClues.length }}</strong>
						</div>
						<div>
							<span>最高风险</span>
							<strong>风险{{ riskText(maxRisk) }}</strong>
						</div>
						<div>
							<span>重点行为</span>
							<strong>{{ behaviorText(selectedClue.behaviorType) }}</strong>
						</div>
						<div>
							<span>AI建议</span>
							<strong>{{ selectedClue.advice ? '已生成' : '待生成' }}</strong>
						</div>
					</div>

					<section class="report-section">
						<h3>一、检测摘要</h3>
						<p>系统基于录制课堂视频素材完成异常行为识别，并将重复检测记录聚合为重点线索。本次报告围绕最需要教师关注的课堂异常行为展开。</p>
					</section>

					<section class="report-section">
						<h3>二、重点事件</h3>
						<div class="event-line">
							<el-tag :type="riskTagType(selectedClue.riskLevel)">风险{{ riskText(selectedClue.riskLevel) }}</el-tag>
							<strong>{{ behaviorText(selectedClue.behaviorType) }} · {{ selectedClue.durationText }} · {{ selectedClue.eventCount }} 条同类记录</strong>
						</div>
						<p>{{ selectedClue.evidenceText }}</p>
					</section>

					<section class="report-section">
						<h3>三、风险说明</h3>
						<p>{{ selectedClue.reason }}</p>
						<p>该风险来自持续时长、行为类型和课堂场景的综合提示，仅用于提醒教师进一步观察与沟通确认。</p>
					</section>

					<section class="report-section">
						<h3>四、教师沟通建议</h3>
						<p>{{ selectedClue.advice || '建议先在 AI 辅助干预页面生成沟通建议，再同步到本记录。' }}</p>
					</section>

					<section class="report-section">
						<h3>五、后续跟进</h3>
						<ul>
							<li>课后单独、温和询问学生近期身体状态、睡眠和课程压力。</li>
							<li>不要在课堂公开点名或给学生贴心理标签。</li>
							<li>若同类线索反复出现，可同步辅导员或心理老师做进一步支持。</li>
							<li>本记录仅作课堂行为研判和沟通辅助，不作为心理诊断结论。</li>
						</ul>
					</section>
				</template>
				<el-empty v-else description="请先完成视频检测，系统将根据真实异常线索生成教师跟进记录">
					<el-button type="primary" @click="router.push('/videoPredict')">去视频检测</el-button>
				</el-empty>
			</section>

			<aside class="panel report-actions">
				<div class="section-title">
					<h3>记录操作</h3>
					<p>导出内容面向教师后续跟进，保留检测依据、沟通建议和非诊断说明。</p>
				</div>
				<el-button type="primary" :disabled="!selectedClue" @click="downloadReport('txt')">导出教师跟进记录</el-button>
				<el-button :disabled="!selectedClue" @click="downloadReport('doc')">导出 Word 兼容文件</el-button>
				<el-button @click="router.push('/aiIntervention')">返回 AI 沟通助手</el-button>

				<div class="event-picker">
					<h3>报告线索</h3>
					<button
						v-for="item in topFocusClues"
						:key="item.clueId"
						:class="{ active: item.eventIds.includes(demoState.selectedEventId) }"
						@click="setCurrentEvent(item.eventId)"
					>
						<span>{{ behaviorText(item.behaviorType) }}</span>
						<em>风险{{ riskText(item.riskLevel) }} · {{ item.durationText }}</em>
					</button>
				</div>
			</aside>
		</div>
	</DemoShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import DemoShell from '/@/views/demo/components/DemoShell.vue';
import DetectionSourceSelector from '/@/views/demo/components/DetectionSourceSelector.vue';
import { behaviorText, currentFocusClue, demoState, exportReportText, focusClues, riskTagType, riskText, setCurrentEvent, sourceNameKey, syncWarningRecords, topFocusClues } from '/@/views/demo/demoState';
import request from '/@/utils/request';

const router = useRouter();
const selectedSource = ref('');
const warningRecords = ref<any[]>([]);
const videoRecords = ref<any[]>([]);
const selectedClue = computed(() => currentFocusClue.value);
const reportDate = computed(() => new Date().toLocaleDateString());
const maxRisk = computed(() => topFocusClues.value[0]?.riskLevel || 'normal');

function downloadReport(type: 'txt' | 'doc') {
	const blob = new Blob([exportReportText()], { type: 'text/plain;charset=utf-8' });
	const link = document.createElement('a');
	link.href = URL.createObjectURL(blob);
	link.download = `${selectedClue.value?.eventId || '课堂异常'}-教师跟进记录.${type}`;
	link.click();
	URL.revokeObjectURL(link.href);
}

function handleSourceChange(option: any) {
	if (!option || !warningRecords.value.length) return;
	selectedSource.value = option.value;
	syncWarningRecords(warningRecords.value, option.inputVideo || option.label);
	if (topFocusClues.value.length) setCurrentEvent(topFocusClues.value[0].eventId);
}

async function loadWarningRecords() {
	try {
		const [warningRes, videoRes] = await Promise.all([
			request.get('/api/warningRecords/all'),
			request.get('/api/videoRecords/all'),
		]);
		if (videoRes?.code == 0 && Array.isArray(videoRes.data)) videoRecords.value = videoRes.data;
		if (warningRes?.code == 0 && Array.isArray(warningRes.data)) {
			warningRecords.value = warningRes.data;
			syncWarningRecords(warningRes.data);
			selectedSource.value = sourceNameKey(demoState.material.sourceName);
		}
	} catch (error) {}
}

onMounted(loadWarningRecords);
</script>

<style scoped lang="scss">
.report-page {
	height: 100%;
	display: grid;
	grid-template-columns: minmax(0, 1fr) 340px;
	grid-template-rows: auto minmax(0, 1fr);
	gap: 16px;
	overflow: hidden;
}

.source-panel {
	grid-column: 1 / 3;
}

.panel {
	border-radius: 8px;
	background: rgba(255, 255, 255, .97);
	border: 1px solid #dde8e5;
	box-shadow: 0 14px 34px rgba(23, 42, 46, .07);
}

.report-preview {
	overflow-y: auto;
	padding: 28px;
}

.report-actions {
	padding: 18px;
	overflow-y: auto;
}

.report-header {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 20px;
	padding-bottom: 20px;
	border-bottom: 1px solid #e2ece9;
}

.report-header span {
	color: #008f87;
	font-weight: 800;
}

.report-header h2 {
	margin: 10px 0 0;
	font-size: 28px;
}

.report-meta p {
	margin: 0 0 8px;
	color: #6b7b80;
}

.overview-grid {
	display: grid;
	grid-template-columns: repeat(4, 1fr);
	gap: 12px;
	margin: 20px 0;
}

.overview-grid div {
	padding: 16px;
	border-radius: 8px;
	border: 1px solid #e2ece9;
	background: #f7fbfa;
}

.overview-grid span {
	display: block;
	color: #7a8a8f;
	font-size: 12px;
}

.overview-grid strong {
	display: block;
	margin-top: 8px;
	font-size: 22px;
}

.report-section {
	padding: 18px 0;
	border-top: 1px solid #eef4f2;
}

.report-section h3 {
	margin: 0 0 12px;
	font-size: 18px;
}

.report-section p,
.report-section li {
	color: #4f6267;
	line-height: 1.85;
}

.event-line {
	display: flex;
	align-items: center;
	gap: 12px;
	margin-bottom: 10px;
}

.report-actions .el-button {
	width: 100%;
	margin: 0 0 12px;
}

.section-title h3,
.event-picker h3 {
	margin: 0 0 8px;
	font-size: 18px;
}

.section-title p {
	margin: 0 0 18px;
	color: #6b7b80;
	line-height: 1.7;
}

.event-picker {
	margin-top: 18px;
	padding-top: 18px;
	border-top: 1px solid #e2ece9;
}

.event-picker button {
	width: 100%;
	margin-top: 10px;
	padding: 14px;
	border-radius: 8px;
	border: 1px solid #e2ece9;
	background: #fbfdfc;
	text-align: left;
	cursor: pointer;
}

.event-picker button.active,
.event-picker button:hover {
	border-color: #008f87;
	background: #f1fbf8;
}

.event-picker span,
.event-picker em {
	display: block;
}

.event-picker span {
	font-weight: 800;
}

.event-picker em {
	margin-top: 8px;
	color: #6b7b80;
	font-style: normal;
}

@media (max-width: 980px) {
	.report-page {
		height: auto;
		grid-template-columns: 1fr;
		grid-template-rows: none;
		overflow: visible;
	}

	.source-panel {
		grid-column: auto;
	}

	.report-preview,
	.report-actions {
		overflow: visible;
	}

	.overview-grid {
		grid-template-columns: repeat(2, 1fr);
	}
}
</style>
