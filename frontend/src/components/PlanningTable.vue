<template>
    <div>
      <h1>Planning des Vacations</h1>
      <table>
        <thead>
          <tr>
            <th>Agent</th>
            <th v-for="day in weekSchedule" :key="day">{{ day }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(agent, index) in Object.keys(planning)" :key="index">
            <td>{{ agent }}</td>
            <td v-for="day in weekSchedule" :key="day">
              <!-- On affiche la vacation de cet agent ce jour-là -->
              {{ getVacationForAgent(agent, day) || '//' }}
            </td>
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
      }
    },
    methods: {
      getVacationForAgent(agent, day) {
        // Chercher la vacation de cet agent pour ce jour
        const vacationForDay = this.planning[agent].find(vac => vac[0] === day);
        return vacationForDay ? vacationForDay[1] : null; // Retourne la vacation ou null si pas de vacation
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
    background-color: #f4f4f4;
  }
  </style>
  