<template>
  <div id="app">
    <div>
      <label for="start">Date de début :</label>
      <input type="date" id="start" name="start" v-model="startDate" />

      <br />
      <label for="end">Date de fin :</label>
      <input type="date" id="end" name="end" v-model="endDate" />
    </div>
    <!-- Sélecteur de mode -->
    <div class="generation-mode">
      <label>
        <input type="radio" v-model="isContinuityMode" :value="false" />
        Nouvelle génération
      </label>
      <label>
        <input type="radio" v-model="isContinuityMode" :value="true" />
        Génération avec continuité
      </label>
    </div>

    <!-- Tableau des Shifts Initiaux (uniquement si mode continuité activé) -->
    <div v-if="isContinuityMode && previousWeekSchedule.length">
      <h3>Semaine de transition</h3>
      <table class="transition-table">
        <thead>
          <tr>
            <th>Agent</th>
            <th v-for="day in previousWeekSchedule" :key="day">{{ day }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="agent in agents" :key="agent.name">
            <td>{{ agent.name }}</td>
            <td v-for="day in previousWeekSchedule" :key="day" :class="[getWeekendClass(day), getVacationClass(agent.name, day)]">
              <select v-model="selectedShifts[agent.name][day]">
                <option value="">-</option>
                <option v-for="vacation in vacations" :key="vacation" :value="vacation">
                  {{ vacation }}
                </option>
              </select>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div>
      <button @click="generatePlanning">Générer le planning</button>
    </div>

    <!-- Display the table only when planningResult is set -->
    <div v-if="planningResult">
      <PlanningTable
        :planning="planningResult"
        :weekSchedule="weekSchedule"
        :vacationDurations="vacationDurations"
        :vacationColors="vacationColors"
        :holidays="holidaysFromConfig"
        :unavailable="unavailableFromConfig"
        :dayOff="dayOffFromConfig"
        :training="trainingFromConfig"
      />
    </div>
    <!-- Otherwise, display an error message if there is an error -->
    <div v-else-if="errorMessage" class="error-card">
      <span class="error-icon">⚠️</span>
      <span class="error-text">{{ errorMessage }}</span>
    </div>
    <!-- Otherwise, display an info message if there is an info -->
     <div v-else-if="infoMessage" class="info-card">
      <span class="info-icon">ℹ️</span>
      <span class="info-text">{{ infoMessage }}</span>
    </div>
    <!-- Otherwise, display a message indicating that the schedule has not yet been generated -->
    <div v-else>
      <p>Le planning n'est pas encore généré.</p>
    </div>
    <div>
      <ConfigComponent />
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import PlanningTable from './components/PlanningTable.vue';
import ConfigComponent from './components/ConfigComponent.vue';

export default {
  components: {
    PlanningTable,
    ConfigComponent
  },
  data() {
    return {
      startDate: null, // Date de début du planning
      endDate: null, // Date de fin du planning
      planningResult: null, // Initialement, aucun planning n'est défini, sera rempli après l'appel à l'API
      vacationDurations: null, // Initialement, aucune durée de vacation n'est définie, sera rempli après l'appel à l'API
      weekSchedule: [],
      vacationColors: {
        'Jour': '#75FA79',  // Couleur pour la vaction Jour
        'Nuit': '#9175FA',  // Couleur pour la vacation Nuit
        'CDP': '#A59384'  // Couleur pour la vacation CDP
      },
      holidaysFromConfig: [], // Initialiser les jours fériés à partir de la configuration
      unavailableFromConfig: null, // Initialement, aucune indisponibilité n'est définie, sera rempli à partir de la configuration
      dayOffFromConfig: null, // Initialement, aucun jour de congé n'est défini, sera rempli à partir de la configuration
      trainingFromConfig: null, // Initialement, aucune formation n'est définie, sera rempli à partir de la configuration
      errorMessage: null, // Initially, no error is defined, will be filled after the call to the API
      infoMessage: null, // Initially, no information message is defined, will be filled in after the call to the API
      isContinuityMode: false, // Set generation mode to false
      previousWeekSchedule: [], // Set the previous week schedule to an empty array, will be filled after the call to the API
      agents: [], // Set the agents to an empty array, will be filled after the call to the API
      vacations: ['Jour', 'Nuit', 'CDP'], // Set the vacation types
      selectedShifts: {} // Set the selected shifts to an empty object
    };
  },
  watch: {
    // When user changes the continuity mode to true, fetch the previous week schedule
    isContinuityMode(newValue) {
      if (newValue) {
        this.fetchPreviousWeekSchedule();
      }
    }
  },
  methods: {
    // Récupérer la semaine précédente via l'API
    async fetchPreviousWeekSchedule() {
      if (!this.startDate) {
        alert("Veuillez sélectionner une période avant de continuer.");
        return;
      }
      try {
        const response = await axios.post("http://127.0.0.1:5000/previous-week-schedule", {
          start_date: this.startDate
        });
        console.log("Data de Fetch :", response.data);
        this.previousWeekSchedule = response.data.previous_week_schedule;
        this.agents = response.data.agents || []; // Si agents est undefined, on le remplace par un tableau vide pour éviter l’erreur.

        // Si agents est vide ou mal formaté, on affiche un message d’erreur dans la console et on stoppe l'exécution.
        if (!Array.isArray(this.agents) || this.agents.length === 0) {
          console.error("Erreur : Liste des agents vide ou mal définie", this.agents);
          return;
        }

        // Si previousWeekSchedule est vide ou mal formaté, on affiche un message d’erreur dans la console et on stoppe l'exécution.
        if (!Array.isArray(this.previousWeekSchedule) || this.previousWeekSchedule.length === 0) {
          console.error("Erreur : Semaine précédente vide ou mal définie", this.previousWeekSchedule);
          return;
        }

        // Initialiser les shifts sélectionnés uniquement si les données sont récupérées avec succès
        this.selectedShifts = {};
        this.agents.forEach(agent => {
          if (!agent.name) { //Si un agent est mal défini, on affiche un avertissement et on évite une potentielle erreur.
            console.warn("Agent sans nom détecté, vérifie le backend", agent);
            return;
          }
          this.selectedShifts[agent.name] = {};
          this.previousWeekSchedule.forEach(day => {
            this.selectedShifts[agent.name][day] = "";
          });
        });
      } catch (error) {
        console.error("Erreur lors de la récupération des données :", error);
      }
    },
    async generatePlanning() {
      const payload = {
        start_date: this.startDate,
        end_date: this.endDate
      };

      // Si le mode de continuité est activé, ajouter les données de la semaine précédente
      if (this.isContinuityMode) {
        payload.initial_shifts = {};
        for (const agent in this.selectedShifts) {
          payload.initial_shifts[agent] = [];
          for (const day in this.selectedShifts[agent]) {
            if (this.selectedShifts[agent][day]) {
            payload.initial_shifts[agent].push([day, this.selectedShifts[agent][day]]);
            }
          }
        }
      }

      try {
        // Envoyer la requête à Flask pour générer le planning avec les dates de début et de fin
        const response = await axios.post('http://127.0.0.1:5000/generate-planning', payload);
        
        this.planningResult = response.data.planning; // Stocker les données dans planningResult
        this.vacationDurations = response.data.vacation_durations; // Stocker les durées de vacation
        this.weekSchedule = response.data.week_schedule; // Stocker le calendrier de la période
        this.holidaysFromConfig = response.data.holidays; // Stocker les jours fériés à partir de la configuration
        this.unavailableFromConfig = response.data.unavailable; // Stocker les indisponibilités à partir de la configuration
        this.dayOffFromConfig = response.data.dayOff; // Stocker les jours de congé à partir de la configuration
        this.trainingFromConfig = response.data.training; // Stocker les formations à partir de la configuration
      } catch (error) {
        // If there is an error, check whether there is an info key in the response, otherwise display the error.
        if (error.response.data.info) {
          this.infoMessage = error.response.data.info;
        } else {
          this.errorMessage = 'Error when generating the schedule : ' + error.response.data.error;
        }
      }
    },
    // Détecte si un jour fait partie du week-end
    getWeekendClass(day) {
      // Si le jour commence par "Sam" ou "Dim", on retourne "weekend"
      // Sinon, on retourne une chaîne vide
      return day.startsWith("Sam") || day.startsWith("Dim") ? "weekend" : "";
    },
    // Applique une classe en fonction de la vacation sélectionnée
    getVacationClass(agentName, day) {
      const vacation = this.selectedShifts[agentName][day];
      // Si une vacation est sélectionnée, on la retourne en minuscule
      if (vacation) {
        return vacation.toLowerCase();
      }
      // Sinon, on retourne une chaîne vide
      return "";
    },
  }
};
</script>

<style scoped>
button {
  padding: 10px 15px;
  margin-bottom: 15px;
  background-color: #007bff;
  color: white;
  border: none;
  cursor: pointer;
}

button:hover {
  background-color: #0056b3;
}

.error-card {
  background-color: #ffe6e6;
  color: #c00;
  border: 1px solid #c00;
  border-radius: 8px;
  padding: 16px;
  margin: 16px 0;
  display: flex;
  align-items: center;
  box-shadow: 0 4 8px rgba(0, 0, 0, 0.1);
}

.error-icon {
  font-size: 24px;
  margin-right: 12px;
}

.error-text {
  font-size: 16px;
  font-weight: bold;
}

.info-card {
  background-color: #e6f7ff;
  color: #007bff;
  border: 1px solid #007bff;
  border-radius: 8px;
  padding: 16px;
  margin: 16px 0;
  display: flex;
  align-items: center;
  box-shadow: 0 4 8px rgba(0, 0, 0, 0.1);
}

.info-icon {
  font-size: 36px;
  margin-right: 12px;
}

.info-text {
  font-size: 16px;
  font-weight: bold;
}

/* Style du toggle de sélection de mode */
.generation-mode {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

/* Tableau de transition */
.transition-table {
  border-collapse: collapse;
  margin-top: 15px;
}

/* Style des en-têtes de colonnes */
.transition-table th {
  background-color: #f4f4f4;
  padding: 10px;
}

/* Bordures et espacement des cellules */
.transition-table th, .transition-table td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: center;
}

/* Griser les samedis et dimanches */
.transition-table td.weekend {
  background-color: #dedede;
}

/* Couleur de fond des cellules sélectionnées */
.transition-table td.jour {
  background-color: #75fa79;
}

.transition-table td.nuit {
  background-color: #9175fa;
}

.transition-table td.cdp {
  background-color: #a59384;
}

/* Sélecteurs de vacation */
.transition-table select {
  width: 100%;
  padding: 5px;
  border: none;
  background: transparent;
  font-size: 14px;
}
</style>
