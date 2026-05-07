<template>
	<div class="warning-record-container layout-padding">
		<div class="warning-record-padding layout-padding-auto layout-padding-view">
			<div class="system-user-search mb15">
				<el-input v-model="state.tableData.param.search" size="default" placeholder="请输入识别用户" style="max-width: 180px" />
				<el-select v-model="state.tableData.param.riskLevel" clearable placeholder="风险等级" style="max-width: 160px; margin-left: 12px">
					<el-option label="高风险" value="high" />
					<el-option label="中风险" value="medium" />
					<el-option label="低风险" value="low" />
				</el-select>
				<el-select v-model="state.tableData.param.behaviorType" clearable placeholder="异常行为" style="max-width: 160px; margin-left: 12px">
					<el-option label="睡觉" value="sleep" />
					<el-option label="趴桌" value="lie_desk" />
					<el-option label="低头" value="head_down" />
					<el-option label="玩手机" value="phone" />
				</el-select>
				<el-button size="default" type="primary" class="ml10" @click="getTableData()">
					<el-icon><ele-Search /></el-icon>
					查询
				</el-button>
			</div>

			<el-table :data="state.tableData.data" v-loading="state.tableData.loading" style="width: 100%">
				<el-table-column prop="num" label="序号" width="80" align="center" />
				<el-table-column prop="riskLevel" label="风险等级" width="110" align="center">
					<template #default="scope">
						<el-tag :type="riskTagType(scope.row.riskLevel)">{{ riskText(scope.row.riskLevel) }}</el-tag>
					</template>
				</el-table-column>
				<el-table-column prop="behaviorType" label="异常行为" width="110" align="center">
					<template #default="scope">{{ behaviorText(scope.row.behaviorType) }}</template>
				</el-table-column>
				<el-table-column prop="durationSeconds" label="持续时长" width="110" align="center">
					<template #default="scope">{{ scope.row.durationSeconds || 0 }}s</template>
				</el-table-column>
				<el-table-column prop="reason" label="触发原因" min-width="220" show-overflow-tooltip />
				<el-table-column prop="advice" label="教师干预建议" min-width="320" show-overflow-tooltip />
				<el-table-column prop="username" label="识别用户" width="120" align="center" />
				<el-table-column prop="detectionType" label="来源" width="100" align="center">
					<template #default="scope">{{ scope.row.detectionType === 'camera' ? '摄像头' : '视频' }}</template>
				</el-table-column>
				<el-table-column prop="status" label="处理状态" width="110" align="center" />
				<el-table-column prop="triggerTime" label="触发时间" width="180" align="center" />
				<el-table-column label="操作" width="170" align="center">
					<template #default="scope">
						<el-button size="small" text type="primary" @click="markHandled(scope.row)">标记处理</el-button>
						<el-button size="small" text type="danger" @click="onRowDel(scope.row)">删除</el-button>
					</template>
				</el-table-column>
			</el-table>

			<el-pagination @size-change="onHandleSizeChange" @current-change="onHandleCurrentChange" class="mt15"
				:pager-count="5" :page-sizes="[10, 20, 30]" v-model:current-page="state.tableData.param.pageNum"
				background v-model:page-size="state.tableData.param.pageSize"
				layout="total, sizes, prev, pager, next, jumper" :total="state.tableData.total">
			</el-pagination>
		</div>
	</div>
</template>

<script setup lang="ts" name="warningRecord">
import { reactive, onMounted } from 'vue';
import { ElMessageBox, ElMessage } from 'element-plus';
import request from '/@/utils/request';
import { useUserInfo } from '/@/stores/userInfo';
import { storeToRefs } from 'pinia';

const stores = useUserInfo();
const { userInfos } = storeToRefs(stores);

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

const riskText = (risk: string) => ({ high: '高风险', medium: '中风险', low: '低风险', normal: '正常' } as any)[risk] || '正常';
const riskTagType = (risk: string) => ({ high: 'danger', medium: 'warning', low: 'info', normal: 'success' } as any)[risk] || 'success';
const behaviorText = (behavior: string) => ({ sleep: '睡觉', lie_desk: '趴桌', head_down: '低头', phone: '玩手机' } as any)[behavior] || behavior;

const getTableData = () => {
	state.tableData.loading = true;
	if (userInfos.value.userName !== 'admin') {
		state.tableData.param.search = userInfos.value.userName;
	}
	request.get('/api/warningRecords', { params: state.tableData.param }).then((res) => {
		state.tableData.loading = false;
		if (res.code == 0) {
			state.tableData.data = res.data.records.map((item: any, index: number) => ({ ...item, num: index + 1 }));
			state.tableData.total = res.data.total;
		} else {
			ElMessage.error(res.msg);
		}
	});
};

const markHandled = (row: any) => {
	request.post('/api/warningRecords/update', { ...row, status: '已处理' }).then((res) => {
		if (res.code == 0) {
			ElMessage.success('处理状态已更新');
			getTableData();
		} else {
			ElMessage.error(res.msg);
		}
	});
};

const onRowDel = (row: any) => {
	ElMessageBox.confirm('此操作将永久删除该预警记录，是否继续？', '提示', {
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

onMounted(() => {
	getTableData();
});
</script>

<style scoped lang="scss">
.warning-record-container {
	width: 100%;
	height: 100%;
}

.warning-record-padding {
	padding: 15px;
	background: #f6f8fb;
}
</style>
