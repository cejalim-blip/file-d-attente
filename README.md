# File d'attente — Relais public

Relais de suivi public pour l'application de file d'attente du
**Centre d'Entraide de Jette – ASBL**.

Ce service reçoit l'état public de la file (numéro en cours,
derniers appels, nombre en attente) depuis le PC du Centre et
l'affiche aux visiteurs sur leur téléphone. Aucune donnée
personnelle, aucun accès à l'administration.

## Déploiement sur Render

1. Déployez ce dépôt sur [Render](https://render.com) (type *Web Service*, plan *Free*).
2. Ajoutez une variable d'environnement `RELAY_KEY` (une phrase secrète).
3. Copiez l'adresse publique (`https://...onrender.com`) et la clé
   dans les Réglages de l'application, sur le PC.

Le fichier `render.yaml` permet un déploiement automatique.
