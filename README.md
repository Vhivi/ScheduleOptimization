# Projet de Génération de Planning de Vacations

## Description

Ce projet a pour objectif de générer un planning de vacations pour un ensemble d'agents répartis sur différents postes de travail. L'algorithme prend en compte plusieurs contraintes afin de garantir une répartition équitable des vacations et le respect des règles relatives aux temps de repos et aux volumes horaires. La génération du planning est optimisée à l'aide de Google OR-Tools pour répondre aux principes d'optimisation tout en respectant les contraintes définies.

## Fonctionnalités

### Répartition des vacations

- Génération d'un planning pour `n` agents sur 3 postes (Jour, CDP, Nuit) du lundi au vendredi, puis sur 2 postes (Jour, Nuit) le week-end.
- Chaque vacation est attribuée à un seul agent.
- Chaque agent travaille au maximum une vacation par jour.
- Répartition équitable des vacations, chaque agent doit travailler au moins une vacation.

### Gestion des exceptions

- **Week-end** : Samedi et dimanche, seules les vacations Jour et Nuit sont disponibles.
- **Jours fériés** : Gestion des jours fériés avec uniquement des vacations Jour et Nuit.
- **Congés** : Un agent en congé ne peut pas être planifié pour une vacation.
- **Indisponibilité** : Un agent indisponible ne peut pas travailler le jour concerné.
- **Récupération** : Un agent en récupération ne peut pas être assigné à une vacation.
- **Formation** : Un agent en formation ne peut pas être planifié pour une vacation.

### Contraintes sur les vacations et les repos

- Un agent ne peut pas travailler la nuit et le matin suivant (nécessité de 48h de repos entre une vacation de nuit et une vacation de jour).
- Volume horaire hebdomadaire : un agent ne peut pas travailler plus de 48h par semaine (recommandé : 35h).
- Volume horaire mensuel : un agent ne peut pas travailler plus de 220h par mois (recommandé : 151,67h).
- Volume horaire annuel : un agent ne peut pas travailler plus de 1607h par an (recommandé : 1607h).
- Repos hebdomadaire : chaque agent doit avoir au moins 2 jours de repos consécutifs par semaine.
- Volume horaire des vacations :
  - Jour : 12h
  - Nuit : 12h
  - CDP : 5,5h
- Temps de repos entre deux vacations : 12h minimum.

### Préférences des agents

- **Vacations préférées** : chaque agent peut indiquer des vacations qu'il souhaite travailler en priorité.
- **Vacations à éviter** : chaque agent peut indiquer des vacations qu'il ne souhaite pas travailler.
- **Vacations en binôme** : (à voir si on intègre cette option) chaque agent peut indiquer des vacations qu'il souhaite travailler en binôme.

### Génération du planning

- Génération d'un planning à partir d'une date de début et d'une date de fin sur un **calendrier réel** et non pas sur une période fictive.
- Génération d'un planning pour une période donnée (1 semaine, 1 mois, 1 an).
- Affichage du planning sous forme de tableau.
- Affichage des vacations de chaque agent.
- Affichage coloré des vacations suivant le poste.
- Export du planning au format PDF ou d'autres formats.
- **Optimisation via Google OR-Tools** pour générer les plannings en tenant compte des contraintes.

## Stack Technique

- **Backend** : Flask pour gérer les requêtes et la logique serveur.
- **Frontend** : Vue.js pour une interface utilisateur simple et réactive.
- **Optimisation** : Google OR-Tools pour la génération optimisée des plannings.
- **Configuration** : Paramètres gérés via un fichier `config.json`.
- **Base de données** : Utilisation possible de SQLite à l'avenir pour persister les données, mais la configuration reste actuellement sur des fichiers JSON.

## Installation

1. Clonez ce dépôt :

   ```bash
   git clone https://github.com/votre-utilisateur/projet-planning-vacations.git
   ```

2. Installez les dépendances :

   ```bash
   pip install -r requirements.txt
   ```

3. Installez Google OR-Tools :

   ```bash
   pip install ortools
   ```

## Utilisation

1. Démarrez le serveur Flask :

   ```bash
   flask run
   ```

2. Accédez à l'interface web via votre navigateur à l'adresse indiquée (par défaut `http://127.0.0.1:5000/`).

3. Depuis l'interface web, configurez les agents, postes et préférences, puis générez et visualisez le planning.

## Contribution

Pour le moment, ce projet est pour usage personnel, les contributions ne sont pas ouvertes.

## Licence

Distribué sous la licence MIT. Voir `LICENSE` pour plus d'informations.
