import csv
import json
import os
import shutil
import subprocess
import sys
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import cv2
import requests


PROTOCOL_VERSION = "classroom-demo-v1"
RISK_WEIGHT = {"normal": 0, "low": 1, "medium": 2, "high": 3}

RAW_LABEL_MAP = {
    "normal": ("focus", "专注/正常"),
    "head_down": ("head_down", "低头"),
    "lie_down": ("lie_desk", "趴桌"),
    "lie_desk": ("lie_desk", "趴桌"),
    "other_action": ("other_action", "其他行为"),
}

MODEL_EXTENSIONS = {".pt", ".pth"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

BEHAVIOR_NAMES = {
    "focus": "专注/正常",
    "head_down": "低头",
    "lie_desk": "趴桌",
    "other_action": "其他行为",
}

BEHAVIOR_TONES = {
    "focus": "normal",
    "head_down": "medium",
    "lie_desk": "high",
    "other_action": "low",
}


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_duration(seconds):
    safe = max(0, int(round(seconds or 0)))
    if safe >= 60:
        return f"{safe // 60}分{safe % 60:02d}秒"
    return f"{safe}秒"


def normalize_pipeline_label(label):
    raw = str(label or "").strip()
    behavior_type, behavior_name = RAW_LABEL_MAP.get(raw, (raw, raw or "未知行为"))
    return behavior_type, behavior_name


class ClassPipelineTaskManager:
    """Task adapter for the class/ offline video behavior pipeline."""

    def __init__(self, socketio, project_root=None):
        self.socketio = socketio
        self.project_root = Path(project_root or Path(__file__).resolve().parents[1])
        self.class_root = Path(os.environ.get("CLASS_ROOT", self.project_root / "class")).resolve()
        self.runtime_dir = self.class_root / "runtime"
        self.pipeline_script = self.class_root / "scripts" / "run_single_pipeline.py"
        self.visualize_script = self.class_root / "scripts" / "run_single_visualize.py"
        self.tasks = {}

    def list_models(self):
        model_dirs = [
            self.class_root / "models",
            self.project_root / "classDetectionFlask" / "weights",
            Path.cwd() / "weights",
        ]
        model_items = []
        seen = set()
        for model_dir in model_dirs:
            if not model_dir.exists():
                continue
            for path in sorted(model_dir.iterdir(), key=lambda item: item.name.lower()):
                if not path.is_file() or path.suffix.lower() not in MODEL_EXTENSIONS or path.name in seen:
                    continue
                seen.add(path.name)
                item = {
                    "value": path.name,
                    "label": path.name,
                    "path": str(path),
                    "size": path.stat().st_size,
                }
                model_items.append(item)

        return {
            "modelDir": str(self.class_root / "models"),
            "weight_items": model_items,
            "yoloModelItems": [item for item in model_items if item["value"].lower().endswith(".pt")],
            "lstmModelItems": [item for item in model_items if item["value"].lower().endswith(".pth")],
        }

    def list_preprocessed(self):
        datasets = []
        seen = set()

        sample_info = self._describe_preprocessed_dir(self.class_root / "sample", value="sample", label="sample")
        if sample_info:
            datasets.append(sample_info)
            seen.add(sample_info["value"])

        input_root = self.class_root / "input"
        output_root = self.class_root / "output"
        for input_dir in sorted(input_root.glob("*"), key=lambda item: item.name.lower()) if input_root.exists() else []:
            if not input_dir.is_dir():
                continue
            output_dir = output_root / input_dir.name
            info = self._describe_preprocessed_dir(
                output_dir,
                input_video=self._first_video(input_dir),
                value=input_dir.name,
                label=input_dir.name,
            )
            if info:
                datasets.append(info)
                seen.add(info["value"])

        runtime_folders = sorted(self.runtime_dir.glob("*"), key=lambda item: item.name.lower()) if self.runtime_dir.exists() else []
        for folder in runtime_folders:
            if not folder.is_dir():
                continue
            info = self._describe_preprocessed_dir(folder)
            if info and info["value"] not in seen:
                datasets.append(info)
                seen.add(info["value"])
        return datasets

    def _describe_preprocessed_dir(self, folder, input_video=None, value=None, label=None):
        if not folder or not folder.is_dir():
            return None
        input_video = input_video or self._first_existing(folder / "input_h264.mp4", folder / "input.mp4") or self._first_video(folder)
        track_csv = self._first_existing(folder / "track_boxes.csv", folder / "track_boxes" / "track_boxes.csv")
        keypoints_csv = self._first_existing(folder / "keypoints.csv", folder / "keypoints" / "keypoints.csv")
        pred_csv = folder / "predictions.csv"
        result_video = self._first_existing(
            folder / "result_h264.mp4",
            folder / "videos" / "result_h264.mp4",
            folder / "result.mp4",
            folder / "videos" / "result.mp4",
        )
        if not track_csv or not pred_csv.exists():
            return None
        dataset_value = value or folder.name
        url_value = quote(dataset_value, safe="")
        return {
            "value": dataset_value,
            "label": label or ("sample" if folder == self.class_root / "sample" else folder.name),
            "path": str(folder),
            "sourceName": input_video.name if input_video else f"{dataset_value}.mp4",
            "inputPath": str(input_video) if input_video else "",
            "resultPath": str(result_video) if result_video else "",
            "inputVideoUrl": f"/flask/class-preprocessed/{url_value}/input-video" if input_video else "",
            "resultVideoUrl": f"/flask/class-preprocessed/{url_value}/result-video" if result_video else "",
            "hasInputVideo": bool(input_video and input_video.exists()),
            "hasTrackBoxes": bool(track_csv),
            "hasKeypoints": bool(keypoints_csv),
            "hasPredictions": pred_csv.exists(),
            "hasResultVideo": bool(result_video),
        }

    def start_task(self, payload):
        task_id = payload.get("taskId") or "task_" + datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
        source_name = payload.get("sourceName") or os.path.basename(str(payload.get("inputVideo") or "video.mp4"))
        task_dir = self.runtime_dir / task_id
        input_video = task_dir / "input.mp4"
        task = {
            "taskId": task_id,
            "sessionId": f"CLASS-{uuid.uuid4().hex[:8].upper()}",
            "status": "pending",
            "taskStatus": "pending",
            "step": "created",
            "progress": 0,
            "sourceType": "video",
            "sourceName": source_name,
            "inputVideo": payload.get("inputVideo"),
            "username": payload.get("username") or "demo",
            "kind": payload.get("kind") or "class-pipeline",
            "startTime": payload.get("startTime") or now_text(),
            "confThr": float(payload.get("confThr") or payload.get("conf") or 0.45),
            "frameStride": int(payload.get("frameStride") or 5),
            "yoloDevice": str(payload.get("yoloDevice") or "cpu"),
            "rtmposeDevice": str(payload.get("rtmposeDevice") or "cpu"),
            "lstmDevice": str(payload.get("lstmDevice") or "cpu"),
            "yoloModel": payload.get("yoloModel") or payload.get("weight") or "yolo_best.pt",
            "lstmModel": payload.get("lstmModel") or "best_lstm.pth",
            "usePrecomputed": bool(payload.get("usePrecomputed", True)),
            "reuseResultVideo": bool(payload.get("reuseResultVideo", True)),
            "preprocessedDataset": payload.get("preprocessedDataset") or "sample",
            "taskDir": str(task_dir),
            "inputPath": str(input_video),
            "inputPlayablePath": str(task_dir / "videos" / "input_h264.mp4"),
            "inputVideoUrl": f"/flask/videoTasks/{task_id}/input-video",
            "resultVideoPath": str(task_dir / "videos" / "result_h264.mp4"),
            "resultVideoUrl": "",
            "videoInfo": {},
            "error": "",
            "behaviorStats": [],
            "events": [],
            "trackSummary": [],
            "predictionWindows": [],
        }
        self.tasks[task_id] = task
        self.socketio.start_background_task(self._run_task, task_id)
        return task

    def get_task(self, task_id):
        return self.tasks.get(task_id)

    def get_result_video_path(self, task_id):
        task = self.tasks.get(task_id)
        if not task:
            return None
        path = Path(task.get("resultVideoPath") or "")
        return path if path.exists() else None

    def get_input_video_path(self, task_id=None):
        if task_id:
            task = self.tasks.get(task_id)
            if task:
                path = Path(task.get("inputPlayablePath") or "")
                if path.exists():
                    return path
                path = Path(task.get("inputPath") or "")
                if path.exists():
                    return path
        sample_source = self.class_root / "sample" / "input.mp4"
        sample_path = self.class_root / "sample" / "input_h264.mp4"
        if sample_source.exists():
            try:
                self._ensure_browser_video(sample_source, sample_path)
            except Exception:
                return sample_source
        return sample_path if sample_path.exists() else None

    def get_preprocessed_input_video_path(self, dataset):
        source = self._resolve_preprocessed_input_video(dataset)
        if not source:
            return None
        target = source.with_name(f"{source.stem}_h264{source.suffix}") if source.suffix.lower() == ".mp4" else source.with_suffix(".mp4")
        try:
            return self._ensure_browser_video(source, target)
        except Exception:
            return source

    def get_preprocessed_result_video_path(self, dataset):
        dataset_dir = self._resolve_preprocessed_dir(dataset)
        source = self._first_existing(
            dataset_dir / "result_h264.mp4",
            dataset_dir / "videos" / "result_h264.mp4",
            dataset_dir / "result.mp4",
            dataset_dir / "videos" / "result.mp4",
        )
        if not source:
            return None
        target = dataset_dir / "result_demo_h264.mp4"
        try:
            return self._ensure_browser_video(source, target, force_encode=True, max_width=960, crf=27, fps=24)
        except Exception:
            return source

    def stats(self, task_id):
        task = self.tasks.get(task_id) or {}
        return task.get("behaviorStats") or []

    def predictions(self, task_id):
        task = self.tasks.get(task_id) or {}
        return task.get("predictionWindows") or []

    def track_summary(self, task_id):
        task = self.tasks.get(task_id) or {}
        return task.get("trackSummary") or []

    def _run_task(self, task_id):
        task = self.tasks[task_id]
        try:
            self._update(task, "running", "download", 5, "正在下载视频素材")
            self._prepare_input_video(task)

            if task.get("usePrecomputed"):
                self._update(task, "running", "precomputed", 15, "正在读取预处理 CSV 素材包")
                self._run_precomputed_pipeline(task)
            else:
                self._update(task, "running", "pipeline", 15, "正在运行姿态行为识别流水线")
                self._run_pipeline(task)

            self._update(task, "running", "parse", 90, "正在解析行为识别结果")
            self._load_results(task)

            self._update(task, "running", "upload", 95, "正在准备浏览器播放地址")
            local_result_url = f"/flask/videoTasks/{task['taskId']}/result-video"
            try:
                task["uploadedResultVideoUrl"] = self._upload_result_video(task)
            except requests.RequestException as exc:
                task["resultUploadError"] = str(exc)
            task["resultVideoUrl"] = local_result_url
            self._save_video_record(task)
            self._save_warning_records(task)

            self._update(task, "done", "done", 100, "检测完成", completed=True)
        except Exception as exc:
            task["error"] = str(exc)
            self._update(task, "failed", "failed", task.get("progress") or 0, str(exc))

    def _update(self, task, status, step, progress, message, completed=False):
        task["status"] = status
        task["taskStatus"] = status
        task["step"] = step
        task["progress"] = int(progress)
        task["message"] = message
        task["updatedAt"] = now_text()
        payload = self._payload(task, completed=completed)
        self.socketio.emit("message", payload)
        self.socketio.emit("progress", {"data": task["progress"], "taskId": task["taskId"], "step": step})

    def _payload(self, task, completed=False):
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "sessionId": task["sessionId"],
            "taskId": task["taskId"],
            "taskStatus": task["taskStatus"],
            "step": task["step"],
            "message": task.get("message", ""),
            "sourceType": "video",
            "sourceName": task["sourceName"],
            "inputVideoUrl": task.get("inputVideoUrl", ""),
            "videoInfo": task.get("videoInfo", {}),
            "timestamp": now_text(),
            "progress": task["progress"],
            "completed": completed,
            "resultVideoUrl": task.get("resultVideoUrl", ""),
            "behaviorStats": task.get("behaviorStats", []),
            "trackSummary": task.get("trackSummary", []),
            "predictionWindows": task.get("predictionWindows", []),
            "warningState": self._warning_state(task),
            "events": task.get("events", []),
        }

    def _warning_state(self, task):
        events = task.get("events") or []
        top_event = None
        if events:
            top_event = sorted(events, key=lambda item: RISK_WEIGHT.get(item.get("riskLevel"), 0), reverse=True)[0]
        return {
            "riskLevel": top_event.get("riskLevel") if top_event else "normal",
            "reason": top_event.get("reason") if top_event else "",
            "durations": {
                item["behaviorType"]: item["durationSeconds"]
                for item in task.get("behaviorStats", [])
            },
            "consecutiveDurations": {},
            "warning": top_event,
        }

    def _prepare_input_video(self, task):
        input_url = task.get("inputVideo")
        task_dir = Path(task["taskDir"])
        task_dir.mkdir(parents=True, exist_ok=True)
        input_path = Path(task["inputPath"])

        if task.get("usePrecomputed"):
            source_path = self._resolve_preprocessed_input_video(task.get("preprocessedDataset"))
            if source_path:
                shutil.copyfile(source_path, input_path)
                return

        if not input_url or str(input_url) in {"class_sample", "sample", "demo_sample"}:
            source_path = self.class_root / "sample" / "input.mp4"
            if not source_path.exists():
                raise FileNotFoundError(f"sample video not found: {source_path}")
            shutil.copyfile(source_path, input_path)
            return

        if str(input_url).startswith(("http://", "https://")):
            with requests.get(input_url, stream=True, timeout=60) as response:
                response.raise_for_status()
                with open(input_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            file.write(chunk)
        else:
            source_path = Path(input_url)
            if not source_path.exists():
                raise FileNotFoundError(f"video file not found: {input_url}")
            shutil.copyfile(source_path, input_path)

    def _run_precomputed_pipeline(self, task):
        dataset_dir = self._resolve_preprocessed_dir(task.get("preprocessedDataset"))
        task["preprocessedDir"] = str(dataset_dir)
        task_dir = Path(task["taskDir"])
        videos_dir = task_dir / "videos"
        keypoints_dir = task_dir / "keypoints"
        track_dir = task_dir / "track_boxes"
        videos_dir.mkdir(parents=True, exist_ok=True)
        keypoints_dir.mkdir(parents=True, exist_ok=True)
        track_dir.mkdir(parents=True, exist_ok=True)

        track_csv = self._first_existing(dataset_dir / "track_boxes.csv", dataset_dir / "track_boxes" / "track_boxes.csv")
        keypoints_csv = self._first_existing(dataset_dir / "keypoints.csv", dataset_dir / "keypoints" / "keypoints.csv")
        pred_csv = dataset_dir / "predictions.csv"
        if not track_csv or not pred_csv.exists():
            raise FileNotFoundError(f"precomputed csv not found in: {dataset_dir}")

        shutil.copyfile(track_csv, track_dir / "track_boxes.csv")
        if keypoints_csv:
            shutil.copyfile(keypoints_csv, keypoints_dir / "keypoints.csv")
        shutil.copyfile(pred_csv, task_dir / "predictions.csv")
        self._ensure_browser_video(Path(task["inputPath"]), Path(task["inputPlayablePath"]))
        task["videoInfo"] = self._read_video_info(task["inputPlayablePath"])
        self._update(task, "running", "csv", 35, "预处理 CSV 已加载，正在准备带标注视频")

        result_video = Path(task["resultVideoPath"])
        cached_video = self._first_existing(
            dataset_dir / "result_h264.mp4",
            dataset_dir / "videos" / "result_h264.mp4",
            dataset_dir / "result.mp4",
            dataset_dir / "videos" / "result.mp4",
        )
        if task.get("reuseResultVideo") and cached_video:
            self._ensure_browser_video(cached_video, result_video)
            self._update(task, "running", "visualize", 85, "已复用预处理标注视频")
            return

        self._render_result_from_csv(task)

    def _render_result_from_csv(self, task):
        if not self.visualize_script.exists():
            raise FileNotFoundError(f"visualize script not found: {self.visualize_script}")
        task_dir = Path(task["taskDir"])
        result_mp4 = task_dir / "videos" / "result.mp4"
        result_h264 = Path(task["resultVideoPath"])
        cmd = [
            sys.executable,
            str(self.visualize_script),
            "--video",
            task["inputPath"],
            "--track_csv",
            str(task_dir / "track_boxes" / "track_boxes.csv"),
            "--pred_csv",
            str(task_dir / "predictions.csv"),
            "--output_video",
            str(result_mp4),
            "--conf_thr",
            str(task["confThr"]),
        ]
        self._update(task, "running", "visualize", 55, "正在用 CSV 给视频叠加行为标签")
        completed = subprocess.run(
            cmd,
            cwd=str(self.project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        task["visualizeLog"] = (completed.stdout or "")[-6000:]
        if completed.returncode != 0:
            raise RuntimeError(f"csv visualize failed, returncode={completed.returncode}\n{task['visualizeLog']}")

        self._update(task, "running", "encode", 80, "正在转码结果视频以便浏览器播放")
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(result_mp4),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "27",
            "-vf",
            "scale=960:-2,fps=24",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            str(result_h264),
        ]
        encoded = subprocess.run(
            ffmpeg_cmd,
            cwd=str(self.project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        task["ffmpegLog"] = (encoded.stdout or "")[-6000:]
        if encoded.returncode != 0:
            shutil.copyfile(result_mp4, result_h264)
            task["ffmpegError"] = task["ffmpegLog"]

    def _resolve_preprocessed_dir(self, dataset):
        name = Path(str(dataset or "sample")).name
        candidates = [
            self.class_root / "sample" if name in {"sample", "class_sample", "demo_sample"} else None,
            self.class_root / "output" / name,
            self.runtime_dir / name,
            self.class_root / name,
        ]
        for candidate in candidates:
            if candidate and candidate.exists() and candidate.is_dir():
                return candidate.resolve()
        raise FileNotFoundError(f"preprocessed dataset not found: {dataset}")

    def _resolve_preprocessed_input_video(self, dataset):
        name = Path(str(dataset or "sample")).name
        candidates = []
        if name in {"sample", "class_sample", "demo_sample"}:
            candidates.extend([
                self.class_root / "sample" / "input_h264.mp4",
                self.class_root / "sample" / "input.mp4",
            ])
        try:
            dataset_dir = self._resolve_preprocessed_dir(dataset)
        except FileNotFoundError:
            dataset_dir = None
        candidates.extend([
            self.class_root / "input" / name / "input_h264.mp4",
            self.class_root / "input" / name / "input.mp4",
            self._first_video(self.class_root / "input" / name),
            dataset_dir / "input_h264.mp4" if dataset_dir else None,
            dataset_dir / "input.mp4" if dataset_dir else None,
        ])
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return Path(candidate).resolve()
        return None

    def _first_video(self, folder):
        folder = Path(folder)
        if not folder.exists() or not folder.is_dir():
            return None
        for path in sorted(folder.iterdir(), key=lambda item: item.name.lower()):
            if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
                return path
        return None

    def _first_existing(self, *paths):
        for path in paths:
            if path and Path(path).exists():
                return Path(path)
        return None

    def _ensure_browser_video(self, source_path, target_path, force_encode=False, max_width=None, crf=26, fps=None):
        source = Path(source_path)
        target = Path(target_path)
        if not source.exists():
            raise FileNotFoundError(f"video not found: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.stat().st_mtime >= source.stat().st_mtime and target.stat().st_size > 0:
            return target
        if not force_encode and self._is_browser_video(source) and source.resolve() != target.resolve():
            shutil.copyfile(source, target)
            return target
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            str(crf),
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
        ]
        filters = []
        if max_width:
            try:
                cap = cv2.VideoCapture(str(source))
                source_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                cap.release()
                if source_width > int(max_width):
                    filters.append(f"scale={int(max_width)}:-2")
            except Exception:
                filters.append(f"scale={int(max_width)}:-2")
        if fps:
            filters.append(f"fps={int(fps)}")
        if filters:
            cmd.extend(["-vf", ",".join(filters)])
        cmd.append(str(target))
        completed = subprocess.run(
            cmd,
            cwd=str(self.project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            raise RuntimeError(f"ffmpeg h264 transcode failed for {source}\n{(completed.stdout or '')[-3000:]}")
        return target

    def _is_browser_video(self, video_path):
        try:
            completed = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=codec_name",
                    "-of",
                    "default=nokey=1:noprint_wrappers=1",
                    str(video_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
            return completed.stdout.strip().lower() in {"h264", "avc1"}
        except Exception:
            return False

    def _run_pipeline(self, task):
        if not self.pipeline_script.exists():
            raise FileNotFoundError(f"pipeline script not found: {self.pipeline_script}")
        cmd = [
            sys.executable,
            str(self.pipeline_script),
            "--video",
            task["inputPath"],
            "--runtime_dir",
            str(self.runtime_dir),
            "--task_id",
            task["taskId"],
            "--yolo_device",
            task["yoloDevice"],
            "--rtmpose_device",
            task["rtmposeDevice"],
            "--lstm_device",
            task["lstmDevice"],
            "--frame_stride",
            str(task["frameStride"]),
            "--conf_thr",
            str(task["confThr"]),
            "--yolo_model",
            str(self._resolve_model(task["yoloModel"], ".pt")),
            "--lstm_model",
            str(self._resolve_model(task["lstmModel"], ".pth")),
        ]
        progress_marks = {
            "run_single_track.py": ("track", 25, "YOLOv8 + ByteTrack ç›®æ ‡è·Ÿè¸ªä¸­"),
            "run_single_rtmpose.py": ("pose", 45, "RTMPose å§¿æ€å…³é”®ç‚¹æå–ä¸­"),
            "run_single_predict.py": ("predict", 70, "LSTM è¡Œä¸ºåˆ†ç±»ä¸­"),
            "run_single_visualize.py": ("visualize", 85, "æ­£åœ¨ç”Ÿæˆç»“æžœè§†é¢‘"),
            "ffmpeg": ("encode", 88, "æ­£åœ¨è½¬ç  H.264 ç»“æžœè§†é¢‘"),
        }
        emitted_steps = set()
        process = subprocess.Popen(
            cmd,
            cwd=str(self.project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        log_lines = []
        assert process.stdout is not None
        for line in process.stdout:
            log_lines.append(line)
            joined = "".join(log_lines[-20:]).lower()
            for marker, (step, progress, message) in progress_marks.items():
                if marker.lower() in joined and step not in emitted_steps:
                    emitted_steps.add(step)
                    self._update(task, "running", step, progress, message)
        returncode = process.wait()
        task["pipelineLog"] = "".join(log_lines)[-6000:]
        if returncode != 0:
            raise RuntimeError(f"class pipeline failed, returncode={returncode}\n{task['pipelineLog']}")

    def _load_results(self, task):
        task_dir = Path(task["taskDir"])
        pred_csv = task_dir / "predictions.csv"
        if not pred_csv.exists():
            raise FileNotFoundError(f"predictions.csv not found: {pred_csv}")
        result_video = Path(task["resultVideoPath"])
        if not result_video.exists():
            raise FileNotFoundError(f"result_h264.mp4 not found: {result_video}")

        fps = self._read_fps(task["inputPath"])
        if not task.get("videoInfo"):
            task["videoInfo"] = self._read_video_info(task["inputPath"])
        windows = self._read_prediction_windows(pred_csv, fps, task.get("confThr"))
        task["predictionWindows"] = windows
        task["behaviorStats"] = self._build_behavior_stats(windows)
        task["trackSummary"] = self._build_track_summary(windows)
        task["events"] = self._build_events(task, windows)

    def _resolve_model(self, model_name, expected_suffix):
        model_path = Path(str(model_name or "")).name
        if not model_path.lower().endswith(expected_suffix):
            raise ValueError(f"invalid model type: {model_name}")
        for model_dir in [self.class_root / "models", self.project_root / "classDetectionFlask" / "weights", Path.cwd() / "weights"]:
            resolved = (model_dir / model_path).resolve()
            if resolved.exists():
                return resolved
        raise FileNotFoundError(f"model not found: {model_name}")

    def _read_fps(self, video_path):
        cap = cv2.VideoCapture(video_path)
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            return fps if fps and fps > 0 else 25
        finally:
            cap.release()

    def _read_video_info(self, video_path):
        cap = cv2.VideoCapture(str(video_path))
        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 0
            frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            duration_seconds = frames / fps if fps > 0 and frames > 0 else 0
            return {
                "resolution": f"{width}×{height}" if width and height else "",
                "duration": self._format_clock(duration_seconds),
                "durationSeconds": round(duration_seconds, 2),
                "fps": f"{round(fps, 2):g}fps" if fps > 0 else "",
                "fpsValue": round(fps, 3) if fps > 0 else 0,
            }
        finally:
            cap.release()

    def _format_clock(self, seconds):
        total = max(0, int(round(seconds or 0)))
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"

    def _read_prediction_windows(self, pred_csv, fps, conf_thr=None):
        windows = []
        threshold = float(conf_thr or 0)
        with open(pred_csv, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                raw_label = row.get("pred_label", "")
                behavior_type, behavior_name = normalize_pipeline_label(raw_label)
                start_frame = int(float(row.get("start_frame") or 0))
                end_frame = int(float(row.get("end_frame") or start_frame))
                confidence = float(row.get("confidence") or 0)
                if confidence < threshold:
                    continue
                windows.append({
                    "videoName": row.get("video_name", ""),
                    "trackId": int(float(row.get("track_id") or 0)),
                    "startFrame": start_frame,
                    "endFrame": end_frame,
                    "startSecond": round(start_frame / fps, 2),
                    "endSecond": round(end_frame / fps, 2),
                    "durationSeconds": round(max(0, end_frame - start_frame + 1) / fps, 2),
                    "rawLabel": raw_label,
                    "behaviorType": behavior_type,
                    "behaviorName": behavior_name,
                    "confidence": round(confidence, 4),
                    "probabilities": {
                        key.replace("prob_", ""): float(value)
                        for key, value in row.items()
                        if key.startswith("prob_") and value not in ("", None)
                    },
                })
        return windows

    def _build_behavior_stats(self, windows):
        merged = self._merged_window_stats(windows, ("trackId", "behaviorType"))
        buckets = defaultdict(lambda: {"duration": 0.0, "count": 0, "conf_sum": 0.0, "conf_count": 0})
        for (track_id, behavior_type), item in merged.items():
            bucket = buckets[behavior_type]
            bucket["duration"] += item["duration"]
            bucket["count"] += item["count"]
            bucket["conf_sum"] += item["confidence"] * item["window_count"]
            bucket["conf_count"] += item["window_count"]

        total = sum(item["duration"] for item in buckets.values()) or 1
        stats = []
        for behavior_type, item in buckets.items():
            avg_conf = item["conf_sum"] / item["conf_count"] if item["conf_count"] else 0
            stats.append({
                "behaviorType": behavior_type,
                "behaviorName": BEHAVIOR_NAMES.get(behavior_type, behavior_type),
                "durationSeconds": round(item["duration"], 1),
                "durationText": format_duration(item["duration"]),
                "count": item["count"],
                "ratio": round(item["duration"] / total * 100, 1),
                "confidence": round(avg_conf, 3),
            })
        stats.sort(key=lambda item: item["durationSeconds"], reverse=True)
        return stats

    def _build_track_summary(self, windows):
        merged = self._merged_window_stats(windows, ("trackId", "behaviorType"))
        grouped = defaultdict(list)
        for (track_id, behavior_type), item in merged.items():
            grouped[track_id].append({
                "behaviorType": behavior_type,
                "durationSeconds": item["duration"],
                "confidence": item["confidence"],
                "windowCount": item["window_count"],
            })

        summary = []
        for track_id, items in grouped.items():
            by_behavior = defaultdict(float)
            conf_sum = 0.0
            conf_count = 0
            for item in items:
                by_behavior[item["behaviorType"]] += item["durationSeconds"]
                conf_sum += item["confidence"] * item["windowCount"]
                conf_count += item["windowCount"]
            main_behavior = max(by_behavior.items(), key=lambda pair: pair[1])[0]
            summary.append({
                "trackId": track_id,
                "mainBehaviorType": main_behavior,
                "mainBehaviorName": BEHAVIOR_NAMES.get(main_behavior, main_behavior),
                "durationSeconds": round(by_behavior[main_behavior], 1),
                "durationText": format_duration(by_behavior[main_behavior]),
                "avgConfidence": round(conf_sum / conf_count, 3) if conf_count else 0,
                "windowCount": sum(item["windowCount"] for item in items),
            })
        summary.sort(key=lambda item: item["trackId"])
        return summary

    def _build_events(self, task, windows):
        grouped = self._merged_window_stats(windows, ("trackId", "behaviorType"))

        events = []
        for (track_id, behavior_type), item in grouped.items():
            seconds = item["duration"]
            risk_level = None
            if behavior_type == "lie_desk" and seconds >= 10:
                risk_level = "high"
            elif behavior_type == "head_down" and seconds >= 15:
                risk_level = "medium"
            if not risk_level:
                continue
            behavior_name = BEHAVIOR_NAMES.get(behavior_type, behavior_type)
            events.append({
                "eventId": f"{task['sessionId']}-{len(events) + 1:03d}",
                "sourceType": "video",
                "sourceName": task["sourceName"],
                "trackId": track_id,
                "behaviorType": behavior_type,
                "behaviorName": behavior_name,
                "riskLevel": risk_level,
                "riskName": {"high": "高风险", "medium": "中风险", "low": "低风险"}.get(risk_level, "正常"),
                "durationSeconds": round(seconds, 1),
                "durationText": format_duration(seconds),
                "confidence": round(item["confidence"], 3),
                "reason": f"学生目标 ID {track_id} 的{behavior_name}行为累计达到 {format_duration(seconds)}，建议教师进行非诊断式关注与沟通。",
                "triggerTime": now_text(),
                "status": "待处理",
            })
        events.sort(key=lambda item: RISK_WEIGHT.get(item["riskLevel"], 0), reverse=True)
        return events

    def _merged_window_stats(self, windows, key_fields):
        grouped = defaultdict(lambda: {"intervals": [], "conf_sum": 0.0, "window_count": 0})
        for item in windows:
            key = tuple(item.get(field) for field in key_fields)
            start = float(item.get("startSecond") or 0)
            end = float(item.get("endSecond") or start)
            if end <= start:
                end = start + float(item.get("durationSeconds") or 0)
            grouped[key]["intervals"].append((start, end))
            grouped[key]["conf_sum"] += float(item.get("confidence") or 0)
            grouped[key]["window_count"] += 1

        result = {}
        for key, item in grouped.items():
            merged = []
            for start, end in sorted(item["intervals"]):
                if not merged or start > merged[-1][1]:
                    merged.append([start, end])
                else:
                    merged[-1][1] = max(merged[-1][1], end)
            duration = sum(max(0, end - start) for start, end in merged)
            result[key] = {
                "duration": duration,
                "count": len(merged),
                "confidence": item["conf_sum"] / item["window_count"] if item["window_count"] else 0,
                "window_count": item["window_count"],
            }
        return result

    def _upload_result_video(self, task):
        result_video = Path(task["resultVideoPath"])
        upload_url = "http://localhost:9999/files/upload"
        with open(result_video, "rb") as file:
            files = {"file": (f"{task['taskId']}_result_h264.mp4", file, "video/mp4")}
            response = requests.post(upload_url, files=files, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data.get("data") or ""

    def _save_video_record(self, task):
        payload = {
            "username": task["username"],
            "weight": f"class/precomputed:{task.get('preprocessedDataset')}" if task.get("usePrecomputed") else f"class/{task.get('yoloModel')} + {task.get('lstmModel')}",
            "conf": str(task["confThr"]),
            "startTime": task["startTime"],
            "inputVideo": task.get("inputVideo") or "",
            "outVideo": task.get("uploadedResultVideoUrl") or task.get("resultVideoUrl") or "",
            "kind": task["kind"],
        }
        try:
            requests.post(
                "http://localhost:9999/videoRecords",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=15,
            )
        except requests.RequestException as exc:
            task["videoRecordError"] = str(exc)

    def _save_warning_records(self, task):
        for event in task.get("events", []):
            advice = self._request_advice(event)
            event["advice"] = advice
            payload = {
                "videoSource": task.get("inputVideo") or task["sourceName"],
                "detectionType": "video",
                "riskLevel": event.get("riskLevel"),
                "behaviorType": event.get("behaviorType"),
                "durationSeconds": event.get("durationSeconds"),
                "triggerTime": event.get("triggerTime"),
                "reason": event.get("reason"),
                "advice": advice,
                "status": event.get("status") or "待处理",
                "username": task.get("username") or "",
            }
            try:
                requests.post(
                    "http://localhost:9999/warningRecords",
                    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    headers={"Content-Type": "application/json; charset=utf-8"},
                    timeout=15,
                )
            except requests.RequestException as exc:
                task.setdefault("warningRecordErrors", []).append(str(exc))

    def _request_advice(self, event):
        payload = {
            "riskLevel": event.get("riskLevel"),
            "behaviorType": event.get("behaviorType"),
            "durationSeconds": event.get("durationSeconds"),
            "reason": event.get("reason"),
            "scene": "课堂监控视频素材分析后的行为预警事件",
        }
        try:
            response = requests.post(
                "http://localhost:9999/warningRecords/advice",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                if str(data.get("code")) == "0" and data.get("data"):
                    return data["data"]
        except Exception:
            pass
        return "建议教师结合课堂情境观察学生状态，课后以非诊断式方式进行简短沟通，了解是否存在疲劳、注意力波动或学习困难，并视情况调整座位、提问节奏或课堂互动。"
