<template>
	<DemoShell active="settings" title="功能设置" status="演示配置">
		<div class="settings-page">
			<section class="panel">
				<div class="section-title">
					<h3>检测阈值</h3>
					<p>此处为比赛演示配置，暂不直接修改后端推理参数。</p>
				</div>
				<div class="setting-row">
					<div>
						<strong>趴桌/睡觉触发阈值</strong>
						<span>连续或累计超过阈值后生成高风险检测事件</span>
					</div>
					<el-slider v-model="demoState.settings.lieDeskThreshold" :min="5" :max="30" show-input />
				</div>
				<div class="setting-row">
					<div>
						<strong>持续低头触发阈值</strong>
						<span>用于生成中风险课堂行为事件</span>
					</div>
					<el-slider v-model="demoState.settings.headDownThreshold" :min="5" :max="40" show-input />
				</div>
				<div class="setting-row">
					<div>
						<strong>模型置信度阈值</strong>
						<span>视频检测页会同步读取该默认值</span>
					</div>
					<el-slider v-model="demoState.settings.confidence" :min="10" :max="90" show-input />
				</div>
			</section>

			<section class="panel">
				<div class="section-title">
					<h3>模型与AI提供方</h3>
					<p>界面展示阿里千问/Kimi选择，接口继续复用现有建议生成服务。</p>
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
						<span>AI辅助干预模型</span>
						<el-radio-group v-model="demoState.provider">
							<el-radio-button label="qwen">阿里千问</el-radio-button>
							<el-radio-button label="kimi">Kimi</el-radio-button>
						</el-radio-group>
					</label>
				</div>
			</section>

			<section class="panel">
				<div class="section-title">
					<h3>隐私与报告模板</h3>
					<p>突出比赛演示版“不做实名追踪、以检测事件为单位”的表达。</p>
				</div>
				<div class="switch-grid">
					<div>
						<strong>脱敏事件展示</strong>
						<el-switch v-model="demoState.settings.anonymous" />
						<p>隐藏学生档案和姓名字段，仅展示检测事件。</p>
					</div>
					<div>
						<strong>保留处理后视频回放</strong>
						<el-switch v-model="demoState.settings.saveVideo" />
						<p>用于比赛验收回放，正式部署可关闭。</p>
					</div>
					<div>
						<strong>报告包含AI建议</strong>
						<el-switch v-model="demoState.settings.reportAdvice" />
						<p>在干预报告中输出教师沟通建议。</p>
					</div>
					<div>
						<strong>报告包含统计图</strong>
						<el-switch v-model="demoState.settings.reportStats" />
						<p>展示行为占比、趋势与重点事件概况。</p>
					</div>
				</div>
			</section>
		</div>
	</DemoShell>
</template>

<script setup lang="ts">
import DemoShell from '/@/views/demo/components/DemoShell.vue';
import { demoState } from '/@/views/demo/demoState';
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
