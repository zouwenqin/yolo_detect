# AGENTS.md

本文件面向后续接手本仓库的开发者和 AI coding agent。请先读完本文件，再修改代码。

当前项目分支基线：`codex/dev`。项目主题为“课堂监控视频行为检测与 AI 辅助干预系统”，比赛展示主线是使用录制好的课堂监控视频素材识别人物行为并生成预警，不以摄像头实时监控作为主要展示方向。

## 项目概览

这是一个三端协同的课堂行为检测系统：

- `classDetectionVue/`：Vue3 + Vite + Element Plus 前端，负责视频素材上传、检测过程展示、行为统计、预警事件、AI 辅助干预和报告页面。
- `classDetectionSpringboot/`：Spring Boot + MyBatis Plus + MySQL 后端，负责用户、文件、检测记录、预警记录、AI 建议接口和业务数据持久化。
- `classDetectionFlask/`：Flask + YOLOv8 + OpenCV 算法服务，负责图片/录制视频素材检测、视频逐帧分析、行为标签归一化、时长统计和风险事件生成。
- 根目录文档：
  - `DETECTION_PROTOCOL.md`：前端、后端、算法服务之间的检测数据协议。
  - `PROJECT_DOCUMENTATION.md`：项目说明文档。
  - `COMPETITION_PRESENTATION_GUIDE.md`：比赛展示执行手册。
  - `COMPETITION_SLIDE_OUTLINE.md`：比赛 PPT 提纲。
  - `COMPETITION_REHEARSAL_CHECKLIST.md`：彩排检查表。

核心业务链路：

```text
录制课堂监控视频素材
  -> Flask/YOLOv8 逐帧检测人物行为
  -> detection_protocol.py 归一化行为标签、统计持续时长、生成风险事件
  -> 前端接收检测消息并更新 demoState
  -> Spring Boot 保存 warning_records 等业务记录
  -> 前端展示检测结果、行为统计、AI 干预建议和报告
```

## 运行环境与端口

本项目通常需要三个服务同时运行：

| 服务 | 路径 | 默认端口 | 说明 |
| --- | --- | --- | --- |
| Vue 前端 | `classDetectionVue/` | `8888` | Vite dev server |
| Spring Boot 后端 | `classDetectionSpringboot/` | `9999` | Java 8 / Spring Boot 2.3.7 |
| Flask 算法服务 | `classDetectionFlask/` | `5000` | Python / Flask / YOLOv8 / OpenCV |
| MySQL | local | `3306` | 数据库名通常为 `yolo_detect` |

前端代理配置在 `classDetectionVue/vite.config.ts`：

- `/api` -> `http://localhost:9999/`
- `/flask` -> `http://localhost:5000/`

后端配置参考：

- 示例配置：`classDetectionSpringboot/src/main/resources/application.properties.example`
- 本地真实配置：`classDetectionSpringboot/src/main/resources/application.properties`

注意：不要把真实数据库密码、外部 AI API key、部署密钥写进新文档或提交到新配置里。若需要说明配置方式，使用占位符。

## 常用命令

前端：

```powershell
cd classDetectionVue
npm install
npm run dev
npm run build
```

后端：

```powershell
cd classDetectionSpringboot
.\mvnw.cmd spring-boot:run
.\mvnw.cmd test
```

如果本机 Maven wrapper 不可用，也可使用已安装的 Maven：

```powershell
cd classDetectionSpringboot
mvn spring-boot:run
mvn test
```

算法服务：

```powershell
cd classDetectionFlask
python main.py
```

Python 依赖没有集中锁定文件时，不要随意升级核心库。尤其是 `ultralytics`、`opencv-python`、`flask`、`flask-socketio`、`requests`，升级前要验证视频检测链路。

## 重点展示口径

比赛材料和演示应保持以下口径：

- 主线是“录制课堂监控视频素材分析”，不是现场摄像头实时监控。
- 重点展示识别视频中的人物行为、统计持续时长、生成风险预警。
- AI 干预建议是教师沟通辅助，不是医学诊断或心理诊断。
- 结果以“课堂事件”为单位，不强调学生实名追踪。
- 隐私表达要谨慎：本项目用于辅助教师发现课堂状态，不用于公开点名、贴标签或替代专业判断。

如果修改展示页面、PPT 或说明文档，请避免把“实时摄像头监控”写成核心卖点。

## 前端开发指南

主要技术：

- Vue3 + Vite
- TypeScript
- Element Plus
- ECharts
- Pinia
- Axios
- socket.io-client

关键文件：

- `classDetectionVue/src/views/videoPredict/index.vue`
  - 录制视频素材上传/预览。
  - 模型权重选择。
  - 置信度阈值。
  - 检测状态、进度、统计图和 AI 干预入口。
- `classDetectionVue/src/views/demo/demoState.ts`
  - 比赛演示态数据中心。
  - 维护素材信息、事件列表、行为统计、AI 历史、报告文本。
  - `applyProtocolPayload(payload)` 将算法协议消息转为前端事件和统计状态。
- `classDetectionVue/src/views/demo/detectionResult/index.vue`
  - 检测事件列表和事件详情。
  - 会读取后端 `/api/warningRecords/all` 同步预警记录。
- `classDetectionVue/src/views/demo/behaviorStats/index.vue`
  - 行为统计图表。
- `classDetectionVue/src/views/demo/aiIntervention/index.vue`
  - AI 辅助干预建议。
- `classDetectionVue/src/views/demo/interventionReport/index.vue`
  - 干预报告预览和导出。
- `classDetectionVue/src/utils/socket.ts`
  - 与 Flask 算法服务建立 Socket.IO 连接。
- `classDetectionVue/src/utils/request.ts`
  - Axios 实例和响应拦截。

前端修改原则：

- 优先保持现有 Vue 单文件组件风格：`<template>`、`<script setup lang="ts">`、`<style scoped lang="scss">`。
- 新增比赛演示功能时，优先接入 `demoState.ts`，不要在多个页面复制分散状态。
- 风险等级和行为名称应复用 `demoState.ts` 中的映射函数，例如 `behaviorText`、`riskText`、`riskTagType`。
- 检测协议字段优先按 `DETECTION_PROTOCOL.md` 和 `applyProtocolPayload` 处理，不要在页面内临时解析散乱字段。
- 页面文案要面向教师和比赛评委，避免技术调试口吻。
- 不要把 camera 页面作为比赛主流程，除非用户明确要求。

前端风险点：

- `request.ts` 中 `baseURL` 使用 Vite 环境变量；本地开发实际依赖 Vite proxy 和 `/api` 前缀。修改请求路径时要确认代理仍然生效。
- 一些历史代码和字符串存在编码显示异常。不要无关地批量“修复编码”，除非用户明确要求；否则容易制造大面积 diff。
- ECharts 容器高度和页面布局要保持稳定，避免现场展示时图表不渲染或挤压。

## 后端开发指南

主要技术：

- Java 8
- Spring Boot 2.3.7
- MyBatis Plus
- MySQL
- Fastjson
- Hutool

入口：

- `classDetectionSpringboot/src/main/java/com/example/Kcsj/Kcsj.java`

关键控制器：

- `PredictionController.java`
  - 路径前缀：`/flask`
  - `POST /flask/predict`：接收图片检测请求，调用 Flask `/predictImg`，保存图片检测记录。
  - `GET /flask/file_names`：获取 Flask 权重文件列表。
- `WarningRecordsController.java`
  - 路径前缀：`/warningRecords`
  - `GET /warningRecords/all`：获取所有预警记录。
  - `GET /warningRecords`：分页查询，支持 `search`、`riskLevel`、`behaviorType`、`status`。
  - `POST /warningRecords`：保存预警记录。
  - `POST /warningRecords/update`：更新预警记录。
  - `POST /warningRecords/advice`：生成 AI 干预建议，外部 AI 不可用时返回本地兜底建议。
- `FileController.java`
  - 路径前缀：`/files`
  - `POST /files/upload`：上传视频/图片素材。
- `ImgRecordsController.java`、`VideoRecordsController.java`、`CameraRecordsController.java`
  - 记录类 CRUD。
- `UserController.java`
  - 登录、注册、用户管理。

后端修改原则：

- 统一返回 `Result`，成功码为字符串 `"0"`，前端常按 `res.code === 0` 或 `res.code == 0` 判断，修改时要兼容。
- 新接口尽量保持 REST 路径清晰，前端通过 `/api/...` 访问。
- 预警记录是比赛展示闭环的核心，不要随意改 `WarningRecords` 字段语义。
- AI 建议接口必须保留本地 fallback，比赛现场不能依赖外部 API 一定可用。
- 外部 AI 环境变量目前使用：
  - `DEEPSEEK_API_KEY`
  - `DEEPSEEK_API_URL`
  - `DEEPSEEK_MODEL`
- 不要在代码中硬编码新的 API key。

后端风险点：

- `application.properties` 可能包含本机数据库配置。新增说明时使用 `application.properties.example`，避免扩散真实凭据。
- `pom.xml` 中存在历史依赖和重复 `fastjson` 版本。非必要不要大改依赖树；如果必须升级，先完整验证后端启动和接口。
- 文件上传大小配置为 500MB，视频素材演示要留意磁盘空间和上传耗时。

## 算法服务开发指南

主要技术：

- Flask
- Flask-SocketIO
- YOLOv8 / ultralytics
- OpenCV
- requests

关键文件：

- `classDetectionFlask/main.py`
  - Flask 路由注册。
  - `predictImg`：图片检测。
  - `predictVideo`：录制视频素材检测，比赛展示主线。
  - `predictCamera`：摄像头检测，当前不是比赛主线。
  - `build_detections`、`handle_protocol_warning` 等辅助逻辑。
- `classDetectionFlask/detection_protocol.py`
  - `DetectionProtocolAdapter`：将模型输出转成稳定协议。
  - `normalize_behavior_label`：行为标签归一化。
  - `behaviorStats`：行为统计。
  - `warningState` / `events`：风险状态和预警事件。
- `classDetectionFlask/predict/predictImg.py`
  - 图片检测封装。
- `classDetectionFlask/train.py`、`test.py`
  - 训练/测试脚本。比赛展示通常不现场训练。

算法服务路由：

- `GET /file_names`
- `POST /predictImg`
- `GET /predictVideo`
- `GET /predictCamera`
- `GET /stopCamera`

算法修改原则：

- 比赛主线围绕 `predictVideo` 和录制视频素材，不要把摄像头逻辑作为主要验收目标。
- 模型输出类别可能是中文、英文或别名，必须经过 `normalize_behavior_label` 归一化。
- 风险事件不要只看单帧检测，应结合连续时长和累计时长。
- `DetectionProtocolAdapter` 输出结构要与 `DETECTION_PROTOCOL.md`、前端 `applyProtocolPayload` 保持一致。
- 对外发送给前端的数据字段应稳定，尤其是：
  - `protocolVersion`
  - `sessionId`
  - `sourceType`
  - `sourceName`
  - `progress`
  - `labels`
  - `normalizedLabels`
  - `displayLabels`
  - `detections`
  - `behaviorStats`
  - `warningState`
  - `events`
- 如果修改阈值，例如趴桌、睡觉、低头、玩手机触发时长，要同步更新比赛讲解材料。

算法风险点：

- 视频检测会读写 `classDetectionFlask/runs/` 下的临时文件。不要把大视频、检测结果、模型权重误提交。
- YOLO 权重通常在 `classDetectionFlask/weights/`。不要移动默认权重文件，除非同步修改前端默认模型和后端说明。
- `predictVideo` 会输出 MJPEG 流用于前端展示，同时通过消息同步检测协议。修改时要同时验证画面和事件数据。
- 原代码中有不少中文字符串存在编码显示异常；不要在无关任务中大范围改动。

## 检测协议约定

协议文档：`DETECTION_PROTOCOL.md`

前端主要入口：`classDetectionVue/src/views/demo/demoState.ts` 的 `applyProtocolPayload(payload)`。

算法主要入口：`classDetectionFlask/detection_protocol.py` 的 `DetectionProtocolAdapter.update()` 和 `complete()`。

后端持久化入口：`WarningRecordsController.java` 和 Flask 中保存预警记录的 HTTP 调用。

修改协议时必须同时检查：

1. Flask payload 字段是否变化。
2. Vue `applyProtocolPayload` 是否兼容。
3. `warning_records` 实体/表是否需要新增字段。
4. 比赛展示文档是否需要同步更新。

## 数据库与 SQL

后端默认数据库：

- 数据库名：`yolo_detect`
- 默认本地连接：`jdbc:mysql://localhost:3306/yolo_detect?serverTimezone=Asia/Shanghai`
- 真实用户名/密码不要写进新提交。

相关文件：

- `classDetectionSpringboot/warning_records.sql`
- `classDetectionSpringboot/src/main/java/com/example/Kcsj/entity/*.java`
- `classDetectionSpringboot/src/main/java/com/example/Kcsj/mapper/*.java`

新增字段时：

- 同步 entity。
- 同步 SQL 或迁移说明。
- 同步前端表格字段。
- 同步比赛展示材料中对数据字段的解释。

## 文档与比赛材料维护

比赛材料以录制视频素材分析为主线：

- `COMPETITION_PRESENTATION_GUIDE.md`
- `COMPETITION_SLIDE_OUTLINE.md`
- `COMPETITION_REHEARSAL_CHECKLIST.md`

修改项目能力后，如果影响演示流程，需要同步修改这些文档。例如：

- 新增行为类别。
- 修改风险阈值。
- 修改 AI 建议生成逻辑。
- 修改报告导出内容。
- 修改页面演示路径。

不要把“摄像头实时监控”重新写成核心展示卖点，除非用户明确要求改回摄像头展示。

## 测试与验证

修改前端后至少运行：

```powershell
cd classDetectionVue
npm run build
```

修改后端后至少运行：

```powershell
cd classDetectionSpringboot
.\mvnw.cmd test
```

修改算法后建议验证：

```powershell
cd classDetectionFlask
python main.py
```

然后在前端页面上传或选择短视频素材，验证：

- 视频可以预览或开始检测。
- 检测进度有变化。
- 检测框或检测画面正常显示。
- 行为统计更新。
- 达到阈值后生成预警事件。
- AI 建议可生成；外部 AI 不可用时 fallback 可用。
- 报告页面可展示和导出。

如果不能运行完整环境，最终回复中必须说明未验证项。

## Git 与变更范围

- 当前仓库可能存在用户或其他 agent 的未提交改动。不要回滚不属于你的修改。
- 新增文档或代码前先看 `git status --short`。
- 不要执行 `git reset --hard`、`git checkout --` 等破坏性命令，除非用户明确要求。
- 修改应尽量小而聚焦，避免无关格式化。
- 不要提交大文件、视频素材、模型权重、临时输出、`runs/` 目录或构建产物。
- 如果任务涉及提交，遵循用户要求；没有明确要求时不要自行 commit。

## 编码与文案注意事项

- 项目里部分旧文件中文显示为乱码或 mojibake。不要在无关任务中全量修复，否则会产生大量无关 diff。
- 新增中文文档使用 UTF-8。
- 用户面向比赛展示时，优先使用清晰、稳妥、职业化的表述：
  - “课堂监控视频素材分析”
  - “人物行为识别”
  - “行为持续时间统计”
  - “风险预警事件”
  - “AI 辅助干预建议”
  - “非诊断式沟通建议”
- 避免绝对化宣传，例如“完全准确”“替代教师判断”“实时监控所有学生”。

## 常见任务落点

新增或修改前端展示页：

- 优先查 `classDetectionVue/src/views/demo/` 和 `classDetectionVue/src/views/videoPredict/index.vue`。
- 路由在 `classDetectionVue/src/router/route.ts`。
- 通用演示状态在 `demoState.ts`。

新增预警字段：

- 后端 entity、mapper、SQL。
- Flask 协议 payload。
- 前端 `DemoEvent` 类型和展示页面。
- 比赛文档。

修改 AI 建议：

- 后端 `WarningRecordsController.advice()` 和 fallback。
- 前端 `aiIntervention` 页面和 `demoState.fallbackAdvice`。
- 报告页 `interventionReport`。

修改行为类别：

- Flask `BEHAVIOR_NAMES` / `BEHAVIOR_ALIASES` 或 `detection_protocol.py`。
- 前端 `behaviorLabelMap`。
- 统计图和报告文案。
- `DETECTION_PROTOCOL.md`。

修改阈值：

- Flask `DetectionProtocolAdapter._build_warning()` 或 `BehaviorWarningTracker`。
- 前端设置页 `demoSettings` 若需要暴露配置。
- 比赛讲解材料中对应示例。

## 最重要的原则

这个项目不是单纯展示 YOLO 检测框，而是展示一个 AI 应用闭环：

```text
视频素材识别 -> 行为统计 -> 风险预警 -> 教师干预建议 -> 报告输出
```

任何修改都应服务这条主线。不要为了炫技引入高风险现场操作，也不要把展示重点从“录制视频素材识别与预警”偏移到“摄像头实时监控”。
