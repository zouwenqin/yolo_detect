import { computed, reactive } from 'vue';

export type RiskLevel = 'normal' | 'low' | 'medium' | 'high';
export type SourceType = 'video' | 'image';
export type Provider = 'qwen' | 'kimi';

export interface DemoEvent {
	eventId: string;
	sourceType: SourceType;
	sourceName: string;
	behaviorType: string;
	riskLevel: RiskLevel;
	durationText: string;
	confidence: string;
	reason: string;
	promptPreview: string;
	advice: string;
	status: string;
	createdAt: string;
	provider: Provider;
}

export interface DemoStat {
	key: string;
	label: string;
	duration: string;
	ratio: string;
	count: number;
	confidence: string;
	tone: string;
	value: number;
}

const defaultAdvice = '建议课后以关心身体状态为切入点进行简短沟通，避免当众批评或贴标签。可询问近期睡眠、课程压力和实训任务完成情况；如多次出现类似行为，建议同步辅导员或心理老师做后续跟进。';

export const behaviorLabelMap: Record<string, string> = {
	raise_hand: '举手互动',
	read: '阅读',
	write: '书写',
	phone: '疑似玩手机',
	head_down: '持续低头',
	lie_desk: '趴桌',
	sleep: '疑似睡觉',
	focus: '专注学习',
	none: '未形成风险事件',
};

export const riskLabelMap: Record<RiskLevel, string> = {
	normal: '正常',
	low: '低',
	medium: '中',
	high: '高',
};

export const demoState = reactive({
	hasLiveData: false,
	material: {
		sourceName: '课堂录制_实训课程_片段01.mp4',
		resolution: '1920×1080',
		duration: '00:28:47',
		fps: '25fps',
		status: '等待上传素材',
		progress: 0,
	},
	provider: 'qwen' as Provider,
	selectedEventId: 'EVT-001',
	events: [
		{
			eventId: 'EVT-001',
			sourceType: 'video',
			sourceName: '课堂录制_实训课程_片段01.mp4',
			behaviorType: 'lie_desk',
			riskLevel: 'high',
			durationText: '15分03秒',
			confidence: '92.4%',
			reason: '画面中央出现长时间趴桌行为，头部持续贴近桌面且未抬头。',
			promptPreview: '',
			advice: defaultAdvice,
			status: '待跟进',
			createdAt: '2026-05-11 10:28',
			provider: 'qwen',
		},
		{
			eventId: 'EVT-002',
			sourceType: 'video',
			sourceName: '课堂录制_实训课程_片段01.mp4',
			behaviorType: 'head_down',
			riskLevel: 'medium',
			durationText: '8分12秒',
			confidence: '86.8%',
			reason: '后排区域检测到持续低头，可能与疲劳、走神或设备使用有关。',
			promptPreview: '',
			advice: '建议教师结合课堂任务完成情况观察，不急于判断原因。课后可用开放式问题了解学生是否听懂课程内容，必要时安排同伴协作或短时休息。',
			status: '观察中',
			createdAt: '2026-05-11 10:36',
			provider: 'qwen',
		},
		{
			eventId: 'EVT-003',
			sourceType: 'video',
			sourceName: '课堂录制_实训课程_片段01.mp4',
			behaviorType: 'phone',
			riskLevel: 'low',
			durationText: '2分45秒',
			confidence: '78.5%',
			reason: '局部区域出现疑似玩手机行为，可作为课堂专注度异常记录。',
			promptPreview: '',
			advice: '建议先通过课堂巡视或任务提醒进行温和干预，避免直接公开批评。若重复出现，可单独了解是否存在学习困难或其他干扰因素。',
			status: '已记录',
			createdAt: '2026-05-11 10:41',
			provider: 'kimi',
		},
	] as DemoEvent[],
	stats: [
		{ key: 'lie_desk', label: '趴桌', duration: '18分24秒', ratio: '10.7%', count: 5, confidence: '高', tone: 'danger', value: 18 },
		{ key: 'sleep', label: '疑似睡觉', duration: '12分11秒', ratio: '7.1%', count: 3, confidence: '中', tone: 'warm', value: 12 },
		{ key: 'head_down', label: '持续低头', duration: '28分36秒', ratio: '16.6%', count: 8, confidence: '中', tone: 'amber', value: 28 },
		{ key: 'phone', label: '疑似玩手机', duration: '6分45秒', ratio: '3.9%', count: 4, confidence: '高', tone: 'purple', value: 7 },
		{ key: 'focus', label: '专注学习', duration: '102分18秒', ratio: '59.6%', count: 18, confidence: '高', tone: 'green', value: 102 },
	] as DemoStat[],
	aiHistory: [] as DemoEvent[],
	settings: {
		lieDeskThreshold: 10,
		headDownThreshold: 15,
		confidence: 50,
		model: 'class.pt',
		saveVideo: true,
		anonymous: true,
		reportAdvice: true,
		reportStats: true,
	},
});

demoState.events.forEach((event) => {
	event.promptPreview = buildPrompt(event);
});
demoState.aiHistory = demoState.events.slice(0, 2);

export const currentEvent = computed(() => {
	return demoState.events.find((event) => event.eventId === demoState.selectedEventId) || demoState.events[0];
});

export function behaviorText(behaviorType: string) {
	return behaviorLabelMap[behaviorType] || behaviorType || '检测事件';
}

export function riskText(level: RiskLevel | string) {
	return riskLabelMap[level as RiskLevel] || '正常';
}

export function riskTagType(level: RiskLevel | string) {
	const map: Record<string, string> = {
		normal: 'success',
		low: 'info',
		medium: 'warning',
		high: 'danger',
	};
	return map[level] || 'success';
}

export function setCurrentEvent(eventId: string) {
	demoState.selectedEventId = eventId;
}

export function buildPrompt(event: Pick<DemoEvent, 'eventId' | 'behaviorType' | 'riskLevel' | 'durationText' | 'reason'>) {
	return `检测事件 ${event.eventId}，检测到${behaviorText(event.behaviorType)}行为，持续时长${event.durationText}，风险等级${riskText(event.riskLevel)}。触发依据：${event.reason}。请生成面向教师的非诊断沟通建议，语气温和，避免当众批评，必要时建议联系辅导员、心理老师或家长。`;
}

export function fallbackAdvice(event: Pick<DemoEvent, 'behaviorType' | 'riskLevel' | 'durationText'>) {
	const behavior = behaviorText(event.behaviorType);
	if (event.riskLevel === 'high') {
		return `针对${behavior}持续${event.durationText}的情况，建议教师课后单独、温和询问学生身体状态和近期睡眠情况，不在课堂公开点名。若后续仍频繁出现，可联系辅导员或心理老师共同跟进。`;
	}
	if (event.riskLevel === 'medium') {
		return `建议先结合课堂任务完成情况观察${behavior}是否持续出现。课后可用开放式问题了解学生是否存在疲劳、压力或学习困难，并提供可执行的小任务支持。`;
	}
	return `建议以课堂提醒和学习支持为主，记录本次${behavior}事件即可。若同类事件反复出现，再进行一对一沟通和后续跟进。`;
}

export function upsertEvent(input: Partial<DemoEvent>) {
	const eventId = input.eventId || `EVT-${String(demoState.events.length + 1).padStart(3, '0')}`;
	const existing = demoState.events.find((item) => item.eventId === eventId);
	const event: DemoEvent = {
		eventId,
		sourceType: input.sourceType || 'video',
		sourceName: input.sourceName || demoState.material.sourceName,
		behaviorType: input.behaviorType || 'none',
		riskLevel: (input.riskLevel || 'normal') as RiskLevel,
		durationText: input.durationText || '0秒',
		confidence: input.confidence || '78.5%',
		reason: input.reason || '检测到课堂行为事件，建议结合课程场景进行研判。',
		promptPreview: input.promptPreview || '',
		advice: input.advice || '',
		status: input.status || '待跟进',
		createdAt: input.createdAt || formatDateTime(new Date()),
		provider: input.provider || demoState.provider,
	};
	event.promptPreview = event.promptPreview || buildPrompt(event);
	event.advice = event.advice || fallbackAdvice(event);
	if (existing) {
		Object.assign(existing, event);
	} else {
		demoState.events.unshift(event);
	}
	demoState.selectedEventId = event.eventId;
	return event;
}

export function applyAdvice(advice: string, provider: Provider = demoState.provider) {
	if (!currentEvent.value) return;
	currentEvent.value.advice = advice;
	currentEvent.value.provider = provider;
	currentEvent.value.promptPreview = buildPrompt(currentEvent.value);
	const historyItem = { ...currentEvent.value };
	demoState.aiHistory = [historyItem, ...demoState.aiHistory.filter((item) => item.eventId !== historyItem.eventId)].slice(0, 6);
}

export function updateStatsFromLabels(labels: string[]) {
	const normalized = labels.map(normalizeBehavior);
	const bucket = demoState.stats.reduce<Record<string, DemoStat>>((map, item) => {
		map[item.key] = item;
		return map;
	}, {});
	normalized.forEach((label) => {
		const key = ['raise_hand', 'read', 'write'].includes(label) ? 'focus' : label;
		if (bucket[key]) {
			bucket[key].count += 1;
			bucket[key].value += 1;
			bucket[key].duration = formatMinuteSecond(bucket[key].value * 60 + bucket[key].count * 8);
		}
	});
}

export function applyProtocolPayload(payload: any) {
	if (!payload || typeof payload !== 'object') return;
	demoState.hasLiveData = true;
	if (payload.sourceName) demoState.material.sourceName = payload.sourceName;
	if (typeof payload.progress === 'number') demoState.material.progress = Math.round(payload.progress);

	if (Array.isArray(payload.behaviorStats) && payload.behaviorStats.length) {
		const nextStats = payload.behaviorStats
			.filter((item: any) => ['lie_desk', 'sleep', 'head_down', 'phone', 'focus'].includes(item.behaviorType))
			.map((item: any) => protocolStatToDemoStat(item));
		if (nextStats.length) {
			demoState.stats.splice(0, demoState.stats.length, ...nextStats);
		}
	}

	const warning = payload.warningState?.warning;
	if (warning) {
		upsertEvent(protocolWarningToDemoEvent(warning, payload));
	}
	if (Array.isArray(payload.events)) {
		payload.events.slice().reverse().forEach((event: any) => {
			upsertEvent(protocolWarningToDemoEvent(event, payload));
		});
	}
}

export function syncWarningRecords(records: any[]) {
	if (!Array.isArray(records) || !records.length) return;
	records.slice(0, 20).reverse().forEach((record) => {
		upsertEvent({
			eventId: record.eventId || `WR-${record.id || record.triggerTime || demoState.events.length + 1}`,
			sourceType: record.detectionType === 'image' ? 'image' : 'video',
			sourceName: record.videoSource || record.sourceName || demoState.material.sourceName,
			behaviorType: record.behaviorType || 'none',
			riskLevel: record.riskLevel || 'normal',
			durationText: record.durationText || formatMinuteSecond(Number(record.durationSeconds || 0)),
			confidence: record.confidence ? `${Math.round(Number(record.confidence) * 100)}%` : '88.0%',
			reason: record.reason || '后端检测事件记录',
			advice: record.advice || fallbackAdvice(record),
			status: record.status || '待跟进',
			createdAt: record.triggerTime || record.createdAt || '',
			provider: record.provider || demoState.provider,
		});
	});
}

export function normalizeBehavior(label: string) {
	const raw = String(label || '').toLowerCase();
	const map: Record<string, string> = {
		raise_hand: 'raise_hand',
		hand: 'raise_hand',
		read: 'read',
		reading: 'read',
		write: 'write',
		writing: 'write',
		phone: 'phone',
		head_down: 'head_down',
		low_head: 'head_down',
		lie_desk: 'lie_desk',
		desk: 'lie_desk',
		sleep: 'sleep',
		举手: 'raise_hand',
		阅读: 'read',
		读书: 'read',
		写字: 'write',
		书写: 'write',
		手机: 'phone',
		低头: 'head_down',
		趴桌: 'lie_desk',
		靠桌子: 'lie_desk',
		睡觉: 'sleep',
	};
	return map[raw] || map[label] || raw;
}

function protocolStatToDemoStat(item: any): DemoStat {
	const key = item.behaviorType || 'none';
	const durationSeconds = Number(item.durationSeconds || 0);
	const ratio = Number(item.ratio || 0);
	const confidence = Number(item.confidence || 0);
	const toneMap: Record<string, string> = {
		lie_desk: 'danger',
		sleep: 'warm',
		head_down: 'amber',
		phone: 'purple',
		focus: 'green',
	};
	return {
		key,
		label: item.behaviorName || behaviorText(key),
		duration: item.durationText || formatMinuteSecond(durationSeconds),
		ratio: `${ratio.toFixed ? ratio.toFixed(1) : ratio}%`,
		count: Number(item.count || 0),
		confidence: confidence >= 0.9 ? '高' : confidence >= 0.75 ? '中' : confidence > 0 ? '低' : '-',
		tone: toneMap[key] || 'green',
		value: Math.round(durationSeconds / 60),
	};
}

function protocolWarningToDemoEvent(warning: any, payload: any): Partial<DemoEvent> {
	const confidence = Number(warning.confidence || 0);
	return {
		eventId: warning.eventId || `EVT-${String(demoState.events.length + 1).padStart(3, '0')}`,
		sourceType: warning.sourceType || payload.sourceType || 'video',
		sourceName: warning.sourceName || payload.sourceName || demoState.material.sourceName,
		behaviorType: warning.behaviorType || 'none',
		riskLevel: warning.riskLevel || 'normal',
		durationText: warning.durationText || formatMinuteSecond(Number(warning.durationSeconds || 0)),
		confidence: confidence ? `${Math.round(confidence * 100)}%` : '88.0%',
		reason: warning.reason || payload.warningState?.reason || '检测事件达到触发阈值',
		advice: warning.advice || '',
		status: warning.status || '待跟进',
		createdAt: warning.triggerTime || payload.timestamp || '',
		provider: warning.provider || demoState.provider,
	};
}

export function formatMinuteSecond(seconds: number) {
	const safe = Math.max(0, Math.round(seconds));
	return `${Math.floor(safe / 60)}分${String(safe % 60).padStart(2, '0')}秒`;
}

export function exportReportText() {
	const event = currentEvent.value;
	return [
		'课堂行为检测与AI辅助干预报告',
		`素材名称：${demoState.material.sourceName}`,
		`检测事件：${event.eventId}`,
		`异常行为：${behaviorText(event.behaviorType)}`,
		`风险等级：${riskText(event.riskLevel)}`,
		`持续时长：${event.durationText}`,
		`触发依据：${event.reason}`,
		`AI模型：${event.provider === 'kimi' ? 'Kimi' : '阿里千问'}`,
		`沟通建议：${event.advice}`,
		'说明：本报告仅用于课堂行为事件研判和教师沟通辅助，不作为心理诊断结论。',
	].join('\n');
}

function formatDateTime(date: Date) {
	const pad = (value: number) => String(value).padStart(2, '0');
	return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
