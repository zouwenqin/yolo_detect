<template>
	<div class="intervention-record-container layout-padding">
		<div class="intervention-record-page layout-padding-auto layout-padding-view">
			<section class="page-header">
				<div>
					<p class="eyebrow">AI辅助干预记录</p>
					<h1>检测事件与沟通建议</h1>
					<p>汇总视频和图片素材产生的检测事件，展示AI生成的非诊断性教师沟通建议。</p>
				</div>
				<div class="header-stats">
					<div>
						<span>记录数</span>
						<strong>{{ state.tableData.total }}</strong>
					</div>
					<div>
						<span>待处理</span>
						<strong>{{ pendingCount }}</strong>
					</div>
				</div>
			</section>

			<section class="filter-panel">
				<el-input v-model="state.tableData.param.search" size="default" placeholder="按演示账号筛选" style="max-width: 190px" />
				<el-select v-model="state.tableData.param.riskLevel" clearable placeholder="风险研判" style="max-width: 160px">
					<el-option label="高风险" value="high" />
					<el-option label="中风险" value="medium" />
					<el-option label="低风险" value="low" />
				</el-select>
				<el-select v-model="state.tableData.param.behaviorType" clearable placeholder="检测行为" style="max-width: 170px">
					<el-option label="疑似睡觉" value="sleep" />
					<el-option label="趴桌" value="lie_desk" />
					<el-option label="持续低头" value="head_down" />
					<el-option label="玩手机" value="phone" />
				</el-select>
				<el-button type="primary" @click="getTableData()">查询记录</el-button>
			</section>

			<section class="table-panel">
				<el-table :data="state.tableData.data" v-loading="state.tableData.loading" style="width: 100%">
					<el-table-column prop="num" label="序号" width="72" align="center" />
					<el-table-column prop="detectionType" label="检测来源" width="110" align="center">
						<template #default="scope">{{ sourceText(scope.row.detectionType) }}</template>
					</el-table-column>
					<el-table-column prop="riskLevel" label="风险研判" width="112" align="center">
						<template #default="scope">
							<el-tag :type="riskTagType(scope.row.riskLevel)">{{ riskText(scope.row.riskLevel) }}</el-tag>
						</template>
					</el-table-column>
					<el-table-column prop="behaviorType" label="检测行为" width="120" align="center">
						<template #default="scope">{{ behaviorText(scope.row.behaviorType) }}</template>
					</el-table-column>
					<el-table-column prop="durationSeconds" label="持续时长" width="112" align="center">
						<template #default="scope">{{ durationText(scope.row.durationSeconds) }}</template>
					</el-table-column>
					<el-table-column prop="reason" label="事件摘要" min-width="220" show-overflow-tooltip />
					<el-table-column prop="advice" label="AI沟通建议" min-width="340" show-overflow-tooltip />
					<el-table-column prop="status" label="处理状态" width="110" align="center">
						<template #default="scope">
							<el-tag :type="scope.row.status === '已处理' ? 'success' : 'warning'">{{ scope.row.status || '未处理' }}</el-tag>
						</template>
					</el-table-column>
					<el-table-column prop="triggerTime" label="生成时间" width="178" align="center" />
					<el-table-column label="操作" width="170" align="center">
						<template #default="scope">
							<el-button size="small" text type="primary" @click="markHandled(scope.row)">标记完成</el-button>
							<el-button size="small" text type="danger" @click="onRowDel(scope.row)">删除</el-button>
						</template>
					</el-table-column>
				</el-table>

				<el-pagination
					@size-change="onHandleSizeChange"
					@current-change="onHandleCurrentChange"
					class="mt15"
					:pager-count="5"
					:page-sizes="[10, 20, 30]"
					v-model:current-page="state.tableData.param.pageNum"
					background
					v-model:page-size="state.tableData.param.pageSize"
					layout="total, sizes, prev, pager, next, jumper"
					:total="state.tableData.total"
				/>
			</section>
		</div>
	</div>
</template>

<script setup lang="ts" name="warningRecord">
import { computed, reactive, onMounted } from 'vue';
import { ElMessageBox, ElMessage } from 'element-plus';
import request from '/@/utils/request';

const state = reactive({
	tableData: {
		data: [] as any[],
		total: 0,
		loading: false,
		param: {
			search: '',
			riskLevel: '',
			behaviorType: '',
			pageNum: 1,
			pageSize: 10,
		},
	},
});

const pendingCount = computed(() => state.tableData.data.filter((item) => (item.status || '未处理') === '未处理').length);
const riskText = (risk: string) => ({ high: '高风险', medium: '中风险', low: '低风险', normal: '正常' } as any)[risk] || '正常';
const riskTagType = (risk: string) => ({ high: 'danger', medium: 'warning', low: 'info', normal: 'success' } as any)[risk] || 'success';
const behaviorText = (behavior: string) => ({ sleep: '疑似睡觉', lie_desk: '趴桌', head_down: '持续低头', phone: '玩手机' } as any)[behavior] || behavior || '课堂行为';
const sourceText = (source: string) => ({ video: '视频素材', image: '图片素材', camera: '摄像头' } as any)[source] || '检测素材';
const durationText = (seconds: number) => {
	const value = Number(seconds || 0);
	if (!value) return '图片单帧';
	return value >= 60 ? `${Math.round(value / 60)}分钟` : `${Math.round(value)}s`;
};

const getTableData = () => {
	state.tableData.loading = true;
	request.get('/api/warningRecords', { params: state.tableData.param }).then((res) => {
		state.tableData.loading = false;
		if (res.code == 0) {
			state.tableData.data = res.data.records.map((item: any, index: number) => ({ ...item, num: index + 1 }));
			state.tableData.total = res.data.total;
		} else {
			ElMessage.error(res.msg);
		}
	}).catch(() => {
		state.tableData.loading = false;
		ElMessage.error('AI干预记录加载失败');
	});
};

const markHandled = (row: any) => {
	request.post('/api/warningRecords/update', { ...row, status: '已处理' }).then((res) => {
		if (res.code == 0) {
			ElMessage.success('干预记录已标记完成');
			getTableData();
		} else {
			ElMessage.error(res.msg);
		}
	});
};

const onRowDel = (row: any) => {
	ElMessageBox.confirm('此操作将删除该AI干预记录，是否继续？', '提示', {
		confirmButtonText: '确认',
		cancelButtonText: '取消',
		type: 'warning',
	}).then(() => {
		request.delete('/api/warningRecords/' + row.id).then((res) => {
			if (res.code == 0) {
				ElMessage.success('删除成功');
				getTableData();
			} else {
				ElMessage.error(res.msg);
			}
		});
	}).catch(() => {});
};

const onHandleSizeChange = (val: number) => {
	state.tableData.param.pageSize = val;
	getTableData();
};

const onHandleCurrentChange = (val: number) => {
	state.tableData.param.pageNum = val;
	getTableData();
};

onMounted(getTableData);
</script>

<style scoped lang="scss">
.intervention-record-container {
	width: 100%;
	min-height: 100%;
	background: #f5f8f7;
	color: #1f2f35;
}

.intervention-record-page {
	padding: 20px;
	background: linear-gradient(180deg, #f7fbfa 0%, #f4f7f6 100%);
}

.page-header,
.filter-panel,
.table-panel {
	background: rgba(255, 255, 255, 0.96);
	border: 1px solid #e3eeeb;
	border-radius: 8px;
	box-shadow: 0 14px 34px rgba(42, 69, 77, 0.08);
}

.page-header {
	padding: 24px 28px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 24px;
	margin-bottom: 16px;
}

.page-header h1 {
	margin: 0;
	font-size: 28px;
}

.page-header p {
	margin: 10px 0 0;
	color: #66787d;
}

.eyebrow {
	margin: 0 0 8px;
	color: #2aa79b;
	font-size: 13px;
	font-weight: 700;
}

.header-stats {
	display: flex;
	gap: 12px;
}

.header-stats div {
	min-width: 116px;
	padding: 14px;
	border-radius: 8px;
	background: #edf8f5;
	display: flex;
	flex-direction: column;
	gap: 6px;
}

.header-stats span {
	color: #60737a;
}

.header-stats strong {
	font-size: 24px;
}

.filter-panel {
	padding: 14px;
	display: flex;
	gap: 12px;
	flex-wrap: wrap;
	margin-bottom: 16px;
}

.table-panel {
	padding: 18px;
}
</style>
