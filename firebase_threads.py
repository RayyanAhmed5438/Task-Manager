
from PyQt5.QtCore import QThread, pyqtSignal
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
        self.type     = upload_type
        self.db       = db
        self.user_id  = user_id

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

            for item in self.snapshot:

                if not self.net_manager.isOnline():
                    print("Upload aborted - No Internet")
                    self.finished_upload.emit(False)
                    return

                ref.document(item["id"]).set(item)

            if self.net_manager.isOnline():
                self.finished_upload.emit(True)    

            else:
                self.finished_upload.emit(False)    

        except Exception:
            self.finished_upload.emit(False)            
