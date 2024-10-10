from flask import Flask, jsonify
import json
from flask_cors import CORS
from ortools.sat.python import cp_model

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
    week_schedule = config['week_schedule']
    
    # Appel de la fonction de génération de planning
    result = generate_planning(agents, vacations, week_schedule)
    return jsonify(result)


def generate_planning(agents, vacations, week_schedule):
    model = cp_model.CpModel()
    
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
        
    # 12 heures de repos minimum entre deux vacations
    for agent in agents:
        agent_name = agent['name']
        for day_idx, day in enumerate(week_schedule[:-1]):  # On ne prend pas en compte le dernier jour
            next_day = week_schedule[day_idx + 1]
            model.AddBoolOr([planning[(agent_name, day, 'Nuit')].Not(), planning[(agent_name, next_day, 'Jour')].Not()])
            
    # Un agent ne peut pas travailler plus de 48 heures par semaine
    for agent in agents:
        agent_name = agent['name']
        total_hours = sum(planning[(agent_name, day, 'Jour')] * 12 + planning[(agent_name, day, 'Nuit')] * 12 for day in week_schedule)
        model.Add(total_hours <= 48)    # Limite à 48 heures par semaine
        
    # Respect des préférences des agents
    for agent in agents:
        agent_name = agent['name']
        for day in week_schedule:
            for vacation in vacations:
                if vacation in agents[agent_name]['preferences']['preferred']:
                    # Favoriser les vacations préférées
                    model.Add(planning[(agent_name, day, vacation)] == 1)
                if vacation in agents[agent_name]['preferences']['avoid']:
                    # Éviter les vacations non désirées
                    model.Add(planning[(agent_name, day, vacation)] == 0)
                    
    ########################################################
    # Objectifs
    ########################################################
    
    # Maximiser les vacations préférées
    objective = cp_model.LinearExpr.Sum(
        planning[(agent['name'], day, vacation)] for agent in agents
        for day in week_schedule for vacation in vacations
        if vacation in agents[agent['name']]['preferences']['preferred']
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
