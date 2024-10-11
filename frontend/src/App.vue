<template>
  <div id="app">
    <button @click="generatePlanning">Générer le planning</button>

    <!-- Afficher le tableau uniquement lorsque planningResult est défini -->
    <div v-if="planningResult">
      <PlanningTable :planning="planningResult" :weekSchedule="weekSchedule" />
    </div>
    <div v-else>
      <p>Le planning n'est pas encore généré.</p>
    </div>
  </div>
</template>

<script>
import axios from 'axios';
import PlanningTable from './components/PlanningTable.vue';

export default {
  components: {
    PlanningTable
  },
  data() {
    return {
      planningResult: null, // Initialement, aucun planning n'est défini
      weekSchedule: ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
    };
  },
  methods: {
    async generatePlanning() {
      try {
        // Envoyer la requête à Flask pour générer le planning
        const response = await axios.post('http://127.0.0.1:5000/generate-planning');
        this.planningResult = response.data; // Stocker les données dans planningResult
      } catch (error) {
        console.error('Erreur lors de la génération du planning :', error);
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
</style>
