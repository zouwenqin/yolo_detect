<template>
	<DemoShell active="ai" title="定性与沟通助手" :status="selectedClue ? '建议可生成' : '等待检测结果'">
		<div class="ai-page">
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
					<p>仅提供沟通方向，所有原因都需要教师课后与学生确认。</p>
				</div>
				<div class="reason-grid">
					<div v-for="item in reasonCards" :key="item.title">
						<strong>{{ item.title }}</strong>
						<p>{{ item.desc }}</p>
					</div>
				</div>
			</section>

			<section class="panel advice-panel">
				<div class="section-title compact">
					<h3>沟通建议</h3>
					<p>MiniMax 会结合行为、持续时长和触发原因生成教师沟通话术。</p>
				</div>
				<div class="advice-card">
					<el-icon><ChatDotRound /></el-icon>
					<p>{{ selectedClue?.advice || '点击生成后，将给出开场话术、追问方向和后续跟进建议。' }}</p>
				</div>
				<div class="guidance-grid">
					<div>
						<span>建议开场</span>
						<strong>先关心身体状态和课堂压力</strong>
					</div>
					<div>
						<span>避免说法</span>
						<strong>避免当众点名或贴标签</strong>
					</div>
					<div>
						<span>追问方向</span>
						<strong>睡眠、课程难度、近期情绪</strong>
					</div>
					<div>
						<span>人工跟进</span>
						<strong>高风险或反复出现时建议复核</strong>
					</div>
				</div>
				<div class="action-row">
					<el-button type="primary" :loading="loading" :disabled="!selectedClue" @click="generateAdvice">生成沟通建议</el-button>
					<el-button :disabled="!selectedClue?.advice" @click="copyAdvice">复制建议</el-button>
					<el-button :disabled="!selectedClue" @click="router.push('/interventionReport')">同步到跟进记录</el-button>
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
import { applyAdvice, behaviorText, buildPrompt, currentFocusClue, demoState, fallbackAdvice, parseDurationSeconds, riskText, setCurrentEvent, syncWarningRecords, topFocusClues } from '/@/views/demo/demoState';
import { normalizeAdviceResult } from '/@/utils/advice';
import request from '/@/utils/request';

type ChatMessage = { role: 'user' | 'assistant'; content: string };

const router = useRouter();
const loading = ref(false);
const chatLoading = ref(false);
const chatInput = ref('');
const selectedEventId = ref(currentFocusClue.value?.eventId || '');
const chatMessages = ref<ChatMessage[]>([]);

const selectedClue = computed(() => currentFocusClue.value);
const reasonCards = computed(() => [
	{ title: '疲劳或身体不适', desc: `${selectedClue.value ? behaviorText(selectedClue.value.behaviorType) : '异常行为'}可能与睡眠、身体状态有关，需温和确认。` },
	{ title: '课程压力或任务受阻', desc: '可询问是否听懂课程、实训任务是否遇到困难，避免直接批评。' },
	{ title: '情绪低落或近期困扰', desc: '仅作为沟通方向，不做诊断；若反复出现再建议辅导员或心理老师介入。' },
	{ title: '临时分心因素', desc: '结合课堂位置、任务进度和同类记录频次，判断是否需要持续观察。' },
]);

watch(selectedClue, (clue) => {
	selectedEventId.value = clue?.eventId || '';
	chatMessages.value = [];
}, { deep: true });

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

function generateAdvice() {
	if (!selectedClue.value) return;
	loading.value = true;
	request.post('/api/warningRecords/advice', buildAdviceRequest()).then((res) => {
		const result = normalizeAdviceResult(res?.code == 0 ? res.data : null, fallbackAdvice(selectedClue.value!));
		applyAdvice(result.advice, demoState.provider);
		chatMessages.value = [{ role: 'assistant', content: result.advice }];
		if (result.fallback) {
			ElMessage.warning(result.message || 'MiniMax 暂未返回，已使用本地模板建议');
		} else {
			ElMessage.success(`MiniMax ${result.model || ''} 沟通建议已生成`.trim());
		}
	}).catch(() => {
		const advice = fallbackAdvice(selectedClue.value!);
		applyAdvice(advice, demoState.provider);
		chatMessages.value = [{ role: 'assistant', content: advice }];
		ElMessage.warning('AI接口暂不可用，已使用本地模板建议');
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
		const result = normalizeAdviceResult(res?.code == 0 ? res.data : null, buildLocalFollowUpAnswer(clue, question));
		chatMessages.value.push({ role: 'assistant', content: result.advice });
		if (result.fallback) ElMessage.warning(result.message || 'MiniMax 暂未返回，已使用本地模板回复');
	}).catch(() => {
		chatMessages.value.push({ role: 'assistant', content: buildLocalFollowUpAnswer(clue, question) });
		ElMessage.warning('AI接口暂不可用，已使用本地模板回复');
	}).finally(() => {
		chatLoading.value = false;
	});
}

function buildLocalFollowUpAnswer(clue: any, question: string) {
	const q = question.toLowerCase();
	const behavior = behaviorText(clue.behaviorType);
	if (q.includes('否认') || q.includes('不承认')) {
		return `如果学生否认${behavior}相关情况，建议不要争辩检测结果。可以说“我不是想批评你，只是看到你这节课状态有点不一样，想确认你是否需要帮助”。先让学生解释当时情况，再根据反馈决定是否继续观察。`;
	}
	if (q.includes('辅导员') || q.includes('班主任') || q.includes('心理')) {
		return `是否联系辅导员要看频次和影响程度。若${behavior}只是一次短暂出现，先由任课老师课后关心确认；如果多次出现、持续时间较长，或伴随明显回避交流、情绪低落，再建议同步班主任、辅导员或心理老师共同跟进。`;
	}
	if (q.includes('家长')) {
		return `不建议一开始就直接联系家长。可以先与学生本人做低压力沟通，了解是否有睡眠、身体或学习压力问题；只有在风险持续、学生需要支持或学校流程要求时，再由班主任或辅导员按规范联系家长。`;
	}
	if (q.includes('自尊') || q.includes('伤害') || q.includes('尴尬')) {
		return `避免伤害学生自尊的关键是私下、具体、非评价。不要说“你有问题”或“你是不是心理不好”，可以说“我注意到你今天有一段时间${behavior}，担心你是不是太累了”。把重点放在支持和确认需求上。`;
	}
	if (q.includes('开口') || q.includes('怎么说') || q.includes('话术')) {
		return `可以这样开口：“今天课堂中我注意到你有一段时间状态比较低，我想确认一下是不是身体不舒服、没休息好，或者课程任务有点吃力？如果需要，我们可以一起想办法。”语气保持关心，不把检测结果当作质问。`;
	}
	return `针对“${question}”，建议围绕${behavior}线索做非诊断式沟通：先描述观察到的课堂状态，再询问学生是否需要帮助，最后根据学生反馈决定是继续观察、提供学习支持，还是同步班主任/辅导员复核。`;
}

function copyAdvice() {
	if (!selectedClue.value?.advice) return;
	navigator.clipboard?.writeText(selectedClue.value.advice);
	ElMessage.success('建议文本已复制');
}

async function loadWarningRecords() {
	try {
		const res = await request.get('/api/warningRecords/all');
		if (res?.code == 0 && Array.isArray(res.data)) {
			syncWarningRecords(res.data);
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
	grid-template-rows: auto minmax(0, 1fr);
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

.advice-panel {
	grid-row: 1 / 3;
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

.advice-card {
	display: grid;
	grid-template-columns: 34px minmax(0, 1fr);
	gap: 12px;
	background: #f1fbf8;
	border-color: #cdebe4;
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

	.advice-panel {
		grid-column: auto;
		grid-row: auto;
		overflow: visible;
	}
}
</style>
