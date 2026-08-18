

import os

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


class TodosMixin:
    def load_todos(self):
        file_path       = "todos.json"
        self.todos_list = []

        try:        
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    self.todos_list = json.load(f)  

        except Exception:
            self.todos_list = []                                           

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

    def build_todo_list_page(self):

        if hasattr(self, "todo_page"):
            self.stack.setCurrentWidget(self.todo_page)
            return

        self.todo_page   = QWidget()
        self.todo_layout = QHBoxLayout(self.todo_page)
        self.todo_layout .setContentsMargins(0, 100, 0 ,0)
        self.todo_layout .addStretch()

        self.container_todo = QWidget()
        self.container_todo .setFixedWidth(950)
        container_layout    = QVBoxLayout(self.container_todo)
        container_layout    .setContentsMargins(0, 0, 0, 0)
        container_layout    .setSpacing(12)

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

    def refresh_todos(self):
        self.clear_layout(self.scroll_layout_todo) 

        self.scroll_layout_todo.setSpacing(20) 

        for index, todo in enumerate(self.todos_list):
            row = QWidget()
            row.setFixedHeight(80)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(4, 4, 4, 4)
            row_layout.setSpacing(6)

            name = QLabel()
            name.setObjectName("name_todo")
            name.setMouseTracking(True)
            text = f"{index+1}. {todo['title']}"

            status = QPushButton("✅" if todo["status"] else "❌")
            status.setObjectName("status_todo")

            edit = QPushButton("📝")
            edit.setObjectName("edit_todo")

            name.setFixedHeight(70)
            name.setFixedWidth(310)
            name.adjustSize()

            status.setFixedHeight(70)
            edit.setFixedHeight(70)

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

            name.setStyleSheet(f"""
                QLabel#name_todo {{
                    font-size: 33px;
                    border: 2px solid white;
                    border-radius: 10px;
                    color: {color};
                    font-family: Segoe UI;
                    font-weight: bold;
                    background-color: rgba(0, 0, 0, 0.5);
                    padding-left: 6px;
                }}

                QLabel#name_todo:hover {{
                    background-color:rgba(255, 255, 255, 0.2);
                }}
            """) 

            name.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            name.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

            name.   setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            fm = name.fontMetrics()
            elided = fm.elidedText(text, Qt.ElideRight, name.width())
            
            name.setText(elided)
            name.setToolTip(text)
            name.setCursor(Qt.PointingHandCursor) 

            name.enterEvent = lambda e, t=name: QToolTip.showText(
                t.mapToGlobal(t.rect().bottomLeft()),
                t.toolTip(),
                t
            )
            name.leaveEvent = lambda e: QToolTip.hideText() 

            status.setStyleSheet(f"""QPushButton#status_todo{{
                                font-size: 28px; border : 4px solid {border};
                                border-radius : 10px;
                                background-color : rgba(0, 0, 0, 0.5);
                                }}
                                
                                QPushButton#status_todo:hover{{
                                    background-color:rgba(255, 255, 255, 0.2);
                                }}
                                
                                """)


            edit.setStyleSheet("""QPushButton#edit_todo{font-size: 28px; border-radius : 10px;
                                background-color : rgba(31, 41, 51, 0.8);
                                border : 4px solid white;
                               }
                                QPushButton#edit_todo:hover{
                                    background-color:rgba(255, 255, 255, 0.2);
                               }
                               """)



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
        if not hasattr(self, "current_todo_index"):
            return
        
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
            "id" : str(uuid.uuid4()),
            "title" : todo_title,
            "status" : False
        }

        self.todos_list.append(todo)

        self.save_todo_file()
        self.todo.clear()

        self.confirm_todo.setText("Saved✅")
        QTimer.singleShot(2000, lambda: hasattr(self, "confirm_todo") and self.confirm_todo.setText("➕"))
