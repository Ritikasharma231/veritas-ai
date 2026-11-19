# VERITAS AI — Setup & Training Pipeline
# Run from the repository root on Linux/macOS/Git-Bash.
set -e

echo "==> 1/4 Installing backend dependencies"
python -m pip install -r backend/requirements.txt

echo "==> 2/4 Downloading & preprocessing dataset (WELFake)"
python -m ml.data.download_data --source welfake
python -m ml.preprocessing.make_splits --seed 42

echo "==> 3/4 Training TF-IDF + LogisticRegression baseline"
python -m ml.training.train_tfidf

echo "==> 4/4 Fine-tuning transformer (CPU-friendly default: distilbert)"
echo "     This can take a long time on CPU. For a quick smoke test add:"
echo "       --max-train-rows 2000 --epochs 1 --max-length 128"
python -m ml.training.train_transformer \
    --model distilbert-base-uncased \
    --max-length 256 --epochs 2 --batch-size 16

echo "==> Done. Reports are in ml/reports/, checkpoints in ml/checkpoints/."
echo "    Point MODEL_PATH in .env at the best checkpoint to use it in the API."
