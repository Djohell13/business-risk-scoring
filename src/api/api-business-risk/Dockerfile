# 1. Utiliser une image Python légère
FROM python:3.9-slim

# 2. Définir le répertoire de travail
WORKDIR /app

# 3. Installer les dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lib/lists/*

# 4. Créer un utilisateur non-root
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# 5. Copier les fichiers de dépendances et installer
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 6. Copier tout le reste du code et les modèles
COPY --chown=user . .

# 7. Exposer le port par défaut de Hugging Face
EXPOSE 7860

# 8. Lancer l'application avec Uvicorn

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]