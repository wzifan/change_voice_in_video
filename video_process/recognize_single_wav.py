import pickle

import chardet
import yaml
import torch
import torchaudio
from torchaudio.compliance import kaldi
from wenet.transformer.asr_model import init_asr_model


def recognize_single_wav(
        wav_path: str,
        model_path: str,
        model_config_path: str,
        cmvn_file: str,
        dict_path: str,
        dict_pickle_path: str,
        init_dict: bool = False,
        mode: str = "attention_rescoring",
        ctc_weight: float = 0.5,
        beam_size: int = 10,
        decoding_chunk_size: int = -1,
        num_decoding_left_chunks: int = -1,
        simulate_streaming: bool = False,
        reverse_weight: float = 0.0,
        resample_rate: int = 16000
) -> str:
    """ recognize single wav file

        Args:
            wav_path (str): path of wav file
            model_path (str): path of model
            model_config_path (str): config of model (yaml file)
            cmvn_file (str): path of cmvn file
            dict_path (str): path of dict (txt file)
            dict_pickle_path (str): path of dict pickle object
            init_dict (bool): whether generate dict pickle object
            mode (str): decode mode
            ctc_weight (float): ctc weight for attention rescore
            beam_size (int): beam size for beam search
            decoding_chunk_size (int): decoding chunk for dynamic chunk trained model.
                <0: for decoding, use full chunk.
                >0: for decoding, use fixed chunk size as set.
                0: used for training, it's prohibited here
            num_decoding_left_chunks (int): number of left chunks, the chunk size is decoding_chunk_size.
                >=0: use num_decoding_left_chunks
                <0: use all left chunks
            simulate_streaming (bool): whether do encoder forward in a streaming fashion
            reverse_weight (float): right to left decoder weight
            resample_rate (int): sample rate for recognizing wav file

        Returns:
            sentence_text (str): result of audio recognition
    """
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # 加载配置文件
    with open(model_config_path, 'r') as fin:
        configs = yaml.load(fin, Loader=yaml.FullLoader)
    configs['cmvn_file'] = cmvn_file
    feature_extraction_conf = configs['collate_conf']['feature_extraction_conf']

    # 读取和转换音频
    waveform, sample_rate = torchaudio.load(wav_path)
    waveform = waveform * (1 << 15)
    if resample_rate != sample_rate:
        waveform = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=resample_rate)(waveform)

    # 提取特征
    feats = kaldi.fbank(
        waveform,
        num_mel_bins=feature_extraction_conf['mel_bins'],
        frame_length=feature_extraction_conf['frame_length'],
        frame_shift=feature_extraction_conf['frame_shift'],
        dither=0.0,
        energy_floor=0.0,
        sample_frequency=resample_rate
    )
    feats_lengths = torch.tensor(feats.size(0)).unsqueeze(0)
    feats = feats.unsqueeze(0)
    feats_lengths = feats_lengths.to(device)
    feats = feats.to(device)

    # 初始化模型
    model = init_asr_model(configs)
    model.load_state_dict(torch.load(model_path))
    model.to(device)
    model.eval()

    if init_dict:
        # 初始化词典
        char_dict = {}
        # 获取文件编码格式
        with open(dict_path, 'rb') as f:
            text = f.read()
            code = chardet.detect(text)['encoding']
        with open(dict_path, 'r', encoding=code) as fin:
            for line in fin:
                arr = line.strip().split()
                assert len(arr) == 2
                char_dict[int(arr[1])] = arr[0]
        with open(dict_pickle_path, "wb") as f:
            pickle.dump(char_dict, f)
    else:
        # 加载词典
        with open(dict_pickle_path, "rb") as f:
            char_dict = pickle.load(f)
    eos = len(char_dict) - 1

    # 语音识别
    predict = []
    with torch.no_grad():
        if mode == 'attention_rescoring':
            predict = model.attention_rescoring(
                feats,
                feats_lengths,
                beam_size,
                decoding_chunk_size=decoding_chunk_size,
                num_decoding_left_chunks=num_decoding_left_chunks,
                ctc_weight=ctc_weight,
                simulate_streaming=simulate_streaming,
                reverse_weight=reverse_weight
            )
        elif mode == 'attention':
            predict = model.recognize(
                feats,
                feats_lengths,
                beam_size=beam_size,
                decoding_chunk_size=decoding_chunk_size,
                num_decoding_left_chunks=num_decoding_left_chunks,
                simulate_streaming=simulate_streaming
            )
            predict = predict[0].tolist()
        elif mode == 'ctc_greedy_search':
            predict = model.ctc_greedy_search(
                feats,
                feats_lengths,
                decoding_chunk_size=decoding_chunk_size,
                num_decoding_left_chunks=num_decoding_left_chunks,
                simulate_streaming=simulate_streaming
            )
            predict = predict[0]
        elif mode == 'ctc_prefix_beam_search':
            predict = model.ctc_prefix_beam_search(
                feats,
                feats_lengths,
                beam_size=beam_size,
                decoding_chunk_size=decoding_chunk_size,
                num_decoding_left_chunks=num_decoding_left_chunks,
                simulate_streaming=simulate_streaming
            )
    # 将token序列转为字序列
    sentence_text = ''
    for w in predict:
        if w == eos:
            break
        sentence_text += char_dict[w]
    # 返回识别结果
    return sentence_text

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
# wav_path = '../output/splited_audio/视频001/vocals.wav'
# text = recognize_single_wav(wav_path, **kwargs)
# print(text)
