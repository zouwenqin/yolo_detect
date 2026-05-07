import tkinter as tk
from tkinter import filedialog
from ultralytics import YOLO
import cv2


def select_and_detect():
    # --- 1. 文件选择 ---
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    file_path = filedialog.askopenfilename(
        title="请选择一张课堂图片",
        filetypes=[("图片文件", "*.jpg *.jpeg *.png *.bmp")]
    )

    if not file_path:
        print("❌ 未选择图片，程序退出。")
        return

    print(f"✅ 已选择图片: {file_path}")

    # --- 2. 加载你下载的课堂行为模型 ---
    # 【关键修改】将 'yolov8n.pt' 替换为你下载的 .pt 文件路径
    # 确保你的 .pt 文件和这个脚本在同一个文件夹下，或者填写完整路径
    model_path = './weights/class.pt'  # 这里假设你下载的文件名为 best.pt
    print(f"⏳ 正在加载课堂行为模型: {model_path}...")
    model = YOLO(model_path)

    # --- 3. 执行检测 ---
    print("🔍 正在分析图片中的行为...")
    results = model(file_path)

    # --- 4. 处理结果并显示 ---
    result = results[0]

    # 绘制检测框和类别标签
    annotated_image = result.plot()

    # 显示图片
    cv2.imshow('课堂行为检测结果', annotated_image)

    # 打印控制台信息
    print("\n--- 📊 行为检测结果 ---")
    for box in result.boxes:
        cls_id = int(box.cls[0])
        cls_name = result.names[cls_id]  # 这里会显示 'hand-raising', 'sleeping' 等
        conf = float(box.conf[0])
        print(f"- 检测到: {cls_name} (置信度: {conf:.2f})")

    print("\n按任意键关闭图片窗口...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    select_and_detect()