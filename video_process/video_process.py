#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Wang Zifan

"""说明"""
import os
import threading
import shutil
import time

from split_video_and_audio import SplitVideoAudioThread, SplitVideoAudioMonitorThread
from audio_split import SplitAudioThread, SplitAudioMonitorThread
from split_and_recognize_wav import SplitAndRecognizeAudioMainThread


class VideoProcessMainThread(threading.Thread):
    """ 视频分离和语音识别主线程

        Author: Wang Zifan
        Date: 2022/05/04

        Attributes:
            thread_id (str): 线程id
            video_path (str): 视频路径
            export_dir (str): 目标目录
    """

    def __init__(self, thread_id: str, video_path: str, export_dir: str):
        super(VideoProcessMainThread, self).__init__()
        self.thread_id = thread_id
        self.video_path = os.path.abspath(video_path)
        self.export_dir = os.path.abspath(export_dir)
        if not os.path.exists(self.export_dir):
            os.makedirs(self.export_dir)
        # 分离进度
        self.split_process = []
        # 语音识别结果
        self.asr_result = []

    def run(self):
        # 1.视频格式转化

        video_name_split = os.path.basename(self.video_path).split('.')
        origin_format = video_name_split[-1]
        video_format = 'mp4'
        if origin_format == video_format:
            shutil.copy(self.video_path, self.export_dir)
            video_name = os.path.basename(self.video_path)
            new_video_path = os.path.join(self.export_dir, video_name)
        else:
            if len(video_name_split) == 1:
                video_name = video_name_split[-1] + '.mp4'
            else:
                video_name = '.'.join(video_name_split[0:-1]) + '.' + video_format
            new_video_path = os.path.join(self.export_dir, video_name)
            self.split_process.append("<视频格式转化>")
            self.split_process.append("正在进行视频格式转化")
            os.system("ffmpeg -i " + self.video_path + " -c copy -y " + new_video_path)
            self.split_process[-1] = "视频格式转化完成"

        # 2.音视频分离
        base_name = '.'.join(video_name.split('.')[0:-1])
        audio_format = 'wav'
        video_without_audio_name = base_name + '_without_audio.' + video_format
        video_without_audio_path = os.path.join(self.export_dir, video_without_audio_name)
        split_audio_name = base_name + '.' + audio_format
        split_audio_path = os.path.join(self.export_dir, split_audio_name)
        self.split_process.append("<音视频分离>")
        self.split_process.append("")
        self.split_process.append("")
        split_video_audio_thread = SplitVideoAudioThread('1', new_video_path, video_without_audio_path,
                                                         split_audio_path)
        split_video_audio_monitor_thread = SplitVideoAudioMonitorThread('1', split_video_audio_thread)
        split_video_audio_thread.start()
        split_video_audio_monitor_thread.start()
        while True:
            self.split_process[-2] = split_video_audio_thread.audio_extract_process
            self.split_process[-1] = split_video_audio_thread.video_extract_process
            if not split_video_audio_monitor_thread.is_alive():
                break
            time.sleep(0.1)

        # 3.语音分离
        self.split_process.append("<语音分离>")
        if os.path.exists("./pretrained_models"):
            self.split_process.append("正在进行语音分离")
        self.split_process.append("")
        split_audio_output_dir = os.path.join(self.export_dir, "splited_audio")
        split_audio_thread = SplitAudioThread('1', split_audio_path, split_audio_output_dir)
        split_audio_monitor_thread = SplitAudioMonitorThread('1', split_audio_thread)
        split_audio_thread.start()
        split_audio_monitor_thread.start()
        while True:
            self.split_process[-1] = split_audio_thread.split_process
            if not split_audio_monitor_thread.is_alive():
                break
            time.sleep(0.1)

        # 4.语音切分和识别
        # 语音识别参数
        kwargs = {
            'model_path': './model_for_asr/final.pt',
            'model_config_path': './model_for_asr/train.yaml',
            'cmvn_file': './model_for_asr/global_cmvn',
            'dict_path': './model_for_asr/lang_char.txt',
            'dict_pickle_path': './model_for_asr/char_dict.pkl',
            'init_dict': False,
            'mode': 'attention_rescoring',
            'ctc_weight': 0.5,
            'beam_size': 10,
            'decoding_chunk_size': -1,
            'num_decoding_left_chunks': -1,
            'simulate_streaming': False,
            'reverse_weight': 0.0,
            'resample_rate': 16000
        }
        # 被切分和识别的音频路径
        self.split_process.append("<语音识别>")
        audio_path_for_asr = os.path.join(os.path.join(split_audio_output_dir, base_name), 'vocals.wav')
        result_txt_path = os.path.join(self.export_dir, base_name + '_asr_result.txt')
        asr_thread = SplitAndRecognizeAudioMainThread('1', audio_path_for_asr, **kwargs)
        asr_thread.start()
        self.split_process.append("正在进行语音识别")
        while True:
            self.asr_result = asr_thread.asr_result
            if not asr_thread.is_alive():
                break
            time.sleep(0.1)
        # 存储语音识别结果
        with open(result_txt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.asr_result))
        self.split_process.append("语音识别完成")

        # 5.清理文件
        # 删除语音分离输出的文件夹及其下所有文件
        if os.path.isdir(split_audio_output_dir):
            self.clean_dir(split_audio_output_dir)
            os.rmdir(split_audio_output_dir)
        # 删除复制进来的原音频文件
        if os.path.isfile(new_video_path):
            os.remove(new_video_path)
        # 删除从视频分离出来的音频文件
        # if os.path.isfile(split_audio_path):
        #     os.remove(split_audio_path)

    def clean_dir(self, dir_path):
        # 原文链接：https: // blog.csdn.net / wwwcaifeng / article / details / 119836725
        if os.path.isdir(dir_path):
            paths = os.listdir(dir_path)
            for path in paths:
                file_path = os.path.join(dir_path, path)
                # 如果是文件则直接删除
                if os.path.isfile(file_path):
                    os.remove(file_path)
                # 如果是文件夹则清理之后再删除
                if os.path.isdir(file_path):
                    self.clean_dir(file_path)
                    os.rmdir(file_path)
