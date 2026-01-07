import os
import sys
import datetime
import json
import copy
from functools import partial
import firebase_admin
from firebase_admin import credentials, firestore

from PyQt5.QtWidgets import (QApplication,QWidget,QLabel,QLineEdit,
                             QVBoxLayout,QHBoxLayout,QPushButton,
                             QStackedWidget,QScrollArea,QMessageBox,
                             QRadioButton,QButtonGroup)
from PyQt5.QtCore import QTimer,QTime,Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap,QFont,QFontDatabase
from PyQt5.QtNetwork import QNetworkConfigurationManager

class FirebaseCheckThread(QThread):
    result = pyqtSignal(bool)

    def __init__(self, db):
        super().__init__()
        self.db = db

    def run(self):
        try:
            list(self.db.collection("users").limit(1).stream())
            self.result.emit(True)

        except Exception as e:
            print("Ping Failed: ",type(e), e)
            self.result.emit(False)    

class UploadThread(QThread):
    finished_upload = pyqtSignal(bool) 

    def __init__(self, snapshot, upload_type, db, user_id):
        super().__init__()
        self.snapshot = snapshot
        self.type = upload_type
        self.db = db
        self.user_id = user_id

        self.net_manager = QNetworkConfigurationManager()

    def run(self):
        if not self.net_manager.isOnline():
            print("Upload aborted - No Internet")
            self.finished_upload.emit(False)
            return
        
        try:
            ref = (
                self.db.collection("users")
                .document(self.user_id)
                .collection(self.type)
            )    

            if not self.net_manager.isOnline():
                print("Upload aborted - No Internet")
                self.finished_upload.emit(False)
                return

            for doc in ref.stream():

                if not self.net_manager.isOnline():
                    print("Upload aborted - No Internet")
                    self.finished_upload.emit(False)
                    return
                
                doc.reference.delete()

            for item in self.snapshot:

                if not self.net_manager.isOnline():
                    print("Upload aborted - No Internet")
                    self.finished_upload.emit(False)
                    return

                ref.add(item)

            if self.net_manager.isOnline():
                self.finished_upload.emit(True)    

            else:
                self.finished_upload.emit(False)    

        except Exception:
            self.finished_upload.emit(False)            

class MainWindow(QWidget):

    def __init__(self): 
        super().__init__()
        self.setGeometry(165,150,1600,800)
        self.setWindowTitle("Task Manager")

        self.user_id = "demo_user"

        self.firebase_ready = False
        self.online = False
        self.cloud_dirty = False

        self.setStyleSheet(self.load_style())

        self.header = QLabel("Task Manager",self)
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setObjectName("header")

        font_id = QFontDatabase.addApplicationFont("assets/digit.ttf")
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            self.my_font = QFont(font_family)
        else:
            self.my_font = QFont("Segoe UI")

        self.bg = QLabel(self)
        self.bg.setScaledContents(True)
        self.bg.setPixmap(QPixmap("assets/bg.png"))
        self.bg.lower()

        self.stack = QStackedWidget(self)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.stack)

        self.cloud_status = QLabel("☁  Cloud:\nInitializing...", self)
        self.cloud_status.setObjectName("cloud_status")
        self.cloud_status.setStyleSheet("""
                    QLabel#cloud_status {
                        font-size: 35px;
                        padding: 6px 12px;
                        background-color: rgba(0, 0, 0, 0.6);
                        border-radius: 8px;
                        color: yellow;
                    }
                """)

        self.tasks = []
        self.todos_list = []

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

    def set_cloud_status_instant(self, is_online):
        self.online = is_online

        if not is_online:
            self.set_cloud_status("offline")  

    def get_cloud_tasks(self):
        if not (hasattr(self, "db") and self.online):
            return []

        try:
            return [doc.to_dict() for doc in self.db.collection("users")
                    .document(self.user_id)
                    .collection("tasks")
                    .stream()]
        except Exception as e:
            print("Cloud fetch failed: ", e)
            return []          
        
    def get_cloud_todos(self):
        if not(hasattr(self, "db") and self.online):
            return []

        try:
            return [doc.to_dict() for doc in
                    self.db.collection("users")
                    .document(self.user_id)
                    .collection("todos")
                    .stream()]

        except Exception as e:
            print("Cloud fetch failed: ", e)
            return []    

    def init_firebase(self):
        if hasattr(self, "db") and self.db is not None:
            return
        
        if not os.path.exists("firebase_key.json"):
            print("firebase key missing - running offline")
            self.firebase_ready = False
            self.online = False
            self.set_cloud_status("offline")
            return

        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate("firebase_key.json")
                firebase_admin.initialize_app(cred)

            self.db = firestore.client()
            self.firebase_ready = True

            self.firebase_thread = FirebaseCheckThread(self.db)
            self.firebase_thread.result.connect(self.on_firebase_checked)
            self.firebase_thread.finished.connect(self.firebase_thread.deleteLater)
            self.firebase_thread.start()

        except Exception as e:
            print("Firebase init failed: ", e)
            self.firebase_ready = False    
            self.online = False
            self.set_cloud_status("offline")
        
    def on_firebase_checked(self, connected):
         
        self.online = connected  

        if not connected:
            self.set_cloud_status("offline")
            return
        
        cloud_tasks = self.get_cloud_tasks()
        cloud_todos = self.get_cloud_todos()     

        if (len(cloud_tasks) != len(self.tasks)) or (len(cloud_todos) != len(self.todos_list)):
            
            if not hasattr(self, "sync_conflict_page"):
                self.build_sync_conflict_page()

            self.stack.setCurrentWidget(self.sync_conflict_page)
            return    
        
        self.set_cloud_status("synced")

    def build_sync_conflict_page(self):

        cloud_tasks = self.get_cloud_tasks()
        cloud_todos = self.get_cloud_todos()

        self.sync_conflict_page = QWidget()         
        layout = QVBoxLayout(self.sync_conflict_page)

        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)

        header = QLabel("SYNC CONFLICT DETECTED")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 38px; font-family: segoe UI; color: yellow;")

        text = (
            f"Cloud and Local Data are different:\n\n"
            f"Local Tasks: {len(self.tasks)}\t\tLocal Todos: {len(self.todos_list)}\n"
            f"Cloud Tasks: {len(cloud_tasks)}\t\tCloud Todos: {len(cloud_todos)}\n\n"
            f"Select Which section should use cloud data."
        )

        info = QLabel(text)
        info.setWordWrap(True)
        info.setStyleSheet("color : yellow; font-size: 25px;")
        info.setAlignment(Qt.AlignCenter)

        self.task_radio_group = QButtonGroup(self)
        self.todo_radio_group = QButtonGroup(self)

        self.task_radio_cloud = QRadioButton("Tasks: Load From CLoud")
        self.task_radio_local = QRadioButton("Tasks: Keep Local Data")

        self.todo_radio_cloud = QRadioButton("Todos: Load From CLoud")
        self.todo_radio_local = QRadioButton("Todos: Keep Local Data")

        self.task_radio_group.addButton(self.task_radio_cloud)
        self.task_radio_group.addButton(self.task_radio_local)

        self.todo_radio_group.addButton(self.todo_radio_cloud)
        self.todo_radio_group.addButton(self.todo_radio_local)

        for radio in (self.task_radio_cloud, self.task_radio_local,
                      self.todo_radio_cloud, self.todo_radio_local):
            
            radio.setStyleSheet("font-size: 26px; padding: 10px; color: lime;")

        if len(cloud_tasks) >= len(self.tasks):
            self.task_radio_cloud.setChecked(True)
        else:
            self.task_radio_local.setChecked(True)

        if len(cloud_todos) >= len(self.todos_list):
            self.todo_radio_cloud.setChecked(True)
        else:
            self.todo_radio_local.setChecked(True)            

        continue_btn = QPushButton("Continue")
        continue_btn.setObjectName("confirm_conflict")    
        continue_btn.clicked.connect(self.apply_sync)

        task = QLabel("Tasks")
        task.setStyleSheet("color : yellow; font-size: 25px; background-color : rgba(0, 0, 0, 0.8);")
        task.setAlignment(Qt.AlignCenter)

        todo = QLabel("Todos")
        todo.setStyleSheet("color : yellow; font-size: 25px; background-color : rgba(0, 0, 0, 0.8);")
        todo.setAlignment(Qt.AlignCenter)

        hbox1 = QHBoxLayout()
        hbox1.addWidget(task)
        hbox1.addWidget(todo)

        hbox2 = QHBoxLayout()
        hbox2.addWidget(self.task_radio_cloud)
        hbox2.addWidget(self.todo_radio_cloud)

        hbox3 = QHBoxLayout()
        hbox3.addWidget(self.task_radio_local)
        hbox3.addWidget(self.todo_radio_local)

        layout.addWidget(header)
        layout.addWidget(info)
        layout.addLayout(hbox1)
        layout.addLayout(hbox2)
        layout.addLayout(hbox3)
        layout.addWidget(continue_btn)

        layout.setAlignment(Qt.AlignCenter)

        self.stack.addWidget(self.sync_conflict_page)

    def apply_sync(self):

        cloud_tasks = self.get_cloud_tasks()
        cloud_todos = self.get_cloud_todos()

        if self.task_radio_cloud.isChecked():
            self.tasks = cloud_tasks

        if self.todo_radio_cloud.isChecked():
            self.todos_list = cloud_todos 

        self.task_radio_cloud.setChecked(False)       
        self.task_radio_local.setChecked(False)
        self.todo_radio_cloud.setChecked(False)
        self.todo_radio_local.setChecked(False)

        self.save_task_file()
        self.save_todo_file()

        self.back_to_menu()
                       
    def update_time(self):
        if hasattr(self, "time_label"):
            current_time = QTime.currentTime().toString("hh:mm:ss AP")
            self.time_label.setText(current_time)    

        if hasattr(self, "date_label"):
            today = datetime.date.today().strftime("%d-%m-%Y")
            self.date_label.setText(str(today))

    def load_todos(self):
        file_path = "todos.json"
        self.todos_list = []

        try:        
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    self.todos_list = json.load(f)  

        except Exception:
            self.todos_list = []                                           

    def load_tasks(self):
        file_path = "tasks.json"
        self.tasks = []

        try:        
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    self.tasks = json.load(f)

        except Exception:
            self.tasks = []                                        

        self.sort_tasks()   

    def load_tasks_from_firebase(self):
        if not hasattr(self, "db") or self.db is None:
            return
        
        try:
            docs = (
                self.db.collection("users")
                .document(self.user_id)
                .collection("tasks")
                .stream()
            )    

            cloud_tasks = [doc.to_dict() for doc in docs]

            if cloud_tasks:
                self.tasks = cloud_tasks
                self.sort_tasks()
                self.cloud_dirty = False

                with open("tasks.json", "w") as f:
                    json.dump(self.tasks, f, indent=4)

        except Exception:
            self.set_cloud_status("offline")  

    def load_todos_from_firebase(self):
        if not hasattr(self, "db") or self.db is None:
            return
        
        try:
            docs = (
                self.db.collection("users")
                .document(self.user_id)
                .collection("todos")
                .stream()
            )     

            cloud_todos = [doc.to_dict() for doc in docs]

            if cloud_todos:
                self.todos_list = cloud_todos
                self.cloud_dirty = False

                with open("todos.json", "w") as f:
                    json.dump(self.todos_list, f, indent=4)

        except Exception:
            self.set_cloud_status("offline")                          

    def set_cloud_status(self, state):

        if not hasattr(self, "cloud_status"):
            return

        if state == "synced":
            self.cloud_status.setText("☁ Cloud:\n   Synced")
            self.cloud_status.setStyleSheet("""
                QLabel#cloud_status {
                    font-size: 35px;
                    padding: 6px 12px;
                    background-color: rgba(0, 120, 0, 0.7);
                    border-radius: 8px;
                    color: white;
                }
            """)

        elif state == "syncing":
            self.cloud_status.setText("☁ Cloud:\n   Syncing…")
            self.cloud_status.setStyleSheet("""
                QLabel#cloud_status {
                    font-size: 35px;
                    padding: 6px 12px;
                    background-color: rgba(180, 140, 0, 0.7);
                    border-radius: 8px;
                    color: black;
                }
            """)

        else:
            self.cloud_status.setText("☁ Cloud:\n   Offline")
            self.cloud_status.setStyleSheet("""
                QLabel#cloud_status {
                    font-size: 35px;
                    padding: 6px 12px;
                    background-color: rgba(150, 0, 0, 0.7);
                    border-radius: 8px;
                    color: white;
                }
            """)
                       
    def menu_page(self):
        self.menu = QWidget()

        vbox = QVBoxLayout(self.menu)
        vbox.setContentsMargins(0, 110, 0, 0)

        container_layout = QVBoxLayout()

        self.time_label = QLabel()      
        self.time_label.setObjectName("time_label")
        self.time_label.setFont(self.my_font)
        self.time_label.setAlignment(Qt.AlignCenter)

        self.date_label = QLabel()
        self.date_label.setObjectName("date_label")
        self.date_label.setFont(self.my_font)
        self.date_label.setAlignment(Qt.AlignCenter)
        
        self.addtask      = QPushButton("Add Tasks")
        self.viewtask     = QPushButton("View Tasks")
        self.completetask = QPushButton("Complete Tasks")
        self.todolist     = QPushButton("✨To-Do List✨")
        self.exit         = QPushButton("Exit")  

        self.addtask     .setObjectName("addtask")
        self.viewtask    .setObjectName("viewtask")
        self.completetask.setObjectName("completetask")
        self.todolist    .setObjectName("todolist")
        self.exit        .setObjectName("exit")

        container_layout.addWidget(self.time_label)
        container_layout.addWidget(self.date_label)
        container_layout.addWidget(self.addtask)
        container_layout.addWidget(self.viewtask)
        container_layout.addWidget(self.completetask)
        container_layout.addWidget(self.todolist)
        container_layout.addWidget(self.exit)

        container_layout.setAlignment(Qt.AlignCenter)

        vbox.addLayout(container_layout)
        vbox.addStretch()

        if self.menu not in [self.stack.widget(i) for i in range(self.stack.count())]:
            self.stack.addWidget(self.menu)
        
        self.addtask.clicked     .connect(self.open_add_task_page)
        self.viewtask.clicked    .connect(self.open_view_task_page)
        self.completetask.clicked.connect(self.open_complete_task_page)
        self.todolist.clicked    .connect(self.open_todo_list_page)
        self.exit.clicked        .connect(QApplication.quit)

    def load_style(self):
        return """

        QLabel#header{
        font-size : 50px;
        font-family: Segoe UI;
        background-color : rgba(0, 0, 0, 0.5);
        color: yellow;
        }

        QPushButton#addtask, #confirm_conflict, #confirm_todo, #delete_button_todo, #save_button_todo, #add_todos_button, #delete_button, #save_button, #viewtask, #completetask, #exit, #confirm{
        font-size : 40px;
        font-family : Segoe UI;
        font-weight : 600;
        border : 4px solid yellow;
        border-radius : 20px;
        margin : 10px;
        padding : 10px;
        background-color : rgba(31, 41, 51, 0.9);
        color : lime;
        }

        QPushButton#back_button_edit_todo, #back_button_add_todo, #back_button_todo,#back_button_view,#back_button_add,#back_button_complete,#back_button_edit{
        font-size : 40px;
        font-family : Segoe UI Emoji;
        border : 5px solid black;
        border-radius : 20px;
        background-color : rgba(0, 120, 255, 0.5);
        color : black;
        font-weight : 600;
        }

        QLabel#task_input,#deadline_input, #todo_input{
        font-size : 40px;
        font-family : Segoe UI;
        font-weight : bold;
        color : lime;
        background-color : rgba(0, 0, 0, 0.3);
        border : 5px solid black;
        border-radius : 10px;
        margin : 30px;
        padding : 20px;
        }

        QLabel#time_label,#date_label{
        font-size : 30px;
        border : 2px solid lime;
        border-radius : 10px;
        background-color: rgba(0, 0, 0, 0.8);
        color : lime;
        }

        QLineEdit{
        font-size : 50px;
        font-family : Segoe UI;
        color : white;
        border-radius : 15px;
        border : 5px solid black;
        background-color : rgba(0, 0, 0, 0.3);
        }

       QPushButton#todolist{
        font-size : 40px;
        font-family : Segoe UI;
        border : 4px solid black;
        border-radius : 20px;
        margin : 10px;
        padding : 10px;
        background-color : grey;
        color : yellow;
       }

        """

    def build_todo_list_page(self):

        if hasattr(self, "todo_page"):
            self.stack.setCurrentWidget(self.todo_page)
            return

        self.todo_page = QWidget()
        self.todo_layout = QHBoxLayout(self.todo_page)
        self.todo_layout.setContentsMargins(0, 100, 0 ,0)
        self.todo_layout.addStretch()

        self.container_todo = QWidget()
        self.container_todo.setFixedWidth(900)
        container_layout = QVBoxLayout(self.container_todo)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(12)

        self.back_button_todo = QPushButton("Back⬅️")
        self.back_button_todo.setObjectName("back_button_todo")
        self.back_button_todo.clicked.connect(self.back_to_menu)

        self.add_todos_button = QPushButton("Add To-Dos")
        self.add_todos_button.setObjectName("add_todos_button")
        self.add_todos_button.clicked.connect(self.open_add_todo)

        tool_layout = QHBoxLayout()
        tool_layout.addWidget(self.back_button_todo)
        tool_layout.addWidget(self.add_todos_button)
       
        container_layout.addLayout(tool_layout)

        header_layout = QHBoxLayout()

        self.todo_name  = QLabel("To-Dos")
        self.status     = QLabel("Toggle Status")
        self.edit       = QLabel("Edit")

        for x in (self.todo_name, self.status, self.edit):
            x.setStyleSheet("""
                            background-color : rgba(0, 255, 0, 0.4);
                            font-size: 34px; font-family : Segoe UI; 
                            font-weight: bold; color: black;
                            border : 8px solid black;
                            """)
            x.setAlignment(Qt.AlignCenter)
            header_layout.addWidget(x)

        container_layout.addLayout(header_layout)  

        self.scroll_todo = QScrollArea()
        self.scroll_todo.setWidgetResizable(True)
        self.scroll_todo.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scroll_todo.setStyleSheet("""
                    QScrollArea {
                        background: transparent;
                        border: none;
                    }
                    QScrollArea > QWidget > QWidget {
                        background: transparent;
                    }
                    QScrollBar:vertical {
                        width: 10px;
                        background: transparent;
                    }
                    QScrollBar::handle:vertical {
                        background: rgba(255,255,255,0.4);
                        border-radius: 5px;
                    }
                """)

        self.scroll_content_todo = QWidget()
        self.scroll_layout_todo = QVBoxLayout(self.scroll_content_todo)
        self.scroll_layout_todo.setAlignment(Qt.AlignTop)
        self.scroll_layout_todo.setContentsMargins(0, 0, 0, 0)  
        self.scroll_layout_todo.setSpacing(4)
        
        self.scroll_todo.setWidget(self.scroll_content_todo)

        container_layout.addWidget(self.scroll_todo)

        self.todo_layout.addWidget(self.container_todo)
        self.todo_layout.addStretch()

    def open_todo_list_page(self):
        if self.todo_page not in [self.stack.widget(i) for i in range(self.stack.count())]:
            self.stack.addWidget(self.todo_page) 

        self.refresh_todos()
        self.stack.setCurrentWidget(self.todo_page)

        if hasattr(self, "header"):
            self.header.setText("To-Do List")   

        if not self.todos_list:
            self.todo_name.setText("No")
            self.status.setText("To-Dos")
            self.edit.setText("Added")    

        else:
            self.todo_name.setText("To-Dos")
            self.status.setText("Toggle Status")
            self.edit.setText("Edit")     

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

            elif item.layout():
                self.clear_layout(item.layout())    

    def refresh_todos(self):
        self.clear_layout(self.scroll_layout_todo) 

        self.scroll_layout_todo.setSpacing(20) 

        for index, todo in enumerate(self.todos_list):
            row = QWidget()
            row.setFixedHeight(70)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(4, 4, 4, 4)
            row_layout.setSpacing(6)

            name = QLabel(todo["title"])
            status = QPushButton("✅" if todo["status"] else "❌")
            edit = QPushButton("📝")

            status.clicked.connect(partial(self.toggle_status_todo, index, status))
            edit.clicked.connect(partial(self.open_edit_todo, index))

            if todo["status"]:
                color = "lime"
                border = "lime"
            else:
                color = "white" 
                border= "red"   

            row.setStyleSheet("""
                                  QWidget{
                                  background-color : rgba(0, 0, 0, 0.5);
                                  }""")    

            name.setStyleSheet(f"font-size: 30px; border: 2px solid white; border-radius: 10px; color: {color};font-family : Segoe UI;font-weight: bold;background-color : rgba(0, 0, 0, 0.5);")
            name.setAlignment(Qt.AlignCenter)

            status.setStyleSheet(f"font-size: 28px; border : 4px solid {border}; border-radius : 10px; background-color : rgba(0, 0, 0, 0.5);")
            edit.setStyleSheet("font-size: 28px; background-color : rgba(31, 41, 51, 0.8); border-radius : 10px; border : 4px solid white;")

            row_layout.addWidget(name)
            row_layout.addWidget(status)
            row_layout.addWidget(edit)

            self.scroll_layout_todo.addWidget(row)

        self.scroll_layout_todo.addStretch()    

    def build_edit_todos(self):
        
        if hasattr(self, "edit_todo_page") :
            self.stack.setCurrentWidget(self.edit_todo_page)
            return

        self.edit_todo_page = QWidget()
        self.edit_todo_layout = QVBoxLayout(self.edit_todo_page)

        container = QWidget()
        container.setFixedWidth(1000)
        container_layout = QVBoxLayout(container)    

        self.back_button_edit_todo = QPushButton("Back⬅️")
        self.back_button_edit_todo.clicked.connect(self.open_todo_list_page)
        self.back_button_edit_todo.setObjectName("back_button_edit_todo")

        todo_input = QLabel("Enter New To-Do")
        self.new_todo = QLineEdit()

        todo_input.setStyleSheet("""
                            font-size : 40px;
                            font-family : Segoe UI;
                            font-weight : bold;
                            color : lime;
                            background-color : rgba(0, 0, 0, 0.3);
                            border : 5px solid black;
                            border-radius : 10px;
                            """)

        hbox1 = QHBoxLayout()
        hbox1.addWidget(todo_input)
        hbox1.addWidget(self.new_todo)

        self.save_button_todo = QPushButton("Save📁")
        self.save_button_todo.setObjectName("save_button_todo")
        self.save_button_todo.clicked.connect(self.save_edited_todo)

        self.delete_button_todo = QPushButton("Delete To-Do ❌")
        self.delete_button_todo.setObjectName("delete_button_todo")
        self.delete_button_todo.clicked.connect(self.confirm_delete_todo)

        container_layout.addWidget(self.back_button_edit_todo)
        container_layout.addLayout(hbox1)
        container_layout.addWidget(self.save_button_todo)
        container_layout.addWidget(self.delete_button_todo)

        self.edit_todo_layout.addWidget(container , alignment= Qt.AlignCenter)

    def confirm_delete_todo(self):
        message = QMessageBox()
        message.setWindowTitle("Confirm Deletion")
        message.setText("Are you sure you want to delete this todo?")
        message.setIcon(QMessageBox.Warning)    

        message.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        message.setStyleSheet("""
                QMessageBox {
                    background-color: #222;
                }

                QMessageBox QLabel {
                    color: white;
                    font-size: 22px;
                    font-family: Segoe UI;
                }

                QMessageBox QPushButton {
                    background-color: #444;
                    color: lime;
                    border: 2px solid yellow;
                    border-radius: 10px;
                    padding: 8px;
                    font-size: 20px;
                    font-weight: bold;
                    margin-right : 120px;
                }
                            """)

        result = message.exec_()

        if result == QMessageBox.Yes:
            self.delete_todo()

    def open_edit_todo(self, index):
        if index < 0 or index >= len(self.todos_list):
            return
        
        self.current_todo_index = index

        todo = self.todos_list[index]
        self.new_todo.setText(todo["title"])      

        if self.edit_todo_page not in [self.stack.widget(i) for i in  range(self.stack.count())]:
            self.stack.addWidget(self.edit_todo_page)

        self.stack.setCurrentWidget(self.edit_todo_page)

        if hasattr(self, "header"):
            self.header.setText("Edit Todo")    

    def toggle_status_todo(self, i, button):
        if i < 0 or i >= len(self.todos_list):
            return
        
        self.todos_list[i]["status"] = not self.todos_list[i]["status"]

        if self.todos_list[i]["status"]:
            button.setText("✅")
        else:
            button.setText("❌")  

        self.save_todo_file()
        self.refresh_todos()
        self.stack.setCurrentWidget(self.todo_page)      

    def save_edited_todo(self):
        
        new_todo = self.new_todo.text().strip()

        if not new_todo:
            self.save_button_todo.setText("Enter To-Do Field!!")
            QTimer.singleShot(2000, lambda: hasattr(self, "save_button_todo") and self.save_button_todo.setText("Save📁"))
            return
        
        self.todos_list[self.current_todo_index]["title"] = new_todo

        self.save_todo_file()
        self.refresh_todos()
        self.open_todo_list_page()

    def delete_todo(self):
        i = self.current_todo_index
        
        del self.todos_list[i]
        self.save_todo_file()
        self.refresh_todos()
        self.open_todo_list_page()

    def build_add_todos_page(self):
        if hasattr(self, "add_todo_page"):
            self.stack.setCurrentWidget(self.add_todo_page)
            return

        self.add_todo_page = QWidget()
        self.add_todo_layout = QVBoxLayout(self.add_todo_page)

        container = QWidget()
        container.setFixedWidth(1000)
        container_layout = QVBoxLayout(container)    

        self.back_button_add_todo = QPushButton("Back⬅️")
        self.back_button_add_todo.clicked.connect(self.open_todo_list_page)
        self.back_button_add_todo.setObjectName("back_button_add_todo")

        todo_input = QLabel("Enter To-Do Title")
        self.todo  = QLineEdit()
        self.todo.setPlaceholderText("Ex:Buying Groceries")

        todo_input.setStyleSheet("""
                            font-size : 40px;
                            font-family : Segoe UI;
                            font-weight : bold;
                            color : lime;
                            background-color : rgba(0, 0, 0, 0.3);
                            border : 5px solid black;
                            border-radius : 10px;
                            """)

        hbox1 = QHBoxLayout()
        hbox1.addWidget(todo_input)
        hbox1.addWidget(self.todo)

        self.confirm_todo = QPushButton("Add➕")
        self.confirm_todo.setObjectName("confirm_todo")
        self.confirm_todo.clicked.connect(self.add_todos)

        container_layout.addWidget(self.back_button_add_todo)
        container_layout.addLayout(hbox1)
        container_layout.addWidget(self.confirm_todo)

        self.add_todo_layout.addWidget(container, alignment= Qt.AlignCenter)

    def open_add_todo(self):
        if self.add_todo_page not in [self.stack.widget(i) for i in range(self.stack.count())]:
            self.stack.addWidget(self.add_todo_page)

        self.stack.setCurrentWidget(self.add_todo_page)

        if hasattr(self, "header"):
            self.header.setText("Add To-Dos")       

    def add_todos(self):

        todo_title = self.todo.text().strip()

        if not todo_title:
            self.confirm_todo.setText("Enter To-Do Field!!")
            QTimer.singleShot(2000, lambda: hasattr(self, "confirm_todo") and self.confirm_todo.setText("➕"))  
            return

        todo = {
            "title" : todo_title,
            "status" : False
        }

        self.todos_list.append(todo)

        self.save_todo_file()
        self.todo.clear()

        self.confirm_todo.setText("Saved✅")
        QTimer.singleShot(2000, lambda: hasattr(self, "confirm_todo") and self.confirm_todo.setText("➕"))
    
    def build_add_task_page(self):
        if hasattr(self, "add_page"):
            self.stack.setCurrentWidget(self.add_page)
            return
        
        self.add_page = QWidget()
        self.add_layout = QVBoxLayout(self.add_page)
        self.add_layout.setContentsMargins(0, 0, 0, 0)

        self.container_add = QWidget()
        self.container_add.setFixedWidth(1000)
        container_layout = QVBoxLayout(self.container_add)
        container_layout.setContentsMargins(0, 0, 0, 0)

        self.back_button_add = QPushButton("Back⬅️")
        self.back_button_add.setObjectName("back_button_add")
        self.back_button_add.clicked.connect(self.back_to_menu)

        container_layout.addWidget(self.back_button_add)

        hbox1 = QHBoxLayout()
        hbox2 = QHBoxLayout()  

        self.title_input = QLabel("Enter Task's Title")

        self.title = QLineEdit()
        self.title.setPlaceholderText("Ex:Math's assignment")
        self.title.setObjectName("task")

        self.deadline_input = QLabel("Set Task's Deadline")
     
        self.deadline = QLineEdit()
        self.deadline.setPlaceholderText("Ex:02-02-2026")
        self.deadline.setObjectName("deadline")

        self.confirm = QPushButton("Add➕")
        self.confirm.setObjectName("confirm")
        self.confirm.clicked.connect(self.add_task)

        for x in (self.title_input, self.deadline_input):
            x.setStyleSheet("""
                            font-size : 40px;
                            font-family : Segoe UI;
                            font-weight : bold;
                            color : lime;
                            background-color : rgba(0, 0, 0, 0.3);
                            border : 5px solid black;
                            border-radius : 10px;
                            """)

        self.title_input.setFixedWidth(390)    

        hbox1.addWidget(self.title_input)
        hbox1.addWidget(self.title)

        hbox2.addWidget(self.deadline_input)
        hbox2.addWidget(self.deadline)

        container_layout.addLayout(hbox1)
        container_layout.addLayout(hbox2)
        container_layout.addWidget(self.confirm)

        self.add_layout.addWidget(self.container_add, alignment=Qt.AlignCenter)

    def open_add_task_page(self):
        if self.add_page not in [self.stack.widget(i) for i in range(self.stack.count())]:
            self.stack.addWidget(self.add_page)

        self.stack.setCurrentWidget(self.add_page)

        if hasattr(self, "header"):
            self.header.setText("Add Task")

    def add_task(self):

        title = self.title.text().strip()
        deadline = self.deadline.text().strip()

        if not title or not deadline:
            self.confirm.setText("Enter All Fields!!")
            QTimer.singleShot(2000,lambda: hasattr(self, "confirm") and self.confirm.setText("➕"))
            return
            
        if not self.valid_date(deadline):
            self.confirm.setText("Invalid Format!!(Use DD-MM-YYYY)")
            QTimer.singleShot(2000,lambda: hasattr(self, "confirm") and self.confirm.setText("➕"))
            return

        task = {
            "title" : title,
            "deadline" : deadline,
            "completed" : False,
            "priority" : False,
            "order" : len(self.tasks)
        }
        self.tasks.append(task)

        self.save_task_file()
        self.title.clear()
        self.deadline.clear()

        self.confirm.setText("Saved✅")
        QTimer.singleShot(2000,lambda: hasattr(self, "confirm") and self.confirm.setText("➕"))

    def valid_date(self,date):
        try:
            datetime.datetime.strptime(date,"%d-%m-%Y")   
            return True
        except ValueError:
            return False     
            
    def back_to_menu(self,*_):
        self.stack.setCurrentWidget(self.menu)
        if hasattr(self, "header"):
            self.header.setText("Task Manager")

    def build_view_task_page(self):

        if hasattr(self, "view_page"):
            self.stack.setCurrentWidget(self.view_page)
            return
            
        self.view_page = QWidget()
        self.view_layout = QHBoxLayout(self.view_page)
        self.view_layout.setContentsMargins(0, 100, 0, 0)
        self.view_layout.addStretch()

        self.container_view = QWidget()
        self.container_view.setFixedWidth(1100)
        container_layout = QVBoxLayout(self.container_view)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(12)

        self.back_button_view = QPushButton("Back⬅️")
        self.back_button_view.setObjectName("back_button_view")
        try:
            self.back_button_view.clicked.disconnect()
        except TypeError:
            pass
        self.back_button_view.clicked.connect(self.back_to_menu)
        
        container_layout.addWidget(self.back_button_view)

        header_layout = QHBoxLayout()

        self.name_h_view = QLabel("Task")
        self.time_h_view = QLabel("Deadline")
        self.done_h_view = QLabel("Status")
        self.edit_h = QLabel("Edit")

        for x in (self.name_h_view, self.time_h_view, self.done_h_view,self.edit_h):
            x.setStyleSheet("""
                            background-color : rgba(0, 255, 0, 0.4);
                            font-size: 34px; font-family : Segoe UI; 
                            font-weight: bold; color: black;
                            border : 8px solid black;
                            """)
            x.setAlignment(Qt.AlignCenter)
            x.setFixedWidth(250)
            
            header_layout.addWidget(x)  
        
        container_layout.addLayout(header_layout)

        self.scroll_view = QScrollArea()
        self.scroll_view.setWidgetResizable(True)
        self.scroll_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scroll_view.setStyleSheet("""
                    QScrollArea {
                        background: transparent;
                        border: none;
                    }
                    QScrollArea > QWidget > QWidget {
                        background: transparent;
                    }
                    QScrollBar:vertical {
                        width: 10px;
                        background: transparent;
                    }
                    QScrollBar::handle:vertical {
                        background: rgba(255,255,255,0.4);
                        border-radius: 5px;
                    }
                """)
        
        self.scroll_content_view = QWidget()
        self.scroll_layout_view = QVBoxLayout(self.scroll_content_view)
        self.scroll_layout_view.setAlignment(Qt.AlignTop)
        self.scroll_layout_view.setContentsMargins(0, 0, 0, 0)  
        self.scroll_layout_view.setSpacing(12)
        
        self.scroll_view.setWidget(self.scroll_content_view)

        container_layout.addWidget(self.scroll_view)

        self.view_layout.addWidget(self.container_view)
        self.view_layout.addStretch() 

    def open_view_task_page(self):
        if self.view_page not in [self.stack.widget(i) for i in range(self.stack.count())]:
            self.stack.addWidget(self.view_page)     

        self.refresh_tasks()
        self.stack.setCurrentWidget(self.view_page)

        if hasattr(self, "header"):
            self.header.setText("View Tasks")

        if not self.tasks:
            self.name_h_view.setText("No")
            self.time_h_view.setText("Tasks")    
            self.done_h_view.setText("Added")
            self.edit_h.hide()  
        else:
            self.name_h_view.setText("Task")
            self.time_h_view.setText("Deadline")    
            self.done_h_view.setText("Status")
            self.edit_h.show()       

    def refresh_tasks(self):
        self.clear_layout(self.scroll_layout_view)  

        self.edit_buttons.clear()

        self.scroll_layout_view.setSpacing(12)

        for index,task in enumerate(self.tasks):
            
            try:
                task_date = datetime.datetime.strptime(task["deadline"],"%d-%m-%Y").date()
            except ValueError:
                task_date = None

            today = datetime.date.today()

            if task_date and not task["completed"] :
                days_left = (task_date - today).days
                
                if days_left < 0:
                    color = "red"
                    text  = f"Deadline: {task['deadline']}\nOverdue by {abs(days_left)} days!!"
                elif days_left == 0:
                    color = "orange"
                    text  = f"Deadline: {task['deadline']}\nDue Today!!"   
                elif days_left <= 2:
                    color = "yellow"
                    text  = f"Deadline: {task['deadline']}\nDue in {days_left} days"
                else:
                    color = "white" 
                    text  = f"Deadline: {task['deadline']}\nTime Remaining:\n {days_left} days"       
            else:
                color = "lime"
                text  = f"Deadline: {task['deadline']}\nTask Completed✅"    

            row = QWidget()    
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(7, 7, 7, 7)

            title = QLabel(task["title"])
            deadline = QLabel(text)
            status = QLabel("✅" if task["completed"] else "❌")
            edit = QPushButton("📝")
            
            edit.clicked.connect(partial(self.open_edit_task_page, index))
            self.edit_buttons.append(edit)    

            if task["priority"]:
                row.setStyleSheet("""
                                  QWidget{
                                  background-color : rgba(255, 215, 0, 0.7);
                                  border : 2px solid gold;
                                  border-radius : 10px;
                                  }""")
            else:
                row.setStyleSheet("""
                                  QWidget{
                                  background-color : rgba(0, 0, 0, 0.5);
                                  }""")

            for w in (title, deadline, status):
                w.setStyleSheet(f"font-size: 33px; border: 2px solid white; border-radius : 10px; color: {color};font-family : Segoe UI;font-weight: bold;background-color : rgba(0, 0, 0, 0.5);")
                w.setAlignment(Qt.AlignCenter)

            deadline.setStyleSheet(f"border-radius : 10px; font-size: 23px; border: 2px solid white; color: {color};font-family : Segoe UI;font-weight: bold; background-color : rgba(0, 0, 0, 0.5);")    
            
            edit.setStyleSheet("font-size: 90px;font-family : Segoe UI;font-weight: bold;background-color : rgba(31, 41, 51, 0.9); border-radius : 10px; border : 2px solid white;")
            

            row_layout.addWidget(title)
            row_layout.addWidget(deadline)
            row_layout.addWidget(status)
            row_layout.addWidget(edit)

            self.scroll_layout_view.addWidget(row) 

        self.scroll_layout_view.addStretch()         

    def build_edit_task_page(self):

        if hasattr(self, "edit_page"):
            self.stack.setCurrentWidget(self.edit_page)
            return

        self.edit_page = QWidget()
        self.edit_layout = QVBoxLayout(self.edit_page)

        container = QWidget(self.edit_page)
        container.setFixedWidth(900)
        container_layout = QVBoxLayout(container)

        self.back_button_edit = QPushButton("Back⬅️")
        self.back_button_edit.setObjectName("back_button_edit")
        self.back_button_edit.clicked.connect(self.open_view_task_page)

        title_label = QLabel("Enter New Title")
        self.edit_title = QLineEdit()

        deadline_label = QLabel("Enter New Deadline")
        self.edit_deadline = QLineEdit() 

        self.delete_button = QPushButton("Delete Task ❌")
        self.delete_button.setObjectName("delete_button")
        self.delete_button.clicked.connect(self.confirm_delete_message)

        self.save_button = QPushButton("Save📁")
        self.save_button.setObjectName("save_button")
        self.save_button.clicked.connect(self.save_edited_task)
   
        for x in (title_label, deadline_label):  
            x.setStyleSheet("""
                            font-size : 40px;
                            font-family : Segoe UI;
                            font-weight : bold;
                            color : lime;
                            background-color : rgba(0, 0, 0, 0.3);
                            border : 5px solid black;
                            border-radius : 10px;
                            """)
        title_label.setFixedWidth(405)   

        hbox1 = QHBoxLayout()
        hbox2 = QHBoxLayout()

        hbox1.addWidget(title_label)
        hbox1.addWidget(self.edit_title)

        hbox2.addWidget(deadline_label)
        hbox2.addWidget(self.edit_deadline) 
            
        container_layout.addWidget(self.back_button_edit)
        container_layout.addLayout(hbox1)
        container_layout.addLayout(hbox2)
        container_layout.addWidget(self.save_button)
        container_layout.addWidget(self.delete_button)

        self.edit_layout.addWidget(container, alignment=Qt.AlignCenter)

    def confirm_delete_message(self):

        message = QMessageBox()
        message.setWindowTitle("Confirm Deletion")
        message.setText("Are you sure you want to delete this task?")
        message.setIcon(QMessageBox.Warning)    

        message.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        message.setStyleSheet("""
                QMessageBox {
                    background-color: #222;
                }

                QMessageBox QLabel {
                    color: white;
                    font-size: 22px;
                    font-family: Segoe UI;
                }

                QMessageBox QPushButton {
                    background-color: #444;
                    color: lime;
                    border: 2px solid yellow;
                    border-radius: 10px;
                    padding: 8px;
                    font-size: 20px;
                    font-weight: bold;
                    margin-right : 120px;
                }
                            """)

        result = message.exec_()

        if result == QMessageBox.Yes:
            self.delete_task_index()

    def open_edit_task_page(self, index):
        if index < 0 or index >= len(self.tasks):
            return

        self.current_task_index = index

        self.edit_title.setText(self.tasks[index]["title"])
        self.edit_deadline.setText(self.tasks[index]["deadline"])

        if self.edit_page not in [self.stack.widget(i) for i in range(self.stack.count())]:
            self.stack.addWidget(self.edit_page)

        self.stack.setCurrentWidget(self.edit_page)

        if hasattr(self, "header"):
            self.header.setText("Edit Task")

    def save_edited_task(self):
        new_title = self.edit_title.text().strip()
        new_deadline = self.edit_deadline.text().strip()   

        if not new_title or not new_deadline:
            self.save_button.setText("Enter All Fields!!")
            QTimer.singleShot(2000,lambda: hasattr(self, "save_button") and self.save_button.setText("Save📁"))
            return
            
        if not self.valid_date(new_deadline):
            self.save_button.setText("Invalid Format!!(Use DD-MM-YYYY)")
            QTimer.singleShot(2000,lambda: hasattr(self, "save_button") and self.save_button.setText("Save📁"))
            return
        
        self.tasks[self.current_task_index]["title"] = new_title
        self.tasks[self.current_task_index]["deadline"] = new_deadline
        
        self.save_task_file()
        self.refresh_tasks()
        self.open_view_task_page()
               
    def build_complete_task_page(self):

        if hasattr(self, "complete_page"):
            self.stack.setCurrentWidget(self.complete_page)
            return

        self.complete_page = QWidget()
        self.complete_layout =  QHBoxLayout(self.complete_page)
        self.complete_layout.setContentsMargins(0, 110, 0, 0)
        self.complete_layout.addStretch()

        self.container_complete = QWidget()
        self.container_complete.setFixedWidth(950)
        container_layout = QVBoxLayout(self.container_complete)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(12)

        self.back_button_complete = QPushButton("Back⬅️")   
        self.back_button_complete.setObjectName("back_button_complete")
        self.back_button_complete.clicked.connect(self.back_to_menu) 

        container_layout.addWidget(self.back_button_complete)

        header_layout = QHBoxLayout()

        self.name_h_comp = QLabel("Task")
        self.status_h_comp = QLabel("Toggle Status")
        self.priority_h_comp = QLabel("Prioritize")

        for x in (self.name_h_comp, self.status_h_comp, self.priority_h_comp):
            x.setStyleSheet("""
                            background-color : rgba(0, 255, 0, 0.4);
                            font-size: 34px; font-family : Segoe UI; 
                            font-weight: bold; color: black;
                            border : 8px solid black;
                            """)
            x.setAlignment(Qt.AlignCenter)
            header_layout.addWidget(x)

        container_layout.addLayout(header_layout)

        self.scroll_complete = QScrollArea()
        self.scroll_complete.setWidgetResizable(True)
        self.scroll_complete.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.scroll_complete.setStyleSheet("""
                    QScrollArea {
                        background: transparent;
                        border: none;
                    }
                    QScrollArea > QWidget > QWidget {
                        background: transparent;
                    }
                    QScrollBar:vertical {
                        width: 10px;
                        background: transparent;
                    }
                    QScrollBar::handle:vertical {
                        background: rgba(255,255,255,0.4);
                        border-radius: 5px;
                    }
                """)
        
        self.scroll_content_complete = QWidget()
        self.scroll_layout_complete = QVBoxLayout(self.scroll_content_complete)
        self.scroll_layout_complete.setAlignment(Qt.AlignTop)
        self.scroll_layout_complete.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout_complete.setSpacing(20)

        self.scroll_complete.setWidget(self.scroll_content_complete)

        container_layout.addWidget(self.scroll_complete)

        self.complete_layout.addWidget(self.container_complete)
        self.complete_layout.addStretch()            

    def open_complete_task_page(self):
        if self.complete_page not in [self.stack.widget(i) for i in range(self.stack.count())]:
            self.stack.addWidget(self.complete_page)

        self.refresh_comp_tasks()
        self.stack.setCurrentWidget(self.complete_page)

        if hasattr(self, "header"):
            self.header.setText("Complete Tasks")

        if not self.tasks:
            self.name_h_comp.setText(  "No" )
            self.status_h_comp.setText("Tasks")    
            self.priority_h_comp.setText("Added")  

        else:
            self.name_h_comp.setText(  "Task" )
            self.status_h_comp.setText("Toggle Status")    
            self.priority_h_comp.setText( "Prioritize" )      

    def refresh_comp_tasks(self):
        self.clear_layout(self.scroll_layout_complete)   

        self.scroll_layout_complete.setSpacing(20)

        for index, task in enumerate(self.tasks):

            row = QWidget()
            row.setFixedHeight(80)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(4, 4, 4, 4)
            row_layout.setSpacing(7)

            title = QLabel(task["title"])
            title.setFixedHeight(60)

            status = QPushButton("✅" if task["completed"] else "❌")
            priority = QPushButton("💡" if task["priority"] else "⭕")
            priority.setCheckable(True)
            priority.setObjectName("priorityBtn")

            status.clicked.connect(partial(self.toggle_status_task, index, status))
            priority.toggled.connect(lambda checked, t=task: self.set_priority(t))

            try:
                task_date = datetime.datetime.strptime(task["deadline"],"%d-%m-%Y").date()
            except ValueError:
                task_date = None

            today = datetime.date.today()    

            if task_date and not task["completed"] :
                border = "red"
                days_left = (task_date - today).days
                
                if days_left < 0:
                    color = "red"
                elif days_left <= 2:
                    color = "yellow"
                else:
                    color = "white"        
            else:
                color = "lime" 
                border = "lime"   

            if task["priority"]:
                row.setStyleSheet("""
                                  QWidget{
                                  background-color : rgba(255, 215, 0, 0.4);
                                  border : 3px solid gold;
                                  border-radius : 10px;
                                  }""")
            else:
                row.setStyleSheet("""
                                  QWidget{
                                  background-color : rgba(0, 0, 0, 0.5);
                                  }""")    

            title   .setStyleSheet(f"font-size: 33px; border : 2px solid white; border-radius : 10px; color: {color};font-family : Segoe UI;font-weight: bold; background-color : rgba(0, 0, 0, 0.5);")
            status  .setStyleSheet(f"font-size: 28px; border : 4px solid {border}; border-radius : 10px; background-color : rgba(0, 0, 0, 0.5);")
            priority.setStyleSheet("""
                                QPushButton#priorityBtn {
                                background-color : rgba(0, 0, 0, 0.5);
                                font-size: 28px;   
                                border-radius : 10px;   
                                border : 4px solid gold;   
                                }
                                """)

            title.   setAlignment(Qt.AlignCenter)
       
            row_layout.addWidget(  title )
            row_layout.addWidget( status )
            row_layout.addWidget(priority)

            self.scroll_layout_complete.addWidget(row)

        self.scroll_layout_complete.addStretch()      

    def sort_tasks(self):
        prioritized = [x for x in self.tasks if x["priority"]]
        normal      = [x for x in self.tasks if not x["priority"]]

        prioritized.sort(key=lambda x: x["order"])         
        normal.sort(key=lambda x: x["order"])

        self.tasks = prioritized + normal

    def set_priority(self, task):

        task["priority"] = not task["priority"]

           
        self.save_task_file()
        self.refresh_comp_tasks()

    def toggle_status_task(self,i, button):
        if i < 0 or i >= len(self.tasks):
            return
        
        self.tasks[i]["completed"] = not self.tasks[i]["completed"]

        if self.tasks[i]["completed"] :   
            button.setText("✅")
        else:
            button.setText("❌")   

        self.save_task_file()
        self.refresh_comp_tasks()
        self.open_complete_task_page()
                   
    def delete_task_index(self):
        index = self.current_task_index
        
        del self.tasks[index]
        self.save_task_file()
        self.refresh_tasks()
        self.open_view_task_page()
 
    def resizeEvent(self, event):
        if hasattr(self, "header"):
            self.header.setGeometry(0, 0, self.width(), 100)

        if hasattr(self, "bg"):
            self.bg.setGeometry(self.rect())

        x = 20
        y = self.height() - self.cloud_status.height() - 90  

        self.cloud_status.adjustSize()

        self.cloud_status.move(x, y) 

        super().resizeEvent(event)

    def save_todo_file(self):
        with open("todos.json", "w") as f:
            json.dump(self.todos_list, f, indent=4)

        self.cloud_dirty = True

        if not (self.firebase_ready and self.online):
            self.set_cloud_status("offline")
            return
        
        self.set_cloud_status("syncing")

        todos_snapshot = copy.deepcopy(self.todos_list)

        self.todo_upload_thread = UploadThread(
            todos_snapshot, "todos", self.db, self.user_id
        )

        self.todo_upload_thread.finished_upload.connect(self.on_upload_finished)
        self.todo_upload_thread.start()

    def save_task_file(self):
        self.sort_tasks()

        with open("tasks.json", "w") as f:
            json.dump(self.tasks, f, indent=4)

        self.cloud_dirty = True

        if not (self.firebase_ready and self.online):
            self.set_cloud_status("offline")
            return
        
        self.set_cloud_status("syncing")

        tasks_snapshot = copy.deepcopy(self.tasks)

        self.upload_thread = UploadThread(
            tasks_snapshot, "tasks", self.db, self.user_id
        )    
        self.upload_thread.finished_upload.connect(self.on_upload_finished)
        self.upload_thread.start()

    def upload_tasks_to_firebase(self, tasks_snapshot):
        if not hasattr(self, "db") or self.db is None:
            QTimer.singleShot(0, lambda: self.set_cloud_status("offline"))
            return
        
        try:
            tasks_ref = (
                self.db.collection("users")
                .document(self.user_id)
                .collection("tasks")
            )   

            for doc in tasks_ref.stream():
                doc.reference.delete()

            for task in tasks_snapshot:
                tasks_ref.add(task)

            self.cloud_dirty = False
            self.set_cloud_status("synced")

        except Exception:
            self.set_cloud_status("offline")

    def upload_todos_to_firebase(self, todos_snapshot):
        if not hasattr(self, "db") or self.db is None:
            QTimer.singleShot(0, lambda: self.set_cloud_status("offline"))
            return
        
        try:
            todos_ref = (
                self.db.collection("users")
                .document(self.user_id)
                .collection("todos")
            )    

            for doc in todos_ref.stream():
                doc.reference.delete()

            for todo in todos_snapshot:
                todos_ref.add(todo)

            self.cloud_dirty = False 
            self.set_cloud_status("synced")

        except Exception:
            self.set_cloud_status("offline")      

    def on_upload_finished(self, ok):
        if ok:
            self.cloud_dirty = False
            self.set_cloud_status("synced")
        else:
            self.set_cloud_status("offline")    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
