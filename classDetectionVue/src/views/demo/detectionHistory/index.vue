<template>
	<DemoShell active="history" title="检测历史" :status="`${state.total} 条记录`" status-type="info">
		<div class="history-page">
			<section class="panel filter-panel">
				<div>
					<h3>历史检测查询</h3>
					<p>按录制课堂视频素材聚合同类检测记录，默认保留最新一次检测结果，避免重复记录影响比赛展示。</p>
				</div>
				<div class="filter-row">
					<el-input v-model="state.query.search3" clearable placeholder="按置信度/阈值查询" @keyup.enter="searchRecords" />
					<el-input v-model="state.query.search2" clearable placeholder="按模型权重查询" @keyup.enter="searchRecords" />
					<el-button type="primary" :loading="state.loading" @click="searchRecords">查询</el-button>
					<el-button @click="resetQuery">重置</el-button>
				</div>
			</section>

			<section class="panel">
				<el-table :data="state.records" v-loading="state.loading" height="100%">
					<el-table-column type="index" label="#" width="64" />
					<el-table-column label="视频素材" min-width="220" show-overflow-tooltip>
						<template #default="{ row }">
							<div class="source-cell">
								<strong>{{ sourceName(row.inputVideo) }}</strong>
								<span>{{ row.inputVideo || '未记录输入路径' }}</span>
							</div>
						</template>
					</el-table-column>
					<el-table-column prop="weight" label="检测模型" min-width="130" show-overflow-tooltip />
					<el-table-column prop="conf" label="置信度阈值" width="120" />
					<el-table-column prop="username" label="检测账号" width="120" show-overflow-tooltip />
					<el-table-column prop="startTime" label="检测时间" width="180" show-overflow-tooltip />
					<el-table-column label="预警事件" width="110">
						<template #default="{ row }">
							<el-tag :type="warningCount(row) ? 'warning' : 'info'">{{ warningCount(row) }} 条</el-tag>
						</template>
					</el-table-column>
					<el-table-column label="状态" width="110">
						<template #default="{ row }">
							<el-tag :type="row.outVideo ? 'success' : 'info'">{{ row.outVideo ? '已完成' : '仅记录' }}</el-tag>
						</template>
					</el-table-column>
					<el-table-column label="操作" width="240" fixed="right">
						<template #default="{ row }">
							<el-button link type="primary" @click="openPlayback(row)">查看回放</el-button>
							<el-button link @click="useAsCurrent(row)">用于展示</el-button>
							<el-button link type="danger" @click="deleteRecord(row)">删除</el-button>
						</template>
					</el-table-column>
				</el-table>
				<el-empty v-if="!state.loading && !state.records.length" description="暂无检测历史，请先完成一次录制视频检测" />
			</section>

			<el-pagination
				v-model:current-page="state.query.pageNum"
				v-model:page-size="state.query.pageSize"
				background
				layout="total, sizes, prev, pager, next, jumper"
				:page-sizes="[10, 20, 30]"
				:total="state.total"
				@size-change="loadRecords"
				@current-change="loadRecords"
			/>
		</div>
	</DemoShell>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue';
import { ElMessage } from 'element-plus';
import DemoShell from '/@/views/demo/components/DemoShell.vue';
import { demoState, syncWarningRecords } from '/@/views/demo/demoState';
import request from '/@/utils/request';

const state = reactive({
	loading: false,
	records: [] as any[],
	warnings: [] as any[],
	total: 0,
	query: {
		search: '',
		search2: '',
		search3: '',
		pageNum: 1,
		pageSize: 10,
	},
});

function sourceName(value: string) {
	const text = String(value || '').trim();
	return text.split(/[\\/]/).pop() || text || '课堂录制视频';
}

function recordKey(row: any) {
	const raw = String(row?.inputVideo || '').trim() || sourceName(row?.inputVideo);
	return raw
		.split(/[?#]/)[0]
		.replace(/\\/g, '/')
		.replace(/\/+/g, '/')
		.toLowerCase();
}

function recordTime(row: any) {
	const time = Date.parse(row?.startTime || '');
	return Number.isFinite(time) ? time : Number(row?.id || 0);
}

function uniqueLatestRecords(records: any[]) {
	const sorted = [...records].sort((a, b) => recordTime(b) - recordTime(a));
	const groups = new Map<string, any>();
	sorted.forEach((row) => {
		const key = recordKey(row) || String(row?.id || '');
		if (!groups.has(key)) {
			groups.set(key, {
				...row,
				duplicateIds: [],
				duplicateCount: 0,
			});
		}
		const group = groups.get(key);
		if (row?.id) group.duplicateIds.push(row.id);
		group.duplicateCount += 1;
	});
	return Array.from(groups.values());
}

function applyQuery(records: any[]) {
	const weight = state.query.search2.trim().toLowerCase();
	const conf = state.query.search3.trim().toLowerCase();
	return records.filter((row) => {
		const matchedWeight = !weight || String(row.weight || '').toLowerCase().includes(weight);
		const matchedConf = !conf || String(row.conf || '').toLowerCase().includes(conf);
		return matchedWeight && matchedConf;
	});
}

function warningCount(row: any) {
	const rowSource = sourceName(row.inputVideo).toLowerCase();
	if (!rowSource) return 0;
	return state.warnings.filter((item) => {
		const source = sourceName(item.videoSource || item.sourceName || '').toLowerCase();
		return source && (source === rowSource || source.includes(rowSource) || rowSource.includes(source));
	}).length;
}

async function loadWarnings() {
	try {
		const res = await request.get('/api/warningRecords/all');
		if (res?.code == 0 && Array.isArray(res.data)) {
			state.warnings = res.data;
			syncWarningRecords(res.data);
		}
	} catch (error) {
		state.warnings = [];
	}
}

async function loadRecords() {
	state.loading = true;
	try {
		const res = await request.get('/api/videoRecords/all');
		if (res?.code == 0 && Array.isArray(res.data)) {
			const filtered = applyQuery(uniqueLatestRecords(res.data));
			state.total = filtered.length;
			const maxPage = Math.max(1, Math.ceil(state.total / state.query.pageSize));
			if (state.query.pageNum > maxPage) state.query.pageNum = maxPage;
			const start = (state.query.pageNum - 1) * state.query.pageSize;
			state.records = filtered.slice(start, start + state.query.pageSize);
		} else {
			state.records = [];
			state.total = 0;
			ElMessage.error(res?.msg || '检测历史加载失败');
		}
	} catch (error) {
		state.records = [];
		state.total = 0;
		ElMessage.warning('后端未启动或检测历史接口不可用');
	} finally {
		state.loading = false;
	}
}

function searchRecords() {
	state.query.pageNum = 1;
	loadRecords();
}

function resetQuery() {
	state.query.search2 = '';
	state.query.search3 = '';
	state.query.pageNum = 1;
	loadRecords();
}

function openPlayback(row: any) {
	if (!row?.id) return;
	window.open(`http://localhost:8888/#/videoShow?id=${row.id}`);
}

function useAsCurrent(row: any) {
	demoState.material.sourceName = sourceName(row.inputVideo);
	demoState.material.status = row.outVideo ? '历史记录已选择' : '历史记录仅有原始素材';
	demoState.material.progress = row.outVideo ? 100 : 0;
	ElMessage.success('已同步为当前展示素材');
}

async function resolveDeleteIds(row: any) {
	const fallbackIds = Array.isArray(row.duplicateIds) && row.duplicateIds.length ? row.duplicateIds : [row.id];
	try {
		const res = await request.get('/api/videoRecords/all');
		if (res?.code == 0 && Array.isArray(res.data)) {
			const key = recordKey(row);
			const matchedIds = res.data.filter((item: any) => recordKey(item) === key && item?.id).map((item: any) => item.id);
			if (matchedIds.length) return matchedIds;
		}
	} catch (error) {
		// Fall back to the ids already carried by the visible grouped row.
	}
	return fallbackIds;
}

async function deleteRecord(row: any) {
	if (!row?.id) return;
	state.loading = true;
	try {
		const ids = await resolveDeleteIds(row);
		for (const id of ids) {
			const res = await request.delete(`/api/videoRecords/${id}`);
			if (res?.code != 0) {
				throw new Error(res?.msg || `记录 ${id} 删除失败`);
			}
		}
		ElMessage.success('删除成功，原视频素材已保留');
		const deletedKey = recordKey(row);
		state.records = state.records.filter((item) => recordKey(item) !== deletedKey);
		state.total = Math.max(0, state.total - 1);
		await loadRecords();
	} catch (error: any) {
		ElMessage.error(error?.message || '删除失败，请确认后端服务是否已启动');
	} finally {
		state.loading = false;
	}
}

onMounted(async () => {
	await Promise.all([loadWarnings(), loadRecords()]);
});
</script>

<style scoped lang="scss">
.history-page {
	height: 100%;
	display: grid;
	grid-template-rows: auto minmax(0, 1fr) auto;
	gap: 14px;
}

.panel {
	border-radius: 8px;
	background: rgba(255, 255, 255, .97);
	border: 1px solid #dde8e5;
	box-shadow: 0 14px 34px rgba(23, 42, 46, .07);
	padding: 16px;
	min-height: 0;
}

.filter-panel {
	display: grid;
	grid-template-columns: minmax(260px, 1fr) minmax(420px, 1.4fr);
	gap: 18px;
	align-items: center;
}

.filter-panel h3 {
	margin: 0 0 6px;
	font-size: 18px;
}

.filter-panel p {
	margin: 0;
	color: #6b7b80;
	line-height: 1.6;
}

.filter-row {
	display: grid;
	grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto auto;
	gap: 10px;
}

.source-cell {
	display: grid;
	gap: 4px;
}

.source-cell strong {
	color: #172327;
}

.source-cell span {
	color: #708086;
	font-size: 12px;
}

@media (max-width: 980px) {
	.filter-panel,
	.filter-row {
		grid-template-columns: 1fr;
	}
}
</style>
