# Equity Strategist

## Vision

Equity Strategist est un assistant conversationnel spécialisé dans les marchés actions.

Son objectif est de répondre à des questions quantitatives comme le ferait un analyste equity ou un très bon stagiaire en recherche.

L'utilisateur interagit uniquement en langage naturel.

L'agent :

- comprend la demande ;
- identifie les données nécessaires ;
- récupère les données de marché ;
- réalise les calculs financiers ;
- restitue une réponse quantitative argumentée.

Cette première version est limitée aux actions.

À terme, Equity Strategist constituera la première brique d'un Financial Reasoning Framework qui sera étendu aux autres classes d'actifs (Fixed Income, FX, Credit...) avant d'alimenter un assistant Sales dédié aux produits structurés.

---

## Philosophie

La valeur du projet réside dans le raisonnement financier.

Les données proviennent d'un fournisseur externe.

La première implémentation utilise Yahoo Finance mais l'architecture reste indépendante du fournisseur.

Le LLM :

- comprend ;
- planifie ;
- orchestre.

Python :

- récupère les données ;
- réalise tous les calculs financiers ;
- retourne des objets métier.

Le projet privilégie des briques simples, réutilisables et testables.
