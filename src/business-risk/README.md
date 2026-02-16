---
title: Business Risk Scoring
emoji: 🚀
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: true
tags:
- streamlit
- machine-learning
- docker
- survival-analysis
- sirene
- fintech
---

# 📊 Scoring du Risque de Défaillance (Expertise ML)

Ce projet démontre ma capacité à concevoir et déployer une solution de **Machine Learning de bout en bout**, en appliquant des méthodes de modélisation avancées (Survival Analysis) à des problématiques de risque métier.

## 🎯 Objectif du Projet
L'enjeu est de modéliser la probabilité de survenance d'un événement (défaillance d'entreprise) sur un horizon temporel donné. Contrairement à une classification binaire classique, ce projet utilise une approche de **Survival Analysis** (Time-to-Event) pour capturer la dynamique temporelle du risque.

## 📂 Source des données & Périmètre
Le modèle exploite les données officielles de la base **SIRENE V3 (Insee)**. 
- **Périmètre ciblé :** Analyse focalisée sur les **SAS** et **SARL**.
- **Contrainte :** Étude limitée aux entités publiant leurs bilans annuels.
- **Ingénierie :** Filtrage et structuration de données administratives brutes pour isoler les variables financières et démographiques pertinentes.

## 🛠 Stack Technique & Ingénierie
- **Langage :** Python
- **Modélisation :** Survival Analysis avec **XGBoost** (Cox Model).
- **Optimisation :** Recherche d'hyperparamètres via **Optuna**.
- **Conteneurisation :** Architecture et déploiement via **Docker**.
- **Interface :** Dashboard de visualisation avec **Streamlit**.
- **Performance :** Modèle validé avec un score **C-index de 0.749**.

## 🚀 Contenu de la Démo
Cette interface est une **vitrine technique** permettant de visualiser :
- **La performance du modèle :** Analyse approfondie des métriques et validation du C-index.
- **L'interprétabilité :** Analyse de l'impact des variables (secteurs d'activité, tranches d'effectifs, ancienneté) sur le calcul du score de risque.
- **L'architecture Ops :** Démonstration d'un service packagé sous Docker, garantissant la portabilité et la mise en production du modèle.

---
**Auteur :** Joël Termondjian – Data Engineer & Expert Risk & Finance  
[LinkedIn](https://www.linkedin.com/in/joeltermondjian) | [GitHub](https://github.com/Djohell13)