import json
import locale
from collections import defaultdict
from datetime import datetime, timedelta

from flask import Flask, jsonify, request
from flask_cors import CORS
from ortools.sat.python import cp_model

app = Flask(__name__)
CORS(app)


@app.route("/config")
# Charger le fichier de configuration
def load_config():
    with open("config.json", "r") as config_file:
        return json.load(config_file)


config = load_config()
weekend_days = ["Sam", "Dim"]  # Jours du week-end abrégés
holidays = config[
    "holidays"
]  # Jours fériés à remettre à jour chaque année, notamment pour le lundi de Pâques


@app.route("/")
def home():
    return "Hello, Flask is up and running!"


@app.route("/generate-planning", methods=["POST"])
def generate_planning_route():
    # Récupération des données à partir du fichier JSON
    agents = config["agents"]
    vacations = config["vacations"]
    vacation_durations = config["vacation_durations"]
    holidays = config["holidays"]
    unavailable = {}
    dayOff = {}
    training = {}

    # Récupérer les jours de formation des agents et les stocker dans un dictionnaire {agent: [jours]}
    for agent in agents:
        if "training" in agent:
            training[agent["name"]] = agent["training"]

    # Récupérer les jours d'indisponibilité des agents et les stocker dans un dictionnaire {agent: [jours]}
    for agent in agents:
        if "unavailable" in agent:
            unavailable[agent["name"]] = agent["unavailable"]

    # Récupérer les jours de congés des agents
    for agent in agents:
        if "vacation" in agent:
            vacation = agent["vacation"]
            if isinstance(vacation, dict) and "start" in vacation and "end" in vacation:
                vacation_start = vacation["start"]
                vacation_end = vacation["end"]

                # Stocker les jours de congés dans un dictionnaire {agent: [début, fin]}
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

    # Calculer la liste des jours à partir des dates
    week_schedule = get_week_schedule(start_date, end_date)

    # Appel de la fonction de génération de planning
    result = generate_planning(agents, vacations, week_schedule, dayOff)

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


def get_week_schedule(start_date_str, end_date_str):
    # Configuer le local pour utiliser les jours de la semaine en français
    locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
    # Convertir les chaines en objets datetime
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")  # Format date / ISO 8601
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")  # Format date / ISO 8601

    # Calculer les jours entre la date de début et la date de fin
    delta = end_date - start_date
    week_schedule = [
        (start_date + timedelta(days=i)).strftime("%a %d-%m").capitalize()
        for i in range(delta.days + 1)
    ]  # Format : Jour abrégé + Date (ex: Lun 25-12)
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
        if day_name == "Dim." or day == week_schedule[-1]:  # Dimanche ou dernier jour
            weeks.append(current_week)
            current_week = []

    return weeks


def split_by_month_or_period(week_schedule):
    # Divise week_schedule en période mensuelle ou unique selon la durée
    periods = []
    current_period = []
    previous_month = None

    for day in week_schedule:
        # Extraire le mois (format : Lun 25-12)
        current_month = day.split(" ")[1].split("-")[1]  # Extraire le mois (ex: 12)

        # Si changement de mois, commencer une nouvelle période
        if previous_month and current_month != previous_month:
            periods.append(current_period)
            current_period = []
        current_period.append(day)
        previous_month = current_month

    # Ajouter la dernière période
    if current_period:
        periods.append(current_period)

    return periods


def is_vacation_day(agent_name, day, dayOff):
    """Vérifie si le jour est un jour de congé pour cet agent."""
    if agent_name in dayOff:
        vacation_start, vacation_end = dayOff[agent_name]
        # Convertir les dates de congé et le jour en objets datetime pour comparaison
        vacation_start_date = datetime.strptime(vacation_start, "%d-%m-%Y")
        vacation_end_date = datetime.strptime(vacation_end, "%d-%m-%Y")
        day_part = day.split(" ")[1]  # Extraire la date (ex: 25-12)
        day_date = datetime.strptime(
            f"{day_part}-{vacation_start_date.year}", "%d-%m-%Y"
        )

        # Vérifier si le jour est entre la date de début et de fin du congé
        return vacation_start_date <= day_date <= vacation_end_date and not is_weekend(
            day
        )
    return False


def is_weekend(day):
    """Détermine si un jour est un samedi ou un dimanche."""
    day_name = day.split(" ")[0]
    return day_name in ["Sam.", "Dim."]


def generate_planning(agents, vacations, week_schedule, dayOff):
    model = cp_model.CpModel()

    weeks_split = split_into_weeks(week_schedule)  # Diviser week_schedule en semaines

    # Ajuster les durées des vacations en multipliant par 10 pour éliminer les décimales
    jour_duration = int(config["vacation_durations"]["Jour"] * 10)
    nuit_duration = int(config["vacation_durations"]["Nuit"] * 10)
    cdp_duration = int(config["vacation_durations"]["CDP"] * 10)
    conge_duration = int(config["vacation_durations"]["Conge"] * 10)

    ########################################################
    # Variables
    ########################################################

    # Une variable par agent/vacation/jour
    planning = {}
    for agent in agents:
        agent_name = agent["name"]  # Utiliser le nom de l'agent comme clé
        for day in week_schedule:
            for vacation in vacations:
                planning[(agent_name, day, vacation)] = model.NewBoolVar(
                    f"planning_{agent_name}_{day}_{vacation}"
                )

    ########################################################
    # Hard Constraints
    ########################################################
    # (Mettre ici toutes les contraintes incontournables)

    # Chaque agent peut travailler au plus une vacation par jour
    for agent in agents:
        agent_name = agent["name"]
        for day in week_schedule:
            model.Add(
                sum(planning[(agent_name, day, vacation)] for vacation in vacations)
                <= 1
            )

    # Au moins une vacation par agent pour la semaine
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

    # Chaque vacation doit être assignée à un agent chaque jour, sauf CDP le week-end et les jours fériés
    for day in week_schedule:
        day_date = day.split(" ")[1]  # Extraire la date
        for vacation in vacations:
            # Exclusion de la vacation CDP le week-end et jours fériés
            if vacation == "CDP" and (
                "Sam" in day or "Dim" in day or day_date in holidays
            ):
                # Ne pas assigner la vacation CDP le week-end et jours fériés
                model.Add(
                    sum(planning[(agent["name"], day, "CDP")] for agent in agents) == 0
                )
            else:
                # Somme des agents assignés à une vacation spécifique pour un jour donné doit être égale à 1
                model.Add(
                    sum(planning[(agent["name"], day, vacation)] for agent in agents)
                    == 1
                )

    # Après une vacation de nuit, pas de vacation de jour ou CDP le lendemain
    for agent in agents:
        agent_name = agent["name"]
        for day_idx, day in enumerate(
            week_schedule[:-1]
        ):  # On ne prend pas en compte le dernier jour
            next_day = week_schedule[day_idx + 1]

            # Variables boolèennes pour les vacations
            nuit_var = planning[(agent_name, day, "Nuit")]
            jour_var = planning[(agent_name, next_day, "Jour")]
            cdp_var = planning[(agent_name, next_day, "CDP")]

            # Si l'agent travaille la nuit, il ne peut pas travailler une vacation de jour ou CDP le lendemain
            model.Add(jour_var == 0).OnlyEnforceIf(nuit_var)
            model.Add(cdp_var == 0).OnlyEnforceIf(nuit_var)

    ########################################################
    # Limitation du nombre de CDP à 2 par semaine
    for agent in agents:
        agent_name = agent["name"]

        for week in weeks_split:
            # Limiter le nombre de vacation CDP à 3 par semaine (du lundi au dimanche)
            model.Add(sum(planning[(agent_name, day, "CDP")] for day in week) <= 2)
    ########################################################

    ########################################################
    # Un agent ne travaille pas quand il est indisponible
    # Une indisponibilité est une journée où l'agent ne peut pas avoir de vacation quelle qu'elle soit.
    for agent in agents:
        agent_name = agent["name"]

        if "unavailable" in agent:
            # Récupérer les jours d'indisponibilité de l'agent
            unavailable_days = agent["unavailable"]

            # Parcourir chaque jour d'indisponibilité
            for unavailable_date in unavailable_days:
                # Extraire la portion date du jour
                unavailable_day = datetime.strptime(
                    unavailable_date, "%d-%m-%Y"
                ).strftime("%d-%m")

                # Interdire toutes les vacations pour l'agent ce jour
                for day in week_schedule:
                    if (
                        unavailable_day in day
                    ):  # Vérifie si le jour correspond à une indisponibilité
                        for vacation in vacations:
                            model.Add(planning[(agent_name, day, vacation)] == 0)
    ########################################################

    ########################################################
    # Un agent ne travaille pas quand il est en formation
    # Une formation est une journée où l'agent ne peut pas avoir de vacation quelle qu'elle soit.
    for agent in agents:
        agent_name = agent["name"]

        if "training" in agent:
            # Récupérer les jours de formation de l'agent
            training_days = agent["training"]

            # Parcourir chaque jour de formation
            for training_date in training_days:
                # Extraire la portion date du jour
                training_day = datetime.strptime(training_date, "%d-%m-%Y").strftime(
                    "%d-%m"
                )

                # Interdire toutes les vacations pour l'agent ce jour
                for day in week_schedule:
                    if (
                        training_day in day
                    ):  # Vérifie si le jour correspond à une formation
                        for vacation in vacations:
                            model.Add(planning[(agent_name, day, vacation)] == 0)
    ########################################################

    ########################################################
    # Congés des agents
    date_format_full = "%d-%m-%Y"
    total_hours = {}

    for agent in agents:
        agent_name = agent["name"]
        total_hours[agent_name] = 0 # Initialiser le total d'heures pour l'agent

        # Récupérer les informations de congés s'il y en a
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
                # Extrait le jour et le mois et compléter avec l'année de vacation_start
                day_part = day_str.split(" ")[1]  # Extrait la date au format %d-%m
                # Identifier le format et convertir le jour en objet datetime
                try:
                    day_date = datetime.strptime(
                        f"{day_part}-{vacation_start.year}", date_format_full
                    )
                except ValueError:
                    continue  # Ignorer la dates mal formées

                # Si le jour est un jour de congé, interdire toutes les vacations
                if vacation_start <= day_date <= vacation_end:
                    for vacation in vacations:
                        model.Add(planning[(agent_name, day_str, vacation)] == 0)

                    # Calcul des heures pour les jours de congés (7 heures du lundi au samedi)
                    if day_date.weekday() < 6:  # lundi (0) à samedi (5)
                        total_hours[agent_name] += 70  # 7 heures * 10
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

    # Résultats
    # Nous acceptons les solutions optimales et réalisables
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
        return "No solution found."


if __name__ == "__main__":
    app.run(debug=True)
