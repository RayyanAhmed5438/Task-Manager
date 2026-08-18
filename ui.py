
import datetime


from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel,
    QVBoxLayout,  QPushButton,
    
)
from PyQt5.QtCore import  QTime, Qt

class UiMixin:
    def update_time(self):
        if hasattr(self, "time_label"):
            current_time = QTime.currentTime().toString("hh:mm:ss AP")
            self.time_label.setText(current_time)    

        if hasattr(self, "date_label"):
            today = datetime.date.today().strftime("%d-%m-%Y")
            self.date_label.setText(str(today))

    def menu_page(self):
        self.menu = QWidget()

        vbox = QVBoxLayout(self.menu)
        vbox.setContentsMargins(0, 110, 0, 0)

        container_layout = QVBoxLayout()

        self.time_label  = QLabel()      
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
        vbox.setAlignment(Qt.AlignCenter)
        

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

        QToolTip {
        font-size: 28px;
        font-family: Segoe UI;
        color: white;
        background-color: rgba(0, 0, 0, 0.85);
        border: 2px solid white;
        border-radius: 8px;
        padding: 8px;
        }
        
        QPushButton#addtask, #confirm_conflict, #confirm_todo,
        #delete_button_todo, #save_button_todo, #add_todos_button,
        #delete_button, #save_button, #viewtask, #completetask,
        #exit, #confirm{
        font-size : 40px;
        font-family : Segoe UI;
        font-weight : 600;
        border : 4px solid yellow;
        border-radius : 20px;
        margin : 20px;
        padding : 10px;
        background-color : rgba(31, 41, 51, 0.6);
        color : lime;
        }

        QPushButton#addtask:hover, #confirm_conflict:hover,
        #confirm_todo:hover, #delete_button_todo:hover, 
        #save_button_todo:hover, #add_todos_button:hover,
        #delete_button:hover, #save_button:hover, #viewtask:hover,
        #completetask:hover, #exit:hover, #confirm:hover{

        border : 10px solid yellow;
        border-radius : 20px;
        background-color : rgba(40, 40, 40, 1);
       
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

        QPushButton#back_button_edit_todo:hover,
        #back_button_add_todo:hover, #back_button_todo:hover,
        #back_button_view:hover,#back_button_add:hover,
        #back_button_complete:hover,#back_button_edit:hover{
        font-size : 40px;
        font-family : Segoe UI Emoji;
        border : 10px solid black;
        border-radius : 20px;
        background-color : rgba(0, 120, 255, 1);
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

        QLineEdit:hover{
        background-color:rgba(255, 255, 255, 0.2);
        border : 5px solid black;
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

       QPushButton#todolist:hover{
        font-size : 40px;
        font-family : Segoe UI;
        border : 10px solid yellow;
        border-radius : 20px;
        margin : 10px;
        padding : 10px;
        background-color : grey;
        color : yellow;
       }

        """

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

            elif item.layout():
                self.clear_layout(item.layout())    

    def back_to_menu(self,*_):
        self.stack.setCurrentWidget(self.menu)
        if hasattr(self, "header"):
            self.header.setText("Task Manager")

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
