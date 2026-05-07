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
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.client.RestTemplate;

import javax.annotation.Resource;
import java.text.SimpleDateFormat;
import java.util.Date;

@RestController
@RequestMapping("/warningRecords")
public class WarningRecordsController {
    @Resource
    WarningRecordsMapper warningRecordsMapper;

    private final RestTemplate restTemplate = new RestTemplate();

    public static class WarningAdviceRequest {
        private String riskLevel;
        private String behaviorType;
        private Double durationSeconds;
        private String reason;
        private String scene;

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
        String fallback = buildFallbackAdvice(request);
        String apiKey = System.getenv("DEEPSEEK_API_KEY");
        if (apiKey == null || apiKey.trim().isEmpty()) {
            return Result.success(fallback);
        }

        try {
            String apiUrl = System.getenv("DEEPSEEK_API_URL");
            if (apiUrl == null || apiUrl.trim().isEmpty()) {
                apiUrl = "https://api.deepseek.com/chat/completions";
            }
            String model = System.getenv("DEEPSEEK_MODEL");
            if (model == null || model.trim().isEmpty()) {
                model = "deepseek-chat";
            }

            JSONObject payload = new JSONObject();
            payload.put("model", model);
            payload.put("temperature", 0.3);
            payload.put("max_tokens", 450);
            JSONArray messages = new JSONArray();
            messages.add(message("system", "你是学校心理健康预警系统的教师助手。只能给出非诊断性的课堂关怀和沟通建议，不得做医学诊断，不得给学生贴标签。"));
            messages.add(message("user", buildAdvicePrompt(request)));
            payload.put("messages", messages);

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setBearerAuth(apiKey);
            HttpEntity<String> requestEntity = new HttpEntity<>(payload.toJSONString(), headers);
            String response = restTemplate.postForObject(apiUrl, requestEntity, String.class);
            JSONObject json = JSONObject.parseObject(response);
            String content = json.getJSONArray("choices")
                    .getJSONObject(0)
                    .getJSONObject("message")
                    .getString("content");
            if (content == null || content.trim().isEmpty()) {
                return Result.success(fallback);
            }
            return Result.success(content.trim());
        } catch (Exception e) {
            return Result.success(fallback);
        }
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
        String scene = request.getScene() == null || request.getScene().isEmpty() ? "课堂实时行为检测" : request.getScene();
        return "场景：" + scene + "\n"
                + "风险等级：" + risk + "\n"
                + "异常行为：" + behavior + "\n"
                + "持续时长：" + String.format("%.1f", seconds) + "秒\n"
                + "触发原因：" + (request.getReason() == null ? "" : request.getReason()) + "\n"
                + "请给教师生成3条简短、温和、可执行的干预建议。要求：非诊断、不直接公开点名、不制造羞耻感；必要时建议联系班主任、心理老师、家长或专业人员。";
    }

    private String buildFallbackAdvice(WarningAdviceRequest request) {
        String behavior = displayBehavior(request.getBehaviorType());
        String risk = displayRisk(request.getRiskLevel());
        return "当前识别到" + risk + "信号：" + behavior + "。建议教师先以非公开、低压力方式观察学生状态；课后进行简短关怀沟通，了解睡眠、身体不适、学习压力等情况；若该行为反复出现或伴随明显情绪低落、回避交流等表现，应及时联系班主任、心理老师，并按学校流程跟进。";
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
            return "长时间趴桌";
        }
        if ("head_down".equals(behaviorType)) {
            return "持续低头";
        }
        if ("phone".equals(behaviorType)) {
            return "玩手机";
        }
        return behaviorType == null ? "异常课堂行为" : behaviorType;
    }
}
