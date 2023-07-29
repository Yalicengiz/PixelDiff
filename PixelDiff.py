import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QScrollArea, QPushButton, QGridLayout, QDialog, QSpinBox, QDialogButtonBox, QTabWidget, QStyleFactory
from PyQt5.QtGui import QPalette, QPixmap, QImage, QColor
from PyQt5.QtCore import Qt, QTimer, QSize
from PIL import ImageGrab
import numpy as np

__author__ = "Yalicengiz"
__date__ = "2023-07-16"

class SettingsDialog(QDialog):
    """Setting Dialog class for setting the maximum number of images and the threshold value."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface."""
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.max_images_label = QLabel("Maximum Numer Of Images:")
        self.max_images_input = self.create_spin_box(1, 100, self.parent().max_images)

        self.threshold_label = QLabel("Threshold Value:")
        self.threshold_input = self.create_spin_box(1, 255, self.parent().threshold)

        self.refresh_rate_label = QLabel("Pixel Control Time(ms):")
        self.refresh_rate_input = self.create_spin_box(1, 1000, self.parent().refresh_rate)

        self.add_widgets_to_layout([self.refresh_rate_label, self.refresh_rate_input])


        self.add_widgets_to_layout([self.max_images_label, self.max_images_input, 
                                    self.threshold_label, self.threshold_input])

        self.init_buttons()

    def create_spin_box(self, min_value, max_value, default_value):
        """Create a spin box with given values."""
        spin_box = QSpinBox()
        spin_box.setMinimum(min_value)
        spin_box.setMaximum(max_value)
        spin_box.setValue(default_value)
        return spin_box

    def add_widgets_to_layout(self, widgets):
        """Add widgets to the layout."""
        for widget in widgets:
            self.layout.addWidget(widget)

    def init_buttons(self):
        """Initialize the OK and Cancel buttons."""
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def accept(self):
        """Accept the changes."""
        self.parent().max_images = self.max_images_input.value()
        self.parent().threshold = self.threshold_input.value()
        self.parent().refresh_rate = self.refresh_rate_input.value()

        super().accept()


class ScreenCaptureViewer(QWidget):
    """Main class for screen capture viewer."""
    
    def __init__(self):
        super().__init__()
        self.init_variables()
        self.init_ui()

    def init_variables(self):
        """Initialize variables."""
        self.images = []
        self.bbox = None
        self.max_images = 10
        self.threshold = 10
        self.refresh_rate = 1000  # default 1 saniye
        self.is_selecting = False
        self.start_point = None
        self.end_point = None

    def init_ui(self):
        """Initialize the user interface."""
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.tab_widget = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab_widget.addTab(self.tab1, "Start/Stop")
        self.tab_widget.addTab(self.tab2, "Settings")
        self.layout.addWidget(self.tab_widget)

        self.init_tab1()
        self.init_tab2()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_images)

        self.hide_overlay_label = QLabel(self)
        self.hide_overlay_label.hide()

    def init_tab1(self):
        """Initialize the first tab."""
        self.tab1_layout = QVBoxLayout()
        self.tab1.setLayout(self.tab1_layout)

        self.start_stop_button = QPushButton("Start")
        self.start_stop_button.clicked.connect(self.toggle_capture)
        self.tab1_layout.addWidget(self.start_stop_button)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QGridLayout()
        self.scroll_content.setLayout(self.scroll_layout)
        self.scroll_area.setWidget(self.scroll_content)

        self.tab1_layout.addWidget(self.scroll_area)

    def init_tab2(self):
        """Initialize the second tab."""
        self.tab2_layout = QVBoxLayout()
        self.tab2.setLayout(self.tab2_layout)

        self.button_layout = QGridLayout()

        self.pixel_select_button = self.create_button("Select Pixel Area", self.toggle_select_bbox)
        self.pixel_select_button.setToolTip('It allows you to send the coordinates to the system by drawing a rectangle with the mouse on the transparent screen that occurs when you press this button.')

        self.settings_button = self.create_button("Visual Settings", self.show_settings)
        self.settings_button.setToolTip('This button allows you to customize the program.')

        self.reset_button = self.create_button("Reset", self.reset_settings)
        self.reset_button.setToolTip('This button resets the screenshots and pixel settings. You should use this to set new pixels.')

        self.button_layout.addWidget(self.pixel_select_button, 1, 0, alignment=Qt.AlignTop)
        self.button_layout.addWidget(self.reset_button, 1, 1, alignment=Qt.AlignTop)
        self.button_layout.addWidget(self.settings_button, 1, 3, alignment=Qt.AlignTop)
        

        self.button_layout.setColumnStretch(0, 2)
        self.button_layout.setColumnStretch(2, 2)

        self.tab2_layout.addLayout(self.button_layout)

    def create_button(self, text, function):
        """Create a button with given text and function."""
        button = QPushButton(text)
        button.setFixedHeight(20)
        button.setFixedSize(120, 80)
        button.clicked.connect(function)
        return button
    
    def reset_settings(self):
        """Reset all settings and clear images."""
        self.images = []
        self.bbox = None
        self.update_grid_layout()
        self.timer.stop()
        if self.timer.isActive():
            self.toggle_capture()
        self.start_stop_button.setText("Start")    
    

    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if self.is_selecting and event.buttons() & Qt.LeftButton:
            self.start_point = event.pos()

    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        if self.is_selecting and event.buttons() & Qt.LeftButton:
            self.end_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if self.is_selecting and event.button() == Qt.LeftButton:
            self.end_point = event.pos()
            self.bbox = (
                min(self.start_point.x(), self.end_point.x()),
                min(self.start_point.y(), self.end_point.y()),
                max(self.start_point.x(), self.end_point.x()),
                max(self.start_point.y(), self.end_point.y())
            )
            self.reset_selection()

    def reset_selection(self):
        """Reset the selection process."""
        self.is_selecting = False
        self.start_point = None
        self.end_point = None
        self.hide_overlay_label.hide()
        self.setWindowOpacity(1.0)
        self.update()

        self.pixel_select_button.show()
        self.settings_button.show()
        self.reset_button.show()

    def toggle_select_bbox(self):
        """Toggle the select bounding box mode."""
        if not self.is_selecting:
            self.pixel_select_button.hide()
            self.settings_button.hide()
            self.reset_button.hide()
        if self.timer.isActive():
            self.toggle_capture()
        self.start_stop_button.setText("Start")

        self.is_selecting = not self.is_selecting

        if self.is_selecting:
            self.hide_overlay_label.show()
            self.setWindowOpacity(0.5)
        else:
            self.reset_selection()

    def show_settings(self):
        """Show the settings dialog."""
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.max_images = dialog.max_images_input.value()
            self.threshold = dialog.threshold_input.value()
            self.refresh_rate = dialog.refresh_rate_input.value()


    def toggle_capture(self):
        """Toggle the screen capture mode."""
        if self.timer.isActive():
            self.timer.stop()
            self.start_stop_button.setText("Start")
        else:
            self.timer.start(self.refresh_rate)
            self.start_stop_button.setText("Stop")

    def check_image_diff(self, img1, img2, threshold=10):
        """Check if the difference between two images is greater than the threshold."""
        diff = np.abs(img1 - img2)
        return np.average(diff) > threshold

    def update_images(self):
        """Update the images based on screen capture."""
        if self.bbox:
            img = ImageGrab.grab(bbox=self.bbox)
            img = np.array(img)

            if not self.images or (
                    img.shape == self.images[0][0].shape and self.check_image_diff(img, self.images[0][0])):
                qimg = QImage(img.data, img.shape[1], img.shape[0], img.shape[1] * 3, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)
                label = QLabel()
                label.setPixmap(pixmap)
                self.images.insert(0, (img, pixmap, label))

                self.update_grid_layout()

                if len(self.images) > self.max_images:
                    _, _, old_label = self.images.pop()
                    old_label.setParent(None)

    def update_grid_layout(self):
        """Update the grid layout with new images."""
        for i in reversed(range(self.scroll_layout.count())):
            self.scroll_layout.itemAt(i).widget().setParent(None)

        for i, (_, pixmap, label) in enumerate(self.images):
            row = i // 3
            col = i % 3
            label.setPixmap(pixmap)
            self.scroll_layout.addWidget(label, row, col)

    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)

        if self.is_selecting:
            self.hide_overlay_label.setGeometry(0, 0, self.width(), self.height())

    def sizeHint(self):
        """Provide a size hint."""
        return QSize(800, 600)


def main():
    """Main function to start the application."""
    app = QApplication(sys.argv)

    # Temayı belirle
    app.setStyle(QStyleFactory.create('Fusion'))

    #Paleti oluştur
    palette = QPalette()

    # Renkleri belirle
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)

    # Paleti uygula
    app.setPalette(palette)

    scv = ScreenCaptureViewer()
    scv.show()
     
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()