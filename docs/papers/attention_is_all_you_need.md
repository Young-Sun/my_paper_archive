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
본 논문은 자연어처리 분야에 혁명을 일으킨 Transformer 모델을 제시합니다. 기존의 sequence transduction 모델들은 복잡한 recurrent 또는 convolutional neural network에 의존했지만, Transformer는 오직 attention mechanism만을 사용하여 recurrence와 convolution을 완전히 배제한 새로운 네트워크 아키텍처입니다. WMT 2014 English-to-German 번역 태스크에서 28.4 BLEU를 달성하여 기존 최고 성능을 2 BLEU 이상 개선했으며, English-to-French 번역에서는 8개 GPU로 3.5일 훈련하여 41.8 BLEU의 새로운 SOTA를 수립했습니다. 병렬화가 뛰어나고 학습 시간이 크게 단축되었으며, English constituency parsing 등 다른 태스크에서도 우수한 일반화 성능을 보였습니다.

### 2. 한 줄 핵심 요약
Recurrence와 convolution을 제거하고 오직 attention mechanism만으로 구성된 Transformer 아키텍처를 제안하여 기계 번역에서 SOTA를 달성하고 학습 효율성을 크게 개선했습니다.

### 3. Contribution
- **완전한 attention 기반 아키텍처**: Recurrent layer와 convolutional layer를 사용하지 않고 오직 self-attention mechanism만으로 구성된 최초의 sequence transduction 모델
- **Multi-head attention 메커니즘**: 병렬적으로 여러 representation subspace에서 정보를 학습할 수 있는 구조 제안
- **Scaled dot-product attention**: 효율적인 attention 계산 방법 제시
- **Position encoding**: Parameter-free positional representation을 통한 순서 정보 인코딩
- **기계 번역 SOTA 달성**: WMT 2014 English-to-German (28.4 BLEU), English-to-French (41.8 BLEU)에서 신기록 수립
- **학습 효율성 개선**: 기존 모델 대비 훨씬 적은 학습 시간과 비용으로 우수한 성능 달성
- **범용성 입증**: English constituency parsing 등 다른 태스크에서도 성공적 적용

### 4. Methods

#### 핵심 아이디어
- **Self-attention의 전면 채택**: RNN이나 CNN 없이 오직 attention만으로 sequence의 representation 학습
- **Encoder-decoder 구조**: 각각 self-attention과 feed-forward network로 구성된 스택으로 구현
- **병렬 처리**: Recurrence 제거로 학습 시 완전한 병렬화 가능
- **위치 정보 인코딩**: Sinusoidal position encoding을 통해 순서 정보 주입

#### 모델 구조
**Encoder:**
- 6개의 동일한 layer 스택
- 각 layer는 2개의 sub-layer로 구성:
  - Multi-head self-attention mechanism
  - Position-wise fully connected feed-forward network
- 각 sub-layer에 residual connection과 layer normalization 적용
- 출력 차원: d_model = 512

**Decoder:**
- 6개의 동일한 layer 스택
- 각 layer는 3개의 sub-layer로 구성:
  - Masked multi-head self-attention (auto-regressive 특성 유지)
  - Multi-head attention over encoder output
  - Position-wise fully connected feed-forward network
- Encoder와 동일한 residual connection과 layer normalization

**Attention 메커니즘:**
- **Scaled Dot-Product Attention**: 
  - Attention(Q, K, V) = softmax(QK^T / √d_k)V
  - Scaling factor (√d_k)로 gradient 안정화
- **Multi-Head Attention**:
  - h=8개의 parallel attention layer
  - 각 head의 차원: d_k = d_v = d_model/h = 64
  - 서로 다른 representation subspace에서 정보 학습

**Position Encoding:**
- Sinusoidal function 사용:
  - PE(pos, 2i) = sin(pos/10000^(2i/d_model))
  - PE(pos, 2i+1) = cos(pos/10000^(2i/d_model))
- 상대적 위치 정보 학습 가능

**Feed-Forward Networks:**
- FFN(x) = max(0, xW_1 + b_1)W_2 + b_2
- 내부 차원: d_ff = 2048
- 각 position에 동일하게 적용

#### 데이터셋
**기계 번역:**
- **WMT 2014 English-to-German**: 약 4.5M sentence pairs
  - Byte-pair encoding 사용
  - 약 37,000개의 공유 vocabulary
- **WMT 2014 English-to-French**: 약 36M sentences
  - Word-piece vocabulary (32,000 tokens)

**English Constituency Parsing:**
- **WSJ portion of Penn Treebank**: 약 40K training sentences
- **Semi-supervised setting**: BerkleyParser corpus (~17M sentences) 추가

#### 평가방법
**기계 번역:**
- BLEU score를 primary metric으로 사용
- Beam search (beam size=4, length penalty α=0.6)
- Checkpoint averaging (마지막 5 checkpoints)
- Ensemble 실험도 수행

**Parsing:**
- F1 score로 평가
- Semi-supervised와 supervised 설정 모두 테스트

**모델 변형 실험:**
- Attention head 수, key/value 차원, model 크기, dropout rate 등 다양한 hyperparameter 조합 평가
- Positional encoding 방식 비교 (sinusoidal vs. learned)

#### 실험 결과
**기계 번역 성능:**
- **English-to-German**:
  - Base model: 27.3 BLEU
  - Big model: 28.4 BLEU (기존 SOTA 대비 +2.0 BLEU)
- **English-to-French**:
  - Big model: 41.8 BLEU (single model SOTA)
  - 8 GPU로 3.5일 훈련 (기존 최고 모델 대비 1/4 미만의 학습 비용)

**학습 효율성:**
- Base model: 8 P100 GPU로 12시간 (100K steps)
- Big model: 8 P100 GPU로 3.5일 (300K steps)
- 기존 RNN/CNN 모델 대비 훨씬 빠른 수렴

**Parsing 성능:**
- WSJ only (40K sentences): 91.3 F1 (RNN 기반 모델과 경쟁력)
- Semi-supervised (BerkleyParser 추가): 92.7 F1

### 5. Findings

#### Objective Evaluations

**BLEU Score 개선:**
- Ensemble이 아닌 single model로 기존 ensemble 성능 초과
- English-to-German: 28.4 BLEU (이전 최고 26.4 대비 +2.0)
- English-to-French: 41.8 BLEU (training cost의 1/4로 달성)

**Model Variation 분석:**
- **(A) Attention head 수**: Single-head보다 multi-head가 우수, h=8이 최적
- **(B) Attention key 크기**: Key 크기 감소가 모델 품질 저하 (compatibility 함수의 중요성)
- **(C) Model 크기**: 더 큰 모델이 더 좋은 성능, dropout이 overfitting 방지에 효과적
- **(D) Dropout**: 적절한 dropout (0.1~0.3)이 성능 향상에 기여
- **(E) Positional encoding**: Sinusoidal과 learned positional encoding이 거의 동일한 성능

**계산 효율성:**
- Self-attention layer의 computational complexity: O(n²·d) (sequence length n, dimension d)
- n < d인 대부분의 경우 recurrent layer보다 빠름
- Maximum path length가 O(1)로 long-range dependency 학습에 유리
- Sequential operations가 최소화되어 병렬화 극대화

**일반화 능력:**
- English constituency parsing에서도 우수한 성능 (92.7 F1)
- 도메인 특화 튜닝 없이 다양한 태스크에 적용 가능
- Semi-supervised learning에도 효과적

#### Subjective Evaluations

**정보 부족** (논문에 subjective evaluation 관련 내용 없음. 주로 BLEU, F1 등 objective metric에 집중)

### 6. Notes

#### 의미
- **딥러닝 패러다임 전환**: RNN/LSTM 중심에서 attention 중심으로의 대전환 촉발
- **현대 NLP의 기반**: BERT, GPT 등 모든 주요 language model의 근간이 되는 아키텍처
- **병렬화 가능성**: GPU 활용 극대화로 대규모 모델 학습 가능성 제시
- **범용성**: 기계 번역뿐만 아니라 다양한 sequence modeling 태스크에 적용 가능
- **해석 가능성**: Attention weight를 통한 모델 의사결정 과정 시각화 가능
- **산업계 영향**: 현재 거의 모든 상용 NLP 시스템의 핵심 기술로 자리잡음

#### 한계
- **Long sequence 처리**: Sequence length의 제곱에 비례하는 메모리/계산 복잡도 (O(n²))
- **위치 정보 인코딩**: Sinusoidal encoding의 이론적 최적성에 대한 명확한 증명 부족
- **제한적 태스크 검증**: 주로 번역과 parsing에 집중, 다른 modality (이미지, 오디오) 실험 미비
- **Interpretability 한계**: Attention이 항상 인간이 이해 가능한 패턴을 학습하는 것은 아님
- **Local context**: 모든 position을 동등하게 고려하여 지역적 구조 정보 활용이 제한적일 수 있음
- **학습 데이터 의존성**: 여전히 대규모 parallel corpus 필요

**향후 연구 방향 (논문에서 언급):**
- 이미지, 오디오, 비디오 등 다른 modality로 확장
- Local, restricted attention mechanism으로 대용량 입출력 효율적 처리
- Less sequential generation 방법 연구

#### 코드/데모
- **공식 구현**: https://github.com/tensorflow/tensor2tensor
- TensorFlow 기반으로 학습 및 평가 코드 제공
- 현재는 PyTorch, JAX 등 다양한 프레임워크로 재구현됨
- Hugging Face Transformers 라이브러리 등에서 표준 구현 제공


---
### 7. Figures/Tables

**Figure 1: The Transformer - model architecture.**

![Figure 1: The Transformer - model architecture.](figures/attention_is_all_you_need/fig_p3_0.png)

**Figure 2: (left) Scaled Dot-Product Attention. (right) Multi-Head Attention consists of several**

![Figure 2: (left) Scaled Dot-Product Attention. (right) Multi-Head Attention consists of several](figures/attention_is_all_you_need/fig_p4_1.png)

**(p.4)**

![(p.4)](figures/attention_is_all_you_need/fig_p4_2.png)
