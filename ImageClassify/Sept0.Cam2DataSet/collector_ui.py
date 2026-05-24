import sys
import os
import datetime
import cv2
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QTextEdit, QAction, QMessageBox,
    QFileDialog, QLabel, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, QProcess
from PyQt5.QtGui import QFont, QColor, QTextCursor

from settings_dialog import SettingsDialog
from augmentations import get_augmentations


class CollectorUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.is_collecting = False
        self.save_dir = ""
        self._settings_dlg = None
        self.capture_cap = None
        self.capture_counter = 0
        self.capture_timer = QTimer(self)
        self.capture_timer.timeout.connect(self._on_capture_tick)
        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self._update_preview)
        self.flash_timer = QTimer(self)
        self.flash_timer.setSingleShot(True)
        self.flash_timer.timeout.connect(self._end_flash)
        self._last_preview_frame = None
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self._on_process_output)
        self.process.finished.connect(self._on_process_finished)
        self._init_ui()

    @property
    def settings_dlg(self):
        if self._settings_dlg is None:
            self._settings_dlg = SettingsDialog(self)
        return self._settings_dlg

    def _init_ui(self):
        self.setWindowTitle("采集器")
        self.resize(1200, 680)
        self.setMinimumSize(900, 500)

        self._setup_menu_bar()
        self._setup_central_widget()

    def _setup_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件(&F)")

        new_action = QAction("新建项目", self)
        new_action.triggered.connect(self._on_new_project)
        file_menu.addAction(new_action)

        open_action = QAction("选择存放目录...", self)
        open_action.triggered.connect(self._on_open)
        file_menu.addAction(open_action)

        save_action = QAction("保存", self)
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu("编辑(&E)")
        settings_action = QAction("系统设置...", self)
        settings_action.triggered.connect(self._on_system_settings)
        edit_menu.addAction(settings_action)

        tools_menu = menubar.addMenu("工具(&T)")

        clear_action = QAction("清空输出", self)
        clear_action.triggered.connect(self._on_clear_output)
        tools_menu.addAction(clear_action)

        export_action = QAction("导出日志", self)
        export_action.triggered.connect(self._on_export_log)
        tools_menu.addAction(export_action)

        about_menu = menubar.addMenu("关于(&A)")
        source_action = QAction("源代码", self)
        source_action.triggered.connect(self._on_source_code)
        about_menu.addAction(source_action)
        license_action = QAction("许可证", self)
        license_action.triggered.connect(self._on_license)
        about_menu.addAction(license_action)

    def _setup_central_widget(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        left_panel = QWidget()
        left_panel.setFixedWidth(180)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        left_layout.addStretch()

        self.start_btn = QPushButton("开始采集")
        self.start_btn.setMinimumHeight(48)
        self.start_btn.setFont(QFont("Microsoft YaHei", 12))
        self.start_btn.clicked.connect(self._on_toggle_collect)
        left_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("停止采集")
        self.stop_btn.setMinimumHeight(48)
        self.stop_btn.setFont(QFont("Microsoft YaHei", 12))
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_toggle_collect)
        left_layout.addWidget(self.stop_btn)

        left_layout.addStretch()

        self.status_label = QLabel("状态: 就绪")
        self.status_label.setFont(QFont("Microsoft YaHei", 9))
        self.status_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.status_label)

        main_layout.addWidget(left_panel)

        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        self.output_area.setFont(QFont("Consolas", 10))
        self.output_area.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #cccccc;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        self.output_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.output_area)

    def _append_output(self, text, color=None):
        if color:
            self.output_area.setTextColor(QColor(color))
        else:
            self.output_area.setTextColor(QColor("#cccccc"))
        self.output_area.append(text)
        cursor = self.output_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.output_area.setTextCursor(cursor)

    def _timestamp(self):
        return datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

    def _on_new_project(self):
        self._append_output(f"{self._timestamp()} 新建项目")

    def _on_open(self):
        path = QFileDialog.getExistingDirectory(self, "选择存放目录")
        if path:
            self.save_dir = path
            self.settings_dlg.dir_input.setText(path)
            self._append_output(f"{self._timestamp()} 存放目录: {path}", "#4ec9b0")

    def _on_save(self):
        self._append_output(f"{self._timestamp()} 保存项目")

    def _on_system_settings(self):
        self.settings_dlg.show()

    def _on_source_code(self):
        QMessageBox.information(self, "源代码", "采集器 v1.0\n开源项目")

    def _on_license(self):
        bat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "USERCheck.bat")
        if not os.path.exists(bat_path):
            QMessageBox.warning(self, "错误", f"找不到脚本文件:\n{bat_path}")
            self._append_output(f"{self._timestamp()} 错误: 脚本不存在 {bat_path}", "#f44747")
            return
        self._append_output(f"{self._timestamp()} 执行: {bat_path}", "#4ec9b0")
        self.process.setWorkingDirectory(os.path.dirname(bat_path))
        self.process.start("cmd.exe", ["/c", bat_path])

    def _on_process_output(self):
        data = self.process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        for line in data.splitlines():
            if line.strip():
                self._append_output(line, "#cccccc")

    def _on_process_finished(self, exit_code, exit_status):
        color = "#4ec9b0" if exit_code == 0 and exit_status == QProcess.NormalExit else "#f44747"
        self._append_output(f"{self._timestamp()} 进程结束 (exit_code={exit_code})", color)

    def _on_clear_output(self):
        self.output_area.clear()
        self._append_output(f"{self._timestamp()} 输出已清空")

    def _on_export_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出日志", "output.log", "Log Files (*.log);;All Files (*)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.output_area.toPlainText())
            self._append_output(f"{self._timestamp()} 日志已导出到: {path}")

    def _on_toggle_collect(self):
        if not self.is_collecting:
            self._start_collect()
        else:
            self._stop_collect()

    def _start_collect(self):
        if not self.save_dir:
            QMessageBox.warning(self, "错误", "请先通过 文件→选择存放目录 选择存放目录")
            self._append_output(f"{self._timestamp()} 错误: 未选择存放目录", "#f44747")
            return

        cam_idx_text = self.settings_dlg.cam_input.text().strip()
        try:
            cam_idx = int(cam_idx_text)
        except ValueError:
            QMessageBox.warning(self, "错误", f"摄像头索引无效: '{cam_idx_text}'")
            self._append_output(f"{self._timestamp()} 错误: 摄像头索引无效 '{cam_idx_text}'", "#f44747")
            return

        cap = cv2.VideoCapture(cam_idx)
        if not cap.isOpened():
            QMessageBox.warning(self, "错误", f"无法打开摄像头 {cam_idx}，请检查设备连接或索引")
            self._append_output(f"{self._timestamp()} 错误: 无法打开摄像头 {cam_idx}", "#f44747")
            return

        w_raw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h_raw = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        try:
            target_w = int(self.settings_dlg.resize_input.text()) if self.settings_dlg.resize_input.text() else w_raw
            target_h = int(self.settings_dlg.resize_input_h.text()) if self.settings_dlg.resize_input_h.text() else h_raw
        except ValueError:
            cap.release()
            QMessageBox.warning(self, "错误", "分辨率输入无效，请输入整数")
            self._append_output(f"{self._timestamp()} 错误: 分辨率输入无效", "#f44747")
            return

        delay_text = self.settings_dlg.delay_combo.currentText().replace("s", "")
        try:
            delay_sec = float(delay_text)
        except ValueError:
            cap.release()
            QMessageBox.warning(self, "错误", f"延时设置无效: '{delay_text}'")
            self._append_output(f"{self._timestamp()} 错误: 延时设置无效", "#f44747")
            return
        delay_ms = int(delay_sec * 1000)

        classname = self.settings_dlg.classname_input.text().strip()
        batchname = self.settings_dlg.batchname_input.text().strip()

        if not classname:
            classname = "default"
        if not batchname:
            batchname = "batch"

        try:
            os.makedirs(self.save_dir, exist_ok=True)
        except OSError as e:
            cap.release()
            QMessageBox.warning(self, "错误", f"无法创建存放目录:\n{e}")
            self._append_output(f"{self._timestamp()} 错误: 无法创建目录 {self.save_dir}", "#f44747")
            return

        self.capture_cap = cap
        self._cam_idx = cam_idx
        self._target_w = target_w
        self._target_h = target_h
        self._classname = classname
        self._batchname = batchname
        self.capture_counter = 0

        self.is_collecting = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("状态: 采集中")
        self.capture_timer.start(delay_ms)
        self.preview_timer.start(30)

        cv2.namedWindow(f"cam{self._cam_idx}", cv2.WINDOW_NORMAL)
        cv2.waitKey(1)

        self._append_output(f"{self._timestamp()} === 开始采集 ===", "#4ec9b0")
        self._append_output(f"{self._timestamp()} 摄像头: {cam_idx} | 分辨率: {w_raw}x{h_raw} -> {target_w}x{target_h} | 延时: {delay_sec}s", "#4ec9b0")

    def _get_enabled_aug_names(self):
        dlg = self.settings_dlg
        mapping = [
            (dlg.cb_gaussian_noise, "gauss_noise"),
            (dlg.cb_sp_noise, "sp_noise"),
            (dlg.cb_poisson_noise, "poisson_noise"),
            (dlg.cb_random_noise, "random_noise"),
            (dlg.cb_gaussian_blur, "gauss_blur"),
            (dlg.cb_mean_blur, "mean_blur"),
            (dlg.cb_median_blur, "median_blur"),
            (dlg.cb_motion_blur, "motion_blur"),
            (dlg.cb_defocus_blur, "defocus_blur"),
            (dlg.cb_brightness, "brightness"),
            (dlg.cb_contrast, "contrast"),
            (dlg.cb_gamma, "gamma"),
            (dlg.cb_hue_sat, "hue_sat"),
            (dlg.cb_rotate, "rotate"),
            (dlg.cb_scale, "scale"),
            (dlg.cb_translate, "translate"),
            (dlg.cb_flip, "flip"),
            (dlg.cb_crop, "crop"),
            (dlg.cb_cutout, "cutout"),
            (dlg.cb_erase, "erase"),
            (dlg.cb_jpeg, "jpeg"),
        ]
        return [name for cb, name in mapping if cb.isChecked()]

    def _on_capture_tick(self):
        if self.capture_cap is None:
            return
        ret, frame = self.capture_cap.read()
        if not ret:
            self._append_output(f"{self._timestamp()} 警告: 读取帧失败", "#dcdcaa")
            return

        self.capture_counter += 1
        base_name = f"{self._classname}_{self._batchname}_{self.capture_counter:06d}"

        if self._target_w and self._target_h:
            save_frame = cv2.resize(frame, (self._target_w, self._target_h))
        else:
            save_frame = frame

        self._do_flash()

        orig_path = os.path.join(self.save_dir, f"{base_name}.jpg")
        try:
            cv2.imwrite(orig_path, save_frame)
        except Exception as e:
            self._append_output(f"{self._timestamp()} 错误: 写入文件失败 {orig_path}: {e}", "#f44747")
            return

        h_raw, w_raw = frame.shape[:2]
        enabled_names = self._get_enabled_aug_names()
        aug_list = get_augmentations(enabled_names, h_raw, w_raw)
        saved_count = 0
        for aug_name, transform in aug_list:
            try:
                aug = transform(image=frame)["image"]
                if self._target_w and self._target_h:
                    aug = cv2.resize(aug, (self._target_w, self._target_h))
                aug_path = os.path.join(self.save_dir, f"{base_name}_{aug_name}.jpg")
                cv2.imwrite(aug_path, aug)
                saved_count += 1
            except Exception as e:
                self._append_output(f"{self._timestamp()} 增广 [{aug_name}] 失败: {e}", "#f44747")

        msg = f"{self._timestamp()} 采集 #{self.capture_counter} -> {base_name}.jpg"
        if saved_count:
            msg += f" (+{saved_count} 增广)"
        self._append_output(msg, "#6a9955")

    def _do_flash(self):
        import numpy as np
        if self._last_preview_frame is not None:
            h, w = self._last_preview_frame.shape[:2]
            white_frame = 255 * np.ones((h, w, 3), dtype=np.uint8)
            cv2.imshow(f"cam{self._cam_idx}", white_frame)
            cv2.waitKey(1)
        self.flash_timer.start(20)

    def _end_flash(self):
        pass

    def _update_preview(self):
        if self.capture_cap is None:
            return
        if self.flash_timer.isActive():
            return
        ret, frame = self.capture_cap.read()
        if not ret:
            return
        self._last_preview_frame = frame.copy()
        cv2.imshow(f"cam{self._cam_idx}", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27:
            self._stop_collect()

    def _stop_collect(self):
        self.is_collecting = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("状态: 就绪")
        self.capture_timer.stop()
        self.preview_timer.stop()

        if self.capture_cap is not None:
            self.capture_cap.release()
            self.capture_cap = None

        try:
            cv2.destroyWindow(f"cam{self._cam_idx}")
        except Exception:
            pass

        self._append_output(f"{self._timestamp()} === 停止采集 ===", "#f44747")

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "确认退出", "确定要退出采集器吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.is_collecting:
                self._stop_collect()
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass
            event.accept()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = CollectorUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
