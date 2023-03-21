#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Wang Zifan

"""分离视频和音频"""
import os
import threading
import time

import chardet
from moviepy.editor import VideoFileClip


class SplitVideoAudioThread(threading.Thread):
    def __init__(self, thread_id: str, video_path: str, video_output_path: str, audio_output_path: str):
        super(SplitVideoAudioThread, self).__init__()
        self.thread_id = thread_id
        self.video_path = video_path
        self.video_output_path = video_output_path
        self.audio_output_path = audio_output_path
        self.log_path_video = video_output_path + '.log'
        self.log_path_audio = audio_output_path + '.log'
        self.audio_extract_process = ""
        self.video_extract_process = ""
        video = VideoFileClip(video_path)
        # 音视频总时长
        self.duration = float(video.duration)
        video.close()

    def run(self):
        self.split_video_and_audio(self.video_path, self.video_output_path, self.audio_output_path)

    def split_video_and_audio(self, video_path: str, video_output_path: str, audio_output_path: str):
        """ 分离视频和音频

           Author: Wang Zifan
           Date: 2022/04/30

           Attributes:
               video_path (str): 输入的视频路径
               video_output_path (str): 输出的不带声音的视频路径
               audio_output_path (str): 输出的音频路径
       """
        # 提取音频
        video = VideoFileClip(video_path)
        audio = video.audio
        audio.write_audiofile(audio_output_path, write_logfile=True)
        # 获取无声的视频
        video_without_audio = video.without_audio()
        video_without_audio.write_videofile(video_output_path, write_logfile=True, threads=8)
        video.close()


class SplitVideoAudioMonitorThread(threading.Thread):
    def __init__(self, thread_id: str, split_thread: SplitVideoAudioThread):
        super(SplitVideoAudioMonitorThread, self).__init__()
        self.split_thread = split_thread

    def run(self):
        while True:
            # 线程正在运行
            if self.split_thread.is_alive():
                # 音频提取进度判断
                if os.path.isfile(self.split_thread.log_path_audio):
                    # 获取文件编码格式
                    with open(self.split_thread.log_path_audio, 'rb') as f:
                        text = f.read()
                        code = chardet.detect(text)['encoding']
                    with open(self.split_thread.log_path_audio, 'r', encoding=code) as f:
                        # 将每一行存入列表，去除每一行首尾的回车和空格，空行不放入列表
                        line_list = [line.strip() for line in f.readlines() if line.strip() != '']
                        # 如果文件不为空
                        if len(line_list) > 0:
                            last_line = line_list[-1]
                            if 'time=' in last_line:
                                last_line_list = last_line.split(' ')
                                for s in last_line_list:
                                    if 'time=' in s:
                                        time_str = s.split('=')[1]
                                        time_str_list = time_str.split(':')
                                        # 已经完成的秒数
                                        time_num_s = 3600 * float(time_str_list[0]) + 60 * float(
                                            time_str_list[1]) + float(time_str_list[2])
                                        self.split_thread.audio_extract_process = "正在进行音频提取：" + format(
                                            100 * time_num_s / self.split_thread.duration, ".2f") + '% '
                                        break
                            elif 'time=' in "".join(line_list):
                                self.split_thread.audio_extract_process = "音频提取完成"
                # 视频提取已经开始了，音频提取应该结束了，异常判断
                if self.split_thread.video_extract_process != "":
                    if not os.path.isfile(self.split_thread.log_path_audio):
                        self.split_thread.audio_extract_process = "音频提取失败"
                    else:
                        # 获取文件编码格式
                        with open(self.split_thread.log_path_audio, 'rb') as f:
                            text = f.read()
                            code = chardet.detect(text)['encoding']
                        with open(self.split_thread.log_path_audio, 'r', encoding=code) as f:
                            # 将每一行存入列表，去除每一行首尾的回车和空格，空行不放入列表
                            line_list = [line.strip() for line in f.readlines() if line.strip() != '']
                            # 文件为空
                            if len(line_list) == 0:
                                self.split_thread.audio_extract_process = "音频提取失败"
                            elif 'time=' in "".join(line_list):
                                self.split_thread.audio_extract_process = "音频提取完成"
                            else:
                                self.split_thread.audio_extract_process = "音频提取失败"
                # 视频提取进度判断
                if os.path.isfile(self.split_thread.log_path_video):
                    # 获取文件编码格式
                    with open(self.split_thread.log_path_video, 'rb') as f:
                        text = f.read()
                        code = chardet.detect(text)['encoding']
                    with open(self.split_thread.log_path_video, 'r', encoding=code) as f:
                        # 将每一行存入列表，去除每一行首尾的回车和空格，空行不放入列表
                        line_list = [line.strip() for line in f.readlines() if line.strip() != '']
                        # 如果文件不为空
                        if len(line_list) > 0:
                            last_line = line_list[-1]
                            if 'time=' in last_line:
                                last_line_list = last_line.split(' ')
                                for s in last_line_list:
                                    if 'time=' in s:
                                        video_time_str = s.split('=')[1]
                                        video_time_str_list = video_time_str.split(':')
                                        # 已经完成的秒数
                                        video_time_num_s = 3600 * float(video_time_str_list[0]) + 60 * float(
                                            video_time_str_list[1]) + float(video_time_str_list[2])
                                        self.split_thread.video_extract_process = "正在进行视频提取：" + format(
                                            100 * video_time_num_s / self.split_thread.duration, ".2f") + '% '
                                        break
                            elif 'time=' in "".join(line_list):
                                self.split_thread.video_extract_process = "视频提取完成"
            # 线程停止运行
            else:
                # 音频提取进度判断
                if not os.path.isfile(self.split_thread.log_path_audio):
                    self.split_thread.audio_extract_process = "音频提取失败"
                else:
                    # 获取文件编码格式
                    with open(self.split_thread.log_path_audio, 'rb') as f:
                        text = f.read()
                        code = chardet.detect(text)['encoding']
                    with open(self.split_thread.log_path_audio, 'r', encoding=code) as f:
                        # 将每一行存入列表，去除每一行首尾的回车和空格，空行不放入列表
                        line_list = [line.strip() for line in f.readlines() if line.strip() != '']
                        # 文件为空
                        if len(line_list) == 0:
                            self.split_thread.audio_extract_process = "音频提取失败"
                        elif 'time=' in "".join(line_list):
                            self.split_thread.audio_extract_process = "音频提取完成"
                        else:
                            self.split_thread.audio_extract_process = "音频提取失败"
                # 视频提取进度判断
                if not os.path.isfile(self.split_thread.log_path_video):
                    self.split_thread.video_extract_process = "视频提取失败"
                else:
                    # 获取文件编码格式
                    with open(self.split_thread.log_path_video, 'rb') as f:
                        text = f.read()
                        code = chardet.detect(text)['encoding']
                    with open(self.split_thread.log_path_video, 'r', encoding=code) as f:
                        # 将每一行存入列表，去除每一行首尾的回车和空格，空行不放入列表
                        line_list = [line.strip() for line in f.readlines() if line.strip() != '']
                        # 文件为空
                        if len(line_list) == 0:
                            self.split_thread.video_extract_process = "视频提取失败"
                        elif 'time=' in "".join(line_list):
                            self.split_thread.video_extract_process = "视频提取完成"
                        else:
                            self.split_thread.video_extract_process = "视频提取失败"

                # 退出前删除文件
                if os.path.isfile(self.split_thread.log_path_audio):
                    os.remove(self.split_thread.log_path_audio)
                if os.path.isfile(self.split_thread.log_path_video):
                    os.remove(self.split_thread.log_path_video)
                break
            time.sleep(0.25)
