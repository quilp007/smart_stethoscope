#!/usr/bin/env python
# coding=utf8

import os, sys, time, datetime, warnings, signal
from PyQt5.QtCore import QSize, QRect, QObject, pyqtSignal, QThread, pyqtSignal, pyqtSlot, Qt, QEvent, QTimer
from PyQt5.QtWidgets import QApplication, QComboBox, QDialog, QMainWindow, QWidget, QLabel, QTextEdit, QListWidget, QListView
from PyQt5.QtWidgets import QPushButton, QGridLayout, QLCDNumber
from PyQt5 import uic, QtTest, QtGui, QtCore
from PyQt5.QtGui import QImage, QPixmap

import numpy as np
import shelve

import pyqtgraph as pg
import struct
import pyaudio
from scipy.fftpack import fft
import wave
import cv2

x_size = 200

form_class = uic.loadUiType('RMS.ui')[0]

#--------------------------------------------------------------
# [THREAD] RECEIVE from PLC (receive from PLC)
#--------------------------------------------------------------
class THREAD_RECEIVE_Data(QThread):
    intReady = pyqtSignal(float)

    @pyqtSlot()
    def __init__(self):
        super(THREAD_RECEIVE_Data, self).__init__()


    def run(self):
        while False:
            print("thread!!\n")


class qt(QMainWindow, form_class):
    def __init__(self):
        self.AUDIO_ENABLE = True
        self.VIDEO_ENABLE = False

        # QMainWindow.__init__(self)
        # uic.loadUiType('qt_test2.ui', self)[0]

        super().__init__()
        self.setupUi(self)
        self.setWindowFlags(Qt.FramelessWindowHint)

        self.btn_main.clicked.connect(lambda: self.main_button_function(self.btn_main))
        self.btn_parameter.clicked.connect(lambda: self.main_button_function(self.btn_parameter))

        self.data = np.linspace(-np.pi, np.pi, x_size)
        self.y1 = np.zeros(len(self.data))
        self.y2 = np.sin(self.data)

        # ----------------------------------------------------------------------------------------
        # ----------------------------------------------------------------------------------------
        # ----------------------------------------------------------------------------------------
        # pyqtgraph stuff

        pg.setConfigOptions(antialias=True)
        self.traces = dict()

        wf_xlabels = [(0, '0'), (2048, '2048'), (4096, '4096')]
        wf_xaxis = pg.AxisItem(orientation='bottom')
        wf_xaxis.setTicks([wf_xlabels])

        wf_ylabels = [(0, '0'), (127, '128'), (255, '255')]
        wf_yaxis = pg.AxisItem(orientation='left')
        wf_yaxis.setTicks([wf_ylabels])

        sp_xlabels = [
            (np.log10(10), '10'), (np.log10(100), '100'),
            (np.log10(1000), '1000'), (np.log10(22050), '22050')
        ]
        sp_xaxis = pg.AxisItem(orientation='bottom')
        sp_xaxis.setTicks([sp_xlabels])

        # self.bottom_plot = self.graphWidget.addPlot(title="Temp.")
        self.waveform = self.graphWidget.addPlot(
            title='WAVEFORM', row=1, col=1, axisItems={'bottom': wf_xaxis, 'left': wf_yaxis},
        )
        self.spectrum = self.graphWidget.addPlot(
            title='SPECTRUM', row=2, col=1, axisItems={'bottom': sp_xaxis},
        )

        # pyaudio stuff
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.CHUNK = 1024 * 2
        self.RECORD_SECONDS = 30
        self.WAVE_OUTPUT_FILENAME = "output1.wav"
        self.frames = []
        self.RECODE = False

        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            output=True,
            frames_per_buffer=self.CHUNK
        )
        # waveform and spectrum x points
        self.x = np.arange(0, 2 * self.CHUNK, 2)
        self.f = np.linspace(0, self.RATE / 2, self.CHUNK / 2)
        # ----------------------------------------------------------------------------------------
        # ----------------------------------------------------------------------------------------
        # ----------------------------------------------------------------------------------------
        # self.animation()

        self.timer = QtCore.QTimer()
        self.timer.setInterval(20)
        self.timer.timeout.connect(self.update)
        self.timer.start()

        # START RECODE
        self.RECODE = False
        self.COUNTER = 0


        # init USB CAMERA
        CAM_ID = 0
        self.cam = cv2.VideoCapture(CAM_ID) 
        if self.cam.isOpened() == False:
            print('Can\'t open the CAM(%d)' % (CAM_ID))
            exit()

        width = self.cam.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.cam.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print('size = [%f, %f]\n' % (width, height)) 

        self.main_button_function(self.btn_main)

        self.btn_capture.clicked.connect(self.btn_capture_function)
        self.btn_record.clicked.connect(self.btn_record_function)
        self.btn_exit1.clicked.connect(self.btn_exit_2)
        self.btn_exit2.clicked.connect(self.btn_exit_2)
    # ----------------------------------------------------------------------------------------
    # ----------------------------------------------------------------------------------------
    def btn_exit_1(self):
        # self.stream.stop_stream()
        # self.stream.close()

        # cv2.destroyAllWindows()
        # self.cam.release()

        sys.exit(1)

    def btn_exit_2(self):
        # self.stream.stop_stream()
        # self.stream.close()

        # cv2.destroyAllWindows()
        # self.cam.release()

        # sys.exit(1)

        os.system("shutdown now -h")


    def btn_record_function(self):
        self.RECODE = True
        
    def btn_capture_function(self):
        ret, img = self.cam.read()
        # img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        filename = './video/' + time.strftime('%y%m%d_%H%M%S', time.localtime(time.time())) + '.png'
        cv2.imwrite(filename, img)
        self.textEdit_2.append('captrued ' + filename)
        # print(time.strftime('%y%m%d_%H%M%S', time.localtime(time.time())))

    def start(self):
        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtGui.QApplication.instance().exec_()

    def set_plotdata(self, name, data_x, data_y):
        if name in self.traces:
            self.traces[name].setData(data_x, data_y)
        else:
            if name == 'waveform':
                self.traces[name] = self.waveform.plot(pen='c', width=3)
                self.waveform.setYRange(0, 255, padding=0)
                self.waveform.setXRange(0, 2 * self.CHUNK, padding=0.005)
            if name == 'spectrum':
                self.traces[name] = self.spectrum.plot(pen='m', width=3)
                self.spectrum.setLogMode(x=True, y=True)
                self.spectrum.setYRange(-4, 0, padding=0)
                self.spectrum.setXRange(
                    np.log10(20), np.log10(self.RATE / 2), padding=0.005)

    def audio_function(self):
        wf_data = self.stream.read(self.CHUNK)

        # output audio data -------------------------------
        self.stream.write(wf_data)
        # output audio data -------------------------------

        # write audio data -------------------------------
        if self.RECODE == True:
            self.frames.append(wf_data)
            self.COUNTER += 1
            text =  'recording ' + str(int(self.COUNTER/(self.RATE / self.CHUNK))) + ' sec'
            self.textEdit.setPlainText(text)
            if self.COUNTER > int(self.RATE / self.CHUNK * self.RECORD_SECONDS):
                self.RECODE = False
                self.COUNTER = 0
                self.recode_wave(self.frames) 
        # write audio data -------------------------------

        wf_data = struct.unpack(str(2 * self.CHUNK) + 'B', wf_data)
        wf_data = np.array(wf_data, dtype='b')[::2] + 128
        self.set_plotdata(name='waveform', data_x=self.x, data_y=wf_data,)

        sp_data = fft(np.array(wf_data, dtype='int8') - 128)
        sp_data = np.abs(sp_data[0:int(self.CHUNK / 2)]
                         ) * 2 / (128 * self.CHUNK)
        self.set_plotdata(name='spectrum', data_x=self.f, data_y=sp_data)

    def video_fucntion(self):
        # USB CAMERA -------------------------------
        ret, img = self.cam.read()
        height, width, bpc = img.shape
        bpl = bpc * width
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        image = QtGui.QImage(img.data, width, height, bpl, QtGui.QImage.Format_RGB888)
        self.label.setPixmap(QPixmap.fromImage(image))
    

    def update(self):
        # if self.AUDIO_ENABLE == False:
        #     self.stream.stop_stream()
        # else:
        #     self.stream.start_stream()
        #     self.audio_function()

        if self.AUDIO_ENABLE:
            self.audio_function()

        if self.VIDEO_ENABLE:
            self.video_fucntion()
    
    def recode_wave(self, frames):
        self.WAVE_OUTPUT_FILENAME = './audio/' + time.strftime('%y%m%d_%H%M%S', time.localtime(time.time())) + '.wav'
        wf = wave.open(self.WAVE_OUTPUT_FILENAME, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(frames))
        self.frames = []
        wf.close()

        self.textEdit.append('saved ' + self.WAVE_OUTPUT_FILENAME)


    def animation(self):
        timer = QtCore.QTimer()
        timer.timeout.connect(self.update)
        timer.start(20)
        # self.start()
    # ----------------------------------------------------------------------------------------
    # ----------------------------------------------------------------------------------------

    def update_upper_plot(self, msg):
        print(msg)
        if self.first_flag == 1:
            self.y1 = np.full(len(self.data), msg)
            self.first_flag = 0

        # self.upper_curve.setData(self.data[self.ptr % 10])
        self.y1 = np.roll(self.y1, -1)

        self.y1[-1] = msg

        self.upper_curve.setData(self.y1)

        self.lcdNum_T_PV_CH1.display("{:.1f}".format(msg))

        if self.ptr == 0:
            self.upper_plot.enableAutoRange('xy', False)  ## stop auto-scaling after the first data set is plotted
        self.ptr += 1


    def update_bottom_plot(self):
        # self.g_plotWidget.plot(hour, temperature)
        # upper_curve = self.graphWidget_2.plot(pen='y')
        self.y2 = np.roll(self.y2, -1)
        self.y2[-1] = np.sin(self.data[self.counter % x_size])
        self.bottom_curve.setData(self.y2)

        mean_value = 10 + np.round(self.y2[-1], 1)/10
        if self.counter % 50 == 0:
            self.lcdNum_T_SV_CH1.display("{:.1f}".format(mean_value))
        # print('y2: ', mean_value)

        self.counter += 1

    # button setting for MAIN PAGE CHANGE 
    def main_button_function(self, button):
        global gLogon

        self.btn_main.setStyleSheet("background-color: #dedede; border: 0px")
        self.btn_parameter.setStyleSheet("background-color: #dedede; border: 0px")

        if button == self.btn_main:     # audio menu
            self.AUDIO_ENABLE = True
            self.VIDEO_ENABLE = False
            self.stream.start_stream()

            self.stackedWidget.setCurrentWidget(self.sw_MAIN)
            self.btn_main.setStyleSheet("background-color: lime; border: 0px")
        elif button == self.btn_parameter:  # video menu
            self.AUDIO_ENABLE = False
            self.VIDEO_ENABLE = True
            self.stream.stop_stream()

            self.stackedWidget.setCurrentWidget(self.sw_PARAMETER)
            self.btn_parameter.setStyleSheet("background-color: lime; border: 0px")

        # elif button == self.btn_logon:
        #     if gLogon == True:
        #         # self.Logoff_func()
        #     else:
        #         # self.stackedWidget.setCurrentWidget(self.sw_LOGON)


def run():
    app = QApplication(sys.argv)
    widget = qt()
    widget.show()
    # widget.update_func_1()

    sys.exit(app.exec_())


if __name__ == "__main__":
    run()
