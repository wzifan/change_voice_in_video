#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Wang Zifan

"""视频下载"""
import os
import threading
import time
from tkinter import *
from tkinter.filedialog import askdirectory, askopenfilename
from video_download import VideoDownloadMainThread


class VideoDownloadMonitorThreadForGUI(threading.Thread):
    """ 视频下载监听进程

        Author: Wang Zifan
        Date: 2022/04/27

        Attributes:
            thread_id (str): 线程id
            main_thread (VideoDownloadMainThread): 视频下载主线程
            TkinterWidgets: tkinter的组件
    """

    def __init__(self, thread_id: str, main_thread: VideoDownloadMainThread, *TkinterWidgets):
        super(VideoDownloadMonitorThreadForGUI, self).__init__()
        self.thread_id = thread_id
        self.main_thread = main_thread
        self.button_start = TkinterWidgets[0]
        self.list_download_info_str = TkinterWidgets[1]

    def run(self):
        while True:
            self.list_download_info_str.set(self.main_thread.list_download_info)
            if not self.main_thread.is_alive():
                # 主线程运行结束，按钮恢复原状态
                self.button_start.config(state=NORMAL, text="开始下载")
                break
            time.sleep(0.1)


class VideoDownloadGUI:
    """ 视频下载 GUI

            Author: Wang Zifan
            Date: 2022/04/27

            Attributes:
                master (str): tkinter根节点
        """

    def __init__(self, master):
        self.master = master
        master.title("视频下载")

        # 用于显示标题或说明
        self.frame1 = Frame(master, pady=10)
        # 主体部分
        self.frame2 = Frame(master, pady=10)
        # 开始下载按钮
        self.frame3 = Frame(master, pady=10)
        # 下载信息显示部分
        self.frame4 = Frame(master, pady=10, width=320, height=320)

        # 标签
        self.label_title = Label(self.frame1, text="视频下载应用")

        # url文件路径
        self.url_file_path = StringVar()
        # 标签
        self.label_select_url_file = Label(self.frame2, text="请选择url文件：")
        # url文件路径输入框
        self.entry_url_file_select = Entry(self.frame2, textvariable=self.url_file_path)
        # 选择url文件路径按钮
        self.button_select_url_path = Button(self.frame2, text="选择文件",
                                             command=lambda: self.select_file_path(self.url_file_path))

        # 变量 是否带视频名称
        self.whether_with_name = BooleanVar()
        self.whether_with_name.set(True)
        # 标签
        self.label_whether_with_name = Label(self.frame2, text="是否带视频名称：")
        # 单选框 “是”
        self.radio_button1 = Radiobutton(self.frame2, text="是", variable=self.whether_with_name, value=True)
        # 单选框 “否”
        self.radio_button2 = Radiobutton(self.frame2, text="否", variable=self.whether_with_name, value=False)

        # 下载目录
        self.download_path = StringVar()
        # 标签
        self.label_select_download_path = Label(self.frame2, text="请选择下载目录：")
        # 下载目录输入框
        self.entry_download_path = Entry(self.frame2, textvariable=self.download_path)
        # 选择url文件路径按钮
        self.button_select_download_path = Button(self.frame2, text="选择目录",
                                                  command=lambda: self.select_dir_path(self.download_path))

        # 最大同时下载个数
        self.max_count = IntVar()
        self.str_max_count = StringVar()
        self.str_max_count.set('1')
        # 标签
        self.label_max_count = Label(self.frame2, text="最大同时下载数：")
        # 最大同时下载个数输入框
        vcmd_int = self.frame2.register(self.validate_int)  # we have to wrap the command
        self.entry_max_count = Entry(self.frame2, validate="key", validatecommand=(vcmd_int, '%P'),
                                     textvariable=self.str_max_count)

        # 开始下载按钮
        self.button_start = Button(self.frame3, text="开始下载", command=self.start_download)

        # 视频下载进度信息字符串列表
        self.list_download_info_str = StringVar()
        # 标签
        self.label_download_progress = Label(self.frame4, text="下载进度：")
        # 视频下载进度信息列表及其滚动条
        self.scrollbar = Scrollbar(self.frame4, orient=VERTICAL)
        self.list_box_download_info = Listbox(self.frame4, height=12, yscrollcommand=self.scrollbar.set,
                                              listvariable=self.list_download_info_str)
        self.scrollbar.config(command=self.list_box_download_info.yview)

        # ***********************************************************************************************
        # layout
        # frame1
        self.label_title.pack()
        # frame2
        self.label_select_url_file.grid(row=0, column=0, sticky=E)
        self.entry_url_file_select.grid(row=0, column=1, columnspan=2)
        self.button_select_url_path.grid(row=0, column=3)
        self.label_whether_with_name.grid(row=1, column=0, sticky=E)
        self.radio_button1.grid(row=1, column=1)
        self.radio_button2.grid(row=1, column=2)
        self.label_select_download_path.grid(row=2, column=0, sticky=E)
        self.entry_download_path.grid(row=2, column=1, columnspan=2)
        self.button_select_download_path.grid(row=2, column=3)
        self.label_max_count.grid(row=3, column=0, sticky=E)
        self.entry_max_count.grid(row=3, column=1, columnspan=2)
        # frame3
        self.button_start.pack()
        # frame4
        self.label_download_progress.grid(row=0, column=0, sticky=W)
        self.list_box_download_info.grid(row=1, column=0, sticky=W + N + S + E)
        self.scrollbar.grid(row=1, column=1, sticky=W + N + S)
        # frame layout
        self.frame1.pack()
        self.frame2.pack()
        self.frame3.pack()
        self.frame4.pack()
        self.frame4.grid_propagate(0)
        self.frame4.grid_columnconfigure(0, minsize=302)

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

    def validate_int(self, new_text):
        if not new_text:  # the field is being cleared
            self.max_count.set(1)
            return True
        try:
            max_count = int(new_text)
            if max_count > 0:
                self.max_count.set(max_count)
                return True
            else:
                return False
        except ValueError:
            return False

    def start_download(self):
        download_main_thread = VideoDownloadMainThread('main-1', self.url_file_path.get(), self.download_path.get(),
                                                       self.max_count.get(), self.whether_with_name.get())
        download_main_thread.start()
        self.button_start.config(state=DISABLED, text="正在下载")
        monitor_thread = VideoDownloadMonitorThreadForGUI('monitor-1', download_main_thread, self.button_start,
                                                          self.list_download_info_str)
        monitor_thread.start()


root = Tk()
root.geometry('400x550')
video_download_gui = VideoDownloadGUI(root)
root.mainloop()
