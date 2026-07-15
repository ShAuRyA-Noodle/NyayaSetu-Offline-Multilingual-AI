#!/usr/bin/env python
"""
Fine-tune a compact transformer to classify governance text by category.

Trains on the REAL labeled dataset scraped from myScheme
(data/classifier/scheme_category.jsonl: scheme text -> official category) and
reports accuracy + macro-F1 on a held-out test split. Saves the model, tokenizer
and label map to models/classifier/ for the grievance router to use.

Self-contained PyTorch loop (no Trainer/accelerate dependency).

    .venv-ml/Scripts/python.exe scripts/train_classifier.py --epochs 3
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_data(path: Path):
    texts, labels = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("text") and r.get("category"):
            texts.append(r["text"])
            labels.append(r["category"])
    return texts, labels


def main() -> int:
    import numpy as np
    import torch
    from sklearn.metrics import accuracy_score, f1_score
    from sklearn.model_selection import train_test_split
    from torch.utils.data import DataLoader, Dataset
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/classifier/scheme_category.jsonl")
    p.add_argument("--model", default="ai4bharat/indic-bert")
    p.add_argument("--out", default="models/classifier")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--lr", type=float, default=2e-5)
    p.add_argument("--max-len", type=int, default=128)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    texts, labels = load_data(ROOT / args.data)
    label_list = sorted(set(labels))
    label2id = {c: i for i, c in enumerate(label_list)}
    y = [label2id[c] for c in labels]
    print(f"{len(texts)} records, {len(label_list)} classes")

    X_tr, X_te, y_tr, y_te = train_test_split(
        texts, y, test_size=0.2, random_state=args.seed, stratify=y
    )

    tok = AutoTokenizer.from_pretrained(args.model)

    class DS(Dataset):
        def __init__(self, X, Y):
            self.X, self.Y = X, Y

        def __len__(self):
            return len(self.X)

        def __getitem__(self, i):
            enc = tok(self.X[i], truncation=True, max_length=args.max_len,
                      padding="max_length", return_tensors="pt")
            return {k: v.squeeze(0) for k, v in enc.items()}, self.Y[i]

    def collate(batch):
        feats = {k: torch.stack([b[0][k] for b in batch]) for k in batch[0][0]}
        ys = torch.tensor([b[1] for b in batch])
        return feats, ys

    tr_loader = DataLoader(DS(X_tr, y_tr), batch_size=args.batch, shuffle=True, collate_fn=collate)
    te_loader = DataLoader(DS(X_te, y_te), batch_size=32, collate_fn=collate)

    model = AutoModelForSequenceClassification.from_pretrained(
        args.model, num_labels=len(label_list),
        id2label={i: c for c, i in label2id.items()}, label2id=label2id,
    ).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)

    for epoch in range(args.epochs):
        model.train()
        total = 0.0
        for step, (feats, ys) in enumerate(tr_loader):
            feats = {k: v.to(device) for k, v in feats.items()}
            ys = ys.to(device)
            opt.zero_grad()
            out = model(**feats, labels=ys)
            out.loss.backward()
            opt.step()
            total += out.loss.item()
            if step % 50 == 0:
                print(f"  epoch {epoch+1} step {step}/{len(tr_loader)} loss {out.loss.item():.3f}", flush=True)
        print(f"epoch {epoch+1} avg loss {total/len(tr_loader):.4f}", flush=True)

    # Evaluate
    model.eval()
    preds, gold = [], []
    with torch.no_grad():
        for feats, ys in te_loader:
            feats = {k: v.to(device) for k, v in feats.items()}
            logits = model(**feats).logits
            preds.extend(torch.argmax(logits, dim=-1).cpu().tolist())
            gold.extend(ys.tolist())
    acc = accuracy_score(gold, preds)
    macro_f1 = f1_score(gold, preds, average="macro")
    weighted_f1 = f1_score(gold, preds, average="weighted")
    print(f"\nTEST accuracy={acc:.4f} macro-F1={macro_f1:.4f} weighted-F1={weighted_f1:.4f}")

    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out_dir)
    tok.save_pretrained(out_dir)
    (out_dir / "labels.json").write_text(json.dumps(label_list, ensure_ascii=False, indent=2), encoding="utf-8")

    results = {
        "model": args.model,
        "dataset": "myScheme scheme->category (real labels)",
        "n_total": len(texts), "n_test": len(X_te), "n_classes": len(label_list),
        "epochs": args.epochs,
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
    }
    res_dir = ROOT / "eval" / "results"
    res_dir.mkdir(parents=True, exist_ok=True)
    (res_dir / "classifier.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved model -> {args.out} | results -> eval/results/classifier.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
