# -*- coding: utf-8 -*-
import cv2
import numpy as np
import sys
import io
import os
import glob

# 设置输出编码为UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 二值化阈值
THRESHOLD = 100

# 列扫描间隔（每隔多少列寻找白色最多的首列）
SCAN_STEP = 3

# ROI参数
# ROI1: 画面中心向上的30%高度，居中，横向90%画面宽度
ROI1_HEIGHT_RATIO = 0.3
ROI1_WIDTH_RATIO = 1.0

# ROI2: 下半部分，横向100%画面宽度
ROI2_HEIGHT_RATIO = 0.5
ROI2_WIDTH_RATIO = 1.0

# Media目录下的所有mp4文件
media_dir = "Media"
output_dir = "output"

# 确保输出目录存在
os.makedirs(output_dir, exist_ok=True)

# 获取所有mp4文件
mp4_files = glob.glob(os.path.join(media_dir, "*.mp4"))

if not mp4_files:
    print(f"在 {media_dir} 目录下没有找到MP4文件")
    exit()

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
    out = cv2.VideoWriter(output_file, fourcc, fps, (320, 240))
    
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 缩放到320x240（原画面的1/4）
        frame = cv2.resize(frame, (320, 240))
        
        h, w = frame.shape[:2]
        
        # 计算ROI1（画面中心向上的30%高度，居中，70%宽度）
        roi1_height = int(h * ROI1_HEIGHT_RATIO)
        roi1_width = int(w * ROI1_WIDTH_RATIO)
        roi1_x = (w - roi1_width) // 2
        roi1_y = (h // 2) - roi1_height
        
        # 计算ROI2（下半部分，100%宽度）
        roi2_height = int(h * ROI2_HEIGHT_RATIO)
        roi2_width = int(w * ROI2_WIDTH_RATIO)
        roi2_x = 0
        roi2_y = h - roi2_height
        
        # 绘制ROI框
        frame_copy = frame.copy()
        cv2.rectangle(frame_copy, (roi1_x, roi1_y), (roi1_x + roi1_width, roi1_y + roi1_height), (255, 0, 0), 2)
        cv2.rectangle(frame_copy, (roi2_x, roi2_y), (roi2_x + roi2_width, h), (0, 255, 0), 2)
        cv2.putText(frame_copy, "ROI1", (roi1_x, roi1_y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
        cv2.putText(frame_copy, "ROI2", (roi2_x, roi2_y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # 转换为灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # 二值化
        _, binary = cv2.threshold(gray, THRESHOLD, 255, cv2.THRESH_BINARY)
        
        # ROI1：每一行检测左右边线并计算中心线
        roi1_binary = binary[roi1_y:roi1_y + roi1_height, roi1_x:roi1_x + roi1_width]
        for y in range(roi1_height):
            row_pixels = roi1_binary[y, :]
            white_indices = np.where(row_pixels > 0)[0]
            if len(white_indices) >= 2:
                left_edge = white_indices[0]
                right_edge = white_indices[-1]
                center_x = (left_edge + right_edge) // 2
                cv2.circle(frame_copy, (roi1_x + left_edge, roi1_y + y), 2, (0, 255, 0), -1)
                cv2.circle(frame_copy, (roi1_x + right_edge, roi1_y + y), 2, (0, 255, 0), -1)
                cv2.circle(frame_copy, (roi1_x + center_x, roi1_y + y), 2, (0, 0, 255), -1)
        
        # ROI2：每一行检测左右边线并计算中心线
        roi2_binary = binary[roi2_y:roi2_y + roi2_height, roi2_x:roi2_x + roi2_width]
        for y in range(roi2_height):
            row_pixels = roi2_binary[y, :]
            white_indices = np.where(row_pixels > 0)[0]
            if len(white_indices) >= 2:
                left_edge = white_indices[0]
                right_edge = white_indices[-1]
                center_x = (left_edge + right_edge) // 2
                cv2.circle(frame_copy, (roi2_x + left_edge, roi2_y + y), 2, (0, 255, 0), -1)
                cv2.circle(frame_copy, (roi2_x + right_edge, roi2_y + y), 2, (0, 255, 0), -1)
                cv2.circle(frame_copy, (roi2_x + center_x, roi2_y + y), 2, (0, 0, 255), -1)
        
        # ROI2最下面一行白色区域黄色高亮
        bottom_row = roi2_binary[roi2_height - 1, :]
        bottom_white_indices = np.where(bottom_row > 0)[0]
        if len(bottom_white_indices) >= 2:
            left_edge = bottom_white_indices[0]
            right_edge = bottom_white_indices[-1]
            cv2.rectangle(frame_copy, (roi2_x + left_edge, roi2_y + roi2_height - 1), (roi2_x + right_edge, roi2_y + roi2_height), (0, 255, 255), -1)
        
        # ROI2中心画竖线作为参考中心线
        roi2_center_x = roi2_x + roi2_width // 2
        cv2.line(frame_copy, (roi2_center_x, roi2_y), (roi2_center_x, h), (255, 255, 255), 2)
        
        # 写入输出视频
        out.write(frame_copy)
        
        frame_count += 1
        
        if frame_count % 100 == 0:
            print(f"  处理帧数: {frame_count}")
    
    cap.release()
    out.release()
    
    print(f"完成! 输出文件: {output_file}")

print("\n所有视频处理完成!")
