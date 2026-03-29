import cv2
import os
import numpy as np
import time

# --- 图像尺寸定义 ---
MT9V03X_W = 188
MT9V03X_H = 120
SEARCH_IMAGE_DIR = "SourceVideo/"
OUTPUT_IMAGE_DIR = "output/"

#基础算法参数
SEARCH_IMAGE_W = MT9V03X_W          # 搜线宽度
SEARCH_IMAGE_H = MT9V03X_H          # 搜线高度
BLACKPOINT = 50                     # 黑点值
CONTRASTOFFSET = 3                  # 搜线对比偏移

# 处理间隔配置
PROCESS_INTERVAL = 3  # 每3帧处理一帧

def processVideoFrames(videoPath, outputDir):
    # 创建输出目录（如果不存在）
    if not os.path.exists(outputDir):
        os.makedirs(outputDir)
    
    # 打开视频文件
    cap = cv2.VideoCapture(videoPath)
    
    # 获取视频基本信息
    fps = cap.get(cv2.CAP_PROP_FPS)
    totalFrames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"视频信息: {videoPath}")
    print(f"帧率: {fps}, 总帧数: {totalFrames}, 分辨率: {width}x{height}")
    
    # 创建原始标注视频写入对象
    outputVideoPath = os.path.join(outputDir, "output.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(outputVideoPath, fourcc, fps, (width, height))
    
    # 创建二值化视频写入对象
    outputBinaryVideoPath = os.path.join(outputDir, "binary_output.mp4")
    outBinary = cv2.VideoWriter(outputBinaryVideoPath, fourcc, fps, (width, height), isColor=False)
    
    frameCount = 0
    processedFrameCount = 0
    startTime = time.time()
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        frameCount += 1
        elapsedTime = time.time() - startTime
        
        # 每3帧处理一帧
        if frameCount % PROCESS_INTERVAL == 0:
            processedFrameCount += 1
            print(f"正在处理第 {frameCount}/{totalFrames} 帧（第 {processedFrameCount} 个处理帧），耗时: {elapsedTime:.2f}s")
            
            # 帧处理逻辑
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 100, 200)
            
            # 二值化处理
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
            
            centerX = width // 2
            filteredEdges = np.zeros_like(edges)
            
            leftBoundaryPoints = []
            rightBoundaryPoints = []
            centerLinePoints = []
            
            for row in range(height - 1, -1, -1):
                leftFound = False
                rightFound = False
                leftX = centerX
                rightX = centerX
                
                max_offset = max(centerX, width - centerX)
                for offset in range(max_offset):
                    if not leftFound and centerX - offset >= 0:
                        if edges[row, centerX - offset] > 0:
                            leftX = centerX - offset
                            leftFound = True
                            filteredEdges[row, leftX] = 255
                            leftBoundaryPoints.append((leftX, row))
                    
                    if not rightFound and centerX + offset < width:
                        if edges[row, centerX + offset] > 0:
                            rightX = centerX + offset
                            rightFound = True
                            filteredEdges[row, rightX] = 255
                            rightBoundaryPoints.append((rightX, row))
                    
                    if leftFound and rightFound:
                        break
                
                if leftFound and rightFound:
                    centerXAvg = (leftX + rightX) // 2
                    centerLinePoints.append((centerXAvg, row))
            
            # 绘制标注
            result = frame.copy()
            
            # 绘制边界点（红色）
            for (x, y) in leftBoundaryPoints:
                cv2.circle(result, (x, y), 2, (0, 0, 255), -1)
            for (x, y) in rightBoundaryPoints:
                cv2.circle(result, (x, y), 2, (0, 0, 255), -1)
            
            # 绘制中心线（绿色）
            if len(centerLinePoints) > 1:
                for i in range(1, len(centerLinePoints)):
                    cv2.line(result, centerLinePoints[i-1], centerLinePoints[i], (0, 255, 0), 2)
            
            # 标注处理时间
            cv2.putText(result, f"Time: {elapsedTime:.2f}s", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # 写入处理后的帧
            out.write(result)
            outBinary.write(binary)
        else:
            # 非处理帧直接写入
            out.write(frame)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            outBinary.write(gray)
    
    cap.release()
    out.release()
    outBinary.release()
    print(f"视频处理完成! 共处理 {processedFrameCount} 帧，总耗时: {time.time() - startTime:.2f}s")
    print(f"输出视频: {outputVideoPath}")
    print(f"二值化视频: {outputBinaryVideoPath}")

def processVideos():
    inputDir = "SourceVideo"
    outputDir = "output"
    
    # 创建输出目录（如果不存在）
    if not os.path.exists(outputDir):
        os.makedirs(outputDir)
    
    # 查找所有MP4文件
    mp4Files = []
    for filename in os.listdir(inputDir):
        if filename.lower().endswith(".mp4"):
            mp4Files.append(filename)
    
    print(f"找到 {len(mp4Files)} 个MP4文件")
    
    for filename in mp4Files:
        inputPath = os.path.join(inputDir, filename)
        # 创建视频专属输出目录
        videoOutputDir = os.path.join(outputDir, os.path.splitext(filename)[0])
        processVideoFrames(inputPath, videoOutputDir)
    
    print("所有视频处理完成!")

if __name__ == "__main__":
    processVideos()