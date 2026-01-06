import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import joblib
from pathlib import Path
import math

DATA_PATH = "data/preprocessed/full_preprocessed.csv"
MODEL_DIR = "modelling"
DEFAULT_MODEL = "modelling/model_gridsearch.pkl"


@st.cache_data
def load_data(path = DATA_PATH):
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        return None

    # Ensure numeric columns are numeric
    for c in ["price", "area", "price_per_m2", "latitude", "longitude"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


@st.cache_resource
def load_model(path=DEFAULT_MODEL):
    p = Path(path)
    if not p.exists():
        return None
    try:
        obj = joblib.load(path)
    except Exception as e:
        st.error(f"Failed to load model {path}: {e}")
        return None
    return obj


def infer_feature_columns(estimator, df_columns):
    # Try to extract feature names from estimator, fallback to sensible defaults
    if estimator is None:
        return []
    # If GridSearchCV or similar
    if hasattr(estimator, "best_estimator_"):
        estimator = estimator.best_estimator_

    # If sklearn Pipeline with named steps
    try:
        # prefer explicit attribute
        if hasattr(estimator, "feature_names_in_"):
            return list(estimator.feature_names_in_)
    except Exception:
        pass

    # Fallback: common numeric features found in dataframe
    common_feats = [
        "area",
        "n_bedrooms",
        "n_bathrooms",
        "n_floors",
        "price_per_m2",
        "front_width",
        "interior_score",
        "legal_score",
    ]
    return [c for c in common_feats if c in df_columns]


def resolve_model(obj):
    """Return (estimator, meta) where meta is a dict of extra info.
    Handles cases where the loaded object is a dict containing keys like
    'best_model', 'best_params', 'scores', or a sklearn GridSearchCV/estimator.
    """
    if obj is None:
        return None, {}
    # dict-style saved artifact
    if isinstance(obj, dict):
        # common keys
        if 'best_model' in obj:
            est = obj.get('best_model')
            meta = {k: obj.get(k) for k in ('best_params', 'scores') if k in obj}
            return est, meta
        if 'model' in obj:
            return obj.get('model'), {k: obj.get(k) for k in obj.keys() if k != 'model'}
        # try other common keys
        for k in ('estimator', 'best_estimator'):
            if k in obj:
                return obj.get(k), {kk: obj.get(kk) for kk in obj.keys() if kk != k}
        # nothing recognizable
        return None, {}

    # sklearn GridSearchCV or estimator
    meta = {}
    if hasattr(obj, 'best_estimator_'):
        est = obj.best_estimator_
        if hasattr(obj, 'best_params_'):
            meta['best_params'] = obj.best_params_
        if hasattr(obj, 'cv_results_'):
            meta['cv_results'] = obj.cv_results_
        return est, meta

    # plain estimator
    return obj, {}


def prepare_features(estimator, df, feature_names):
    """Return DataFrame X with exactly the columns in feature_names in the same order.
    If columns are missing from df, add them with sensible defaults (median for numeric, 0 for others)
    and return a list of filled columns so the UI can warn the user.
    """
    filled = []
    X = pd.DataFrame(index=df.index)
    for col in feature_names:
        if col in df.columns:
            X[col] = df[col]
        else:
            # choose default: numeric -> median if possible, else 0
            default_val = 0
            if any(pd.api.types.is_numeric_dtype(df[c]) for c in df.columns):
                # attempt to use a reasonable default: 0 or median of a similar numeric column
                default_val = 0
            X[col] = default_val
            filled.append(col)
    # coerce numeric columns where possible
    for c in X.columns:
        X[c] = pd.to_numeric(X[c], errors='coerce')
    return X, filled


def main():
    st.set_page_config(layout="wide", page_title="Real Estate Explorer")
    st.title("Vietnamese Real Estate")

    st.markdown(
        """
        Simple interactive explorer for the project's preprocessed dataset.
        Use the sidebar to filter listings, view a map, histograms, and download filtered rows.
        """
    )

    df = load_data()
    if df is None:
        st.error(f"Could not find dataset at `{DATA_PATH}`. Run preprocessing first.")
        return

    # Sidebar filters
    st.sidebar.header("Filters")

    # City/Province filter
    if "city_province" in df.columns:
        cities = sorted(df["city_province"].dropna().unique().tolist())
        selected_cities = st.sidebar.multiselect("City / Province", options=cities, default=None)
    else:
        selected_cities = None

    # Property type
    if "property_type" in df.columns:
        ptypes = sorted(df["property_type"].dropna().unique().tolist())
        selected_types = st.sidebar.multiselect("Property type", options=ptypes, default=None)
    else:
        selected_types = None

    # Area slider
    if "area" in df.columns:
        a_min = float(np.nanmin(df["area"])) if df["area"].notna().any() else 0.0
        a_max = float(np.nanmax(df["area"])) if df["area"].notna().any() else 1000.0
        area_range = st.sidebar.slider("Area (m²)", min_value=0.0, max_value=round(a_max, 1), value=(round(a_min, 1), round(a_max, 1)))
    else:
        area_range = None

    # Price slider (use price_per_m2 if available else price)
    price_col = "price" if "price" in df.columns else "price"
    if price_col in df.columns:
        p_min = float(np.nanmin(df[price_col])) if df[price_col].notna().any() else 0.0
        p_max = float(np.nanmax(df[price_col])) if df[price_col].notna().any() else 1.0
        price_range = st.sidebar.slider(f"{price_col}", min_value=0.0, max_value=round(p_max, 2), value=(round(p_min, 2), round(p_max, 2)))
    else:
        price_range = None

    # Apply filters
    df_filtered = df.copy()
    if selected_cities:
        df_filtered = df_filtered[df_filtered["city_province"].isin(selected_cities)]
    if selected_types:
        df_filtered = df_filtered[df_filtered["property_type"].isin(selected_types)]
    if area_range and "area" in df_filtered.columns:
        df_filtered = df_filtered[(df_filtered["area"] >= area_range[0]) & (df_filtered["area"] <= area_range[1])]
    if price_range and "price" in df_filtered.columns:
        df_filtered = df_filtered[(df_filtered[price_col] >= price_range[0]) & (df_filtered[price_col] <= price_range[1])]

    st.sidebar.markdown(f"**Results:** {len(df_filtered):,} rows")

    # Top metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Listings", f"{len(df_filtered):,}")
    with col2:
        if price_col in df_filtered.columns and df_filtered[price_col].notna().any():
            st.metric(f"Avg {price_col}", f"{df_filtered[price_col].median():.2f}")
        else:
            st.metric(f"Avg {price_col}", "n/a")
    with col3:
        if "area" in df_filtered.columns and df_filtered["area"].notna().any():
            st.metric("Avg area (m²)", f"{df_filtered['area'].median():.1f}")
        else:
            st.metric("Avg area (m²)", "n/a")

    # ---------------------
    # Modelling panel (sidebar)
    # ---------------------
    st.sidebar.header("Modeling")
    # list available models in modelling dir
    model_files = []
    md = Path(MODEL_DIR)
    if md.exists() and md.is_dir():
        model_files = sorted([str(p) for p in md.glob("*.pkl")])
    if DEFAULT_MODEL not in model_files and Path(DEFAULT_MODEL).exists():
        model_files.insert(0, DEFAULT_MODEL)

    selected_model = st.sidebar.selectbox("Choose model file", options=model_files or ["(no models found)"], index=0 if model_files else 0)
    model_obj = None
    if selected_model and selected_model != "(no models found)":
        model_obj = load_model(selected_model)

    if model_obj is None:
        st.sidebar.info("No model loaded. Place a .pkl trained model in the `modelling/` folder.")
    else:
        st.sidebar.markdown(f"**Loaded:** `{Path(selected_model).name}`")
        # show basic model info
        try:
            est, meta = resolve_model(model_obj)
            st.sidebar.write(type(est))
            if 'best_params' in meta:
                st.sidebar.write("**Best params**")
                st.sidebar.write(meta['best_params'])
            if 'scores' in meta:
                st.sidebar.write("**Scores**")
                st.sidebar.write(meta['scores'])
            if 'cv_results' in meta:
                mean_scores = meta['cv_results'].get("mean_test_score")
                if mean_scores is not None:
                    best_idx = int(np.nanargmax(mean_scores))
                    st.sidebar.write(f"CV best score: {mean_scores[best_idx]:.4f}")
        except Exception:
            pass

    # predict settings
    predict_log = st.sidebar.checkbox("Model predicts log(price) -> inverse exp()", value=False)
    run_predict = st.sidebar.button("Run predictions on filtered data")

    if run_predict and model_obj is not None:
        estimator, _meta = resolve_model(model_obj)
        feature_cols = infer_feature_columns(estimator, df_filtered.columns)
        if not feature_cols:
            st.warning("Could not infer model feature columns. Please provide a pipeline that preserves `feature_names_in_` or ensure default features exist in dataset.")
        else:
            # prepare feature matrix with exact order and fill missing cols
            X, filled = prepare_features(estimator, df_filtered, feature_cols)
            if filled:
                st.warning(f"The model expects features that were missing in the dataset. Added columns with default values: {filled}")
            try:
                preds = estimator.predict(X)
                df_filtered = df_filtered.copy()
                df_filtered["model_output"] = preds
                if predict_log:
                    df_filtered["predicted_price"] = np.exp(preds)
                else:
                    df_filtered["predicted_price"] = preds

                st.success(f"Predicted {len(df_filtered)} rows")
                # show summary metrics
                if "price" in df_filtered.columns:
                    fig = px.scatter(df_filtered.sample(min(len(df_filtered), 2000)), x="price", y="predicted_price", trendline="ols", title="Actual vs Predicted")
                    st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df_filtered[["predicted_price"]].head(200))
                csvp = df_filtered.to_csv(index=False).encode("utf-8")
                st.download_button(label="Download predictions (CSV)", data=csvp, file_name="predictions.csv", mime="text/csv")

                # feature importance
                try:
                    imp = None
                    if hasattr(estimator, "feature_importances_"):
                        imp = estimator.feature_importances_
                    elif hasattr(estimator, "coef_"):
                        imp = np.abs(estimator.coef_).ravel()
                    if imp is not None:
                        # align importance to X columns (if lengths match)
                        feat_names = list(X.columns)
                        if len(imp) == len(feat_names):
                            fi = pd.DataFrame({"feature": feat_names, "importance": imp})
                            fi = fi.sort_values("importance", ascending=False).head(30)
                            fig2 = px.bar(fi, x="importance", y="feature", orientation="h", title="Feature importances")
                            st.plotly_chart(fig2, use_container_width=True)
                except Exception:
                    pass
            except Exception as e:
                st.error(f"Prediction failed: {e}")

    # single-record prediction form
    st.sidebar.markdown("---")
    st.sidebar.subheader("Single-record prediction")
    single_pred = None
    if model_obj is not None:
        estimator, _meta = resolve_model(model_obj)
        feature_cols = infer_feature_columns(estimator, df.columns)
        if not feature_cols:
            # fallback small form
            f_area = st.sidebar.number_input("Area (m2)", value=50.0)
            f_bed = st.sidebar.number_input("Bedrooms", value=2, step=1)
            f_bath = st.sidebar.number_input("Bathrooms", value=1, step=1)
            if st.sidebar.button("Predict single"):
                x = pd.DataFrame([{"area": f_area, "n_bedrooms": f_bed, "n_bathrooms": f_bath}])
                try:
                    p = estimator.predict(x)[0]
                    if predict_log:
                        p = float(np.exp(p))
                    st.sidebar.success(f"Predicted price: {p:.2f}")
                except Exception as e:
                    st.sidebar.error(f"Prediction failed: {e}")
        else:
            # build inputs dynamically for inferred features
            inp = {}
            with st.sidebar.form("single_form"):
                for f in feature_cols:
                    # numeric inputs only
                    val = 0.0
                    if f in df.columns and pd.api.types.is_numeric_dtype(df[f]):
                        val = float(df[f].median() if df[f].notna().any() else 0.0)
                    inp[f] = st.number_input(f, value=val)
                submit = st.form_submit_button("Predict single")
            if submit:
                x_raw = pd.DataFrame([inp])
                X_single, filled_single = prepare_features(estimator, x_raw, feature_cols)
                if filled_single:
                    st.sidebar.warning(f"Added missing feature columns with defaults: {filled_single}")
                try:
                    p = estimator.predict(X_single)[0]
                    if predict_log:
                        p = float(np.exp(p))
                    st.sidebar.success(f"Predicted price: {p:.2f}")
                except Exception as e:
                    st.sidebar.error(f"Prediction failed: {e}")

    # Map
    st.subheader("Map of listings")
    if "latitude" in df_filtered.columns and "longitude" in df_filtered.columns:
        map_df = df_filtered[["latitude", "longitude"]].dropna()
        if not map_df.empty:
            map_df = map_df.rename(columns={"latitude": "lat", "longitude": "lon"})
            st.map(map_df.sample(min(len(map_df), 2000)))
        else:
            st.info("No geolocation data available for the current filters.")
    else:
        st.info("Dataset does not contain `latitude`/`longitude` columns.")

    # Histogram
    st.subheader(f"Distribution of {price_col}")
    if price_col in df_filtered.columns and df_filtered[price_col].notna().any():
        fig = px.histogram(df_filtered, x=price_col, nbins=50, title=f"{price_col} distribution")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info(f"No `{price_col}` values available to plot.")

    # Table and download
    st.subheader("Listings table")
    display_cols = [c for c in ["title", "address", "city_province", "district", "area", "price", "price_per_m2", "property_type", "date_of_posting", "url"] if c in df_filtered.columns]
    st.dataframe(df_filtered[display_cols].head(500))

    csv = df_filtered.to_csv(index=False).encode("utf-8")
    st.download_button(label="Download filtered data (CSV)", data=csv, file_name="filtered_listings.csv", mime="text/csv")


if __name__ == "__main__":
    main()
