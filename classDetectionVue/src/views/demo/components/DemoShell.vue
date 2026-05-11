<template>
	<div class="demo-shell">
		<aside class="demo-sidebar">
			<div class="brand-block">
				<h2>课堂行为检测演示</h2>
				<p>基于录制素材的课堂行为识别与AI辅助干预系统</p>
			</div>

			<nav class="demo-nav">
				<button
					v-for="item in menus"
					:key="item.key"
					:class="{ active: active === item.key }"
					@click="router.push(item.path)"
				>
					<el-icon><component :is="item.icon" /></el-icon>
					<span>{{ item.label }}</span>
				</button>
			</nav>

			<div class="usage-card">
				<div class="usage-icon">
					<el-icon><TrendCharts /></el-icon>
				</div>
				<h3>使用说明</h3>
				<p>上传课堂录制视频，系统自动识别行为事件，并生成AI干预建议。</p>
			</div>
		</aside>

		<main class="demo-main">
			<header class="demo-topbar">
				<div class="title-row">
					<h1>{{ title }}</h1>
					<el-tag v-if="status" :type="statusType" effect="light">
						<el-icon><CircleCheckFilled /></el-icon>
						{{ status }}
					</el-tag>
				</div>
				<div class="top-actions">
					<slot name="actions">
						<el-button @click="router.push('/videoPredict')">
							<el-icon><FolderOpened /></el-icon>
							视频素材
						</el-button>
						<el-button @click="router.push('/interventionReport')">
							<el-icon><Document /></el-icon>
							检测报告
						</el-button>
						<el-button @click="router.push('/demoSettings')">
							<el-icon><Setting /></el-icon>
							系统设置
						</el-button>
					</slot>
				</div>
			</header>

			<section class="demo-content">
				<slot />
			</section>
		</main>
	</div>
</template>

<script setup lang="ts">
import { markRaw } from 'vue';
import { useRouter } from 'vue-router';
import {
	ChatDotRound,
	CircleCheckFilled,
	Document,
	DocumentChecked,
	FolderOpened,
	PieChart,
	Setting,
	Tickets,
	TrendCharts,
	VideoCameraFilled,
} from '@element-plus/icons-vue';

withDefaults(defineProps<{
	active: string;
	title: string;
	status?: string;
	statusType?: 'success' | 'warning' | 'info' | 'danger';
}>(), {
	status: '',
	statusType: 'success',
});

const router = useRouter();

const menus = [
	{ key: 'video', label: '视频检测', path: '/videoPredict', icon: markRaw(VideoCameraFilled) },
	{ key: 'result', label: '检测结果', path: '/detectionResult', icon: markRaw(DocumentChecked) },
	{ key: 'stats', label: '行为统计', path: '/behaviorStats', icon: markRaw(PieChart) },
	{ key: 'ai', label: 'AI 辅助干预', path: '/aiIntervention', icon: markRaw(ChatDotRound) },
	{ key: 'report', label: '干预报告', path: '/interventionReport', icon: markRaw(Tickets) },
	{ key: 'settings', label: '功能设置', path: '/demoSettings', icon: markRaw(Setting) },
];
</script>

<style scoped lang="scss">
.demo-shell {
	position: fixed;
	inset: 0;
	z-index: 2147483000;
	display: grid;
	grid-template-columns: 250px minmax(0, 1fr);
	background: #f7faf9;
	color: #172327;
	font-family: "Inter", "PingFang SC", "Microsoft YaHei", sans-serif;
}

.demo-sidebar {
	position: relative;
	display: flex;
	flex-direction: column;
	padding: 34px 18px 28px;
	background: rgba(255, 255, 255, 0.98);
	border-right: 1px solid #e5ecea;
	box-shadow: 12px 0 34px rgba(23, 42, 46, 0.06);
}

.brand-block h2 {
	margin: 0;
	font-size: 21px;
	font-weight: 800;
	letter-spacing: 0;
}

.brand-block p {
	margin: 12px 0 28px;
	color: #647276;
	font-size: 13px;
	line-height: 1.7;
}

.demo-nav {
	display: grid;
	gap: 10px;
}

.demo-nav button {
	height: 50px;
	padding: 0 16px;
	border: 0;
	border-radius: 8px;
	background: transparent;
	color: #56666b;
	display: flex;
	align-items: center;
	gap: 12px;
	font-size: 16px;
	text-align: left;
	cursor: pointer;
	transition: all 0.18s ease;
}

.demo-nav button:hover {
	background: #eef7f5;
	color: #007f78;
}

.demo-nav button.active {
	background: linear-gradient(135deg, #008f87 0%, #00a99d 100%);
	color: #fff;
	box-shadow: 0 12px 22px rgba(0, 143, 135, 0.24);
}

.demo-nav .el-icon {
	font-size: 20px;
}

.usage-card {
	margin-top: auto;
	padding: 28px 20px;
	border-radius: 8px;
	background: linear-gradient(180deg, rgba(245, 251, 250, 0.95), rgba(255, 255, 255, 0.98));
	box-shadow: 0 18px 44px rgba(23, 42, 46, 0.08);
	text-align: center;
}

.usage-icon {
	width: 66px;
	height: 66px;
	margin: 0 auto 14px;
	border-radius: 8px;
	background: #dff4f1;
	color: #008f87;
	display: flex;
	align-items: center;
	justify-content: center;
	font-size: 34px;
}

.usage-card h3 {
	margin: 0 0 12px;
	color: #008f87;
	font-size: 16px;
}

.usage-card p {
	margin: 0;
	color: #748287;
	line-height: 1.75;
	font-size: 13px;
}

.demo-main {
	min-width: 0;
	height: 100vh;
	display: flex;
	flex-direction: column;
	overflow: hidden;
	background:
		linear-gradient(120deg, rgba(250, 253, 252, 0.98), rgba(247, 249, 248, 0.94)),
		radial-gradient(circle at 68% 4%, rgba(0, 143, 135, 0.06), transparent 30%);
}

.demo-topbar {
	height: 78px;
	padding: 0 28px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 24px;
	flex-shrink: 0;
}

.title-row {
	display: flex;
	align-items: center;
	gap: 14px;
	min-width: 0;
}

.title-row h1 {
	margin: 0;
	font-size: 24px;
	font-weight: 800;
	letter-spacing: 0;
	white-space: nowrap;
}

.top-actions {
	display: flex;
	gap: 14px;
	flex-shrink: 0;
}

.demo-content {
	min-height: 0;
	flex: 1;
	padding: 0 26px 26px;
	overflow: hidden;
}

:deep(.el-button--primary) {
	background: #008f87;
	border-color: #008f87;
}

:deep(.el-button--primary:hover) {
	background: #00a99d;
	border-color: #00a99d;
}

:deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
	background: #e9f8f5;
	border-color: #008f87;
	color: #008f87;
	box-shadow: -1px 0 0 0 #008f87;
}

@media (max-width: 1180px) {
	.demo-shell {
		grid-template-columns: 204px minmax(0, 1fr);
	}

	.demo-sidebar {
		padding-left: 14px;
		padding-right: 14px;
	}

	.demo-nav button {
		padding: 0 12px;
		font-size: 15px;
	}

	.demo-content {
		padding: 0 16px 18px;
	}
}

@media (max-width: 860px) {
	.demo-shell {
		position: relative;
		min-height: 100vh;
		grid-template-columns: 1fr;
	}

	.demo-sidebar {
		display: none;
	}

	.demo-main {
		height: auto;
		min-height: 100vh;
	}

	.demo-content {
		overflow: visible;
	}
}
</style>
