export interface AdviceResult {
	advice: string;
	source: string;
	model?: string;
	fallback: boolean;
	message?: string;
}

export function normalizeAdviceResult(data: any, fallbackAdvice: string): AdviceResult {
	if (typeof data === 'string') {
		return {
			advice: data || fallbackAdvice,
			source: 'legacy_unknown',
			fallback: true,
			message: data ? '后端仍是旧返回格式，无法确认是否真实调用 MiniMax；重启后端后会显示真实/兜底来源。' : undefined,
		};
	}

	if (data && typeof data === 'object') {
		const source = String(data.source || (data.fallback ? 'local_fallback' : 'minimax'));
		const advice = data.advice || data.content || data.text || fallbackAdvice;
		return {
			advice,
			source,
			model: data.model,
			fallback: Boolean(data.fallback || source.includes('fallback')),
			message: data.message,
		};
	}

	return {
		advice: fallbackAdvice,
		source: 'local_fallback',
		fallback: true,
	};
}
