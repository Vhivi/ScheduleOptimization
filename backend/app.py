from flask import Flask, jsonify, request
import json
from flask_cors import CORS
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
import locale
from collections import defaultdict

app = Flask(__name__)
CORS(app)

@app.route('/config')
# Charger le fichier de configuration
def load_config():
    with open('config.json', 'r') as config_file:
        return json.load(config_file)

config = load_config()
weekend_days = ["Sam", "Dim"]  # Jours du week-end abrégés
holidays = config['holidays-2024']  # Jours fériés en 2024

@app.route('/')
def home():
    return "Hello, Flask is up and running!"

@app.route('/generate-planning', methods=['POST'])
def generate_planning_route():
    # Récupération des données à partir du fichier JSON
    agents = config['agents']
    vacations = config['vacations']
    vacation_durations = config['vacation_durations']
    holidays = config['holidays-2024']
    unavailable = {}
    dayOff = {}
    
    # Récupérer les jours d'indisponibilité des agents et les stocker dans un dictionnaire {agent: [jours]}
    for agent in agents:
        if "unavailable" in agent:
            unavailable[agent['name']] = agent['unavailable']
            
    
    # Récupérer les jours de congés des agents
    for agent in agents:
        if "vacation" in agent:
            vacation = agent['vacation']
            if isinstance(vacation, dict) and 'start' in vacation and 'end' in vacation:
                vacation_start = vacation['start']
                vacation_end = vacation['end']

                # Stocker les jours de congés dans un dictionnaire {agent: [début, fin]}
                dayOff[agent['name']] = [vacation_start, vacation_end]
    
    # # Récupérer les dates de début et de fin
    start_date = request.json['start_date']
    end_date = request.json['end_date']
    
    # Calculer la liste des jours à partir des dates
    week_schedule = get_week_schedule(start_date, end_date)
    
    # Appel de la fonction de génération de planning
    result = generate_planning(agents, vacations, week_schedule)
    
    return jsonify({
        "planning": result,
        "vacation_durations": vacation_durations,
        "week_schedule": week_schedule,
        "holidays": holidays,
        "unavailable": unavailable,
        "dayOff": dayOff
    })
    
def get_week_schedule(start_date_str, end_date_str):
    # Configuer le local pour utiliser les jours de la semaine en français
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
    # Convertir les chaines en objets datetime
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')  # Format date / ISO 8601
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')  # Format date / ISO 8601
    
    # Calculer les jours entre la date de début et la date de fin
    delta = end_date - start_date
    week_schedule = [(start_date + timedelta(days=i)).strftime("%a %d-%m").capitalize() for i in range(delta.days + 1)] # Format : Jour abrégé + Date (ex: Lun 25-12)
    return week_schedule

def split_into_weeks(week_schedule):
    # Diviser la liste des jours en semaines calendaires (lundi à dimanche)
    weeks = []
    current_week = []
    
    for day in week_schedule:
        # Ajouter le jour à la semaine courante
        current_week.append(day)
        
        # Si le jour est un dimanche ou le dernier jour du planning, terminer la semaine
        day_name = day.split(" ")[0]  # Extraire le nom du jour (ex: Lun.)
        if day_name == "Dim." or day == week_schedule[-1]:   # Dimanche ou dernier jour
            weeks.append(current_week)
            current_week = []
            
    return weeks


def generate_planning(agents, vacations, week_schedule):
    model = cp_model.CpModel()
    
    # Ajuster les durées des vacations en multipliant par 10 pour éliminer les décimales
    jour_duration = int(config['vacation_durations']['Jour'] * 10)
    nuit_duration = int(config['vacation_durations']['Nuit'] * 10)
    cdp_duration = int(config['vacation_durations']['CDP'] * 10)
    
    ########################################################
    # Variables
    ########################################################
    
    # Une variable par agent/vacation/jour
    planning = {}
    for agent in agents:
        agent_name = agent['name']  # Utiliser le nom de l'agent comme clé
        for day in week_schedule:
            for vacation in vacations:
                planning[(agent_name, day, vacation)] = model.NewBoolVar(f'planning_{agent_name}_{day}_{vacation}')
                
    ########################################################
    # Contraintes
    ########################################################
    
    # Chaque agent peut travailler au plus une vacation par jour
    for agent in agents:
        agent_name = agent['name']
        for day in week_schedule:
            model.Add(sum(planning[(agent_name, day, vacation)] for vacation in vacations) <= 1)
            
    # Au moins une vacation par agent pour la semaine
    for agent in agents:
        agent_name = agent['name']
        model.Add(sum(planning[(agent_name, day, vacation)] for day in week_schedule for vacation in vacations) >= 1)
        
    # Chaque vacation doit être assignée à un agent chaque jour, sauf CDP le week-end et les jours fériés
    for day in week_schedule:
        day_date = day.split(" ")[1]  # Extraire la date
        for vacation in vacations:
            # Exclusion de la vacation CDP le week-end et jours fériés
            if vacation == 'CDP' and ("Sam" in day or "Dim" in day or day_date in holidays):
                # Ne pas assigner la vacation CDP le week-end et jours fériés
                model.Add(sum(planning[(agent['name'], day, 'CDP')] for agent in agents) == 0)
            else:
                # Somme des agents assignés à une vacation spécifique pour un jour donné doit être égale à 1
                model.Add(sum(planning[(agent['name'], day, vacation)] for agent in agents) == 1)
        
    # Après une vacation de nuit, pas de vacation de jour ou CDP le lendemain
    for agent in agents:
        agent_name = agent['name']
        for day_idx, day in enumerate(week_schedule[:-1]):  # On ne prend pas en compte le dernier jour
            next_day = week_schedule[day_idx + 1]
            
            # Variables boolèennes pour les vacations
            nuit_var = planning[(agent_name, day, 'Nuit')]
            jour_var = planning[(agent_name, next_day, 'Jour')]
            cdp_var = planning[(agent_name, next_day, 'CDP')]
            
            # Si l'agent travaille la nuit, il ne peut pas travailler une vacation de jour ou CDP le lendemain
            model.Add(jour_var == 0).OnlyEnforceIf(nuit_var)
            model.Add(cdp_var == 0).OnlyEnforceIf(nuit_var)
    
    ########################################################
    # Contrainte d'équilibre : tous les agents doivent avoir un volume horaire similaire
    total_hours = {}
    for agent in agents:
        agent_name = agent['name']
        total_hours[agent_name] = sum(
            planning[(agent_name, day, 'Jour')] * jour_duration +
            planning[(agent_name, day, 'Nuit')] * nuit_duration +
            planning[(agent_name, day, 'CDP')] * cdp_duration
            for day in week_schedule
        )
        
    # Imposer que la différence entre le minimum et le maximum d'heures travaillées par les agents soit limitée
    min_hours = model.NewIntVar(0, 10000, 'min_hours')  # Limite inférieure - Ajuster les bornes (*10) si nécessaire
    max_hours = model.NewIntVar(0, 10000, 'max_hours')  # Limite supérieure - Ajuster les bornes (*10) si nécessaire
    
    # Contrainte pour équilibrer les heures travaillées entre agents
    for agent_name in total_hours:
        model.Add(min_hours <= total_hours[agent_name])
        model.Add(total_hours[agent_name] <= max_hours)
        
    # Contraindre la différence entre max_hours et min_hours pour un équilibre global
    model.Add(max_hours - min_hours <= 240)  # Ajuster la flexibilité si nécessaire (*10)
    ########################################################
    
    ########################################################
    # Limitation du nombre de Nuit à 3 par semaine et gestion des vacations Jour et CDP
    weeks = split_into_weeks(week_schedule) # Diviser week_schedule en semaines
    
    for agent in agents:
        agent_name = agent["name"]
        
        for week in weeks:
            # Limiter le nombre de vacation Nuit à 3 par semaine (du lundi au dimanche)
            model.Add(sum(planning[(agent_name, day, 'Nuit')] for day in week) <= 3)
            
            # Calculer le total d'heures pour Jour et CDP par semaine
            total_heures = sum(
                planning[(agent_name, day, 'Jour')] * jour_duration +
                planning[(agent_name, day, 'CDP')] * cdp_duration
                for day in week
            )
            
            # Limiter à 36 heures par semaine
            model.Add(total_heures <= 360)  # 36 heures * 10
    ########################################################
            
    # Un agent ne travaille pas quand il est indisponible
    # Une indisponibilité est une journée où l'agent ne peut pas avoir de vacation quelle qu'elle soit.
    for agent in agents:
        agent_name = agent['name']
        
        if "unavailable" in agent:
            # Récupérer les jours d'indisponibilité de l'agent
            unavailable_days = agent['unavailable']
            
            # Parcourir chaque jour d'indisponibilité
            for unavailable_date in unavailable_days:
                # Extraire la portion date du jour
                unavailable_day = datetime.strptime(unavailable_date, '%d-%m-%Y').strftime("%d-%m")
                
                # Interdire toutes les vacations pour l'agent ce jour
                for day in week_schedule:
                    if unavailable_day in day:  # Vérifie si le jour correspond à une indisponibilité
                        for vacation in vacations:
                            model.Add(planning[(agent_name, day, vacation)] == 0)
                            
    ########################################################
    # Congés
    ########################################################
    date_format_full = "%d-%m-%Y"
    
    for agent in agents:
        agent_name = agent['name']
        
        # Récupérer les informations de congés s'il y en a
        vacation = agent.get('vacation')
        if vacation and isinstance(vacation, dict) and 'start' in vacation and 'end' in vacation:
            vacation_start = datetime.strptime(vacation['start'], date_format_full)
            vacation_end = datetime.strptime(vacation['end'], date_format_full)
            
            for day_str in week_schedule:
                # Extrait le jour et le mois et compléter avec l'année de vacation_start
                day_part = day_str.split(" ")[1] # Extrait la date au format %d-%m
                # Identifier le format et convertir le jour en objet datetime
                try:
                    day_date = datetime.strptime(f"{day_part}-{vacation_start.year}", date_format_full)
                except ValueError:
                    continue    # Ignorer la dates mal formées
                
                # Si le jour est un jour de congé, interdire toutes les vacations
                if vacation_start <= day_date <= vacation_end:
                    for vacation in vacations:
                        model.Add(planning[(agent_name, day_str, vacation)] == 0)
                        
                    # Calcul des heures pour les jours de congés (7 heures du lundi au samedi)
                    if day_date.weekday() < 6:   # lundi (0) à samedi (5)
                        total_hours[agent_name] += 70   # 7 heures * 10
                        # model.Add(total_hours[agent_name])
            
            # Si le congé commence un lundi, ajoutez l'indisponibilité du week-end précédent
            if vacation_start.weekday() == 0:  # lundi (0)
                previous_saturday = vacation_start - timedelta(days=2)
                previous_sunday = vacation_start - timedelta(days=1)
                
                for weekend_day in [previous_saturday, previous_sunday]:
                    weekend_str = weekend_day.strftime("%a %d-%m").capitalize()
                    
                    # Vérifie si le jour est dans la semaine de planification
                    if weekend_str in week_schedule:
                        for vacation in vacations:
                            model.Add(planning[(agent_name, weekend_str, vacation)] == 0)
            
    ########################################################
    # Limitation à 3 vacations de Jour par semaine
    # Convertir week_schedule en objet datetime pour faciliter le regroupement par semaine
    week_days = [(day, datetime.strptime(day.split(" ")[1], "%d-%m")) for day in week_schedule]
    weeks = defaultdict(list)
    
    # Regrouper les jours par semaine
    for day_str, day_date in week_days:
        # `isocalendar()` renvoie un tuple (année, semaine, jour) ce qui permet de regrouper par semaine
        # Utiliser une clé lisible en chaîne de caractères pour le regroupement (année-semaine)
        week_number = day_date.isocalendar()[:2]
        weeks[week_number].append(day_str)
        
    # Limiter à 3 vacations de Jour par semaine
    for agent in agents:
        agent_name = agent['name']
        for week, days in weeks.items():
            # Limiter les vacations "Jour" à 3 par semaine pour cet agent
            model.Add(sum(planning[(agent_name, day, 'Jour')] for day in days) <= 3)
    ########################################################
    
    # #! A retravailler sur le calcul des heures et sur la durée
    # # Un agent ne peut pas travailler plus de 48 heures par semaine
    # for agent in agents:
    #     agent_name = agent['name']
        
    #     # Calculer le total des heures travaillées sur la période définie
    #     total_hours = sum(
    #         planning[(agent_name, day, 'Jour')] * jour_duration +
    #         planning[(agent_name, day, 'Nuit')] * nuit_duration +
    #         planning[(agent_name, day, 'CDP')] * cdp_duration
    #         for day in week_schedule
    #     )
        
    #     # Limiter le total des heures à 48 heures par semaine proportionnellement au nombre de jours
    #     # Si la semaine est plus courte, ajuster le total des heures en conséquence
    #     total_days = len(week_schedule)
    #     max_hours = int((480 / 7) * total_days)  # Limite proportionnelle au nombre de jours
        
    #     model.Add(total_hours <= max_hours)
    # #! ########################################################
    
    # # Interdire les vacations les jours où l'agent est indisponible
    # for agent in agents:
    #     agent_name = agent['name']
    #     if "unavailable" in agent:
    #         for unavailable_date in agent['unavailable']:
    #             # Convertir la date indisponible en jour de la semaine
    #             unavailable_day = datetime.strptime(unavailable_date, '%Y-%m-%d').strftime("%A")
    #             if unavailable_day in week_schedule:
    #                 for vacation in vacations:
    #                     model.Add(planning[(agent_name, unavailable_day, vacation)] == 0)
                        
        
    ########################################################
    # Objectifs
    ########################################################
    
    # Maximiser les vacations préférées avec un poids supplémentaire
    objective_preferred_vacations = cp_model.LinearExpr.Sum(
        list(
            planning[(agent['name'], day, vacation)] * 100  # Poids plus élévé pour les vacations préférées
            for agent in agents
            for day in week_schedule
            for vacation in vacations
            if vacation in agent['preferences']['preferred']
        )
    )
    
    # Ajouter un poids normal pour les autres vacations
    objective_other_vacations = cp_model.LinearExpr.Sum(
        list(
            planning[(agent['name'], day, vacation)]
            for agent in agents
            for day in week_schedule
            for vacation in vacations
            if vacation not in agent['preferences']['preferred']
        )
    )
    
    # Pénaliser les vacations non désirées (évitées)
    penalized_vacations = cp_model.LinearExpr.Sum(
        list(
            planning[(agent['name'], day, vacation)] * -50  # Pénalité pour les vacations non désirées
            for agent in agents
            for day in week_schedule
            for vacation in vacations
            if vacation in agent['preferences']['avoid']
        )
    )
    
    # Maximiser l'objectif global, avec une préférence marquée pour les vacations préférées
    model.Maximize(objective_preferred_vacations + objective_other_vacations + penalized_vacations)
        
    # Solver
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60 # Limite de temps de résolution
    status = solver.Solve(model)
    
    # Résultats
    # Nous acceptons les solutions optimales et réalisables
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        result = {}
        for agent in agents:
            agent_name = agent['name']
            result[agent_name] = []
            for day in week_schedule:
                for vacation in vacations:
                    if solver.Value(planning[(agent_name, day, vacation)]):
                        result[agent_name].append((day, vacation))
        return result
    else:
        return "No solution found."


if __name__ == '__main__':
    app.run(debug=True)
