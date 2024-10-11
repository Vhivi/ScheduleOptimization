from flask import Flask, jsonify, request
import json
from flask_cors import CORS
from ortools.sat.python import cp_model
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

@app.route('/config')
# Charger le fichier de configuration
def load_config():
    with open('config.json', 'r') as config_file:
        return json.load(config_file)

config = load_config()

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
    # Convertir les chaines en objets datetime
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')  # Format date / ISO 8601
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')  # Format date / ISO 8601
    
    # Calculer les jours entre la date de début et la date de fin
    delta = end_date - start_date
    week_schedule = [(start_date + timedelta(days=i)).strftime("%A") for i in range(delta.days + 1)]
    return week_schedule


def generate_planning(agents, vacations, week_schedule):
    model = cp_model.CpModel()
    
    jour_duration = config['vacation_durations']['Jour']
    nuit_duration = config['vacation_durations']['Nuit']
    cdp_duration = config['vacation_durations']['CDP']
    
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
        
    # Chaque vacation doit être assignée à un agent chaque jour
    for day in week_schedule:
        for vacation in vacations:
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
    
    #! A retravailler sur le calcul des heures et sur la durée
    # Un agent ne peut pas travailler plus de 48 heures par semaine
    for agent in agents:
        agent_name = agent['name']
        total_hours = sum(planning[(agent_name, day, 'Jour')] * 12 + planning[(agent_name, day, 'Nuit')] * 12 for day in week_schedule)
        model.Add(total_hours <= 48)    # Limite à 48 heures par semaine
    #! ########################################################
    
    # Indisponibilité ou congés
    for agent in agents:
        agent_name = agent['name']
        if "unavailable" in agent:
            for day in agent['unavailable']:
                for vacation in vacations:
                    model.Add(planning[(agent_name, day, vacation)] == 0)
        
    # Respect des préférences des agents
    for agent in agents:
        agent_name = agent['name']
        preferences = agent['preferences']
        for day in week_schedule:
            for vacation in vacations:
                if vacation in preferences['preferred']:
                    # Favoriser les vacations préférées
                    model.Add(planning[(agent_name, day, vacation)] == 1)
                if vacation in preferences['avoid']:
                    # Éviter les vacations non désirées
                    model.Add(planning[(agent_name, day, vacation)] == 0)
                    
    # Contrainte d'équilibre : tous les agents doivent avoir un nombre similaire de vacations
    total_vacations = len(week_schedule) * len(vacations) // len(agents)
    
    for agent in agents:
        agent_name = agent['name']
        
        # Chaque agent doit travailler entre [total_vacations - 1] et [total_vacations + 1] vacations
        model.Add(sum(planning[(agent_name, day, vacation['name'] if isinstance(vacation, dict) else vacation)]
                    for day in week_schedule for vacation in vacations) >= total_vacations - 1)
        model.Add(sum(planning[(agent_name, day, vacation['name'] if isinstance(vacation, dict) else vacation)]
                    for day in week_schedule for vacation in vacations) <= total_vacations + 1)
                    
    ########################################################
    # Objectifs
    ########################################################
    
    # Maximiser les vacations préférées
    objective = cp_model.LinearExpr.Sum(
        list(
            planning[(agent['name'], day, vacation)]
            for agent in agents
            for day in week_schedule
            for vacation in vacations
            if vacation in agent['preferences']['preferred']
        )
    )
    model.Maximize(objective)
    
    # Solver
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    # Résultats
    if status == cp_model.OPTIMAL:
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
