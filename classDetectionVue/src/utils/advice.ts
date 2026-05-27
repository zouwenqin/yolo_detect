export interface AdviceResult {
	advice: string;
	source: string;
	model?: string;
	fallback: boolean;
	message?: string;
	possibleReasons: AdviceCard[];
	guidanceCards: AdviceCard[];
}

export interface AdviceCard {
	title: string;
	desc: string;
}

export function normalizeAdviceResult(data: any, fallbackAdvice: string): AdviceResult {
	if (typeof data === 'string') {
		const nested = parseNestedAdvice(data);
		if (nested) return normalizeAdviceResult(nested, fallbackAdvice);
		return {
			advice: cleanupAdviceText(data) || fallbackAdvice,
			source: 'legacy_unknown',
			fallback: true,
			message: data ? '后端仍是旧返回格式，无法确认是否真实调用大模型；请重启后端后重试。' : undefined,
			possibleReasons: [],
			guidanceCards: [],
		};
	}

	if (data && typeof data === 'object') {
		const source = String(data.source || (data.fallback ? 'local_fallback' : 'minimax'));
		const rawAdvice = data.advice || data.content || data.text || fallbackAdvice;
		const nested = parseNestedAdvice(rawAdvice);
		const incompleteJson = typeof rawAdvice === 'string' && rawAdvice.trim().startsWith('{') && !nested?.advice;
		const advice = normalizeAdviceText(nested?.advice || (incompleteJson ? fallbackAdvice : rawAdvice), fallbackAdvice);
		return {
			advice,
			source,
			model: data.model,
			fallback: Boolean(data.fallback || source.includes('fallback') || incompleteJson),
			message: incompleteJson ? '大模型已被调用，但返回内容不完整，当前不展示本地模板；请重试或检查后端模型配置。' : data.message,
			possibleReasons: normalizeCards(data.possibleReasons || data.reasonCards || nested?.possibleReasons || nested?.reasonCards),
			guidanceCards: normalizeCards(data.guidanceCards || nested?.guidanceCards),
		};
	}

	return {
		advice: fallbackAdvice,
		source: 'invalid_response',
		fallback: true,
		possibleReasons: [],
		guidanceCards: [],
	};
}

export function normalizeAdviceText(value: any, fallbackAdvice = ''): string {
	if (value && typeof value === 'object') {
		return normalizeAdviceText(value.advice || value.content || value.text || '', fallbackAdvice);
	}
	if (typeof value !== 'string') return fallbackAdvice;
	const nested = parseNestedAdvice(value);
	const nestedAdvice = nested?.advice || nested?.content || nested?.text;
	if (nestedAdvice && nestedAdvice !== value) return normalizeAdviceText(nestedAdvice, fallbackAdvice);
	const text = cleanupAdviceText(value);
	if (text.startsWith('{') && text.includes('"advice"')) return fallbackAdvice;
	return text || fallbackAdvice;
}

function parseNestedAdvice(value: any): any {
	if (typeof value !== 'string') return null;
	const text = value.trim().replace(/^```(?:json)?\s*/, '').replace(/\s*```$/, '');
	const start = text.indexOf('{');
	const end = text.lastIndexOf('}');
	if (start < 0) return null;
	const closedJson = end > start ? text.slice(start, end + 1) : text.slice(start);
	const jsonLike = text.slice(start);
	try {
		return JSON.parse(closedJson);
	} catch (error) {
		const partial = {
			advice: extractJsonStringField(jsonLike, 'advice'),
			possibleReasons: extractJsonArrayField(jsonLike, 'possibleReasons'),
			reasonCards: extractJsonArrayField(jsonLike, 'reasonCards'),
			guidanceCards: extractJsonArrayField(jsonLike, 'guidanceCards'),
		};
		return partial.advice || partial.possibleReasons.length || partial.reasonCards.length || partial.guidanceCards.length ? partial : null;
	}
}

function extractJsonArrayField(text: string, field: string): any[] {
	const marker = `"${field}"`;
	const start = text.indexOf(marker);
	if (start < 0) return [];
	const arrayStart = text.indexOf('[', start);
	if (arrayStart < 0) return [];
	let depth = 0;
	let inString = false;
	let escaped = false;
	for (let index = arrayStart; index < text.length; index += 1) {
		const char = text[index];
		if (escaped) {
			escaped = false;
			continue;
		}
		if (char === '\\') {
			escaped = true;
			continue;
		}
		if (char === '"') inString = !inString;
		if (inString) continue;
		if (char === '[') depth += 1;
		if (char === ']') {
			depth -= 1;
			if (depth === 0) {
				try {
					return JSON.parse(text.slice(arrayStart, index + 1));
				} catch (error) {
					return [];
				}
			}
		}
	}
	return [];
}

function extractJsonStringField(text: string, field: string): string {
	const marker = `"${field}"`;
	const start = text.indexOf(marker);
	if (start < 0) return '';
	const colon = text.indexOf(':', start + marker.length);
	const quote = text.indexOf('"', colon + 1);
	if (colon < 0 || quote < 0) return '';
	let escaped = false;
	for (let index = quote + 1; index < text.length; index += 1) {
		const char = text[index];
		if (escaped) {
			escaped = false;
			continue;
		}
		if (char === '\\') {
			escaped = true;
			continue;
		}
		if (char === '"') {
			return unescapeJsonString(text.slice(quote + 1, index));
		}
	}
	return unescapeJsonString(text.slice(quote + 1).replace(/[",}\]]+$/, ''));
}

function unescapeJsonString(value: string) {
	try {
		return JSON.parse(`"${value.replace(/"/g, '\\"')}"`);
	} catch (error) {
		return value.replace(/\\n/g, '\n').replace(/\\"/g, '"').replace(/\\\\/g, '\\');
	}
}

function cleanupAdviceText(value: string) {
	return String(value || '')
		.trim()
		.replace(/^```(?:json)?\s*/, '')
		.replace(/\s*```$/, '')
		.replace(/<br\s*\/?>/gi, '\n')
		.replace(/\\n/g, '\n')
		.replace(/\\"/g, '"')
		.replace(/\\\\/g, '\\')
		.replace(/\*\*([^*]+)\*\*/g, '$1')
		.replace(/^\s*[-*]\s+/gm, '')
		.trim();
}

function normalizeCards(value: any): AdviceCard[] {
	if (!Array.isArray(value)) return [];
	return value
		.map((item) => ({
			title: String(item?.title || item?.name || '').trim(),
			desc: String(item?.desc || item?.description || item?.content || '').trim(),
		}))
		.filter((item) => item.title && item.desc);
}
