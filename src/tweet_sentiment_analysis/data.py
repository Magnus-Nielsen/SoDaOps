# from sklearn.model_selection import train_test_split
import os
import re
import shutil
import sys
from pathlib import Path

import pandas as pd
import typer
from dotenv import load_dotenv
from loguru import logger
from sklearn.preprocessing import LabelEncoder

logger.remove()
logger.add(sys.stdout, level="DEBUG")
try:
    from kagglehub import dataset_download
except ModuleNotFoundError as e:
    logger.error(f"Failed to import module: {e}")


def download():
    # Note this is not used as we download via gcp
    # Define the target directory for the raw data
    raw_data_path = Path("data/raw/")
    # Download the dataset
    path = dataset_download("emirhanai/2024-u-s-election-sentiment-on-x", force_download=True)
    path = Path(path)
    for file in path.iterdir():
        if file.is_file():
            shutil.move(str(file), raw_data_path / file.name)


def clean_text(text):
    text = text.lower()  # Lowercase
    text = re.sub(r"http\S+", "", text)  # Remove URLs
    text = re.sub(r"@\w+", "", text)  # Remove mentions
    text = re.sub(r"#\w+", "", text)  # Remove hashtags
    text = re.sub(r"[^a-zA-Z\s]", "", text)  # Remove non-alphabetic characters
    text = re.sub(r"^\s+|\s+$", "", text)  # Remove leading and trailing spaces

    return text


def preprocess():
    load_dotenv()
    logger.info("Preprocessing data")
    raw_data_path = Path("data/raw/")
    train_path = raw_data_path / "train.csv"
    test_path = raw_data_path / "test.csv"
    val_path = raw_data_path / "val.csv"

    # Check if files exist; if not, download them
    if not train_path.exists() or not test_path.exists() or not val_path.exists():
        logger.info("Files not found. Downloading dataset.")
        download()

    train = pd.read_csv("data/raw/train.csv")
    test = pd.read_csv("data/raw/test.csv")
    val = pd.read_csv("data/raw/val.csv")

    # List of datasets
    datasets = [train, test, val]

    # Apply cleaning and encoding to each dataset
    for dataset in datasets:
        # Apply cleaning
        dataset["clean_text"] = dataset["tweet_text"].apply(clean_text)

        # Encode 'party' using Label Encoding
        le_party = LabelEncoder()
        dataset["party_encoded"] = le_party.fit_transform(dataset["party"])

        # Map sentiment to numerical values for evaluation
        sentiment_mapping = {"negative": int(0), "neutral": int(1), "positive": int(2)}
        dataset["sentiment_encoded"] = dataset["sentiment"].str.strip().map(sentiment_mapping)
        if (
            os.getenv("development_mode").replace("'", "").replace('"', "") == "Yes"
        ):  # yaml parsing doesn't like bools and I don't like yaml parsing
            logger.warning("Reducing dataset size to max 50 rows for development purposes!")
            dataset.drop(dataset[dataset.index > 49].index, inplace=True)

    logger.debug(f"Train-size: {train.shape}")
    logger.debug(f"Validation-size: {val.shape}")
    logger.debug(f"Test-size: {test.shape}")
    train.to_parquet("data/processed/train.parquet")
    val.to_parquet("data/processed/val.parquet")
    test.to_parquet("data/processed/test.parquet")


def load_data():
    process_path = Path("data/processed/")
    train_path = process_path / "train.parquet"
    test_path = process_path / "test.parquet"
    val_path = process_path / "val.parquet"

    # Check if files exist; if not, preprocess them
    if not train_path.exists() or not test_path.exists() or not val_path.exists():
        logger.info("Files not found. Preprocessing dataset.")
        preprocess()

    train = pd.read_parquet("data/processed/train.parquet")
    test = pd.read_parquet("data/processed/test.parquet")
    val = pd.read_parquet("data/processed/val.parquet")
    return (train, test, val)


if __name__ == "__main__":
    typer.run(preprocess)
