# Projekt Data Analytics – Struktur der deutschen Gastronomiebranche

Dieses Repository enthält den Code zum Projekt **„Struktur der deutschen Gastronomiebranche“** (JLU Gießen, M.Sc. Data Analytics). Analysiert werden Plattformdaten von *speisekarte.de* (Crawl: November 2025) mit Fokus auf strukturelle Kategorien wie **Küchenregion**, **Restaurantkonzept**, **Serviceklasse**, **Öffnungsklasse** und **Kette vs. unabhängig**.

## Inhalte

**Notebooks**
- `Sampling_500_Final.ipynb` – Stichprobe (n=500) für manuelles Labeling
- `PDA_Dummy_Model_Base.ipynb` – Dummy-Baseline (z. B. Mehrheitsklasse)
- `LearningCurve_SetFit.ipynb` – Learning Curves (SetFit)
- `SetFIT_GridSearch.ipynb` – Hyperparameter-Grid-Search (SetFit)
- `Inference.ipynb` – finale Evaluation & Inferenz
- `Predicting_Prices.ipynb` – Vorhersage/Kategorisierung der Preise (z. B. Lieblingsgericht)
- `PDA_Viz.ipynb` – Visualisierungen & Ergebnisplots

**Scrapy Crawler**
- `speisekarte.py` – Spider für speisekarte.de
- `items.py` – Item-Schema/Datamodel
- `parsers.py` – Parser/Helper für Extraktion und Textaufbereitung
- `pipelines.py` – Cleaning/Export-Pipelines
- `settings.py` – Scrapy Settings

## Reihenfolge 
Scraping → Sampling → Baseline → Learning Curves → Grid Search → Inferenz  

