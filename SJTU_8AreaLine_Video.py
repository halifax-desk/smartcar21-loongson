# -*- coding: utf-8 -*-
import cv2
import numpy as np
import sys
import io
import time
import os
import glob

# 设置输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 图像尺寸（根据image.h）
image_h = 120    # 图像高度
image_w = 188    # 图像宽度

# 颜色定义
uesr_RED = 0XF800    # 红色像素值
uesr_GREEN = 0X07E0  # 绿色像素值
uesr_BLUE = 0X001F    # 蓝色像素值

# 宏定义
white_pixel = 255   # 白色像素值
black_pixel = 0     # 黑色像素值
bin_jump_num = 1    # 二值化跳转步长
border_max = image_w - 2  # 边界最大值
border_min = 1        # 边界最小值

# 全局变量
original_image = np.zeros((image_h, image_w), dtype=np.uint8)   # 原始图像
bin_image = np.zeros((image_h, image_w), dtype=np.uint8)        # 二值化图像
image_thereshold = 120                                        # 二值化阈值

l_border = np.zeros(image_h, dtype=np.uint8)                    # 左边线
r_border = np.zeros(image_h, dtype=np.uint8)                    # 右边线
center_line = np.zeros(image_h, dtype=np.uint8)                # 中心线

data_stastics_l = 0                                            # 左边线数据统计
data_stastics_r = 0                                            # 右边线数据统计

points_l = np.zeros((image_h * 3, 2), dtype=np.uint16)        # 左边线点
points_r = np.zeros((image_h * 3, 2), dtype=np.uint16)        # 右边线点

hightest = 0                                                    # 最高点行号

def limit_a_b(x, a, b):
    """限制x在[a, b]范围内"""
    return max(a, min(x, b))

def image_process():
    """图像处理函数（根据C++版本转换）"""
    global bin_image, points_l, points_r, data_stastics_l, data_stastics_r
    global center_line, l_border, r_border, hightest
    
    # 二值化
    _, bin_image = cv2.threshold(original_image, image_thereshold, 255, cv2.THRESH_BINARY)
    
    # 清空数组
    points_l = np.zeros((image_h * 3, 2), dtype=np.uint16)
    points_r = np.zeros((image_h * 3, 2), dtype=np.uint16)
    center_line = np.zeros(image_h, dtype=np.uint8)
    l_border = np.zeros(image_h, dtype=np.uint8)
    r_border = np.zeros(image_h, dtype=np.uint8)
    hightest = 0
    
    # 从下到上检测边线
    for i in range(image_h - 1, -1, -1):
        row = bin_image[i, :]
        white_indices = np.where(row > 0)[0]
        
        if len(white_indices) >= 2:
            left_edge = white_indices[0]
            right_edge = white_indices[-1]
            
            l_border[i] = limit_a_b(left_edge, border_min, border_max)
            r_border[i] = limit_a_b(right_edge, border_min, border_max)
            center_line[i] = (l_border[i] + r_border[i]) // 2
            
            if hightest == 0:
                hightest = i
    
    # 记录左右边线的点（每bin_jump_num个点记录一次）
    point_idx_l = 0
    point_idx_r = 0
    
    for i in range(hightest, image_h - 1, bin_jump_num):
        if l_border[i] > 0 and l_border[i] < image_w:
            if point_idx_l < len(points_l):
                points_l[point_idx_l][0] = l_border[i]
                points_l[point_idx_l][1] = i
                point_idx_l += 1
        
        if r_border[i] > 0 and r_border[i] < image_w:
            if point_idx_r < len(points_r):
                points_r[point_idx_r][0] = r_border[i]
                points_r[point_idx_r][1] = i
                point_idx_r += 1
    
    data_stastics_l = point_idx_l
    data_stastics_r = point_idx_r

# Media目录下的所有mp4文件
media_dir = "Media"
output_dir = "output"

# 确保输出目录存在
os.makedirs(output_dir, exist_ok=True)

# 清空output目录
for filename in os.listdir(output_dir):
    file_path = os.path.join(output_dir, filename)
    if os.path.isfile(file_path):
        os.remove(file_path)
print(f"已清空 {output_dir} 目录")

# 获取所有mp4文件
mp4_files = glob.glob(os.path.join(media_dir, "*.mp4"))

if not mp4_files:
    print(f"在 {media_dir} 目录下没有找到MP4文件")
    sys.exit(1)

print(f"找到 {len(mp4_files)} 个MP4文件")

for mp4_file in mp4_files:
    print(f"\n处理文件: {os.path.basename(mp4_file)}")
    
    # 打开视频文件
    cap = cv2.VideoCapture(mp4_file)
    if not cap.isOpened():
        print(f"无法打开视频文件: {mp4_file}")
        continue
    
    # 获取视频属性
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # 输出文件名
    base_name = os.path.splitext(os.path.basename(mp4_file))[0]
    output_file = os.path.join(output_dir, f"{base_name}_processed.mp4")
    
    # 创建视频写入器
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_file, fourcc, fps, (image_w, image_h))
    
    frame_count = 0
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            break
        
        # 缩放到指定尺寸
        frame = cv2.resize(frame, (image_w, image_h))
        original_image = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 图像处理
        image_process()
        
        # 创建显示帧（从二值化图像转换为彩色）
        display_frame = cv2.cvtColor(bin_image, cv2.COLOR_GRAY2BGR)
        
        # 绘制左右点（只绘制有效的点）
        for i in range(data_stastics_l):
            x = int(points_l[i][0])
            y = int(points_l[i][1])
            if 0 <= x < image_w and 0 <= y < image_h:
                cv2.circle(display_frame, (x, y), 1, (255, 0, 0), 1)
        
        for i in range(data_stastics_r):
            x = int(points_r[i][0])
            y = int(points_r[i][1])
            if 0 <= x < image_w and 0 <= y < image_h:
                cv2.circle(display_frame, (x, y), 1, (0, 0, 255), 1)
        
        # 绘制中心线和边界
        for i in range(hightest, image_h - 1):
            if center_line[i] > 0 and center_line[i] < image_w:
                cv2.circle(display_frame, (int(center_line[i]), i), 1, (0, 255, 0), 2)
            if l_border[i] > 0 and l_border[i] < image_w:
                cv2.circle(display_frame, (int(l_border[i]), i), 1, (255, 0, 0), 1)
            if r_border[i] > 0 and r_border[i] < image_w:
                cv2.circle(display_frame, (int(r_border[i]), i), 1, (0, 0, 255), 1)
        
        # 写入输出视频
        out.write(display_frame)
        
        frame_count += 1
        
        if frame_count % 100 == 0:
            current_time = time.time() - start_time
            print(f"  处理帧数: {frame_count}, 时间: {current_time:.2f}s")
    
    cap.release()
    out.release()
    
    print(f"完成! 输出文件: {output_file}")

print("\n所有视频处理完成!")
