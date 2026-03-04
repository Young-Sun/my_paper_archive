# Qwen3-TTS Technical Report

!!! warning "Stage 1 only"
    Stage 2 refinement was not performed. Methods/Findings may be limited.

**Link**: https://arxiv.org/abs/2601.15621  
**Authors**: Hangrui Hu, Xinfa Zhu, Ting He, Dake Guo, Bin Zhang, Xiong Wang, Zhifang Guo, Ziyue Jiang, Hongkun Hao, Zishan Guo, Xinyu Zhang, Pei Zhang, Baosong Yang, Jin Xu, Jingren Zhou, Junyang Lin  
**Institution**:   
**Venue**: arXiv:2601.15621 [cs.SD] (2026)  
**Model**: `claude-sonnet-4-5-20250929`

---
## Abstract

In this report, we present the Qwen3-TTS series, a family of advanced multilingual, controllable, robust, and streaming text-to-speech models. Qwen3-TTS supports state-of-the-art 3-second voice cloning and description-based control, allowing both the creation of entirely novel voices and fine-grained manipulation over the output speech. Trained on over 5 million hours of speech data spanning 10 languages, Qwen3-TTS adopts a dual-track LM architecture for real-time synthesis, coupled with two speech tokenizers: 1) Qwen-TTS-Tokenizer-25Hz is a single-codebook codec emphasizing semantic content, which offers seamlessly integration with Qwen-Audio and enables streaming waveform reconstruction via a block-wise DiT. 2) Qwen-TTS-Tokenizer-12Hz achieves extreme bitrate reduction and ultra-low-latency streaming, enabling immediate first-packet emission ($97\,\mathrm{ms}$) through its 12.5 Hz, 16-layer multi-codebook design and a lightweight causal ConvNet. Extensive experiments indicate state-of-the-art performance across diverse objective and subjective benchmark (e.g., TTS multilingual test set, InstructTTSEval, and our long speech test set). To facilitate community research and development, we release both tokenizers and models under the Apache 2.0 license.


---
## Summary

### 1. Abstract 요약

Qwen3-TTS는 알리바바에서 개발한 다국어 지원, 제어 가능, 안정적, 스트리밍 가능한 대규모 text-to-speech 모델 시리즈입니다. 이 시스템은 3초의 음성만으로 voice cloning이 가능하며, 자연어 설명을 통해 완전히 새로운 목소리를 생성하거나 음성 출력을 세밀하게 조작할 수 있습니다. 10개 언어에 걸친 500만 시간 이상의 음성 데이터로 학습되었으며, 실시간 합성을 위한 dual-track LM 아키텍처와 두 가지 speech tokenizer를 채택했습니다.

첫 번째 tokenizer인 Qwen-TTS-Tokenizer-25Hz는 semantic content를 강조하는 single-codebook codec으로, Qwen-Audio와 원활하게 통합되며 block-wise DiT를 통한 스트리밍 waveform 재구성을 지원합니다. 두 번째 tokenizer인 Qwen-TTS-Tokenizer-12Hz는 극도로 낮은 bitrate와 ultra-low-latency 스트리밍을 달성하며, 12.5 Hz, 16-layer multi-codebook 설계와 경량 causal ConvNet을 통해 97ms의 즉각적인 first-packet 생성을 가능하게 합니다.

Qwen3-TTS는 다양한 객관적·주관적 benchmark(TTS multilingual test set, InstructTTSEval, long speech test set 등)에서 state-of-the-art 성능을 달성했습니다. 특히 zero-shot voice cloning에서 최저 Word Error Rate(WER)를 기록했으며, MiniMax, ElevenLabs 같은 상용 시스템 대비 10개 언어 모두에서 우수한 화자 유사도를 보였습니다. 또한 복잡한 자연어 instruction을 따르는 능력이 뛰어나 GPT-4o-mini-tts를 능가했으며, 10분 이상의 자연스럽고 유창한 장문 음성 생성이 가능합니다. 연구자들과 개발자 커뮤니티를 위해 모든 tokenizer와 모델을 Apache 2.0 라이선스로 공개합니다.

### 2. 한 줄 핵심 요약

Qwen3-TTS는 dual-track LM 아키텍처와 두 가지 특화된 speech tokenizer를 활용하여 97ms의 ultra-low-latency 스트리밍과 3초 voice cloning, 자연어 기반 세밀한 음성 제어를 지원하는 다국어 TTS 시스템입니다.

### 3. Contribution

1. **Dual Speech Tokenizer 설계**: Qwen-TTS-Tokenizer-25Hz(semantic 중심, single-codebook)와 Qwen-TTS-Tokenizer-12Hz(ultra-low-latency, multi-codebook) 두 가지 complementary tokenizer 개발
2. **Ultra-Low-Latency 스트리밍**: 97ms(0.6B) / 101ms(1.7B)의 first-packet latency 달성, 12.5 Hz multi-codebook과 lightweight causal ConvNet 사용
3. **Dual-Track LM 아키텍처**: 텍스트와 음향 토큰을 channel axis로 결합하여 실시간 스트리밍 텍스트 입력 및 오디오 출력 지원
4. **대규모 다국어 학습**: 10개 언어, 500만 시간 이상의 음성 데이터로 pre-training 및 post-training (DPO, GSPO 포함)
5. **State-of-the-Art 성능**: Zero-shot voice cloning에서 최저 WER, cross-lingual 시나리오(중국어→한국어 등)에서 현저한 성능 향상, instruction-following에서 GPT-4o-mini-tts 초과
6. **모델 및 Tokenizer 공개**: Apache 2.0 라이선스로 전체 모델 family와 tokenizer 오픈소스 제공

### 4. Methods

#### 핵심 아이디어
- **Discrete Speech Representation**: 음성을 discrete token으로 변환하여 autoregressive LM으로 안정적 합성
- **Semantic-Acoustic Balance**: 순수 semantic tokenizer는 표현력이 부족하고, 순수 acoustic tokenizer는 low-level detail 과다로 LM 모델링 복잡화. 이를 해결하기 위해 두 가지 tokenizer 전략 채택
- **Streaming 최적화**: Block-wise attention, causal architecture, MTP(Multi-Token Prediction) 모듈로 latency 최소화

#### 모델 구조

**Tokenizers:**
1. **Qwen-TTS-Tokenizer-25Hz**:
   - 25 Hz single-codebook tokenizer
   - Qwen2-Audio 기반, 2-stage training (Stage 1: ASR task에서 continue pretraining + VQ layer 추가, Stage 2: mel-spectrogram decoder로 fine-tuning)
   - Streaming: Block-wise DiT (4 blocks receptive field: 현재 block, 3-block lookback, 1-block lookahead) + Flow Matching + BigVGAN
   
2. **Qwen-TTS-Tokenizer-12Hz**:
   - 12.5 Hz, 16-layer multi-codebook (1 semantic + 15 acoustic RVQ)
   - Mimi 아키텍처 기반 semantic-acoustic disentangled quantization
   - GAN-based training: WavLM teacher guidance (semantic), multi-scale mel-spectrogram reconstruction loss
   - Fully causal encoder/decoder for streaming

**LM Architecture:**
- **Qwen3-TTS-25Hz**: Single-level speech token 예측, chunk-wise DiT로 waveform 재구성
- **Qwen3-TTS-12Hz**: Dual-track representation (text + acoustic token concatenation), hierarchical prediction (backbone으로 zeroth codebook 예측 → MTP module로 residual codebooks 생성), single-frame instant generation

**Model Sizes**: 0.6B, 1.7B variants 제공

#### 데이터셋
- **Pre-training**: 500만 시간 이상, 10개 언어의 다국어 음성 데이터
- **Training Stages**:
  - S1 (General): 다국어 일반 데이터로 기본 text-to-speech mapping 학습
  - S2 (High-Quality): 고품질 데이터로 continual pre-training, hallucination 완화
  - S3 (Long-Context): 최대 토큰 길이 8,192 → 32,768 확장, long speech upsampling
- **Post-training**: DPO (human feedback 기반 preference pairs), GSPO (rule-based rewards), speaker fine-tuning

#### 평가방법

**Objective Metrics:**
- Word Error Rate (WER): ASR 기반 텍스트 정확도
- Speaker Similarity: 화자 임베딩 기반 유사도
- Pronunciation: 발음 정확도

**Subjective Metrics:**
- Mean Opinion Score (MOS): 자연스러움, 품질, 화자 유사도 등 인간 평가 (1~5점)

**Benchmarks:**
- Seed-TTS test set: Zero-shot voice cloning 평가 (10개 언어)
- Cross-lingual scenarios: 언어 간 voice transfer (중국어↔한국어, 영어↔일본어 등)
- InstructTTSEval: Instruction-following capability
- Long speech test set: 10분 이상 장문 음성 생성 안정성

#### 실험 결과

**Zero-shot Voice Cloning:**
- 10개 언어 모두에서 MiniMax, ElevenLabs 등 상용 시스템 대비 최저 WER 달성
- Speaker similarity에서도 모든 언어에서 우수한 성능

**Cross-lingual Transfer:**
- 중국어→한국어: 상당한 error rate 감소
- 다양한 언어 쌍에서 탁월한 적응력

**Instruction Following:**
- GPT-4o-mini-tts 대비 target speaker manipulation에서 우수한 성능
- 복잡한 자연어 instruction 처리 능력 (probabilistically activated thinking pattern 적용)

**Long-form Generation:**
- 10분 이상의 자연스럽고 유창한 음성 생성, chunk-based 시스템의 전형적인 artifact 없음

**Latency:**
- First-packet latency: 0.6B (97ms), 1.7B (101ms)
- Streaming efficiency: 다양한 concurrency level에서 안정적 성능 (표 2 참조)

### 5. Findings

#### Objective Evaluations
- **Zero-shot Voice Cloning**: Seed-TTS benchmark 10개 언어에서 최저 WER, 모든 언어에서 상용 시스템(MiniMax, ElevenLabs) 대비 우수한 speaker similarity
- **Cross-lingual Transfer**: 중국어→한국어, 영어→일본어 등 challenging language pairs에서 현저한 error rate 감소 및 적응력 향상
- **Pronunciation & Robustness**: 복잡한 텍스트, 다국어 혼합 입력에서도 안정적 발음 및 생성 품질 유지

#### Subjective Evaluations
- **Naturalness**: 1.7B 모델이 state-of-the-art, human-like 품질 달성. ASR 관련 메트릭에 overfitting하지 않고 perceptual quality 극대화
- **Instruction Following**: InstructTTSEval에서 GPT-4o-mini-tts 초과. Voice design, fine-grained control 등 복잡한 instruction에서도 높은 정확도
- **Long-form Stability**: 10분 이상 연속 음성 생성에서 chunk-based 시스템의 전형적인 artifact(불연속성, 품질 저하) 없이 자연스럽고 일관된 출력
- **User Preference**: Human evaluation에서 다양한 task(voice cloning, voice design, multilingual generation 등)에 걸쳐 높은 선호도

### 6. Notes

#### 의미
- **Unified Framework**: Voice cloning, cross-lingual transfer, instruction-based control 등 다양한 음성 생성 task를 단일 autoregressive framework로 통합
- **Practical Deployment**: Ultra-low-latency streaming (97~101ms)으로 real-time 서비스 및 interactive application에 적합
- **LLM Integration**: Discrete representation 기반으로 LLM과 seamless 통합 가능, 향후 omni-capable audio system으로 확장 가능성
- **Open Research**: Apache 2.0 라이선스로 모델 및 tokenizer 공개, 커뮤니티 연구 활성화 기대

#### 한계
1. **언어 커버리지**: 현재 10개 언어 지원, 향후 더 많은 언어로 확장 필요
2. **Stylistic Control Granularity**: 더 세밀한 스타일 제어 기능 탐색 필요
3. **Long-horizon Error Accumulation**: Autoregressive 모델 특성상 장문 생성 시 누적 오류 가능성 (현재는 완화되었으나 완전 해결은 아님)
4. **Computational Cost**: 1.7B 모델은 고품질 출력 제공하나, 일부 edge device에서는 0.6B variant 필요
5. **Evaluation Scope**: Subjective evaluation이 일부 benchmark에 국한, 더 광범위한 사용자 연구 필요

#### 코드/데모
- **공개 예정**: 모든 tokenizer 및 모델 family를 Apache 2.0 라이선스로 공개
- **Repository**: 보고서 발표 시점 기준 공식 링크 미명시 (일반적으로 Hugging Face 또는 Alibaba GitHub에 공개 예상)
- **Demo**: 음성 샘플 및 interactive demo 제공 가능성 높음 (보고서 내 구체적 링크 없음)
- **Integration**: Qwen3 LM family 및 vLLM engine과의 통합 지원, torch.compile 및 CUDA Graph 최적화 적용


---
### 7. Figures/Tables

**Figure 1: Qwen3-TTS is a multilingual, controllable, robust, and streaming text-to-speech model. Based**

![Figure 1: Qwen3-TTS is a multilingual, controllable, robust, and streaming text-to-speech model. Based](figures/qwen3-tts_technical_report/fig_p1_0.png)

**(p.1)**

![(p.1)](figures/qwen3-tts_technical_report/fig_p1_1.jpeg)

**(p.1)**

![(p.1)](figures/qwen3-tts_technical_report/fig_p1_2.png)

**Figure 2: Overview of Qwen-TTS tokenizers.**

![Figure 2: Overview of Qwen-TTS tokenizers.](figures/qwen3-tts_technical_report/fig_p3_3.png)

**Figure 3: The overview of Qwen3-TTS. Dashed lines represent optional.**

![Figure 3: The overview of Qwen3-TTS. Dashed lines represent optional.](figures/qwen3-tts_technical_report/fig_p4_4.png)
