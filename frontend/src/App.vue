<template>
  <div id="app">
    <div class="mode-switch">
      <button class="mode-btn" :class="{ active: activeMode === 'planning' }" @click="activeMode = 'planning'">
        Planning
      </button>
      <button class="mode-btn" :class="{ active: activeMode === 'config' }" @click="activeMode = 'config'">
        Configuration
      </button>
    </div>

    <div v-if="activeMode === 'config'" class="config-panel">
      <h2>Configuration interactive</h2>

      <div class="config-actions">
        <button @click="loadActiveConfig" :disabled="isConfigLoading">Charger config active</button>
        <button @click="loadDefaultConfig" :disabled="isConfigLoading">Charger défaut</button>
        <button @click="saveConfig" :disabled="isConfigSaving || isConfigLoading">
          {{ isConfigSaving ? 'Sauvegarde...' : 'Sauvegarder config.json' }}
        </button>
      </div>

      <p v-if="configDirty" class="config-dirty">Modifications non sauvegardées.</p>

      <div class="config-block">
        <h3>Vacations</h3>
        <label for="vacationsInput">Liste (séparée par virgules)</label>
        <input
          id="vacationsInput"
          type="text"
          :value="vacationsInput"
          @input="vacationsInput = $event.target.value"
          @change="applyVacationsInput"
        />

        <div v-for="vacation in configData.vacations" :key="vacation" class="vacation-row">
          <span class="vacation-name">{{ vacation }}</span>
          <label>Durée</label>
          <input
            type="number"
            min="0.1"
            step="0.1"
            :value="configData.vacation_durations[vacation]"
            @input="setVacationDuration(vacation, $event.target.value)"
          />
          <label>Agents simultanés</label>
          <input
            type="number"
            min="0"
            step="1"
            :value="configData.staffing_requirements[vacation]"
            @input="setStaffingRequirement(vacation, $event.target.value)"
          />
        </div>
      </div>

      <div class="config-block">
        <h3>Jours fériés</h3>
        <label for="holidaysInput">Format `dd-mm` (séparés par virgules)</label>
        <input id="holidaysInput" type="text" :value="holidaysInput" @input="setHolidaysInput($event.target.value)" />
      </div>

      <div class="config-block">
        <h3>Agents</h3>
        <button @click="addAgent">Ajouter un agent</button>

        <div v-for="(agent, index) in configData.agents" :key="agent.name + '_' + index" class="agent-card">
          <div class="agent-header">
            <strong>Agent {{ index + 1 }}</strong>
            <button class="danger-btn" @click="removeAgent(index)">Supprimer</button>
          </div>

          <label>Nom</label>
          <input type="text" v-model="agent.name" />

          <label>Preferred (virgules)</label>
          <input
            type="text"
            :value="joinList(agent.preferences.preferred)"
            @input="setList(agent.preferences, 'preferred', $event.target.value)"
          />

          <label>Avoid (virgules)</label>
          <input
            type="text"
            :value="joinList(agent.preferences.avoid)"
            @input="setList(agent.preferences, 'avoid', $event.target.value)"
          />

          <label>Restrictions (virgules)</label>
          <input type="text" :value="joinList(agent.restriction)" @input="setList(agent, 'restriction', $event.target.value)" />

          <label>Indisponibilités `dd-mm-YYYY`</label>
          <input type="text" :value="joinList(agent.unavailable)" @input="setList(agent, 'unavailable', $event.target.value)" />

          <label>Formation `dd-mm-YYYY`</label>
          <input type="text" :value="joinList(agent.training)" @input="setList(agent, 'training', $event.target.value)" />

          <label>Exclusions `dd-mm-YYYY`</label>
          <input type="text" :value="joinList(agent.exclusion)" @input="setList(agent, 'exclusion', $event.target.value)" />

          <div class="vacation-periods">
            <div class="vacation-periods-header">
              <span>Congés</span>
              <button @click="addVacationPeriod(agent)">Ajouter période</button>
            </div>
            <div
              v-for="(period, periodIndex) in agent.vacations"
              :key="`p_${index}_${periodIndex}`"
              class="vacation-period-row"
            >
              <input
                type="text"
                :value="period.start"
                placeholder="start dd-mm-YYYY"
                @input="setVacationPeriod(agent, periodIndex, 'start', $event.target.value)"
              />
              <input
                type="text"
                :value="period.end"
                placeholder="end dd-mm-YYYY"
                @input="setVacationPeriod(agent, periodIndex, 'end', $event.target.value)"
              />
              <button class="danger-btn" @click="removeVacationPeriod(agent, periodIndex)">X</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else>
      <div>
        <label for="start">Date de début :</label>
        <input type="date" id="start" name="start" v-model="startDate" />
        <br />
        <label for="end">Date de fin :</label>
        <input type="date" id="end" name="end" v-model="endDate" />
      </div>

      <div class="generation-mode">
        <label>
          <input type="radio" v-model="generationMode" value="new" />
          Nouvelle génération
        </label>
        <label>
          <input type="radio" v-model="generationMode" value="continuity" />
          Génération avec continuité
        </label>
        <label>
          <input type="radio" v-model="generationMode" value="existing" />
          Optimisation de l'existant
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

      <div v-if="isExistingOptimizationMode && manualWeekSchedule.length && agents.length">
        <h3>Saisie manuelle (cellule unitaire)</h3>
        <div v-for="(monthDays, monthKey) in manualScheduleByMonth" :key="monthKey">
          <h4>{{ formatMonthTitle(monthKey) }}</h4>
          <table class="transition-table">
            <thead>
              <tr>
                <th>Agent</th>
                <th v-for="day in monthDays" :key="day">{{ day }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="agent in agents" :key="agent.name">
                <td>{{ agent.name }}</td>
                <td
                  v-for="day in monthDays"
                  :key="day"
                  :class="[getWeekendClass(day), getManualCellClass(agent.name, day), getWarningCellClass(agent.name, day)]"
                  :style="getManualCellStyle(agent.name, day)"
                >
                  <select v-model="manualSelectedShifts[agent.name][day]">
                    <option value="">-</option>
                    <option v-for="vacation in vacations" :key="vacation" :value="vacation">
                      {{ vacation }}
                    </option>
                    <option value="status:unavailable">Indisponible</option>
                    <option value="status:training">Formation</option>
                    <option value="status:vacations">Congé</option>
                    <option value="status:restriction">Restriction</option>
                    <option
                      v-for="(duration, restrictionType) in restrictionTypesDurations"
                      :key="`r_${restrictionType}`"
                      :value="`status:restrictions:${restrictionType}`"
                    >
                      Restriction - {{ restrictionType }}
                    </option>
                  </select>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="isExistingOptimizationMode && optimizationMeta" class="info-card">
        <span class="info-icon">📊</span>
        <span class="info-text">
          {{ optimizationMeta.manual_cell_count || 0 }} cellule(s) manuelle(s),
          {{ optimizationMeta.conflict_count || 0 }} warning(s),
          statut: {{ optimizationStatus || 'ok' }}.
        </span>
      </div>

      <div v-if="isExistingOptimizationMode && optimizationWarnings.length" class="warning-card">
        <h4>Warnings d'optimisation</h4>
        <ul>
          <li v-for="(warning, index) in optimizationWarnings" :key="`warn_${index}`">
            {{ warning.agent }} - {{ warning.date }} ({{ warning.slot }}) : {{ warning.message }}
          </li>
        </ul>
      </div>

      <div v-if="isExistingOptimizationMode && optimizationSuggestions.length" class="warning-card">
        <h4>Suggestions de correction</h4>
        <ul>
          <li v-for="(suggestion, index) in optimizationSuggestions" :key="`sugg_${index}`">
            {{ suggestion.agent }} - {{ suggestion.date }} : {{ suggestion.message }}
            <button
              v-if="hasClearCellProposal(suggestion)"
              class="secondary-btn"
              @click="applyClearCellSuggestion(suggestion)"
            >
              Appliquer: vider la cellule
            </button>
          </li>
        </ul>
      </div>

      <div>
        <button @click="generatePlanning" :disabled="isLoading || isConfigSaving">
          {{ isLoading ? "Génération en cours..." : actionButtonLabel }}
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
          :restrictions="restrictionsFromConfig"
          :restrictionsDurations="restrictionDurationsFromConfig"
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
  </div>
</template>

<script>
import { apiGet, apiPost, apiPut, normalizeApiError } from './apiClient';
import PlanningTable from './components/PlanningTable.vue';

function cloneConfig(config) {
  return JSON.parse(JSON.stringify(config));
}

function parseCsvList(value) {
  if (!value) {
    return [];
  }
  const unique = new Set();
  value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
    .forEach((item) => unique.add(item));
  return Array.from(unique);
}

function defaultAgent(name = 'NouvelAgent') {
  return {
    name,
    preferences: {
      preferred: [],
      avoid: []
    },
    restriction: [],
    unavailable: [],
    training: [],
    exclusion: [],
    vacations: []
  };
}

export default {
  components: {
    PlanningTable
  },
  data() {
    return {
      activeMode: 'planning',
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
      restrictionsFromConfig: null,
      restrictionDurationsFromConfig: {},
      errorMessage: null,
      infoMessage: null,
      generationMode: 'new',
      previousWeekSchedule: [],
      agents: [],
      vacations: ['Jour', 'Nuit', 'CDP'],
      selectedShifts: {},
      manualWeekSchedule: [],
      manualSelectedShifts: {},
      optimizationWarnings: [],
      optimizationSuggestions: [],
      optimizationMeta: null,
      optimizationStatus: null,
      isLoading: false,
      isConfigLoading: false,
      isConfigSaving: false,
      configDirty: false,
      isHydratingConfig: false,
      configData: {
        agents: [],
        vacations: ['Jour', 'Nuit', 'CDP'],
        vacation_durations: {
          Jour: 12,
          Nuit: 12,
          CDP: 5.5,
          Conge: 7
        },
        staffing_requirements: {
          Jour: 1,
          Nuit: 1,
          CDP: 1
        },
        holidays: [],
        solver: {}
      },
      vacationsInput: '',
      holidaysInput: ''
    };
  },
  watch: {
    generationMode(newValue) {
      if (newValue === 'continuity') {
        this.fetchPreviousWeekSchedule();
      }
      if (newValue === 'existing') {
        this.initializeManualGrid();
      }
    },
    startDate() {
      if (this.isExistingOptimizationMode) this.initializeManualGrid();
    },
    endDate() {
      if (this.isExistingOptimizationMode) this.initializeManualGrid();
    },
    configData: {
      deep: true,
      handler() {
        if (!this.isHydratingConfig && !this.isConfigLoading && !this.isConfigSaving) {
          this.configDirty = true;
        }
      }
    }
  },
  async mounted() {
    await this.loadActiveConfig();
  },
  computed: {
    isContinuityMode() {
      return this.generationMode === 'continuity';
    },
    isExistingOptimizationMode() {
      return this.generationMode === 'existing';
    },
    actionButtonLabel() {
      if (this.isExistingOptimizationMode) return "Optimiser le reste";
      return "Générer le planning";
    },
    manualScheduleByMonth() {
      return this.manualWeekSchedule.reduce((months, day) => {
        const monthKey = day.split(' ')[1]?.split('-')[1] || '??';
        if (!months[monthKey]) {
          months[monthKey] = [];
        }
        months[monthKey].push(day);
        return months;
      }, {});
    },
    restrictionTypesDurations() {
      return this.restrictionDurationsFromConfig || this.configData?.restriction_types_durations || {};
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
      this.restrictionsFromConfig = null;
      this.restrictionDurationsFromConfig = {};
      this.optimizationWarnings = [];
      this.optimizationSuggestions = [];
      this.optimizationMeta = null;
      this.optimizationStatus = null;
    },
    async applyConfigToState(config) {
      this.isHydratingConfig = true;
      const normalized = cloneConfig(config);
      normalized.agents = Array.isArray(normalized.agents) ? normalized.agents : [];
      normalized.vacations = Array.isArray(normalized.vacations) ? normalized.vacations : [];
      normalized.vacation_durations = normalized.vacation_durations || {};
      normalized.staffing_requirements = normalized.staffing_requirements || {};
      normalized.holidays = Array.isArray(normalized.holidays) ? normalized.holidays : [];
      normalized.solver = normalized.solver || {};
      normalized.restriction_types_durations = normalized.restriction_types_durations || {};

      normalized.vacations = normalized.vacations.map((value) => String(value).trim()).filter(Boolean);
      normalized.vacations.forEach((vacation) => {
        if (normalized.vacation_durations[vacation] == null) {
          normalized.vacation_durations[vacation] = 1;
        }
        if (normalized.staffing_requirements[vacation] == null) {
          normalized.staffing_requirements[vacation] = 1;
        }
      });

      if (normalized.vacation_durations.Conge == null) {
        normalized.vacation_durations.Conge = 7;
      }

      normalized.agents = normalized.agents.map((agent, index) => ({
        ...defaultAgent(`Agent${index + 1}`),
        ...agent,
        preferences: {
          preferred: Array.isArray(agent?.preferences?.preferred) ? agent.preferences.preferred : [],
          avoid: Array.isArray(agent?.preferences?.avoid) ? agent.preferences.avoid : []
        },
        restriction: Array.isArray(agent?.restriction) ? agent.restriction : [],
        unavailable: Array.isArray(agent?.unavailable) ? agent.unavailable : [],
        training: Array.isArray(agent?.training) ? agent.training : [],
        exclusion: Array.isArray(agent?.exclusion) ? agent.exclusion : [],
        vacations: Array.isArray(agent?.vacations) ? agent.vacations : []
      }));

      this.configData = normalized;
      this.vacationsInput = normalized.vacations.join(', ');
      this.holidaysInput = normalized.holidays.join(', ');
      this.vacations = [...normalized.vacations];
      this.agents = [...normalized.agents];
      this.restrictionDurationsFromConfig = normalized.restriction_types_durations;
      await this.$nextTick();
      this.isHydratingConfig = false;
      this.configDirty = false;
    },
    async loadActiveConfig() {
      this.resetMessages();
      this.isConfigLoading = true;
      try {
        const response = await apiGet('/config');
        await this.applyConfigToState(response.data);
      } catch (error) {
        this.errorMessage = normalizeApiError(error, 'Erreur lors du chargement de la configuration active');
      } finally {
        this.isConfigLoading = false;
      }
    },
    async loadDefaultConfig() {
      this.resetMessages();
      this.isConfigLoading = true;
      try {
        const response = await apiGet('/config/default');
        await this.applyConfigToState(response.data);
        this.infoMessage = 'Configuration par défaut chargée (non sauvegardée).';
      } catch (error) {
        this.errorMessage = normalizeApiError(error, 'Erreur lors du chargement de la configuration par défaut');
      } finally {
        this.isConfigLoading = false;
      }
    },
    buildConfigPayload() {
      const payload = cloneConfig(this.configData);
      payload.vacations = parseCsvList(this.vacationsInput);
      payload.holidays = parseCsvList(this.holidaysInput);

      payload.vacation_durations = payload.vacation_durations || {};
      payload.staffing_requirements = payload.staffing_requirements || {};

      payload.vacations.forEach((vacation) => {
        const duration = Number(payload.vacation_durations[vacation]);
        payload.vacation_durations[vacation] = Number.isFinite(duration) && duration > 0 ? duration : 1;

        const staffing = Number(payload.staffing_requirements[vacation]);
        payload.staffing_requirements[vacation] = Number.isFinite(staffing) && staffing >= 0 ? Math.floor(staffing) : 1;
      });

      if (payload.vacation_durations.Conge == null || Number(payload.vacation_durations.Conge) <= 0) {
        payload.vacation_durations.Conge = 7;
      } else {
        payload.vacation_durations.Conge = Number(payload.vacation_durations.Conge);
      }

      payload.agents = (payload.agents || []).map((agent, index) => ({
        ...defaultAgent(`Agent${index + 1}`),
        ...agent,
        name: (agent.name || `Agent${index + 1}`).trim(),
        preferences: {
          preferred: parseCsvList((agent.preferences?.preferred || []).join(', ')),
          avoid: parseCsvList((agent.preferences?.avoid || []).join(', '))
        },
        restriction: parseCsvList((agent.restriction || []).join(', ')),
        unavailable: parseCsvList((agent.unavailable || []).join(', ')),
        training: parseCsvList((agent.training || []).join(', ')),
        exclusion: parseCsvList((agent.exclusion || []).join(', ')),
        vacations: (agent.vacations || [])
          .filter((period) => period?.start && period?.end)
          .map((period) => ({
            start: String(period.start).trim(),
            end: String(period.end).trim()
          }))
      }));

      return payload;
    },
    formatValidationErrors(details) {
      if (!Array.isArray(details) || details.length === 0) {
        return '';
      }
      return details.map((item) => `${item.path}: ${item.message}`).join(' | ');
    },
    async saveConfig() {
      this.resetMessages();
      this.isConfigSaving = true;
      try {
        const payload = this.buildConfigPayload();
        const response = await apiPut('/config', payload);
        await this.applyConfigToState(response.data);
        this.infoMessage = 'Configuration sauvegardée et appliquée.';
        if (this.isContinuityMode) {
          await this.fetchPreviousWeekSchedule();
        }
      } catch (error) {
        const details = this.formatValidationErrors(error?.response?.data?.details);
        if (details) {
          this.errorMessage = `${normalizeApiError(error, 'Erreur de validation config')} | ${details}`;
        } else {
          this.errorMessage = normalizeApiError(error, 'Erreur lors de la sauvegarde de la configuration');
        }
      } finally {
        this.isConfigSaving = false;
      }
    },
    async saveConfigIfNeeded() {
      if (!this.configDirty) {
        return true;
      }
      await this.saveConfig();
      if (this.configDirty) {
        this.configDirty = false;
      }
      return true;
    },
    applyVacationsInput() {
      const parsed = parseCsvList(this.vacationsInput);
      this.configData.vacations = parsed;
      parsed.forEach((vacation) => {
        if (this.configData.vacation_durations[vacation] == null) {
          this.configData.vacation_durations[vacation] = 1;
        }
        if (this.configData.staffing_requirements[vacation] == null) {
          this.configData.staffing_requirements[vacation] = 1;
        }
      });
    },
    setVacationDuration(vacation, value) {
      const parsed = Number(value);
      this.configData.vacation_durations[vacation] = Number.isFinite(parsed) ? parsed : 1;
    },
    setStaffingRequirement(vacation, value) {
      const parsed = Math.floor(Number(value));
      this.configData.staffing_requirements[vacation] = Number.isFinite(parsed) ? Math.max(parsed, 0) : 1;
    },
    setHolidaysInput(value) {
      this.holidaysInput = value;
      this.configData.holidays = parseCsvList(value);
    },
    joinList(values) {
      if (!Array.isArray(values)) {
        return '';
      }
      return values.join(', ');
    },
    setList(target, key, value) {
      target[key] = parseCsvList(value);
    },
    addAgent() {
      this.configData.agents.push(defaultAgent(`Agent${this.configData.agents.length + 1}`));
    },
    removeAgent(index) {
      this.configData.agents.splice(index, 1);
    },
    addVacationPeriod(agent) {
      if (!Array.isArray(agent.vacations)) {
        agent.vacations = [];
      }
      agent.vacations.push({ start: '', end: '' });
    },
    removeVacationPeriod(agent, periodIndex) {
      if (!Array.isArray(agent.vacations)) {
        return;
      }
      agent.vacations.splice(periodIndex, 1);
    },
    setVacationPeriod(agent, periodIndex, key, value) {
      if (!agent.vacations?.[periodIndex]) {
        return;
      }
      agent.vacations[periodIndex][key] = value;
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
        this.errorMessage = normalizeApiError(error, 'Erreur lors de la récupération de la semaine précédente');
      }
    },
    buildWeekScheduleBetweenDates(startDate, endDate) {
      const dayNames = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'];
      const result = [];
      const current = new Date(startDate);
      const end = new Date(endDate);
      while (current <= end) {
        const dayName = dayNames[current.getDay()];
        const day = String(current.getDate()).padStart(2, '0');
        const month = String(current.getMonth() + 1).padStart(2, '0');
        result.push(`${dayName}. ${day}-${month}`);
        current.setDate(current.getDate() + 1);
      }
      return result;
    },
    initializeManualGrid() {
      if (!this.startDate || !this.endDate || this.endDate < this.startDate) {
        this.manualWeekSchedule = [];
        this.manualSelectedShifts = {};
        return;
      }
      this.manualWeekSchedule = this.buildWeekScheduleBetweenDates(this.startDate, this.endDate);
      this.manualSelectedShifts = {};
      this.agents.forEach((agent) => {
        if (!agent?.name) return;
        this.manualSelectedShifts[agent.name] = {};
        this.manualWeekSchedule.forEach((day) => {
          this.manualSelectedShifts[agent.name][day] = '';
        });
      });
    },
    async generatePlanning() {
      this.resetMessages();
      this.resetPlanningData();

      if (!this.startDate || !this.endDate) {
        this.errorMessage = 'Veuillez sélectionner une date de début et une date de fin.';
        return;
      }

      const canProceed = await this.saveConfigIfNeeded();
      if (!canProceed) {
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
      if (this.isExistingOptimizationMode) {
        payload.manual_entries = [];
        Object.entries(this.manualSelectedShifts).forEach(([agent, days]) => {
          Object.entries(days || {}).forEach(([dayLabel, value]) => {
            if (!value) return;
            const [dayPart, monthPart] = dayLabel.split(' ')[1].split('-');
            const isStatus = value.startsWith('status:');
            payload.manual_entries.push({
              agent,
              date: `${this.startDate.slice(0, 4)}-${monthPart}-${dayPart}`,
              slot: 'day',
              type: isStatus ? 'status' : 'shift',
              value: isStatus ? value.replace('status:', '') : value
              })
            });
          });
        }

      this.isLoading = true;
      try {
        const endpoint = this.isExistingOptimizationMode ? '/optimize-existing-planning' : '/generate-planning';
        const response = await apiPost(endpoint, payload);
        this.planningResult = response.data.planning;
        this.vacationDurations = response.data.vacation_durations;
        this.weekSchedule = response.data.week_schedule;
        this.holidaysFromConfig = response.data.holidays;
        this.unavailableFromConfig = response.data.unavailable;
        this.dayOffFromConfig = response.data.dayOff;
        this.trainingFromConfig = response.data.training;
        this.restrictionsFromConfig = response.data.restrictions;
        this.restrictionDurationsFromConfig = response.data.restriction_types_durations || {};
        this.optimizationWarnings = response.data.warnings || [];
        this.optimizationSuggestions = response.data.suggestions || [];
        this.optimizationMeta = response.data.meta || null;
        this.optimizationStatus = response.data.status || null;
      } catch (error) {
        const responseData = error?.response?.data;
        if (responseData?.info) {
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
    },
    getManualCellClass(agentName, day) {
      const value = this.manualSelectedShifts?.[agentName]?.[day] || '';
      if (value.startsWith('status:')) return value.replace('status:', '');
      return '';
    },
    getManualCellStyle(agentName, day) {
      const value = this.manualSelectedShifts?.[agentName]?.[day] || '';
      if (!value || value.startsWith('status:')) return {};
      return { 
        backgroundColor: this.vacationColors[value] || '#ffffff'
      };
    },
    buildDayLabelFromIsoDate(isoDate) {
      if (!isoDate || typeof isoDate !== 'string') return null;
      const [yearRaw, monthRaw, dayRaw] = isoDate.split('-');
      const year = Number(yearRaw);
      const month = Number(monthRaw);
      const day = Number(dayRaw);
      const date = new Date(year, month - 1, day);
      if (Number.isNaN(date.getTime())) return null;
      const dayNames = ['Dim', 'Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam'];
      const dayName = dayNames[date.getDay()];
      return `${dayName}. ${String(day).padStart(2, '0')}-${String(month).padStart(2, '0')}`;
    },
    getWarningCellClass(agentName, dayLabel) {
      const hasWarning = (this.optimizationWarnings || []).some((warning) => {
        if (!warning || warning.agent !== agentName) return false;
        const warningDayLabel = this.buildDayLabelFromIsoDate(warning.date);
        return warningDayLabel === dayLabel;
      });
      return hasWarning ? 'warning-outline' : '';
    },
    hasClearCellProposal(suggestion) {
      return (suggestion?.proposals || []).some((proposal) => proposal?.action === 'clear_cell');
    },
    applyClearCellSuggestion(suggestion) {
      const agentName = suggestion?.agent;
      const dayLabel = this.buildDayLabelFromIsoDate(suggestion?.date);
      if (!agentName || !dayLabel) return;
      if (this.manualSelectedShifts?.[agentName] && dayLabel in this.manualSelectedShifts[agentName]) {
        this.manualSelectedShifts[agentName][dayLabel] = '';
      }
    },
    formatMonthTitle(month) {
      const monthMap = {
        '01': 'Janvier',
        '02': 'Février',
        '03': 'Mars',
        '04': 'Avril',
        '05': 'Mai',
        '06': 'Juin',
        '07': 'Juillet',
        '08': 'Août',
        '09': 'Septembre',
        '10': 'Octobre',
        '11': 'Novembre',
        '12': 'Décembre'
      };
      return monthMap[month] || month;
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

.mode-switch {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
}

.mode-btn {
  margin-bottom: 0;
}

.mode-btn.active {
  background-color: #0f4a8a;
}

.config-panel {
  border: 1px solid #d7e0eb;
  padding: 16px;
  border-radius: 10px;
  background: #fafcff;
}

.config-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.config-block {
  margin-top: 16px;
  padding-top: 10px;
  border-top: 1px solid #e5edf7;
}

.config-block input {
  width: 100%;
  max-width: 700px;
  margin: 4px 0 8px;
  padding: 8px;
}

.config-dirty {
  color: #9a6400;
  font-weight: bold;
}

.vacation-row {
  display: grid;
  grid-template-columns: 140px 70px 120px 130px 120px;
  gap: 8px;
  align-items: center;
  margin-top: 6px;
}

.vacation-row input {
  margin: 0;
  max-width: 120px;
}

.vacation-name {
  font-weight: bold;
}

.agent-card {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid #dce8f7;
  border-radius: 8px;
  background: white;
}

.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.danger-btn {
  background-color: #cc3d3d;
}

.danger-btn:hover {
  background-color: #9f2424;
}

.vacation-periods {
  margin-top: 8px;
}

.vacation-periods-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.vacation-period-row {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.vacation-period-row input {
  max-width: 180px;
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

.warning-card {
  background-color: #fff4e5;
  color: #9a6400;
  border: 1px solid #f0b35e;
  border-radius: 8px;
  padding: 12px 16px;
  margin: 12px 0;
}

.secondary-btn {
  margin-left: 10px;
  background: #6c757d;
  padding: 4px 8px;
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
.transition-table td.unavailable {
  background-color: #f2cb05;
}
.transition-table td.training {
  background-color: #d93030;
}
.transition-table td.vacations {
  background-color: #f2cb05;
}
.transition-table td.restriction {
  background-color: #ffd8a8;
}
.transition-table td.warning-outline {
  box-shadow: inset 0 0 0 2px #d93030;
}

.transition-table select {
  width: 100%;
  padding: 5px;
  border: none;
  background: transparent;
  font-size: 14px;
}

@media (max-width: 900px) {
  .vacation-row {
    grid-template-columns: 1fr;
    justify-items: start;
  }
}
</style>
