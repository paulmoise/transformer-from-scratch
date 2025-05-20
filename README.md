# Transformer from Scratch: English to French Translation

This project implements the **Transformer architecture from scratch** in Python, inspired by the YouTube tutorial [Implementing Transformers From Scratch | NLP Course](https://www.youtube.com/watch?v=ISNdQcPhsts) by *Aladdin Persson*.

In the original video, the model is trained for English-to-Italian translation. In this project, we adapt it for **English to French translation**.

---

## Features

- Transformer model (encoder-decoder) implemented from scratch (no Hugging Face, no PyTorch modules)
- Trained on a small English-French dataset
- Clean training and inference pipeline
- Fully reproducible setup using [`uv`](https://github.com/astral-sh/uv)

---

## Installation (with `uv`)

1. Install `uv` if not already installed:

```bash
curl -Ls https://astral.sh/uv/install.sh | sh
```

2. Create a virtual environment and install dependencies:

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

3. If needed, install `torch` manually based on your system:

```bash
uv pip install torch torchvision
```

---

## Usage

### Training

```bash
python train.py
```

This will train the Transformer model on your English-French dataset. You can customize hyperparameters inside `config.py` (if available) or directly in the script.

### Inference

After training:

```bash
python translate.py --sentence "I love natural language processing."
```

Expected output:

```
> Je aime le traitement du langage naturel.
```

Note: Output might vary depending on your training data and number of epochs.

---

## Project Structure

```bash
.
├── train.py           # Training script
├── translate.py       # Inference script
├── model.py           # Transformer model (encoder, decoder, etc.)
├── utils.py           # Helper functions (e.g., masks, positional encoding)
├── vocab.py           # Tokenizer and vocabulary management
├── dataset.py         # Dataset loading and preprocessing
├── requirements.txt   # Dependencies
└── README.md
```

