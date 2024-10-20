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
      }
    },
    methods: {
      getVacationForAgent(agent, day) {
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
      getColumnColor(agent, day) {
        // Récupérer la couleur de la vacation
        const vacationColor = this.getVacationColor(agent, day);
        // Si une vacation est définie, retourner cette couleur, sinon retourner la couleur de la colonne
        if (!vacationColor || vacationColor === "white") {
          // Retourner la couleur de la colonne suivant le jour de la semaine
          if (day.includes("Sam") || day.includes("Dim")) {
            return "#dedede"; // Gris pour les week-ends
          } 
        }
        return vacationColor; // Retourner la couleur de la vacation
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
  