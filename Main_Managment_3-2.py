from PyQt5 import uic
from PyQt5.QtWidgets import QLineEdit, QMainWindow, QLabel, QApplication
# from PyQt5.QtOpenGL import QGLWidget
# import subprocess
import os
# import psutil
import pyautogui
import requests
import socket

import sys
import time
import json
import psutil 
from PyQt5 import QtCore

# import pywinauto.keyboard as keyboard


class WorkerThread(QtCore.QObject):
    def __init__(self, updateUI, school_id, start_function, download_handler, closeProgramXYZ, resetUiState, nPrinted, downloadUrl):
        super().__init__()
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.s.connect((socket.gethostname(), 1242))
        self.s.connect(("127.0.0.1", 1242))
        # self.s.sendall(b"Hello")
        self.msg = ''
        self.updateUI = updateUI

        self.is_obj_on_heat_bed = False

        self.downloadUrl = downloadUrl

        self.nPrinted = nPrinted
        self.n_loop = 0
        self.now_command = ''
        self.last_command = ''

        self.count_previous_command = 0
        self.previous_commands = []

        self.school_id = school_id
        self.is_fetch = True
        self.startFunction = start_function
        self.download3DModel = download_handler
        self.closeProgramXYZ = closeProgramXYZ
        self.is_closed_program = False
        self.resetUiState = resetUiState
        self.last_time = time.time()

    def setFetchStatus(self, status):
        self.is_fetch = status

    @QtCore.pyqtSlot()
    def run(self):
        while True:
            self.last_command = self.now_command
            self.now_command = self.msg

            self.msg = self.s.recv(1024)
            # .decode("utf-8") # รับค่า
            # print(f"---{self.msg}---")
            if self.msg == b'Busy':
                self.updateUI('Printer Busy')
            elif self.msg == b'Ready':
                self.updateUI('Printer Ready')
            elif self.msg == b'Pre-heat Extruder':
                # self.n_loop = 0  # Reset count show round to ui
                self.updateUI('Pre-heat Extrude')
                if not self.is_closed_program:
                    self.closeProgramXYZ()
                    self.is_closed_program = True
                self.setFetchStatus(status=True)
            elif self.msg == b'Printing':
                self.updateUI('Printing')
                self.n_loop += 1
            elif self.msg == b'Store Extruder':
                self.updateUI('Store Extruder')
            elif self.msg == b'Object On Heat Bed':  # Waiting user to press OK on Printer
                self.updateUI('Object On Heat Bed')
                self.is_closed_program = False
                self.is_obj_on_heat_bed = True
            elif self.msg == b'\x00':
                pass

            time_pass = time.time() - self.last_time

            if self.n_loop == 0:
                print(f"IF {self.n_loop=}")
                if self.is_fetch and self.msg == b'Ready' and time_pass > 3:

                    print("\t+ Fetching in IF")

                    response = requests.get(self.downloadUrl).json()
                    self.last_time = time.time()

                    for obj in response:
                        if obj['school_id'] == self.school_id:
                            print(f"\t+ Found match {self.school_id=}")
                            self.is_fetch = False

                            # Don't forget to reset self.is_fetch state !!! When print finish !!
                            save_path = self.download3DModel(
                                file_id=obj['file_id'], file_name=obj['file'])
                            self.n_loop += 1
                            # Status Printing is here
                            self.startFunction(
                                is_worker_handle=True, save_path=save_path)

            else:  # != 0
                print(f"ELSE {self.n_loop=}")
                # if self.last_command == b'Object On Heat Bed':
                if self.is_obj_on_heat_bed:
                    print(f"\t+ Obj on heat bed, {self.is_fetch=}, {self.msg=}")
                    
                    self.is_fetch = True
                    if self.is_fetch and self.msg == b'Ready':
                        print(f"\t+ Fetching in ELSE")
                        self.resetUiState()
                        count = int(self.nPrinted.text())+1
                        self.nPrinted.setText(str(count))

                        response = requests.get(self.downloadUrl).json()
                        self.last_time = time.time()

                        for obj in response:
                            if obj['school_id'] == self.school_id:
                                print(f"\t+ Found match {self.school_id=}")
                                self.is_fetch = False
                                self.is_obj_on_heat_bed = False

                                # Don't forget to reset self.is_fetch state !!! When print finish !!
                                save_path = self.download3DModel(
                                    file_id=obj['file_id'], file_name=obj['file'])
                                # self.n_loop += 1
                                self.startFunction(
                                    is_worker_handle=True, save_path=save_path, is_first_time=False)

            # if self.msg == b'Pre-heat Extruder':
            #     self.closeProgramXYZ()


class Ui(QMainWindow):

    def __init__(self):
        super(Ui, self).__init__()

        with open('CONFIG.json', 'r') as file:
            self.DEFAULT_CONFIG = json.load(file)

        uic.loadUi('XYZ_Print_Managment.ui', self)

        self.setWindowTitle("Tele3DPrint - FIBO - KMUTT")

        self.sc_id = self.findChild(QLabel, 'fill_scID')
        self.sc_id.setText(self.DEFAULT_CONFIG['SCHOOL_ID'])

        self.downloadUrl = self.findChild(QLabel, 'fill_url')
        self.downloadModelUrl = self.findChild(QLabel, 'fill_model_url')
        self.downloadUrl.setText(self.DEFAULT_CONFIG['DOWNLOAD_URL'])
        self.downloadModelUrl.setText(self.DEFAULT_CONFIG['ID_MODEL_URL'])

        self.printerStatus = self.findChild(QLabel, 'fill_status')
        self.nPrinted = self.findChild(QLabel, 'fill_nPrint')
        self.download3DModelStatus = self.findChild(
            QLabel, 'fill_download_model_status')
        self.xyzStatus = self.findChild(QLabel, 'fill_xyz_status')

        self.resetUiState()

        self.show()

        ''' ---------------------- Thread ----------------------- '''
        self.worker = WorkerThread(self.updateUI, self.DEFAULT_CONFIG['SCHOOL_ID'], self.start,
                                   self.download3DModel, self.closeProgramXYZ, self.resetUiState, self.nPrinted, self.downloadUrl.text())
        self.workerThread = QtCore.QThread()
        # Init worker run() at startup (optional)
        self.workerThread.started.connect(self.worker.run)
        # self.worker.signalExample.connect(self.signalExample)  # Connect your signals/slots
        # Move the Worker object to the Thread object
        self.worker.moveToThread(self.workerThread)
        self.workerThread.start()

    def resetUiState(self):
        self.printerStatus.setText("-")
        # self.nPrinted.setText(0)
        self.download3DModelStatus.setText("-")
        self.xyzStatus.setText("-")

    def updateUI(self, text):
        text = str(text)
        print(f"\t+ Status = {text}")
        if text == self.printerStatus.text():
            return
        print(f"{text=}")
        self.printerStatus.setText(text)

    def closeProgramXYZ(self):
        # if "XYZPrint.exe" in (p.name() for p in psutil.process_iter()):
        os.system("TASKKILL /F /IM XYZPrint.exe")
        self.xyzStatus.setText("XYZ Print is Closed.")
        # self.resetUiState()

    def openProgramXYZ(self):
        print("Open Program XYZ.")
        self.xyzStatus.setText("XYZ Print is Opening")
        # subprocess.call(["C:\\Program Files\\XYZprint\\XYZprint.exe"])
        os.startfile("C:\\Program Files\\XYZprint\\XYZprint.exe")
        time.sleep(1)
        if self.isXyzOpen():
            print("XYZ is Opened")
        else:
            os.startfile("C:\\Program Files\\XYZprint\\XYZprint.exe")
            print("Reopening XYZ")
        # os.startfile("XYZprint.exe.lnk")
    
    def isXyzOpen(self):
        return "XYZprint.exe" in (p.name() for p in psutil.process_iter())


    def download3DModel(self, file_id, file_name):  # .3w
        print("Downloading 3D Model")

        desktop_path = os.path.expanduser("~/Desktop")  # Find desktop path
        directory_path = desktop_path+"/3DTeleprint"

        try:
            if not os.path.exists(directory_path):  # Check is path alive?
                print(f"Create directory : {directory_path}")
                os.makedirs(directory_path)  # Create folder
        except OSError:
            print('Error: Creating directory. ' + directory_path)
        
        # self.fileName.setText(file_name)

        # download_url = 'http://tele3dprinting.com/2019/process.php?api=stl.read&file_id=' + file_id
        download_url = self.downloadModelUrl.text() + file_id
        print(f"{download_url=}")
        r = requests.get(download_url, allow_redirects=True)
        save_path = directory_path+'/'+file_name
        with open(save_path, 'wb') as file:
            file.write(r.content)

        # return save_path
        # "%userprofile%" = Get username of this PC
        return os.path.join(os.path.expandvars("%userprofile%"), "Desktop", "3DTeleprint", file_name)
        # C:\Users\Lookpeach\Desktop\3DTeleprint\2020-10-14 16-09-58 (2) (Cube_test.stl).0.stl

    def checkImageExisting(self, state_click_image_url, timeout=5):
        print(f"[checkImageExisting_2] - {state_click_image_url}", end='.. ')
        time.sleep(1)
        found_location = None
        is_found_image = False
        last = time.time()
        while found_location == None and time.time()-last < timeout:
            found_location = pyautogui.locateOnScreen(state_click_image_url)

            if found_location:
                is_found_image = True
                # buttonx, buttony = pyautogui.center(found_location)
                # pyautogui.click(buttonx, buttony)
        print(f"{'Found' if is_found_image else 'NotFound'}")
        return is_found_image

    def checkImageExisting_2(self, state_click_image_url, timeout=5, click=False):
        print(f"[checkImageExisting_2] - {state_click_image_url}", end='.. ')
        time.sleep(1)
        found_location = None
        is_found_image = False
        last = time.time()
        while found_location == None and time.time()-last < timeout:
            found_location = pyautogui.locateOnScreen(state_click_image_url)

            if found_location:
                if click:
                    buttonx, buttony = pyautogui.center(found_location)
                    pyautogui.click(buttonx, buttony)
                is_found_image = True

        print(f"{'Found' if is_found_image else 'NotFound'}")
        return is_found_image

    def emulateFunction(self, state_click_image_url):
        print(f"[emulateFunction] - {state_click_image_url}", end='.. ')
        found_location = None
        while found_location == None:
            # found_location = pyautogui.locateOnScreen(state_click_image_url, confidence=0.8)
            # found_location = pyautogui.locateOnScreen(state_click_image_url)
            found_location = pyautogui.locateOnScreen(
                state_click_image_url, grayscale=True)

            if found_location:
                buttonx, buttony = pyautogui.center(found_location)
                pyautogui.click(buttonx, buttony)
        print(f"{'Found' if found_location != None else 'NotFound'}")

    def mouseEmulation(self, file_path):
        time.sleep(15)
        self.checkImageExisting_2(
            'ImageRecognition/1-Close-Login.PNG', click=True)
        self.checkImageExisting_2(
            'ImageRecognition/2-Import-file.PNG', click=True)
        self.checkImageExisting_2(
            'ImageRecognition/3-Open-file.PNG', click=True)
        print(f"---> File Path : {file_path}")
        # time.sleep(2)
        pyautogui.write(file_path)
        # pyautogui.typewrite(file_path)
        # keyboard.send_keys(file_path)
        time.sleep(2)
        # self.emulateFunction('ImageRecognition/4-OK-open-file.PNG')
        is_found_image = self.checkImageExisting_2(
            'ImageRecognition/4-OK-open-file.PNG', click=True)  # เปลี่ยนรูปด้วย
        if not is_found_image:
            is_found_image = self.checkImageExisting_2(
                'ImageRecognition/4-2-OK-open-file.PNG', click=True)  # เปลี่ยนรูปด้วย
            # is_found_image
        # pyautogui.press('enter')
        # self.fileState.setText('Import to XYZ.')

        is_found_image = self.checkImageExisting(
            'ImageErrorCase/ObjectSmall-Cut.png')  # เปลี่ยนรูปด้วย
        if not is_found_image:
            self.checkImageExisting_2('ImageRecognition/4-1-No.PNG')

        is_found_image = self.checkImageExisting(
            'ImageErrorCase/FileError-Cut.png')  # เปลี่ยนรูปด้วย
        if not is_found_image:
            self.checkImageExisting_2(
                'ImageErrorCase/OkFileError-Cut.PNG', click=True)
            self.checkImageExisting_2(
                'ImageRecognition/1-Close-Login.PNG', click=True, timeout=3)
            self.checkImageExisting_2(
                'ImageRecognition/2-Import-file.PNG', click=True, timeout=3)
            self.checkImageExisting_2(
                'ImageRecognition/3-Open-file.PNG', click=True, timeout=3)
            is_found_image = self.checkImageExisting(
                'ImageErrorCase/CannotRenderFile-Cut.png')  # เปลี่ยนรูปด้วย
            # if not is_found_image:
            #     os.system('shutdown /r /t 0')

        # self.worker.s.sendall(b'st:0:st')
        
        self.checkImageExisting_2('ImageRecognition/5-Print.PNG', click=True)
        time.sleep(3)
        self.worker.s.sendall(b'st:1:st')

        is_handle_error = False
        is_found_image = self.checkImageExisting(
            'ImageErrorCase/SettingInstalledMaterial-Cut.png', timeout=10)  # เปลี่ยนรูปด้วย
        if is_found_image:
            self.checkImageExisting_2(
                'ImageRecognition/5-Print.PNG', click=True)
            time.sleep(3)
            self.worker.s.sendall(b'st:1:st')
            is_found_image = self.checkImageExisting(
                'ImageErrorCase/PrinterBusy-Cut.png')
            if is_found_image:
                is_found_image = self.checkImageExisting_2(
                    'ImageRecognition/5-1-Print.PNG', click=True)
                time.sleep(3)
                self.worker.s.sendall(b'st:1:st')
                if not is_found_image:
                    self.checkImageExisting_2(
                        'ImageRecognition/5-Print.PNG', click=True)
                    time.sleep(3)
                    self.worker.s.sendall(b'st:1:st')
            is_handle_error = True

        if not is_handle_error:
            is_found_image = self.checkImageExisting(
                'ImageErrorCase/NoPrinter-Cut.png')  # เปลี่ยนรูปด้วย
            # if not is_found_image:
            #     os.system('shutdown /r /t 0')
            is_handle_error = True

        if not is_handle_error:
            is_found_image = self.checkImageExisting(
                'ImageErrorCase/PrinterBusy-Cut.png')  # เปลี่ยนรูปด้วย
            # if not is_found_image:
            #     os.system('shutdown /r /t 0')
            is_handle_error = True


    def start(self, is_worker_handle=False, save_path='', is_first_time=True):
        # This is executed when the button is pressed
        print("START")
        self.worker.s.sendall(b"st:0:st")

        ready_status = self.printerStatus.text()
        print(f"{ready_status=}")
        if ready_status == "Printer Ready" or not is_first_time:
            # if is_worker_handle:
            #     save_path = save_path
            print(f"save_path = {save_path}")
            # save_path = '"C:\\Users\\Lookpeach\\Desktop\\3DTeleprint\\2020-10-14 16-09-58 (2) (Cube_test.stl).0.stl"'
            if save_path == None:
                self.download3DModelStatus.setText("No file to download.")
                print("No file to download.")
            else:
                print("Download Model Complete.")
                self.download3DModelStatus.setText("Download Model Complete.")

                self.openProgramXYZ()
                self.mouseEmulation(save_path)
                self.closeProgramXYZ()

                # self.worker.setFetchStatus(status=True) # Reset fetch status

    # def stopButtonPressed(self):
    #     # This is executed when the button is pressed
    #     # self.worker.s.send(b'\x01')
    #     self.worker.s.sendall(b'st:2:st')
    #     print('STOP')


app = QApplication(sys.argv)
window = Ui()
app.exec_()
