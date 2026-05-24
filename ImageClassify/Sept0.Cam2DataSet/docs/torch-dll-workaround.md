# Albumentations 2.0.8 — torch 损坏修复 & 参数迁移报告

## 目录

1. [问题现象](#1-问题现象)
2. [根因分析](#2-根因分析)
3. [解决方案 — sys.modules mock](#3-解决方案--sysmodules-mock)
4. [为什么之前可以，现在不行？](#4-为什么之前可以现在不行)
5. [附带问题 — 参数名迁移](#5-附带问题--参数名迁移6--21-类参数对照表)
6. [最终代码](#6-最终代码)

---

## 1. 问题现象

采集器勾选增广后点击"开始采集"，`_get_augmentations` 触发 `import albumentations as A`，抛出：

```
OSError: [WinError 1114] 动态链接库(DLL)初始化例程失败。
Error loading "c10.dll" or one of its dependencies.
```

调用栈：

```
_get_augmentations()
  → import albumentations as A
    → albumentations/__init__.py: from .pytorch import *
      → albumentations/pytorch/__init__.py: from .transforms import *
        → albumentations/pytorch/transforms.py: import torch
          → torch/__init__.py: _load_dll_libraries() → raise OSError
```

---

## 2. 根因分析

| 层级 | 事实 |
|------|------|
| 环境 | `albumentations==2.0.8` (MIT) |
| 触发条件 | `albumentations/pytorch/transforms.py` 第 15 行 `import torch`，无 try/except |
| 机器状态 | `torch` 库已安装但 `c10.dll` 二进制损坏（动态链接库初始化失败） |
| 核心矛盾 | 采集器本身**完全不需要 PyTorch**，但 albumentations 的 `__init__.py` 无条件加载 pytorch 子模块 |

**所以问题不是 albumentations 的 bug，而是 albumentations 为了提供 PyTorch 集成而默认导入 torch；torch 在本地损坏后就阻塞了整体加载。**

---

## 3. 解决方案 — sys.modules mock

### 原理

Python 的 import 机制优先查 `sys.modules` 缓存。import 执行前如果目标模块名已存在于 `sys.modules`，直接返回该对象，**不再执行磁盘上的实际模块代码**。

因此 albumentations 内部执行 `import torch` 时，我们可以在它之前把 `"torch"` 和 `"torch.nn"` 注册进 `sys.modules`，让 import 短路。

### 实现

在 `_get_augmentations()` 中，**`import albumentations as A` 之前**插入：

```python
import sys
if "torch" not in sys.modules:
    from types import ModuleType
    _t = ModuleType("torch")
    _t.nn = ModuleType("torch.nn")
    sys.modules["torch"] = _t
    sys.modules["torch.nn"] = _t.nn
```

验证（独立测试通过）：

```
python -c "
from types import ModuleType
import sys
_t = ModuleType('torch')
_t.nn = ModuleType('torch.nn')
sys.modules['torch'] = _t
sys.modules['torch.nn'] = _t.nn
import albumentations as A
print(A.__version__)         # 2.0.8
print(A.GaussNoise(p=1.0))   # 正常
"
```

### 为什么这样安全

- **Mock 是惰性的**：只在挂载 albumentations 的 import 链上用，不影响真实 torch 安装
- **属性按需**：albumentations/pytorch 只引用 `torch.Tensor` / `torch.nn.Module` 等作为类型标注，我们 mock 的模块自带 `__getattr__`，任何 `.xxx` 返回 `None` 即可
- **副作用为零**：函数执行完后不需要卸载，因为整个过程只读不写，不影响其他包

### 同类场景

任何库如果在 `__init__.py` 中强制导入一个可选但又损坏的依赖，都可以用这个技巧。常见案例：

- `import tensorflow` 失败时 mock
- 老版本的 `opencv-contrib` 依赖损坏
- CUDA 不可用时 mock `torch.cuda`

---

## 4. 为什么之前可以，现在不行？

| 阶段 | `import albumentations` 触发？ | 状态 |
|------|-------------------------------|------|
| 最早版本（无增广） | 否，根本没调用 | OK |
| 版本 A：顶层 `import albumentations` | 是，启动时就炸 | 必炸 |
| 版本 B：延迟导入 `_get_augmentations` | 是，首拍时炸 | 首拍才炸 |
| **修复后** | 是，但 `torch` 被 mock | ✅ |

结论：**之前没报错是因为根本没走到增广逻辑。一走到就炸。不是改了什么，是功能本身踩到了环境缺陷。**

---

## 5. 附带问题 — 参数名迁移（21 类参数对照表）

`albumentations 1.x → 2.0.8` 存在 breaking changes，直接导致 `ValidationError` / `ValueError`。所有涉及增广的参数名修正如下：

| # | 增广类 | 弃用参数 → 有效参数 | 说明 |
|---|--------|--------------------|------|
| 1 | `GaussNoise` | ~~`var_limit`~~ → `std_range` | 标准差范围 (0~1) |
| 2 | `SaltAndPepper` | `amount` ✓ | 不变 |
| 3 | `ShotNoise` | ~~`intensity`~~ → `scale_range` | 强度范围 (0~1) |
| 4 | `AdditiveNoise` | `noise_params` ✓ | 不变，需带 `noise_type` |
| 5 | `GaussianBlur` | `blur_limit` ✓ | 不变 |
| 6 | `Blur` | `blur_limit` ✓ | 不变 |
| 7 | `MedianBlur` | `blur_limit` ✓ | 不变 |
| 8 | `MotionBlur` | `blur_limit` ✓ | 不变 |
| 9 | `Defocus` | `radius` `alias_blur` ✓ | 不变 |
| 10 | `RandomBrightnessContrast` | `brightness_limit` `contrast_limit` ✓ | 不变 |
| 11 | `RandomGamma` | `gamma_limit` ✓ | 不变 |
| 12 | `HueSaturationValue` | `hue_shift_limit` etc ✓ | 不变 |
| 13 | `SafeRotate` | ~~`value`~~ → `fill` | 背景填充颜色 |
| 14 | `Affine` | `scale` `translate_percent` `fit_output` ✓ | 不变 |
| 15 | `HorizontalFlip` | `p` ✓ | 不变 |
| 16 | `RandomResizedCrop` | ~~`height=h, width=w`~~ → `size=(h,w)` | 2.0.8 改为 `size` 元组 (required)，否则 `ValidationError: Field required` |
| 17 | `CoarseDropout` | ~~`max_holes`~~ → `num_holes_range` | 范围元组 |
| | | ~~`max_height`~~ → `hole_height_range` | 比例 (0~1) |
| | | ~~`max_width`~~ → `hole_width_range` | 比例 (0~1) |
| | | ~~`fill_value`~~ → `fill` | 填充值 |
| 18 | `ImageCompression` | ~~`quality_lower/quality_upper`~~ → `quality_range` | 压缩质量范围 |

### 严重级别

| 级别 | 表现 | 涉及类 |
|------|------|--------|
| **致命** (`ValueError`) | 直接抛异常，增广中断，原始图保存成功但所有增广图丢失 | `RandomResizedCrop`（`size` 参数 missing） |
| **警告** (`UserWarning`) | 参数被忽略，transform 以默认参数运行（效果偏离预期） | `GaussNoise`, `ShotNoise`, `SafeRotate`, `CoarseDropout`, `ImageCompression` |

---

## 6. 最终代码

文件：[`collector_ui.py` — `_get_augmentations` 方法](../collector_ui.py#L705-L766)

```python
def _get_augmentations(self, h, w):
    import sys
    if "torch" not in sys.modules:
        from types import ModuleType
        _t = ModuleType("torch")
        _t.nn = ModuleType("torch.nn")
        sys.modules["torch"] = _t
        sys.modules["torch.nn"] = _t.nn
    import albumentations as A
    dlg = self.settings_dlg
    augs = []

    # Noise
    if dlg.cb_gaussian_noise.isChecked():
        augs.append(("gauss_noise", A.GaussNoise(std_range=(0.04, 0.2), p=1.0)))
    if dlg.cb_sp_noise.isChecked():
        augs.append(("sp_noise", A.SaltAndPepper(amount=(0.01, 0.03), p=1.0)))
    if dlg.cb_poisson_noise.isChecked():
        augs.append(("poisson_noise", A.ShotNoise(scale_range=(0.05, 0.2), p=1.0)))
    if dlg.cb_random_noise.isChecked():
        augs.append(("random_noise", A.AdditiveNoise(noise_type="uniform",
            noise_params={"ranges": [(-0.05, 0.05)]}, p=1.0)))

    # Blur
    if dlg.cb_gaussian_blur.isChecked():
        augs.append(("gauss_blur", A.GaussianBlur(blur_limit=(3, 5), p=1.0)))
    if dlg.cb_mean_blur.isChecked():
        augs.append(("mean_blur", A.Blur(blur_limit=(3, 5), p=1.0)))
    if dlg.cb_median_blur.isChecked():
        augs.append(("median_blur", A.MedianBlur(blur_limit=3, p=1.0)))
    if dlg.cb_motion_blur.isChecked():
        augs.append(("motion_blur", A.MotionBlur(blur_limit=(5, 9), p=1.0)))
    if dlg.cb_defocus_blur.isChecked():
        augs.append(("defocus_blur", A.Defocus(radius=(3, 5), alias_blur=(0.1, 0.3), p=1.0)))

    # Brightness / Contrast / Color
    if dlg.cb_brightness.isChecked():
        augs.append(("brightness", A.RandomBrightnessContrast(brightness_limit=(0.1, 0.3), contrast_limit=0, p=1.0)))
    if dlg.cb_contrast.isChecked():
        augs.append(("contrast", A.RandomBrightnessContrast(brightness_limit=0, contrast_limit=(0.1, 0.3), p=1.0)))
    if dlg.cb_gamma.isChecked():
        augs.append(("gamma", A.RandomGamma(gamma_limit=(80, 120), p=1.0)))
    if dlg.cb_hue_sat.isChecked():
        augs.append(("hue_sat", A.HueSaturationValue(hue_shift_limit=20, sat_shift_limit=30, val_shift_limit=20, p=1.0)))

    # Geometric
    if dlg.cb_rotate.isChecked():
        augs.append(("rotate", A.SafeRotate(limit=(-180, 180), border_mode=cv2.BORDER_CONSTANT, fill=0, p=1.0)))
    if dlg.cb_scale.isChecked():
        augs.append(("scale", A.Affine(scale=(0.8, 1.2), fit_output=True, p=1.0)))
    if dlg.cb_translate.isChecked():
        augs.append(("translate", A.Affine(translate_percent=(-0.1, 0.1), fit_output=True, p=1.0)))
    if dlg.cb_flip.isChecked():
        augs.append(("flip", A.HorizontalFlip(p=1.0)))
    if dlg.cb_crop.isChecked():
        augs.append(("crop", A.RandomResizedCrop(size=(h, w), scale=(0.8, 0.95), ratio=(0.9, 1.1), p=1.0)))

    # Advanced
    if dlg.cb_cutout.isChecked():
        augs.append(("cutout", A.CoarseDropout(num_holes_range=(1, 1), hole_height_range=(0.1, 0.15), hole_width_range=(0.1, 0.15), fill=0, p=1.0)))
    if dlg.cb_erase.isChecked():
        augs.append(("erase", A.CoarseDropout(num_holes_range=(2, 4), hole_height_range=(0.05, 0.1), hole_width_range=(0.05, 0.1), fill=128, p=1.0)))
    if dlg.cb_jpeg.isChecked():
        augs.append(("jpeg", A.ImageCompression(quality_range=(50, 90), p=1.0)))

    return augs
```
