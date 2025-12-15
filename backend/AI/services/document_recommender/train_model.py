"""
Training Pipeline for Multi-Label Document Requirement Classifier
Trains a model to predict required shipping documents based on shipment attributes.
"""
import argparse
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Tuple, List, Dict
from datetime import datetime

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder, FunctionTransformer
from sklearn.compose import ColumnTransformer
from sklearn.multioutput import MultiOutputClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score, hamming_loss
from sklearn.preprocessing import MultiLabelBinarizer

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    from sklearn.feature_extraction.text import TfidfVectorizer

import warnings
warnings.filterwarnings("ignore")


class DocumentRequirementTrainer:
    """Multi-label document requirement classifier trainer."""
    
    def __init__(self, text_model: str = "all-MiniLM-L6-v2"):
        self.text_model = text_model
        self.mlb = MultiLabelBinarizer()
        self.feature_preprocessor = None
        self.classifier = None
        self.label_names = None
        self.model_metadata = {}
    
    def load_and_validate_data(self, data_file: str) -> pd.DataFrame:
        """Load CSV and validate required columns."""
        df = pd.read_csv(data_file)
        required_cols = [
            "product_name", "category", "product_description", "hs_code",
            "origin_country", "destination_country", "package_type", "weight",
            "declared_value", "shipment_type", "service_level", "required_documents"
        ]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        if df["required_documents"].isna().any():
            raise ValueError("required_documents column contains null values")
        
        print(f"✓ Loaded {len(df)} records from {data_file}")
        return df
    
    def preprocess_features(self, df: pd.DataFrame) -> np.ndarray:
        """Preprocess and combine all features."""
        # Text features: combine product info
        text_features = (
            df["product_name"] + " " +
            df["category"] + " " +
            df["product_description"] + " " +
            df["hs_code"]
        ).values
        
        # Encode text
        if HAS_SENTENCE_TRANSFORMERS:
            print(f"  Encoding text with SentenceTransformer ({self.text_model})...")
            model = SentenceTransformer(self.text_model)
            text_embeddings = model.encode(text_features, show_progress_bar=False)
        else:
            print("  Encoding text with TF-IDF...")
            tfidf = TfidfVectorizer(max_features=128, stop_words="english")
            text_embeddings = tfidf.fit_transform(text_features).toarray()
        
        # Categorical features
        categorical_features = df[["origin_country", "destination_country", "package_type", "shipment_type", "service_level"]]
        ohe = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
        cat_embeddings = ohe.fit_transform(categorical_features)
        
        # Numeric features
        numeric_features = df[["weight", "declared_value"]].values
        scaler = StandardScaler()
        numeric_scaled = scaler.fit_transform(numeric_features)
        
        # Combine all
        features = np.hstack([text_embeddings, cat_embeddings, numeric_scaled])
        print(f"  Feature matrix shape: {features.shape}")
        
        return features
    
    def parse_labels(self, df: pd.DataFrame) -> np.ndarray:
        """Parse comma-separated document lists into binary matrix."""
        label_lists = [
            [doc.strip() for doc in docs_str.split(",")]
            for docs_str in df["required_documents"]
        ]
        
        # Get all unique labels
        all_labels = set()
        for docs in label_lists:
            all_labels.update(docs)
        self.label_names = sorted(list(all_labels))
        
        print(f"  Found {len(self.label_names)} unique document types:")
        for label in self.label_names:
            print(f"    - {label}")
        
        # Binarize
        labels = self.mlb.fit_transform(label_lists)
        print(f"  Label matrix shape: {labels.shape}")
        
        return labels
    
    def train(
        self,
        data_file: str,
        test_size: float = 0.2,
        random_state: int = 42
    ):
        """Train the multi-label classifier."""
        print(f"\n{'='*60}")
        print("DOCUMENT REQUIREMENT CLASSIFIER TRAINING")
        print(f"{'='*60}\n")
        
        # Load data
        df = self.load_and_validate_data(data_file)
        
        # Preprocess features
        print("\nPreprocessing features...")
        X = self.preprocess_features(df)
        
        # Parse labels
        print("\nParsing labels...")
        y = self.parse_labels(df)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        print(f"\nTrain/test split: {len(X_train)} / {len(X_test)}")
        
        # Train classifier
        print("\nTraining multi-output classifier...")
        self.classifier = MultiOutputClassifier(
            LogisticRegression(max_iter=1000, random_state=random_state, n_jobs=-1)
        )
        self.classifier.fit(X_train, y_train)
        
        # Evaluate
        print("\nEvaluating model...")
        y_pred = self.classifier.predict(X_test)
        
        # Compute metrics
        precision = precision_score(y_test, y_pred, average="micro", zero_division=0)
        recall = recall_score(y_test, y_pred, average="micro", zero_division=0)
        f1 = f1_score(y_test, y_pred, average="micro", zero_division=0)
        h_loss = hamming_loss(y_test, y_pred)
        
        print(f"  Precision (micro): {precision:.4f}")
        print(f"  Recall (micro):    {recall:.4f}")
        print(f"  F1-score (micro):  {f1:.4f}")
        print(f"  Hamming Loss:      {h_loss:.4f}")
        
        # Store metadata
        self.model_metadata = {
            "model_version": "v1",
            "training_timestamp": datetime.utcnow().isoformat(),
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "num_labels": len(self.label_names),
            "label_names": self.label_names,
            "metrics": {
                "precision": float(precision),
                "recall": float(recall),
                "f1": float(f1),
                "hamming_loss": float(h_loss),
            },
            "text_encoder": self.text_model if HAS_SENTENCE_TRANSFORMERS else "tfidf",
        }
    
    def save_model(self, models_dir: str = None):
        """Save trained model and preprocessing pipeline."""
        models_dir = Path(models_dir or Path(__file__).parent / "models")
        models_dir.mkdir(parents=True, exist_ok=True)
        
        # Save classifier
        model_path = models_dir / "required_docs_model.pkl"
        with open(model_path, "wb") as f:
            pickle.dump({
                "classifier": self.classifier,
                "mlb": self.mlb,
                "label_names": self.label_names,
                "metadata": self.model_metadata,
            }, f)
        print(f"\n✓ Saved model to {model_path}")
        
        # Save metadata separately for easy access
        metadata_path = models_dir / "model_metadata.pkl"
        with open(metadata_path, "wb") as f:
            pickle.dump(self.model_metadata, f)
        print(f"✓ Saved metadata to {metadata_path}")


def main():
    parser = argparse.ArgumentParser(description="Train document requirement classifier")
    parser.add_argument(
        "--data-file",
        type=str,
        help="Path to training CSV file"
    )
    parser.add_argument(
        "--use-synthetic",
        action="store_true",
        help="Generate and use synthetic data"
    )
    parser.add_argument(
        "--synthetic-rows",
        type=int,
        default=1000,
        help="Number of synthetic records (if --use-synthetic)"
    )
    parser.add_argument(
        "--save-dir",
        type=str,
        help="Directory to save models"
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Test set fraction"
    )
    
    args = parser.parse_args()
    
    # Determine data file
    if args.use_synthetic:
        from generate_synthetic_data import generate_synthetic_documents
        data_dir = Path(__file__).parent / "data"
        data_file = data_dir / "synthetic_documents_data.csv"
        print(f"Generating {args.synthetic_rows} synthetic records...")
        generate_synthetic_documents(
            num_records=args.synthetic_rows,
            output_file=str(data_file)
        )
    elif args.data_file:
        data_file = args.data_file
    else:
        # Try default locations
        default_path = Path(__file__).parent / "data" / "documents_training_data.csv"
        synthetic_path = Path(__file__).parent / "data" / "synthetic_documents_data.csv"
        
        if default_path.exists():
            data_file = str(default_path)
        elif synthetic_path.exists():
            data_file = str(synthetic_path)
        else:
            print("❌ No training data found. Provide --data-file or use --use-synthetic")
            return
    
    # Train
    trainer = DocumentRequirementTrainer()
    trainer.train(data_file=str(data_file), test_size=args.test_size)
    
    # Save
    trainer.save_model(models_dir=args.save_dir)
    print("\n✓ Training complete!")


if __name__ == "__main__":
    main()
