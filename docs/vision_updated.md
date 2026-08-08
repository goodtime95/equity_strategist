# Equity Strategist

## Vision

Equity Strategist est un assistant conversationnel spécialisé dans les marchés actions.

Son objectif est de répondre à des questions quantitatives et d'analyser un univers d'investissement comme le ferait un analyste equity ou un très bon stagiaire en recherche.

L'utilisateur interagit uniquement en langage naturel.

L'agent :

- comprend la demande ;
- identifie les actifs, périodes et données nécessaires ;
- sélectionne les capacités déterministes appropriées ;
- récupère les données de marché ;
- réalise les calculs financiers en Python ;
- interprète les résultats ;
- restitue une réponse quantitative claire et argumentée.

Cette première version est volontairement limitée aux actions.

À terme, Equity Strategist constituera la première spécialisation d'un Financial Reasoning Framework étendu au Fixed Income, FX, Credit et Cross Asset, avant d'alimenter un assistant Sales dédié aux produits structurés.

---

## Philosophie

La valeur du projet réside dans le raisonnement financier, pas dans la possession d'une base de données de marché.

Les données proviennent de fournisseurs externes.

La première implémentation utilise Yahoo Finance, mais l'architecture reste indépendante du fournisseur.

Le système sépare volontairement deux mondes.

### Raisonnement probabiliste / LLM

Le LLM :

- comprend le langage naturel ;
- identifie l'intention ;
- planifie les étapes ;
- choisit les services appropriés ;
- conserve le contexte conversationnel ;
- interprète les résultats ;
- formule la réponse.

### Moteur déterministe / Python

Python :

- identifie les actifs via le registre interne ;
- récupère les données ;
- normalise les observations ;
- construit les séries temporelles ;
- réalise tous les calculs financiers ;
- exécute les workflows métier déterministes ;
- retourne des résultats structurés.

Le LLM ne réalise jamais lui-même un calcul financier.

---

## Core Abstractions

Le framework repose progressivement sur trois objets centraux :

```text
Asset
= identité d'un instrument financier

MarketSeries
= une grandeur financière observée dans le temps

MarketDataset
= un ensemble cohérent de séries pour plusieurs actifs
```

Ces abstractions doivent rester indépendantes du fournisseur de données et du LLM.

---

## Development Philosophy

Le projet privilégie des briques :

- simples ;
- réutilisables ;
- testables ;
- composables ;
- indépendantes des fournisseurs externes.

Le développement est volontairement vertical.

L'objectif n'est pas de construire toutes les capacités financières avant de tester l'agent.

Une fois un moteur déterministe suffisamment riche pour plusieurs vrais cas d'usage, la priorité devient de connecter un Equity Strategist minimal et de tester des questions réelles.

Les capacités supplémentaires — rankings, univers, périodes de marché, fréquences, cache, nouvelles métriques — sont ensuite ajoutées en fonction des besoins observés.

---

## Long-Term Architecture

```text
User
  |
  v
Equity Strategist
  |
  v
Deterministic Analysis Services
  |
  +-------------------------+
  |                         |
  v                         v
Market Data Engine       Compute Engine
  |                         |
  +------------+------------+
               |
               v
       Structured Results
               |
               v
        LLM Interpretation
```

The Equity Strategist is therefore not a chatbot around a market-data API.

It is a reasoning layer built on top of a deterministic, reusable financial-analysis engine.
