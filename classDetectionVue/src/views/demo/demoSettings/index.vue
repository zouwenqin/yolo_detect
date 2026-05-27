<template>
	<DemoShell active="settings" title="演示策略配置" status="教师可控">
		<div class="settings-page">
			<section class="panel">
				<div class="section-title">
					<h3>异常发现策略</h3>
					<p>这些配置用于解释系统如何从课堂视频中筛出重点线索，比赛展示时强调“辅助发现”，不替代教师判断。</p>
				</div>
				<div class="setting-row">
					<div>
						<strong>趴桌/疑似睡觉触发阈值</strong>
						<span>连续或累计超过阈值后生成高关注线索</span>
					</div>
					<el-slider v-model="demoState.settings.lieDeskThreshold" :min="5" :max="30" show-input />
				</div>
				<div class="setting-row">
					<div>
						<strong>发呆/持续低头触发阈值</strong>
						<span>用于发现老师不易注意到的后排持续异常状态</span>
					</div>
					<el-slider v-model="demoState.settings.headDownThreshold" :min="5" :max="40" show-input />
				</div>
				<div class="setting-row">
					<div>
						<strong>模型置信度阈值</strong>
						<span>过滤低置信度检测，降低误报对展示和教师判断的干扰</span>
					</div>
					<el-slider v-model="demoState.settings.confidence" :min="10" :max="90" show-input />
				</div>
			</section>

			<section class="panel">
				<div class="section-title">
					<h3>干预边界</h3>
					<p>系统只做课堂行为线索和沟通辅助，不做心理诊断，不公开点名学生。</p>
				</div>
				<div class="switch-grid">
					<div>
						<strong>匿名事件展示</strong>
						<el-switch v-model="demoState.settings.anonymous" />
						<p>页面以检测事件和课堂线索为单位，不展示学生姓名或档案。</p>
					</div>
					<div>
						<strong>非诊断式表述</strong>
						<el-switch v-model="demoState.settings.nonDiagnostic" />
						<p>所有建议使用“可能原因、沟通确认、人工复核”等表达。</p>
					</div>
					<div>
						<strong>建议人工复核</strong>
						<el-switch v-model="demoState.settings.manualReview" />
						<p>高风险或反复出现的线索建议教师、辅导员或心理老师复核。</p>
					</div>
					<div>
						<strong>保留处理后视频回放</strong>
						<el-switch v-model="demoState.settings.saveVideo" />
						<p>用于比赛现场说明检测依据，正式部署可按隐私要求关闭。</p>
					</div>
				</div>
			</section>

			<section class="panel">
				<div class="section-title">
					<h3>AI 服务状态</h3>
					<p>AI 辅助干预统一使用后端配置的大模型接口，不在前端暴露 API-Key。</p>
				</div>
				<div class="form-grid">
					<label>
						<span>检测模型</span>
						<el-select v-model="demoState.settings.model">
							<el-option label="class.pt" value="class.pt" />
							<el-option label="class_yolov8_demo.pt" value="class_yolov8_demo.pt" />
							<el-option label="best_behavior.pt" value="best_behavior.pt" />
						</el-select>
					</label>
					<label>
						<span>AI 辅助模型</span>
						<div class="provider-card">
							<strong>后端大模型 · {{ aiService.model || '后端配置模型' }}</strong>
							<em>{{ aiService.configured ? 'API-Key 已在后端配置，生成建议时会返回真实/兜底来源' : '未检测到后端 API-Key，将使用本地兜底建议' }}</em>
							<el-tag :type="aiService.configured ? 'success' : 'warning'" size="small">
								{{ aiService.configured ? 'Key 已配置' : '本地兜底可用' }}
							</el-tag>
						</div>
					</label>
				</div>
			</section>

			<section class="panel">
				<div class="section-title">
					<h3>报告内容</h3>
					<p>教师跟进记录保留必要证据和沟通建议，服务后续复查，而不是输出技术日志。</p>
				</div>
				<div class="switch-grid">
					<div>
						<strong>包含检测证据</strong>
						<el-switch v-model="demoState.settings.reportStats" />
						<p>记录行为类型、持续时长、风险等级和触发原因。</p>
					</div>
					<div>
						<strong>包含 AI 建议</strong>
						<el-switch v-model="demoState.settings.reportAdvice" />
						<p>输出开场话术、追问方向和后续跟进建议。</p>
					</div>
				</div>
			</section>
		</div>
	</DemoShell>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue';
import DemoShell from '/@/views/demo/components/DemoShell.vue';
import { demoState } from '/@/views/demo/demoState';
import request from '/@/utils/request';

const aiService = reactive({
	configured: false,
	model: '',
});

async function loadAiServiceStatus() {
	try {
		const res = await request.get('/api/warningRecords/advice/status');
		if (res?.code == 0 && res.data) {
			aiService.configured = Boolean(res.data.configured);
			aiService.model = res.data.model || '';
		}
	} catch (error) {
		aiService.configured = false;
	}
}

onMounted(loadAiServiceStatus);
</script>

<style scoped lang="scss">
.settings-page {
	height: 100%;
	display: grid;
	grid-template-columns: minmax(0, 1fr);
	gap: 16px;
	overflow-y: auto;
	padding-right: 2px;
	scrollbar-width: thin;
}

.panel {
	border-radius: 8px;
	background: rgba(255, 255, 255, .97);
	border: 1px solid #dde8e5;
	box-shadow: 0 14px 34px rgba(23, 42, 46, .07);
	padding: 18px;
}

.section-title {
	margin-bottom: 16px;
}

.section-title h3 {
	margin: 0 0 6px;
	font-size: 18px;
}

.section-title p {
	margin: 0;
	color: #6b7b80;
	line-height: 1.7;
}

.setting-row {
	display: grid;
	grid-template-columns: 320px minmax(0, 1fr);
	gap: 24px;
	align-items: center;
	padding: 16px 0;
	border-top: 1px solid #eef4f2;
}

.setting-row:first-of-type {
	border-top: 0;
}

.setting-row strong,
.switch-grid strong {
	display: block;
	font-size: 16px;
}

.setting-row span {
	display: block;
	margin-top: 8px;
	color: #6b7b80;
}

.form-grid,
.switch-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 14px;
}

.form-grid label,
.switch-grid div {
	padding: 16px;
	border-radius: 8px;
	border: 1px solid #e2ece9;
	background: #fbfdfc;
}

.form-grid span {
	display: block;
	margin-bottom: 10px;
	color: #516166;
	font-weight: 800;
}

.provider-card {
	display: grid;
	gap: 6px;
	padding: 12px;
	border-radius: 8px;
	background: #f7fbfa;
	border: 1px solid #dbe9e6;
}

.provider-card strong {
	color: #0b766f;
}

.provider-card em {
	color: #66787d;
	font-size: 13px;
	font-style: normal;
}

.switch-grid div {
	display: grid;
	grid-template-columns: minmax(0, 1fr) auto;
	gap: 8px 16px;
	align-items: center;
}

.switch-grid p {
	grid-column: 1 / 3;
	margin: 0;
	color: #6b7b80;
	line-height: 1.7;
}

@media (max-width: 960px) {
	.setting-row,
	.form-grid,
	.switch-grid {
		grid-template-columns: 1fr;
	}

	.switch-grid p {
		grid-column: auto;
	}
}
</style>
