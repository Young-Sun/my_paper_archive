---
# Attention Is All You Need

> :warning: **Stage 1 only** - Stage 2 refinement was not performed.

**Link**: https://arxiv.org/abs/1706.03762  
**Authors**: Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser, Illia Polosukhin  
**Institution**:   
**Venue**: arXiv:1706.03762 [cs.CL] (2017)  
**Model**: `claude-sonnet-4-5-20250929`

---
## Abstract

The dominant sequence transduction models are based on complex recurrent or convolutional neural networks in an encoder-decoder configuration. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results, including ensembles by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.8 after training for 3.5 days on eight GPUs, a small fraction of the training costs of the best models from the literature. We show that the Transformer generalizes well to other tasks by applying it successfully to English constituency parsing both with large and limited training data.


---
## Summary

# Attention Is All You Need - 논문 분석

### 1. Abstract 요약
이 논문은 기존의 sequence transduction 모델이 복잡한 recurrent 또는 convolutional neural network에 의존하던 것과 달리, attention mechanism만으로 구성된 새로운 네트워크 구조인 Transformer를 제안합니다. Transformer는 recurrence와 convolution을 완전히 배제하고 오직 attention mechanism만을 사용하여, 기존 모델들보다 우수한 성능을 달성하면서도 병렬화가 용이하고 학습 시간이 크게 단축되었습니다. WMT 2014 English-to-German 번역 작업에서 28.4 BLEU를 달성하여 기존 최고 성능을 2 BLEU 이상 개선했으며, English-to-French 번역에서는 8개의 GPU로 3.5일 학습하여 41.8 BLEU의 새로운 SOTA를 수립했습니다. 또한 English constituency parsing 작업에도 성공적으로 적용하여 Transformer의 일반화 능력을 입증했습니다.

### 2. 한 줄 핵심 요약
Recurrence와 convolution을 완전히 제거하고 오직 attention mechanism만으로 구성된 Transformer 아키텍처를 제안하여, machine translation에서 SOTA를 달성하고 병렬 학습을 가능하게 만든 혁신적 연구입니다.

### 3. Contribution
- **Transformer 아키텍처 제안**: Recurrent 및 convolutional layer 없이 전적으로 attention mechanism에만 기반한 최초의 sequence transduction 모델
- **Multi-headed self-attention**: Encoder-decoder 구조에서 recurrent layer를 multi-headed self-attention으로 대체
- **Scaled dot-product attention**: 효율적인 attention 계산 메커니즘 도입
- **병렬화 및 학습 효율성**: 기존 RNN 기반 모델 대비 훨씬 빠른 학습 속도와 높은 병렬화 가능성
- **SOTA 달성**: WMT 2014 English-to-German 및 English-to-French 번역 작업에서 새로운 최고 성능 기록
- **일반화 능력**: English constituency parsing 등 다른 작업에도 성공적으로 적용 가능함을 입증

### 4. Methods

#### 핵심 아이디어
- **Attention-only 아키텍처**: Sequential computation의 한계를 극복하기 위해 recurrence를 제거하고 attention mechanism만으로 모델 구성
- **Self-attention**: 입력 sequence의 모든 위치 간 관계를 직접적으로 모델링하여 long-range dependency 문제 해결
- **Position encoding**: Recurrence가 없어 위치 정보를 명시적으로 주입하기 위한 positional encoding 사용
- **Parallelization**: Recurrent 연산 제거로 학습 시 높은 수준의 병렬 처리 가능

#### 모델 구조
1. **Encoder-Decoder 구조**
   - Encoder: N=6개의 동일한 layer 스택
   - Decoder: N=6개의 동일한 layer 스택
   
2. **Encoder Layer 구성**
   - Multi-head self-attention mechanism
   - Position-wise fully connected feed-forward network
   - 각 sub-layer에 residual connection과 layer normalization 적용

3. **Decoder Layer 구성**
   - Masked multi-head self-attention (auto-regressive 속성 유지)
   - Encoder output에 대한 multi-head attention
   - Position-wise feed-forward network
   - Residual connection과 layer normalization

4. **Attention Mechanism**
   - **Scaled Dot-Product Attention**: 
     - Query, Key, Value 사용
     - Attention(Q,K,V) = softmax(QK^T/√d_k)V
   - **Multi-Head Attention**:
     - 8개의 parallel attention heads (각 d_k = d_v = 64)
     - 다양한 representation subspace에서 정보 집계
   
5. **Position-wise Feed-Forward Networks**
   - 두 개의 linear transformation과 ReLU activation
   - FFN(x) = max(0, xW_1 + b_1)W_2 + b_2

6. **Positional Encoding**
   - Sine과 cosine 함수 사용한 고정된 positional encoding
   - PE(pos, 2i) = sin(pos/10000^(2i/d_model))
   - PE(pos, 2i+1) = cos(pos/10000^(2i/d_model))

7. **모델 크기**
   - Base model: d_model=512, h=8, d_ff=2048, d_k=d_v=64
   - Big model: d_model=1024, h=16, d_ff=4096

#### 데이터셋
1. **WMT 2014 English-to-German**
   - 약 4.5M sentence pairs
   - Byte-pair encoding으로 37,000 token vocabulary
   - Sentence batching by approximate sequence length

2. **WMT 2014 English-to-French**
   - 36M sentences
   - 32,000 word-piece vocabulary
   - Hardware: 8 NVIDIA P100 GPUs

3. **English Constituency Parsing**
   - WSJ portion of Penn Treebank
   - 약 40K training sentences
   - Semi-supervised setting에서 평가

#### 평가방법
1. **Machine Translation**
   - BLEU score 사용
   - Beam search (beam size=4, length penalty α=0.6)
   - Checkpoint averaging (last 5-20 checkpoints)

2. **Parsing**
   - F1 score 측정
   - Task-specific tuning 최소화하여 일반화 능력 평가

3. **Training Details**
   - Optimizer: Adam (β1=0.9, β2=0.98, ε=10^-9)
   - Learning rate scheduling: warmup + decay
   - Regularization: Dropout (P_drop=0.1), Label smoothing (ε_ls=0.1)
   - Base model: 100K steps (12시간), Big model: 300K steps (3.5일)

#### 실험 결과
1. **WMT 2014 English-to-German Translation**
   - Transformer (big): 28.4 BLEU (기존 SOTA 대비 +2.0 BLEU 이상)
   - Training cost: 3.5일 (8 P100 GPUs)
   - 기존 ensemble 모델들도 능가

2. **WMT 2014 English-to-French Translation**
   - Transformer (big): 41.8 BLEU (새로운 single-model SOTA)
   - 기존 최고 모델 대비 1/4 미만의 학습 비용
   - Dropout P_drop=0.1 적용

3. **Model Variations (Ablation Studies)**
   - Attention head 수, key/value dimension, model size, dropout 등 다양한 변형 실험
   - Multi-head attention과 model dimension이 성능에 중요함을 확인

4. **English Constituency Parsing**
   - WSJ only (40K sentences): F1 score 향상 달성
   - Semi-supervised (high-confidence, BerkleyParser): competitive 성능
   - Task-specific tuning 없이도 다른 task에 일반화 가능함을 입증

### 5. Findings

#### Objective Evaluations
1. **번역 성능**
   - WMT 2014 En-De: 28.4 BLEU (ensemble 포함 모든 기존 모델 능가)
   - WMT 2014 En-Fr: 41.8 BLEU (single-model SOTA)
   - Base model도 기존 모델들과 경쟁력 있는 성능

2. **학습 효율성**
   - 기존 최고 모델 대비 훨씬 적은 학습 비용
   - Base model: 12시간, Big model: 3.5일 (8 P100 GPUs)
   - 높은 병렬화로 인한 학습 속도 향상

3. **Ablation Study 결과**
   - Single-head attention은 multi-head 대비 0.9 BLEU 감소
   - Attention key size 감소는 모델 품질 저하
   - 더 큰 모델이 일관되게 더 나은 성능
   - Dropout이 over-fitting 방지에 효과적
   - Positional encoding (learned vs sinusoidal)은 거의 동일한 성능

4. **Computational Efficiency**
   - Self-attention layer가 recurrent layer보다 빠른 sequential operation
   - Long-range dependency 학습에 필요한 path length 감소 (O(1) vs O(n))
   - Separable convolution보다 파라미터 효율적

#### Subjective Evaluations
정보 부족 - 논문에서 주관적 평가(human evaluation 등)에 대한 상세 내용이 제공되지 않음. BLEU score 등 객관적 지표 중심으로 평가 진행.

### 6. Notes

#### 의미
1. **패러다임 전환**: RNN/CNN 없이 attention만으로 sequence modeling이 가능함을 입증하여 NLP 분야의 패러다임을 완전히 변화시킴
2. **현대 대규모 언어 모델의 기반**: BERT, GPT 시리즈 등 현재 모든 주요 언어 모델의 기초 아키텍처가 됨
3. **병렬화 혁신**: Sequential computation 제거로 대규모 병렬 학습 가능하게 하여 더 큰 모델과 데이터셋 활용의 길을 열음
4. **범용성**: Machine translation뿐 아니라 parsing 등 다양한 task에 적용 가능한 일반적 아키텍처임을 입증
5. **효율성과 성능의 동시 달성**: 더 빠른 학습과 더 나은 성능을 동시에 달성하는 드문 사례

#### 한계
1. **Long sequence 처리**: 매우 긴 sequence에 대해서는 여전히 computational cost가 높음 (O(n²) complexity)
2. **Autoregressive generation**: Decoder의 sequential한 생성 과정은 여전히 병렬화가 어려움
3. **Position encoding**: Sinusoidal encoding의 이론적 근거와 최적성에 대한 완전한 이해 부족
4. **Memory 요구사항**: Self-attention의 quadratic memory requirement
5. **Local structure modeling**: Convolution이나 RNN이 잘 포착하는 local pattern에 대한 explicit bias 부족
6. **제한된 실험 범위**: 주로 번역과 parsing에 집중, 다른 modality(이미지, 오디오 등)에 대한 실험은 향후 과제로 남김

#### 코드/데모
- **공식 구현**: https://github.com/tensorflow/tensor2tensor
- **논문에서 명시**: 학습 및 평가에 사용한 코드를 tensor2tensor 레포지토리에 공개
- **재현 가능성**: 논문에서 모든 hyperparameter와 학습 설정을 상세히 기술하여 재현 가능하도록 함
- **Impact**: 공개 코드로 인해 연구 커뮤니티에서 빠르게 채택되고 발전됨


---
### 7. Figures/Tables

**Figure 1: The Transformer - model architecture.**

![Figure 1: The Transformer - model architecture.](figures/attention_is_all_you_need/fig_p3_0.png)

**Figure 2: (left) Scaled Dot-Product Attention. (right) Multi-Head Attention consists of several**

![Figure 2: (left) Scaled Dot-Product Attention. (right) Multi-Head Attention consists of several](figures/attention_is_all_you_need/fig_p4_1.png)

**(p.4)**

![(p.4)](figures/attention_is_all_you_need/fig_p4_2.png)
