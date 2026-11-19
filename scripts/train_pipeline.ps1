# Windows PowerShell equivalent of train_pipeline.sh
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

Write-Host "==> 1/4 Installing backend dependencies"
python -m pip install -r backend/requirements.txt

Write-Host "==> 2/4 Downloading & preprocessing dataset (WELFake)"
python -m ml.data.download_data --source welfake
python -m ml.preprocessing.make_splits --seed 42

Write-Host "==> 3/4 Training TF-IDF + LogisticRegression baseline"
python -m ml.training.train_tfidf

Write-Host "==> 4/4 Fine-tuning transformer"
Write-Host "     For a quick smoke test use: --max-train-rows 2000 --epochs 1 --max-length 128"
python -m ml.training.train_transformer --model distilbert-base-uncased --max-length 256 --epochs 2 --batch-size 16
