import cv2
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QSizePolicy, QDialog, QTabWidget, QLineEdit, QFormLayout,
    QGroupBox, QComboBox, QCheckBox, QSpinBox, QMessageBox,
    QFileDialog
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QImage, QPixmap


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cap = None
        self.cam_timer = QTimer(self)
        self.cam_timer.timeout.connect(self._update_frame)
        self.fps_counter = 0
        self.fps_timer = QTimer(self)
        self.fps_timer.timeout.connect(self._update_fps)
        self._current_fps = 0
        self._frame_count = 0
        self.orig_w = None
        self.orig_h = None
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle("系统设置")
        self.resize(640, 520)
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        cam_tab = QWidget()
        cam_layout = QVBoxLayout(cam_tab)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("摄像头索引:"))

        self.cam_input = QLineEdit("0")
        self.cam_input.setMaximumWidth(80)
        top_row.addWidget(self.cam_input)

        self.detect_btn = QPushButton("检测摄像头")
        self.detect_btn.clicked.connect(self._on_detect_camera)
        top_row.addWidget(self.detect_btn)

        top_row.addStretch()
        cam_layout.addLayout(top_row)

        self.cam_view = QLabel("摄像头画面")
        self.cam_view.setAlignment(Qt.AlignCenter)
        self.cam_view.setMinimumHeight(240)
        self.cam_view.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                color: #555;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
            }
        """)
        self.cam_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        cam_layout.addWidget(self.cam_view)

        info_group = QGroupBox("摄像头信息")
        info_layout = QFormLayout(info_group)

        self.res_label = QLabel("--")
        info_layout.addRow("分辨率:", self.res_label)

        self.fps_label = QLabel("--")
        info_layout.addRow("帧率:", self.fps_label)

        self.status_label = QLabel("未检测")
        info_layout.addRow("状态:", self.status_label)

        cam_layout.addWidget(info_group)

        tabs.addTab(cam_tab, "摄像头测试")

        cap_tab = QWidget()
        cap_layout = QVBoxLayout(cap_tab)
        cap_layout.setContentsMargins(10, 10, 10, 10)
        cap_layout.setSpacing(12)

        scale_group = QGroupBox("缩倍率")
        scale_layout = QHBoxLayout(scale_group)
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["1", "2", "4", "8"])
        self.scale_combo.currentIndexChanged.connect(self._on_scale_changed)
        scale_layout.addWidget(self.scale_combo)
        scale_layout.addStretch()
        cap_layout.addWidget(scale_group)

        res_group = QGroupBox("分辨率")
        res_layout = QHBoxLayout(res_group)

        self.resize_input = QLineEdit()
        self.resize_input.setMaximumWidth(70)
        self.resize_input.setPlaceholderText("宽")
        res_layout.addWidget(self.resize_input)

        res_layout.addWidget(QLabel("x"))

        self.resize_input_h = QLineEdit()
        self.resize_input_h.setMaximumWidth(70)
        self.resize_input_h.setPlaceholderText("高")
        res_layout.addWidget(self.resize_input_h)
        res_layout.addStretch()
        cap_layout.addWidget(res_group)

        delay_group = QGroupBox("采集延时")
        delay_layout = QHBoxLayout(delay_group)

        self.delay_combo = QComboBox()
        self.delay_combo.addItems(["0.5s", "1s", "2s", "3s", "5s"])
        self.delay_combo.setCurrentIndex(1)
        delay_layout.addWidget(self.delay_combo)
        delay_layout.addStretch()
        cap_layout.addWidget(delay_group)

        cap_layout.addStretch()
        tabs.addTab(cap_tab, "采集设置")

        save_tab = QWidget()
        save_layout = QVBoxLayout(save_tab)
        save_layout.setContentsMargins(10, 10, 10, 10)
        save_layout.setSpacing(12)

        dir_group = QGroupBox("存放目录")
        dir_h_layout = QHBoxLayout(dir_group)
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("选择或输入目录路径...")
        dir_h_layout.addWidget(self.dir_input)
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self._on_browse_dir)
        dir_h_layout.addWidget(self.browse_btn)
        save_layout.addWidget(dir_group)

        self.autosave_check = QCheckBox("AutoSave")
        save_layout.addWidget(self.autosave_check)

        name_group = QGroupBox("命名规则")
        name_layout = QHBoxLayout(name_group)
        self.classname_input = QLineEdit()
        self.classname_input.setPlaceholderText("类名")
        name_layout.addWidget(self.classname_input)

        self.batchname_input = QLineEdit()
        self.batchname_input.setPlaceholderText("批次名")
        name_layout.addWidget(self.batchname_input)

        name_layout.addWidget(QLabel("自动编号"))
        save_layout.addWidget(name_group)

        limit_group = QGroupBox("存储限制")
        limit_layout = QHBoxLayout(limit_group)

        limit_layout.addWidget(QLabel("单文件上限:"))
        self.file_size_spin = QSpinBox()
        self.file_size_spin.setRange(1, 10000)
        self.file_size_spin.setValue(100)
        self.file_size_spin.setSuffix(" MB")
        self.file_size_spin.setMaximumWidth(100)
        limit_layout.addWidget(self.file_size_spin)

        limit_layout.addSpacing(20)

        limit_layout.addWidget(QLabel("目录上限:"))
        self.dir_size_spin = QSpinBox()
        self.dir_size_spin.setRange(1, 10000)
        self.dir_size_spin.setValue(1000)
        self.dir_size_spin.setSuffix(" MB")
        self.dir_size_spin.setMaximumWidth(100)
        limit_layout.addWidget(self.dir_size_spin)

        limit_layout.addStretch()
        save_layout.addWidget(limit_group)

        save_layout.addStretch()
        tabs.addTab(save_tab, "存放设置")

        aug_tab = QWidget()
        aug_scroll = QVBoxLayout(aug_tab)
        aug_scroll.setContentsMargins(10, 10, 10, 10)
        aug_scroll.setSpacing(6)

        def _sep():
            line = QWidget()
            line.setFixedHeight(1)
            line.setStyleSheet("background-color: #3c3c3c;")
            return line

        def _cat(title):
            lbl = QLabel(title)
            lbl.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
            return lbl

        def _row(cb_list):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(16)
            for cb in cb_list:
                row_layout.addWidget(cb)
            row_layout.addStretch()
            return row

        self.cb_gaussian_noise = QCheckBox("高斯噪点")
        self.cb_sp_noise = QCheckBox("椒盐噪点")
        self.cb_poisson_noise = QCheckBox("泊松噪点")
        self.cb_random_noise = QCheckBox("随机噪点")

        self.cb_gaussian_blur = QCheckBox("高斯模糊")
        self.cb_mean_blur = QCheckBox("均值模糊")
        self.cb_median_blur = QCheckBox("中值模糊")
        self.cb_motion_blur = QCheckBox("运动模糊")
        self.cb_defocus_blur = QCheckBox("焦外模糊")

        self.cb_brightness = QCheckBox("随机亮度")
        self.cb_contrast = QCheckBox("随机对比度")
        self.cb_gamma = QCheckBox("随机伽马值")
        self.cb_hue_sat = QCheckBox("随机色相/饱和度")

        self.cb_rotate = QCheckBox("旋转")
        self.cb_scale = QCheckBox("缩放")
        self.cb_translate = QCheckBox("平移")
        self.cb_flip = QCheckBox("翻转")
        self.cb_crop = QCheckBox("裁剪")

        self.cb_cutout = QCheckBox("随机遮挡(Cutout)")
        self.cb_erase = QCheckBox("随机擦除")
        self.cb_jpeg = QCheckBox("JPEG压缩失真")

        aug_scroll.addWidget(_cat("噪点 (Noise)"))
        aug_scroll.addWidget(_row([self.cb_gaussian_noise, self.cb_sp_noise,
                                   self.cb_poisson_noise, self.cb_random_noise]))
        aug_scroll.addWidget(_sep())

        aug_scroll.addWidget(_cat("模糊 (Blur)"))
        aug_scroll.addWidget(_row([self.cb_gaussian_blur, self.cb_mean_blur,
                                   self.cb_median_blur, self.cb_motion_blur,
                                   self.cb_defocus_blur]))
        aug_scroll.addWidget(_sep())

        aug_scroll.addWidget(_cat("亮度 / 对比度 / 色彩"))
        aug_scroll.addWidget(_row([self.cb_brightness, self.cb_contrast,
                                   self.cb_gamma, self.cb_hue_sat]))
        aug_scroll.addWidget(_sep())

        aug_scroll.addWidget(_cat("几何变换"))
        aug_scroll.addWidget(_row([self.cb_rotate, self.cb_scale,
                                   self.cb_translate, self.cb_flip, self.cb_crop]))
        aug_scroll.addWidget(_sep())

        aug_scroll.addWidget(_cat("高级增强"))
        aug_scroll.addWidget(_row([self.cb_cutout, self.cb_erase, self.cb_jpeg]))

        aug_scroll.addStretch()
        tabs.addTab(aug_tab, "采集增广")

    def _on_browse_dir(self):
        path = QFileDialog.getExistingDirectory(self, "选择存放目录")
        if path:
            self.dir_input.setText(path)

    def _on_detect_camera(self):
        cam_idx_text = self.cam_input.text().strip()
        try:
            cam_idx = int(cam_idx_text)
        except ValueError:
            self.status_label.setText("摄像头索引无效")
            return

        if self.cap is not None:
            self.cap.release()
            self.cam_timer.stop()
            self.fps_timer.stop()

        self.cap = cv2.VideoCapture(cam_idx)
        if not self.cap.isOpened():
            self.status_label.setText(f"无法打开摄像头 {cam_idx}")
            self.res_label.setText("--")
            self.fps_label.setText("--")
            self.cam_view.setText("摄像头画面")
            return

        w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.res_label.setText(f"{w} x {h}")

        self._frame_count = 0
        self._current_fps = 0
        self.fps_label.setText("--")

        self.cam_timer.start(30)
        self.fps_timer.start(1000)
        self.status_label.setText("运行中")

        self.orig_w = w
        self.orig_h = h
        self.scale_combo.setCurrentIndex(0)
        self._apply_scale()

    def _update_frame(self):
        if self.cap is None:
            return
        ret, frame = self.cap.read()
        if not ret:
            return
        self._frame_count += 1
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        self.cam_view.setPixmap(
            pixmap.scaled(self.cam_view.width(), self.cam_view.height(),
                          Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def _update_fps(self):
        self._current_fps = self._frame_count
        self._frame_count = 0
        self.fps_label.setText(f"{self._current_fps} fps")

    def _on_scale_changed(self, idx):
        cam_text = self.cam_input.text().strip()
        try:
            cam_idx = int(cam_text)
        except ValueError:
            QMessageBox.warning(self, "提示", f"摄像头索引无效: '{cam_text}'")
            self.scale_combo.blockSignals(True)
            self.scale_combo.setCurrentIndex(0)
            self.scale_combo.blockSignals(False)
            return

        cap = cv2.VideoCapture(cam_idx)
        if not cap.isOpened():
            QMessageBox.warning(self, "提示", f"无法打开摄像头 {cam_idx}，请检查设备连接或索引")
            self.scale_combo.blockSignals(True)
            self.scale_combo.setCurrentIndex(0)
            self.scale_combo.blockSignals(False)
            return

        self.orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        self._apply_scale()

    def _apply_scale(self):
        if self.orig_w is None or self.orig_h is None:
            return
        scale_text = self.scale_combo.currentText()
        try:
            scale = int(scale_text)
        except ValueError:
            return
        new_w = self.orig_w // scale
        new_h = self.orig_h // scale
        self.resize_input.setText(str(new_w))
        self.resize_input_h.setText(str(new_h))

    def closeEvent(self, event):
        if self.cap is not None:
            self.cam_timer.stop()
            self.fps_timer.stop()
            self.cap.release()
            self.cap = None
        event.accept()
