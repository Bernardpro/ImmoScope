# Étape 1 : build de l'application
FROM node:20-alpine AS builder

WORKDIR /app

# Copier les fichiers de dépendances
COPY package.json package-lock.json ./

# Installer les dépendances
RUN npm ci

# Étape 2 : image finale
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=development

COPY . .
# Expose port 3000
EXPOSE 3000

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
# Commande de démarrage (en prod ou dev selon besoin)
ENTRYPOINT ["/entrypoint.sh"]
