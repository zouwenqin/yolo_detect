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
## 行为统计字段口径

前端 `#/videoPredict` 的行为统计、趋势图和占比图使用以下协议口径：

### `behaviorStats`

`behaviorStats` 是从算法输出明细聚合后的行为统计数组，主要用于统计卡片和累计行为占比图。

常见字段：

- `behaviorType`：归一化后的行为类型，例如 `head_down`、`lie_desk`、`focus`、`other_action`。
- `behaviorName`：页面展示名称。
- `durationSeconds`：累计人次时长，单位为秒。多名学生目标同时出现同一行为时分别累计，因此可能大于视频自然时长。
- `durationText`：`durationSeconds` 的中文展示文本。
- `count`：合并后的连续行为片段数。合并键为 `trackId + behaviorType`，不是 `predictions.csv` 原始行数。
- `ratio`：该行为累计人次时长在全部行为累计人次时长中的占比。
- `confidence`：该行为相关预测窗口的平均置信度。

### `predictionWindows`

`predictionWindows` 是从 `predictions.csv` 解析得到的目标行为时间窗，主要用于人次时长趋势图。

常见字段：

- `trackId`：目标轨迹编号。
- `behaviorType` / `behaviorName`：归一化后的行为类型和展示名称。
- `startFrame` / `endFrame`：原始预测窗口帧号。
- `startSecond` / `endSecond`：换算后的视频时间。
- `durationSeconds`：该预测窗口持续时间。
- `confidence`：该窗口识别置信度。

趋势图展示前会按 `trackId + behaviorType` 合并重叠窗口，再按视频时间分桶累计每类行为的人次秒。这样可以避免 LSTM/BiLSTM 重叠滑窗导致同一目标同一行为被重复计时，同时保留多学生同时出现同类行为时的群体累计效果。

### 与 `predictions.csv` 的对应关系

`predictions.csv` 是逐目标滑窗预测明细，不直接等同于页面统计卡片。页面统计的生成链路为：

```text
predictions.csv
  -> 读取 track_id / start_frame / end_frame / pred_label / confidence
  -> 行为标签归一化
  -> 按 trackId + behaviorType 合并重叠窗口
  -> 生成 behaviorStats、predictionWindows、warning events
  -> 前端展示统计卡片、趋势图、累计占比图和 AI 干预事件
```
