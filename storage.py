
import json
import copy

from PyQt5.QtCore import QTimer

from firebase_threads import UploadThread


class StorageMixin:
    def save_todo_file(self):
        try:
            with open("todos.json", "w") as f:
                json.dump(self.todos_list, f, indent=4)

        except Exception as e:
            print("File write Failed: ", e)        

        self.cloud_dirty = True

        if not (self.firebase_ready and self.online):
            self.set_cloud_status("offline")
            return
        
        self.set_cloud_status("syncing")

        todos_snapshot = copy.deepcopy(self.todos_list)

        if self.todo_upload_thread and self.todo_upload_thread.isRunning():
            self.todo_upload_pending = True
            return

        self.todo_upload_thread = UploadThread(
            todos_snapshot, "todos", self.db, self.user_id
        )

        self.todo_upload_thread.finished_upload.connect(self.on_todo_upload_finished)
        self.todo_upload_thread.finished.connect(self.on_todo_upload_thread_finished)
        self.todo_upload_thread.start()

    def save_task_file(self):
        self.sort_tasks()

        try:
            with open("tasks.json", "w") as f:
                json.dump(self.tasks, f, indent=4)

        except Exception as e:
            print("File write failed: ", e)        

        self.cloud_dirty = True

        if not (self.firebase_ready and self.online):
            self.set_cloud_status("offline")
            return
        
        self.set_cloud_status("syncing")

        tasks_snapshot = copy.deepcopy(self.tasks)

        if self.upload_thread and self.upload_thread.isRunning():
            self.task_upload_pending = True
            return

        self.upload_thread = UploadThread(
            tasks_snapshot, "tasks", self.db, self.user_id
        )    
        self.upload_thread.finished_upload.connect(self.on_task_upload_finished)
        self.upload_thread.finished.connect(self.on_upload_thread_finished)
        self.upload_thread.start()      

    def on_task_upload_finished(self, ok):
        if ok:
            local_ids = {t["id"] for t in self.tasks}
            self.delete_missing_cloud_docs("tasks", local_ids)

            if not self.task_upload_pending:
                self.cloud_dirty = False
                self.set_cloud_status("synced")

        else:
            self.set_cloud_status("offline")   

        if self.task_upload_pending:
            self.task_upload_pending = False
            QTimer.singleShot(0, self.save_task_file) 

    def on_todo_upload_finished(self, ok):
        if ok:
            local_ids = {t["id"] for t in self.todos_list}
            self.delete_missing_cloud_docs("todos", local_ids)

            if not self.todo_upload_pending:
                self.cloud_dirty = False
                self.set_cloud_status("synced")

        else:
            self.set_cloud_status("offline")   

        if self.todo_upload_pending:
            self.todo_upload_pending = False
            QTimer.singleShot(0, self.save_todo_file)             

    def on_upload_thread_finished(self):
        if self.upload_thread:
            self.upload_thread.deleteLater()
            self.upload_thread = None

    def on_todo_upload_thread_finished(self):
        if self.todo_upload_thread:
            self.todo_upload_thread.deleteLater()
            self.todo_upload_thread = None    

    def delete_missing_cloud_docs(self, collection_name, local_ids):
        if not (self.firebase_ready and self.online):
            return
        
        ref = (
            self.db.collection("users")
            .document(self.user_id)
            .collection(collection_name)
        )

        for doc in ref.stream():
            if doc.id not in local_ids:
                doc.reference.delete()
