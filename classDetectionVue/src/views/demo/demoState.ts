import { computed, reactive } from 'vue';

export type RiskLevel = 'normal' | 'low' | 'medium' | 'high';
export type SourceType = 'video' | 'image';
export type Provider = 'minmax';

export interface DemoEvent {
	eventId: string;
	sourceType: SourceType;
	sourceName: string;
	behaviorType: string;
	riskLevel: RiskLevel;
	durationSeconds?: number;
	durationText: string;
	confidence: string;
	reason: string;
	promptPreview: string;
	advice: string;
	status: string;
	createdAt: string;
	provider: Provider;
	isSample?: boolean;
}

export interface FocusClue extends DemoEvent {
	clueId: string;
	eventIds: string[];
	eventCount: number;
	evidenceText: string;
	timeRange: string;
	teacherHint: string;
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
	provider: 'minmax' as Provider,
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
			provider: 'minmax',
			isSample: true,
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
			provider: 'minmax',
			isSample: true,
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
			provider: 'minmax',
			isSample: true,
		},
	] as DemoEvent[],
	stats: [
		{ key: 'pending', label: '等待算法结果', duration: '0秒', ratio: '0.0%', count: 0, confidence: '-', tone: 'green', value: 0 },
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
		manualReview: true,
		nonDiagnostic: true,
	},
});

demoState.events.forEach((event) => {
	event.promptPreview = buildPrompt(event);
});
demoState.aiHistory = demoState.events.slice(0, 2);

export const currentEvent = computed(() => {
	return demoState.events.find((event) => event.eventId === demoState.selectedEventId) || demoState.events[0];
});

export const realEvents = computed(() => demoState.events.filter((event) => !event.isSample));

export const focusClues = computed<FocusClue[]>(() => {
	const groups = new Map<string, DemoEvent[]>();
	realEvents.value.forEach((event) => {
		const key = `${event.behaviorType || 'none'}::${event.riskLevel || 'normal'}`;
		if (!groups.has(key)) groups.set(key, []);
		groups.get(key)!.push(event);
	});
	return Array.from(groups.values()).map(eventsToFocusClue).sort((a, b) => {
		const riskDelta = riskWeight(b.riskLevel) - riskWeight(a.riskLevel);
		if (riskDelta) return riskDelta;
		return Number(b.durationSeconds || 0) - Number(a.durationSeconds || 0);
	});
});

export const topFocusClues = computed(() => focusClues.value.slice(0, 3));

export const currentFocusClue = computed(() => {
	return focusClues.value.find((clue) => clue.eventIds.includes(demoState.selectedEventId)) || focusClues.value[0];
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

export function parseDurationSeconds(durationText = '') {
	const text = String(durationText || '').trim();
	if (!text) return 0;
	const minuteSecond = text.match(/(\d+(?:\.\d+)?)\s*(?:分|m|min|minute|minutes)\s*(\d+(?:\.\d+)?)?\s*(?:秒|s|sec|second|seconds)?/i);
	if (minuteSecond) return Math.round(Number(minuteSecond[1] || 0) * 60 + Number(minuteSecond[2] || 0));
	const secondOnly = text.match(/(\d+(?:\.\d+)?)\s*(?:秒|s|sec|second|seconds)/i);
	if (secondOnly) return Math.round(Number(secondOnly[1] || 0));
	const clock = text.match(/^(?:(\d+):)?(\d{1,2}):(\d{1,2})$/);
	if (clock) return Number(clock[1] || 0) * 3600 + Number(clock[2] || 0) * 60 + Number(clock[3] || 0);
	const fallback = Number(text.replace(/[^\d.]/g, ''));
	return Number.isFinite(fallback) ? Math.round(fallback) : 0;
}

export function upsertEvent(input: Partial<DemoEvent>) {
	const eventId = input.eventId || `EVT-${String(demoState.events.length + 1).padStart(3, '0')}`;
	const existing = demoState.events.find((item) => item.eventId === eventId);
	const durationText = input.durationText || '0秒';
	const event: DemoEvent = {
		eventId,
		sourceType: input.sourceType || 'video',
		sourceName: input.sourceName || demoState.material.sourceName,
		behaviorType: input.behaviorType || 'none',
		riskLevel: (input.riskLevel || 'normal') as RiskLevel,
		durationSeconds: Number(input.durationSeconds || 0) || parseDurationSeconds(durationText),
		durationText,
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
			.filter((item: any) => ['lie_desk', 'sleep', 'head_down', 'phone', 'focus', 'other_action'].includes(item.behaviorType))
			.map((item: any) => protocolStatToDemoStat(item));
		if (nextStats.length) {
			demoState.stats.splice(0, demoState.stats.length, ...nextStats);
		}
	}

	const warning = payload.warningState?.warning;
	if (warning) {
		clearSampleEvents();
		upsertEvent(protocolWarningToDemoEvent(warning, payload));
	}
	if (Array.isArray(payload.events)) {
		if (payload.events.length) clearSampleEvents();
		payload.events.slice().reverse().forEach((event: any) => {
			upsertEvent(protocolWarningToDemoEvent(event, payload));
		});
	}
}

export function syncWarningRecords(records: any[], sourceName = '') {
	if (!Array.isArray(records)) return;
	const normalizedRecords = records
		.filter(Boolean)
		.sort((a, b) => recordTimestamp(a) - recordTimestamp(b));
	if (!normalizedRecords.length) {
		if (sourceName) resetStatsForSource(sourceName);
		return;
	}
	const latestRecord = normalizedRecords[normalizedRecords.length - 1];
	const latestSourceKey = sourceName ? sourceNameKey(sourceName) : recordSourceKey(latestRecord);
	const matchedRecords = latestSourceKey
		? normalizedRecords.filter((record) => recordMatchesSource(record, latestSourceKey))
		: normalizedRecords;
	const eventRecords = matchedRecords.slice(-20);
	const statsRecords = sourceName ? matchedRecords : eventRecords;
	if (!eventRecords.length) {
		if (sourceName) resetStatsForSource(sourceName);
		return;
	}
	clearSampleEvents();
	demoState.hasLiveData = true;
	if (sourceName) demoState.material.sourceName = formatSourceName(sourceName);
	const selectedIds = new Set(eventRecords.map((record) => warningRecordEventId(record)));
	demoState.events.splice(0, demoState.events.length, ...demoState.events.filter((event) => selectedIds.has(event.eventId)));
	demoState.aiHistory = demoState.aiHistory.filter((event) => selectedIds.has(event.eventId));
	const syncedStats = warningRecordsToStats(statsRecords);
	if (syncedStats.length) demoState.stats.splice(0, demoState.stats.length, ...syncedStats);
	eventRecords.forEach((record) => {
		const durationSeconds = Number(record.durationSeconds || 0);
		const durationText = record.durationText || formatMinuteSecond(durationSeconds);
		const behaviorType = normalizeBehavior(record.behaviorType || record.behaviorName || record.type || 'none');
		const riskLevel = normalizeRisk(record.riskLevel);
		upsertEvent({
			eventId: warningRecordEventId(record),
			sourceType: record.detectionType === 'image' ? 'image' : 'video',
			sourceName: formatSourceName(record.videoSource || record.sourceName || demoState.material.sourceName),
			behaviorType,
			riskLevel,
			durationSeconds,
			durationText,
			confidence: formatConfidence(record.confidence),
			reason: record.reason || '\u540e\u7aef\u68c0\u6d4b\u4e8b\u4ef6\u8bb0\u5f55',
			advice: record.advice || fallbackAdvice({ behaviorType, riskLevel, durationText }),
			status: record.status || '\u5f85\u8ddf\u8fdb',
			createdAt: record.triggerTime || record.createdAt || '',
			provider: record.provider || demoState.provider,
		});
	});
}

export function clearSampleEvents() {
	if (!demoState.events.some((event) => event.isSample)) return;
	const nextEvents = demoState.events.filter((event) => !event.isSample);
	demoState.events.splice(0, demoState.events.length, ...nextEvents);
	demoState.aiHistory = demoState.aiHistory.filter((event) => !event.isSample);
	if (!demoState.events.some((event) => event.eventId === demoState.selectedEventId)) {
		demoState.selectedEventId = demoState.events[0]?.eventId || '';
	}
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
		lie_down: 'lie_desk',
		normal: 'focus',
		focus: 'focus',
		other_action: 'other_action',
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
		other_action: 'green',
	};
	return {
		key,
		label: item.behaviorName || behaviorText(key),
		duration: item.durationText || formatMinuteSecond(durationSeconds),
		ratio: `${ratio.toFixed ? ratio.toFixed(1) : ratio}%`,
		count: Number(item.count || 0),
		confidence: confidence >= 0.9 ? '高' : confidence >= 0.75 ? '中' : confidence > 0 ? '低' : '-',
		tone: toneMap[key] || 'green',
		value: durationSeconds,
	};
}

function warningRecordsToStats(records: any[]): DemoStat[] {
	const groups = new Map<string, { duration: number; count: number; confidence: number; confidenceCount: number }>();
	records.forEach((record) => {
		const key = normalizeBehavior(record.behaviorType || record.behaviorName || record.type || 'none');
		const duration = Number(record.durationSeconds || 0) || parseDurationSeconds(record.durationText || '');
		const confidence = Number(record.confidence || 0);
		const group = groups.get(key) || { duration: 0, count: 0, confidence: 0, confidenceCount: 0 };
		group.duration += duration;
		group.count += 1;
		if (Number.isFinite(confidence) && confidence > 0) {
			group.confidence += confidence <= 1 ? confidence : confidence / 100;
			group.confidenceCount += 1;
		}
		groups.set(key, group);
	});
	const totalDuration = Array.from(groups.values()).reduce((sum, item) => sum + item.duration, 0) || 1;
	const toneMap: Record<string, string> = {
		lie_desk: 'danger',
		sleep: 'warm',
		head_down: 'amber',
		phone: 'purple',
		focus: 'green',
		other_action: 'green',
		none: 'green',
	};
	return Array.from(groups.entries())
		.filter(([, item]) => item.duration > 0 || item.count > 0)
		.sort((a, b) => b[1].duration - a[1].duration)
		.map(([key, item]) => {
			const avgConfidence = item.confidenceCount ? item.confidence / item.confidenceCount : 0;
			return {
				key,
				label: behaviorText(key),
				duration: formatMinuteSecond(item.duration),
				ratio: `${((item.duration / totalDuration) * 100).toFixed(1)}%`,
				count: item.count,
				confidence: avgConfidence >= 0.9 ? '高' : avgConfidence >= 0.75 ? '中' : avgConfidence > 0 ? '低' : '-',
				tone: toneMap[key] || 'green',
				value: item.duration,
			};
		});
}

function protocolWarningToDemoEvent(warning: any, payload: any): Partial<DemoEvent> {
	const confidence = Number(warning.confidence || 0);
	const durationSeconds = Number(warning.durationSeconds || 0);
	return {
		eventId: warning.eventId || `EVT-${String(demoState.events.length + 1).padStart(3, '0')}`,
		sourceType: warning.sourceType || payload.sourceType || 'video',
		sourceName: warning.sourceName || payload.sourceName || demoState.material.sourceName,
		behaviorType: warning.behaviorType || 'none',
		riskLevel: warning.riskLevel || 'normal',
		durationSeconds,
		durationText: warning.durationText || formatMinuteSecond(durationSeconds),
		confidence: confidence ? `${Math.round(confidence * 100)}%` : '-',
		reason: warning.reason || payload.warningState?.reason || '检测事件达到触发阈值',
		advice: warning.advice || '',
		status: warning.status || '待跟进',
		createdAt: warning.triggerTime || payload.timestamp || '',
		provider: warning.provider || demoState.provider,
	};
}

function normalizeRisk(level: any): RiskLevel {
	const raw = String(level || '').toLowerCase();
	if (raw === 'high' || raw.includes('高')) return 'high';
	if (raw === 'medium' || raw.includes('中')) return 'medium';
	if (raw === 'low' || raw.includes('低')) return 'low';
	if (raw === 'normal' || raw.includes('正常')) return 'normal';
	return 'normal';
}

function formatConfidence(value: any) {
	if (value === undefined || value === null || value === '') return '-';
	const numeric = Number(value);
	if (!Number.isFinite(numeric)) return String(value);
	return numeric <= 1 ? `${Math.round(numeric * 100)}%` : `${Math.round(numeric)}%`;
}

function formatSourceName(value: any) {
	const text = String(value || '').trim();
	if (!text) return demoState.material.sourceName;
	return (text.split(/[\\/]/).pop() || text).split(/[?#]/)[0];
}

export function displaySourceName(value: any) {
	return formatSourceName(value);
}

export function sourceNameKey(value: any) {
	return formatSourceName(value).toLowerCase();
}

function recordSourceKey(record: any) {
	return sourceNameKey(record?.videoSource || record?.sourceName || record?.fileName || '');
}

function recordMatchesSource(record: any, targetSourceKey: string) {
	const currentKey = recordSourceKey(record);
	return Boolean(currentKey && targetSourceKey && (currentKey === targetSourceKey || currentKey.includes(targetSourceKey) || targetSourceKey.includes(currentKey)));
}

function resetStatsForSource(sourceName: string) {
	clearSampleEvents();
	demoState.hasLiveData = false;
	demoState.material.sourceName = formatSourceName(sourceName);
	demoState.stats.splice(0, demoState.stats.length, {
		key: 'empty',
		label: '暂无预警统计',
		duration: '0秒',
		ratio: '0.0%',
		count: 0,
		confidence: '-',
		tone: 'green',
		value: 0,
	});
	demoState.events.splice(0, demoState.events.length);
	demoState.aiHistory = [];
	demoState.selectedEventId = '';
}

function warningRecordEventId(record: any) {
	return String(record?.eventId || `WR-${record?.id || record?.triggerTime || recordTimestamp(record) || 'unknown'}`);
}

function recordTimestamp(record: any) {
	const raw = record.triggerTime || record.createdAt || record.updateTime || '';
	const time = raw ? new Date(String(raw).replace(/-/g, '/')).getTime() : 0;
	return Number.isFinite(time) ? time : Number(record.id || 0);
}

function riskWeight(level: RiskLevel | string) {
	const map: Record<string, number> = { high: 3, medium: 2, low: 1, normal: 0 };
	return map[level] || 0;
}

function eventsToFocusClue(events: DemoEvent[]): FocusClue {
	const sorted = events.slice().sort((a, b) => Number(b.durationSeconds || 0) - Number(a.durationSeconds || 0));
	const primary = sorted[0];
	const primarySeconds = Number(primary.durationSeconds || parseDurationSeconds(primary.durationText));
	const createdTimes = events.map((event) => event.createdAt).filter(Boolean);
	const behavior = behaviorText(primary.behaviorType);
	return {
		...primary,
		clueId: `${primary.behaviorType}-${primary.riskLevel}`,
		eventIds: events.map((event) => event.eventId),
		eventCount: events.length,
		durationSeconds: primarySeconds,
		durationText: primary.durationText || formatMinuteSecond(primarySeconds),
		evidenceText: buildEvidenceText(primary, events.length),
		timeRange: createdTimes.length ? `${createdTimes[0]}${createdTimes.length > 1 ? ` 至 ${createdTimes[createdTimes.length - 1]}` : ''}` : '检测视频片段内',
		teacherHint: `系统已将多条${behavior}记录合并为一条重点线索，建议教师课后以关心状态为切入点单独沟通确认。`,
	};
}

function buildEvidenceText(event: DemoEvent, count: number) {
	const behavior = behaviorText(event.behaviorType);
	if (event.behaviorType === 'lie_desk' || event.behaviorType === 'sleep') {
		return `画面中出现${behavior}线索，持续时长达到关注阈值；同类记录 ${count} 条，建议优先关注身体状态、睡眠和近期压力。`;
	}
	if (event.behaviorType === 'head_down') {
		return `检测到长时间低头或发呆状态，同类记录 ${count} 条；需结合课堂任务完成情况沟通确认原因。`;
	}
	if (event.behaviorType === 'phone') {
		return `检测到疑似分心行为，同类记录 ${count} 条；适合作为课堂专注度提醒，不直接定性学生动机。`;
	}
	return event.reason || `检测到${behavior}线索，建议结合课堂场景进行人工复核。`;
}

export function formatMinuteSecond(seconds: number) {
	const safe = Math.max(0, Math.round(seconds));
	return `${Math.floor(safe / 60)}分${String(safe % 60).padStart(2, '0')}秒`;
}

export function exportReportText() {
	const event = currentFocusClue.value || currentEvent.value;
	if (!event) return '请先完成视频检测，再生成教师跟进记录。';
	return [
		'课堂异常行为检测与教师跟进记录',
		`检测摘要：系统在本次录制课堂视频中筛选出重点异常线索：${behaviorText(event.behaviorType)}。`,
		`重点事件：${event.eventId}，风险等级：${riskText(event.riskLevel)}，持续时长：${event.durationText}。`,
		`风险说明：${event.reason}`,
		`教师沟通建议：${event.advice || fallbackAdvice(event)}`,
		'后续跟进：建议教师先进行非公开、低压力沟通，记录学生反馈和后续课堂状态。',
		'边界说明：本记录仅作为教师观察与沟通辅助，不作为医学或心理诊断结论。',
	].join('\n');
}

function formatDateTime(date: Date) {
	const pad = (value: number) => String(value).padStart(2, '0');
	return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
