# Projekt Data Analytics – Struktur der deutschen Gastronomiebranche

Dieses Repository enthält den Code zum Projekt **„Struktur der deutschen Gastronomiebranche“** (JLU Gießen, M.Sc. Data Analytics). Analysiert werden Plattformdaten von *speisekarte.de* (Crawl: November 2025) mit Fokus auf strukturelle Kategorien wie **Küchenregion**, **Restaurantkonzept**, **Serviceklasse**, **Öffnungsklasse** und **Chain vs. Independent**.

## Inhalte
**Notebooks**
- `Sampling_500_Final.ipynb` – Stichprobe (n=500) für manuelles Labeling  
- `PDA_Dummy_Model_Base.ipynb` – Dummy-Baseline  
- `LearningCurve_SetFit.ipynb` – Learning Curves  
- `SetFIT_GridSearch.ipynb` – Grid Search  
- `Inference.ipynb` – finale Evaluation & Inferenz

**Scrapy**
- `speisekarte.py`, `parsers.py`, `items.py`, `pipelines.py`, `settings.py`

## Reihenfolge (empfohlen)
Sampling → Baseline → Learning Curves → Grid Search → Inferenz  

