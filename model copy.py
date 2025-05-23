import torch
import torch.nn as nn
import math


#  Embedding layer for the input and output token
"""
It is a vector of size 512
"""
class InputEmbedding(nn.Module):
    def __init__(self, d_model, vocab_size) -> None:
        super().__init__()
        self.d_model = d_model
        self.vocab_size = vocab_size
        self.embedding = nn.Embedding(vocab_size, d_model)

    def forward(self, x):
        return self.embedding(x) * math.sqrt(self.d_model)


# Positional encoding 
"""
- It is a vector of size 512
- It's computed once and reused for every sentence during the training and inference

Explaination:
- d_model: the size of the vector of the positional encoding
- seq_len: the maximum length of the sentence and we have to create one vector for each position
- dropout: to make the model less overfit

Goal:
We want to create a matrix of size: (seq_len, d_model)
"""
class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, seq_len: int, dropout: float) -> None:
        super().__init__()
        self.d_model = d_model
        self.seq_len = seq_len
        self.dropout = nn.Dropout(dropout)
        # create a matrix of size (seq_len, d_model)
        pe = torch.zeros(seq_len, d_model) # this represent the position of the word inside the sequence

        # create a vector of shape (seq_len, 1)
        position = torch.arange(0, seq_len, dtype=torch.float).unsqueeze(1)
        # $$ a^x = e^{x ln(a)} \quad \text{ where } a > 0 $$
        # $$ PE(pos, 2i) = sin\left[\dfrac{pos}{10000^{\dfrac{2i}{d_{model}}}} \right]$$
        # $$ \dfrac{pos}{10000^{\dfrac{2i}{d_{model}}}} = pos * 10000^{- \dfrac{2i}{d_{model}} } $$
        # $$ 10000^{ - \dfrac{2i}{d_{model}}} = e^{2i * \dfrac{- ln(10000)}{d_{model}}}$$
        
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0)/ d_model))

        # apply the sin to even position and cos to odd
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        
        # pe size: (seq_len, d_model)
        pe = pe.unsqueeze(0) # (1, seq_len, d_model)

        self.register_buffer('pe', pe) # register as buffer so we can save it 




    def forward(self, x):
        x = x + (self.pe[: , :x.shape[1], :]).requires_grad_(False) # they are not learn along the train 
        return x

class LayerNormalization(nn.Module):
    def __init__(self, features:int,  eps: float = 10**-6):
        super().__init__()
        self.eps = eps
        self.alpha = nn.Parameter(torch.ones(features)) # The Multiplied parameter:  We use nn.Parameter to make them learnable
        self.bias = nn.Parameter(torch.zeros(features)) # The Added parameter


    def forward(self, x):
        mean = x.mean(dim = -1, keepdim=True)
        std = x.std(dim = -1, keepdim=True)
        return self.alpha * (x - mean) / (std + self.eps) + self.bias
    

# FeedForwardBlock
class FeedFordwardBlock(nn.Module):
    def __init__(self, d_model: int, d_ff: int, dropout: float) -> None:
        super().__init__()
        self.linear_1 = nn.Linear(d_model, d_ff, bias = True)  # W1 and B1
        self.dropout = nn.Dropout(dropout)
        self.linear_2 = nn.Linear(d_ff, d_model, bias = True)


    def forward(self, x):
        # (Batch, seq_len, d_model) --> (Batch, seq_len, d_ff) --> (Batch, seq_len, d_model)
        return self.linear_2(self.dropout(torch.relu(self.linear_1(x))))

"""
h: the number of header to have in the attention mecanism
"""

class MultiHeadAttentionBlock(nn.Module):
    def __init__(self, d_model: int, h: int, dropout: float) -> None:
        super().__init__()

        self.d_model = d_model
        self.h = h

        # be sure that d_model is divisible by h
        assert d_model % h == 0, "d_model is not divisible by h"

        self.d_k = d_model // h

        self.w_q = nn.Linear(d_model, d_model) # Wq  matrix size = (d_model, d_model)
        self.w_k = nn.Linear(d_model, d_model) # Wk  matrix size = (d_model, d_model)
        self.w_v = nn.Linear(d_model, d_model) # Wv  matrix size = (d_model, d_model)

        self.w_o = nn.Linear(d_model, d_model) # Wo  matrix size = (d_model, d_model)
        self.dropout = nn.Dropout(dropout)


    @staticmethod
    def attention(query, key, value, mask, dropout: nn.Dropout):
        d_k = query.shape[-1]
        # (Batch, h, seq_len, seq_len) = (Batch, h, seq_len, d_k) @ (Batch, h, d_k, seq_len)
        attention_scores = (query @ key.transpose(-2, -1)) / math.sqrt(d_k)

        if mask is not None:
            attention_scores.masked_fill_(mask == 0, -1e9)
        attention_scores = attention_scores.softmax(dim = -1) # (Batch, h, seq_len, seq_len)

        if dropout is not None:
            attention_scores  = dropout(attention_scores)

        return (attention_scores @ value), attention_scores
    


    """
    We introduce the batch in matrix dimension because the sentence will be treated batch by batch
    """
    def forward(self, q, k, v, mask):
        query = self.w_q(q) #  (Batch, seq_len, d_model) *  (Batch, d_model, d_model) --> (Batch, seq_len, d_model)
        key = self.w_k(k)   #  (Batch, seq_len, d_model) *  (Batch, d_model, d_model) --> (Batch, seq_len, d_model)
        value = self.w_v(v) #  (Batch, seq_len, d_model) *  (Batch, d_model, d_model) --> (Batch, seq_len, d_model)
        
        # # we keep the first dimension and divide our original matrix to have 
        # (shape[0], shape[1]) matrixes of size (self.h, self.d_k) each one
        # (Batch, seq_len, d_model) apply(view) --> (Batch, seq_len, h, d_k)^T --> (Batch, h, seq_len, d_k)
        query = query.view(query.shape[0], query.shape[1], self.h, self.d_k).transpose(1, 2)  #(Batch, h, seq_len, d_k)
        key = key.view(key.shape[0], key.shape[1], self.h, self.d_k).transpose(1, 2)          #(Batch, h, seq_len, d_k)
        value = value.view(value.shape[0], value.shape[1], self.h, self.d_k).transpose(1, 2)  #(Batch, h, seq_len, d_k)

        # calculate attention scores
        x, self.attention_scores = MultiHeadAttentionBlock.attention(query, key, value, mask, self.dropout)

        # (Batch, seq_len, d_model) = (Batch, h, seq_len, d_k)^T --> (Batch, seq_len, h, d_k)
        x = x.transpose(1, 2).contiguous().view(x.shape[0], -1, self.h * self.d_k)

        return self.w_o(x) # (Batch, seq_len, d_model) --> (Batch, seq_len, d_model)
    

class ResidualConnection(nn.Module):
    def __init__(self, features: int, dropout: float):
        super().__init__()

        self.dropout = nn.Dropout(dropout)
        self.norm = LayerNormalization(features)
        

    def forward(self, x, sublayer):
        return x + self.dropout(sublayer(self.norm(x)))
    
class EncoderBlock(nn.Module):
    def __init__(self, features:int,  self_attention_block: MultiHeadAttentionBlock, feed_forward_block: FeedFordwardBlock, dropout: float):
        super().__init__()

        self.self_attention_block = self_attention_block
        self.feed_forward_block = feed_forward_block
        self.residual_connections = nn.ModuleList([ResidualConnection(features, dropout) for _ in range(2)]) 

    # src_mask: is the mask to apply to the input of the encoder
    # hide the interaction of the hidding word with the other words.
    def forward(self, x, src_mask): 
        x = self.residual_connections[0](x, lambda x: self.self_attention_block(x, x, x, src_mask))
        x = self.residual_connections[1](x, self.feed_forward_block)
        return x

class Encoder(nn.Module):

    def __init__(self, features:int, layers: nn.ModuleList ):
        super().__init__()

        self.layers = layers
        self.norm = LayerNormalization(features)


    def forward(self, x, mask):
        for layer in self.layers:
            x = layer(x, mask)
        return self.norm(x)
    

class DecoderBlock(nn.Module):

    def __init__(self, features:int,  self_attention_block: MultiHeadAttentionBlock, cross_attention_block: MultiHeadAttentionBlock, feed_forward_block: FeedFordwardBlock, dropout: float):
        super().__init__()

        self.self_attention_block = self_attention_block
        self.cross_attention_block = cross_attention_block
        self.feed_forward_block = feed_forward_block
        self.residual_connections = nn.ModuleList([ResidualConnection(features, dropout) for _ in range(3)])


    def forward(self, x, encoder_output, src_mask, tgt_mask):

        x = self.residual_connections[0](x, lambda x: self.self_attention_block(x, x, x, tgt_mask))

        x = self.residual_connections[1](x, lambda x: self.cross_attention_block(x, encoder_output, encoder_output, src_mask ))

        x = self.residual_connections[2](x, self.feed_forward_block)

        return x
    

class Decoder(nn.Module):
    def __init__(self, features:int, layers: nn.ModuleList):
        super().__init__()

        self.layers = layers
        self.norm = LayerNormalization(features)

    def forward(self, x, encoder_output, src_mask, tgt_mask):
        for layer in self.layers:
            x = layer(x, encoder_output, src_mask, tgt_mask)
        return self.norm(x)



class ProjectionLayer(nn.Module):

    def __init__(self, d_model: int, vocab_size: int):
        super().__init__()
        self.proj = nn.Linear(d_model, vocab_size)


    def forward(self, x):

        # (Batch, seq_len, d_model) --> (Batch, seq_len, vocab_size)
        return torch.log_softmax(self.proj(x), dim= -1)
    

class Transformer(nn.Module):

    def __init__(self, 
                 encoder: Encoder,
                 decoder: Decoder,
                 src_embed: InputEmbedding, 
                 tgt_embed: InputEmbedding, 
                 src_pos: PositionalEncoding,
                 tgt_pos: PositionalEncoding,
                 projection_layer: ProjectionLayer):
        super().__init__()


        self.encoder = encoder
        self.decoder = decoder
        self.src_embed = src_embed
        self.tgt_embed = tgt_embed
        self.src_pos = src_pos
        self.tgt_pos = tgt_pos
        self.projection_layer = projection_layer


    def encode(self, src, src_mask):
        src = self.src_embed(src)
        src = self.src_pos(src)
        src = self.encoder(src, src_mask)
        return src
    
    def decode(self, encoder_output, src_mask, tgt, tgt_mask):
        tgt = self.tgt_embed(tgt)
        tgt = self.tgt_pos(tgt)
        tgt = self.decoder(tgt, encoder_output, src_mask, tgt_mask)
        return tgt


    def project(self, x):
        return self.projection_layer(x)
    


def build_transformer(
        src_vocab_size: int, 
        tgt_vocab_size: int, 
        src_seq_len: int, 
        tgt_seq_len: int, 
        d_model: int = 512, 
        N: int=6, h: int=8, 
        dropout: float = 0.1, 
        d_ff: int=2048
        )-> Transformer:
    # Create the embedding layers
    src_embed = InputEmbedding(d_model, src_vocab_size)
    tgt_embed = InputEmbedding(d_model, tgt_vocab_size)

    # Create the positional encoding layers
    src_pos = PositionalEncoding(d_model, src_seq_len, dropout)
    tgt_pos = PositionalEncoding(d_model, tgt_seq_len, dropout)

    # Create the encoder blocks
    encoder_blocks = []
    for _ in range(N):
        encoder_self_attention_block = MultiHeadAttentionBlock(d_model, h, dropout)
        feed_forward_block = FeedFordwardBlock(d_model, d_ff, dropout)
        encoder_block = EncoderBlock(d_model, encoder_self_attention_block, feed_forward_block, dropout)
        encoder_blocks.append(encoder_block)

    
    # Create the decoder blocks
    decoder_blocks = []
    for _ in range(N):
        decoder_self_attention_block = MultiHeadAttentionBlock(d_model, h, dropout)
        decoder_cross_attention_block = MultiHeadAttentionBlock(d_model, h, dropout)
        feed_forward_block = FeedFordwardBlock(d_model, d_ff, dropout)
        decoder_block = DecoderBlock(d_model, decoder_self_attention_block, decoder_cross_attention_block, feed_forward_block, dropout)
        decoder_blocks.append(decoder_block)

    # Create the encoder and the decoder
    encoder = Encoder(d_model, nn.ModuleList(encoder_blocks))
    decoder = Decoder(d_model, nn.ModuleList(decoder_blocks))

    # Create the projection layer
    projection_layer = ProjectionLayer(d_model, tgt_vocab_size)


    # create the transformer
    transformer = Transformer(encoder, decoder, src_embed, tgt_embed, src_pos, tgt_pos, projection_layer)


    # Initialize the parameters
    for p in transformer.parameters():
        if p.dim() > 1:
            nn.init.xavier_uniform_(p)

    return transformer

