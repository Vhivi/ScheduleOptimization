<template>
  <div id="app">
    <div>
      <label for="start">Date de début :</label>
      <input type="date" id="start" name="start" v-model="startDate" />

      <br />
      <label for="end">Date de fin :</label>
      <input type="date" id="end" name="end" v-model="endDate" />
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
      errorMessage: null // Initially, no error is defined, will be filled after the call to the API
    };
  },
  methods: {
    async generatePlanning() {
      try {
        // Envoyer la requête à Flask pour générer le planning avec les dates de début et de fin
        const response = await axios.post('http://127.0.0.1:5000/generate-planning', {
          start_date: this.startDate,
          end_date: this.endDate
        });
        this.planningResult = response.data.planning; // Stocker les données dans planningResult
        this.vacationDurations = response.data.vacation_durations; // Stocker les durées de vacation
        this.weekSchedule = response.data.week_schedule; // Stocker le calendrier de la période
        this.holidaysFromConfig = response.data.holidays; // Stocker les jours fériés à partir de la configuration
        this.unavailableFromConfig = response.data.unavailable; // Stocker les indisponibilités à partir de la configuration
        this.dayOffFromConfig = response.data.dayOff; // Stocker les jours de congé à partir de la configuration
        this.trainingFromConfig = response.data.training; // Stocker les formations à partir de la configuration
        this.errorMessage = response.data.error; // Stocke l'erreur pour affichage si nécessaire
      } catch (error) {
        this.errorMessage = 'Erreur lors de la génération du planning : ' + error.response.data.error;
        console.error('Erreur lors de la génération du planning :', error.response.data.error);
      }
    }
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
</style>
