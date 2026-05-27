import { RouteRecordRaw } from 'vue-router';

declare module 'vue-router' {
	interface RouteMeta {
		title?: string;
		isLink?: string;
		isHide?: boolean;
		isKeepAlive?: boolean;
		isAffix?: boolean;
		isIframe?: boolean;
		roles?: string[];
		icon?: string;
	}
}

const commonMeta = {
	isLink: '',
	isHide: false,
	isKeepAlive: true,
	isAffix: false,
	isIframe: false,
	roles: ['admin', 'common', 'others'],
};

export const dynamicRoutes: Array<RouteRecordRaw> = [
	{
		path: '/',
		name: '/',
		component: () => import('/@/layout/index.vue'),
		redirect: '/videoPredict',
		meta: {
			isKeepAlive: true,
		},
		children: [
			{
				path: '/data',
				name: 'data',
				component: () => import('/@/views/data/index.vue'),
				meta: {
					...commonMeta,
					title: '首页',
					icon: 'iconfont icon-shouye',
				},
			},
			{
				path: '/videoPredict',
				name: 'videoPredict',
				component: () => import('/@/views/videoPredict/index.vue'),
				meta: {
					...commonMeta,
					title: '录制视频检测',
					icon: 'iconfont icon-shipin1',
				},
			},
			{
				path: '/detectionResult',
				name: 'detectionResult',
				component: () => import('/@/views/demo/detectionResult/index.vue'),
				meta: {
					...commonMeta,
					title: '检测结果',
					icon: 'iconfont icon-jilu',
				},
			},
			{
				path: '/behaviorStats',
				name: 'behaviorStats',
				component: () => import('/@/views/demo/behaviorStats/index.vue'),
				meta: {
					...commonMeta,
					title: '行为统计',
					icon: 'iconfont icon-tongji',
				},
			},
			{
				path: '/aiIntervention',
				name: 'aiIntervention',
				component: () => import('/@/views/demo/aiIntervention/index.vue'),
				meta: {
					...commonMeta,
					title: 'AI辅助干预',
					icon: 'iconfont icon-xiaoxi',
				},
			},
			{
				path: '/interventionReport',
				name: 'interventionReport',
				redirect: '/detectionResult',
				meta: {
					...commonMeta,
					isHide: true,
					title: '检测结果',
					icon: 'iconfont icon-baobiao',
				},
			},
			{
				path: '/detectionHistory',
				name: 'detectionHistory',
				component: () => import('/@/views/demo/detectionHistory/index.vue'),
				meta: {
					...commonMeta,
					title: '检测历史',
					icon: 'iconfont icon-shipinjilu',
				},
			},
			{
				path: '/demoSettings',
				name: 'demoSettings',
				component: () => import('/@/views/demo/demoSettings/index.vue'),
				meta: {
					...commonMeta,
					title: '功能设置',
					icon: 'iconfont icon-shezhi',
				},
			},
			{
				path: '/imgPredict',
				name: 'imgPredict',
				component: () => import('/@/views/imgPredict/index.vue'),
				meta: {
					...commonMeta,
					title: '图片检测',
					icon: 'iconfont icon-tupian',
				},
			},
			{
				path: '/warningRecord',
				name: 'warningRecord',
				component: () => import('/@/views/warningRecord/index.vue'),
				meta: {
					...commonMeta,
					title: 'AI干预记录',
					icon: 'iconfont icon-xiaoxi',
					isHide: true,
				},
			},
			{
				path: '/videoRecord',
				name: 'videoRecord',
				component: () => import('/@/views/videoRecord/index.vue'),
				meta: {
					...commonMeta,
					title: '视频识别记录',
					icon: 'iconfont icon-shipinjilu',
					isHide: true,
				},
			},
			{
				path: '/imgRecord',
				name: 'imgRecord',
				component: () => import('/@/views/imgRecord/index.vue'),
				meta: {
					...commonMeta,
					title: '图片识别记录',
					icon: 'iconfont icon-tupianjilu',
					isHide: true,
				},
			},
			{
				path: '/cameraPredict',
				name: 'cameraPredict',
				component: () => import('/@/views/cameraPredict/index.vue'),
				meta: {
					...commonMeta,
					title: '摄像头检测',
					icon: 'iconfont icon-shexiangtou1',
					isHide: true,
				},
			},
			{
				path: '/cameraRecord',
				name: 'cameraRecord',
				component: () => import('/@/views/cameraRecord/index.vue'),
				meta: {
					...commonMeta,
					title: '摄像头记录',
					icon: 'iconfont icon-NVR',
					isHide: true,
				},
			},
			{
				path: '/usermanage',
				name: 'usermanage',
				component: () => import('/@/views/userManage/index.vue'),
				meta: {
					...commonMeta,
					title: '用户管理',
					roles: ['admin'],
					icon: 'iconfont icon-yonghuguanli',
					isHide: true,
				},
			},
			{
				path: '/personal',
				name: 'personal',
				component: () => import('/@/views/personal/index.vue'),
				meta: {
					...commonMeta,
					title: '个人中心',
					icon: 'iconfont icon-gerenzhongxin',
					isHide: true,
				},
			},
		],
	},
];

export const notFoundAndNoPower = [
	{
		path: '/:path(.*)*',
		name: 'notFound',
		component: () => import('/@/views/error/404.vue'),
		meta: {
			title: 'message.staticRoutes.notFound',
			isHide: true,
		},
	},
	{
		path: '/401',
		name: 'noPower',
		component: () => import('/@/views/error/401.vue'),
		meta: {
			title: 'message.staticRoutes.noPower',
			isHide: true,
		},
	},
];

export const staticRoutes: Array<RouteRecordRaw> = [
	{
		path: '/login',
		name: 'login',
		component: () => import('/@/views/login/index.vue'),
		meta: {
			title: '登录',
		},
	},
	{
		path: '/register',
		name: 'register',
		component: () => import('/@/views/login/register.vue'),
		meta: {
			title: '注册',
		},
	},
	{
		path: '/videoShow',
		name: 'videoShow',
		component: () => import('/@/views/videoRecord/show.vue'),
		meta: {
			title: '视频回放',
		},
	},
];
