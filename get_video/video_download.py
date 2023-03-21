#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Wang Zifan

"""说明"""
import os
import threading
import time
import queue
import copy
import subprocess
import chardet


class VideoDownloadThread(threading.Thread):
    """ 视频下载线程类

        Author: Wang Zifan
        Date: 2022/04/22

        Attributes:
            thread_id (str): 线程id
            video_url (str): 下载视频的链接
            dir_path (str): 下载目录
            wav_name (str): 下载视频的名称
    """

    def __init__(self, thread_id: str, video_url: str, dir_path: str, wav_name: str):
        super(VideoDownloadThread, self).__init__()
        self.thread_id = thread_id
        self.video_url = video_url
        self.dir_path = dir_path
        self.wav_name = wav_name
        self.log_path = os.path.join(self.dir_path, self.wav_name + "下载信息.txt")
        self.run_state = ""
        self.final_state = ""

    def run(self):
        # 视频下载信息文件的绝对路径，用于显示视频信息、视频下载进度
        print(self.wav_name + "开始下载")
        with open(self.log_path, 'w', encoding="utf-8") as log_file:
            export_exe = True
            # 如果代码用于导出exe文件，则需要加上'./'，并在导出的exe同目录下加入you-get.exe
            if export_exe:
                startup = subprocess.STARTUPINFO()
                startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
                startup.wShowWindow = subprocess.SW_HIDE
                subprocess.run(os.path.join(os.path.abspath('./'), 'you-get.exe ') + self.video_url + " -o " +
                               self.dir_path + " -O " + self.wav_name + " --no-caption",
                               stdin=None, stdout=log_file, stderr=log_file, shell=False, startupinfo=startup)
            else:
                subprocess.run("you-get " + self.video_url + " -o " + self.dir_path + " -O " + self.wav_name +
                                " --no-caption", stdin=None, stdout=log_file, stderr=log_file, shell=False)
        print(self.wav_name + "下载完成")


class VideoDownloadMonitorThread(threading.Thread):
    """ 视频下载子线程监听

        Author: Wang Zifan
        Date: 2022/04/27

        Attributes:
            thread_id (str): 线程id
            download_thread (VideoDownloadThread): 视频下载子线程
    """

    def __init__(self, thread_id: str, download_thread: VideoDownloadThread):
        super(VideoDownloadMonitorThread, self).__init__()
        self.thread_id = thread_id
        self.download_thread = download_thread

    def run(self):
        while True:
            # 线程正在运行的情况
            if self.download_thread.is_alive():
                # 如果文件不存在，状态为准备下载
                if not os.path.isfile(self.download_thread.log_path):
                    self.download_thread.run_state = "准备下载"
                # 如果文件存在
                else:
                    # 获取文件编码格式
                    with open(self.download_thread.log_path, 'rb') as f:
                        text = f.read()
                        code = chardet.detect(text)['encoding']
                    # 打开文件
                    with open(self.download_thread.log_path, 'r', encoding=code) as f:
                        # 将每一行存入列表，去除每一行首尾的回车和空格，空行不放入列表
                        line_list = [line.strip() for line in f.readlines() if line.strip() != '']
                        # 如果文件为空，状态为准备下载
                        if len(line_list) == 0:
                            self.download_thread.run_state = "准备下载"
                        # 如果文件不为空
                        else:
                            # 日志信息有错误信息，状态为下载失败
                            if "[error]" in line_list[0]:
                                self.download_thread.run_state = "下载失败"
                                self.download_thread.final_state = "下载失败"
                            # 日志信息没有错误信息
                            else:
                                # 取文件最后一行
                                last_line = line_list[-1]
                                # 如果最后一行含有%，且没有'100%'，说明正在下载
                                if '%' in last_line and '100%' not in last_line:
                                    last_line_list = last_line.split(' ')
                                    last_line_list = [s for s in last_line_list if '├' not in s]
                                    self.download_thread.run_state = ' '.join(last_line_list)
                                # 如果最后一行含'Skipping'或'100%'，说明下载成功
                                elif 'Skipping' or "Merging" or '100%' in last_line:
                                    self.download_thread.run_state = "下载完成"
                                    self.download_thread.final_state = "下载完成"
                                # 其它情况为未知错误
                                else:
                                    self.download_thread.run_state = "未知错误"
                                    self.download_thread.final_state = "未知错误"
            # 线程停止运行的情况
            else:
                # 如果文件不存在
                if not os.path.isfile(self.download_thread.log_path):
                    self.download_thread.final_state = "未知错误"
                # 如果文件存在
                else:
                    # 获取文件编码格式
                    with open(self.download_thread.log_path, 'rb') as f:
                        text = f.read()
                        code = chardet.detect(text)['encoding']
                    # 打开文件
                    with open(self.download_thread.log_path, 'r', encoding=code) as f:
                        # 将每一行存入列表，去除每一行首尾的回车和空格，空行不放入列表
                        line_list = [line.strip() for line in f.readlines() if line.strip() != '']
                        # 如果文件为空，最终状态为未知错误
                        if len(line_list) == 0:
                            self.download_thread.final_state = "未知错误"
                        # 如果文件不为空
                        else:
                            # 日志信息有错误信息，最终状态为下载失败
                            if "[error]" in line_list[0]:
                                self.download_thread.final_state = "下载失败"
                            # 日志信息没有错误信息，最后一行有'Skipping'，最终状态为下载完成
                            elif 'Skipping' in line_list[-1]:
                                self.download_thread.final_state = "下载完成"
                # 退出前删除文件
                if os.path.isfile(self.download_thread.log_path):
                    os.remove(self.download_thread.log_path)
                break
            time.sleep(0.25)


class VideoDownloadMainThread(threading.Thread):
    """ 视频下载主线程

        Author: Wang Zifan
        Date: 2022/04/22

        thread_id (str): 线程id
        url_list_file (str): 存放下载视频链接的文件路径
        dir_path (str): 下载视频的存放目录
        max_count (str): 最大同时下载数
        whether_with_name (str):
            True: 视频链接文件中不带视频名称，一行一个链接
            False: 视频链接文件中带视频名称(用于自定义命名视频文件)，第 1、3、5...行为视频名称，第 2、4、6...行为视频链接
    """

    def __init__(self, thread_id: str, url_list_file: str, dir_path: str, max_count: int = 5,
                 whether_with_name: bool = False):
        super(VideoDownloadMainThread, self).__init__()
        self.thread_id = thread_id
        self.url_list_file = url_list_file
        self.dir_path = dir_path
        self.max_count = max_count
        self.whether_with_name = whether_with_name
        self.list_download_info = []
        self.index = -1

    def run(self):
        self.VideoDownload(self.url_list_file, self.dir_path, self.max_count, self.whether_with_name)

    def VideoDownload(self, url_list_file: str, dir_path: str, max_count: int, whether_with_name: bool = False):
        """ 视频下载方法

            Author: Wang Zifan
            Date: 2022/04/27

            Attributes:
                url_list_file (str): 存放下载视频链接的文件路径
                dir_path (str): 下载视频的存放目录
                max_count (str): 最大同时下载数
                whether_with_name (str):
                    True: 视频链接文件中不带视频名称，一行一个链接
                    False: 视频链接文件中带视频名称(用于自定义命名视频文件)，第 1、3、5...行为视频名称，第 2、4、6...行为视频链接
        """
        # 打开视频链接文件
        # 获取文件编码格式
        with open(url_list_file, 'rb') as f:
            text = f.read()
            code = chardet.detect(text)['encoding']
        with open(url_list_file, 'r', encoding=code) as f:
            # 将每一行存入列表，去除每一行首尾的回车和空格，空行不放入列表
            line_list = [line.strip() for line in f.readlines() if line.strip() != '']

        if whether_with_name:
            # 带视频名称用于自定义命名视频文件，第 1、3、5...行为视频名称，第 2、4、6...行为视频链接
            url_list = line_list[1::2]
            wave_name_list = line_list[0::2]
        else:
            # 不带视频名称，一行一个链接
            url_list = line_list
            # wav_name默认为视频001，视频002...
            wave_name_list = ["视频" + str(i + 1).zfill(3) for i in range(len(url_list))]

        # 根据 url个数创建线程队列，将所有的线程放入队列
        thread_queue = queue.Queue(len(url_list))
        # 存放所有线程的列表，用于线程状态的监测
        thread_list_all = []
        # 定义线程列表，用于存放运行的线程
        thread_list = []
        # 根据视频链接、下载目录、视频名称创建所有线程并存入队列
        for i, url in enumerate(url_list):
            id = str(i + 1)
            thread_temp = VideoDownloadThread(id, url, dir_path, wave_name_list[i])
            thread_queue.put(thread_temp)
            thread_list_all.append(thread_temp)

        # 线程总数
        count_threads = len(thread_list_all)
        # 初始化旧状态
        list_download_info_old = [thread_list_all[i].wav_name + "：等待下载" for i in range(count_threads)]
        while True:
            # 获取最新的线程状态
            self.list_download_info = [thread_list_all[i].wav_name + "：等待下载" if i > self.index
                                       else self.get_state(thread_list_all[i], list_download_info_old[i])
                                       for i in range(count_threads)]
            # 更新旧状态
            list_download_info_old = copy.deepcopy(self.list_download_info)

            # 去掉运行结束的线程，只保留正在运行的线程
            thread_list = [x for x in thread_list if x.is_alive()]
            # 将线程队列中的线程放入列表运行
            if len(thread_list) < max_count:
                if not thread_queue.empty():
                    thread_list.append(thread_queue.get())
                    self.index += 1
                    thread_list[-1].start()
                    # 运行对应的监听线程
                    VideoDownloadMonitorThread(thread_list[-1].thread_id, thread_list[-1]).start()
            # 如果列表仍为空，说明所有线程运行完毕
            if len(thread_list) == 0:
                # 结束之前等待下载状态更新
                time.sleep(1)
                self.list_download_info = [thread_list_all[i].wav_name + "：等待下载" if i > self.index
                                           else self.get_state(thread_list_all[i], list_download_info_old[i])
                                           for i in range(count_threads)]
                break
            # 主线程每次循环睡眠 0.1秒，大大降低 cpu利用率
            time.sleep(0.1)

    def get_state(self, th: VideoDownloadThread, old_state: str):
        """ 获取下载状态

            Author: Wang Zifan
            Date: 2022/04/28

            Attributes:
                th (VideoDownloadThread): 下载线程
                old_state (str): 旧状态
        """
        # 下载线程正在运行，取 run_state
        if th.is_alive():
            # 线程状态为空，取旧状态
            if th.run_state == "":
                return old_state
            else:
                return th.wav_name + "：" + th.run_state
        # 下载线程停止运行，取 final_state
        else:
            # 线程状态为空，取旧状态
            if th.final_state == "":
                return old_state
            else:
                return th.wav_name + "：" + th.final_state
