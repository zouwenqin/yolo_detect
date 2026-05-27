package com.example.Kcsj.controller;

import cn.hutool.core.util.StrUtil;
import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.example.Kcsj.common.Result;
import com.example.Kcsj.entity.WarningRecords;
import com.example.Kcsj.mapper.WarningRecordsMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import javax.annotation.Resource;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

@RestController
@RequestMapping("/warningRecords")
public class WarningRecordsController {
    private static final Logger log = LoggerFactory.getLogger(WarningRecordsController.class);
    private static final String DEFAULT_LLM_API_URL = "https://api.minimax.com/v1/text/chatcompletion_v2";
    private static final String DEFAULT_LLM_MODEL = "MiniMax-M2.7-highspeed";

    @Resource
    WarningRecordsMapper warningRecordsMapper;

    private final RestTemplate restTemplate = createRestTemplate();

    @Value("${llm.api-key:${deepseek.api-key:${DEEPSEEK_API_KEY:${minimax.api-key:${minmax.api-key:${MINIMAX_API_KEY:}}}}}}")
    private String llmApiKey;

    @Value("${llm.api-url:${deepseek.api-url:${DEEPSEEK_API_URL:${minimax.api-url:${minmax.api-url:https://api.minimax.com/v1/text/chatcompletion_v2}}}}}")
    private String llmApiUrl;

    @Value("${llm.model:${deepseek.model:${DEEPSEEK_MODEL:${minimax.model:${minmax.model:MiniMax-M2.7-highspeed}}}}}")
    private String llmModel;

    private RestTemplate createRestTemplate() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(8000);
        factory.setReadTimeout(30000);
        return new RestTemplate(factory);
    }

    public static class WarningAdviceRequest {
        private String riskLevel;
        private String behaviorType;
        private Double durationSeconds;
        private String durationText;
        private String reason;
        private String scene;
        private String question;
        private String provider;
        private List<ChatMessage> messages;

        public String getRiskLevel() {
            return riskLevel;
        }

        public void setRiskLevel(String riskLevel) {
            this.riskLevel = riskLevel;
        }

        public String getBehaviorType() {
            return behaviorType;
        }

        public void setBehaviorType(String behaviorType) {
            this.behaviorType = behaviorType;
        }

        public Double getDurationSeconds() {
            return durationSeconds;
        }

        public void setDurationSeconds(Double durationSeconds) {
            this.durationSeconds = durationSeconds;
        }

        public String getDurationText() {
            return durationText;
        }

        public void setDurationText(String durationText) {
            this.durationText = durationText;
        }

        public String getReason() {
            return reason;
        }

        public void setReason(String reason) {
            this.reason = reason;
        }

        public String getScene() {
            return scene;
        }

        public void setScene(String scene) {
            this.scene = scene;
        }

        public String getQuestion() {
            return question;
        }

        public void setQuestion(String question) {
            this.question = question;
        }

        public String getProvider() {
            return provider;
        }

        public void setProvider(String provider) {
            this.provider = provider;
        }

        public List<ChatMessage> getMessages() {
            return messages;
        }

        public void setMessages(List<ChatMessage> messages) {
            this.messages = messages;
        }
    }

    public static class ChatMessage {
        private String role;
        private String content;

        public String getRole() {
            return role;
        }

        public void setRole(String role) {
            this.role = role;
        }

        public String getContent() {
            return content;
        }

        public void setContent(String content) {
            this.content = content;
        }
    }

    public static class WarningAdviceResponse {
        private String advice;
        private String provider;
        private String model;
        private String source;
        private boolean fallback;
        private boolean configured;
        private String message;
        private List<AdviceCard> possibleReasons;
        private List<AdviceCard> guidanceCards;

        public WarningAdviceResponse() {
        }

        public WarningAdviceResponse(String advice, String model, String source, boolean fallback, boolean configured, String message) {
            this.advice = advice;
            this.provider = "minmax";
            this.model = model;
            this.source = source;
            this.fallback = fallback;
            this.configured = configured;
            this.message = message;
        }

        public String getAdvice() {
            return advice;
        }

        public void setAdvice(String advice) {
            this.advice = advice;
        }

        public String getProvider() {
            return provider;
        }

        public void setProvider(String provider) {
            this.provider = provider;
        }

        public String getModel() {
            return model;
        }

        public void setModel(String model) {
            this.model = model;
        }

        public String getSource() {
            return source;
        }

        public void setSource(String source) {
            this.source = source;
        }

        public boolean isFallback() {
            return fallback;
        }

        public void setFallback(boolean fallback) {
            this.fallback = fallback;
        }

        public boolean isConfigured() {
            return configured;
        }

        public void setConfigured(boolean configured) {
            this.configured = configured;
        }

        public String getMessage() {
            return message;
        }

        public void setMessage(String message) {
            this.message = message;
        }

        public List<AdviceCard> getPossibleReasons() {
            return possibleReasons;
        }

        public void setPossibleReasons(List<AdviceCard> possibleReasons) {
            this.possibleReasons = possibleReasons;
        }

        public List<AdviceCard> getGuidanceCards() {
            return guidanceCards;
        }

        public void setGuidanceCards(List<AdviceCard> guidanceCards) {
            this.guidanceCards = guidanceCards;
        }
    }

    public static class AdviceCard {
        private String title;
        private String desc;

        public AdviceCard() {
        }

        public AdviceCard(String title, String desc) {
            this.title = title;
            this.desc = desc;
        }

        public String getTitle() {
            return title;
        }

        public void setTitle(String title) {
            this.title = title;
        }

        public String getDesc() {
            return desc;
        }

        public void setDesc(String desc) {
            this.desc = desc;
        }
    }

    @GetMapping("/all")
    public Result<?> getAll() {
        return Result.success(warningRecordsMapper.selectList(null));
    }

    @GetMapping("/{id}")
    public Result<?> getById(@PathVariable int id) {
        return Result.success(warningRecordsMapper.selectById(id));
    }

    @GetMapping
    public Result<?> findPage(@RequestParam(defaultValue = "1") Integer pageNum,
                              @RequestParam(defaultValue = "10") Integer pageSize,
                              @RequestParam(defaultValue = "") String search,
                              @RequestParam(defaultValue = "") String riskLevel,
                              @RequestParam(defaultValue = "") String behaviorType,
                              @RequestParam(defaultValue = "") String status) {
        LambdaQueryWrapper<WarningRecords> wrapper = Wrappers.<WarningRecords>lambdaQuery();
        wrapper.orderByDesc(WarningRecords::getTriggerTime);
        if (StrUtil.isNotBlank(search)) {
            wrapper.like(WarningRecords::getUsername, search);
        }
        if (StrUtil.isNotBlank(riskLevel)) {
            wrapper.eq(WarningRecords::getRiskLevel, riskLevel);
        }
        if (StrUtil.isNotBlank(behaviorType)) {
            wrapper.eq(WarningRecords::getBehaviorType, behaviorType);
        }
        if (StrUtil.isNotBlank(status)) {
            wrapper.eq(WarningRecords::getStatus, status);
        }
        Page<WarningRecords> page = warningRecordsMapper.selectPage(new Page<>(pageNum, pageSize), wrapper);
        return Result.success(page);
    }

    @PostMapping
    public Result<?> save(@RequestBody WarningRecords warningRecords) {
        if (warningRecords.getTriggerTime() == null || warningRecords.getTriggerTime().isEmpty()) {
            warningRecords.setTriggerTime(new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new Date()));
        }
        if (warningRecords.getStatus() == null || warningRecords.getStatus().isEmpty()) {
            warningRecords.setStatus("未处理");
        }
        warningRecordsMapper.insert(warningRecords);
        return Result.success(warningRecords);
    }

    @PostMapping("/update")
    public Result<?> update(@RequestBody WarningRecords warningRecords) {
        warningRecordsMapper.updateById(warningRecords);
        return Result.success();
    }

    @DeleteMapping("/{id}")
    public Result<?> delete(@PathVariable int id) {
        warningRecordsMapper.deleteById(id);
        return Result.success();
    }

    @PostMapping("/advice")
    public Result<?> advice(@RequestBody WarningAdviceRequest request) {
        String model = normalizeModel();
        String apiKey = normalizeApiKey();
        if (StrUtil.isBlank(apiKey)) {
            return Result.error("AI_CONFIG_MISSING", "未配置大模型 API-Key，未生成建议。请检查 LLM_API_KEY、MINIMAX_API_KEY 或 DEEPSEEK_API_KEY。");
        }

        try {
            String apiUrl = normalizeApiUrl();

            JSONObject payload = new JSONObject();
            payload.put("model", model);
            payload.put("temperature", 0.3);
            payload.put("max_tokens", StrUtil.isNotBlank(request.getQuestion()) ? 500 : 700);
            JSONArray messages = buildMessages(request);
            payload.put("messages", messages);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setBearerAuth(apiKey);
            HttpEntity<String> requestEntity = new HttpEntity<>(payload.toJSONString(), headers);
            String response = restTemplate.postForObject(apiUrl, requestEntity, String.class);
            String content = extractAssistantContent(response);
            if (StrUtil.isBlank(content)) {
                String modelError = extractModelError(response);
                if (StrUtil.isNotBlank(modelError)) {
                    return Result.error("AI_EMPTY_RESPONSE", "大模型接口未返回建议：" + modelError);
                }
                return Result.error("AI_EMPTY_RESPONSE", "大模型返回内容为空，未生成建议。请检查模型名、API 地址和账号权限。");
            }
            return Result.success(parseAdviceResponse(content.trim(), request, model));
        } catch (Exception e) {
            log.warn("LLM advice request failed: {}", e.getMessage());
            return Result.error("AI_REQUEST_FAILED", "大模型请求失败，未生成建议：" + safeErrorMessage(e));
        }
    }

    @GetMapping("/advice/status")
    public Result<?> adviceStatus() {
        JSONObject status = new JSONObject();
        status.put("provider", "minmax");
        status.put("model", normalizeModel());
        status.put("apiUrl", normalizeApiUrl());
        status.put("configured", StrUtil.isNotBlank(normalizeApiKey()));
        status.put("apiKeySource", apiKeySource());
        return Result.success(status);
    }

    private String normalizeApiKey() {
        return firstNonBlank(
                llmApiKey,
                System.getenv("LLM_API_KEY"),
                System.getenv("MINIMAX_API_KEY"),
                System.getenv("MINIMAX_CN_API_KEY"),
                System.getenv("MINMAX_API_KEY"),
                System.getenv("DEEPSEEK_API_KEY")
        );
    }

    private String normalizeApiUrl() {
        return firstNonBlank(
                llmApiUrl,
                System.getenv("LLM_API_URL"),
                System.getenv("MINIMAX_API_URL"),
                System.getenv("MINMAX_API_URL"),
                System.getenv("DEEPSEEK_API_URL"),
                DEFAULT_LLM_API_URL
        );
    }

    private String normalizeModel() {
        return firstNonBlank(
                llmModel,
                System.getenv("LLM_MODEL"),
                System.getenv("MINIMAX_MODEL"),
                System.getenv("MINMAX_MODEL"),
                System.getenv("DEEPSEEK_MODEL"),
                DEFAULT_LLM_MODEL
        );
    }

    private String apiKeySource() {
        if (StrUtil.isNotBlank(llmApiKey)) return "spring_property";
        if (StrUtil.isNotBlank(System.getenv("LLM_API_KEY"))) return "LLM_API_KEY";
        if (StrUtil.isNotBlank(System.getenv("MINIMAX_API_KEY"))) return "MINIMAX_API_KEY";
        if (StrUtil.isNotBlank(System.getenv("MINIMAX_CN_API_KEY"))) return "MINIMAX_CN_API_KEY";
        if (StrUtil.isNotBlank(System.getenv("MINMAX_API_KEY"))) return "MINMAX_API_KEY";
        if (StrUtil.isNotBlank(System.getenv("DEEPSEEK_API_KEY"))) return "DEEPSEEK_API_KEY";
        return "";
    }

    private String safeErrorMessage(Exception e) {
        String message = e == null ? "" : String.valueOf(e.getMessage());
        if (message.length() > 180) {
            message = message.substring(0, 180) + "...";
        }
        return message.replaceAll("(?i)(bearer\\s+)[^\\s,;]+", "$1***");
    }

    private JSONArray buildMessages(WarningAdviceRequest request) {
        JSONArray messages = new JSONArray();
        messages.add(message("system", "你是课堂行为检测系统中的教师沟通助手。所有建议必须是非诊断式、温和、可执行的课堂关怀建议；不得做医学或心理诊断，不得给学生贴标签，不得建议公开点名批评。直接输出纯文本，不要使用 Markdown、星号加粗、表格或代码块。"));
        if (request.getMessages() != null) {
            for (ChatMessage item : request.getMessages()) {
                if (item == null || StrUtil.isBlank(item.getContent())) {
                    continue;
                }
                String role = "assistant".equals(item.getRole()) ? "assistant" : "user";
                messages.add(message(role, item.getContent().trim()));
            }
        }
        if (StrUtil.isNotBlank(request.getQuestion())) {
            messages.add(message("user", buildChatPrompt(request)));
        } else {
            messages.add(message("user", buildAdvicePrompt(request)));
        }
        return messages;
    }

    private String extractAssistantContent(String response) {
        if (StrUtil.isBlank(response)) {
            return "";
        }
        JSONObject json = JSONObject.parseObject(response);
        JSONArray choices = json.getJSONArray("choices");
        if (choices != null && !choices.isEmpty()) {
            JSONObject first = choices.getJSONObject(0);
            JSONObject message = first.getJSONObject("message");
            if (message != null) {
                String messageText = firstNonBlank(message.getString("content"), message.getString("text"));
                if (StrUtil.isNotBlank(messageText)) {
                    return messageText;
                }
            }
            String choiceText = firstNonBlank(first.getString("text"), first.getString("content"));
            if (StrUtil.isNotBlank(choiceText)) {
                return choiceText;
            }
            JSONArray messages = first.getJSONArray("messages");
            if (messages != null && !messages.isEmpty()) {
                for (int i = messages.size() - 1; i >= 0; i--) {
                    JSONObject item = messages.getJSONObject(i);
                    String itemText = firstNonBlank(item.getString("content"), item.getString("text"));
                    if (StrUtil.isNotBlank(itemText)) {
                        return itemText;
                    }
                }
            }
        }
        JSONObject data = json.getJSONObject("data");
        if (data != null) {
            String dataText = firstNonBlank(data.getString("output_text"), data.getString("reply"), data.getString("text"), data.getString("content"));
            if (StrUtil.isNotBlank(dataText)) {
                return dataText;
            }
        }
        return firstNonBlank(json.getString("output_text"), json.getString("reply"), json.getString("text"), json.getString("content"));
    }

    private String extractModelError(String response) {
        if (StrUtil.isBlank(response)) {
            return "";
        }
        try {
            JSONObject json = JSONObject.parseObject(response);
            JSONObject baseResp = json.getJSONObject("base_resp");
            if (baseResp == null) {
                baseResp = json.getJSONObject("base_response");
            }
            if (baseResp == null) {
                baseResp = json.getJSONObject("baseResp");
            }
            if (baseResp != null) {
                String code = firstNonBlank(baseResp.getString("status_code"), baseResp.getString("code"), baseResp.getString("err_code"));
                String message = firstNonBlank(baseResp.getString("status_msg"), baseResp.getString("message"), baseResp.getString("msg"), baseResp.getString("error_msg"));
                if (StrUtil.isNotBlank(message) && (StrUtil.isBlank(code) || !"0".equals(code))) {
                    return codeMessage(code, message);
                }
            }
            String topMessage = firstNonBlank(json.getString("error_msg"), json.getString("message"), json.getString("msg"), json.getString("error"));
            String topCode = firstNonBlank(json.getString("code"), json.getString("status_code"), json.getString("err_code"));
            if (StrUtil.isNotBlank(topMessage)) {
                return codeMessage(topCode, topMessage);
            }
        } catch (Exception e) {
            log.warn("LLM error response parse failed: {}", e.getMessage());
        }
        return "";
    }

    private String codeMessage(String code, String message) {
        if (StrUtil.isBlank(code)) {
            return message;
        }
        return code + " - " + message;
    }

    private JSONObject message(String role, String content) {
        JSONObject message = new JSONObject();
        message.put("role", role);
        message.put("content", content);
        return message;
    }

    private WarningAdviceResponse parseAdviceResponse(String content, WarningAdviceRequest request, String model) {
        if (StrUtil.isNotBlank(request.getQuestion())) {
            return buildAdviceResponse(content, request, model, "llm_api", false, true, "大模型接口已返回追问回复。");
        }
        JSONObject json = parseJsonContent(content);
        if (json == null) {
            return buildModelTextResponse(content, request, model, "大模型接口已返回沟通建议。");
        }
        String advice = firstNonBlank(json.getString("advice"), json.getString("content"), json.getString("text"), content);
        WarningAdviceResponse response = buildModelTextResponse(advice, request, model, "大模型接口已返回结构化建议。");
        List<AdviceCard> reasons = parseCards(json.getJSONArray("possibleReasons"));
        if (reasons.isEmpty()) reasons = parseCards(json.getJSONArray("reasonCards"));
        if (!reasons.isEmpty()) response.setPossibleReasons(reasons);
        List<AdviceCard> guidance = parseCards(json.getJSONArray("guidanceCards"));
        if (!guidance.isEmpty()) response.setGuidanceCards(guidance);
        return response;
    }

    private WarningAdviceResponse buildModelTextResponse(String advice, WarningAdviceRequest request, String model, String message) {
        String normalized = normalizeAdviceText(advice);
        WarningAdviceResponse response = buildAdviceResponse(normalized, request, model, "llm_api", false, true, message);
        response.setGuidanceCards(buildGuidanceCardsFromAdvice(normalized));
        return response;
    }

    private JSONObject parseJsonContent(String content) {
        if (StrUtil.isBlank(content)) {
            return null;
        }
        String text = unwrapJsonText(content.trim());
        JSONObject json = tryParseJsonObject(text);
        if (json != null) {
            return json;
        }
        Object parsed = tryParseJsonValue(text);
        if (parsed instanceof String) {
            return tryParseJsonObject(unwrapJsonText(((String) parsed).trim()));
        }
        return null;
    }

    private String unwrapJsonText(String text) {
        if (text.startsWith("```")) {
            text = text.replaceFirst("^```(?:json)?\\s*", "").replaceFirst("\\s*```$", "").trim();
        }
        int start = text.indexOf('{');
        int end = text.lastIndexOf('}');
        if (start >= 0 && end > start) {
            text = text.substring(start, end + 1);
        }
        return text;
    }

    private JSONObject tryParseJsonObject(String text) {
        try {
            return JSONObject.parseObject(text);
        } catch (Exception e) {
            return null;
        }
    }

    private Object tryParseJsonValue(String text) {
        try {
            return JSON.parse(text);
        } catch (Exception e) {
            log.warn("LLM advice response is not JSON: {}", e.getMessage());
            return null;
        }
    }

    private List<AdviceCard> parseCards(JSONArray array) {
        List<AdviceCard> cards = new ArrayList<>();
        if (array == null) {
            return cards;
        }
        for (int i = 0; i < array.size(); i++) {
            Object raw = array.get(i);
            if (!(raw instanceof JSONObject)) {
                continue;
            }
            JSONObject item = (JSONObject) raw;
            String title = firstNonBlank(item.getString("title"), item.getString("name"), "");
            String desc = firstNonBlank(item.getString("desc"), item.getString("description"), item.getString("content"), "");
            if (StrUtil.isNotBlank(title) && StrUtil.isNotBlank(desc)) {
                cards.add(new AdviceCard(title, desc));
            }
        }
        return cards;
    }

    private WarningAdviceResponse buildAdviceResponse(String advice, WarningAdviceRequest request, String model, String source, boolean fallback, boolean configured, String message) {
        WarningAdviceResponse response = new WarningAdviceResponse(advice, model, source, fallback, configured, message);
        return response;
    }

    private String firstNonBlank(String... values) {
        if (values == null) {
            return "";
        }
        for (String value : values) {
            if (StrUtil.isNotBlank(value)) {
                return value.trim();
            }
        }
        return "";
    }

    private String normalizeAdviceText(String advice) {
        if (StrUtil.isBlank(advice)) {
            return "";
        }
        String text = advice.trim();
        JSONObject json = parseJsonContent(text);
        if (json != null) {
            text = firstNonBlank(json.getString("advice"), json.getString("content"), json.getString("text"), text);
        }
        text = text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n");
        text = text.replace("\\n", "\n").replace("\\\"", "\"");
        return text.trim();
    }

    private String buildAdvicePrompt(WarningAdviceRequest request) {
        String behavior = displayBehavior(request.getBehaviorType());
        String risk = displayRisk(request.getRiskLevel());
        Double seconds = request.getDurationSeconds() == null ? 0 : request.getDurationSeconds();
        String scene = request.getScene() == null || request.getScene().isEmpty() ? "课堂录制视频异常行为检测" : request.getScene();
        return "场景：" + scene + "\n"
                + "风险等级：" + risk + "\n"
                + "异常行为：" + behavior + "\n"
                + "持续时长：" + String.format("%.1f", seconds) + "秒\n"
                + "触发原因：" + (request.getReason() == null ? "" : request.getReason()) + "\n"
                + "请直接生成教师沟通建议，不要返回 JSON，不要使用 Markdown、星号加粗或表格。"
                + "按四行输出，每行以普通中文标题开头：温和开场、追问方向、避免说法、后续跟进。"
                + "总字数控制在 180 到 260 个中文字符，表达必须非诊断、温和、可执行。";
    }

    private List<AdviceCard> buildGuidanceCardsFromAdvice(String advice) {
        List<AdviceCard> cards = new ArrayList<>();
        addAdviceCardIfPresent(cards, advice, "开场", "建议开场");
        addAdviceCardIfPresent(cards, advice, "追问", "追问方向");
        addAdviceCardIfPresent(cards, advice, "避免", "避免说法");
        addAdviceCardIfPresent(cards, advice, "跟进", "后续跟进");
        return cards;
    }

    private void addAdviceCardIfPresent(List<AdviceCard> cards, String advice, String keyword, String title) {
        String line = pickAdviceLine(advice, keyword);
        if (StrUtil.isNotBlank(line)) {
            cards.add(new AdviceCard(title, line));
        }
    }

    private String pickAdviceLine(String advice, String keyword) {
        if (StrUtil.isBlank(advice)) {
            return "";
        }
        String[] lines = advice.split("\\r?\\n|；|。");
        for (String line : lines) {
            String text = line.replaceAll("^[-\\d.、\\s]+", "").trim();
            if (text.contains(keyword) && text.length() >= 6) {
                return text.length() > 42 ? text.substring(0, 42) + "..." : text;
            }
        }
        return "";
    }

    private String buildChatPrompt(WarningAdviceRequest request) {
        return buildAdvicePrompt(request)
                + "\n\n教师继续追问：" + request.getQuestion()
                + "\n请基于前文异常线索直接回答这个追问，保持非诊断、尊重学生隐私、可执行。";
    }

    private String displayRisk(String riskLevel) {
        if ("high".equals(riskLevel)) {
            return "高风险";
        }
        if ("medium".equals(riskLevel)) {
            return "中风险";
        }
        if ("low".equals(riskLevel)) {
            return "低风险";
        }
        return "正常";
    }

    private String displayBehavior(String behaviorType) {
        if ("sleep".equals(behaviorType)) {
            return "疑似睡觉";
        }
        if ("lie_desk".equals(behaviorType)) {
            return "趴桌";
        }
        if ("head_down".equals(behaviorType)) {
            return "持续低头";
        }
        if ("phone".equals(behaviorType)) {
            return "疑似玩手机";
        }
        if ("other_action".equals(behaviorType)) {
            return "其他异常行为";
        }
        if ("focus".equals(behaviorType)) {
            return "正常听课";
        }
        return behaviorType == null ? "课堂异常行为" : behaviorType;
    }

    
}
