

import os


import firebase_admin
from firebase_admin import credentials, firestore

from PyQt5.QtWidgets import (
    QWidget, QLabel,
    QVBoxLayout, QHBoxLayout, QPushButton,
    QRadioButton, QButtonGroup
    
)
from PyQt5.QtCore import QTimer, Qt

from firebase_threads import FirebaseCheckThread

class SyncMixin:
    def start_auto_reconnect(self):
        self.reconnect_timer = QTimer(self)
        self.reconnect_timer.timeout.connect(self.try_firebase_reconnect)
        self.reconnect_timer.start(5000)

        self.net_manager.onlineStateChanged.connect(self.on_internet_state_changed)

    def on_internet_state_changed(self, is_online):    
        if not is_online:
            return
        
        if not hasattr(self, "db"):
            return
        
        self.run_firebase_check()

    def try_firebase_reconnect(self):

        if not self.net_manager.isOnline():
            return

        if not hasattr(self, "db") or self.db is None:  
            self.init_firebase()
            return
        
        if self.firebase_thread and self.firebase_thread.isRunning():
            return
        
        if not self.online:
            self.run_firebase_check()
            return
        
        self.set_cloud_status("synced")
        if hasattr(self, "reconnect_timer"):
            self.reconnect_timer.stop()

    def run_firebase_check(self):

        if self.firebase_thread and self.firebase_thread.isRunning():
            return

        self.firebase_thread = FirebaseCheckThread(self.db)
        self.firebase_thread.result.connect(self.on_firebase_checked)
        self.firebase_thread.finished.connect(self.on_firebase_thread_finished)
        self.firebase_thread.start()     

    def on_firebase_thread_finished(self):
        self.firebase_thread.deleteLater()
        self.firebase_thread = None    

    def set_cloud_status_instant(self, is_online):
        self.online = is_online

        if not is_online:
            self.set_cloud_status("offline")  
        else:
            self.try_firebase_reconnect()    

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
            self.key_missing    = True
            self.firebase_ready = False
            self.online         = False
            self.set_cloud_status("offline")
            return

        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate("firebase_key.json")
                firebase_admin.initialize_app(cred)

            self.db = firestore.client()
            self.firebase_ready = True

            self.run_firebase_check()

        except Exception as e:
            print("Firebase init failed: ", e)
            self.firebase_ready = False    
            self.online         = False
            self.set_cloud_status("offline")

    def on_firebase_checked(self, connected):
         
        self.online = connected  

        if not connected:
            self.set_cloud_status("offline")
            return
        
        cloud_tasks = self.get_cloud_tasks()
        cloud_todos = self.get_cloud_todos()

        cloud_task_ids = {t["id"] for t in cloud_tasks}
        local_task_ids = {t["id"] for t in self.tasks}

        cloud_todo_ids = {t["id"] for t in cloud_todos}
        local_todo_ids = {t["id"] for t in self.todos_list}

        if (cloud_task_ids != local_task_ids) or (cloud_todo_ids != local_todo_ids):
            
            if not hasattr(self, "sync_conflict_page"):
                self.build_sync_conflict_page()

            self.stack.setCurrentWidget(self.sync_conflict_page)
            return    
        
        self.set_cloud_status("synced")

    def build_sync_conflict_page(self):

        cloud_tasks = self.get_cloud_tasks()
        cloud_todos = self.get_cloud_todos()

        self.sync_conflict_page = QWidget()         
        layout                  = QVBoxLayout(self.sync_conflict_page)

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
        else:
            local_ids  = {t["id"] for t in self.tasks}
            self.delete_missing_cloud_docs("tasks", local_ids)    

        if self.todo_radio_cloud.isChecked():
            self.todos_list = cloud_todos 
        else:
            local_ids  = {t["id"] for t in self.todos_list}
            self.delete_missing_cloud_docs("todos", local_ids)    

        self.task_radio_cloud.setChecked(False)       
        self.task_radio_local.setChecked(False)
        self.todo_radio_cloud.setChecked(False)
        self.todo_radio_local.setChecked(False)

        self.save_task_file()
        self.save_todo_file()

        self.back_to_menu()

    def set_cloud_status(self, state):

        if not hasattr(self, "cloud_status"):
            return

        if state == "synced":
            self.cloud_status.setText("☁ Cloud:\n   Synced")
            self.cloud_status.setToolTip("Synced with firestore")
            self.cloud_status.setStyleSheet("""
                QLabel#cloud_status {
                    font-size: 35px;
                    padding: 6px 12px;
                    background-color: rgba(0, 120, 0, 1);
                    border-radius: 8px;
                    color: white;
                }

                QLabel#cloud_status:hover{
                    background-color: rgba(0, 120, 0, 0.5);
                }                            
                                                                        
            """)

        elif state == "syncing":
            self.cloud_status.setText("☁ Cloud:\n   Syncing…")
            self.cloud_status.setToolTip("Syncing with firestore...")
            self.cloud_status.setStyleSheet("""
                QLabel#cloud_status {
                    font-size: 35px;
                    padding: 6px 12px;
                    background-color: rgba(180, 140, 0, 1);
                    border-radius: 8px;
                    color: black;
                }
                                            
                QLabel#cloud_status:hover{
                    background-color: rgba(180, 140, 0, 0.6);
                }    

            """)

        else:
            self.cloud_status.setText("☁ Cloud:\n   Offline")
            if self.key_missing:
                self.cloud_status.setToolTip("Firebase Key missing - Running Offline")
            elif not self.net_manager.isOnline():
                self.cloud_status.setToolTip("No Internet Connection")
            
            self.cloud_status.setStyleSheet("""
                QLabel#cloud_status {
                    font-size: 35px;
                    padding: 6px 12px;
                    background-color: rgba(150, 0, 0, 1);
                    border-radius: 8px;
                    color: white;
                }
                                            
                QLabel#cloud_status:hover{
                    background-color: rgba(150, 0, 0, 0.6);
                }    
            """)
