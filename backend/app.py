import json
import locale
import os
from collections import defaultdict
from datetime import datetime, timedelta

from flask import Flask, jsonify, request
from flask_cors import CORS
from ortools.sat.python import cp_model

app = Flask(__name__)
CORS(app)


@app.route("/config")
# Loading the configuration file
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, "r") as config_file:
        return json.load(config_file)


config = load_config()
weekend_days = ["Sam", "Dim"]  # Shortened weekend days
holidays = config[
    "holidays"
]  # Public holidays to be updated each year, in particular for Easter Monday


@app.route("/")
def home():
    return "Hello, Flask is up and running!"


@app.route("/generate-planning", methods=["POST"])
def generate_planning_route():
    # Retrieving data from the JSON file
    agents = config["agents"]
    vacations = config["vacations"]
    vacation_durations = config["vacation_durations"]
    holidays = config["holidays"]
    unavailable = {}
    dayOff = {}
    training = {}

    # Retrieve agent training days and store them in a dictionary {agent: [days]}.
    for agent in agents:
        if "training" in agent:
            training[agent["name"]] = agent["training"]

    # Retrieve agent unavailability days and store them in a dictionary {agent: [days]}.
    for agent in agents:
        if "unavailable" in agent:
            unavailable[agent["name"]] = agent["unavailable"]

    # Recovering employees' holiday days
    for agent in agents:
        if "vacation" in agent:
            vacation = agent["vacation"]
            if isinstance(vacation, dict) and "start" in vacation and "end" in vacation:
                vacation_start = vacation["start"]
                vacation_end = vacation["end"]

                # Store holiday days in a dictionary {agent: [start, end]}
                dayOff[agent["name"]] = [vacation_start, vacation_end]

    # Retrieve start and end dates
    # Check whether the dates are present in the query
    if "start_date" not in request.json or "end_date" not in request.json:
        return jsonify({"error": "Missing start_date or end_date"}), 400
    # Check that the dates are valid
    if not is_valid_date(request.json["start_date"]) or not is_valid_date(
        request.json["end_date"]
    ):
        return jsonify({"error": "Invalid date format"}), 400

    start_date = request.json["start_date"]
    end_date = request.json["end_date"]
    
    # Retrieve initial shifts, if supplied otherwise default to an empty dictionary
    initial_shifts = request.json.get("initial_shifts", {})

    # Validate initial shifts
    valid_agents = [agent["name"] for agent in agents]
    valid_vacations = vacations
    for agent_name, shifts in initial_shifts.items():
        if agent_name not in valid_agents:
            return jsonify({"error": f"Invalid agent: {agent_name}"}), 400
        for _, vacation in shifts:
            if vacation not in valid_vacations:
                return jsonify({"error": f"Invalid vacation: {vacation}"}), 400

    # Calculate the list of days from dates
    week_schedule = get_week_schedule(start_date, end_date)
    previous_week_schedule = get_previous_week_schedule(start_date)

    # Calling up the schedule generation function
    result = generate_planning(agents, vacations, week_schedule, dayOff, previous_week_schedule, initial_shifts)
    # If the result is a dict with an info key, return a 400 error.
    if "info" in result:
        return jsonify(result), 400
    else:   # Otherwise, return the result
        return jsonify(
            {
                "planning": result,
                "vacation_durations": vacation_durations,
                "week_schedule": week_schedule,
                "holidays": holidays,
                "unavailable": unavailable,
                "dayOff": dayOff,
                "training": training,
            }
        )


def is_valid_date(date_str):
    """
    Check if the given string is a valid date in the format YYYY-MM-DD
    or if the given string is valid date even if it has the right format.

    Args:
        date_str (str): The date string to validate.

    Returns:
        bool: True if the date string is valid, False otherwise.
    """

    # Check if the date string is not None and is a string
    # If not, return False
    # This test is necessary to avoid TypeError when calling the strptime method
    if date_str is None or not isinstance(date_str, str):
        return False

    # Check if the date string has the right format
    # If not, return False
    # This test is necessary to avoid ValueError when calling the strptime method
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


@app.route("/previous-week-schedule", methods=["POST"])
def compute_previous_week_schedule():
    try:
        # Check if the start_date is present in the query
        if "start_date" not in request.json:
            return jsonify({"error": "Missing start_date"}), 400
        # Check that the date is valid
        if not is_valid_date(request.json["start_date"]):
            return jsonify({"error": "Invalid date format"}), 400

        start_date = request.json["start_date"]
        previous_week_schedule = get_previous_week_schedule(start_date)
        
        agents = config["agents"]

        return jsonify({
            "previous_week_schedule": previous_week_schedule,
            "agents": agents
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


def get_previous_week_schedule(start_date_str):
    # Configure the locale to use the days of the week in French
    locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
    
    try:
        # Convert the string into a datetime object
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")  # Format date / ISO 8601
    except ValueError as e:
        raise ValueError("Invalid date format. Use YYYY-MM-DD.") from e
    
    previous_week_start = start_date - timedelta(days=7)

    # Calculate the days of the previous week
    return [
        (previous_week_start + timedelta(days=i)).strftime("%a %d-%m").capitalize()
        for i in range(7)
    ] # Format: Shortened day + Date (e.g. Lun 25-12)

def get_week_schedule(start_date_str, end_date_str):
    # Configure the locale to use the days of the week in French
    locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
    # Convert strings into datetime objects
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")  # Format date / ISO 8601
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")  # Format date / ISO 8601

    # Calculate the days between the start date and the end date
    delta = end_date - start_date
    return [
        (start_date + timedelta(days=i)).strftime("%a %d-%m").capitalize()
        for i in range(delta.days + 1)
    ]  # Format : Shortened day + Date (e.g. Lun 25-12)


def split_into_weeks(week_schedule):
    # Divide the list of days into calendar weeks (Monday to Sunday)
    weeks = []
    current_week = []

    for day in week_schedule:
        # Add the day to the current week
        current_week.append(day)

        # If the day is a Sunday or the last day of the schedule, end the week
        day_name = day.split(" ")[0]  # Extract the name of the day (e.g. Lun.)
        if day_name == "Dim." or day == week_schedule[-1]:  # Sunday or last day
            weeks.append(current_week)
            current_week = []

    return weeks


def split_by_month_or_period(week_schedule):
    # Divides week_schedule into monthly or single periods according to duration
    periods = []
    current_period = []
    previous_month = None

    for day in week_schedule:
        # Extract month (format: Lun 25-12)
        current_month = day.split(" ")[1].split("-")[1]  # Extract the month (e.g. 12)

        # If the month changes, start a new period
        if previous_month and current_month != previous_month:
            periods.append(current_period)
            current_period = []
        current_period.append(day)
        previous_month = current_month

    # Add the last period
    if current_period:
        periods.append(current_period)

    return periods


def is_vacation_day(agent_name, day, dayOff):
    """Checks whether the day is a day off for this agent."""
    if agent_name in dayOff:
        vacation_start, vacation_end = dayOff[agent_name]
        # Convert holiday dates and the day into datetime objects for comparison
        vacation_start_date = datetime.strptime(vacation_start, "%d-%m-%Y")
        vacation_end_date = datetime.strptime(vacation_end, "%d-%m-%Y")
        day_part = day.split(" ")[1]  # Extract the date (e.g. 25-12)
        day_date = datetime.strptime(
            f"{day_part}-{vacation_start_date.year}", "%d-%m-%Y"
        )

        # Check if the day is between the holiday start and end dates
        return vacation_start_date <= day_date <= vacation_end_date and not is_weekend(
            day
        )
    return False


def is_weekend(day):
    """Determines whether a day is Saturday or Sunday."""
    day_name = day.split(" ")[0]
    return day_name in ["Sam.", "Dim."]


def generate_planning(agents, vacations, week_schedule, dayOff, previous_week_schedule, initial_shifts):
    model = cp_model.CpModel()

    weeks_split = split_into_weeks(week_schedule)  # Divide week_schedule into weeks

    # Adjust shift durations by multiplying by 10 to eliminate decimals
    jour_duration = int(config["vacation_durations"]["Jour"] * 10)
    nuit_duration = int(config["vacation_durations"]["Nuit"] * 10)
    cdp_duration = int(config["vacation_durations"]["CDP"] * 10)
    conge_duration = int(config["vacation_durations"]["Conge"] * 10)

    ########################################################
    # Variables
    ########################################################

    # One variable per agent/shift/day
    planning = {}
    for agent in agents:
        agent_name = agent["name"]  # Use agent name as key
        for day in set(week_schedule + previous_week_schedule):  # Include both week_schedule and previous_week_schedule
            for vacation in vacations:
                planning[(agent_name, day, vacation)] = model.NewBoolVar(
                    f"planning_{agent_name}_{day}_{vacation}"
                )

    ########################################################
    # Hard Constraints
    ########################################################
    # (Put all the unavoidable constraints here)
    
    # Only apply initial shifts from the previous week
    for agent_name, shifts in initial_shifts.items():
        for day, vacation in shifts:
            if agent_name in [agent["name"] for agent in agents] and vacation in vacations and day in previous_week_schedule:
                model.Add(planning[(agent_name, day, vacation)] == 1)

    # Each agent may work a maximum of one shift per day
    for agent in agents:
        agent_name = agent["name"]
        for day in week_schedule:
            model.Add(
                sum(planning[(agent_name, day, vacation)] for vacation in vacations)
                <= 1
            )

    # At least one shift per agent per week
    for agent in agents:
        agent_name = agent["name"]
        model.Add(
            sum(
                planning[(agent_name, day, vacation)]
                for day in week_schedule
                for vacation in vacations
            )
            >= 1
        )

    # Each shift must be assigned to an agent each day, except for the CDP shift at weekends and on public holidays.
    for day in week_schedule:
        day_date = day.split(" ")[1]  # Extract date
        for vacation in vacations:
            # Exclusion from the CDP shift at weekends and public holidays
            if vacation == "CDP" and (
                "Sam" in day or "Dim" in day or day_date in holidays
            ):
                # Do not assign the CDP shift at weekends or on public holidays
                model.Add(
                    sum(planning[(agent["name"], day, "CDP")] for agent in agents) == 0
                )
            else:
                # Sum of agents assigned to a specific shift on a given day must be equal to 1
                model.Add(
                    sum(planning[(agent["name"], day, vacation)] for agent in agents)
                    == 1
                )

    # After a night shift, prohibit the day shift or CDP the following day
    # to avoid the agent working 24 hours in a row
    for agent in agents:
        agent_name = agent["name"]
        for day_idx, day in enumerate(
            week_schedule[:-1]
        ):  # The last day is not taken into account
            next_day = week_schedule[day_idx + 1]

            # Boolean variables for shifts
            nuit_var = planning[(agent_name, day, "Nuit")]
            jour_var = planning[(agent_name, next_day, "Jour")]
            cdp_var = planning[(agent_name, next_day, "CDP")]

            # If the agent works at night, he/she cannot work a day shift or CDP the following day.
            model.Add(jour_var == 0).OnlyEnforceIf(nuit_var)
            model.Add(cdp_var == 0).OnlyEnforceIf(nuit_var)

    ########################################################
    # Limit the number of CDPs to 2 per week
    # Personal choice to try and find a balance between shifts
    for agent in agents:
        agent_name = agent["name"]

        for week in weeks_split:
            # Limit the number of CDP shifts to 2 per week (Monday to Sunday)
            model.Add(sum(planning[(agent_name, day, "CDP")] for day in week) <= 2)
    ########################################################

    ########################################################
    # An agent does not work when he is unavailable
    # Unavailability is a day on which the agent is unable to work any kind of shift.
    for agent in agents:
        agent_name = agent["name"]

        if "unavailable" in agent:
            # Retrieve the agent's days of unavailability
            unavailable_days = agent["unavailable"]

            # Browse each day of unavailability
            for unavailable_date in unavailable_days:
                # Extract today's date
                unavailable_day = datetime.strptime(
                    unavailable_date, "%d-%m-%Y"
                ).strftime("%d-%m")

                # Prohibit the agent from working any shifts on this day
                for day in week_schedule:
                    if (
                        unavailable_day in day
                    ):  # Checks whether the day corresponds to unavailability
                        for vacation in vacations:
                            model.Add(planning[(agent_name, day, vacation)] == 0)
    ########################################################

    ########################################################
    # An agent does not work while on training
    # A training session is a day on which the agent is not allowed to do any work.
    for agent in agents:
        agent_name = agent["name"]

        if "training" in agent:
            # Retrieve the agent's training days
            training_days = agent["training"]

            # Browse each training day
            for training_date in training_days:
                # Extract today's date
                training_day = datetime.strptime(training_date, "%d-%m-%Y").strftime(
                    "%d-%m"
                )

                # Forbid the agent from working any shifts on this day
                for day in week_schedule:
                    if (
                        training_day in day
                    ):  # Checks whether the day corresponds to training
                        for vacation in vacations:
                            model.Add(planning[(agent_name, day, vacation)] == 0)
    ########################################################

    ########################################################
    # Staff leave
    date_format_full = "%d-%m-%Y"
    total_hours = {}

    for agent in agents:
        agent_name = agent["name"]
        total_hours[agent_name] = 0  # Initialise the total number of hours for the agent

        # Retrieve leave information if available
        vacation = agent.get("vacation")
        if (
            vacation
            and isinstance(vacation, dict)
            and "start" in vacation
            and "end" in vacation
        ):
            vacation_start = datetime.strptime(vacation["start"], date_format_full)
            vacation_end = datetime.strptime(vacation["end"], date_format_full)

            for day_str in week_schedule:
                # Extract the day and month and complete with the year of vacation_start
                day_part = day_str.split(" ")[1]  # Extracts the date in %d-%m format
                # Identify the format and convert the day into a datetime object
                try:
                    day_date = datetime.strptime(
                        f"{day_part}-{vacation_start.year}", date_format_full
                    )
                except ValueError:
                    continue  # Ignore malformed dates

                # If the day is a leave, prohibit all shifts
                if vacation_start <= day_date <= vacation_end:
                    for vacation in vacations:
                        model.Add(planning[(agent_name, day_str, vacation)] == 0)

                    # Calculating hours for days off (7 hours from Monday to Saturday)
                    if day_date.weekday() < 6:  # Monday (0) to Saturday (5)
                        total_hours[agent_name] += 70  # 7 hours * 10
                        # model.Add(total_hours[agent_name])

            # If the leave starts on a Monday, add the unavailability from the previous weekend
            if vacation_start.weekday() == 0:  # Monday (0)
                previous_saturday = vacation_start - timedelta(days=2)
                previous_sunday = vacation_start - timedelta(days=1)

                for weekend_day in [previous_saturday, previous_sunday]:
                    weekend_str = weekend_day.strftime("%a %d-%m").capitalize()

                    # Checks if the day is in the planning week
                    if weekend_str in week_schedule:
                        for vacation in vacations:
                            model.Add(
                                planning[(agent_name, weekend_str, vacation)] == 0
                            )
    ########################################################

    ########################################################
    # Limitation à 3 vacations de Jour par semaine
    # Convertir week_schedule en objet datetime pour faciliter le regroupement par semaine
    week_days = [
        (day, datetime.strptime(day.split(" ")[1], "%d-%m")) for day in week_schedule
    ]
    weeks_dict = defaultdict(list)

    # Regrouper les jours par semaine
    for day_str, day_date in week_days:
        # `isocalendar()` renvoie un tuple (année, semaine, jour) ce qui permet de regrouper par semaine
        # Utiliser une clé lisible en chaîne de caractères pour le regroupement (année-semaine)
        week_number = day_date.isocalendar()[:2]
        weeks_dict[week_number].append(day_str)

    # Limiter à 3 vacations de Jour par semaine
    for agent in agents:
        agent_name = agent["name"]
        for week, days in weeks_dict.items():
            # Limiter les vacations "Jour" à 3 par semaine pour cet agent
            model.Add(sum(planning[(agent_name, day, "Jour")] for day in days) <= 3)
    ########################################################

    ########################################################
    # Interdire une vacation de nuit avant une indisponibilité
    for agent in agents:
        agent_name = agent["name"]

        if "unavailable" in agent:
            # Récupérer les jours d'indisponibilité de l'agent
            unavailable_days = [
                datetime.strptime(date, "%d-%m-%Y").strftime("%d-%m")
                for date in agent["unavailable"]
            ]

            # Interdire la vacation de nuit la veille de l'indisponibilité
            for day_idx, day in enumerate(
                week_schedule[:-1]
            ):  # Ignorer le dernier jour
                next_day = week_schedule[day_idx + 1]

                # Vérifie si le jour suivant est une indisponibilité
                if any(
                    unavailable_day in next_day for unavailable_day in unavailable_days
                ):
                    model.Add(planning[(agent_name, day, "Nuit")] == 0)
    ########################################################

    ########################################################
    # Interdire une vacation de nuit avant une formation
    for agent in agents:
        agent_name = agent["name"]

        if "training" in agent:
            # Récupérer les jours de formation de l'agent
            training_days = [
                datetime.strptime(date, "%d-%m-%Y").strftime("%d-%m")
                for date in agent["training"]
            ]

            # Interdire la vacation de nuit la veille de la formation
            for day_idx, day in enumerate(
                week_schedule[:-1]
            ):  # Ignorer le dernier jour
                next_day = week_schedule[day_idx + 1]

                # Vérifie si le jour suivant est une formation
                if any(training_day in next_day for training_day in training_days):
                    model.Add(planning[(agent_name, day, "Nuit")] == 0)
    ########################################################

    ########################################################
    # Limiter les vacations avant et après une formation
    for agent in agents:
        agent_name = agent["name"]

        if "training" in agent:
            # Récupérer les jours de formation de l'agent
            training_days = [
                datetime.strptime(date, "%d-%m-%Y").strftime("%d-%m")
                for date in agent["training"]
            ]

            for day_idx, day in enumerate(week_schedule):
                if any(training_day in day for training_day in training_days):
                    # Vérifier le jour précédent (veille de la formation)
                    if day_idx > 0:
                        previous_day = week_schedule[day_idx - 1]

                        # Si une vacation est attribuée la veille, elle doit être CDP ou rien
                        for vacation in vacations:
                            if vacation != "CDP":
                                model.Add(
                                    planning[(agent_name, previous_day, vacation)] == 0
                                )

                    # Vérifier le jour suivant (lendemain de la formation)
                    if day_idx < len(week_schedule) - 1:
                        next_day = week_schedule[day_idx + 1]

                        # Si une vacation est attribuée le lendemain, elle doit être CDP, Nuit ou rien
                        allowed_vacations = ["CDP", "Nuit"]
                        for vacation in vacations:
                            if vacation not in allowed_vacations:
                                model.Add(
                                    planning[(agent_name, next_day, vacation)] == 0
                                )
    ########################################################

    ########################################################
    # Interdire une vacation pour une exclusion de vacation
    for agent in agents:
        agent_name = agent["name"]

        if "exclusion" in agent:
            # Récupérer les vacations à exclure
            exclusion_dates = agent["exclusion"]

            # Parcourir chaque date d'exclusion
            for exclusion_date in exclusion_dates:
                # Extraire la portion date de l'exclusion
                exclusion_day = datetime.strptime(exclusion_date, "%d-%m-%Y").strftime(
                    "%d-%m"
                )

                # Interdire toutes les vacations pour l'agent ce jour
                for day_str in week_schedule:
                    day_date = day_str.split(" ")[1]  # Extraire la date (dd-mm)

                    if (
                        exclusion_day == day_date
                    ):  # Vérifie si le jour correspond à une exclusion
                        for vacation in vacations:
                            model.Add(planning[(agent_name, day_str, vacation)] == 0)
    ########################################################

    ########################################################
    # Interdire la vacation nuit du lundi si l'agent à travailler le week-end
    for agent in agents:
        agent_name = agent["name"]

        for day_idx, day in enumerate(
            week_schedule[:-2]
        ):  # on parcourt jusqu'à l'avant-dernier jour
            # On vérifie si le jour est un samedi
            if "Sam" in day:
                sunday_idx = day_idx + 1
                monday_idx = day_idx + 2

                if sunday_idx < len(week_schedule) and monday_idx < len(week_schedule):
                    sunday = week_schedule[sunday_idx]
                    monday = week_schedule[monday_idx]

                    # Récupérer les variables de travail de nuit pour samedi et dimanche et auncune vacation le lundi
                    saturday_night = planning[(agent_name, day, "Nuit")]
                    sunday_night = planning[(agent_name, sunday, "Nuit")]

                    # Créer une variable booléenne pour forcer l'agent à ne pas travailler le lundi
                    model.Add(
                        planning[(agent_name, monday, "Nuit")] == 0
                    ).OnlyEnforceIf([saturday_night, sunday_night])
    ########################################################

    ########################################################
    # Appliquer les restrictions
    for agent in agents:
        agent_name = agent["name"]

        if "restriction" in agent:
            restricted_vacations = agent["restriction"]

            # Interdire ces vacations pour l'agent tous les jours du planning
            for day in week_schedule:
                for restricted_vacation in restricted_vacations:
                    model.Add(planning[(agent_name, day, restricted_vacation)] == 0)
    ########################################################

    ########################################################
    # Soft Constraints
    ########################################################
    # (Mettre ici toutes les contraintes [souples] qui influencent l'objectif global)

    ########################################################
    # Contrainte d'équilibre : tous les agents doivent avoir un volume horaire similaire
    total_hours = {}
    for agent in agents:
        agent_name = agent["name"]
        total_hours[agent_name] = sum(
            planning[(agent_name, day, "Jour")] * jour_duration
            + planning[(agent_name, day, "Nuit")] * nuit_duration
            + planning[(agent_name, day, "CDP")] * cdp_duration
            +
            # Ajout de la durée de congé pour chaque jour de congé détecté
            (
                conge_duration
                if is_vacation_day(agent_name, day, dayOff) and not is_weekend(day)
                else 0
            )
            for day in week_schedule
        )
        print(
            f"Congé pour {agent_name}: {sum((conge_duration if is_vacation_day(agent_name, day, dayOff) else 0) for day in week_schedule)}"
        )

    # Imposer que la différence entre le minimum et le maximum d'heures travaillées par les agents soit limitée
    min_hours = model.NewIntVar(
        0, 10000, "min_hours"
    )  # Limite inférieure - Ajuster les bornes (*10) si nécessaire
    max_hours = model.NewIntVar(
        0, 10000, "max_hours"
    )  # Limite supérieure - Ajuster les bornes (*10) si nécessaire

    # Contrainte pour équilibrer les heures travaillées entre agents
    for agent_name in total_hours:
        model.Add(min_hours <= total_hours[agent_name])
        model.Add(total_hours[agent_name] <= max_hours)

    # Contraindre la différence entre max_hours et min_hours pour un équilibre global
    model.Add(
        max_hours - min_hours <= 240
    )  # Ajuster la flexibilité si nécessaire (*10)
    ########################################################

    ########################################################
    # Contrainte d'équilibre par période

    # Diviser week_schedule en périodes mensuelles ou uniques
    periods = split_by_month_or_period(week_schedule)

    for period in periods:
        total_hours = {}
        for agent in agents:
            agent_name = agent["name"]
            # Calcul des heures totales par agent sur la période
            total_hours[agent_name] = cp_model.LinearExpr.Sum(
                list(
                    planning[(agent_name, day, "Jour")] * jour_duration
                    + planning[(agent_name, day, "Nuit")] * nuit_duration
                    + planning[(agent_name, day, "CDP")] * cdp_duration
                    for day in period
                )
            )

    # Définir min_hours et max_hours pour l'équilibrage
    min_hours = model.NewIntVar(
        0, 100000, "min_hours_period"
    )  # Limite inférieure - Ajuster les bornes (*10) si nécessaire
    max_hours = model.NewIntVar(
        0, 100000, "max_hours_period"
    )  # Limite supérieure - Ajuster les bornes (*10) si nécessaire

    # Ajouter des contraintes pour chaque agent
    for agent_name in total_hours:
        model.Add(min_hours <= total_hours[agent_name])
        model.Add(total_hours[agent_name] <= max_hours)

    # Limiter l'écart d'heure entre les agents
    max_difference = 240  # Ajuster la flexibilité si nécessaire (*10)
    model.Add(max_hours - min_hours <= max_difference)
    ########################################################

    ########################################################
    # Ajouter l'équilibrage des week-ends complets

    total_weekends = sum(
        1 for day in week_schedule if "Sam" in day
    )  # Nombre total de week-ends dans la période
    # Doublez la cible pour tenir compte de deux vacations (Jour et Nuit) par week-end
    target_weekends_per_agent = (total_weekends * 2) // len(
        agents
    )  # Nombre de week-ends idéal par agent

    # Initialiser les compteurs de week-ends travaillés pour chaque agent
    weekends_worked = {}
    for agent in agents:
        agent_name = agent["name"]
        weekends_worked[agent_name] = model.NewIntVar(
            0, total_weekends, f"weekends_worked_{agent_name}"
        )

        # Calculer le nombre de week-ends complets travaillés pour chaque agent
        weekend_count = []
        for day_idx, day in enumerate(week_schedule):
            if (
                "Sam" in day
                and day_idx + 1 < len(week_schedule)
                and "Dim" in week_schedule[day_idx + 1]
            ):
                saturday = day
                sunday = week_schedule[day_idx + 1]

                # Variables booléennes pour le travail le samedi et le dimanche
                saturday_work = model.NewBoolVar(
                    f"{agent_name}_works_saturday_{saturday}"
                )
                sunday_work = model.NewBoolVar(f"{agent_name}_works_sunday_{sunday}")

                # Ajouter les contraintes pour assigner ces variables
                model.Add(
                    planning[(agent_name, saturday, "Jour")]
                    + planning[(agent_name, saturday, "Nuit")]
                    > 0
                ).OnlyEnforceIf(saturday_work)
                model.Add(
                    planning[(agent_name, saturday, "Jour")]
                    + planning[(agent_name, saturday, "Nuit")]
                    == 0
                ).OnlyEnforceIf(saturday_work.Not())

                model.Add(
                    planning[(agent_name, sunday, "Jour")]
                    + planning[(agent_name, sunday, "Nuit")]
                    > 0
                ).OnlyEnforceIf(sunday_work)
                model.Add(
                    planning[(agent_name, sunday, "Jour")]
                    + planning[(agent_name, sunday, "Nuit")]
                    == 0
                ).OnlyEnforceIf(sunday_work.Not())

                # L'agent travaille un week-end complet si les deux jours sont travaillés
                works_weekend = model.NewBoolVar(
                    f"{agent_name}_works_weekend_{saturday}_{sunday}"
                )
                model.AddBoolAnd([saturday_work, sunday_work]).OnlyEnforceIf(
                    works_weekend
                )
                model.AddBoolOr([saturday_work.Not(), sunday_work.Not()]).OnlyEnforceIf(
                    works_weekend.Not()
                )

                # Ajouter works_weekend à la liste des week-ends travaillés
                weekend_count.append(works_weekend)

        # Assignation de la somme des week-ends travaillés
        model.Add(weekends_worked[agent_name] == sum(weekend_count))

    # Ajouter l'objectif pour équilibrer les week-ends travaillés
    min_weekends = model.NewIntVar(0, total_weekends, "min_weekends")
    max_weekends = model.NewIntVar(0, total_weekends, "max_weekends")
    for agent_name in weekends_worked:
        model.Add(min_weekends <= weekends_worked[agent_name])
        model.Add(weekends_worked[agent_name] <= max_weekends)

    # Minimiser l'écart entre le minimum et le maximum de week-ends travaillés par les agents
    model.Minimize(max_weekends - min_weekends)

    # Calcul de l'équilibrage des week-ends travaillés
    weekend_balancing_terms = []

    for agent in agents:
        agent_name = agent["name"]
        difference = model.NewIntVar(
            -2 * total_weekends, 2 * total_weekends, f"difference_weekends_{agent_name}"
        )
        squared_difference = model.NewIntVar(
            0, (total_weekends * 2) ** 2, f"squared_difference_weekends_{agent_name}"
        )

        # Calculer la différence entre les week-ends travaillés et le nombre de week-ends cible
        model.Add(difference == weekends_worked[agent_name] - target_weekends_per_agent)

        # Définir le carré de la différence
        model.AddMultiplicationEquality(squared_difference, [difference, difference])

        # Ajouter ce carré à l'objectif d'équilibrage des week-ends
        weekend_balancing_terms.append(squared_difference)

    # Équilibrage des week-ends travaillés
    weekend_balancing_objective = cp_model.LinearExpr.Sum(weekend_balancing_terms)
    ########################################################

    ########################################################
    # Mixed Constraints
    ########################################################
    # (Mettre ici toutes les contraintes qui combinent les contraintes dures et souples)
    # (Pensez à les retravailler pour dissocier les contraintes dures et souples)

    ########################################################
    # Limitation du nombre de Nuit à 3 par semaine et gestion des vacations Jour et CDP
    for agent in agents:
        agent_name = agent["name"]

        for week in weeks_split:
            # Limiter le nombre de vacation Nuit à 3 par semaine (du lundi au dimanche)
            model.Add(sum(planning[(agent_name, day, "Nuit")] for day in week) <= 3)

            # Calculer le total d'heures pour Jour et CDP par semaine
            total_heures = sum(
                planning[(agent_name, day, "Jour")] * jour_duration
                + planning[(agent_name, day, "CDP")] * cdp_duration
                for day in week
            )

            # Limiter à 36 heures par semaine
            model.Add(total_heures <= 360)  # 36 heures * 10
    ########################################################

    ########################################################
    # Fournir des week-ends complets
    # for agent in agents:
    #     agent_name = agent['name']

    #     for day_idx, day in enumerate(week_schedule):
    #         # Vérifier si le jour est un samedi
    #         if "Sam" in day:
    #             sunday_idx = day_idx + 1

    #             if sunday_idx < len(week_schedule) and "Dim" in week_schedule[sunday_idx]:
    #                 saturday = day
    #                 sunday = week_schedule[sunday_idx]

    #                 # Créer des variables booléennes pour savoir si l'agent travaille le samedi et le dimanche
    #                 saturday_jour = model.NewBoolVar(f'{agent_name}_work_saturday_jour_{saturday}')
    #                 saturday_nuit = model.NewBoolVar(f'{agent_name}_work_saturday_nuit_{saturday}')
    #                 sunday_jour = model.NewBoolVar(f'{agent_name}_work_sunday_jour_{sunday}')
    #                 sunday_nuit = model.NewBoolVar(f'{agent_name}_work_sunday_nuit_{sunday}')

    #                 # Assigner les variables en fonction de la planification
    #                 model.Add(planning[(agent_name, saturday, 'Jour')] == 1).OnlyEnforceIf(saturday_jour)
    #                 model.Add(planning[(agent_name, saturday, 'Jour')] == 0).OnlyEnforceIf(saturday_jour)
    #                 model.Add(planning[(agent_name, saturday, 'Nuit')] == 1).OnlyEnforceIf(saturday_nuit)
    #                 model.Add(planning[(agent_name, saturday, 'Nuit')] == 0).OnlyEnforceIf(saturday_nuit)

    #                 model.Add(planning[(agent_name, sunday, 'Jour')] == 1).OnlyEnforceIf(sunday_jour)
    #                 model.Add(planning[(agent_name, sunday, 'Jour')] == 0).OnlyEnforceIf(sunday_jour)
    #                 model.Add(planning[(agent_name, sunday, 'Nuit')] == 1).OnlyEnforceIf(sunday_nuit)
    #                 model.Add(planning[(agent_name, sunday, 'Nuit')] == 0).OnlyEnforceIf(sunday_nuit)

    #                 # Créer des variables de travail pour le samdi et le dimanche
    #                 saturday_work = model.NewBoolVar(f'{agent_name}_work_saturday_{saturday}')
    #                 sunday_work = model.NewBoolVar(f'{agent_name}_work_sunday_{sunday}')

    #                 # Si l'agent travaille soit en "Jour" soit en "Nuit" le samedi, alors saturday_work = 1
    #                 model.AddBoolOr([saturday_jour, saturday_nuit]).OnlyEnforceIf(saturday_work)
    #                 model.AddBoolOr([sunday_jour, sunday_nuit]).OnlyEnforceIf(sunday_work)

    #                 # Contraindre à un week-end complet ou rien
    #                 model.Add(saturday_work == sunday_work)

    #                 # Pénalité pour un week-end partiel
    #                 partial_weekend_penalty = model.NewBoolVar(f'{agent_name}_partial_weekend_penalty_{saturday}')
    #                 model.Add(saturday_work != sunday_work).OnlyEnforceIf(partial_weekend_penalty)

    #                 # Ajouter une légère pénalité pour encourager les week-ends complets
    #                 penalty_weight_weekends = 100    # Ajustable pour les pénalités
    #                 reward_weight_weekends = -100     # Ajustable pour les récompenses

    #                 # Pénaliser les week-ends partiels
    #                 model.Minimize(penalty_weight_weekends * partial_weekend_penalty)

    #                 # Récompenser les week-ends complets
    #                 model.Minimize(reward_weight_weekends * (saturday_work + sunday_work))
    ########################################################

    ########################################################
    # ! Mise en suspens de la contrainte de volume horaire similaire pour le moment
    # Tous les agents doivent avoir un volume horaire similaire
    # total_hours = {}
    # for agent in agents:
    #     agent_name = agent['name']
    #     total_hours[agent_name] = cp_model.LinearExpr.Sum(list(
    #         planning[(agent_name, day, 'Jour')] * jour_duration +
    #         planning[(agent_name, day, 'Nuit')] * nuit_duration +
    #         planning[(agent_name, day, 'CDP')] * cdp_duration
    #         for day in week_schedule
    #     ))

    # # Calculer le volume cible d'heures par agent
    # total_available_hours = sum(
    #     jour_duration + nuit_duration + cdp_duration for day in week_schedule
    # )
    # target_hours_per_agent = total_available_hours // len(agents)
    # print("Target hours per agent:", target_hours_per_agent)

    # acceptable_deviation = 240  # Ajuste cette valeur selon tes besoins (*10)
    # for agent_name in total_hours:
    #     model.Add(total_hours[agent_name] <= target_hours_per_agent + acceptable_deviation)
    #     model.Add(total_hours[agent_name] >= target_hours_per_agent - acceptable_deviation)

    # # Crée des variables pour la variance
    # variance = {}
    # for agent in agents:
    #     agent_name = agent['name']

    #     # Variable pour la différence entre les heures travaillées et l'objectif cible
    #     diff = model.NewIntVar(-10000, 10000, f'diff_{agent_name}')
    #     model.Add(diff == total_hours[agent_name] - target_hours_per_agent)

    #     # Variable pour le carré de la différence
    #     squared_diff = model.NewIntVar(0, 100000000, f'squared_diff_{agent_name}')
    #     model.AddMultiplicationEquality(squared_diff, [diff, diff])

    #     # Stocker la variance pour chaque agent
    #     variance[agent_name] = squared_diff

    # # Calculer la variance totale
    # total_variance = cp_model.LinearExpr.Sum(variance.values())
    # ! Fin de la mise en suspens de la contrainte de volume horaire similaire pour le moment
    ########################################################

    ########################################################
    # Objectifs
    ########################################################

    # Poids pour chaque composante de l'objectif
    weight_preferred = 100
    weight_other = 1
    weight_avoid = -250
    # variance_weight = 100

    # Maximiser les vacations préférées avec un poids supplémentaire
    objective_preferred_vacations = cp_model.LinearExpr.Sum(
        list(
            planning[(agent["name"], day, vacation)] * weight_preferred
            for agent in agents
            for day in week_schedule
            for vacation in vacations
            if vacation in agent["preferences"]["preferred"]
        )
    )

    # Ajouter un poids normal pour les autres vacations
    objective_other_vacations = cp_model.LinearExpr.Sum(
        list(
            planning[(agent["name"], day, vacation)] * weight_other
            for agent in agents
            for day in week_schedule
            for vacation in vacations
            if vacation not in agent["preferences"]["preferred"]
        )
    )

    # Pénaliser les vacations non désirées (évitées)
    penalized_vacations = cp_model.LinearExpr.Sum(
        list(
            planning[(agent["name"], day, vacation)] * weight_avoid
            for agent in agents
            for day in week_schedule
            for vacation in vacations
            if vacation in agent["preferences"]["avoid"]
        )
    )

    # Maximiser l'objectif global, avec une préférence marquée pour les vacations préférées et équilibre des heures
    model.Maximize(
        objective_preferred_vacations
        + objective_other_vacations
        + penalized_vacations
        - weekend_balancing_objective
        # (variance_weight * total_variance)  # ! Mise en suspens de la contrainte de volume horaire similaire pour le moment
    )

    # Solver
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = (
        120  # Limite de temps de résolution en secondes
    )
    status = solver.Solve(model)

    # Results
    # We accept optimal and feasible solutions
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        result = {}
        for agent in agents:
            agent_name = agent["name"]
            result[agent_name] = []
            for day in week_schedule:
                for vacation in vacations:
                    if solver.Value(planning[(agent_name, day, vacation)]):
                        result[agent_name].append((day, vacation))
        return result
    else:
        return {"info": "No solution found."}


if __name__ == "__main__":
    app.run(debug=True)
