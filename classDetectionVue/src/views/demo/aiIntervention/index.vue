<template>
	<DemoShell active="ai" title="AI辅助干预" status="建议可生成">
		<div class="ai-page">
			<section class="panel event-panel">
				<div class="section-title">
					<div>
						<h3>检测事件摘要</h3>
						<p>当前选中事件来自“检测结果”页，页面间保持联动。</p>
					</div>
					<el-select v-model="selectedEventId" style="width: 160px" @change="setCurrentEvent">
						<el-option v-for="item in demoState.events" :key="item.eventId" :label="item.eventId" :value="item.eventId" />
					</el-select>
				</div>

				<div class="event-summary" :class="currentEvent.riskLevel">
					<div>
						<span>事件编号</span>
						<strong>{{ currentEvent.eventId }}</strong>
					</div>
					<div>
						<span>异常行为</span>
						<strong>{{ behaviorText(currentEvent.behaviorType) }}</strong>
					</div>
					<div>
						<span>风险等级</span>
						<strong>风险{{ riskText(currentEvent.riskLevel) }}</strong>
					</div>
					<div>
						<span>持续时长</span>
						<strong>{{ currentEvent.durationText }}</strong>
					</div>
				</div>

				<div class="reason-box">
					<h3>触发依据</h3>
					<p>{{ currentEvent.reason }}</p>
				</div>
			</section>

			<section class="panel prompt-panel">
				<div class="section-title compact">
					<h3>Prompt 构建预览</h3>
					<p>不使用学生姓名，以检测事件和课堂场景为输入。</p>
				</div>
				<el-input v-model="promptText" type="textarea" :rows="8" resize="none" />
				<div class="model-row">
					<span>模型选择</span>
					<el-radio-group v-model="demoState.provider">
						<el-radio-button label="qwen">阿里千问</el-radio-button>
						<el-radio-button label="kimi">Kimi</el-radio-button>
					</el-radio-group>
					<el-button type="primary" :loading="loading" @click="generateAdvice">生成沟通建议</el-button>
				</div>
			</section>

			<section class="panel advice-panel">
				<div class="section-title compact">
					<h3>建议生成结果</h3>
					<p>建议内容定位为教师沟通辅助，不作为心理诊断。</p>
				</div>
				<div class="advice-card">
					<el-icon><ChatDotRound /></el-icon>
					<p>{{ currentEvent.advice }}</p>
				</div>
				<div class="action-row">
					<el-button type="primary" @click="router.push('/interventionReport')">同步到报告</el-button>
					<el-button @click="copyAdvice">复制建议</el-button>
				</div>
			</section>

			<aside class="panel history-panel">
				<div class="section-title compact">
					<h3>生成历史</h3>
					<p>最近生成的AI辅助干预建议。</p>
				</div>
				<div class="history-list">
					<button v-for="item in demoState.aiHistory" :key="item.eventId" @click="setCurrentEvent(item.eventId)">
						<span>{{ item.eventId }} · {{ behaviorText(item.behaviorType) }}</span>
						<em>{{ item.provider === 'kimi' ? 'Kimi' : '阿里千问' }} · 风险{{ riskText(item.riskLevel) }}</em>
					</button>
				</div>
			</aside>
		</div>
	</DemoShell>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { ChatDotRound } from '@element-plus/icons-vue';
import DemoShell from '/@/views/demo/components/DemoShell.vue';
import { applyAdvice, behaviorText, buildPrompt, currentEvent, demoState, fallbackAdvice, riskText, setCurrentEvent } from '/@/views/demo/demoState';
import request from '/@/utils/request';

const router = useRouter();
const loading = ref(false);
const selectedEventId = ref(currentEvent.value.eventId);
const promptText = ref(buildPrompt(currentEvent.value));

watch(currentEvent, (event) => {
	selectedEventId.value = event.eventId;
	promptText.value = buildPrompt(event);
}, { deep: true });

const providerLabel = computed(() => demoState.provider === 'kimi' ? 'Kimi' : '阿里千问');

function generateAdvice() {
	loading.value = true;
	request.post('/api/warningRecords/advice', {
		riskLevel: currentEvent.value.riskLevel,
		behaviorType: currentEvent.value.behaviorType,
		durationText: currentEvent.value.durationText,
		reason: currentEvent.value.reason,
		scene: promptText.value,
		provider: demoState.provider,
	}).then((res) => {
		const advice = res?.code === 0 ? (res.data || fallbackAdvice(currentEvent.value)) : fallbackAdvice(currentEvent.value);
		applyAdvice(advice, demoState.provider);
		ElMessage.success(`${providerLabel.value} 建议已生成`);
	}).catch(() => {
		applyAdvice(fallbackAdvice(currentEvent.value), demoState.provider);
		ElMessage.warning('AI接口暂不可用，已使用本地模板建议');
	}).finally(() => {
		loading.value = false;
	});
}

function copyAdvice() {
	navigator.clipboard?.writeText(currentEvent.value.advice);
	ElMessage.success('建议文本已复制');
}
</script>

<style scoped lang="scss">
.ai-page {
	height: 100%;
	display: grid;
	grid-template-columns: minmax(0, 1fr) 360px;
	grid-template-rows: auto auto minmax(0, 1fr);
	gap: 16px;
	overflow: hidden;
}

.panel {
	border-radius: 8px;
	background: rgba(255, 255, 255, .97);
	border: 1px solid #dde8e5;
	box-shadow: 0 14px 34px rgba(23, 42, 46, .07);
	padding: 16px;
}

.history-panel {
	grid-column: 2;
	grid-row: 1 / 4;
	overflow-y: auto;
}

.section-title {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 16px;
	margin-bottom: 14px;
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

.event-summary {
	display: grid;
	grid-template-columns: repeat(4, 1fr);
	gap: 12px;
}

.event-summary div {
	padding: 16px;
	border-radius: 8px;
	background: #f7fbfa;
	border: 1px solid #e2ece9;
}

.event-summary.high div {
	background: #fff4f2;
	border-color: #f4d6d2;
}

.event-summary.medium div {
	background: #fffaf0;
	border-color: #eee2c7;
}

.event-summary span {
	display: block;
	color: #7a8a8f;
	font-size: 12px;
}

.event-summary strong {
	display: block;
	margin-top: 8px;
	font-size: 20px;
}

.reason-box {
	margin-top: 14px;
	padding: 14px;
	border-radius: 8px;
	background: #fbfdfc;
	border: 1px solid #e2ece9;
}

.reason-box h3 {
	margin: 0 0 8px;
	font-size: 16px;
}

.reason-box p,
.advice-card p {
	margin: 0;
	color: #53666b;
	line-height: 1.8;
}

.model-row {
	display: flex;
	align-items: center;
	gap: 16px;
	margin-top: 14px;
}

.model-row span {
	color: #516166;
	font-weight: 700;
}

.advice-card {
	display: grid;
	grid-template-columns: 34px minmax(0, 1fr);
	gap: 12px;
	padding: 18px;
	border-radius: 8px;
	background: #f1fbf8;
	border: 1px solid #cdebe4;
}

.advice-card .el-icon {
	margin-top: 4px;
	color: #008f87;
	font-size: 24px;
}

.action-row {
	display: flex;
	gap: 10px;
	margin-top: 14px;
}

.history-list {
	display: grid;
	gap: 10px;
}

.history-list button {
	padding: 14px;
	border-radius: 8px;
	border: 1px solid #e2ece9;
	background: #fbfdfc;
	text-align: left;
	cursor: pointer;
}

.history-list button:hover {
	border-color: #008f87;
	background: #f1fbf8;
}

.history-list span,
.history-list em {
	display: block;
}

.history-list span {
	font-weight: 800;
	color: #172327;
}

.history-list em {
	margin-top: 8px;
	color: #6b7b80;
	font-style: normal;
	font-size: 13px;
}

@media (max-width: 1040px) {
	.ai-page {
		height: auto;
		grid-template-columns: 1fr;
		grid-template-rows: none;
		overflow: visible;
	}

	.history-panel {
		grid-column: auto;
		grid-row: auto;
		overflow: visible;
	}

	.event-summary {
		grid-template-columns: repeat(2, 1fr);
	}
}
</style>
