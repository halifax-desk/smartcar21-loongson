# Cam2DataSet — 摄像头图像采集与增广工具

基于 PyQt5 的摄像头图像采集器，支持定时拍照、分辨率缩放、命名规则管理，以及 **21 种 Albumentations 实时图像增广**。

## 项目结构

```
Cam2DataSet/
├── collector_ui.py        # 主入口 — CollectorUI 菜单/信号/采集逻辑
├── settings_dialog.py     # 设置对话框 — 4个Tab (摄像头测试/采集/存放/增广)
├── augmentations.py       # 增广引擎 — 零GUI依赖，可独立调用
├── USERCheck.bat          # 许可证脚本
├── docs/
│   └── torch-dll-workaround.md  # torch DLL 损坏修复报告
├── .gitignore
└── README.md
```

## 功能

### 采集
- 摄像头实时预览 (`cv2` 独立窗口，窗口名 `cam{索引}`)
- 定时采集：0.5s / 1s / 2s / 3s / 5s
- 拍瞬间 20ms 白色闪烁（拍照效果）
- ESC 键自动停止采集
- 自定义类名 + 批次名 + 6 位自动编号

### 图像增广 (Albumentations)

| 类别 | 增广项 |
|------|--------|
| 噪点 | 高斯噪点、椒盐噪点、泊松噪点、随机噪点 |
| 模糊 | 高斯模糊、均值模糊、中值模糊、运动模糊、焦外模糊 |
| 色彩 | 随机亮度、随机对比度、随机伽马值、色相/饱和度 |
| 几何 | 旋转(±180°)、缩放(80-120%)、平移、水平翻转、裁剪 |
| 高级 | 随机遮挡(Cutout)、随机擦除、JPEG 压缩失真 |

每拍 1 张原始帧 + N 张增广变体，文件命名：
```
{类名}_{批次}_{编号}.jpg          # 原始
{类名}_{批次}_{编号}_{增广名}.jpg  # 增广变体
```

### augmentations.py 独立调用

```python
from augmentations import AugRegistry, get_augmentations, apply_augmentations

# 列出全部21种增广
print(AugRegistry.all_names())

# 按名字获取 transform 对象
augs = get_augmentations(["gauss_noise", "rotate", "flip"], h=480, w=640)

# 批量应用到一帧
results = apply_augmentations(frame, augs, target_w=320, target_h=240)
```

## 依赖

| 包 | 版本 (开发环境) | 用途 |
|----|:---:|------|
| Python | 3.11+ | 运行环境 |
| PyQt5 | 5.15.11 | GUI 框架 |
| opencv-python-headless | 4.13.0 | 摄像头采集 / 图像读写 / 预览 |
| albumentations | 2.0.8 | 图像增广 |
| numpy | 2.4.4 | 白色闪光帧生成、增广底层计算 |

### 安装

```bash
pip install PyQt5 opencv-python-headless albumentations numpy
```

> **注意**：使用 `opencv-python-headless`（无 GUI 后端）可避免和 PyQt5 的 Qt 冲突。如果你已有 `opencv-python`，两者功能等价。

## 运行

```bash
python collector_ui.py
```

操作流程：
1. **文件 → 选择存放目录** 指定输出路径
2. **编辑 → 系统设置** 配置摄像头索引、分辨率、延时、命名、增广勾选
3. 点击 **开始采集**，右侧终端实时输出日志
4. **ESC** 或点击 **停止采集** 结束

## 已知问题 & 解决方案

### torch / c10.dll 损坏导致 albumentations 无法 import

**症状**：勾选增广后采集报错 `OSError: [WinError 1114] c10.dll ...`

**根因**：`albumentations 2.0.8` 无条件 `import torch`，而本地 torch 的 `c10.dll` 损坏。

**解决**：已在 `augmentations.py` 中采用 `sys.modules` mock 方案，block 真实 torch 加载（详见 `docs/torch-dll-workaround.md`）。此修复对 albumentations 的 cv2 后端功能无任何影响。

### albumentations 2.0.8 参数名变更

1.x → 2.0.8 存在 breaking changes，已全部适配。详见报告。

## 许可证

MIT — 见 `USERCheck.bat` 或 关于 → 许可证。

## 作者

**Zhovice** — [zhovices@outlook.com](mailto:zhovices@outlook.com)
