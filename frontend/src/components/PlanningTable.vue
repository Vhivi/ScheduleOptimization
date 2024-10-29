<template>
    <div>
      <h1>Planning des Vacations</h1>
      <table>
        <thead>
          <tr>
            <th>Agent</th>
            <th v-for="day in weekSchedule" :key="day">{{ day }}</th>
            <th>Total Vacations</th> <!-- Ajouter une colonne pour afficher le nombre de vacations -->
            <th>Total Heures</th> <!-- Ajouter une colonne pour afficher le total des heures -->
          </tr>
        </thead>
        <tbody>
          <tr v-for="(agent, index) in Object.keys(planning)" :key="index">
            <td>{{ agent }}</td>
            <td v-for="day in weekSchedule" :key="day" :style="{ backgroundColor: getColumnColor(agent, day)}">
              <!-- On affiche la vacation de cet agent ce jour-là -->
              {{ getVacationForAgent(agent, day) || '//' }}
            </td>
            <td>{{ calculateNumberShifts(agent) }}</td> <!-- Afficher le nombre de vacations pour cet agent -->
            <td>{{ calculateTotalHours(agent) }} h</td> <!-- Afficher le total des heures pour cet agent -->
          </tr>
        </tbody>
      </table>
    </div>
  </template>
  
  <script>
  export default {
    props: {
      planning: {
        type: Object,
        required: true
      },
      weekSchedule: {
        type: Array,
        required: true
      },
      vacationDurations: {
        type: Object,
        required: true
      },
      vacationColors: {
        type: Object,
        required: true
      },
      holidays: {
        type: Array,
        required: true
      },
      unavailable: {
        type: Object,
        required: true
      },
      dayOff: {
        type: Object,
        required: true
      }
    },
    methods: {
      getVacationForAgent(agent, day) {
        // Vérifie si le jour est un jour de congé
        if (this.isVacationDay(agent, day)) {
          return "Con."; // Retourner "Congé" si c'est un jour de congé
        }
        // Vérifie d'abord si l'agent est indisponible
        if (this.isUnavailable(agent, day)) {
          return "Ind."; // Retourner "Indisponible" si l'agent est indisponible
        }
        const vacations = this.planning[agent]

        if (Array.isArray(vacations)) {
          // Si c'est un tableau, utilisez .find()
          const vacationForDay = vacations.find(vac => vac[0] === day);
          return vacationForDay ? vacationForDay[1] : null;
        } else if (typeof vacations === 'object') {
          /// Si c'est un objet, utilisez Object.entries() pour parcourir les clés/valeurs
          for (const [vacationDay, vacation] of Object.entries(vacations)) {
            if (vacationDay === day) {
              return vacation;
            }
          }
          return null;
        }
      },
      isVacationDay(agent, day) { // Vérifie si un jour est un jour de congé
        // Vérifie si les jours de congé existent pour cet agent
        if (!this.dayOff || !this.dayOff[agent]) {
          console.error(`Jour de congé pour l'agent ${agent} non défini.`, this.dayOff);
          return false; // Retourner false si aucun jour de congé n'est défini
        }

        const vacation = this.dayOff[agent] || {}; // Obtenir les jours de congé pour cet agent
        const dayPart = day.split(" ")[1]; // Extraire la partie date (dd-mm)

        // Ajouter une année fictive pour les comparaisons
        const referenceYear = new Date().getFullYear();
        const vacationStartDate = new Date(`${vacation[0].slice(6, 10)}-${vacation[0].slice(3, 5)}-${vacation[0].slice(0, 2)}`); // Convertir la date de début au format YYYY-mm-dd
        const vacationEndDate = new Date(`${vacation[1].slice(6, 10)}-${vacation[1].slice(3, 5)}-${vacation[1].slice(0, 2)}`); // Convertir la date de fin au format YYYY-mm-dd
        const currentDate = new Date(`${referenceYear}-${dayPart.slice(3, 5)}-${dayPart.slice(0, 2)}`); // Convertir la date actuelle au format YYYY-mm-dd

        if (vacationStartDate > vacationEndDate) {
          // Si la date de début est supérieure à la date de fin, c'est un congé qui chevauche l'année
          return currentDate >= vacationStartDate || currentDate <= vacationEndDate;
        }

        // Sinon, c'est un congé normal
        return vacationStartDate <= currentDate && currentDate <= vacationEndDate;
      },
      isUnavailable(agent, day) { // Vérifie si un jour est une indisponibilité
        // Vérifie si les indisponibilités exsitent pour cet agent
        if (!this.unavailable || !this.unavailable[agent]) {
          console.error(`Indisponibilités pour l'agent ${agent} non définies.`, this.unavailable);
          return false; // Retourner false si aucune indisponibilité n'est définie
        }

        const unavailableDays = this.unavailable[agent] || [];
        const datePart = day.split(" ")[1]; // Extraire la partie de la date dd-mm

        // Comparer uniquement dd-mm des indisponiblités
        const formatedUnavailableDays = unavailableDays.map(date => date.slice(0, 5));  // Extraire uniquement dd-mm
        return formatedUnavailableDays.includes(datePart); // Retourner true si le jour est indisponible
      },
      //   // Chercher la vacation de cet agent pour ce jour
      //   const vacationForDay = this.planning[agent].find(vac => vac[0] === day);
      //   return vacationForDay ? vacationForDay[1] : null; // Retourne la vacation ou null si pas de vacation
      // },
      getVacationColor(agent, day) {
        // Obtenir la vacation pour cet agent
        const vacation = this.getVacationForAgent(agent, day);
        // Retourner la couleur correspondante
        return vacation ? this.vacationColors[vacation] : "white";  // Blanc si pas de vacation
      },
      // Vérifie si le jour est un jour férié
      isHoliday(day) {
        if (this.holidays && Array.isArray(this.holidays)) {
          // Extrait la partie de la date dd-mm de la chaine
          const datePart = day.split(" ")[1]; // Extraire la partie de la date
          return this.holidays.includes(datePart); // Retourner true si le jour est un jour férié dans la liste
        }
        return false; // Retourner false si la liste des jours fériés n'est pas définie
      },
      getColumnColor(agent, day) {
        // Vérifier d'abord si c'est un jour de congé
        if (this.isVacationDay(agent, day)) {
          return "#f2cb05"; // Jaune pour les jours de congé
        }

        // Vérifier d'abord si l'agent est indisponible
        if (this.isUnavailable(agent, day)) {
            return "#f2cb05"; // Jaune pour les jours indisponibles
          }
        
        // Enfin retourner la couleur de la vacation si elle existe
        const vacationColor = this.getVacationColor(agent, day);
        if (vacationColor && vacationColor !== "white") {
          return vacationColor; // Retourner la couleur de la vacation
        }

        // Vérifier si c'est un jour férié ou un week-end
        if (this.isHoliday(day) || day.includes("Sam") || day.includes("Dim")) {
            return "#dedede"; // Gris pour les jours fériés et les week-ends
          }

        return "white"; // Retourner blanc par défaut
      },
      calculateTotalHours(agent) {
        // Vérifier si this.planning[agent] est un tableau
        if (!Array.isArray(this.planning[agent])) {
          console.error(`Planning pour l'agent ${agent} n'est pas un tableau.`, this.planning[agent]);
          return 0; // Retourner 0 si ce n'est pas un tableau
        }
        // Calculer le total des heures pour cet agent en utilisant vacationDurations
        return this.planning[agent].reduce((total, vac) => {
          const vacation = vac[1]; // Obtenir la vacation
          return total + (this.vacationDurations[vacation] || 0); // Ajouter la durée de la vacation
        }, 0);  // Commencer à 0
      },
      calculateNumberShifts(agent) {
        // Vérifier si this.planning[agent] est un tableau
        if (!Array.isArray(this.planning[agent])) {
          console.error(`Planning pour l'agent ${agent} n'est pas un tableau.`, this.planning[agent]);
          return 0; // Retourner 0 si ce n'est pas un tableau
        }
        // Retourner le nombre de vacations pour cet agent
        return this.planning[agent].length;
      }
    }
  };
  </script>
  
  <style scoped>
  table {
    width: 100%;
    border-collapse: collapse;
  }
  
  th, td {
    border: 1px solid black;
    padding: 8px;
    text-align: center;
  }
  
  th {
    background-color: #dedede
  }
  </style>
  