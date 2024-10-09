from flask import Flask
import json
from flask_cors import CORS
from ortools.sat.python import cp_model

app = Flask(__name__)
CORS(app)

with open('config.json') as config_file:
    config = json.load(config_file)
    
@app.route('/config')
def get_config():
    return config

@app.route('/')
def home():
    return "Hello, Flask is up and running!"

def generate_planning(agents, vacations, week_schedule):
    model = cp_model.CpModel()
    
    # Variables : une variable par agent/vacation/jour
    planning = {}
    for agent in agents:
        for day in week_schedule:
            for vacation in vacations:
                planning[(agent, day, vacation)] = model.NewBoolVar(f'planning_{agent}_{day}_{vacation}')
                
    # Contraintes : chaque agent peut travailler au plus une vacation par jour
    for agent in agents:
        for day in week_schedule:
            model.Add(sum(planning[(agent, day, vacation)] for vacation in vacations) <= 1)
            
    # Contraintes : au moins une vacation par agent pour la semaine
    for agent in agents:
        model.Add(sum(planning[(agent, day, vacation)] for day in week_schedule for vacation in vacations) >= 1)
        
    # Solver
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    # Résultats
    if status == cp_model.OPTIMAL:
        result = {}
        for agent in agents:
            result[agent] = []
            for day in week_schedule:
                for vacation in vacations:
                    if solver.Value(planning[(agent, day, vacation)]):
                        result[agent].append((day, vacation))
        return result
    else:
        return "No solution found."


if __name__ == '__main__':
    app.run(debug=True)
