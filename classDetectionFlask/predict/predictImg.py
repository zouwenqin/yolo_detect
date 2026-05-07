
from ultralytics import YOLO
import json
import time



class ImagePredictor:
    def __init__(self, weights_path, img_path, kind, save_path="./runs/result.jpg", conf=0.5):
        """
        初始化ImagePredictor类
        :param weights_path: 权重文件路径
        :param img_path: 输入图像路径
        :param save_path: 结果保存路径
        :param conf: 置信度阈值
        """
        self.model = YOLO(weights_path)
        self.conf = conf
        self.img_path = img_path
        self.save_path = save_path
        self.kind = {
            'class':[ '举手', '阅读', '写作','玩手机', '低头', '靠桌子'],
        }
        self.labels = self.kind[kind]

    def predict(self):
        """
        预测图像并保存结果
        """
        start_time = time.time()  # 开始计时

        # 执行预测
        results = self.model(source=self.img_path, conf=self.conf, half=True, save_conf=True)

        end_time = time.time()  # 结束计时
        elapsed_time = end_time - start_time  # 计算用时

        all_results = {
            'labels': [],  # 存储所有标签
            'confidences': [],  # 存储所有置信度
            'allTime': f"{elapsed_time:.3f}秒"
        }

        try:
            # 检查是否有检测结果
            if len(results) == 0:
                print("未检测到目标，请换一张图片。")
                all_results = {
                    'labels': '预测失败',  # 存储所有标签
                    'confidences': "0.00%",  # 存储所有置信度
                    'allTime': f"{elapsed_time:.3f}秒"
                }
                return all_results

            for result in results:
                # 提取置信度和标签
                confidences = result.boxes.conf if hasattr(result.boxes, 'conf') else []
                labels = result.boxes.cls if hasattr(result.boxes, 'cls') else []

                # 检查 confidences 和 labels 是否为空
                if confidences.numel() == 0 or labels.numel() == 0:
                    print("未检测到目标，请换一张图片。")
                    all_results = {
                        'labels': '预测失败',  # 存储所有标签
                        'confidences': "0.00%",  # 存储所有置信度
                        'allTime': f"{elapsed_time:.3f}秒"
                    }
                    return all_results

                # 获取标签名称和对应置信度
                label_names = [self.labels[int(cls)] for cls in labels]
                predictions = list(zip(label_names, confidences))

                # 将每个结果保存到字典中
                for label, conf in predictions:
                    all_results['labels'].append(label)
                    all_results['confidences'].append(f"{conf * 100:.2f}%")

                result.save(filename=self.save_path)  # 保存结果

            return all_results  # 返回包含标签和置信度的字典
        except Exception as e:
            # 如果预测过程中发生异常，打印错误信息并返回空结果
            print(f"预测过程中发生异常: {e}")
            all_results = {
                'labels': '预测失败',  # 存储所有标签
                'confidences': "0.00%",  # 存储所有置信度
                'allTime': f"{elapsed_time:.3f}秒"
            }
            return all_results


if __name__ == '__main__':
    # 初始化预测器
    predictor = ImagePredictor("../weights/rice_best.pt", "E:/yolo_detection/new/yolo_cropDisease_detection_web/yolo_cropDisease_detection_flask/dataset/rice_dataset/images/test/blast_orig_001.jpg", 'rice', save_path="../runs/result.jpg", conf=0.01)

    # 执行预测
    result = predictor.predict()
    labels_str = json.dumps(result['labels'])  # 将列表转换为 JSON 格式的字符串
    confidences_str = json.dumps(result['confidences'])  # 将列表转换为 JSON 格式的字符串
    print(labels_str)
    print(confidences_str)
    print(result['allTime'])