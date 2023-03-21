#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Author: Wang Zifan

"""切分和识别音频"""
import os
import threading
import time
import wave
import webrtcvad
import sox

from recognize_single_wav import recognize_single_wav


class SplitAndRecognizeAudioMainThread(threading.Thread):
    """ 语音切分和识别主线程

        Author: Wang Zifan
        Date: 2022/05/09

        Attributes:
            thread_id (str): 线程id
            wav_path (str): 音频路径
            kwargs (str): 语音识别参数
    """

    def __init__(self, thread_id: str, wav_path: str, **kwargs):
        super(SplitAndRecognizeAudioMainThread, self).__init__()
        self.wav_path = wav_path
        self.kwargs = kwargs
        # 存放语音识别结果的列表
        self.asr_result = []

    def run(self):
        self.split_and_recognize_wav(self.wav_path, **self.kwargs)

    def split_and_recognize_wav(self, wav_path: str, **kwargs):
        # 音频名称（不带后缀）
        base_name = '.'.join(os.path.basename(wav_path).split('.')[0:-1])
        # 音频文件类型
        audio_format = os.path.basename(wav_path).split('.')[-1]
        # 被识别的音频所在目录
        dir_path = os.path.dirname(wav_path)
        # 用sox对原音频进行采样率、通道数的转变（系统需安装sox并配置环境变量）
        tfm = sox.Transformer()
        tfm.rate(16000)
        tfm.channels(1)
        # 转变后的音频存放路径
        wav_path_changed = os.path.join(dir_path, base_name + "_temp." + audio_format)
        # 转变音频
        tfm.build(wav_path, wav_path_changed)

        # 读取更改后的音频文件
        rf = wave.open(wav_path_changed, "rb")
        # 获取音频参数
        # 通道数，vad只支持单通道
        channels = rf.getnchannels()
        # 每个通道的采样率，vad只支持8k、16k、32k和48k
        rate = rf.getframerate()
        # 采样大小（每次采样数据的字节数），vad只支持2
        samp_width = rf.getsampwidth()
        # vad采样大小只支持2
        assert samp_width == 2

        # 定义帧长，vad只支持10、20和30ms
        frame_duration_ms = 20
        # 读取数据块大小（每一帧每个通道上的采样次数）（除以通道数和乘以采样大小分之2来进行勉强的纠正）
        chunk_size = int(rate * frame_duration_ms / 1000 / channels * 2 / samp_width)
        # 判断人声的敏感程度（一般为1~3,3为最敏感）
        vad = webrtcvad.Vad(3)

        buffer_data = b''
        temp = []
        file_num = 1
        # 上一段是否为人声
        pre_is_speech = False
        # 当前已读的帧数
        num_frames_i = 0
        while True:
            # 读取一帧的数据
            data = rf.readframes(chunk_size)
            num_frames_i += 1
            len_data = len(data)
            # 如果这一帧是最后一帧
            if len_data < chunk_size * channels * samp_width:
                buffer_data += data
                # 如果上一段有人声，则将数据写入文件
                if pre_is_speech:
                    temp_wav_path = os.path.join(dir_path,
                                                 base_name + '_' + str(file_num).zfill(4) + '.' + audio_format)
                    wf = wave.open(temp_wav_path, "wb")
                    wf.setnchannels(channels)
                    wf.setsampwidth(samp_width)
                    wf.setframerate(rate)
                    wf.writeframes(buffer_data)
                    wf.close()
                    # 识别
                    recognize_txt = recognize_single_wav(temp_wav_path, **kwargs)
                    self.asr_result.append(recognize_txt)
                    # 删除这句话的音频文件
                    os.remove(temp_wav_path)
                    print(recognize_txt)
                buffer_data = b''
                temp = []
                # 结束循环
                break
            # 否则
            else:
                is_speech = vad.is_speech(data, rate)
            # 将这一帧的数据和判断结果放入缓存
            buffer_data += data
            temp += [is_speech]

            # buffer_data里面包含数据的帧数
            numframes_buffer_data = int(len(buffer_data) / chunk_size / 2)
            # cache_size帧里面有大于等于threshold帧是人声，就认为这一段(cache_size帧)是人声
            # 根据buffer_data里面包含数据的帧数动态调整切分窗口
            # 小于3秒，什么都不做。如果连续1秒没人声，则删除这1秒
            if numframes_buffer_data <= 150:
                cache_size = 0
                threshold = 0
                # 每30帧判断一次，判断当前buffer_data里面的数据是否为人声
                if numframes_buffer_data % 30 == 0:
                    # 不是人声，则清空缓存
                    if sum(temp) < numframes_buffer_data / 10:
                        pre_is_speech = False
                        buffer_data = b''
                        temp = []
                    # 是人声。本阶段最后一次判断时，清空temp,以便后续判断
                    else:
                        pre_is_speech = True
                        if numframes_buffer_data == 150:
                            temp = []
            # 3到5秒，正常切分
            elif numframes_buffer_data < 250:
                cache_size = 10
                threshold = 2
            # 5到7秒，按较小的窗口切分
            elif numframes_buffer_data < 350:
                cache_size = 5
                threshold = 2
            # 7到9秒，按更小的窗口切分
            elif numframes_buffer_data < 450:
                cache_size = 3
                threshold = 2
            # 9到16秒，逐一判断
            elif numframes_buffer_data < 800:
                cache_size = 1
                threshold = 1
            # 16秒，达到最大长度，强制切分，将buffer_data里面的数据写入文件并语音识别，然后清空缓存，回归初始状态
            else:
                cache_size = 0
                threshold = 0
                pre_is_speech = False
                temp_wav_path = os.path.join(dir_path, base_name + '_' + str(file_num).zfill(4) + '.' + audio_format)
                wf = wave.open(temp_wav_path, "wb")
                file_num += 1
                wf.setnchannels(channels)
                wf.setsampwidth(samp_width)
                wf.setframerate(rate)
                wf.writeframes(buffer_data)
                wf.close()
                # 识别
                recognize_txt = recognize_single_wav(temp_wav_path, **kwargs)
                self.asr_result.append(recognize_txt)
                print(recognize_txt)
                # 删除这句话的音频文件
                os.remove(temp_wav_path)
                buffer_data = b''
                temp = []

            # 如果缓存满了
            if len(temp) >= cache_size > 0:
                num_is_speech = sum(temp)
                # cache_size帧里面有大于等于threshold帧是人声，就认为这一段(cache_size帧)是人声
                if num_is_speech >= threshold:
                    # 如果是人声，清空判断结果缓存
                    pre_is_speech = True
                    temp = []
                # 如果这一段不是人声且上一段是人声，就将缓存中的所有数据写入文件并清空缓存
                elif pre_is_speech == True:
                    pre_is_speech = False
                    temp_wav_path = os.path.join(dir_path,
                                                 base_name + '_' + str(file_num).zfill(4) + '.' + audio_format)
                    wf = wave.open(temp_wav_path, "wb")
                    file_num += 1
                    wf.setnchannels(channels)
                    wf.setsampwidth(samp_width)
                    wf.setframerate(rate)
                    wf.writeframes(buffer_data)
                    wf.close()
                    # 识别
                    recognize_txt = recognize_single_wav(temp_wav_path, **kwargs)
                    self.asr_result.append(recognize_txt)
                    print(recognize_txt)
                    # 删除这句话的音频文件
                    os.remove(temp_wav_path)
                    buffer_data = b''
                    temp = []
                # 如果这一段不是人声且上一段也不是人声
                else:
                    # 如果后(threshold-1)帧为人声，则认为这一段是人声
                    if 0 < num_is_speech == sum(temp[cache_size - threshold + 1:cache_size]):
                        pre_is_speech = True
                        temp = []
                    # 否则清空缓存
                    else:
                        buffer_data = b''
                        temp = []
        rf.close()
        os.remove(wav_path_changed)

# kwargs = {
#     'model_path': '../exp/final.pt',
#     'model_config_path': '../exp/train.yaml',
#     'cmvn_file': '../exp/global_cmvn',
#     'dict_path': '../exp/lang_char.txt',
#     'dict_pickle_path': '../exp/char_dict.pkl',
#     'init_dict': False,
#     'mode': 'attention_rescoring',
#     'ctc_weight': 0.5,
#     'beam_size': 10,
#     'decoding_chunk_size': -1,
#     'num_decoding_left_chunks': -1,
#     'simulate_streaming': False,
#     'reverse_weight': 0.0,
#     'resample_rate': 16000
# }
# th = SplitAndRecognizeAudioMainThread('1', '../output/splited_audio/视频001/vocals.wav', **kwargs)
# th.start()
# while True:
#     print(th.asr_result)
#     if not th.is_alive():
#         break
#     time.sleep(0.5)
