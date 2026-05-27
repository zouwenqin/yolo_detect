<template>
	<div class="personal-center-bg">
		<div class="personal-center-card">
			<el-row :gutter="40">
				<!-- 左侧：头像和基础信息 -->
				<el-col :xs="24" :sm="24" :md="10" :lg="10" :xl="10" class="left-col">
					<div class="avatar-section">
						<el-upload
							v-model="state.form.avatar"
							ref="uploadFile"
							class="avatar-uploader"
							action="/api/files/upload"
							:show-file-list="false"
							:on-success="handleAvatarSuccessone"
						>
							<img v-if="imageUrl" :src="imageUrl" class="avatar" />
							<el-icon v-if="!imageUrl"><Plus /></el-icon>
						</el-upload>
						<div class="user-basic">
							<div class="user-name">{{ state.form.name || '未命名' }}</div>
							<div class="user-role">{{ state.form.role }}</div>
						</div>
					</div>
					<el-divider></el-divider>
					<div class="info-list">
						<div class="info-item"><span>账号：</span><el-input v-model="state.form.username" placeholder="请输入账号" size="small" clearable style="width: 220px" /></div>
						<div class="info-item"><span>姓名：</span><el-input v-model="state.form.name" placeholder="请输入姓名" size="small" clearable style="width: 220px" /></div>
						<div class="info-item"><span>角色：</span><el-input v-model="state.form.role" disabled size="small" style="width: 220px" /></div>
					</div>
				</el-col>
				<!-- 右侧：详细信息表单 -->
				<el-col :xs="24" :sm="24" :md="14" :lg="14" :xl="14" class="right-col">
					<el-form ref="roleDialogFormRef" :model="state.form" size="default" label-width="90px" class="detail-form">
						<el-form-item label="密码">
							<el-input v-model="state.form.password" placeholder="请输入密码" clearable type="password" style="width: 220px" />
						</el-form-item>
						<el-form-item label="性别">
							<el-input v-model="state.form.sex" placeholder="请输入性别" clearable style="width: 220px" />
						</el-form-item>
						<el-form-item label="Email">
							<el-input v-model="state.form.email" placeholder="请输入Email" clearable style="width: 220px" />
						</el-form-item>
						<el-form-item label="手机号码">
							<el-input v-model="state.form.tel" placeholder="请输入手机号码" clearable style="width: 220px" />
						</el-form-item>
					</el-form>
					<div class="btn-row">
						<el-button type="primary" @click="upData" size="default">确认修改</el-button>
					</div>
				</el-col>
			</el-row>
		</div>
	</div>
</template>

<script setup lang="ts" name="personal">
import { reactive, ref, onMounted } from 'vue';
import type { UploadInstance, UploadProps } from 'element-plus';
import { ElMessage } from 'element-plus';
import request from '/@/utils/request';
import { useUserInfo } from '/@/stores/userInfo';
import { storeToRefs } from 'pinia';
import { Plus } from '@element-plus/icons-vue';

const imageUrl = ref('');
const uploadFile = ref<UploadInstance>();

const handleAvatarSuccessone: UploadProps['onSuccess'] = (response, uploadFile) => {
	// console.log(response);
	imageUrl.value = URL.createObjectURL(uploadFile.raw!);
	state.form.avatar = response.data;
};

// 定义变量内容
const state = reactive({
	form: {} as any,
});
const stores = useUserInfo();
const { userInfos } = storeToRefs(stores);
// 初始化表格数据
const getTableData = () => {
	// console.log(userInfos.value.userName);
	request.get('/api/user/' + userInfos.value.userName).then((res) => {
		// console.log(res);
		if (res.code == 0) {
			state.form = res.data;
			if (state.form['role'] == 'admin') {
				state.form['role'] = '管理员';
			} else if (state.form['role'] == 'common') {
				state.form['role'] = '普通用户';
			} else if (state.form['role'] == 'others') {
				state.form['role'] = '其他用户';
			}
			imageUrl.value = state.form.avatar;
			// console.log(state.form);
		} else {
			ElMessage({
				type: 'error',
				message: res.msg,
			});
		}
	});
};

const upData = () => {
	if (state.form['role'] == '管理员') {
		state.form['role'] = 'admin';
	} else if (state.form['role'] == '普通用户') {
		state.form['role'] = 'common';
	} else if (state.form['role'] == '其他用户') {
		state.form['role'] = 'others';
	}
	request.post('/api/user/update', state.form).then((res) => {
		if (res.code == 0) {
			ElMessage.success('修改成功！');
		} else {
			ElMessage({
				type: 'error',
				message: res.msg,
			});
		}
	});
	setTimeout(() => {
		getTableData();
	}, 200);
};
// 页面加载时
onMounted(() => {
	getTableData();
});
</script>

<style scoped lang="scss">
.personal-center-bg {
	min-height: calc(100vh - 85px);
	background: linear-gradient(120deg, #e0e7ef 0%, #f8fafc 100%);
	display: flex;
	align-items: flex-start;
	justify-content: center;
	padding-top: 48px;
	box-sizing: border-box;
}
.personal-center-card {
	width: 900px;
	background: #fff;
	border-radius: 18px;
	box-shadow: 0 8px 32px 0 rgba(60, 80, 120, 0.12);
	padding: 32px 36px 24px 36px;
	margin: 0;
	max-height: 90vh;
	overflow: hidden;
	display: flex;
	flex-direction: column;
	justify-content: flex-start;
}
.left-col {
	display: flex;
	flex-direction: column;
	align-items: center;
	border-right: 1.5px solid #f0f0f0;
	min-height: 420px;
}
.right-col {
	display: flex;
	flex-direction: column;
	justify-content: center;
	padding-left: 36px;
}
.avatar-section {
	display: flex;
	flex-direction: column;
	align-items: center;
	margin-bottom: 18px;
}
.avatar-uploader {
	width: 120px;
	height: 120px;
	display: flex;
	justify-content: center;
	align-items: center;
	border: 2px dashed #b3c0d1;
	border-radius: 50%;
	margin-bottom: 16px;
	background: #f4f8fb;
	cursor: pointer;
	overflow: hidden;
}
.avatar-uploader .avatar {
	width: 120px;
	height: 120px;
	border-radius: 50%;
	object-fit: cover;
	display: block;
}
.user-basic {
	text-align: center;
}
.user-name {
	font-size: 22px;
	font-weight: 600;
	color: #2b3a55;
	margin-bottom: 4px;
}
.user-role {
	font-size: 15px;
	color: #6a7ba2;
	background: #f0f4fa;
	border-radius: 8px;
	padding: 2px 12px;
	display: inline-block;
}
.info-list {
	width: 100%;
	margin-top: 10px;
}
.info-item {
	font-size: 15px;
	color: #3a4a6b;
	margin-bottom: 10px;
	display: flex;
	align-items: center;
	span {
		color: #8a98b8;
		min-width: 60px;
		display: inline-block;
	}
}
.detail-form {
	margin-top: 10px;
	max-width: 350px;
}
.btn-row {
	display: flex;
	justify-content: flex-end;
	margin-top: 18px;
}
@media (max-width: 1000px) {
	.personal-center-card {
		width: 98vw;
		padding: 18px 2vw;
	}
	.right-col {
		padding-left: 0;
	}
}
</style>
