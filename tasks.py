
import os
import datetime
import json
import uuid
from functools import partial


from PyQt5.QtWidgets import (
     QWidget, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QPushButton,
     QScrollArea, QMessageBox,
     QSizePolicy,
    QToolTip
)
from PyQt5.QtCore import QTimer, Qt


class TasksMixin:
    def load_tasks(self):
        file_path  = "tasks.json"
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
            "id" : str(uuid.uuid4()),
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
                    text  = f"Deadline: {task['deadline']}\nOverdue by:\n{abs(days_left)} days!!"
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

            title = QLabel()
            title.setObjectName("title_view")
            title.setMouseTracking(True)

            deadline = QLabel(text)
            status = QLabel("✅" if task["completed"] else "❌")

            edit = QPushButton("📝")
            edit.setObjectName("edit_view")
            
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

            for w in (deadline, status):
                w.setStyleSheet(f"font-size: 33px; border: 2px solid white; border-radius : 10px; color: {color};font-family : Segoe UI;font-weight: bold;background-color : rgba(0, 0, 0, 0.5);")
                w.setAlignment(Qt.AlignCenter)

            title.setStyleSheet(f"""
                QLabel#title_view {{
                    font-size: 33px;
                    border: 2px solid white;
                    border-radius: 10px;
                    color: {color};
                    font-family: Segoe UI;
                    font-weight: bold;
                    background-color: rgba(0, 0, 0, 0.5);
                    padding-left: 6px;
                }}

                QLabel#title_view:hover {{
                    background-color:rgba(255, 255, 255, 0.2);
                }}
            """)    

            title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter) 
            title.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred) 
            title.setFixedWidth(265)
            title.adjustSize()

            text = f"{index+1}. {task['title']}"

            fm = title.fontMetrics()
            elided = fm.elidedText(text, Qt.ElideRight, title.width())
            
            title.setText(elided)
            title.setToolTip(text)
            title.setCursor(Qt.PointingHandCursor) 

            title.enterEvent = lambda e, t=title: QToolTip.showText(
                t.mapToGlobal(t.rect().bottomLeft()),
                t.toolTip(),
                t
            )
            title.leaveEvent = lambda e: QToolTip.hideText()   

            deadline.setStyleSheet(f"border-radius : 10px; font-size: 23px; border: 2px solid white; color: {color};font-family : Segoe UI;font-weight: bold; background-color : rgba(0, 0, 0, 0.5);")    

            edit.setStyleSheet("""QPushButton#edit_view{
                               font-size: 90px;font-family : Segoe UI;
                               font-weight: bold;background-color : rgba(31, 41, 51, 0.9);
                               border-radius : 10px; border : 2px solid white;
                               }
                               
                               QPushButton#edit_view:hover{
                                  background-color:rgba(255, 255, 255, 0.2);  
                               }
                               
                               """)
            

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

            title = QLabel()
            title.setObjectName("title_comp")
            title.setMouseTracking(True)
            title.setFixedHeight(70)
            title.setFixedWidth(310)
            title.adjustSize()
            text = f"{index+1}. {task['title']}"

            status = QPushButton("✅" if task["completed"] else "❌")
            status.setObjectName("status_comp")
            status.setFixedHeight(70)

            priority = QPushButton("💡" if task["priority"] else "⭕")
            priority.setFixedHeight(70)
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

            title.setStyleSheet(f"""
                QLabel#title_comp {{
                    font-size: 33px;
                    border: 2px solid white;
                    border-radius: 10px;
                    color: {color};
                    font-family: Segoe UI;
                    font-weight: bold;
                    background-color: rgba(0, 0, 0, 0.5);
                    padding-left: 6px;
                }}

                QLabel#title_comp:hover {{
                    background-color:rgba(255, 255, 255, 0.2);
                }}
            """) 

            title.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)    

            status.setStyleSheet(f"""QPushButton#status_comp{{
                                font-size: 28px; border : 4px solid {border};
                                border-radius : 10px; background-color : rgba(0, 0, 0, 0.5);
                                }}

                                QPushButton#status_comp:hover{{
                                    background-color:rgba(255, 255, 255, 0.2);
                                }} 
                                 
                                 """)
            
            
            priority.setStyleSheet("""
                                QPushButton#priorityBtn {
                                background-color : rgba(0, 0, 0, 0.5);
                                font-size: 28px;   
                                border-radius : 10px;   
                                border : 4px solid gold;   
                                }

                                QPushButton#priorityBtn:hover{
                                    background-color:rgba(255, 255, 255, 0.2);   
                                }      

                                """)

            title.   setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            fm = title.fontMetrics()
            elided = fm.elidedText(text, Qt.ElideRight, title.width())
            
            title.setText(elided)
            title.setToolTip(text)
            title.setCursor(Qt.PointingHandCursor) 

            title.enterEvent = lambda e, t=title: QToolTip.showText(
                t.mapToGlobal(t.rect().bottomLeft()),
                t.toolTip(),
                t
            )
            title.leaveEvent = lambda e: QToolTip.hideText()  
       
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
        if not hasattr(self, "current_task_index"):
            return
        
        index = self.current_task_index
        
        del self.tasks[index]
        self.save_task_file()
        self.refresh_tasks()
        self.open_view_task_page()
