package com.example.Kcsj.controller;

import cn.hutool.core.util.StrUtil;
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
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import javax.annotation.Resource;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;

@RestController
@RequestMapping("/warningRecords")
public class WarningRecordsController {
    private static final Logger log = LoggerFactory.getLogger(WarningRecordsController.class);
    private static final String DEFAULT_LLM_API_URL = "https://api.minimaxi.com/v1/text/chatcompletion_v2";
    private static final String DEFAULT_LLM_MODEL = "MiniMax-M2.7";

    @Resource
    WarningRecordsMapper warningRecordsMapper;

    private final RestTemplate restTemplate = new RestTemplate();

    @Value("${llm.api-key:${minimax.api-key:${minmax.api-key:${MINIMAX_API_KEY:}}}}")
    private String llmApiKey;

    @Value("${llm.api-url:${minimax.api-url:${minmax.api-url:https://api.minimaxi.com/v1/text/chatcompletion_v2}}}")
    private String llmApiUrl;

    @Value("${llm.model:${minimax.model:${minmax.model:MiniMax-M2.7}}}")
    private String llmModel;

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
        String fallback = StrUtil.isNotBlank(request.getQuestion()) ? buildFallbackChatAnswer(request) : buildFallbackAdvice(request);
        String model = normalizeModel();
        if (llmApiKey == null || llmApiKey.trim().isEmpty()) {
            return Result.success(new WarningAdviceResponse(fallback, model, "local_fallback", true, false, "未配置 MiniMax API-Key，已使用本地兜底建议。"));
        }

        try {
            String apiUrl = normalizeApiUrl();

            JSONObject payload = new JSONObject();
            payload.put("model", model);
            payload.put("temperature", 0.3);
            payload.put("max_tokens", StrUtil.isNotBlank(request.getQuestion()) ? 700 : 450);
            JSONArray messages = buildMessages(request);
            payload.put("messages", messages);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setBearerAuth(llmApiKey.trim());
            HttpEntity<String> requestEntity = new HttpEntity<>(payload.toJSONString(), headers);
            String response = restTemplate.postForObject(apiUrl, requestEntity, String.class);
            String content = extractAssistantContent(response);
            if (StrUtil.isBlank(content)) {
                return Result.success(new WarningAdviceResponse(fallback, model, "local_fallback", true, true, "MiniMax 返回内容为空，已使用本地兜底建议。"));
            }
            return Result.success(new WarningAdviceResponse(content.trim(), model, "minimax", false, true, "MiniMax 接口已返回建议。"));
        } catch (Exception e) {
            log.warn("MiniMax advice request failed: {}", e.getMessage());
            return Result.success(new WarningAdviceResponse(fallback, model, "local_fallback", true, true, "MiniMax 请求失败，已使用本地兜底建议。"));
        }
    }

    @GetMapping("/advice/status")
    public Result<?> adviceStatus() {
        JSONObject status = new JSONObject();
        status.put("provider", "minmax");
        status.put("model", normalizeModel());
        status.put("apiUrl", normalizeApiUrl());
        status.put("configured", StrUtil.isNotBlank(llmApiKey));
        return Result.success(status);
    }

    private String normalizeApiUrl() {
        return StrUtil.isBlank(llmApiUrl) ? DEFAULT_LLM_API_URL : llmApiUrl.trim();
    }

    private String normalizeModel() {
        return StrUtil.isBlank(llmModel) ? DEFAULT_LLM_MODEL : llmModel.trim();
    }

    private JSONArray buildMessages(WarningAdviceRequest request) {
        JSONArray messages = new JSONArray();
        messages.add(message("system", "你是课堂行为检测系统中的教师沟通助手。所有建议必须是非诊断式、温和、可执行的课堂关怀建议；不得做医学或心理诊断，不得给学生贴标签，不得建议公开点名批评。"));
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
                return message.getString("content");
            }
            return first.getString("text");
        }
        return json.getString("output_text");
    }

    private JSONObject message(String role, String content) {
        JSONObject message = new JSONObject();
        message.put("role", role);
        message.put("content", content);
        return message;
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
                + "请生成教师沟通建议，必须遵守：1. 非诊断式表达；2. 不给学生贴标签；3. 给出温和开场话术、追问方向、避免说法和后续跟进建议。";
    }

    private String buildFallbackAdvice(WarningAdviceRequest request) {
        String behavior = displayBehavior(request.getBehaviorType());
        String risk = displayRisk(request.getRiskLevel());
        return "当前识别到" + risk + "信号：" + behavior + "。建议教师先以非公开、低压力方式观察学生状态；课后可用“我注意到你这节课有一段时间状态不太舒服，是不是最近睡眠、课程压力或身体情况有点影响？”作为开场。沟通时避免直接说“你有问题”或公开点名；若该行为反复出现、学生明显情绪低落或影响学习任务，建议同步班主任、辅导员或心理老师做人工复核与持续跟进。";
    }

    private String buildChatPrompt(WarningAdviceRequest request) {
        return buildAdvicePrompt(request)
                + "\n\n教师继续追问：" + request.getQuestion()
                + "\n请基于前文异常线索直接回答这个追问，保持非诊断、尊重学生隐私、可执行。";
    }

    private String buildFallbackChatAnswer(WarningAdviceRequest request) {
        String behavior = displayBehavior(request.getBehaviorType());
        String question = request.getQuestion() == null ? "" : request.getQuestion().trim();
        String normalized = question.toLowerCase();
        if (question.contains("否认") || question.contains("不承认")) {
            return "如果学生否认" + behavior + "或不愿多说，建议教师先接住他的感受，不争辩、不追问细节。可以说：“没关系，我不是要批评你，只是想确认你最近状态还好吗。如果你之后愿意聊，可以随时找我。”之后继续观察一两次课堂状态，必要时记录并与班主任或辅导员做非诊断式沟通。";
        }
        if (question.contains("辅导员") || question.contains("班主任") || question.contains("心理")) {
            return "建议在高风险、反复出现或学生表达明显压力时同步辅导员/班主任。同步时只描述课堂观察事实，例如“某节课出现较长时间" + behavior + "，持续时间较长”，不要推断心理疾病，也不要扩大传播范围。";
        }
        if (question.contains("家长")) {
            return "不建议一开始就直接联系家长。可以先由任课教师做一次温和沟通；若学生状态持续异常、影响学习生活，或涉及安全风险，再按学校流程由班主任/辅导员评估是否联系家长。";
        }
        if (question.contains("自尊") || question.contains("伤害") || question.contains("尴尬")) {
            return "保护学生自尊的关键是私下、具体、非评价。不要说“你怎么又这样”，可以说“我注意到你今天有一段时间状态比较低，我想确认你是不是太累或哪里不舒服”。沟通地点尽量选择课后走廊、办公室门口等低压力场景。";
        }
        if (question.contains("开口") || question.contains("怎么说") || question.contains("话术") || normalized.contains("how")) {
            return "可以这样开口：“刚才课堂上我注意到你有一段时间状态不太好，我不是要批评你，只是想了解一下是不是最近睡眠、身体或课程压力影响到了你。有什么我能帮你调整的吗？”后续追问围绕睡眠、身体、课程难度和近期情绪，不做诊断。";
        }
        return "关于“" + question + "”，建议仍围绕" + behavior + "这一课堂观察事实来沟通：先表达关心，再询问可能原因，最后约定一个可执行的小跟进，例如下节课观察状态、调整座位或必要时请班主任协助。";
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
