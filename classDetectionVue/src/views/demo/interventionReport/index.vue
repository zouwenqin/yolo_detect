<template>
	<DemoShell active="report" title="干预报告" status="报告已生成">
		<div class="report-page">
			<section class="panel report-preview">
				<div class="report-header">
					<div>
						<span>课堂行为检测与AI辅助干预报告</span>
						<h2>{{ demoState.material.sourceName }}</h2>
					</div>
					<div class="report-meta">
						<p>生成时间：2026-05-11</p>
						<p>报告类型：比赛演示版</p>
					</div>
				</div>

				<div class="overview-grid">
					<div>
						<span>检测事件</span>
						<strong>{{ demoState.events.length }}</strong>
					</div>
					<div>
						<span>最高风险</span>
						<strong>风险{{ riskText(maxRisk) }}</strong>
					</div>
					<div>
						<span>重点行为</span>
						<strong>{{ behaviorText(currentEvent.behaviorType) }}</strong>
					</div>
					<div>
						<span>AI建议</span>
						<strong>{{ demoState.aiHistory.length }}</strong>
					</div>
				</div>

				<section class="report-section">
					<h3>一、检测概况</h3>
					<p>系统基于录制课堂视频素材完成行为识别和事件研判。本演示版不进行学生实名追踪，输出结果以“检测事件”为单位，用于辅助教师理解课堂状态。</p>
				</section>

				<section class="report-section">
					<h3>二、重点事件</h3>
					<div class="event-line">
						<el-tag :type="riskTagType(currentEvent.riskLevel)">风险{{ riskText(currentEvent.riskLevel) }}</el-tag>
						<strong>{{ currentEvent.eventId }} · {{ behaviorText(currentEvent.behaviorType) }} · {{ currentEvent.durationText }}</strong>
					</div>
					<p>{{ currentEvent.reason }}</p>
				</section>

				<section class="report-section">
					<h3>三、AI沟通建议</h3>
					<p>{{ currentEvent.advice }}</p>
				</section>

				<section class="report-section">
					<h3>四、后续跟进建议</h3>
					<ul>
						<li>建议教师先以关怀身体状态和学习压力为切入点，避免当众批评。</li>
						<li>若同类异常行为在后续课堂反复出现，可同步辅导员或心理老师进行跟进。</li>
						<li>报告仅作为课堂行为研判与沟通辅助，不作为心理诊断结论。</li>
					</ul>
				</section>
			</section>

			<aside class="panel report-actions">
				<div class="section-title">
					<h3>报告操作</h3>
					<p>演示阶段导出为本地文本/Word兼容文件，便于现场验收。</p>
				</div>
				<el-button type="primary" @click="downloadReport('txt')">导出报告文本</el-button>
				<el-button @click="downloadReport('doc')">导出Word兼容文件</el-button>
				<el-button @click="router.push('/aiIntervention')">返回AI辅助干预</el-button>

				<div class="event-picker">
					<h3>报告事件</h3>
					<button v-for="item in demoState.events" :key="item.eventId" :class="{ active: item.eventId === currentEvent.eventId }" @click="setCurrentEvent(item.eventId)">
						<span>{{ item.eventId }} · {{ behaviorText(item.behaviorType) }}</span>
						<em>风险{{ riskText(item.riskLevel) }} · {{ item.durationText }}</em>
					</button>
				</div>
			</aside>
		</div>
	</DemoShell>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import DemoShell from '/@/views/demo/components/DemoShell.vue';
import { behaviorText, currentEvent, demoState, exportReportText, riskTagType, riskText, setCurrentEvent } from '/@/views/demo/demoState';

const router = useRouter();

const maxRisk = computed(() => {
	if (demoState.events.some((item) => item.riskLevel === 'high')) return 'high';
	if (demoState.events.some((item) => item.riskLevel === 'medium')) return 'medium';
	if (demoState.events.some((item) => item.riskLevel === 'low')) return 'low';
	return 'normal';
});

function downloadReport(type: 'txt' | 'doc') {
	const blob = new Blob([exportReportText()], { type: 'text/plain;charset=utf-8' });
	const link = document.createElement('a');
	link.href = URL.createObjectURL(blob);
	link.download = `${currentEvent.value.eventId}-干预报告.${type}`;
	link.click();
	URL.revokeObjectURL(link.href);
}
</script>

<style scoped lang="scss">
.report-page {
	height: 100%;
	display: grid;
	grid-template-columns: minmax(0, 1fr) 340px;
	gap: 16px;
	overflow: hidden;
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
		overflow: visible;
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
