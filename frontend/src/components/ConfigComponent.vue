<template>
  <div>
    <h1>Générer Planning</h1>
    <button @click="generatePlanning">Générer</button>
    <pre>{{ planningResult }}</pre>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      planningResult: null,
    };
  },
  methods: {
    async generatePlanning() {
      const payload = {
        agents: ["Agent1", "Agent2"], // Exemple de données
        vacations: ["Jour", "Nuit"],
        week_schedule: ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
      };

      try {
        const response = await axios.post('http://127.0.0.1:5000/generate-planning', payload);
        this.planningResult = response.data;
      } catch (error) {
        console.error('Erreur lors de la génération du planning :', error);
      }
    },
  },
};
</script>
