"""
AvatarWindow: Always-on-top window for AiChris avatar animation

Place your avatar image files (PNG):
- chris avatar cropped.png (mouth closed)
- Aichrisopenmouth.png (mouth open)

in the same directory as this script, or set the full paths below.

Set your avatar image file paths here:
AVATAR_CLOSED_PATH = "C:/Users/User/Desktop/AiChris 3.0/chris avatar cropped.png"  # or full path
AVATAR_OPEN_PATH = "C:/Users/User/Desktop/AiChris 3.0/Aichrisopenmouth.png"      # or full path

Usage:
from avatar import AvatarWindow, AVATAR_CLOSED_PATH, AVATAR_OPEN_PATH
avatar = AvatarWindow(AVATAR_CLOSED_PATH, AVATAR_OPEN_PATH)
avatar.show_open()  # Show mouth open
avatar.show_closed()  # Show mouth closed
"""
from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtCore import Qt, QPoint

# Define a maximum size constant (replacement for QWIDGETSIZE_MAX)
QWIDGETSIZE_MAX = 16777215  # This is the value used in Qt

AVATAR_CLOSED_PATH = "C:/Users/User/Desktop/AiChris 3.0/chris avatar cropped.png"  # or full path
AVATAR_OPEN_PATH = "C:/Users/User/Desktop/AiChris 3.0/Aichrisopenmouth.png"      # or full path

class AvatarWindow(QWidget):
    def __init__(self, closed_path, open_path, scale_factor=0.5):
        super().__init__()
        self.setWindowTitle('AiChris Avatar')
        self.closed_pixmap_orig = QPixmap(closed_path)
        self.open_pixmap_orig = QPixmap(open_path)
        self.scale_factor = scale_factor
        
        # Set initial size to a reasonable default
        initial_width = int(self.closed_pixmap_orig.width() * self.scale_factor)
        initial_height = int(self.closed_pixmap_orig.height() * self.scale_factor)
        
        self.closed_pixmap = self.closed_pixmap_orig.scaled(
            initial_width, initial_height,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.open_pixmap = self.open_pixmap_orig.scaled(
            initial_width, initial_height,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.label = QLabel(self)
        self.label.setPixmap(self.closed_pixmap)
        
        # Set a reasonable minimum size
        self.setMinimumSize(200, 200)
        
        # Set initial size
        self.resize(initial_width, initial_height)
        
        # Make window transparent
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        
        # For dragging the window
        self.dragging = False
        self.drag_position = None
        
        # For resizing
        self.resizing = False
        self.resize_start_pos = None
        self.resize_start_size = None
        self.resize_handle_size = 40  # Increased size of the resize handle area
        
        # Border width for dragging
        self.border_width = 10  # Width of the border area for dragging
        
        self.show_closed()
        self.show()

    def show_closed(self):
        if self.isVisible():
            self.label.setPixmap(self.closed_pixmap)
            self.is_mouth_open = False
            
    def show_open(self):
        if self.isVisible():
            self.label.setPixmap(self.open_pixmap)
            self.is_mouth_open = True

    def resizeEvent(self, event):
        # Allow resizing and rescale the avatar images
        w = self.width()
        h = self.height()
        self.closed_pixmap = self.closed_pixmap_orig.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.open_pixmap = self.open_pixmap_orig.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label.setPixmap(self.closed_pixmap if not hasattr(self, 'is_mouth_open') or not self.is_mouth_open else self.open_pixmap)
        self.label.resize(w, h)
        super().resizeEvent(event)

    def set_avatar_size(self, width, height):
        self.resize(width, height)
        
    # Mouse events for dragging and resizing
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            if self.is_in_resize_handle(pos):
                self.resizing = True
                self.resize_start_pos = event.globalPos()
                self.resize_start_size = self.size()
            else:
                # Allow dragging from anywhere in the window, not just the border
                self.dragging = True
                self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            if self.resizing:
                # Calculate new size
                delta = event.globalPos() - self.resize_start_pos
                new_width = max(self.resize_start_size.width() + delta.x(), self.minimumWidth())
                new_height = max(self.resize_start_size.height() + delta.y(), self.minimumHeight())
                self.resize(new_width, new_height)
            elif self.dragging:
                # Move the window
                self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.resizing = False
            event.accept()
            
    def is_in_resize_handle(self, pos):
        """Check if the position is in the resize handle area (bottom-right corner)"""
        return (pos.x() > self.width() - self.resize_handle_size and 
                pos.y() > self.height() - self.resize_handle_size)
    
    def is_in_border(self, pos):
        """Check if the position is in the border area for dragging"""
        return (pos.x() < self.border_width or 
                pos.x() > self.width() - self.border_width or 
                pos.y() < self.border_width or 
                pos.y() > self.height() - self.border_width)
                
    def paintEvent(self, event):
        """Draw a visible resize handle in the bottom-right corner and border around the window"""
        super().paintEvent(event)
        if self.isVisible():
            painter = QPainter(self)
            
            # Draw border around the entire window with increased thickness
            pen = painter.pen()
            pen.setWidth(self.border_width)  # Use border_width for thickness
            painter.setPen(QColor(255, 255, 255, 240))  # More opaque white border
            
            # Draw the border as four separate lines to create a solid border
            # Top border
            painter.drawLine(0, int(self.border_width/2), self.width(), int(self.border_width/2))
            # Bottom border
            painter.drawLine(0, self.height() - int(self.border_width/2), self.width(), self.height() - int(self.border_width/2))
            # Left border
            painter.drawLine(int(self.border_width/2), 0, int(self.border_width/2), self.height())
            # Right border
            painter.drawLine(self.width() - int(self.border_width/2), 0, self.width() - int(self.border_width/2), self.height())
            
            # Draw resize handle with increased size
            painter.setPen(QColor(255, 255, 255, 240))  # More visible white
            painter.setBrush(QColor(255, 255, 255, 180))  # More visible fill
            
            # Draw a larger triangle in the corner for the resize handle
            bottom_right = QPoint(self.width(), self.height())
            points = [
                bottom_right,
                QPoint(bottom_right.x() - self.resize_handle_size, bottom_right.y()),
                QPoint(bottom_right.x(), bottom_right.y() - self.resize_handle_size)
            ]
            
            # Fill the triangle for better visibility
            polygon = [points[0], points[1], points[2]]
            painter.setBrush(QColor(255, 255, 255, 180))
            painter.drawPolygon(polygon)
            
            # Draw the triangle outline
            for i in range(len(points)):
                painter.drawLine(points[i], points[(i+1) % len(points)])
                
            # Draw a second smaller triangle inside for better visibility
            inset = 10
            inner_points = [
                QPoint(bottom_right.x() - inset, bottom_right.y() - inset),
                QPoint(bottom_right.x() - self.resize_handle_size + inset, bottom_right.y() - inset),
                QPoint(bottom_right.x() - inset, bottom_right.y() - self.resize_handle_size + inset)
            ]
            
            # Draw the inner triangle
            for i in range(len(inner_points)):
                painter.drawLine(inner_points[i], inner_points[(i+1) % len(inner_points)]) 