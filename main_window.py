
import os



from PyQt5.QtWidgets import (
     QWidget, QLabel,
    QVBoxLayout, 
    QStackedWidget
    
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap, QFont, QFontDatabase
from PyQt5.QtNetwork import QNetworkConfigurationManager

from sync import SyncMixin
from ui import UiMixin
from todos import TodosMixin
from tasks import TasksMixin
from storage import StorageMixin


class MainWindow(SyncMixin, UiMixin, TodosMixin, TasksMixin, StorageMixin, QWidget):
    def __init__(self): 
        super().__init__()
        self.setGeometry(165,120,1600,830)
        self.setWindowTitle("Task Manager")

        self.user_id             = "demo_user"

        self.firebase_ready      = False
        self.online              = False
        self.cloud_dirty         = False

        self.firebase_thread     = None
        self.upload_thread       = None
        self.todo_upload_thread  = None

        self.task_upload_pending = False
        self.todo_upload_pending = False

        self.key_missing         = False

        self.setStyleSheet(self.load_style())


        self.header = QLabel("Task Manager",self)
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setObjectName("header")

        font_path = "assets/digit.ttf"

        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                font_family = QFontDatabase.applicationFontFamilies(font_id)
                if font_family:
                    self.my_font = QFont(font_family[0])
            else:
                print("Custum font failed to load!")
                self.my_font = QFont("Segoe UI")        
        else:
            print("Custom font failed to load!,\nfont should be at -> assets/digit.ttf")
            self.my_font = QFont("Segoe UI")

        bg_path = "assets/bg.png"    

        self.bg = QLabel(self)
        self.bg.setScaledContents(True)
        if os.path.exists(bg_path):
            pixmap = QPixmap(bg_path)
            if not pixmap.isNull():
                self.bg.setPixmap(pixmap)
            else:
                print("background image failed to load!")
                self.bg.setStyleSheet("background-color: rgba(128, 128, 128, 0.6);")
        else:
            print("Background image failed to load,\nimage should be at -> assets/bg.png")
            self.bg.setStyleSheet("background-color: rgba(128, 128, 128, 0.6);")        

        self.bg.lower()

        self.stack  = QStackedWidget(self)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.stack)

        self.cloud_status = QLabel("☁  Cloud:\nInitializing...", self)
        self.cloud_status.setMouseTracking(True)
        self.cloud_status.setObjectName("cloud_status")
        self.cloud_status.setStyleSheet("""
                    QLabel#cloud_status {
                        font-size: 35px;
                        padding: 6px 12px;
                        background-color: rgba(0, 0, 0, 1);
                        border-radius: 8px;
                        color: yellow;
                    }                                         
                """)
        
        self.cloud_status.setToolTip("initializing")

        self.tasks        = []
        self.todos_list   = []

        self.edit_buttons = []

        self.menu_page()
        
        self.load_tasks()
        self.load_todos()
        
        self.build_add_task_page()
        self.build_view_task_page()
        self.build_edit_task_page()
        self.build_complete_task_page()
        self.build_todo_list_page()
        self.build_add_todos_page()
        self.build_edit_todos()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        QTimer.singleShot(0, self.init_firebase)  

        self.net_manager = QNetworkConfigurationManager()
        self.net_manager.onlineStateChanged.connect(self.set_cloud_status_instant)

        QTimer.singleShot(0, self.start_auto_reconnect)
