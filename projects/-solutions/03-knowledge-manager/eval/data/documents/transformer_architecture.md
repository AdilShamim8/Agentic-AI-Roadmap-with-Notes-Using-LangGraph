# The Transformer Architecture

The Transformer is a neural network architecture introduced by
Ashish Vaswani and colleagues at Google in the 2017 paper "Attention
Is All You Need". It replaced recurrent layers with multi-head
self-attention, enabling parallel training on GPUs.

A transformer consists of an encoder and a decoder, each made of
stacked layers. Each layer has a multi-head self-attention sublayer
and a position-wise feed-forward sublayer. Positional encodings are
added to input embeddings to preserve word order information.

Encoder-only transformers such as BERT (Devlin et al., 2018) excel
at classification and span extraction. Decoder-only transformers
such as GPT (Radford et al., 2018) excel at autoregressive text
generation. T5 (Raffel et al., 2019) uses the full encoder-decoder
for text-to-text tasks.

Scaled dot-product attention computes softmax(QK^T / sqrt(d_k)) V.
Multi-head attention runs several attention layers in parallel and
concatenates their outputs.