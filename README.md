# 🚀 GroundTruth Automated Insight Engine

**Tagline:** Drop raw campaign data → get beautiful, AI-written PDF & PPT insights — fully automated.

## 🧩 1. The Problem (Real AdTech Scenario)

Account Managers in AdTech spend **4–6 hours every week**:

- Exporting CSVs manually
- Copying numbers into Excel
- Taking screenshots
- Writing performance summaries manually

This delays insights and hides overspending.

### 💡 My Solution

The **Automated Insight Engine**:

- Ingests raw CSVs
- Processes & aggregates KPIs
- Generates charts & tables
- Uses **Gemini via REST API** for executive summaries
- Outputs beautifully formatted **PDF + PPT**

## 🎯 2. Expected End Result

### Input:

- traffic.csv
- clicks.csv
- weather.csv
- (optional) SQL tables

### Output:

- 📄 PDF Report
- 📊 PPT Deck

Both fully automated.

## 🛠️ 3. Technical Approach

The Automated Insight Engine follows a clean, modular pipeline that goes from raw CSV files to fully generated PDF + PPT reports using AI.

### 3.1 Ingestion

The pipeline starts by loading all raw data:

- traffic.csv – impressions per day/campaign

- clicks.csv – clicks per day/campaign

- weather.csv – optional weather context

- Optional SQL tables (using SQLAlchemy)

Data is validated, types are corrected (dates, numbers), and missing fields are handled so that the rest of the pipeline receives clean input.

### 3.2 Processing

Once the data is ingested, the engine:

- Merges datasets on campaign_id and date

- Calculates all key performance metrics:

- CTR, CPC, CPA, CVR, spend ratios

Builds:

- Campaign-level summaries

- Overall account performance

- Prepares clean tables for charts and reporting

This step produces a single, structured dataset used for both visualizations and AI analysis.

### 3.3 AI Insight Generation

The insight engine sends processed metrics to Google Gemini using a custom HTTP API client.

The LLM generates:

- Executive summary

- Trend explanations

- Key campaign highlights

- Recommendations for next week

The prompt is structured so the AI writes like a senior data analyst.
If the LLM is not available or fails → the pipeline stops with an error (as required).

### 3.4 Visualization

Using Matplotlib, the engine automatically generates charts. These images are saved as PNGs and later embedded in the PDF and PPT.

### 3.5 Reporting

Finally, the system produces two polished outputs: PDF (ReportLab), PPT Deck (python-pptx).
Both files are formatted to be ready for client delivery.

## 🧰 5. Tools Used

- Python
- Pandas
- Matplotlib
- ReportLab
- python-pptx
- Requests (Gemini API)
- YAML

## ▶️ 6. How to Run

```
# Create a virtual environment
python -m venv .venv

# Activate venv
.\.venv\Scripts\Activate.ps1

# Install deps
pip install -r requirements.txt

# Add Gemini key
$env:GEMINI_API_KEY="your_key"

# Run
python -m src.main --config config/config.yaml
```
