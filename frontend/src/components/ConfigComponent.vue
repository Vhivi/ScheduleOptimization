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
      try {
        const response = await axios.post('http://127.0.0.1:5000/generate-planning', {
          start_date: '2024-10-11',
          end_date: '2024-10-20',
        }
        );
        this.planningResult = response.data;
      } catch (error) {
        console.error('Erreur lors de la génération du planning :', error);
      }
    },
  },
};
</script>
