<template>
	<DemoShell active="ai" title="定性与沟通助手" :status="selectedClue ? '建议可生成' : '等待检测结果'">
		<div class="ai-page">
			<DetectionSourceSelector v-model="selectedSource" :records="warningRecords" :history-records="videoRecords" @change="handleSourceChange" />

			<section class="panel event-panel">
				<div class="section-title">
					<div>
						<h3>异常行为摘要</h3>
						<p>围绕当前重点线索生成非诊断式沟通建议，帮助老师判断如何开口，而不是替代老师下结论。</p>
					</div>
					<el-select v-model="selectedEventId" style="width: 190px" :disabled="!topFocusClues.length" @change="setCurrentEvent">
						<el-option v-for="item in topFocusClues" :key="item.clueId" :label="`${behaviorText(item.behaviorType)} · ${item.durationText}`" :value="item.eventId" />
					</el-select>
				</div>

				<template v-if="selectedClue">
					<div class="event-summary" :class="selectedClue.riskLevel">
						<div>
							<span>重点线索</span>
							<strong>{{ behaviorText(selectedClue.behaviorType) }}</strong>
						</div>
						<div>
							<span>风险等级</span>
							<strong>风险{{ riskText(selectedClue.riskLevel) }}</strong>
						</div>
						<div>
							<span>最长持续</span>
							<strong>{{ selectedClue.durationText }}</strong>
						</div>
						<div>
							<span>同类记录</span>
							<strong>{{ selectedClue.eventCount }} 条</strong>
						</div>
					</div>
					<div class="reason-box">
						<h3>证据依据</h3>
						<p>{{ selectedClue.evidenceText }}</p>
					</div>
				</template>
				<el-empty v-else description="请先完成视频检测，AI 助手会基于真实异常线索生成建议">
					<el-button type="primary" @click="router.push('/videoPredict')">去视频检测</el-button>
				</el-empty>
			</section>

			<section class="panel judgement-panel">
				<div class="section-title compact">
					<h3>可能原因研判</h3>
					<p>{{ reasonPanelHint }}</p>
				</div>
				<div v-if="reasonCards.length" class="reason-grid">
					<div v-for="item in reasonCards" :key="item.title">
						<strong>{{ item.title }}</strong>
						<p>{{ item.desc }}</p>
					</div>
				</div>
				<el-empty v-else description="点击“生成沟通建议”后，由后端携带检测证据调用大模型生成可能原因。" />
			</section>

			<section class="panel advice-panel">
				<div class="section-title compact">
					<h3>沟通建议</h3>
					<p>{{ advicePanelHint }}</p>
				</div>
				<div class="ai-source-row">
					<el-tag :type="sourceTagType" size="small">{{ sourceLabel }}</el-tag>
					<span>{{ sourceDetail }}</span>
				</div>
				<div class="advice-card">
					<el-icon><ChatDotRound /></el-icon>
					<p>{{ currentAdviceText }}</p>
				</div>
				<div v-if="guidanceCards.length" class="guidance-grid">
					<div v-for="item in guidanceCards" :key="item.title">
						<span>{{ item.title }}</span>
						<strong>{{ item.desc }}</strong>
					</div>
				</div>
				<div class="action-row">
					<el-button type="primary" :loading="loading" :disabled="!selectedClue" @click="generateAdvice">
						{{ loading ? '生成中，约 5-15 秒' : '生成沟通建议' }}
					</el-button>
					<el-button :disabled="!aiResult || !selectedClue?.advice" @click="copyAdvice">复制建议</el-button>
					<el-button :disabled="!aiResult || !selectedClue" @click="router.push('/detectionResult')">回到检测结果</el-button>
				</div>
				<div class="chat-box">
					<div class="section-title compact">
						<h3>连续追问</h3>
						<p>可继续询问“学生否认怎么办”“是否需要联系辅导员”“怎么避免伤害学生自尊”。</p>
					</div>
					<div class="chat-list">
						<div v-if="!chatMessages.length" class="chat-empty">围绕当前线索继续提问，系统会带上检测证据和前文对话。</div>
						<div v-for="(message, index) in chatMessages" :key="index" class="chat-message" :class="message.role">
							{{ message.content }}
						</div>
					</div>
					<div class="chat-input-row">
						<el-input v-model="chatInput" :disabled="!selectedClue" placeholder="输入追问内容" @keyup.enter="askFollowUp" />
						<el-button type="primary" :loading="chatLoading" :disabled="!selectedClue" @click="askFollowUp">发送</el-button>
					</div>
				</div>
			</section>
		</div>
	</DemoShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { ChatDotRound } from '@element-plus/icons-vue';
import DemoShell from '/@/views/demo/components/DemoShell.vue';
import DetectionSourceSelector from '/@/views/demo/components/DetectionSourceSelector.vue';
import { behaviorText, buildPrompt, clearDemoDetectionState, currentFocusClue, demoState, filterWarningRecordsByHistories, getAiDialogue, parseDurationSeconds, riskText, setAiDialogue, setCurrentEvent, sourceNameKey, syncWarningRecords, topFocusClues } from '/@/views/demo/demoState';
import { normalizeAdviceResult } from '/@/utils/advice';
import type { AdviceCard, AdviceResult } from '/@/utils/advice';
import request from '/@/utils/request';

type ChatMessage = { role: 'user' | 'assistant'; content: string };

const router = useRouter();
const loading = ref(false);
const chatLoading = ref(false);
const chatInput = ref('');
const selectedEventId = ref(currentFocusClue.value?.eventId || '');
const selectedSource = ref('');
const warningRecords = ref<any[]>([]);
const videoRecords = ref<any[]>([]);
const chatMessages = ref<ChatMessage[]>([]);
const reasonCards = ref<AdviceCard[]>([]);
const guidanceCards = ref<AdviceCard[]>([]);
const aiResult = ref<Pick<AdviceResult, 'source' | 'model' | 'fallback' | 'message'> | null>(null);

const selectedClue = computed(() => currentFocusClue.value);
const sourceLabel = computed(() => {
	if (!aiResult.value) return '待调用';
	return aiResult.value.fallback ? '生成失败' : '真实大模型';
});
const sourceTagType = computed(() => {
	if (!aiResult.value) return 'info';
	return aiResult.value.fallback ? 'danger' : 'success';
});
const sourceDetail = computed(() => {
	if (!aiResult.value) return '尚未请求后端 AI 接口。';
	const modelText = aiResult.value.model ? `模型：${aiResult.value.model}` : '模型：后端配置';
	return `${modelText}；来源：${aiResult.value.source}${aiResult.value.message ? `；${aiResult.value.message}` : ''}`;
});
const reasonPanelHint = computed(() => {
	if (!aiResult.value) return '可能原因不会使用前端固定模板，生成时由后端携带检测证据请求大模型；所有原因仍需教师课后确认。';
	return aiResult.value.fallback ? '大模型未成功返回，本页不会使用本地模板冒充 AI 研判。' : '以下可能原因由大模型基于检测证据生成，仅提供沟通方向，所有原因都需要教师课后确认。';
});
const advicePanelHint = computed(() => {
	if (loading.value) return '正在等待后端大模型接口返回；系统不会使用本地模板冒充 AI 建议。';
	if (!aiResult.value) return '点击生成后，前端会请求后端接口，由后端使用 API-Key 调用大模型生成话术。';
	return aiResult.value.fallback ? '大模型未成功返回，请检查后端 API-Key、模型名称和接口地址后重试。' : '已通过后端 API-Key 调用大模型，并结合行为、持续时长和触发原因生成教师沟通话术。';
});
const currentAdviceText = computed(() => {
	if (!aiResult.value) return '点击“生成沟通建议”后，本页才会展示本次后端大模型接口返回的开场话术、追问方向和后续跟进建议。';
	if (aiResult.value.fallback) return aiResult.value.message || '大模型请求失败，未生成建议。';
	return selectedClue.value?.advice || '大模型接口未返回有效建议，请检查后端 API-Key 与模型接口配置。';
});

watch(() => selectedClue.value ? `${selectedClue.value.clueId}:${selectedClue.value.eventIds.join(',')}` : '', () => {
	const clue = selectedClue.value;
	selectedEventId.value = clue?.eventId || '';
	chatMessages.value = clue ? getAiDialogue(clue.eventId).slice() : [];
	reasonCards.value = [];
	guidanceCards.value = [];
	aiResult.value = null;
});

function buildAdviceRequest(extra: Record<string, any> = {}) {
	const clue = selectedClue.value;
	if (!clue) return {};
	return {
		riskLevel: clue.riskLevel,
		behaviorType: clue.behaviorType,
		durationSeconds: clue.durationSeconds || parseDurationSeconds(clue.durationText),
		durationText: clue.durationText,
		reason: `${clue.reason} ${clue.evidenceText}`,
		scene: buildPrompt(clue),
		provider: demoState.provider,
		...extra,
	};
}

function handleSourceChange(option: any) {
	if (!option || !warningRecords.value.length) return;
	selectedSource.value = option.value;
	syncWarningRecords(warningRecords.value, option.inputVideo || option.label);
	if (topFocusClues.value.length) setCurrentEvent(topFocusClues.value[0].eventId);
}

function generateAdvice() {
	if (!selectedClue.value) return;
	loading.value = true;
	request.post('/api/warningRecords/advice', buildAdviceRequest()).then((res) => {
		if (res?.code != 0) throw new Error(res?.msg || '大模型接口未返回成功状态');
		const result = normalizeAdviceResult(res.data, '');
		if (result.fallback || !result.advice) throw new Error(result.message || '大模型未返回有效建议');
		applyGeneratedAdvice(result);
		chatMessages.value = [{ role: 'assistant', content: result.advice }];
		setAiDialogue(selectedClue.value!.eventId, chatMessages.value);
		ElMessage.success(`${result.model || '大模型'} 沟通建议已生成`.trim());
	}).catch((error) => {
		markAdviceFailure(error, '大模型请求失败，未生成建议。');
	}).finally(() => {
		loading.value = false;
	});
}

function askFollowUp() {
	const clue = selectedClue.value;
	const question = chatInput.value.trim();
	if (!clue || !question || chatLoading.value) return;
	chatMessages.value.push({ role: 'user', content: question });
	chatInput.value = '';
	chatLoading.value = true;
	request.post('/api/warningRecords/advice', buildAdviceRequest({
		question,
		messages: chatMessages.value.slice(0, -1),
	})).then((res) => {
		if (res?.code != 0) throw new Error(res?.msg || '大模型接口未返回成功状态');
		const result = normalizeAdviceResult(res.data, '');
		if (result.fallback || !result.advice) throw new Error(result.message || '大模型未返回有效回复');
		chatMessages.value.push({ role: 'assistant', content: result.advice });
		setAiDialogue(clue.eventId, chatMessages.value);
		aiResult.value = result;
	}).catch((error) => {
		markAdviceFailure(error, '大模型请求失败，未生成追问回复。');
	}).finally(() => {
		chatLoading.value = false;
	});
}

function applyGeneratedAdvice(result: AdviceResult) {
	applyAdviceToSelectedClue(result.advice);
	reasonCards.value = result.possibleReasons;
	guidanceCards.value = result.guidanceCards;
	aiResult.value = result;
}

function applyAdviceToSelectedClue(advice: string) {
	const clue = selectedClue.value;
	if (!clue) return;
	const ids = new Set(clue.eventIds?.length ? clue.eventIds : [clue.eventId]);
	const updated = demoState.events.filter((event) => ids.has(event.eventId));
	updated.forEach((event) => {
		event.advice = advice;
		event.provider = demoState.provider;
		event.promptPreview = buildPrompt(event);
	});
	const historyItem = updated.find((event) => event.eventId === clue.eventId) || updated[0];
	if (historyItem) {
		demoState.aiHistory = [{ ...historyItem }, ...demoState.aiHistory.filter((item) => !ids.has(item.eventId))].slice(0, 6);
	}
}

function markAdviceFailure(error: any, fallbackMessage: string) {
	const message = error?.message || fallbackMessage;
	reasonCards.value = [];
	guidanceCards.value = [];
	aiResult.value = { source: 'llm_error', fallback: true, message };
	ElMessage.error(message);
}

function copyAdvice() {
	if (!selectedClue.value?.advice) return;
	navigator.clipboard?.writeText(selectedClue.value.advice);
	ElMessage.success('建议文本已复制');
}

async function loadWarningRecords() {
	try {
		const [warningRes, videoRes] = await Promise.all([
			request.get('/api/warningRecords/all'),
			request.get('/api/videoRecords/all'),
		]);
		if (videoRes?.code == 0 && Array.isArray(videoRes.data)) videoRecords.value = videoRes.data;
		if (!videoRecords.value.length) {
			warningRecords.value = [];
			selectedSource.value = '';
			clearDemoDetectionState();
			return;
		}
		if (warningRes?.code == 0 && Array.isArray(warningRes.data)) {
			const activeWarnings = filterWarningRecordsByHistories(warningRes.data, videoRecords.value);
			warningRecords.value = activeWarnings;
			if (!activeWarnings.length) {
				clearDemoDetectionState();
				return;
			}
			syncWarningRecords(activeWarnings);
			selectedSource.value = sourceNameKey(demoState.material.sourceName);
			if (topFocusClues.value.length && !selectedEventId.value) setCurrentEvent(topFocusClues.value[0].eventId);
		}
	} catch (error) {}
}

onMounted(loadWarningRecords);
</script>

<style scoped lang="scss">
.ai-page {
	height: 100%;
	display: grid;
	grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr);
	grid-template-rows: auto auto minmax(0, 1fr);
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
	padding: 16px;
}

.advice-panel {
	grid-row: 2 / 4;
	grid-column: 2;
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

.event-summary,
.reason-grid,
.guidance-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 12px;
}

.event-summary div,
.reason-grid div,
.guidance-grid div {
	padding: 14px;
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

.event-summary span,
.guidance-grid span {
	display: block;
	color: #7a8a8f;
	font-size: 12px;
}

.event-summary strong,
.guidance-grid strong {
	display: block;
	margin-top: 8px;
	font-size: 18px;
}

.reason-box,
.advice-card,
.chat-box {
	margin-top: 14px;
}

.reason-box,
.advice-card {
	padding: 14px;
	border-radius: 8px;
	background: #fbfdfc;
	border: 1px solid #e2ece9;
}

.reason-box h3,
.reason-grid strong {
	margin: 0 0 8px;
	font-size: 16px;
}

.reason-box p,
.reason-grid p,
.advice-card p,
.chat-empty {
	margin: 0;
	color: #53666b;
	line-height: 1.8;
}

.advice-card p {
	white-space: pre-wrap;
	word-break: break-word;
	overflow-wrap: anywhere;
}

.advice-card {
	display: grid;
	grid-template-columns: 34px minmax(0, 1fr);
	gap: 12px;
	background: #f1fbf8;
	border-color: #cdebe4;
	align-items: start;
}

.ai-source-row {
	display: flex;
	align-items: center;
	gap: 10px;
	margin-bottom: 12px;
	color: #5f7075;
	font-size: 13px;
	line-height: 1.5;
}

.advice-card .el-icon {
	margin-top: 4px;
	color: #008f87;
	font-size: 24px;
}

.guidance-grid {
	margin-top: 12px;
}

.action-row {
	display: flex;
	flex-wrap: wrap;
	gap: 10px;
	margin-top: 14px;
}

.chat-box {
	padding-top: 16px;
	border-top: 1px solid #e5eeeb;
}

.chat-list {
	display: grid;
	gap: 10px;
	max-height: 260px;
	overflow-y: auto;
	padding-right: 2px;
}

.chat-message {
	width: fit-content;
	max-width: 86%;
	padding: 10px 12px;
	border-radius: 8px;
	line-height: 1.65;
	background: #f7fbfa;
	color: #34464a;
	border: 1px solid #e0e9e7;
	white-space: pre-wrap;
	word-break: break-word;
	overflow-wrap: anywhere;
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
	gap: 10px;
	margin-top: 12px;
}

@media (max-width: 1040px) {
	.ai-page {
		height: auto;
		grid-template-columns: 1fr;
		grid-template-rows: none;
		overflow: visible;
	}

	.source-panel {
		grid-column: auto;
	}

	.advice-panel {
		grid-column: auto;
		grid-row: auto;
		overflow: visible;
	}
}
</style>
