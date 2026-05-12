from ultralytics import YOLO
import json
import os
import subprocess
import cv2
import requests
from datetime import datetime
from flask import Flask, Response, request

from predict import predictImg

from flask_socketio import SocketIO, emit
from detection_protocol import DetectionProtocolAdapter, normalize_behavior_label as protocol_normalize_behavior_label, behavior_name as protocol_behavior_name


BEHAVIOR_LABELS = {
    "raise_hand": "举手",
    "read": "阅读",
    "write": "写作",
    "phone": "玩手机",
    "head_down": "低头",
    "lie_desk": "趴桌",
    "sleep": "睡觉",
}

LABEL_ALIASES = {
    "raise_hand": {"raise_hand", "hand-raising", "hand_raising", "raise hand", "举手"},
    "read": {"read", "reading", "阅读"},
    "write": {"write", "writing", "写作"},
    "phone": {"phone", "play_phone", "playing phone", "cellphone", "mobile", "玩手机"},
    "head_down": {"head_down", "head-down", "low_head", "low-head", "bow", "lower_head", "低头"},
    "lie_desk": {"lie_desk", "lie-desk", "desk", "lean_desk", "lean-desk", "table", "sleep on desk", "靠桌子", "靠桌", "趴桌", "趴桌子"},
    "sleep": {"sleep", "sleeping", "asleep", "睡觉", "睡眠"},
}

RISK_WEIGHT = {"normal": 0, "low": 1, "medium": 2, "high": 3}


def normalize_behavior_label(label):
    raw = str(label).strip()
    key = raw.lower().replace(" ", "_")
    for behavior, aliases in LABEL_ALIASES.items():
        if raw in aliases or key in aliases:
            return behavior
    return key


def display_behavior_label(label):
    return BEHAVIOR_LABELS.get(label, label)


class BehaviorWarningTracker:
    def __init__(self, fps=20):
        self.frame_seconds = 1.0 / fps if fps and fps > 0 else 0.05
        self.watch_behaviors = ["sleep", "lie_desk", "head_down", "phone"]
        self.cumulative = {name: 0.0 for name in self.watch_behaviors}
        self.consecutive = {name: 0.0 for name in self.watch_behaviors}
        self.emitted = set()
        self.current_risk = "normal"
        self.current_reason = ""

    def update(self, labels):
        normalized = [normalize_behavior_label(label) for label in labels]
        detected = set(normalized)
        for behavior in self.watch_behaviors:
            if behavior in detected:
                self.cumulative[behavior] += self.frame_seconds
                self.consecutive[behavior] += self.frame_seconds
            else:
                self.consecutive[behavior] = 0.0

        warning = self._build_warning()
        if warning:
            self.current_risk = warning["riskLevel"]
            self.current_reason = warning["reason"]

        return {
            "labels": labels,
            "normalizedLabels": normalized,
            "displayLabels": [display_behavior_label(label) for label in normalized],
            "durations": {key: round(value, 1) for key, value in self.cumulative.items()},
            "consecutiveDurations": {key: round(value, 1) for key, value in self.consecutive.items()},
            "riskLevel": self.current_risk,
            "reason": self.current_reason,
            "warning": warning,
        }

    def _build_warning(self):
        candidates = []
        if "sleep" not in self.emitted and (self.consecutive["sleep"] >= 10 or self.cumulative["sleep"] >= 10):
            candidates.append(("sleep", "high", self.cumulative["sleep"], "疑似睡觉行为累计超过10秒"))
        if "lie_desk" not in self.emitted and (self.consecutive["lie_desk"] >= 10 or self.cumulative["lie_desk"] >= 10):
            candidates.append(("lie_desk", "high", self.cumulative["lie_desk"], "长时间趴桌/靠桌行为累计超过10秒"))
        if "head_down" not in self.emitted and (self.consecutive["head_down"] >= 15 or self.cumulative["head_down"] >= 15):
            candidates.append(("head_down", "medium", self.cumulative["head_down"], "持续低头行为累计超过15秒"))
        if "phone" not in self.emitted and self.cumulative["phone"] >= 15:
            candidates.append(("phone", "low", self.cumulative["phone"], "玩手机行为累计超过15秒"))

        if not candidates:
            return None

        candidates.sort(key=lambda item: RISK_WEIGHT[item[1]], reverse=True)
        behavior, risk_level, duration, reason = candidates[0]
        self.emitted.add(behavior)
        return {
            "riskLevel": risk_level,
            "behaviorType": behavior,
            "behaviorName": display_behavior_label(behavior),
            "durationSeconds": round(duration, 1),
            "reason": reason,
        }


# Flask 应用设置
class VideoProcessingApp:
    def __init__(self, host='0.0.0.0', port=5000):
        """初始化 Flask 应用并设置路由"""
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")  # 初始化 SocketIO
        self.host = host
        self.port = port
        self.setup_routes()
        self.data = {}  # 存储接收参数
        self.paths = {
            'download': './runs/video/download.mp4',
            'output': './runs/video/output.mp4',
            'camera_output': "./runs/video/camera_output.avi",
            'video_output': "./runs/video/camera_output.avi"
        }
        self.recording = False  # 标志位，判断是否正在录制视频

    def setup_routes(self):
        """设置所有路由"""
        self.app.add_url_rule('/file_names', 'file_names', self.file_names, methods=['GET'])
        self.app.add_url_rule('/predictImg', 'predictImg', self.predictImg, methods=['POST'])
        self.app.add_url_rule('/predictVideo', 'predictVideo', self.predictVideo)
        self.app.add_url_rule('/predictCamera', 'predictCamera', self.predictCamera)
        self.app.add_url_rule('/stopCamera', 'stopCamera', self.stopCamera, methods=['GET'])

        # 添加 WebSocket 事件
        @self.socketio.on('connect')
        def handle_connect():
            print("WebSocket connected!")
            emit('message', {'data': 'Connected to WebSocket server!'})

        @self.socketio.on('disconnect')
        def handle_disconnect():
            print("WebSocket disconnected!")

    def run(self):
        """启动 Flask 应用"""
        self.socketio.run(self.app, host=self.host, port=self.port, allow_unsafe_werkzeug=True)

    def file_names(self):
        """模型列表接口"""
        weight_items = [{'value': name, 'label': name} for name in self.get_file_names("./weights")]
        return json.dumps({'weight_items': weight_items})

    '''
    输入：接收包含用户名、模型权重名、置信度、图片路径等信息的 JSON 数据。
    处理：
    调用 predictImg.ImagePredictor 类（外部依赖）加载模型。
    执行推理，生成标注后的图片。
    输出：
    将结果图片上传至远程服务器（http://localhost:9999/files/upload）。
    返回包含图片 URL、识别标签、置信度、耗时等信息的 JSON 响应。
    '''
    def predictImg(self):
        """图片预测接口"""
        data = request.get_json()
        print(data)
        self.data.clear()
        self.data.update({
            "username": data['username'], "weight": data['weight'],
            "conf": data['conf'], "startTime": data['startTime'],
            "inputImg": data['inputImg'],
            "kind": data['kind']
        })
        print(self.data)
        predict = predictImg.ImagePredictor(weights_path=f'./weights/{self.data["weight"]}',
                                            img_path=self.data["inputImg"], save_path='./runs/result.jpg', kind=self.data["kind"],
                                            conf=float(self.data["conf"]))
        # 执行预测
        results = predict.predict()
        uploadedUrl = self.upload('./runs/result.jpg')
        if results['labels'] != '预测失败':
            self.data["status"] = 200
            self.data["message"] = "预测成功"
            self.data["outImg"] = uploadedUrl
            self.data["allTime"] = results['allTime']
            self.data["confidence"] = json.dumps(results['confidences'])
            self.data["label"] = json.dumps(results['labels'])
        else:
            self.data["status"] = 400
            self.data["message"] = "该图片无法识别，请重新上传！"
        path = self.data["inputImg"].split('/')[-1]
        if os.path.exists('./' + path):
            os.remove('./' + path)
        return json.dumps(self.data, ensure_ascii=False)


    '''下载：从提供的 URL 下载视频文件到本地 (./runs/video/download.mp4)。
    推理与推流：
    使用 OpenCV 读取视频帧。
    使用 YOLO 模型对每一帧进行预测。
    实时推送：通过 socketio.emit 将当前帧识别到的物体标签（如 "person", "car"）推送到前端。
    生成流：将处理后的帧编码为 JPEG 格式，通过 multipart/x-mixed-replace 协议返回给前端，实现网页端实时播放。
    后处理：
    视频处理完成后，使用 FFmpeg 将临时的 AVI 文件转换为 MP4 格式。
    通过 WebSocket 推送转换进度。
    将最终视频上传并保存记录。
       '''

    def predictVideo(self):
        """视频流处理接口"""
        self.data.clear()
        self.data.update({
            "username": request.args.get('username'), "weight": request.args.get('weight'),
            "conf": request.args.get('conf'), "startTime": request.args.get('startTime'),
            "inputVideo": request.args.get('inputVideo'),
            "kind": request.args.get('kind')
        })
        self.download(self.data["inputVideo"], self.paths['download'])
        cap = cv2.VideoCapture(self.paths['download'])
        if not cap.isOpened():
            raise ValueError("无法打开视频文件")
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0:
            fps = 20
        print(fps)

        # 视频写入器
        video_writer = cv2.VideoWriter(
            self.paths['video_output'],
            cv2.VideoWriter_fourcc(*'XVID'),
            fps,
            (640, 480)
        )
        model = YOLO(f'./weights/{self.data["weight"]}')
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        protocol_adapter = DetectionProtocolAdapter(
            fps=fps,
            source_type="video",
            source_name=os.path.basename(self.data.get("inputVideo") or "video")
        )

        def generate():
            try:
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        break
                    frame = cv2.resize(frame, (640, 480))
                    results = model.predict(source=frame, conf=float(self.data['conf']), show=False)
                    processed_frame = results[0].plot()
                    video_writer.write(processed_frame)
                    _, jpeg = cv2.imencode('.jpg', processed_frame)

                    # ----------- 新增：提取标签并推送 -----------
                    detections = self.build_detections(results[0])
                    labels = [item["label"] for item in detections]
                    current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                    progress = round(current_frame / total_frames * 100, 1) if total_frames else None
                    protocol_payload = protocol_adapter.update(labels, detections=detections, progress=progress)
                    warning = protocol_payload.get("warningState", {}).get("warning")
                    if warning:
                        warning = self.enrich_and_save_warning(
                            warning,
                            detection_type="video",
                            video_source=self.data.get("inputVideo")
                        )
                        protocol_payload["warningState"]["warning"] = warning
                        if protocol_payload.get("events"):
                            protocol_payload["events"][0] = warning
                    self.socketio.emit('message', protocol_payload)
                    # -----------------------------------------

                    yield b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n'
            finally:
                self.socketio.emit('message', protocol_adapter.complete())
                self.cleanup_resources(cap, video_writer)
                self.socketio.emit('message', {'data': '处理完成，正在保存！'})
                for progress in self.convert_avi_to_mp4(self.paths['video_output']):
                    self.socketio.emit('progress', {'data': progress})
                uploadedUrl = self.upload(self.paths['output'])
                self.data["outVideo"] = uploadedUrl
                self.save_data(json.dumps(self.data), 'http://localhost:9999/videoRecords')
                self.cleanup_files([self.paths['download'], self.paths['output'], self.paths['video_output']])

        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

    def predictCamera(self):
        """摄像头视频流处理接口"""
        self.data.clear()
        self.data.update({
            "username": request.args.get('username'), "weight": request.args.get('weight'),
            "kind": request.args.get('kind'),
            "conf": request.args.get('conf'), "startTime": request.args.get('startTime')
        })
        self.socketio.emit('message', {'data': '正在加载，请稍等！'})
        model = YOLO(f'./weights/{self.data["weight"]}')
        protocol_adapter = DetectionProtocolAdapter(
            fps=20,
            source_type="camera",
            source_name="camera"
        )
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        video_writer = cv2.VideoWriter(self.paths['camera_output'], cv2.VideoWriter_fourcc(*'XVID'), 20, (640, 480))
        self.recording = True

        def generate():
            try:
                while self.recording:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    results = model.predict(source=frame, imgsz=640, conf=float(self.data['conf']), show=False)
                    processed_frame = results[0].plot()
                    if self.recording and video_writer:
                        video_writer.write(processed_frame)
                    _, jpeg = cv2.imencode('.jpg', processed_frame)

                    # ----------- 新增：提取标签并推送 -----------
                    detections = self.build_detections(results[0])
                    labels = [item["label"] for item in detections]
                    protocol_payload = protocol_adapter.update(labels, detections=detections)
                    warning = protocol_payload.get("warningState", {}).get("warning")
                    if warning:
                        warning = self.enrich_and_save_warning(
                            warning,
                            detection_type="camera",
                            video_source="camera"
                        )
                        protocol_payload["warningState"]["warning"] = warning
                        if protocol_payload.get("events"):
                            protocol_payload["events"][0] = warning
                    self.socketio.emit('message', protocol_payload)
                    # -----------------------------------------

                    yield b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n'
            finally:
                self.socketio.emit('message', protocol_adapter.complete())
                self.cleanup_resources(cap, video_writer)
                self.socketio.emit('message', {'data': '处理完成，正在保存！'})
                for progress in self.convert_avi_to_mp4(self.paths['camera_output']):
                    self.socketio.emit('progress', {'data': progress})
                uploadedUrl = self.upload(self.paths['output'])
                self.data["outVideo"] = uploadedUrl
                print(self.data)
                self.save_data(json.dumps(self.data), 'http://localhost:9999/cameraRecords')
                self.cleanup_files([self.paths['download'], self.paths['output'], self.paths['camera_output']])

        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

    def stopCamera(self):
        """停止摄像头预测"""
        self.recording = False
        return json.dumps({"status": 200, "message": "预测成功", "code": 0})

    def build_detections(self, yolo_result):
        """Build standard detection items from one YOLO result."""
        detections = []
        for box in yolo_result.boxes:
            cls_id = int(box.cls[0])
            label = yolo_result.names[cls_id]
            behavior_type = protocol_normalize_behavior_label(label)
            confidence = float(box.conf[0]) if hasattr(box, "conf") and len(box.conf) else 0.0
            try:
                bbox = [round(float(value), 2) for value in box.xyxy[0].tolist()]
            except Exception:
                bbox = []
            detections.append({
                "label": label,
                "behaviorType": behavior_type,
                "behaviorName": protocol_behavior_name(behavior_type),
                "confidence": round(confidence, 4),
                "bbox": bbox,
            })
        return detections

    def enrich_and_save_warning(self, warning, detection_type, video_source):
        """生成教师建议并保存预警记录。"""
        advice = self.request_warning_advice(warning)
        warning_record = {
            "videoSource": video_source or "",
            "detectionType": detection_type,
            "riskLevel": warning.get("riskLevel"),
            "behaviorType": warning.get("behaviorType"),
            "durationSeconds": warning.get("durationSeconds"),
            "triggerTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "reason": warning.get("reason"),
            "advice": advice,
            "status": "未处理",
            "username": self.data.get("username", ""),
        }
        try:
            requests.post(
                "http://localhost:9999/warningRecords",
                data=json.dumps(warning_record, ensure_ascii=False),
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
        except requests.RequestException as e:
            print(f"保存预警记录失败: {str(e)}")
        warning.update(warning_record)
        return warning

    def request_warning_advice(self, warning):
        payload = {
            "riskLevel": warning.get("riskLevel"),
            "behaviorType": warning.get("behaviorType"),
            "durationSeconds": warning.get("durationSeconds"),
            "reason": warning.get("reason"),
            "scene": "课堂实时行为检测"
        }
        try:
            response = requests.post(
                "http://localhost:9999/warningRecords/advice",
                data=json.dumps(payload, ensure_ascii=False),
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                if str(result.get("code")) == "0" and result.get("data"):
                    return result.get("data")
        except Exception as e:
            print(f"生成干预建议失败: {str(e)}")
        return self.fallback_warning_advice(warning)

    def fallback_warning_advice(self, warning):
        behavior_name = warning.get("behaviorName") or display_behavior_label(warning.get("behaviorType"))
        return f"当前识别到{behavior_name}异常信号。建议教师先进行非公开观察，课后以关怀方式简短沟通，了解学生睡眠、身体状态和学习压力；若该行为反复出现，应联系班主任或心理老师按学校流程跟进。"

    def save_data(self, data, path):
        """将结果数据上传到服务器"""
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(path, data=data, headers=headers)
            print("记录上传成功！" if response.status_code == 200 else f"记录上传失败，状态码: {response.status_code}")
        except requests.RequestException as e:
            print(f"上传记录时发生错误: {str(e)}")

    def convert_avi_to_mp4(self, temp_output):
        """使用 FFmpeg 将 AVI 格式转换为 MP4 格式，并显示转换进度。"""
        ffmpeg_command = f"ffmpeg -i {temp_output} -vcodec libx264 {self.paths['output']} -y"
        process = subprocess.Popen(ffmpeg_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True)
        total_duration = self.get_video_duration(temp_output)

        for line in process.stderr:
            if "time=" in line:
                try:
                    time_str = line.split("time=")[1].split(" ")[0]
                    h, m, s = map(float, time_str.split(":"))
                    processed_time = h * 3600 + m * 60 + s
                    if total_duration > 0:
                        progress = (processed_time / total_duration) * 100
                        yield progress
                except Exception as e:
                    print(f"解析进度时发生错误: {e}")

        process.wait()
        yield 100

    def get_video_duration(self, path):
        """获取视频总时长（秒）"""
        try:
            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                return 0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            return total_frames / fps if fps > 0 else 0
        except Exception:
            return 0

    def get_file_names(self, directory):
        """获取指定文件夹中的所有文件名"""
        try:
            return [file for file in os.listdir(directory) if os.path.isfile(os.path.join(directory, file))]
        except Exception as e:
            print(f"发生错误: {e}")
            return []

    def upload(self, out_path):
        """上传处理后的图片或视频文件到远程服务器"""
        upload_url = "http://localhost:9999/files/upload"
        try:
            with open(out_path, 'rb') as file:
                files = {'file': (os.path.basename(out_path), file)}
                response = requests.post(upload_url, files=files)
                if response.status_code == 200:
                    print("文件上传成功！")
                    return response.json()['data']
                else:
                    print("文件上传失败！")
        except Exception as e:
            print(f"上传文件时发生错误: {str(e)}")

    def download(self, url, save_path):
        """下载文件并保存到指定路径"""
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        try:
            with requests.get(url, stream=True) as response:
                response.raise_for_status()
                with open(save_path, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file.write(chunk)
            print(f"文件已成功下载并保存到 {save_path}")
        except requests.RequestException as e:
            print(f"下载失败: {e}")

    def cleanup_files(self, file_paths):
        """清理文件"""
        for path in file_paths:
            if os.path.exists(path):
                os.remove(path)

    def cleanup_resources(self, cap, video_writer):
        """释放资源"""
        if cap.isOpened():
            cap.release()
        if video_writer is not None:
            video_writer.release()
        cv2.destroyAllWindows()


# 启动应用
if __name__ == '__main__':
    video_app = VideoProcessingApp()
    video_app.run()
