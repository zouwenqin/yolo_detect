# 课堂行为检测演示标准数据协议

## 目标

算法模型仍在调试时，前端和后端先围绕一个稳定协议开发。后续模型无论输出中文类别、英文类别、检测框、置信度，Flask 算法适配层统一转换成该协议。

## Socket 事件

Flask 通过 Socket.IO 的 `message` 事件推送：

```json
{
  "protocolVersion": "classroom-demo-v1",
  "sessionId": "DEMO-AB12CD34",
  "sourceType": "video",
  "sourceName": "课堂录制_实训课程_片段01.mp4",
  "timestamp": "2026-05-11 10:28:00",
  "frameIndex": 128,
  "progress": 42,
  "labels": ["lie_desk"],
  "normalizedLabels": ["lie_desk"],
  "displayLabels": ["趴桌"],
  "detections": [
    {
      "label": "lie_desk",
      "behaviorType": "lie_desk",
      "behaviorName": "趴桌",
      "confidence": 0.92,
      "bbox": [120, 88, 260, 210]
    }
  ],
  "behaviorStats": [
    {
      "behaviorType": "lie_desk",
      "behaviorName": "趴桌",
      "durationSeconds": 15.0,
      "durationText": "15秒",
      "count": 300,
      "ratio": 22.4,
      "confidence": 0.92
    }
  ],
  "warningState": {
    "riskLevel": "high",
    "reason": "趴桌行为持续超过10秒，建议生成高风险检测事件。",
    "durations": { "lie_desk": 15.0 },
    "consecutiveDurations": { "lie_desk": 15.0 },
    "warning": {
      "eventId": "DEMO-AB12CD34-001",
      "sourceType": "video",
      "sourceName": "课堂录制_实训课程_片段01.mp4",
      "behaviorType": "lie_desk",
      "behaviorName": "趴桌",
      "riskLevel": "high",
      "durationSeconds": 15.0,
      "durationText": "15秒",
      "confidence": 0.92,
      "reason": "趴桌行为持续超过10秒，建议生成高风险检测事件。",
      "triggerTime": "2026-05-11 10:28:00",
      "status": "待跟进"
    }
  },
  "events": []
}
```

## 标准行为标签

- `raise_hand`: 举手互动
- `read`: 阅读
- `write`: 书写
- `phone`: 疑似玩手机
- `head_down`: 持续低头
- `lie_desk`: 趴桌
- `sleep`: 疑似睡觉
- `focus`: 专注学习

## 风险等级

- `normal`: 正常
- `low`: 低
- `medium`: 中
- `high`: 高

## 数据流

1. YOLO 或其他算法输出原始类别、置信度、检测框。
2. Flask `DetectionProtocolAdapter` 做类别归一化、时长统计、事件触发。
3. Flask 通过 Socket 推送 `behaviorStats` 和 `warningState`。
4. 前端优先读取 Socket 真实数据；无数据时使用演示兜底数据。
5. 触发 `warning` 后 Flask 调用 Spring Boot `/warningRecords/advice` 生成建议，再保存到 `/warningRecords`。
6. 前端检测结果、行为统计、AI辅助干预、干预报告读取同一份事件状态。
