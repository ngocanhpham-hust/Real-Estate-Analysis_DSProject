```markdown
This repository contains a small end-to-end real-estate analysis pipeline: data scraping, preprocessing, exploratory analysis, and modelling. A Streamlit frontend is included to explore the preprocessed dataset and run predictions with saved models.

Contents
- `data/raw/` — raw scraped CSVs
- `data/preprocessed/` — preprocessed CSVs and the integrated dataset
- `data_preprocessed/` — preprocessing notebooks and `integrate.py`
- `data_scraping/` — scraper (`scraper.py`) and helpers (`utils.py`)
- `EDA_and_Data_Visualization/` — EDA notebook
- `modelling/` — modelling notebooks and saved model artifact (`model_gridsearch.pkl`)
- `streamlit_app.py` — Streamlit frontend for interactive exploration and predictions
- `requirements.txt` — Python dependencies

## Quick start

1. Create and activate a Python virtual environment (macOS / zsh):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Ensure the preprocessed dataset exists. The Streamlit app expects `data/preprocessed/full_preprocessed.csv`.

```bash
ls -l data/preprocessed/full_preprocessed.csv
```

If the file is missing but per-source preprocessed files exist (`data/preprocessed/*_preprocessed.csv`), you can integrate them:

```bash
python data_preprocessed/integrate.py
```

4. Run the Streamlit app:

```bash
streamlit run streamlit_app.py
```

Open the URL printed by Streamlit (usually `http://localhost:8501`) in your browser.

## What the Streamlit app provides
- Data Explorer: filters (city, property type, area, price), map view, table and CSV download.
- EDA: histograms and distribution plots for price/price_per_m2.
- Modelling panel (sidebar): select a saved model from `modelling/`, view basic info (best params / scores), run batch predictions on the currently-filtered dataset, download predictions, and perform single-record predictions.
- Feature importance visualization for compatible models.

## Model artifacts
- The repo contains `modelling/model_gridsearch.pkl` — this project saved a dictionary with keys like `best_model`, `best_params`, and `scores`. The Streamlit app handles this format and extracts the inner estimator for prediction.
- Best practice: when training, save a scikit-learn `Pipeline` that includes preprocessing and the estimator. This makes it safe to call `pipeline.predict(X_raw)` from the app without reimplementing transformations.

## Notes about predictions
- The model may have been trained on a transformed target (e.g., `log_price`). The app provides a checkbox `Model predicts log(price) -> inverse exp()` — enable it if your model predicts log(price) so the app will exponentiate outputs before showing prices.
- The app attempts to infer the feature names expected by the model. If features are missing in the current dataset, the app will auto-fill those columns with sensible defaults and show a warning listing which features were added. For production use, prefer saving a Pipeline so preprocessing is consistent.

## Running the scraper
- `data_scraping/scraper.py` uses Selenium and `undetected_chromedriver` to scrape `batdongsan.com.vn`. Scraping requires a compatible Chrome and the `undetected-chromedriver` package; consult the notebook and `scraper.py` for configuration constants (page ranges, delays). Be mindful of site terms-of-service and polite scraping practices.

## Troubleshooting
- If Streamlit reports missing dataset: verify `DATA_PATH` in `streamlit_app.py` or regenerate preprocessed files.
- If prediction fails due to mismatched feature names: ensure your saved model's expected features are present in the preprocessed dataset or save a Pipeline that includes feature engineering.
- If unpickling a model warns about scikit-learn versions: train and save models with the same scikit-learn version you plan to load with.

