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
      isContinuityMode: false, // Set generation mode to false
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
      } catch (error) {
        // If there is an error, check whether there is an info key in the response, otherwise display the error.
        if (error.response.data.info) {
          this.infoMessage = error.response.data.info;
        } else {
          this.errorMessage = 'Error when generating the schedule : ' + error.response.data.error;
        }
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

</style>
