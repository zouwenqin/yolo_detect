<template>
	<DemoShell active="result" title="课堂异常发现" :status="pageStatus">
		<div class="result-page">
			<section class="panel overview-panel">
				<div class="section-title">
					<div>
						<h3>本次检测概览</h3>
						<p>系统把同一视频中的重复检测记录聚合成重点线索，帮助老师先看到最需要关注的课堂异常。</p>
					</div>
					<el-tag :type="clueCount ? 'success' : 'info'">{{ clueCount ? '已发现重点线索' : '等待检测结果' }}</el-tag>
				</div>
				<div class="overview-grid">
					<div>
						<span>视频素材</span>
						<strong>{{ demoState.material.sourceName }}</strong>
					</div>
					<div>
						<span>异常线索</span>
						<strong>{{ clueCount }}</strong>
					</div>
					<div>
						<span>最高风险</span>
						<strong>风险{{ riskText(maxRisk) }}</strong>
					</div>
					<div>
						<span>重点行为</span>
						<strong>{{ primaryClue ? behaviorText(primaryClue.behaviorType) : '待检测' }}</strong>
					</div>
				</div>
			</section>

			<section class="panel clue-panel">
				<div class="section-title">
					<div>
						<h3>重点异常线索</h3>
						<p>只保留 Top 3 风险线索，按风险等级和持续时长排序，减少比赛展示时的重复信息。</p>
					</div>
					<el-button text @click="showRaw = !showRaw">{{ showRaw ? '收起原始记录' : '查看原始记录' }}</el-button>
				</div>

				<el-alert v-if="loadError" :title="loadError" type="warning" :closable="false" show-icon class="result-alert" />

				<div v-loading="loading" class="clue-list">
					<button
						v-for="item in topFocusClues"
						:key="item.clueId"
						class="clue-card"
						:class="{ active: item.eventIds.includes(demoState.selectedEventId) }"
						@click="handleClueClick(item.eventId)"
					>
						<div class="clue-head">
							<strong>{{ behaviorText(item.behaviorType) }}</strong>
							<el-tag :type="riskTagType(item.riskLevel)">风险{{ riskText(item.riskLevel) }}</el-tag>
						</div>
						<p>{{ item.evidenceText }}</p>
						<div class="clue-meta">
							<span>最长持续 {{ item.durationText }}</span>
							<span>{{ item.eventCount }} 条同类记录</span>
							<span>{{ item.confidence }}</span>
						</div>
					</button>
					<el-empty v-if="!loading && !topFocusClues.length" description="请先完成录制视频检测，系统将自动筛选课堂异常线索">
						<el-button type="primary" @click="router.push('/videoPredict')">去视频检测</el-button>
					</el-empty>
				</div>

				<el-collapse-transition>
					<div v-if="showRaw" class="raw-table">
						<el-table :data="realEvents" height="220">
							<el-table-column prop="eventId" label="事件编号" width="120" />
							<el-table-column label="行为类型" width="130">
								<template #default="{ row }">{{ behaviorText(row.behaviorType) }}</template>
							</el-table-column>
							<el-table-column label="风险等级" width="110">
								<template #default="{ row }">风险{{ riskText(row.riskLevel) }}</template>
							</el-table-column>
							<el-table-column prop="durationText" label="持续时长" width="120" />
							<el-table-column prop="reason" label="触发原因" min-width="260" />
						</el-table>
					</div>
				</el-collapse-transition>
			</section>

			<aside class="panel evidence-panel">
				<template v-if="selectedClue">
					<div class="section-title compact">
						<h3>行为证据卡片</h3>
						<p>{{ selectedClue.timeRange }}</p>
					</div>
					<div class="evidence-visual">
						<div class="board"></div>
						<div v-for="item in 7" :key="item" class="head" :class="`h${item}`"></div>
						<div class="outline">{{ behaviorText(selectedClue.behaviorType) }}</div>
					</div>
					<div class="evidence-summary">
						<el-tag :type="riskTagType(selectedClue.riskLevel)" size="large">风险{{ riskText(selectedClue.riskLevel) }}</el-tag>
						<h2>{{ behaviorText(selectedClue.behaviorType) }} · {{ selectedClue.durationText }}</h2>
						<p>{{ selectedClue.reason }}</p>
					</div>
					<div class="info-grid">
						<div><span>同类记录</span><strong>{{ selectedClue.eventCount }} 条</strong></div>
						<div><span>置信度</span><strong>{{ selectedClue.confidence }}</strong></div>
						<div><span>处理状态</span><strong>{{ selectedClue.status }}</strong></div>
						<div><span>数据来源</span><strong>算法检测 + 后端预警</strong></div>
					</div>
					<section class="teacher-note">
						<h3>教师关注提示</h3>
						<p>{{ selectedClue.teacherHint }}</p>
						<p>该提示不是心理诊断，只用于提醒教师课后进行温和、私下的沟通确认。</p>
					</section>
					<div class="action-row">
						<el-button type="primary" @click="router.push('/aiIntervention')">进入 AI 沟通助手</el-button>
						<el-button @click="router.push('/interventionReport')">生成跟进记录</el-button>
					</div>
				</template>
				<div v-else class="empty-detail">
					<el-empty description="完成视频检测后将展示行为证据卡片" />
				</div>
			</aside>
		</div>
	</DemoShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import DemoShell from '/@/views/demo/components/DemoShell.vue';
import { behaviorText, currentFocusClue, demoState, focusClues, realEvents, riskTagType, riskText, setCurrentEvent, syncWarningRecords, topFocusClues } from '/@/views/demo/demoState';
import request from '/@/utils/request';

const router = useRouter();
const loading = ref(false);
const loadError = ref('');
const showRaw = ref(false);

const clueCount = computed(() => focusClues.value.length);
const selectedClue = computed(() => currentFocusClue.value);
const primaryClue = computed(() => topFocusClues.value[0]);
const maxRisk = computed(() => primaryClue.value?.riskLevel || 'normal');
const pageStatus = computed(() => loading.value ? '同步检测结果' : (clueCount.value ? '已生成线索' : '等待检测结果'));

function handleClueClick(eventId: string) {
	setCurrentEvent(eventId);
}

async function loadWarningRecords() {
	loading.value = true;
	loadError.value = '';
	try {
		const res = await request.get('/api/warningRecords/all');
		if (res?.code == 0 && Array.isArray(res.data)) {
			syncWarningRecords(res.data);
			if (topFocusClues.value.length && !topFocusClues.value.some((item) => item.eventIds.includes(demoState.selectedEventId))) {
				setCurrentEvent(topFocusClues.value[0].eventId);
			}
			return;
		}
		loadError.value = '后端暂未返回检测线索，请先完成一次视频检测。';
	} catch (error) {
		loadError.value = '检测线索同步失败，请确认 Spring Boot 后端服务已启动。';
		ElMessage.warning(loadError.value);
	} finally {
		loading.value = false;
	}
}

onMounted(loadWarningRecords);
</script>

<style scoped lang="scss">
.result-page {
	height: 100%;
	display: grid;
	grid-template-columns: minmax(0, 1fr) 420px;
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

.overview-panel,
.clue-panel {
	min-width: 0;
}

.evidence-panel {
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
	font-size: 13px;
}

.overview-grid {
	display: grid;
	grid-template-columns: repeat(4, minmax(0, 1fr));
	gap: 12px;
}

.overview-grid div,
.info-grid div {
	padding: 14px;
	border-radius: 8px;
	border: 1px solid #e2ece9;
	background: #f7fbfa;
}

.overview-grid span,
.info-grid span {
	display: block;
	color: #7a8a8f;
	font-size: 12px;
}

.overview-grid strong,
.info-grid strong {
	display: block;
	margin-top: 8px;
	font-size: 17px;
}

.clue-list {
	display: grid;
	gap: 12px;
	min-height: 260px;
}

.clue-card {
	width: 100%;
	padding: 16px;
	border-radius: 8px;
	border: 1px solid #e2ece9;
	background: #fbfdfc;
	text-align: left;
	cursor: pointer;
}

.clue-card.active,
.clue-card:hover {
	border-color: #008f87;
	background: #f1fbf8;
}

.clue-head,
.clue-meta,
.action-row {
	display: flex;
	align-items: center;
	gap: 10px;
}

.clue-head {
	justify-content: space-between;
}

.clue-head strong {
	font-size: 18px;
}

.clue-card p,
.teacher-note p,
.evidence-summary p {
	color: #53666b;
	line-height: 1.75;
	margin: 10px 0 0;
}

.clue-meta {
	flex-wrap: wrap;
	margin-top: 12px;
	color: #6b7b80;
	font-size: 13px;
}

.result-alert,
.raw-table {
	margin-bottom: 12px;
}

.evidence-visual {
	position: relative;
	height: 210px;
	border-radius: 8px 8px 0 0;
	background:
		linear-gradient(#e6edea 0 32%, transparent 32%),
		linear-gradient(#805d45 0 0);
	overflow: hidden;
}

.board {
	position: absolute;
	left: 31%;
	top: 9%;
	width: 38%;
	height: 22%;
	border: 7px solid #304a48;
	background: #edf3f0;
}

.head {
	position: absolute;
	width: 58px;
	height: 48px;
	border-radius: 32px 32px 8px 8px;
	background: #243a3d;
	box-shadow: 0 28px 0 #c99d71;
}

.h1 { left: 10%; top: 42%; transform: scale(.75); }
.h2 { left: 27%; top: 39%; transform: scale(.82); }
.h3 { left: 45%; top: 49%; transform: scale(1.22); }
.h4 { left: 65%; top: 41%; transform: scale(.86); }
.h5 { left: 80%; top: 44%; transform: scale(.76); }
.h6 { left: 20%; top: 66%; transform: scale(1); }
.h7 { left: 57%; top: 67%; transform: scale(.98); }

.outline {
	position: absolute;
	left: 42%;
	top: 39%;
	padding: 7px 12px;
	border: 2px solid #ef4f45;
	border-radius: 6px;
	color: #ef4f45;
	background: rgba(255, 255, 255, .72);
	font-weight: 800;
}

.evidence-summary {
	padding: 16px 0 8px;
}

.evidence-summary h2 {
	margin: 12px 0 8px;
	font-size: 24px;
}

.info-grid {
	display: grid;
	grid-template-columns: repeat(2, 1fr);
	gap: 10px;
	margin: 12px 0;
}

.teacher-note {
	padding: 14px;
	border-radius: 8px;
	background: #f1fbf8;
	border: 1px solid #cdebe4;
}

.teacher-note h3 {
	margin: 0;
	font-size: 16px;
}

.empty-detail {
	min-height: 480px;
	display: grid;
	place-items: center;
}

.action-row {
	margin-top: 16px;
}

@media (max-width: 1040px) {
	.result-page {
		height: auto;
		grid-template-columns: 1fr;
		grid-template-rows: none;
		overflow: visible;
	}

	.evidence-panel {
		grid-row: auto;
		grid-column: auto;
		overflow: visible;
	}

	.overview-grid {
		grid-template-columns: repeat(2, 1fr);
	}
}
</style>
