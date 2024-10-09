<template>
    <div>
      <h1>Configuration</h1>
      <pre>{{ configData }}</pre>
    </div>
  </template>
  
  <script>
  import axios from 'axios';
  
  export default {
    data() {
      return {
        configData: null, // Variable pour stocker la réponse de l'API
      };
    },
    mounted() {
      // Cette méthode est appelée lorsque le composant est monté
      this.getConfig();
    },
    methods: {
      async getConfig() {
        try {
          // Faire une requête GET vers ton serveur Flask
          const response = await axios.get('http://127.0.0.1:5000/config');
          this.configData = response.data; // Stocker la réponse dans data
        } catch (error) {
          console.error('Erreur lors de la récupération de la configuration:', error);
        }
      },
    },
  };
  </script>
  