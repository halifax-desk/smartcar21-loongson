import time
import cv2
import numpy as np


def main():
    # 初始化摄像头（0表示默认摄像头）
    cap = cv2.VideoCapture(0)
    
    # 设置摄像头分辨率为640x480
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # 记录程序启动时间
    start_time = time.time()
    
    # 主循环：实时捕获和显示画面
    while True:
        # 读取一帧画面
        ret, frame = cap.read()
        
        # 如果读取失败（如摄像头断开），退出循环
        if not ret:
            break
        
        # 计算程序运行时间（精确到毫秒）
        elapsed_time = time.time() - start_time
        
        # 在画面左上角显示运行时间
        cv2.putText(frame, f"Time: {elapsed_time:.3f}s", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # 显示画面
        cv2.imshow("Screen1", frame)
        
        # 等待1毫秒，检测按键输入
        key = cv2.waitKey(1)
        
        # 如果按下ESC键（ASCII码27），退出循环
        if key == 27:
            break
    
    # 释放摄像头资源
    cap.release()
    
    # 关闭所有显示窗口
    cv2.destroyAllWindows()


# 程序入口
if __name__ == "__main__":
    main()