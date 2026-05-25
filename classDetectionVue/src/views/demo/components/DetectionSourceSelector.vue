<template>
	<section class="panel source-panel">
		<div class="source-title">
			<div>
				<h3>检测结果切换</h3>
				<p>当前查看：{{ selectedLabel }}</p>
			</div>
			<div class="source-actions">
				<el-button @click="router.push('/detectionHistory')">检测历史</el-button>
			</div>
		</div>
		<div class="history-strip">
			<button
				v-for="item in sourceOptions"
				:key="`source-${item.key}`"
				class="history-item"
				:class="{ active: item.value === selectedValue }"
				type="button"
				:disabled="loading"
				@click="handleSelect(item.value)"
			>
				<strong>{{ item.label }}</strong>
				<span>{{ item.startTime || '当前检测' }} · {{ item.warningCount }} 条预警</span>
			</button>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import { demoState, displaySourceName, sourceNameKey } from '/@/views/demo/demoState';

type DetectionSourceOption = {
	key: string;
	value: string;
	label: string;
	inputVideo: string;
	startTime: string;
	warningCount: number;
	isCurrent?: boolean;
};
type DetectionSourceOptionWithTime = DetectionSourceOption & { latestTime: number };

const props = defineProps<{
	records: any[];
	historyRecords?: any[];
	modelValue: string;
	loading?: boolean;
}>();

const emit = defineEmits<{
	(e: 'update:modelValue', value: string): void;
	(e: 'change', option: DetectionSourceOption): void;
}>();

const router = useRouter();

const selectedValue = computed({
	get: () => props.modelValue,
	set: (value: string) => emit('update:modelValue', value),
});

const sourceOptions = computed<DetectionSourceOption[]>(() => {
	const groups = new Map<string, { source: string; latestTime: number; startTime: string; warningCount: number }>();
	const hasHistorySource = Array.isArray(props.historyRecords);
	const sourceRows = hasHistorySource ? props.historyRecords || [] : props.records;

	sourceRows.filter(Boolean).forEach((record) => {
		const source = recordSource(record) || demoState.material.sourceName;
		const key = sourceNameKey(source);
		if (!key) return;
		const time = recordTime(record);
		const current = groups.get(key);
		if (!current) {
			groups.set(key, {
				source,
				latestTime: time,
				startTime: record.startTime || record.triggerTime || record.createdAt || '',
				warningCount: 0,
			});
			return;
		}
		if (time >= current.latestTime) {
			current.latestTime = time;
			current.startTime = record.startTime || record.triggerTime || record.createdAt || current.startTime;
		}
	});

	const currentSource = demoState.material.sourceName;
	const currentKey = sourceNameKey(currentSource);
	if (!hasHistorySource && currentKey && !groups.has(currentKey)) {
		groups.set(currentKey, {
			source: currentSource,
			latestTime: Date.now(),
			startTime: '当前检测',
			warningCount: 0,
		});
	}

	props.records.filter(Boolean).forEach((record) => {
		const recordKey = sourceNameKey(warningRecordSource(record));
		if (!recordKey) return;
		groups.forEach((group, key) => {
			if (sourceKeyMatches(recordKey, key)) group.warningCount += 1;
		});
	});

	return Array.from(groups.entries())
		.map<DetectionSourceOptionWithTime>(([key, item]) => ({
			key,
			value: key,
			label: displaySourceName(item.source),
			inputVideo: item.source,
			startTime: item.startTime,
			warningCount: item.warningCount,
			isCurrent: key === currentKey,
			latestTime: item.latestTime,
		}))
		.sort((a, b) => Number(b.isCurrent) - Number(a.isCurrent) || b.latestTime - a.latestTime)
		.map(({ latestTime, ...item }) => item);
});

const selectedLabel = computed(() => sourceOptions.value.find((item) => item.value === selectedValue.value)?.label || displaySourceName(demoState.material.sourceName));

watch(sourceOptions, () => {
	if (!sourceOptions.value.length) return;
	if (!props.records.length && !selectedValue.value) return;
	if (sourceOptions.value.some((item) => item.value === selectedValue.value)) return;
	const currentKey = sourceNameKey(demoState.material.sourceName);
	const option = sourceOptions.value.find((item) => item.value === currentKey) || sourceOptions.value[0];
	handleSelect(option.value);
}, { immediate: true });

function handleSelect(value: string) {
	const option = sourceOptions.value.find((item) => item.value === value);
	if (!option) return;
	emit('update:modelValue', option.value);
	emit('change', option);
}

function recordSource(record: any) {
	return record?.inputVideo || record?.videoSource || record?.sourceName || record?.fileName || '';
}

function warningRecordSource(record: any) {
	return record?.videoSource || record?.sourceName || record?.fileName || '';
}

function sourceKeyMatches(leftKey: string, rightKey: string) {
	return Boolean(leftKey && rightKey && (leftKey === rightKey || leftKey.includes(rightKey) || rightKey.includes(leftKey)));
}

function recordTime(record: any) {
	const raw = record?.startTime || record?.triggerTime || record?.createdAt || record?.updateTime || '';
	const time = raw ? Date.parse(String(raw).replace(/-/g, '/')) : 0;
	return Number.isFinite(time) ? time : Number(record?.id || 0);
}
</script>

<style scoped lang="scss">
.panel {
	border-radius: 8px;
	background: rgba(255, 255, 255, .97);
	border: 1px solid #dde8e5;
	box-shadow: 0 14px 34px rgba(23, 42, 46, .07);
	padding: 16px;
}

.source-panel {
	margin-bottom: 16px;
}

.source-title {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 16px;
}

.source-title h3 {
	margin: 0 0 6px;
	font-size: 18px;
}

.source-title p {
	margin: 0;
	color: #6b7b80;
	line-height: 1.6;
	font-size: 13px;
}

.source-actions {
	display: flex;
	align-items: center;
	justify-content: flex-end;
}

.history-strip {
	display: flex;
	gap: 8px;
	margin-top: 14px;
	padding-bottom: 2px;
	overflow-x: auto;
	scrollbar-width: thin;
}

.history-item {
	min-width: 180px;
	max-width: 240px;
	border: 1px solid #d8e8e4;
	background: #f8fbfa;
	border-radius: 8px;
	padding: 10px 12px;
	text-align: left;
	cursor: pointer;
}

.history-item.active {
	border-color: #00a99d;
	background: #eaf8f5;
	box-shadow: 0 8px 18px rgba(0, 143, 135, .14);
}

.history-item:disabled {
	cursor: not-allowed;
	opacity: .68;
}

.history-item strong,
.history-item span {
	display: block;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: nowrap;
}

.history-item strong {
	color: #173337;
	font-size: 14px;
}

.history-item span {
	margin-top: 4px;
	color: #718388;
	font-size: 12px;
}

@media (max-width: 760px) {
	.source-title {
		grid-template-columns: 1fr;
		display: grid;
	}

	.source-actions {
		justify-content: flex-start;
	}
}
</style>
