<template>
  <div id="app">
    <div>
      <label for="start">Date de début :</label>
      <input type="date" id="start" name="start" v-model="startDate" />

      <br />
      <label for="end">Date de fin :</label>
      <input type="date" id="end" name="end" v-model="endDate" />
    </div>

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
            <td
              v-for="day in previousWeekSchedule"
              :key="day"
              :class="[getWeekendClass(day), getVacationClass(agent.name, day)]"
            >
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
      <button @click="generatePlanning" :disabled="isLoading">
        {{ isLoading ? "Génération en cours..." : "Générer le planning" }}
      </button>
    </div>

    <div v-if="isLoading" class="info-card">
      <span class="info-icon">ℹ️</span>
      <span class="info-text">Calcul en cours, merci de patienter...</span>
    </div>

    <div v-else-if="planningResult">
      <PlanningTable
        :planning="planningResult"
        :weekSchedule="weekSchedule"
        :vacationDurations="vacationDurations"
        :vacationColors="vacationColors"
        :holidays="holidaysFromConfig"
        :unavailable="unavailableFromConfig"
        :dayOff="dayOffFromConfig"
        :training="trainingFromConfig"
        :planningStartDate="startDate"
      />
    </div>

    <div v-else-if="errorMessage" class="error-card">
      <span class="error-icon">⚠️</span>
      <span class="error-text">{{ errorMessage }}</span>
    </div>

    <div v-else-if="infoMessage" class="info-card">
      <span class="info-icon">ℹ️</span>
      <span class="info-text">{{ infoMessage }}</span>
    </div>

    <div v-else>
      <p>Le planning n'est pas encore généré.</p>
    </div>
  </div>
</template>

<script>
import { apiPost, normalizeApiError } from './apiClient';
import PlanningTable from './components/PlanningTable.vue';

export default {
  components: {
    PlanningTable
  },
  data() {
    return {
      startDate: null,
      endDate: null,
      planningResult: null,
      vacationDurations: null,
      weekSchedule: [],
      vacationColors: {
        Jour: '#75FA79',
        Nuit: '#9175FA',
        CDP: '#A59384'
      },
      holidaysFromConfig: [],
      unavailableFromConfig: null,
      dayOffFromConfig: null,
      trainingFromConfig: null,
      errorMessage: null,
      infoMessage: null,
      isContinuityMode: false,
      previousWeekSchedule: [],
      agents: [],
      vacations: ['Jour', 'Nuit', 'CDP'],
      selectedShifts: {},
      isLoading: false
    };
  },
  watch: {
    isContinuityMode(newValue) {
      if (newValue) {
        this.fetchPreviousWeekSchedule();
      }
    }
  },
  methods: {
    resetMessages() {
      this.errorMessage = null;
      this.infoMessage = null;
    },
    resetPlanningData() {
      this.planningResult = null;
      this.vacationDurations = null;
      this.weekSchedule = [];
      this.holidaysFromConfig = [];
      this.unavailableFromConfig = null;
      this.dayOffFromConfig = null;
      this.trainingFromConfig = null;
    },
    async fetchPreviousWeekSchedule() {
      this.resetMessages();
      if (!this.startDate) {
        this.errorMessage = "Veuillez sélectionner une date de début avant d'activer la continuité.";
        return;
      }

      try {
        const response = await apiPost('/previous-week-schedule', {
          start_date: this.startDate
        });
        this.previousWeekSchedule = response.data.previous_week_schedule;
        this.agents = response.data.agents || [];

        if (!Array.isArray(this.agents) || this.agents.length === 0) {
          this.errorMessage = 'Erreur : liste des agents vide ou mal définie.';
          return;
        }

        if (!Array.isArray(this.previousWeekSchedule) || this.previousWeekSchedule.length === 0) {
          this.errorMessage = 'Erreur : semaine précédente vide ou mal définie.';
          return;
        }

        this.selectedShifts = {};
        this.agents.forEach((agent) => {
          if (!agent.name) {
            return;
          }
          this.selectedShifts[agent.name] = {};
          this.previousWeekSchedule.forEach((day) => {
            this.selectedShifts[agent.name][day] = '';
          });
        });
      } catch (error) {
        this.errorMessage = normalizeApiError(
          error,
          'Erreur lors de la récupération de la semaine précédente'
        );
      }
    },
    async generatePlanning() {
      this.resetMessages();
      this.resetPlanningData();

      if (!this.startDate || !this.endDate) {
        this.errorMessage = 'Veuillez sélectionner une date de début et une date de fin.';
        return;
      }

      const payload = {
        start_date: this.startDate,
        end_date: this.endDate
      };

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

      this.isLoading = true;
      try {
        const response = await apiPost('/generate-planning', payload);

        this.planningResult = response.data.planning;
        this.vacationDurations = response.data.vacation_durations;
        this.weekSchedule = response.data.week_schedule;
        this.holidaysFromConfig = response.data.holidays;
        this.unavailableFromConfig = response.data.unavailable;
        this.dayOffFromConfig = response.data.dayOff;
        this.trainingFromConfig = response.data.training;
      } catch (error) {
        const responseData = error?.response?.data;
        if (responseData && responseData.info) {
          this.infoMessage = responseData.info;
        } else {
          this.errorMessage = normalizeApiError(error, 'Erreur lors de la génération du planning');
        }
      } finally {
        this.isLoading = false;
      }
    },
    getWeekendClass(day) {
      return day.startsWith('Sam') || day.startsWith('Dim') ? 'weekend' : '';
    },
    getVacationClass(agentName, day) {
      const vacation = this.selectedShifts?.[agentName]?.[day];
      return vacation ? vacation.toLowerCase() : '';
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

button:disabled {
  background-color: #8fb8e8;
  cursor: not-allowed;
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
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
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
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.info-icon {
  font-size: 24px;
  margin-right: 12px;
}

.info-text {
  font-size: 16px;
  font-weight: bold;
}

.generation-mode {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}

.transition-table {
  border-collapse: collapse;
  margin-top: 15px;
}

.transition-table th {
  background-color: #f4f4f4;
  padding: 10px;
}

.transition-table th,
.transition-table td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: center;
}

.transition-table td.weekend {
  background-color: #dedede;
}

.transition-table td.jour {
  background-color: #75fa79;
}

.transition-table td.nuit {
  background-color: #9175fa;
}

.transition-table td.cdp {
  background-color: #a59384;
}

.transition-table select {
  width: 100%;
  padding: 5px;
  border: none;
  background: transparent;
  font-size: 14px;
}
</style>
