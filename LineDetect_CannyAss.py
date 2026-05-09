import cv2
import numpy as np

# ===================== 算法核心参数（可根据车模微调）=====================
# 1. 大面积ROI设置（截取图像下半部分，排除天空/背景干扰）
# 为ROI参数添加注释，说明ROI顶部和底部的占比设置
ROI_TOP_RATIO = 0.4    # ROI顶部占比（只保留下方60%区域）
ROI_BOTTOM_RATIO = 1.0

# 2. 颜色阈值（HSV空间，红线/绿线）
RED_LOWER = np.array([0, 120, 70])
RED_UPPER = np.array([10, 255, 255])
GREEN_LOWER = np.array([40, 80, 40])
GREEN_UPPER = np.array([70, 255, 255])

# 3. 消抖控制参数
FILTER_WINDOW = 5       # 滑动窗口滤波大小
DEAD_ZONE = 8           # 舵机死区（小于该偏差不动作）
MAX_CORRECTION = 60     # 最大舵机转角限制

# 4. PID控制参数（巡线核心）
KP = 0.3                # 比例系数
KD = 0.1                # 微分系数

# ===================== 全局变量（消抖/滤波使用）=====================
last_error = 0          # 上一帧偏差
error_buffer = []       # 偏差滑动窗口

# ===================== 1. 大面积ROI截取 =====================
def get_roi(image):
    """提取赛道核心ROI区域，大幅降低计算量"""
    height = image.shape[0]
    top = int(height * ROI_TOP_RATIO)
    bottom = int(height * ROI_BOTTOM_RATIO)
    roi = image[top:bottom, :]  # 只保留图像下半部分
    return roi, top

# ===================== 2. 颜色提取 + Canny边缘辅助 =====================
def extract_lines(roi):
    """提取绿色中心线、红色边界线（Canny强化边界）"""
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    
    # 提取绿色中心线（固定阈值170二值化）
    green_mask = cv2.inRange(hsv, GREEN_LOWER, GREEN_UPPER)
    green_mask = cv2.threshold(green_mask, 170, 255, cv2.THRESH_BINARY)[1]
    # 形态学闭运算，消除噪点
    green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_CLOSE, np.ones((3,3), np.uint8))
    
    # 提取红色边界线 + Canny边缘检测强化边界
    red_mask = cv2.inRange(hsv, RED_LOWER, RED_UPPER)
    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    canny_edges = cv2.Canny(gray_roi, 50, 150)  # Canny边缘检测
    red_mask = cv2.bitwise_or(red_mask, canny_edges)  # 边缘辅助边界判断
    red_mask = cv2.threshold(red_mask, 170, 255, cv2.THRESH_BINARY)[1]
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, np.ones((3,3), np.uint8))
    
    return green_mask, red_mask

# ===================== 3. 计算中心线偏差 =====================
def calculate_center_error(green_mask):
    """计算绿色中心线与图像中心的偏差（控制核心）"""
    h, w = green_mask.shape
    image_center = w // 2  # 图像物理中心
    
    # 提取中心线像素点
    y_points, x_points = np.where(green_mask > 0)
    if len(x_points) == 0:
        return 0  # 无中心线，保持直行
    
    # 计算中心线重心
    line_center = int(np.mean(x_points))
    raw_error = line_center - image_center
    
    return raw_error

# ===================== 4. 消抖滤波算法 =====================
def debounce_filter(error):
    """滑动窗口平均滤波 + 死区控制，彻底消除抖动"""
    global error_buffer
    
    # 滑动窗口更新
    error_buffer.append(error)
    if len(error_buffer) > FILTER_WINDOW:
        error_buffer.pop(0)
    
    # 均值滤波
    filtered_error = int(np.mean(error_buffer))
    
    # 死区控制（小偏差不动作）
    if abs(filtered_error) < DEAD_ZONE:
        return 0
    
    return filtered_error

# ===================== 5. 边界保护 + PID控制 =====================
def pid_control(error):
    """PID算法 + 边界保护，防止冲出红线边界"""
    global last_error
    
    # PID计算
    p = KP * error
    d = KD * (error - last_error)
    output = p + d
    last_error = error
    
    # 限幅（防止舵机过载）
    output = np.clip(output, -MAX_CORRECTION, MAX_CORRECTION)
    
    return int(output)

# ===================== 6. 主巡线流程 =====================
def line_following_process(frame):
    """智能车巡线主函数"""
    # 步骤1：截取大面积ROI
    roi, roi_top = get_roi(frame)
    
    # 步骤2：提取绿线、红线（Canny辅助红线）
    green_mask, red_mask = extract_lines(roi)
    
    # 步骤3：计算原始偏差
    raw_error = calculate_center_error(green_mask)
    
    # 步骤4：消抖滤波
    filtered_error = debounce_filter(raw_error)
    
    # 步骤5：PID计算控制量
    steer_output = pid_control(filtered_error)
    
    # 可视化调试（可选）
    debug_view = frame.copy()
    h, w = frame.shape[:2]
    cv2.rectangle(debug_view, (0, int(h*ROI_TOP_RATIO)), (w, h), (255,0,0), 2)  # 画ROI区域
    cv2.putText(debug_view, f"Error: {filtered_error}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
    cv2.putText(debug_view, f"Steer: {steer_output}", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
    
    return steer_output, debug_view, green_mask, red_mask

# ===================== 测试主函数 =====================
if __name__ == "__main__":
    # 摄像头/视频读取
    cap = cv2.VideoCapture(0)  # 0为默认摄像头，可替换为视频路径
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 执行巡线算法
        steer, debug_img, green, red = line_following_process(frame)
        
        # 显示结果
        cv2.imshow("Debug View", debug_img)
        cv2.imshow("Green Center Line", green)
        cv2.imshow("Red Boundary + Canny", red)
        
        # 退出按键
        if cv2.waitKey(1) & 0xFF == 27:
            break
    
    cap.release()
    cv2.destroyAllWindows()