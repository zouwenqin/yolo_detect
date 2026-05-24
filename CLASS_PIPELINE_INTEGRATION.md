# class 视频行为识别算法接入说明

## 改动概览

本次接入将新增 `class/` 目录中的视频行为识别流水线用于项目的视频检测主流程，替换原来 `predictVideo` 中“YOLO 逐帧检测并 MJPEG 推流”的比赛展示路径。

新流程不再把检测结果逐帧作为图片流返回给前端，而是以任务方式运行：

```text
前端上传录制课堂视频
  -> Spring Boot /files/upload 返回视频 URL
  -> 前端 POST /flask/videoTasks 启动算法任务
  -> Flask 下载视频并调用 class/scripts/run_single_pipeline.py
  -> class pipeline 生成 predictions.csv 与 videos/result_h264.mp4
  -> Flask 解析 CSV，生成统计、预警事件、明细和学生 track 概览
  -> Socket.IO 推送进度与最终协议数据
  -> Flask 上传 result_h264.mp4 到 Spring Boot /files/upload
  -> 前端使用 <video> 播放 H.264 结果视频
```

这样做的原因是 `class/` 新算法本身是离线流水线：YOLOv8 + ByteTrack 先生成跟踪框，RTMPose 再提取关键点，LSTM/BiLSTM 最后按时间窗口识别行为。它不是单帧即可得到最终行为标签的算法，因此更适合“录制视频素材分析 -> 行为统计 -> 风险预警 -> AI 干预建议”的展示主线。

## 本次新增和修改

- 新增 `classDetectionFlask/class_pipeline.py`
  - 管理视频检测任务。
  - 下载上传视频。
  - 调用 `class/scripts/run_single_pipeline.py`。
  - 解析 `predictions.csv`。
  - 生成 `behaviorStats`、`trackSummary`、`predictionWindows` 和 `events`。
  - 上传 `result_h264.mp4` 并保存视频记录、预警记录。
- 修改 `class/scripts/run_single_pipeline.py`
  - `CLASS_ROOT` 改为优先读取环境变量 `CLASS_ROOT`，否则自动解析当前 `class/` 目录。
  - 避免继续硬编码 `C:\Users\admin\Desktop\class`。
- 修改 `classDetectionFlask/main.py`
  - 新增任务式接口 `/videoTasks`。
  - 保留原 `/predictVideo`，但比赛视频主流程改用 `/videoTasks`。
- 修改 `classDetectionVue/src/views/videoPredict/index.vue`
  - 开始检测时调用 `/flask/videoTasks`。
  - Socket.IO 接收任务进度与最终结果。
  - 完成后播放 `resultVideoUrl`，不再用 `<img>` 加载 MJPEG 检测流。
- 修改 `classDetectionVue/src/views/demo/demoState.ts`
  - 兼容新算法标签：`normal`、`head_down`、`lie_down`、`other_action`。

## 新增 Flask 接口

### 0. 获取 `class/models` 模型列表

```http
GET /class-models
```

返回 `class/models` 目录下的 `.pt` 和 `.pth` 模型。前端视频检测页面的模型下拉框现在使用这个接口，不再固定写死 `class.pt`。

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "modelDir": "F:/yolo_detect/classDetection/project/class/models",
    "weight_items": [
      { "value": "best_lstm.pth", "label": "best_lstm.pth" },
      { "value": "yolo_best.pt", "label": "yolo_best.pt" }
    ],
    "yoloModelItems": [
      { "value": "yolo_best.pt", "label": "yolo_best.pt" }
    ],
    "lstmModelItems": [
      { "value": "best_lstm.pth", "label": "best_lstm.pth" }
    ]
  }
}
```

### 1. 启动视频检测任务

```http
POST /videoTasks
Content-Type: application/json
```

请求体：

```json
{
  "username": "demo",
  "inputVideo": "http://localhost:9999/files/xxx_input.mp4",
  "sourceName": "input.mp4",
  "kind": "class-pipeline",
  "startTime": "2026-05-21 10:00:00",
  "confThr": 0.45,
  "frameStride": 5,
  "yoloModel": "yolo_best.pt",
  "lstmModel": "best_lstm.pth",
  "yoloDevice": "cpu",
  "rtmposeDevice": "cpu",
  "lstmDevice": "cpu"
}
```

如果前端尚未上传素材，也可以传：

```json
{
  "inputVideo": "class_sample"
}
```

Flask 会使用 `class/sample/input.mp4` 作为内置演示样例，方便直接点击“开始检测”验证算法链路。

返回：

```json
{
  "code": 0,
  "message": "started",
  "data": {
    "taskId": "task_20260521_100000_ab12cd",
    "status": "pending",
    "taskStatus": "pending"
  }
}
```

### 2. 查询任务状态

```http
GET /videoTasks/{taskId}
```

返回 `status/taskStatus`、`step`、`progress`、`resultVideoUrl`、`behaviorStats`、`events`、`trackSummary` 和 `predictionWindows`。

### 3. 查询行为统计

```http
GET /videoTasks/{taskId}/stats
```

返回：

```json
[
  {
    "behaviorType": "head_down",
    "behaviorName": "低头",
    "durationSeconds": 18.4,
    "durationText": "18秒",
    "count": 6,
    "ratio": 21.8,
    "confidence": 0.91
  }
]
```

### 4. 查询预测窗口明细

```http
GET /videoTasks/{taskId}/predictions
```

返回由 `predictions.csv` 解析后的明细：

```json
[
  {
    "trackId": 1,
    "startFrame": 0,
    "endFrame": 70,
    "startSecond": 0.0,
    "endSecond": 2.8,
    "rawLabel": "head_down",
    "behaviorType": "head_down",
    "behaviorName": "低头",
    "confidence": 0.93
  }
]
```

### 5. 查询学生跟踪 ID 概览

```http
GET /videoTasks/{taskId}/track-summary
```

返回：

```json
[
  {
    "trackId": 1,
    "mainBehaviorType": "head_down",
    "mainBehaviorName": "低头",
    "durationSeconds": 18.4,
    "durationText": "18秒",
    "avgConfidence": 0.91,
    "windowCount": 6
  }
]
```

### 6. 获取结果视频文件

```http
GET /videoTasks/{taskId}/result-video
```

兜底返回 `videos/result_h264.mp4` 文件流，`mimetype` 为 `video/mp4`，并开启 Flask 条件响应。正常前端优先使用 `resultVideoUrl`，即上传到 Spring Boot `/files/upload` 后得到的视频 URL。

## Socket.IO 数据

算法任务运行期间，Flask 通过 `message` 和 `progress` 推送。

`progress`：

```json
{
  "data": 90,
  "taskId": "task_20260521_100000_ab12cd",
  "step": "parse"
}
```

`message` 保持 `classroom-demo-v1` 协议，并新增任务字段：

```json
{
  "protocolVersion": "classroom-demo-v1",
  "sessionId": "CLASS-AB12CD34",
  "taskId": "task_20260521_100000_ab12cd",
  "taskStatus": "done",
  "step": "done",
  "message": "检测完成",
  "sourceType": "video",
  "sourceName": "input.mp4",
  "progress": 100,
  "completed": true,
  "resultVideoUrl": "http://localhost:9999/files/xxx_result_h264.mp4",
  "behaviorStats": [],
  "trackSummary": [],
  "predictionWindows": [],
  "warningState": {
    "riskLevel": "medium",
    "reason": "学生目标 ID 1 的低头行为累计达到 18秒，建议教师进行非诊断式关注与沟通。",
    "durations": {
      "head_down": 18.4
    },
    "consecutiveDurations": {},
    "warning": {}
  },
  "events": []
}
```

## 标签映射

`class/` 新算法输出四类原始标签：

| 原始标签 | 对外 behaviorType | 展示名称 | 说明 |
| --- | --- | --- | --- |
| `normal` | `focus` | 专注/正常 | 正常坐姿或正常听课状态 |
| `head_down` | `head_down` | 低头 | 持续低头、看桌面、写字或看书 |
| `lie_down` | `lie_desk` | 趴桌 | 明显趴桌或上半身贴近桌面 |
| `other_action` | `other_action` | 其他行为 | 回头、说话、站立、走动等其他动作 |

保留 `rawLabel` 字段用于追溯模型原始输出。

## 预警规则

当前 v1 预警规则：

| behaviorType | 条件 | 风险等级 |
| --- | --- | --- |
| `lie_desk` | 单个 `trackId` 累计达到 10 秒 | `high` |
| `head_down` | 单个 `trackId` 累计达到 15 秒 | `medium` |
| `focus` | 不触发预警 | `normal` |
| `other_action` | v1 只做统计，不触发预警 | `low/normal` |

预警事件会写入 Spring Boot `/warningRecords`，AI 建议仍通过 `/warningRecords/advice` 获取；外部 AI 不可用时使用后端 fallback。

## 前后端数据传输方式

### 前端 -> Spring Boot

- `POST /api/files/upload`
- 上传原始录制视频素材。
- 返回 `inputVideo` URL。

### 前端 -> Flask

- `POST /flask/videoTasks`
- 发送 `inputVideo`、用户名、任务参数。
- 返回 `taskId`。

### Flask -> 前端

- Socket.IO `progress`
- 推送任务进度数字。
- Socket.IO `message`
- 推送统一检测协议、统计、预警、最终结果视频 URL。
- 前端同时每 3 秒轮询 `GET /flask/videoTasks/{taskId}` 作为兜底，确保 Socket.IO 未及时返回时，行为统计和 AI 干预事件也能从算法任务结果刷新。

### Flask -> Spring Boot

- `POST /files/upload`
- 上传 `result_h264.mp4`。
- `POST /videoRecords`
- 保存输入视频、输出视频、模型、阈值、用户和开始时间。
- `POST /warningRecords`
- 保存风险预警事件。
- `POST /warningRecords/advice`
- 获取 AI 辅助干预建议。

### 前端播放结果

前端不再用：

```html
<img src="http://127.0.0.1:5000/predictVideo?...">
```

改为：

```html
<video :src="resultVideoUrl" controls preload="metadata"></video>
```

点击“开始检测”后的页面刷新规则：

- 立即清空原来的演示统计，显示“等待算法结果”。
- 算法任务进入 `parse/upload/done` 后，用 `behaviorStats` 刷新“行为统计”卡片。
- 用 `events` / `warningState.warning` 刷新右侧“AI 辅助干预”的检测事件、触发原因、风险等级、置信度和建议。
- 完成后用 `resultVideoUrl` 播放 `result_h264.mp4`。

## 性能说明

结果视频传输一般不是主要耗时，主要耗时在算法流水线：

- YOLOv8 + ByteTrack 跟踪
- RTMPose 姿态关键点提取
- LSTM/BiLSTM 时间窗口行为识别
- OpenCV 可视化和 FFmpeg H.264 转码

如果视频较大，建议后续优化 Spring Boot `/files/{flag}` 的视频响应，支持 `Range` 分片和 `video/mp4` content type，减少浏览器等待时间。

## 验证建议

1. 运行 Python 语法检查：

```powershell
python -m py_compile classDetectionFlask\class_pipeline.py classDetectionFlask\main.py class\scripts\run_single_pipeline.py
```

2. 使用短视频验证 pipeline：

```powershell
python class\scripts\run_single_pipeline.py --video class\sample\input.mp4 --runtime_dir class\runtime --task_id task_test --yolo_device cpu --rtmpose_device cpu --lstm_device cpu --frame_stride 5
```

3. 启动三端服务后，在前端视频检测页完成：

- 上传录制视频。
- 启动检测任务。
- 看到进度更新。
- 完成后播放 H.264 结果视频。
- 行为统计和预警事件更新。
- AI 干预建议可生成。
