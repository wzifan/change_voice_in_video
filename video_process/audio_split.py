#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Wang Zifan

"""说明"""
import os
import subprocess
import threading
import time
import chardet


class SplitAudioThread(threading.Thread):
    def __init__(self, thread_id: str, audio_path: str, output_dir: str):
        super(SplitAudioThread, self).__init__()
        self.thread_id = thread_id
        self.audio_path = audio_path
        self.output_dir = output_dir
        self.log_path = os.path.join(self.output_dir, '.'.join(os.path.basename(audio_path).split('.')[0:-1]) + '.log')
        # 创建日志所需文件夹
        if not os.path.exists(os.path.dirname(self.log_path)):
            os.makedirs(os.path.dirname(self.log_path))
        self.split_process = ""

    def run(self):
        with open(self.log_path, 'w', encoding="utf-8") as log_file:
            export_exe = True
            # 如果代码用于导出exe文件，则需要加上'./'，并在导出的exe同目录下加入ffmpeg.exe及其相关文件(如ffplay.exe、ffprobe.exe)
            if export_exe:
                startup = subprocess.STARTUPINFO()
                startup.dwFlags = subprocess.STARTF_USESHOWWINDOW
                startup.wShowWindow = subprocess.SW_HIDE
                subprocess.run(os.path.join(os.path.abspath('./'), 'spleeter') + " separate -p spleeter:2stems -o " +
                               self.output_dir + " " + self.audio_path,
                               stdout=log_file, stderr=log_file, shell=False, startupinfo=startup)
            else:
                subprocess.run("spleeter separate -p spleeter:2stems -o " + self.output_dir + " " + self.audio_path,
                               stdout=log_file, stderr=log_file, shell=False)


class SplitAudioMonitorThread(threading.Thread):
    def __init__(self, thread_id: str, split_audio_thread: SplitAudioThread):
        super(SplitAudioMonitorThread, self).__init__()
        self.thread_id = thread_id
        self.split_audio_thread = split_audio_thread

    def run(self):
        while True:
            # 线程正在运行
            if self.split_audio_thread.is_alive():
                if os.path.isfile(self.split_audio_thread.log_path):
                    # 获取文件编码格式
                    with open(self.split_audio_thread.log_path, 'rb') as f:
                        text = f.read()
                        code = chardet.detect(text)['encoding']
                    with open(self.split_audio_thread.log_path, 'r', encoding=code) as f:
                        # 将每一包含'INFO:'的行存入列表，去除每一行首尾的回车和空格，空行不放入列表
                        line_list = [line.strip() for line in f.readlines() if line.strip() != '' and 'INFO:' in line]
                        # 如果文件不为空
                        if len(line_list) > 0:
                            if 'Downloading model' in line_list[-1]:
                                self.split_audio_thread.split_process = "正在下载模型"
                            elif 'Validating' in line_list[-1]:
                                self.split_audio_thread.split_process = "模型下载完成\n正在校验"
                            elif 'Extracting' in line_list[-1]:
                                self.split_audio_thread.split_process = "模型下载完成\n校验完成\n正在解压模型"
                            elif 'extracted' in line_list[-1]:
                                self.split_audio_thread.split_process = "模型下载完成\n校验完成\n模型解压完成\n正在进行语音分离"
                            elif 'succesfully' in line_list[-1] and len(line_list) >= 6:
                                self.split_audio_thread.split_process = "模型下载完成\n校验完成\n模型解压完成\n语音分离完成"
                            elif 'succesfully' in line_list[-1] and len(line_list) <= 5:
                                self.split_audio_thread.split_process = "语音分离完成"
            # 线程停止运行
            else:
                if not os.path.isfile(self.split_audio_thread.log_path):
                    self.split_audio_thread.split_process = "语音分离失败"
                else:
                    # 获取文件编码格式
                    with open(self.split_audio_thread.log_path, 'rb') as f:
                        text = f.read()
                        code = chardet.detect(text)['encoding']
                    with open(self.split_audio_thread.log_path, 'r', encoding=code) as f:
                        # 将每一包含'INFO:'的行存入列表，去除每一行首尾的回车和空格，空行不放入列表
                        line_list = [line.strip() for line in f.readlines() if line.strip() != '' and 'INFO:' in line]
                        # 文件为空
                        if len(line_list) == 0:
                            self.split_audio_thread.split_process = "语音分离失败"
                        elif 'succesfully' in "".join(line_list) and len(line_list) >= 6:
                            self.split_audio_thread.split_process = "模型下载完成\n校验完成\n模型解压完成\n语音分离完成"
                        elif 'succesfully' in "".join(line_list) and len(line_list) <= 5:
                            self.split_audio_thread.split_process = "语音分离完成"
                        else:
                            self.split_audio_thread.split_process = "语音分离失败"
                # 退出前删除文件
                if os.path.isfile(self.split_audio_thread.log_path):
                    os.remove(self.split_audio_thread.log_path)
                break
            time.sleep(0.25)
