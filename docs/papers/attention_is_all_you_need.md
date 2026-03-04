# Attention Is All You Need

**Link**: https://arxiv.org/abs/1706.03762  
**Authors**: Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser, Illia Polosukhin  
**Venue**: arXiv:1706.03762 [cs.CL] (2017)  
**Model**: `claude-opus-4-6`

---
## Abstract

The dominant sequence transduction models are based on complex recurrent or convolutional neural networks in an encoder-decoder configuration. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train. Our model achieves 28.4 BLEU on the WMT 2014 English-to-German translation task, improving over the existing best results, including ensembles by over 2 BLEU. On the WMT 2014 English-to-French translation task, our model establishes a new single-model state-of-the-art BLEU score of 41.8 after training for 3.5 days on eight GPUs, a small fraction of the training costs of the best models from the literature. We show that the Transformer generalizes well to other tasks by applying it successfully to English constituency parsing both with large and limited training data.


---
## Summary

### 1. Abstract 요약
본 논문은 기존의 sequence transduction 모델이 의존하던 recurrence와 convolution을 완전히 배제하고, attention mechanism만으로 구성된 새로운 네트워크 아키텍처인 Transformer를 제안한다. Transformer는 encoder-decoder 구조를 따르되, multi-head self-attention과 position-wise feed-forward network로 구성되어 병렬화가 크게 향상되고 학습 시간이 대폭 단축된다. WMT 2014 영어-독일어 번역에서 28.4 BLEU로 기존 최고 성능(앙상블 포함)을 2 BLEU 이상 능가하였고, 영어-프랑스어 번역에서는 8개 GPU로 3.5일 학습만으로 41.8 BLEU의 새로운 single-model SOTA를 달성하였다. 또한 English constituency parsing에서도 우수한 일반화 성능을 보여 Transformer의 범용성을 입증하였다.

### 2. 한 줄 핵심 요약
Recurrence와 convolution 없이 self-attention만으로 구성된 Transformer 아키텍처를 제안하여 기계 번역에서 SOTA 성능을 달성하면서 학습 비용을 대폭 절감하였다.

### 3. Contribution
- **최초의 순수 attention 기반 sequence transduction 모델**: RNN이나 CNN 없이 오직 self-attention mechanism만으로 encoder-decoder 모델을 구성한 최초의 아키텍처 (Transformer) 제안
- **Scaled Dot-Product Attention 및 Multi-Head Attention 도입**: dot-product attention에 √d_k 스케일링을 적용하고, 여러 attention head를 병렬로 수행하여 서로 다른 representation subspace의 정보를 동시에 학습
- **높은 병렬화와 학습 효율성**: 기존 RNN 기반 모델 대비 훨씬 적은 학습 비용으로 (8 GPU, 3.5일) SOTA 달성
- **기계 번역에서의 새로운 SOTA**: WMT 2014 EN-DE 28.4 BLEU, EN-FR 41.8 BLEU
- **우수한 일반화 성능 입증**: English constituency parsing에서 task-specific tuning 없이도 경쟁력 있는 결과 달성

### 4. Methods
#### 핵심 아이디어
기존 sequence transduction 모델의 RNN 기반 순차 연산은 병렬화를 제한하고 장거리 의존성 학습을 어렵게 만든다. Self-attention은 시퀀스 내 임의의 두 위치를 O(1) 연산으로 연결할 수 있어 이 문제를 해결한다. 이 핵심 관찰에 기반하여 recurrence를 완전히 제거하고 attention만으로 입출력 간 global dependency를 모델링하는 Transformer를 설계하였다.

#### 모델 구조
- **Encoder**: N=6개의 동일한 레이어 스택. 각 레이어는 (1) multi-head self-attention, (2) position-wise feed-forward network의 2개 sub-layer로 구성. 각 sub-layer에 residual connection + layer normalization 적용. d_model = 512.
- **Decoder**: N=6개의 동일한 레이어 스택. Encoder와 동일한 2개 sub-layer에 추가로 encoder 출력에 대한 multi-head attention sub-layer 삽입 (총 3개 sub-layer). Decoder의 self-attention에는 미래 위치를 참조하지 못하도록 masking 적용.
- **Scaled Dot-Product Attention**: Attention(Q,K,V) = softmax(QK^T/√d_k)V. √d_k로 스케일링하여 큰 d_k에서 softmax의 gradient vanishing 방지.
- **Multi-Head Attention**: h=8개의 병렬 attention head 사용. d_k = d_v = d_model/h = 64. 각 head의 출력을 concatenate 후 linear projection.
- **Position-wise FFN**: 2층 fully connected (d_ff = 2048), ReLU 활성 함수.
- **Positional Encoding**: 순서 정보를 위해 sine/cosine 함수 기반 positional encoding을 embedding에 더함.
- **Embedding 공유**: 입력/출력 embedding과 pre-softmax linear transformation의 가중치 행렬 공유.

#### 데이터셋
- **WMT 2014 English-German**: 약 450만 문장 쌍, byte-pair encoding (약 37,000 토큰 공유 vocabulary)
- **WMT 2014 English-French**: 약 3,600만 문장, 32,000 word-piece vocabulary
- **Penn Treebank (WSJ)**: English constituency parsing용, 약 40K 학습 문장 (WSJ only) 및 약 17M 문장 (semi-supervised)

#### 평가방법
- **BLEU score**: 기계 번역 품질 평가 (newstest2014 테스트셋)
- **Training cost (FLOPs)**: 학습 효율성 비교
- **Perplexity (PPL)**: development set에서 모델 변형 실험 평가
- **F1 score**: English constituency parsing (WSJ Section 23)

#### 실험 결과
- **EN-DE 번역**: Transformer (big) 28.4 BLEU — 기존 최고 앙상블(GNMT+RL Ensemble 26.30) 대비 +2.1 BLEU 향상. Training cost 2.3×10^19 FLOPs (앙상블의 1/8 수준).
- **EN-FR 번역**: Transformer (big) 41.8 BLEU — 기존 single-model SOTA 대비 최고 성능. 학습 비용은 이전 SOTA의 1/4 이하.
- **Base model**: EN-DE 27.3 BLEU (training cost 3.3×10^18 FLOPs만으로 기존 모든 single model 및 앙상블 능가)
- **Ablation study (Table 3)**: single-head attention은 best setting 대비 0.9 BLEU 하락; d_k 축소 시 성능 저하; 모델 크기 증가와 dropout이 성능에 중요; sinusoidal vs learned positional encoding은 거의 동일 성능.
- **English constituency parsing**: WSJ only에서 91.3 F1 (Dyer et al. 91.7에 근접), semi-supervised에서 92.7 F1 (기존 대부분 모델 상회).

### 5. Findings
#### Objective Evaluations
| 모델 | EN-DE BLEU | EN-FR BLEU | Training FLOPs (EN-DE) |
|---|---|---|---|
| GNMT+RL Ensemble | 26.30 | 41.16 | 1.8×10^20 |
| ConvS2S Ensemble | 26.36 | 41.29 | 7.7×10^19 |
| **Transformer (base)** | **27.3** | **38.1** | **3.3×10^18** |
| **Transformer (big)** | **28.4** | **41.8** | **2.3×10^19** |

- Self-attention의 레이어당 계산 복잡도는 O(n²·d)이지만, 순차 연산은 O(1)이고 maximum path length도 O(1)로, RNN의 O(n)이나 CNN의 O(log_k(n))보다 장거리 의존성 학습에 유리
- 8-head attention이 최적이며, head 수가 너무 적거나(1) 많으면(32) 성능 하락
- 큰 모델(d_model=1024, d_ff=4096, h=16, 213M params)이 base model(65M params) 대비 우수

#### Subjective Evaluations
- Attention visualization 분석: encoder self-attention의 개별 head가 서로 다른 언어적 과업을 수행함을 확인
  - 장거리 의존성 포착 (예: 'making...more difficult' 구문에서 'making'이 'more difficult'에 attend)
  - 대용어 해결 (anaphora resolution): 'its'가 'Law'에 정확히 attend하는 패턴 관찰
  - 문장 구조와 관련된 attention 패턴 (구문적/의미적 구조 반영)
- 이러한 결과는 self-attention이 더 해석 가능한 모델을 만들 수 있음을 시사

### 6. Notes
#### 의미
- **딥러닝 역사의 전환점**: Transformer는 이후 BERT, GPT, T5, ViT 등 거의 모든 현대 딥러닝 아키텍처의 기초가 되어, NLP는 물론 computer vision, speech, multimodal AI 전반에 혁명적 영향을 미침
- Self-attention만으로 RNN을 완전히 대체할 수 있음을 최초로 실증적으로 증명하여, 시퀀스 모델링의 패러다임을 근본적으로 변화시킴
- 병렬화 가능성과 학습 효율성을 동시에 확보하여, 이후 대규모 언어 모델(LLM) 학습의 기반을 마련

#### 한계
- Self-attention의 O(n²) 복잡도로 인해 매우 긴 시퀀스(이미지, 오디오, 비디오 등)에 대한 직접 적용이 어려움 (저자들도 restricted self-attention을 향후 연구로 언급)
- 위치 정보를 sinusoidal encoding으로만 주입하여, 상대적 위치 관계의 명시적 모델링이 부족
- 기계 번역과 constituency parsing 두 가지 과업에서만 검증되어, 당시 기준으로 범용성 검증이 제한적
- Auto-regressive decoding의 순차적 특성은 여전히 잔존 (생성 시 병렬화 미해결)

#### 코드/데모
- 학습 및 평가 코드: https://github.com/tensorflow/tensor2tensor


---
### 7. Figures/Tables

**Figure 1: The Transformer - model architecture.**

![Figure 1: The Transformer - model architecture.](figures/attention_is_all_you_need/fig_p3_0.png)

**Figure 2: (left) Scaled Dot-Product Attention. (right) Multi-Head Attention consists of several**

![Figure 2: (left) Scaled Dot-Product Attention. (right) Multi-Head Attention consists of several](figures/attention_is_all_you_need/fig_p4_1.png)

**(p.4)**

![(p.4)](figures/attention_is_all_you_need/fig_p4_2.png)
