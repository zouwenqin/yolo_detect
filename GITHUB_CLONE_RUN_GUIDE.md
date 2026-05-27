# GitHub Clone 后运行说明

本项目比赛演示推荐使用“预处理结果复用模式”：不在现场重新跑 YOLO/LSTM 完整推理，而是读取 `class/input` 和 `class/output` 中已经处理好的视频、CSV 和标注结果，前端仍然展示“视频素材识别 -> 行为统计 -> 风险预警 -> AI 辅助干预建议 -> 报告输出”的完整闭环。

## 1. Clone 代码

```powershell
git clone <你的 GitHub 仓库地址>
cd project
```

仓库不会提交大视频、权重、上传文件和本地密钥配置，相关内容需要本地补齐。

## 2. 复制预处理素材

在项目根目录创建或复制以下目录：

```text
class/
  input/
    1/
      1.mp4 或 input.mp4
    2/
      2.mp4 或 input.mp4
  output/
    1/
      predictions.csv
      track_boxes.csv
      result_h264.mp4 或 result_demo_h264.mp4
    2/
      predictions.csv
      track_boxes.csv
      result_h264.mp4 或 result_demo_h264.mp4
```

只使用预处理演示时，不需要复制 `class/models`。模型权重只在重新完整推理时才需要。

每个素材编号需要在 `input` 和 `output` 中同名，例如：

```text
class/input/1/
class/output/1/
```

`output` 中至少需要：

- `predictions.csv`
- `track_boxes.csv` 或 `track_boxes/track_boxes.csv`
- 一个结果视频：优先 `result_demo_h264.mp4`，其次 `result_h264.mp4`，再其次 `result.mp4`

`input` 中的视频用于前端左侧原始视频预览。

## 3. 后端配置

复制示例配置：

```powershell
copy classDetectionSpringboot\src\main\resources\application.properties.example classDetectionSpringboot\src\main\resources\application.properties
```

然后在 `application.properties` 中填写本机 MySQL：

```properties
spring.datasource.url=jdbc:mysql://localhost:3306/yolo_detect?serverTimezone=Asia/Shanghai
spring.datasource.username=你的用户名
spring.datasource.password=你的密码
server.port=9999
file.ip=localhost
flask.api-base-url=http://localhost:5000
```

AI 建议接口可以不填真实 key；不填或不可用时，后端会返回本地兜底建议。

## 4. 启动服务

前端：

```powershell
cd classDetectionVue
npm install
npm run dev
```

后端：

```powershell
cd classDetectionSpringboot
.\mvnw.cmd spring-boot:run
```

Flask：

```powershell
cd classDetectionFlask
python main.py
```

默认端口：

- 前端：`http://localhost:8888`
- 后端：`http://localhost:9999`
- Flask：`http://localhost:5000`

## 5. 演示方式

打开前端的视频检测页面，选择“预处理素材”，点击开始检测。系统会读取 `class/output/<素材编号>` 中的 CSV 和结果视频，不会重新跑完整模型推理，所以速度会接近本机当前演示效果。

如果页面没有看到预处理素材，优先检查：

- `class/input`、`class/output` 是否放在项目根目录下。
- `input` 和 `output` 的素材编号是否一致。
- `output/<编号>` 是否有 `predictions.csv`、`track_boxes.csv` 和结果视频。
- Flask 服务是否已经启动。

## 6. 不要提交到 GitHub 的内容

以下内容应保留在本地或通过网盘单独交付：

- `class/`
- `classDetectionSpringboot/files/`
- `classDetectionFlask/runs/`
- `classDetectionFlask/weights/`
- `classDetectionSpringboot/src/main/resources/application.properties`
- 任何真实数据库密码、API key、模型权重和大视频文件
