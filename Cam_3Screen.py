import cv2
import numpy as np

# 核心配置参数定义
CAMERA_INDEX = 0       # 摄像头索引（默认0为内置摄像头）
CAM_WIDTH = 640        # 摄像头采集宽度
CAM_HEIGHT = 480       # 摄像头采集高度
CANNY_LOW = 50         # Canny边缘检测低阈值
CANNY_HIGH = 150       # Canny边缘检测高阈值

def main():
    # 初始化摄像头对象
    cap = cv2.VideoCapture(CAMERA_INDEX)

    # 设置摄像头采集分辨率
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

    # 主循环：实时采集和处理帧
    while True:
        # 读取摄像头帧
        ret, frame = cap.read()
        # 检查帧是否读取成功
        if not ret or frame is None:
            print("读取帧失败！")
            break

        # 步骤1：彩色图像转灰度图像
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 步骤2：灰度图像二值化（针对白色赛道场景）  THRESH_OTSU：自动计算最佳阈值，THRESH_BINARY：二值化模式
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        # 步骤3：二值化图像进行Canny边缘检测 参数说明：输入图像、输出图像、低阈值、高阈值、Sobel算子孔径大小
        edges = cv2.Canny(binary, CANNY_LOW, CANNY_HIGH, 3)

        # 显示处理结果
        cv2.imshow("原始画面", frame)
        cv2.imshow("二值化图像（白色赛道）", binary)
        cv2.imshow("Canny边缘检测结果", edges)

        # 按下ESC键退出循环
        if cv2.waitKey(1) & 0xFF == 27:
            break

    # 释放资源
    cap.release()           # 释放摄像头
    cv2.destroyAllWindows() # 关闭所有显示窗口

if __name__ == "__main__":
    main()