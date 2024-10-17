from flask import Flask, jsonify, request
import json
from flask_cors import CORS
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
import locale

app = Flask(__name__)
CORS(app)

@app.route('/config')
# Charger le fichier de configuration
def load_config():
    with open('config.json', 'r') as config_file:
        return json.load(config_file)

config = load_config()
weekend_days = ["Samedi", "Dimanche"]

@app.route('/')
def home():
    return "Hello, Flask is up and running!"

@app.route('/generate-planning', methods=['POST'])
def generate_planning_route():
    # Récupération des données à partir du fichier JSON
    agents = config['agents']
    vacations = config['vacations']
    vacation_durations = config['vacation_durations']
    
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
        "week_schedule": week_schedule
    })
    
def get_week_schedule(start_date_str, end_date_str):
    # Configuer le local pour utiliser les jours de la semaine en français
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
    # Convertir les chaines en objets datetime
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')  # Format date / ISO 8601
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')  # Format date / ISO 8601
    
    # Calculer les jours entre la date de début et la date de fin
    delta = end_date - start_date
    week_schedule = [(start_date + timedelta(days=i)).strftime("%A").capitalize() for i in range(delta.days + 1)]
    return week_schedule


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
        
    # Chaque vacation doit être assignée à un agent chaque jour, sauf CDP le week-end
    for day in week_schedule:
        for vacation in vacations:
            # Exclusion de la vacation CDP le week-end
            if vacation == 'CDP' and day in weekend_days:
                # Ne pas assigner la vacation CDP le week-end
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
        
    # Imposer que la différence netre le minimum et le maximum d'heures travaillées par les agents soit limitée
    min_hours = model.NewIntVar(0, 10000, 'min_hours')  # Limite inférieure - Ajuster les bornes (*10) si nécessaire
    max_hours = model.NewIntVar(0, 10000, 'max_hours')  # Limite supérieure - Ajuster les bornes (*10) si nécessaire
    
    # Contrainte pour équilibrer les heures travaillées entre agents
    for agent_name in total_hours:
        model.Add(min_hours <= total_hours[agent_name])
        model.Add(total_hours[agent_name] <= max_hours)
        
    # Contraindre la différence entre max_hours et min_hours pour un équilibre global
    model.Add(max_hours - min_hours <= 240)  # Ajuster la flexibilité si nécessaire (*10)
    ########################################################
    
    # #! A retravailler sur le calcul des heures et sur la durée
    # # # Un agent ne peut pas travailler plus de 48 heures par semaine
    # # for agent in agents:
    # #     agent_name = agent['name']
    # #     total_hours = sum(planning[(agent_name, day, 'Jour')] * jour_duration + planning[(agent_name, day, 'Nuit')] * nuit_duration + planning[(agent_name, day, 'CDP')] * cdp_duration for day in week_schedule)
    # #     model.Add(total_hours <= 480)    # Limite à 48 heures par semaine (480 au lieu de 48)
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
            planning[(agent['name'], day, vacation)] * 10  # Poids plus élévé pour les vacations préférées
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
    
    # Maximiser l'objectif global, avec une préférence marquée pour les vacations préférées
    model.Maximize(objective_preferred_vacations + objective_other_vacations)
        
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
