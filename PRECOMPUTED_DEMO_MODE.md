# 现场快速预处理模式说明

更新时间：2026-05-21

## 背景

完整算法链路需要依次执行 YOLOv8/ByteTrack、RTMPose、LSTM 行为分类和视频转码。2-3 分钟课堂视频即使用 GPU 也可能耗时 10 分钟以上，不适合比赛现场等待。

因此当前演示页改为默认使用“预处理素材包”：赛前先生成 `track_boxes.csv`、`keypoints.csv`、`predictions.csv`，现场点击“开始检测”时只读取这些离线结果，快速生成或复用带标签视频，并同步刷新行为统计、预警事件和 AI 辅助干预。

## 素材包结构

推荐把现场演示素材放到 `class/sample/`：

```text
class/sample/
  input.mp4
  track_boxes.csv
  keypoints.csv
  predictions.csv
  result_h264.mp4   # 可选，存在时直接复用，速度最快
  result.mp4        # 可选，作为备用结果视频
```

也支持放到 `class/runtime/<dataset_name>/`：

```text
class/runtime/<dataset_name>/
  input.mp4
  track_boxes/track_boxes.csv   # 或直接 track_boxes.csv
  keypoints/keypoints.csv       # 或直接 keypoints.csv
  predictions.csv
  videos/result_h264.mp4        # 可选
```

## 接口变化

- `GET /flask/class-preprocessed`
  - 返回 `class/sample` 和 `class/runtime/*` 下可用的预处理素材包。

- `GET /flask/sample-video`
  - 返回 `class/sample/input.mp4`，用于页面左侧“处理前视频”默认预览。

- `GET /flask/videoTasks/{taskId}/input-video`
  - 返回当前任务复制后的原始视频。

- `POST /flask/videoTasks` 新增字段：

```json
{
  "usePrecomputed": true,
  "preprocessedDataset": "sample",
  "reuseResultVideo": true
}
```

字段含义：

- `usePrecomputed`：为 `true` 时跳过完整模型推理，只读取预处理 CSV。
- `preprocessedDataset`：指定素材包名称，默认 `sample`。
- `reuseResultVideo`：为 `true` 且素材包已有 `result_h264.mp4` / `result.mp4` 时直接复用；否则 Flask 调用 `class/scripts/run_single_visualize.py` 根据 CSV 给视频叠加标签，再尝试转码为浏览器友好的 H.264。

## 前端展示变化

`classDetectionVue/src/views/videoPredict/index.vue` 已改为左右对比：

- 左侧展示处理前视频，默认读取 `/flask/sample-video`。
- 右侧展示处理后视频，检测完成后读取 `resultVideoUrl` 或 `/flask/videoTasks/{taskId}/result-video`。
- 行为统计、AI 辅助干预、预警事件仍然来自 `predictions.csv` 解析结果。
- Flask 会把 `input.mp4` 和结果视频转为浏览器可播放的 H.264/yuv420p，再通过 Flask 视频接口提供给前端；页面顶部的分辨率、时长、帧率从实际视频元数据更新，不再使用固定展示值。
- 行为统计卡片、行为时长趋势图、行为占比图统一由 `/videoTasks/{taskId}` 返回的 `behaviorStats` 和 `predictionWindows` 刷新：卡片/饼图按 `durationSeconds` 展示“累计人次时长”，趋势图按 `startSecond/endSecond` 分段统计每类行为在时间轴上的累计人次秒数。
- 统计口径不是“视频自然播放时长”。算法端会先按 `trackId + behaviorType` 合并重叠滑窗，再累计每个学生轨迹的行为时长；因此同一学生的重叠窗口不会重复计时，但多个学生同时出现同类行为时，累计人次时长仍可能大于视频长度。
- 卡片里的“片段”表示合并后的连续行为片段数，不等同于右侧 AI 辅助干预里的风险预警事件数。

## 现场推荐流程

1. 赛前运行完整算法，生成 CSV 和可选的 `result_h264.mp4`。
2. 将素材包放入 `class/sample` 或 `class/runtime/<dataset_name>`。
3. 启动 Flask、Spring Boot、Vue。
4. 打开“录制视频检测”页面，选择预处理素材包。
5. 点击“开始检测”，页面快速展示处理前/处理后视频，并同步刷新统计与 AI 干预内容。
