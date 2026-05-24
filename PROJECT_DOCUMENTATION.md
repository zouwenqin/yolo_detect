# 项目详细说明文档



## 1. 项目整体是什么

这个项目是一个“基于 YOLOv8 的课堂学生行为检测系统”。用户可以在网页里登录，然后进行三类识别：

1. 图片识别：上传一张课堂图片，系统检测学生行为，生成识别后的图片和统计图。
2. 视频识别：上传视频，系统边处理边在网页显示视频流，同时实时统计专注度和心理风险预警。
3. 摄像头识别：调用本机摄像头实时检测，停止后保存处理后的视频记录。

项目根目录下有三个子项目：

```text
F:\yolo_detect\classDetection\project
├── classDetectionVue          前端页面，Vue3 + Vite + Element Plus
├── classDetectionSpringboot   Java 后端，Spring Boot + MyBatis Plus + MySQL
└── classDetectionFlask        Python 后端，Flask + YOLOv8 + OpenCV
```

可以把它理解成三个角色：

```text
浏览器页面 Vue
  负责：展示页面、按钮、上传文件、表格、图表、视频流、调用接口

Spring Boot 后端
  负责：登录注册、数据库增删改查、文件上传下载、保存识别记录、调用 Flask 图片识别、保存预警记录

Flask/Python 后端
  负责：加载 YOLO 模型、真正做图片/视频/摄像头识别、实时推送识别标签和预警状态
```

## 2. 三个服务分别跑在哪个端口

根据当前代码：

| 服务          | 默认地址                    | 主要作用                       |
| ----------- | ----------------------- | -------------------------- |
| Vue 前端      | `http://localhost:8888` | 浏览器访问的网页                   |
| Spring Boot | `http://localhost:9999` | Java 业务接口、数据库、文件上传         |
| Flask       | `http://localhost:5000` | YOLO 推理、视频流、WebSocket 实时消息 |
| MySQL       | `localhost:3306`        | 数据库 `yolo_detect`          |

对应配置文件：

- Vue 端口在 `classDetectionVue/.env`：`VITE_PORT = 8888`
- Vite 代理在 `classDetectionVue/vite.config.ts`
- Spring Boot 端口在 `classDetectionSpringboot/src/main/resources/application.properties`：`server.port=9999`
- Flask 端口在 `classDetectionFlask/main.py` 的 `VideoProcessingApp(host='0.0.0.0', port=5000)`
- MySQL 连接在 `application.properties`：

```properties
spring.datasource.url=jdbc:mysql://localhost:3306/yolo_detect?serverTimezone=Asia/Shanghai
spring.datasource.username=root
spring.datasource.password=1234
```

## 3. 前端和后端怎么交互

前端和后端主要通过 HTTP 接口交互，也就是浏览器发请求，后端返回 JSON 数据。

Vue 里统一请求工具是：

```text
classDetectionVue/src/utils/request.ts
```

它创建了一个 `axios` 对象。你可以把 axios 理解成前端里的 `requests`，类似 Python 里的：

```python
import requests
requests.get("http://localhost:9999/user")
requests.post("http://localhost:9999/user/login", json=data)
```

Vue 里写成：

```ts
request.get('/api/user')
request.post('/api/user/login', data)
```

### 3.1 `/api` 是怎么变成 Spring Boot 接口的

在开发环境里，前端页面运行在 `localhost:8888`，Java 后端运行在 `localhost:9999`，端口不同。如果浏览器直接跨端口请求，可能会遇到跨域问题。这个项目用 Vite 代理解决。

文件：

```text
classDetectionVue/vite.config.ts
```

关键配置：

```ts
proxy: {
  '/api': {
    target: 'http://localhost:9999/',
    rewrite: (path) => path.replace(/^\/api/, ''),
  },
  '/flask': {
    target: 'http://localhost:5000/',
    rewrite: (path) => path.replace(/^\/flask/, ''),
  },
}
```

含义：

```text
前端请求 /api/user/login
实际转发到 http://localhost:9999/user/login

前端请求 /api/flask/predict
实际转发到 http://localhost:9999/flask/predict

前端请求 /flask/stopCamera
实际转发到 http://localhost:5000/stopCamera
```

注意：这个代理只在 `npm run dev` 开发环境生效。如果项目打包上线，需要用 Nginx 或后端配置实现同样的转发。

### 3.2 返回数据格式

Spring Boot 统一返回格式由这个类决定：

```text
classDetectionSpringboot/src/main/java/com/example/Kcsj/common/Result.java
```

成功时大致是：

```json
{
  "code": "0",
  "msg": "成功",
  "data": {}
}
```

失败时大致是：

```json
{
  "code": "-1",
  "msg": "错误原因"
}
```

所以 Vue 代码里经常写：

```ts
if (res.code == 0) {
  // 成功，使用 res.data
} else {
  ElMessage.error(res.msg)
}
```

## 4. Vue 前端怎么理解

你可以先把 Vue 理解成“把 HTML、JavaScript、CSS 写在一个 `.vue` 文件里”的前端框架。

一个 `.vue` 文件一般有三块：

```vue
<template>
  页面结构，类似 HTML
</template>

<script setup lang="ts">
  页面逻辑，类似 JavaScript/TypeScript
</script>

<style scoped>
  页面样式，类似 CSS
</style>
```

例如图片识别页面：

```text
classDetectionVue/src/views/imgPredict/index.vue
```

- `<template>` 里写上传框、按钮、图片展示、图表容器。
- `<script setup>` 里写上传成功后保存图片 URL、点击“开始预测”后调用接口。
- `<style>` 里写页面布局和大小。

### 4.1 Vue 项目入口

| 文件                              | 作用                                          |
| ------------------------------- | ------------------------------------------- |
| `classDetectionVue/index.html`  | 浏览器最开始加载的 HTML，里面有 `#app` 容器                |
| `classDetectionVue/src/main.ts` | Vue 应用入口，创建 Vue App，注册路由、Pinia、Element Plus |
| `classDetectionVue/src/App.vue` | 根组件，里面放 `<router-view>`，真正页面会显示在这里          |

执行顺序可以理解为：

```text
index.html
  -> 加载 src/main.ts
    -> createApp(App)
      -> 使用 router
      -> 使用 pinia
      -> 挂载到 #app
        -> App.vue 里的 router-view 显示当前页面
```

### 4.2 路由是什么

路由就是“浏览器地址和页面文件的对应关系”。

主要文件：

```text
classDetectionVue/src/router/route.ts
classDetectionVue/src/router/index.ts
```

比如 `route.ts` 中有：

```ts
{
  path: '/imgPredict',
  name: 'imgPredict',
  component: () => import('/@/views/imgPredict/index.vue'),
}
```

意思是：

```text
当浏览器访问 http://localhost:8888/#/imgPredict
就加载 src/views/imgPredict/index.vue
```

主要页面对应关系：

| 地址                | 页面文件                                | 功能      |
| ----------------- | ----------------------------------- | ------- |
| `#/login`         | `src/views/login/index.vue`         | 登录      |
| `#/register`      | `src/views/login/register.vue`      | 注册      |
| `#/data`          | `src/views/data/index.vue`          | 首页/数据展示 |
| `#/imgPredict`    | `src/views/imgPredict/index.vue`    | 图片识别    |
| `#/videoPredict`  | `src/views/videoPredict/index.vue`  | 视频识别    |
| `#/cameraPredict` | `src/views/cameraPredict/index.vue` | 摄像头识别   |
| `#/imgRecord`     | `src/views/imgRecord/index.vue`     | 图片识别记录  |
| `#/videoRecord`   | `src/views/videoRecord/index.vue`   | 视频识别记录  |
| `#/cameraRecord`  | `src/views/cameraRecord/index.vue`  | 摄像头识别记录 |
| `#/warningRecord` | `src/views/warningRecord/index.vue` | 心理预警记录  |
| `#/usermanage`    | `src/views/userManage/index.vue`    | 用户管理    |
| `#/personal`      | `src/views/personal/index.vue`      | 个人中心    |

### 4.3 登录状态怎么保存

登录页面文件：

```text
classDetectionVue/src/views/login/index.vue
```

点击登录后：

```ts
request.post('/api/user/login', ruleForm)
```

也就是请求：

```text
http://localhost:9999/user/login
```

登录成功后前端做了两件事：

1. 用 `Session.set('token', ...)` 保存一个 token，表示“已经登录”。
2. 用 `Cookies.set('role', res.data.role)` 和 `Cookies.set('userName', ruleForm.username)` 保存角色和用户名。

用户信息 Store：

```text
classDetectionVue/src/stores/userInfo.ts
```

它从 Cookie 里读 `role`、`userName`，并根据角色决定能看到哪些菜单。

路由守卫：

```text
classDetectionVue/src/router/index.ts
```

它会检查是否有 `Session.get('token')`：

```text
没有 token：跳转到登录页
有 token：允许进入系统页面
```

注意：这里的 token 是前端模拟生成的随机字符串，并不是后端签发的 JWT。也就是说当前项目的登录安全性比较基础，适合课程设计展示，不适合直接当真实生产系统。

## 5. Spring Boot 后端怎么理解

Spring Boot 是 Java 写的后端服务。它主要负责：

1. 提供 HTTP 接口给 Vue 调用。
2. 操作 MySQL 数据库。
3. 上传和读取文件。
4. 图片识别时转发请求给 Flask。
5. 保存图片、视频、摄像头、心理预警记录。

### 5.1 Java 后端入口

```text
classDetectionSpringboot/src/main/java/com/example/Kcsj/Kcsj.java
```

这是 Spring Boot 启动类。运行它后，Java 后端监听 `9999` 端口。

### 5.2 Controller、Entity、Mapper 分别是什么

这三个概念非常重要。可以对照 Java 基础来理解：

```text
Controller：接收 HTTP 请求，相当于“接口入口”
Entity：数据库表对应的 Java 类，相当于“一行数据的对象模型”
Mapper：操作数据库的接口，相当于“DAO”
```

举例：图片记录。

```text
ImgRecordsController.java
  接收 /imgRecords 接口请求

ImgRecords.java
  对应数据库表 imgrecords

ImgRecordsMapper.java
  继承 BaseMapper，可以调用 insert、selectPage、deleteById、updateById
```

常见代码：

```java
imgRecordsMapper.insert(imgRecords);
imgRecordsMapper.selectPage(new Page<>(pageNum, pageSize), wrapper);
imgRecordsMapper.deleteById(id);
imgRecordsMapper.updateById(imgRecords);
```

这些就是 MyBatis Plus 帮你封装好的增删改查。

### 5.3 Java 后端主要文件

| 文件                                         | 作用                            |
| ------------------------------------------ | ----------------------------- |
| `Kcsj.java`                                | Spring Boot 启动入口              |
| `common/Result.java`                       | 统一接口返回格式                      |
| `common/CorsConfig.java`                   | 跨域配置，让前端能访问后端                 |
| `common/MybatisPlusConfig.java`            | MyBatis Plus 分页等配置            |
| `controller/UserController.java`           | 登录、注册、用户管理                    |
| `controller/FileController.java`           | 文件上传、文件下载                     |
| `controller/PredictionController.java`     | 图片识别代理，调用 Flask `/predictImg` |
| `controller/ImgRecordsController.java`     | 图片识别记录增删改查                    |
| `controller/VideoRecordsController.java`   | 视频识别记录增删改查                    |
| `controller/CameraRecordsController.java`  | 摄像头识别记录增删改查                   |
| `controller/WarningRecordsController.java` | 心理预警记录、预警建议生成                 |
| `entity/User.java`                         | `user` 表对应实体                  |
| `entity/ImgRecords.java`                   | `imgrecords` 表对应实体            |
| `entity/VideoRecords.java`                 | `videorecords` 表对应实体          |
| `entity/CameraRecords.java`                | `camerarecords` 表对应实体         |
| `entity/WarningRecords.java`               | `warning_records` 表对应实体       |
| `mapper/*.java`                            | 数据库操作接口                       |
| `application.properties`                   | 端口、数据库、文件上传大小配置               |
| `pom.xml`                                  | Maven 依赖配置                    |

## 6. Flask/Python 后端怎么理解

Python 后端负责真正的 YOLO 推理。

主要文件：

```text
classDetectionFlask/main.py
classDetectionFlask/predict/predictImg.py
classDetectionFlask/weights/class.pt
```

### 6.1 Flask 的作用

Flask 提供几个接口：

| Flask 接口         | 方法   | 作用                       |
| ---------------- | ---- | ------------------------ |
| `/file_names`    | GET  | 返回 `weights` 文件夹里的模型文件列表 |
| `/predictImg`    | POST | 图片识别                     |
| `/predictVideo`  | GET  | 视频识别，返回实时视频流             |
| `/predictCamera` | GET  | 摄像头识别，返回实时视频流            |
| `/stopCamera`    | GET  | 停止摄像头录制                  |

这些路由在 `main.py` 的 `setup_routes()` 里注册：

```python
self.app.add_url_rule('/file_names', 'file_names', self.file_names, methods=['GET'])
self.app.add_url_rule('/predictImg', 'predictImg', self.predictImg, methods=['POST'])
self.app.add_url_rule('/predictVideo', 'predictVideo', self.predictVideo)
self.app.add_url_rule('/predictCamera', 'predictCamera', self.predictCamera)
self.app.add_url_rule('/stopCamera', 'stopCamera', self.stopCamera, methods=['GET'])
```

### 6.2 YOLO 图片识别类

文件：

```text
classDetectionFlask/predict/predictImg.py
```

核心类：

```python
class ImagePredictor:
```

它做的事情：

1. 加载 YOLO 模型：

```python
self.model = YOLO(weights_path)
```

2. 用模型预测图片：

```python
results = self.model(source=self.img_path, conf=self.conf, half=True, save_conf=True)
```

3. 从结果里取类别和置信度：

```python
confidences = result.boxes.conf
labels = result.boxes.cls
```

4. 保存识别后的图片：

```python
result.save(filename=self.save_path)
```

5. 返回：

```json
{
  "labels": ["举手", "阅读"],
  "confidences": ["95.20%", "88.31%"],
  "allTime": "0.123秒"
}
```

### 6.3 视频和摄像头实时识别

视频和摄像头逻辑都在：

```text
classDetectionFlask/main.py
```

核心流程：

```text
OpenCV 读取视频帧/摄像头帧
  -> YOLO 对每一帧预测
  -> results[0].plot() 画出检测框
  -> cv2.imencode('.jpg', processed_frame) 编码成 jpg
  -> Flask Response 用 multipart/x-mixed-replace 返回给前端
  -> 前端 <img :src="..."> 像播放视频一样显示连续图片
```

这就是为什么前端视频识别页面用的是：

```html
<img v-if="state.video_path" class="video" :src="state.video_path">
```

它不是普通图片，而是 Flask 持续返回的一帧一帧 JPEG 流。

### 6.4 WebSocket 实时消息

HTTP 视频流只能显示画面，不方便推送额外数据，例如“当前识别标签”“预警状态”“保存进度”。所以项目还用了 Socket.IO。

前端：

```text
classDetectionVue/src/utils/socket.ts
```

```ts
this.socket = io('http://localhost:5000');
```

Flask：

```python
self.socketio = SocketIO(self.app, cors_allowed_origins="*")
```

视频/摄像头每处理一帧，Flask 会推送：

```python
self.socketio.emit('message', {
  'labels': labels,
  'warningState': warning_state
})
```

前端监听：

```ts
socketService.on('message', (data) => {
  // 更新专注度曲线、预警面板
})
```

保存视频时，Flask 还会推送进度：

```python
self.socketio.emit('progress', {'data': progress})
```

前端监听后更新进度条。

## 7. 图片识别完整流程

这是最典型、最容易理解的一条链路。

```text
用户打开图片识别页
  -> Vue 获取模型列表
  -> 用户上传图片到 Spring Boot
  -> Spring Boot 保存图片并返回图片 URL
  -> 用户点击开始预测
  -> Vue 把图片 URL、模型名、置信度、用户名等发给 Spring Boot
  -> Spring Boot 调用 Flask 图片识别接口
  -> Flask 加载 YOLO 模型并识别图片
  -> Flask 把结果图片上传回 Spring Boot
  -> Flask 返回识别标签、置信度、耗时、结果图 URL
  -> Spring Boot 保存识别记录到 MySQL
  -> Vue 展示结果图片、统计文字、柱状图、饼图
```

### 7.1 获取模型列表

前端文件：

```text
classDetectionVue/src/views/imgPredict/index.vue
```

调用：

```ts
request.get('/api/flask/file_names')
```

经过 Vite 代理后：

```text
/api/flask/file_names
  -> http://localhost:9999/flask/file_names
```

Java 文件：

```text
classDetectionSpringboot/src/main/java/com/example/Kcsj/controller/PredictionController.java
```

Java 再调用 Flask：

```java
restTemplate.getForObject("http://127.0.0.1:5000/file_names", String.class)
```

Flask 文件：

```text
classDetectionFlask/main.py
```

Flask 读取：

```text
classDetectionFlask/weights
```

返回类似：

```json
{
  "weight_items": [
    {
      "value": "class.pt",
      "label": "class.pt"
    }
  ]
}
```

### 7.2 上传图片

前端图片上传组件：

```vue
<el-upload
  action="http://localhost:9999/files/upload"
  :on-success="handleAvatarSuccessone">
</el-upload>
```

这里没有走 `/api` 代理，而是直接请求 Spring Boot：

```text
POST http://localhost:9999/files/upload
```

Java 文件：

```text
classDetectionSpringboot/src/main/java/com/example/Kcsj/controller/FileController.java
```

后端会把文件保存到：

```text
classDetectionSpringboot/files
```

返回一个可访问 URL：

```text
http://localhost:9999/files/随机ID_原文件名
```

前端保存这个 URL：

```ts
state.img = response.data
```

### 7.3 开始图片预测

前端点击按钮执行 `upData()`：

```ts
request.post('/api/flask/predict', state.form)
```

请求体大概是：

```json
{
  "username": "admin",
  "weight": "class.pt",
  "conf": 0.5,
  "startTime": "2026-05-07 16:00:00",
  "inputImg": "http://localhost:9999/files/xxx.png",
  "kind": "class"
}
```

经过代理：

```text
Vue /api/flask/predict
  -> Spring Boot http://localhost:9999/flask/predict
```

Java 文件：

```text
classDetectionSpringboot/src/main/java/com/example/Kcsj/controller/PredictionController.java
```

Java 再调用 Flask：

```java
restTemplate.postForObject("http://localhost:5000/predictImg", requestEntity, String.class)
```

Flask 接口：

```text
POST http://localhost:5000/predictImg
```

Flask 调用：

```python
predict = predictImg.ImagePredictor(
  weights_path=f'./weights/{weight}',
  img_path=inputImg,
  save_path='./runs/result.jpg',
  kind=kind,
  conf=float(conf)
)
results = predict.predict()
```

识别完成后，Flask 把结果图上传回 Spring Boot：

```python
self.upload('./runs/result.jpg')
```

上传接口仍然是：

```text
POST http://localhost:9999/files/upload
```

最后 Flask 返回给 Java：

```json
{
  "status": 200,
  "message": "预测成功",
  "outImg": "http://localhost:9999/files/xxx_result.jpg",
  "allTime": "0.123秒",
  "confidence": "[\"95.20%\"]",
  "label": "[\"举手\"]"
}
```

Java 收到后保存到数据库表 `imgrecords`：

```java
imgRecordsMapper.insert(imgRecords);
```

Vue 收到结果后：

1. 把 `outImg` 显示为结果图。
2. 解析 `label` 和 `confidence`。
3. 用 ECharts 画行为统计柱状图和专注度饼图。

## 8. 视频识别完整流程

视频识别和图片识别不同：视频需要边处理边显示，所以前端更直接地访问 Flask 视频流。

```text
用户打开视频识别页
  -> Vue 获取模型列表
  -> 用户上传视频到 Spring Boot
  -> Spring Boot 返回 inputVideo URL
  -> 用户点击开始处理
  -> Vue 构造 Flask /predictVideo URL，放到 <img src>
  -> 浏览器向 Flask 请求视频流
  -> Flask 下载原视频
  -> Flask 用 YOLO 逐帧检测
  -> Flask 把处理后的帧连续返回给前端显示
  -> Flask 通过 WebSocket 推送 labels、warningState、progress
  -> Flask 处理完后转 MP4、上传 Spring Boot
  -> Flask 调用 Spring Boot /videoRecords 保存记录
```

### 8.1 上传视频

前端文件：

```text
classDetectionVue/src/views/videoPredict/index.vue
```

上传接口：

```text
POST http://localhost:9999/files/upload
```

返回视频 URL 后保存：

```ts
state.form.inputVideo = response.data
```

### 8.2 开始处理视频

前端：

```ts
const queryParams = new URLSearchParams(state.form).toString();
state.video_path = `http://127.0.0.1:5000/predictVideo?${queryParams}`;
```

页面里：

```html
<img v-if="state.video_path" class="video" :src="state.video_path">
```

这会让浏览器访问：

```text
GET http://127.0.0.1:5000/predictVideo?username=...&weight=...&conf=...&inputVideo=...
```

Flask 文件：

```text
classDetectionFlask/main.py
```

核心方法：

```python
def predictVideo(self):
```

它做这些事：

1. 从 query 参数读取用户名、模型名、置信度、视频 URL。
2. 下载视频到 `./runs/video/download.mp4`。
3. 用 `cv2.VideoCapture` 逐帧读取。
4. 用 `YOLO` 逐帧预测。
5. 用 `results[0].plot()` 画检测框。
6. 用 `yield` 持续返回 JPEG 帧给浏览器。
7. 同时写入本地临时视频。
8. 处理结束后用 FFmpeg 转成 MP4。
9. 上传结果视频到 Spring Boot。
10. 调用 `http://localhost:9999/videoRecords` 保存记录。

### 8.3 视频识别实时消息

前端通过：

```text
classDetectionVue/src/utils/socket.ts
```

连接：

```text
http://localhost:5000
```

Flask 每帧推送：

```json
{
  "labels": ["read", "write"],
  "warningState": {
    "riskLevel": "normal",
    "durations": {
      "sleep": 0,
      "lie_desk": 0,
      "head_down": 0,
      "phone": 0
    }
  }
}
```

前端收到后：

1. 调用 `onFrameDetect()` 更新专注度折线图。
2. 更新右侧心理风险预警面板。
3. 如果有预警，显示提示消息和干预建议。

## 9. 摄像头识别完整流程

摄像头识别和视频识别很像，只是输入源变成了本机摄像头。

```text
用户打开摄像头识别页
  -> 选择模型和置信度
  -> 点击开始录制
  -> Vue 构造 Flask /predictCamera URL，放到 <img src>
  -> Flask 打开 cv2.VideoCapture(0)
  -> YOLO 实时检测摄像头画面
  -> 画面通过 HTTP 流返回前端
  -> labels、warningState 通过 WebSocket 推送
  -> 用户点击结束录制
  -> Vue 调用 Flask /stopCamera
  -> Flask 停止循环、转 MP4、上传结果视频、保存 cameraRecords
```

前端开始：

```ts
state.video_path = `http://127.0.0.1:5000/predictCamera?${queryParams}`;
```

Flask：

```python
cap = cv2.VideoCapture(0)
```

前端停止：

```ts
request.get('/flask/stopCamera')
```

经过 Vite 代理：

```text
/flask/stopCamera
  -> http://localhost:5000/stopCamera
```

Flask 设置：

```python
self.recording = False
```

循环结束后保存记录到：

```text
POST http://localhost:9999/cameraRecords
```

## 10. 心理预警功能怎么连接

改完之后项目里新增或强化了课堂心理风险预警相关逻辑。核心在 Flask 的 `BehaviorWarningTracker` 和 Spring Boot 的 `WarningRecordsController`。

### 10.1 Flask 里怎么判断预警

文件：

```text
classDetectionFlask/main.py
```

类：

```python
class BehaviorWarningTracker:
```

它重点关注这些行为：

```python
["sleep", "lie_desk", "head_down", "phone"]
```

也就是：

| 行为 key      | 含义  |
| ----------- | --- |
| `sleep`     | 睡觉  |
| `lie_desk`  | 趴桌  |
| `head_down` | 低头  |
| `phone`     | 玩手机 |

每处理一帧，Flask 会把 YOLO 检测到的标签传入：

```python
warning_state = warning_tracker.update(labels)
```

它会累计每种异常行为持续的时间。

触发规则大概是：

| 行为   | 触发条件         | 风险等级   |
| ---- | ------------ | ------ |
| 睡觉   | 连续或累计超过 10 秒 | high   |
| 趴桌   | 连续或累计超过 10 秒 | high   |
| 持续低头 | 连续或累计超过 15 秒 | medium |
| 玩手机  | 累计超过 15 秒    | low    |

触发后会生成：

```json
{
  "riskLevel": "high",
  "behaviorType": "sleep",
  "durationSeconds": 10.0,
  "reason": "疑似睡觉行为累计超过10秒"
}
```

### 10.2 Flask 怎么保存预警

触发预警后，Flask 调用：

```python
self.enrich_and_save_warning(...)
```

它会先请求 Spring Boot 生成干预建议：

```text
POST http://localhost:9999/warningRecords/advice
```

然后保存预警记录：

```text
POST http://localhost:9999/warningRecords
```

保存的数据类似：

```json
{
  "videoSource": "camera",
  "detectionType": "camera",
  "riskLevel": "high",
  "behaviorType": "sleep",
  "durationSeconds": 10.0,
  "triggerTime": "2026-05-07 16:00:00",
  "reason": "疑似睡觉行为累计超过10秒",
  "advice": "教师干预建议...",
  "status": "未处理",
  "username": "admin"
}
```

### 10.3 Spring Boot 怎么生成建议

文件：

```text
classDetectionSpringboot/src/main/java/com/example/Kcsj/controller/WarningRecordsController.java
```

接口：

```text
POST /warningRecords/advice
```

它会先读取 Spring Boot 固定配置文件：

```text
classDetectionSpringboot/src/main/resources/application.properties
```

配置项如下：

```properties
llm.api-key=你的API-Key
llm.api-url=https://api.minimax.io/v1/chat/completions
llm.model=MiniMax-M2.7
```

如果 `llm.api-key` 为空，就返回本地兜底建议，不会调用大模型。

如果配置了：

```text
llm.api-key
llm.api-url
llm.model
```

就会请求对应的大模型接口生成更自然的教师干预建议。当前默认示例是 MiniMax，也可以把 `llm.api-url` 和 `llm.model` 改成阿里千问、Kimi 或 DeepSeek 的 OpenAI 兼容接口。

这部分的定位是“非诊断性建议”，也就是只给教师课堂观察和沟通建议，不做医学诊断，不给学生贴标签。

### 10.4 前端怎么展示预警

视频识别页面：

```text
classDetectionVue/src/views/videoPredict/index.vue
```

摄像头识别页面：

```text
classDetectionVue/src/views/cameraPredict/index.vue
```

这两个页面都有：

1. 专注度实时折线图。
2. 心理风险实时预警面板。
3. 异常行为持续时间。
4. 教师干预建议。

前端监听 Socket.IO：

```ts
socketService.on('message', (data) => {
  if (data.warningState) {
    state.warningState = data.warningState
  }
})
```

预警记录页面：

```text
classDetectionVue/src/views/warningRecord/index.vue
```

它调用：

```ts
request.get('/api/warningRecords', { params: ... })
```

也就是：

```text
GET http://localhost:9999/warningRecords
```

用于分页查询预警记录。还能调用：

```text
POST /warningRecords/update
DELETE /warningRecords/{id}
```

实现标记处理、删除记录。

## 11. 主要接口总表

### 11.1 用户接口

| 前端调用                   | 实际 Spring Boot 接口  | 方法     | 文件                    | 作用      |
| ---------------------- | ------------------ | ------ | --------------------- | ------- |
| `/api/user/login`      | `/user/login`      | POST   | `UserController.java` | 登录      |
| `/api/user/register`   | `/user/register`   | POST   | `UserController.java` | 注册      |
| `/api/user`            | `/user`            | GET    | `UserController.java` | 分页查询用户  |
| `/api/user/all`        | `/user/all`        | GET    | `UserController.java` | 查询全部用户  |
| `/api/user/{username}` | `/user/{username}` | GET    | `UserController.java` | 根据用户名查询 |
| `/api/user/update`     | `/user/update`     | POST   | `UserController.java` | 更新用户    |
| `/api/user/{id}`       | `/user/{id}`       | DELETE | `UserController.java` | 删除用户    |

### 11.2 文件接口

| 调用地址                                 | 方法   | 文件                    | 作用       |
| ------------------------------------ | ---- | --------------------- | -------- |
| `http://localhost:9999/files/upload` | POST | `FileController.java` | 上传图片或视频  |
| `http://localhost:9999/files/{flag}` | GET  | `FileController.java` | 下载或访问文件  |
| `/files/editor/upload`               | POST | `FileController.java` | 富文本编辑器上传 |

### 11.3 图片识别接口

| 前端调用                    | Spring Boot         | Flask         | 作用      |
| ----------------------- | ------------------- | ------------- | ------- |
| `/api/flask/file_names` | `/flask/file_names` | `/file_names` | 获取模型文件名 |
| `/api/flask/predict`    | `/flask/predict`    | `/predictImg` | 图片识别    |

### 11.4 视频和摄像头接口

| 前端调用                                      | 实际服务                   | 方法        | 作用        |
| ----------------------------------------- | ---------------------- | --------- | --------- |
| `http://127.0.0.1:5000/predictVideo?...`  | Flask `/predictVideo`  | GET       | 视频识别流     |
| `http://127.0.0.1:5000/predictCamera?...` | Flask `/predictCamera` | GET       | 摄像头识别流    |
| `/flask/stopCamera`                       | Flask `/stopCamera`    | GET       | 停止摄像头     |
| Socket.IO `message`                       | Flask WebSocket        | WebSocket | 推送标签和预警状态 |
| Socket.IO `progress`                      | Flask WebSocket        | WebSocket | 推送视频保存进度  |

### 11.5 记录接口

| 前端调用                         | 方法         | 文件                              | 数据表               |
| ---------------------------- | ---------- | ------------------------------- | ----------------- |
| `/api/imgRecords`            | GET        | `ImgRecordsController.java`     | `imgrecords`      |
| `/api/imgRecords/{id}`       | DELETE     | `ImgRecordsController.java`     | `imgrecords`      |
| `/api/videoRecords`          | GET/POST   | `VideoRecordsController.java`   | `videorecords`    |
| `/api/videoRecords/{id}`     | GET/DELETE | `VideoRecordsController.java`   | `videorecords`    |
| `/api/cameraRecords`         | GET/POST   | `CameraRecordsController.java`  | `camerarecords`   |
| `/api/cameraRecords/{id}`    | GET/DELETE | `CameraRecordsController.java`  | `camerarecords`   |
| `/api/warningRecords`        | GET/POST   | `WarningRecordsController.java` | `warning_records` |
| `/api/warningRecords/update` | POST       | `WarningRecordsController.java` | `warning_records` |
| `/api/warningRecords/{id}`   | GET/DELETE | `WarningRecordsController.java` | `warning_records` |
| `/api/warningRecords/advice` | POST       | `WarningRecordsController.java` | 不直接对应表，用来生成建议     |

## 12. 数据库实体说明

### 12.1 `user` 用户表

对应文件：

```text
classDetectionSpringboot/src/main/java/com/example/Kcsj/entity/User.java
```

主要字段：

| 字段         | 含义                    |
| ---------- | --------------------- |
| `id`       | 用户 ID                 |
| `username` | 登录用户名                 |
| `password` | 密码                    |
| `name`     | 姓名                    |
| `sex`      | 性别                    |
| `email`    | 邮箱                    |
| `tel`      | 电话                    |
| `role`     | 角色，如 `admin`、`common` |
| `avatar`   | 头像                    |
| `time`     | 创建或注册时间               |

### 12.2 `imgrecords` 图片识别记录表

对应文件：

```text
classDetectionSpringboot/src/main/java/com/example/Kcsj/entity/ImgRecords.java
```

主要字段：

| 字段           | 含义           |
| ------------ | ------------ |
| `id`         | 记录 ID        |
| `weight`     | 使用的模型权重文件    |
| `inputImg`   | 原图 URL       |
| `outImg`     | 识别后图片 URL    |
| `confidence` | 每个检测目标置信度    |
| `allTime`    | 识别耗时         |
| `conf`       | 用户设置的最低置信度阈值 |
| `label`      | 识别到的标签列表     |
| `username`   | 操作用户         |
| `kind`       | 检测类型         |
| `startTime`  | 开始识别时间       |

### 12.3 `videorecords` 视频识别记录表

对应文件：

```text
classDetectionSpringboot/src/main/java/com/example/Kcsj/entity/VideoRecords.java
```

主要字段：

| 字段           | 含义        |
| ------------ | --------- |
| `id`         | 记录 ID     |
| `weight`     | 使用的模型     |
| `inputVideo` | 原视频 URL   |
| `outVideo`   | 处理后视频 URL |
| `conf`       | 最低置信度     |
| `username`   | 操作用户      |
| `kind`       | 检测类型      |
| `startTime`  | 开始时间      |

### 12.4 `camerarecords` 摄像头识别记录表

对应文件：

```text
classDetectionSpringboot/src/main/java/com/example/Kcsj/entity/CameraRecords.java
```

主要字段：

| 字段          | 含义          |
| ----------- | ----------- |
| `id`        | 记录 ID       |
| `weight`    | 使用的模型       |
| `outVideo`  | 摄像头录制处理后的视频 |
| `conf`      | 最低置信度       |
| `username`  | 操作用户        |
| `kind`      | 检测类型        |
| `startTime` | 开始时间        |

### 12.5 `warning_records` 心理预警记录表

对应文件：

```text
classDetectionSpringboot/src/main/java/com/example/Kcsj/entity/WarningRecords.java
```

主要字段：

| 字段                | 含义                         |
| ----------------- | -------------------------- |
| `id`              | 记录 ID                      |
| `videoSource`     | 视频来源，例如视频 URL 或 camera     |
| `detectionType`   | 来源类型，`video` 或 `camera`    |
| `riskLevel`       | 风险等级，`low`、`medium`、`high` |
| `behaviorType`    | 异常行为类型                     |
| `durationSeconds` | 持续秒数                       |
| `triggerTime`     | 触发时间                       |
| `reason`          | 触发原因                       |
| `advice`          | 教师干预建议                     |
| `status`          | 处理状态                       |
| `username`        | 操作用户                       |

## 13. 关键页面文件功能

### 13.1 登录注册

| 文件                             | 作用                             |
| ------------------------------ | ------------------------------ |
| `src/views/login/index.vue`    | 登录页，提交用户名密码到 `/api/user/login` |
| `src/views/login/register.vue` | 注册页，提交到 `/api/user/register`   |
| `src/stores/userInfo.ts`       | 根据 Cookie 里的用户名和角色生成前端用户信息     |

登录成功后的数据流：

```text
UserController 返回用户信息
  -> Vue 保存 role 到 Cookies
  -> Vue 保存 userName 到 Cookies
  -> Vue 保存 token 到 Session
  -> router/index.ts 放行页面访问
```

### 13.2 图片识别页

文件：

```text
src/views/imgPredict/index.vue
```

主要变量：

| 变量                       | 作用                          |
| ------------------------ | --------------------------- |
| `kind`                   | 检测类型，目前是 `class`            |
| `weight`                 | 模型权重文件名                     |
| `conf`                   | 置信度滑块值，前端显示 0-100，提交时除以 100 |
| `state.img`              | 上传后得到的原图 URL                |
| `state.form`             | 提交给后端的表单数据                  |
| `state.predictionResult` | 后端返回的识别结果                   |

主要方法：

| 方法                         | 作用                             |
| -------------------------- | ------------------------------ |
| `getData()`                | 获取模型列表                         |
| `handleAvatarSuccessone()` | 图片上传成功后保存图片 URL                |
| `upData()`                 | 点击开始预测，调用 `/api/flask/predict` |
| `renderCharts()`           | 用 ECharts 渲染柱状图和饼图             |

### 13.3 视频识别页

文件：

```text
src/views/videoPredict/index.vue
```

主要方法：

| 方法                         | 作用                  |
| -------------------------- | ------------------- |
| `getData()`                | 获取模型列表              |
| `handleAvatarSuccessone()` | 上传视频成功后保存视频 URL     |
| `upData()`                 | 拼接 Flask 视频流地址并开始处理 |
| `initFocusLineChart()`     | 初始化专注度折线图           |
| `onFrameDetect()`          | 每帧标签到来后计算专注/非专注比例   |

Socket 监听：

```ts
socketService.on('message', ...)
socketService.on('progress', ...)
```

### 13.4 摄像头识别页

文件：

```text
src/views/cameraPredict/index.vue
```

主要方法：

| 方法                | 作用                                |
| ----------------- | --------------------------------- |
| `start()`         | 请求 Flask `/predictCamera` 开始摄像头识别 |
| `stop()`          | 请求 Flask `/stopCamera` 停止录制       |
| `onFrameDetect()` | 更新专注度折线图                          |

### 13.5 记录页面

| 文件                                  | 作用                       |
| ----------------------------------- | ------------------------ |
| `src/views/imgRecord/index.vue`     | 查询图片识别记录，展示原图、结果图、标签和置信度 |
| `src/views/videoRecord/index.vue`   | 查询视频识别记录，展示原视频和处理后视频     |
| `src/views/cameraRecord/index.vue`  | 查询摄像头识别记录，展示处理后视频        |
| `src/views/warningRecord/index.vue` | 查询心理预警记录，支持按风险等级、行为类型筛选  |

这些页面基本都是同一种模式：

```text
onMounted()
  -> getTableData()
    -> request.get('/api/xxxRecords', { params })
      -> Spring Boot 分页查询数据库
      -> 返回 records 和 total
      -> Vue 填充 el-table
```

## 14. 为什么图片识别走 Spring Boot，而视频识别直接走 Flask

这是这个项目最容易困惑的地方。

图片识别：

```text
Vue -> Spring Boot -> Flask -> Spring Boot -> Vue
```

原因是图片识别只需要一次请求，结果也是一次性返回，所以让 Spring Boot 做中间层比较方便，还能马上保存数据库记录。

视频识别：

```text
Vue -> Flask 视频流
Flask -> Spring Boot 保存文件和记录
Flask -> Vue WebSocket 推送实时数据
```

原因是视频是连续流。如果 Vue 先请求 Spring Boot，再由 Spring Boot 转发 Flask 视频流，会更复杂。当前代码让浏览器直接拉 Flask 的视频流，Flask 处理完后自己把结果写回 Spring Boot。

可以记成：

```text
普通业务、数据库、文件：找 Spring Boot
真正 YOLO 推理、实时视频流：找 Flask
网页展示和用户交互：找 Vue
```

## 15. 如果你要调试，按什么顺序看

建议按下面顺序，不要一上来全看，会乱。

### 15.1 先看图片识别

1. `src/views/imgPredict/index.vue`
2. `src/utils/request.ts`
3. `vite.config.ts`
4. `PredictionController.java`
5. `classDetectionFlask/main.py` 的 `predictImg`
6. `predict/predictImg.py`
7. `ImgRecordsController.java`
8. `ImgRecords.java`

图片识别理解了，基本就懂一半了。

### 15.2 再看视频识别

1. `src/views/videoPredict/index.vue`
2. `src/utils/socket.ts`
3. `classDetectionFlask/main.py` 的 `predictVideo`
4. `BehaviorWarningTracker`
5. `VideoRecordsController.java`
6. `WarningRecordsController.java`

### 15.3 最后看摄像头识别

1. `src/views/cameraPredict/index.vue`
2. `classDetectionFlask/main.py` 的 `predictCamera`
3. `stopCamera`
4. `CameraRecordsController.java`

## 16. 常见问题和注意点

### 16.1 为什么页面里有 `/api`，后端 Controller 却没有 `/api`

因为 `/api` 是前端开发服务器的代理前缀，不是 Spring Boot 的真实接口路径。

```text
Vue 写 /api/user/login
Spring Boot 实际收到 /user/login
```

### 16.2 为什么有些地方写 `localhost:9999`，有些写 `/api`

当前项目混用了两种写法：

1. `request.get('/api/...')`：走 Vite 代理。
2. `action="http://localhost:9999/files/upload"`：直接请求 Java 后端。
3. `http://127.0.0.1:5000/predictVideo`：直接请求 Flask。

开发环境能跑，但如果上线部署，建议统一改成配置化地址。

### 16.3 为什么视频用 `<img>` 显示

因为 Flask 返回的是 MJPEG 流，本质上是一张张连续 JPEG 图片。浏览器会不断刷新这张 `<img>`，看起来像视频。

### 16.4 为什么需要 FFmpeg

OpenCV 先把处理后的视频写成 AVI 临时文件，之后 Flask 调用 FFmpeg 转成 MP4，这样浏览器和记录页面更容易播放。

### 16.5 为什么非 admin 用户只能看自己的记录

记录页面里有类似逻辑：

```ts
if (userInfos.value.userName != 'admin') {
  state.tableData.param.search = userInfos.value.userName;
}
```

所以普通用户查询记录时会自动按用户名过滤。

### 16.6 当前登录有什么局限

当前后端只校验用户名密码，前端成功后自己生成 token。后端接口并没有真正校验 token，所以安全性有限。课程设计展示可以，真实系统需要改成后端签发 JWT 或 Session，并给接口加鉴权。

### 16.7 心理预警是不是医学诊断

不是。代码里的设计是课堂行为预警，只根据“持续睡觉、趴桌、低头、玩手机”等行为给教师温和提醒和沟通建议。它不能替代心理测评或医学诊断。

## 17. 运行项目时要同时启动什么

一般需要同时启动四个东西：

1. MySQL：保证 `yolo_detect` 数据库存在，用户名密码和 `application.properties` 一致。
2. Spring Boot：启动 `Kcsj.java`，端口 `9999`。
3. Flask：进入 `classDetectionFlask`，运行 `main.py`，端口 `5000`。
4. Vue：进入 `classDetectionVue`，运行 `npm run dev`，端口 `8888`。

启动后访问：

```text
http://localhost:8888
```

## 18. 用一句话总结各部分连接关系

```text
Vue 负责让用户操作页面；
Spring Boot 负责业务接口、数据库、文件存储；
Flask 负责 YOLO 识别和实时视频流；
MySQL 负责保存用户、识别记录、预警记录。
```

更具体地说：

```text
登录注册、记录查询、文件上传：
Vue -> Spring Boot -> MySQL/文件夹 -> Vue

图片识别：
Vue -> Spring Boot -> Flask -> Spring Boot 保存文件和记录 -> Vue

视频识别：
Vue -> Flask 视频流 -> Vue
Flask -> Spring Boot 保存结果视频和记录
Flask -> Vue WebSocket 推送标签、预警和进度

摄像头识别：
Vue -> Flask 摄像头流 -> Vue
Flask -> Spring Boot 保存结果视频和记录
Flask -> Vue WebSocket 推送标签、预警和进度
```

## 19. 给 Python/Java 基础同学的学习建议

如果你要真正讲明白这个项目，可以按这个顺序学：

1. 先理解 HTTP：GET、POST、JSON、URL 参数、文件上传。
2. 再理解 Spring Boot Controller：`@RestController`、`@RequestMapping`、`@GetMapping`、`@PostMapping`。
3. 再理解数据库实体和 Mapper：Entity 对应表，Mapper 做增删改查。
4. 再理解 Vue 单文件组件：`template` 是页面，`script` 是逻辑，`style` 是样式。
5. 再理解 axios：前端怎么调用后端接口。
6. 最后理解 Flask 视频流和 Socket.IO：为什么实时视频和实时标签要分两条通道。

这个项目的主线其实很清晰：页面收集参数，后端调用模型，模型产出结果，后端保存记录，页面展示结果。抓住这条线，再看文件就不会散。
