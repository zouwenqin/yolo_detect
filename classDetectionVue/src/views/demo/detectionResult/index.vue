<template>
	<DemoShell active="result" title="检测结果" status="检测完成">
		<div class="result-page">
			<section class="panel result-list">
				<div class="section-title">
					<div>
						<h3>检测事件列表</h3>
						<p>基于录制视频素材生成的课堂行为事件，不绑定学生实名信息。</p>
					</div>
					<el-tag type="success">{{ demoState.events.length }} 条事件</el-tag>
				</div>

				<el-table :data="demoState.events" height="100%" highlight-current-row @row-click="handleRowClick">
					<el-table-column prop="eventId" label="事件编号" width="110" />
					<el-table-column label="检测来源" min-width="170">
						<template #default="{ row }">{{ row.sourceName }}</template>
					</el-table-column>
					<el-table-column label="行为类型" width="130">
						<template #default="{ row }">{{ behaviorText(row.behaviorType) }}</template>
					</el-table-column>
					<el-table-column label="风险等级" width="110">
						<template #default="{ row }">
							<el-tag :type="riskTagType(row.riskLevel)">风险{{ riskText(row.riskLevel) }}</el-tag>
						</template>
					</el-table-column>
					<el-table-column prop="durationText" label="持续时长" width="120" />
					<el-table-column prop="confidence" label="置信度" width="100" />
					<el-table-column label="处理状态" width="110">
						<template #default="{ row }">
							<el-tag effect="plain">{{ row.status }}</el-tag>
						</template>
					</el-table-column>
					<el-table-column prop="createdAt" label="生成时间" width="150" />
				</el-table>
			</section>

			<aside class="panel detail-panel">
				<div class="section-title compact">
					<div>
						<h3>事件详情</h3>
						<p>{{ currentEvent.eventId }} · {{ demoState.material.sourceName }}</p>
					</div>
				</div>
				<div class="preview-card">
					<div class="thumbnail">
						<div class="board"></div>
						<div v-for="item in 7" :key="item" class="head" :class="`h${item}`"></div>
						<div class="outline">{{ behaviorText(currentEvent.behaviorType) }}</div>
					</div>
					<div class="risk-summary">
						<el-tag :type="riskTagType(currentEvent.riskLevel)" size="large">风险{{ riskText(currentEvent.riskLevel) }}</el-tag>
						<h2>{{ behaviorText(currentEvent.behaviorType) }} {{ currentEvent.durationText }}</h2>
						<p>{{ currentEvent.reason }}</p>
					</div>
				</div>

				<div class="info-grid">
					<div><span>行为类型</span><strong>{{ behaviorText(currentEvent.behaviorType) }}</strong></div>
					<div><span>持续时长</span><strong>{{ currentEvent.durationText }}</strong></div>
					<div><span>置信度</span><strong>{{ currentEvent.confidence }}</strong></div>
					<div><span>处理状态</span><strong>{{ currentEvent.status }}</strong></div>
				</div>

				<section class="advice-snippet">
					<h3>AI建议摘要</h3>
					<p>{{ currentEvent.advice }}</p>
				</section>

				<div class="action-row">
					<el-button type="primary" @click="router.push('/aiIntervention')">生成干预建议</el-button>
					<el-button @click="router.push('/interventionReport')">查看报告</el-button>
				</div>
			</aside>
		</div>
	</DemoShell>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import DemoShell from '/@/views/demo/components/DemoShell.vue';
import { behaviorText, currentEvent, demoState, riskTagType, riskText, setCurrentEvent, syncWarningRecords } from '/@/views/demo/demoState';
import request from '/@/utils/request';

const router = useRouter();

function handleRowClick(row: any) {
	setCurrentEvent(row.eventId);
}

onMounted(() => {
	request.get('/api/warningRecords/all').then((res) => {
		if (res?.code === 0 && Array.isArray(res.data)) {
			syncWarningRecords(res.data);
		}
	}).catch(() => {});
});
</script>

<style scoped lang="scss">
.result-page {
	height: 100%;
	display: grid;
	grid-template-columns: minmax(620px, 1fr) 420px;
	gap: 16px;
	overflow: hidden;
}

.panel {
	border-radius: 8px;
	background: rgba(255, 255, 255, .97);
	border: 1px solid #dde8e5;
	box-shadow: 0 14px 34px rgba(23, 42, 46, .07);
}

.result-list {
	min-width: 0;
	padding: 16px;
	display: flex;
	flex-direction: column;
	overflow: hidden;
}

.detail-panel {
	padding: 18px;
	overflow-y: auto;
}

.section-title {
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 16px;
	margin-bottom: 14px;
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

.preview-card {
	border-radius: 8px;
	border: 1px solid #e1ebe8;
	background: #fbfdfc;
	overflow: hidden;
}

.thumbnail {
	position: relative;
	height: 210px;
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

.risk-summary {
	padding: 16px;
}

.risk-summary h2 {
	margin: 12px 0 8px;
	font-size: 24px;
}

.risk-summary p,
.advice-snippet p {
	margin: 0;
	color: #53666b;
	line-height: 1.75;
}

.info-grid {
	display: grid;
	grid-template-columns: repeat(2, 1fr);
	gap: 10px;
	margin: 14px 0;
}

.info-grid div {
	padding: 14px;
	border-radius: 8px;
	background: #f7fbfa;
	border: 1px solid #e2ece9;
}

.info-grid span {
	display: block;
	color: #7a8a8f;
	font-size: 12px;
}

.info-grid strong {
	display: block;
	margin-top: 8px;
	font-size: 17px;
}

.advice-snippet {
	padding: 14px;
	border-radius: 8px;
	background: #f1fbf8;
	border: 1px solid #cdebe4;
}

.advice-snippet h3 {
	margin: 0 0 10px;
	font-size: 16px;
}

.action-row {
	display: flex;
	gap: 10px;
	margin-top: 16px;
}

@media (max-width: 980px) {
	.result-page {
		height: auto;
		grid-template-columns: 1fr;
		overflow: visible;
	}

	.detail-panel {
		overflow: visible;
	}
}
</style>
