#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Wang Zifan

"""说明"""
import os
import threading
import time
from tkinter import *
from tkinter.filedialog import askdirectory, askopenfilename

from video_process import VideoProcessMainThread


class VideoProcessMonitorThreadForGUI(threading.Thread):
    """ 视频下载监听进程

        Author: Wang Zifan
        Date: 2022/04/27

        Attributes:
            thread_id (str): 线程id
            main_thread (VideoDownloadMainThread): 视频下载主线程
            TkinterWidgets: tkinter的组件
    """

    def __init__(self, thread_id: str, main_thread: VideoProcessMainThread, *TkinterWidgets):
        super(VideoProcessMonitorThreadForGUI, self).__init__()
        self.thread_id = thread_id
        self.main_thread = main_thread
        self.button_start = TkinterWidgets[0]
        self.video_split_progress = TkinterWidgets[1]
        self.asr_result = TkinterWidgets[2]

    def run(self):
        while True:
            self.video_split_progress.set('\n'.join(self.main_thread.split_process))
            self.asr_result.set(self.main_thread.asr_result)
            if not self.main_thread.is_alive():
                # 主线程运行结束，按钮恢复原状态
                self.button_start.config(state=NORMAL, text="开始分离与识别")
                break
            time.sleep(0.1)


class VideoProcessGUI:
    """ 视频下载 GUI

            Author: Wang Zifan
            Date: 2022/04/27

            Attributes:
                master (str): tkinter根节点
        """

    def __init__(self, master):
        self.master = master
        master.title("视频处理")

        # 主体
        self.frame1 = Frame(master, pady=10)
        # xxx
        self.frame2 = Frame(master, pady=10)
        # xxx
        self.frame3 = Frame(master, pady=0)

        # 原始视频文件路径
        self.video_original_path = StringVar()
        # 视频分离目录+
        self.split_dir = StringVar()
        # 视频分离进度
        self.video_split_progress = StringVar()
        # 语音识别结果
        self.asr_result = StringVar()
        # 标签
        self.label_video_split = Label(self.frame1, text="音视频分离与语音识别")
        # 标签
        self.label_video_original_path = Label(self.frame1, text="请选择视频：")
        # 标签
        self.label_split_dir = Label(self.frame1, text="目标目录：")
        # 原视频路径输入框
        self.entry_video_original_path = Entry(self.frame1, textvariable=self.video_original_path)
        # 分离目录输入框
        self.entry_split_dir = Entry(self.frame1, textvariable=self.split_dir)
        # 选择原视频路径按钮
        self.button_select_video_path = Button(self.frame1, text="选择文件",
                                               command=lambda: self.select_file_path(self.video_original_path))
        # 选择分离目录按钮
        self.button_select_split_dir = Button(self.frame1, text="选择目录",
                                              command=lambda: self.select_dir_path(self.split_dir))
        # 开始分离按钮
        self.button_start_split_and_asr = Button(self.frame1, text="开始分离与识别", command=self.start_split_and_asr)
        # 标签
        self.label_video_split_progress = Label(self.frame1, text="分离进度：")
        # 分离进度消息
        self.massage1 = Message(self.frame1, textvariable=self.video_split_progress,
                                width=300, anchor=W, justify=LEFT, bg="white")
        # 标签
        self.label_asr_result = Label(self.frame1, text="识别结果：")
        # 垂直进度条
        self.scrollbar_v = Scrollbar(self.frame1, orient=VERTICAL)
        # 水平进度条
        self.scrollbar_h = Scrollbar(self.frame1, orient=HORIZONTAL)
        # 分离进度消息
        self.listbox_asr_result = Listbox(self.frame1, height=10, width=2, xscrollcommand=self.scrollbar_h.set,
                                          yscrollcommand=self.scrollbar_v.set,
                                          listvariable=self.asr_result, selectmode="extended")
        self.scrollbar_v.config(command=self.listbox_asr_result.yview)
        self.scrollbar_h.config(command=self.listbox_asr_result.xview)

        # ***********************************************************************************************
        # layout
        # frame1
        self.label_video_split.grid(row=0, column=1, pady=5)
        self.label_video_original_path.grid(row=1, column=0, sticky=E)
        self.label_split_dir.grid(row=2, column=0, sticky=E)
        self.entry_video_original_path.grid(row=1, column=1)
        self.entry_split_dir.grid(row=2, column=1)
        self.button_select_video_path.grid(row=1, column=2, sticky=W)
        self.button_select_split_dir.grid(row=2, column=2, sticky=W)
        self.button_start_split_and_asr.grid(row=3, column=1, pady=10)
        self.label_video_split_progress.grid(row=4, column=0, pady=5, sticky=W)
        self.massage1.grid(row=5, column=0, columnspan=3, sticky=W + N + S + E)
        self.label_asr_result.grid(row=6, column=0, pady=5, sticky=W)
        self.listbox_asr_result.grid(row=7, column=0, columnspan=3, sticky=W + N + S + E)
        self.scrollbar_v.grid(row=7, column=4, sticky=W + N + S)
        self.scrollbar_h.grid(row=8, column=0, columnspan=3, sticky=W + N + E)

        # frame layout
        self.frame1.pack()
        self.frame1.grid_columnconfigure(0, minsize=100)
        self.frame1.grid_columnconfigure(0, minsize=200)
        self.frame1.grid_columnconfigure(0, minsize=100)
        self.frame2.pack()
        self.frame3.pack()

    def select_file_path(self, path):
        s = askopenfilename()
        if os.name == 'nt':
            s = s.replace("/", "\\")
        path.set(s)

    def select_dir_path(self, path):
        s = askdirectory()
        if os.name == 'nt':
            s = s.replace("/", "\\")
        path.set(s)

    def start_split_and_asr(self):
        video_process_main_thread = VideoProcessMainThread('1', self.video_original_path.get(), self.split_dir.get())
        video_process_main_thread.start()
        self.button_start_split_and_asr.config(state=DISABLED, text="正在分离与识别")
        monitor_thread = VideoProcessMonitorThreadForGUI('monitor-1', video_process_main_thread,
                                                         self.button_start_split_and_asr,
                                                         self.video_split_progress,
                                                         self.asr_result)
        monitor_thread.start()


root = Tk()
root.geometry('400x640')
video_download_gui = VideoProcessGUI(root)
root.mainloop()
