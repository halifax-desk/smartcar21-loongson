import cv2
import numpy as np
import time

# 初始化视频捕获（0为默认摄像头，也可替换为视频文件路径如"video.mp4"）
cap = cv2.VideoCapture(0)
# 设置摄像头分辨率（可选，根据实际设备调整）
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# 初始化帧率计算相关变量
prev_time = time.time()
start_time = time.time()
fps = 0
frame_count = 0

# 巡线核心参数（可根据实际场景调整）
lower_white = np.array([0, 0, 200])    # 白色巡线的HSV下限（适用于白底黑线/黑底白线，可微调）
upper_white = np.array([180, 30, 255]) # 白色巡线的HSV上限
kernel = np.ones((5, 5), np.uint8)     # 形态学操作核，用于去噪

def detect_lane(frame):
    """
    巡线检测核心函数：返回处理后的帧、中心线坐标、左右边界坐标
    """
    # 1. 图像预处理
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)          # 转HSV色彩空间（抗光照干扰）
    mask = cv2.inRange(hsv, lower_white, upper_white)      # 提取白色区域掩码
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel) # 闭运算去噪（填充小黑洞）
    mask = cv2.medianBlur(mask, 5)                         # 中值滤波进一步去噪

    # 2. 查找轮廓（检测巡线边界）
    contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    left_bound = []  # 左边界坐标列表
    right_bound = [] # 右边界坐标列表
    center_line = [] # 中心线坐标列表

    if contours:
        # 找到最大轮廓（假设巡线是画面中最大的白色区域）
        max_contour = max(contours, key=cv2.contourArea)
        # 遍历轮廓的所有点，按x坐标划分左右边界
        for point in max_contour:
            x, y = point[0]
            # 计算轮廓的中心点x坐标（用于划分左右）
            contour_center_x = int(np.mean(max_contour[:, :, 0]))
            if x < contour_center_x:
                left_bound.append((x, y))
            else:
                right_bound.append((x, y))
        
        # 计算中心线（左右边界对应y坐标的x均值）
        # 先将左右边界按y坐标排序，确保一一对应
        left_bound.sort(key=lambda p: p[1])
        right_bound.sort(key=lambda p: p[1])
        # 取最小长度，避免索引越界
        min_len = min(len(left_bound), len(right_bound))
        for i in range(min_len):
            lx, ly = left_bound[i]
            rx, ry = right_bound[i]
            # 中心线x坐标 = （左边界x + 右边界x）/2，y坐标取对应值（保证对齐）
            cx = int((lx + rx) / 2)
            cy = ly  # 左右y坐标基本一致，取其一即可
            center_line.append((cx, cy))
    
    # 3. 在原图上绘制标注
    # 绘制左边界（红色）
    if left_bound:
        cv2.polylines(frame, [np.array(left_bound)], isClosed=False, color=(0, 0, 255), thickness=2)
    # 绘制右边界（蓝色）
    if right_bound:
        cv2.polylines(frame, [np.array(right_bound)], isClosed=False, color=(255, 0, 0), thickness=2)
    # 绘制中心线（绿色，加粗）
    if center_line:
        cv2.polylines(frame, [np.array(center_line)], isClosed=False, color=(0, 255, 0), thickness=3)
    
    return frame, center_line, left_bound, right_bound

# 主循环
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("无法读取视频帧，退出...")
        break
    
    # 全高ROI（即整个画面，无需裁剪）
    roi_frame = frame.copy()
    
    # 巡线检测
    result_frame, center_line, left_bound, right_bound = detect_lane(roi_frame)
    
    # 计算帧率和当前时间
    frame_count += 1
    curr_time = time.time()
    if curr_time - prev_time >= 1.0:  # 每1秒更新一次帧率
        fps = frame_count / (curr_time - prev_time)
        prev_time = curr_time
        frame_count = 0
    
    # 显示时间、帧率（左上角，白色字体，黑色背景增强可读性）
    elapsed_time = time.time() - start_time
    cv2.putText(result_frame, f"Time: {elapsed_time:.3f}s", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(result_frame, f"FPS: {fps:.1f}", (10, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # 显示结果
    cv2.imshow("Screen1", result_frame)
    # 按ESC键退出
    if cv2.waitKey(1) & 0xFF == 27:
        break

# 释放资源
cap.release()
cv2.destroyAllWindows()