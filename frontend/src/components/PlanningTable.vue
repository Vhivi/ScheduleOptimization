<template>
  <div>
    <h1>Planning des Vacations</h1>

    <div
      v-for="(monthDays, monthKey) in splitByMonth(weekSchedule)"
      :key="monthKey"
      class="month-table"
    >
      <h2>{{ formatMonthTitle(monthKey) }}</h2>
      <table>
        <thead>
          <tr>
            <th>Agent</th>
            <th v-for="day in monthDays" :key="day">{{ day }}</th>
            <th>Total Vacations</th>
            <th>Total Heures</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(agent, index) in Object.keys(planning)" :key="index">
            <td>{{ agent }}</td>
            <td v-for="day in monthDays" :key="day" :style="{ backgroundColor: getColumnColor(agent, day) }">
              {{ getVacationForAgent(agent, day) || '//' }}
            </td>
            <td>{{ calculateNumberShifts(agent, monthDays) }}</td>
            <td>{{ calculateTotalHours(agent, monthDays) }} h</td>
          </tr>
        </tbody>
      </table>
    </div>
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
    },
    vacationDurations: {
      type: Object,
      required: true
    },
    vacationColors: {
      type: Object,
      required: true
    },
    holidays: {
      type: Array,
      required: true
    },
    unavailable: {
      type: Object,
      required: true
    },
    dayOff: {
      type: Object,
      required: true
    },
    training: {
      type: Object,
      required: true
    }
  },
  computed: {
    planningLookup() {
      const lookup = {};
      Object.entries(this.planning || {}).forEach(([agent, vacations]) => {
        lookup[agent] = {};
        if (Array.isArray(vacations)) {
          vacations.forEach((entry) => {
            if (Array.isArray(entry) && entry.length === 2) {
              lookup[agent][entry[0]] = entry[1];
            }
          });
        } else if (vacations && typeof vacations === 'object') {
          Object.entries(vacations).forEach(([day, vacation]) => {
            lookup[agent][day] = vacation;
          });
        }
      });
      return lookup;
    }
  },
  methods: {
    splitByMonth(weekSchedule) {
      if (!Array.isArray(weekSchedule)) {
        return {};
      }
      return weekSchedule.reduce((months, day) => {
        const dayPart = this.getDayPart(day);
        const monthKey = dayPart ? dayPart.split('-')[1] : '??';
        if (!months[monthKey]) {
          months[monthKey] = [];
        }
        months[monthKey].push(day);
        return months;
      }, {});
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
    },
    getDayPart(dayLabel) {
      const parts = (dayLabel || '').split(' ');
      return parts.length > 1 ? parts[1] : null;
    },
    isWeekendLabel(dayLabel) {
      return dayLabel.includes('Sam') || dayLabel.includes('Dim');
    },
    parseConfigDate(dateStr) {
      if (!dateStr || typeof dateStr !== 'string' || dateStr.length !== 10) {
        return null;
      }
      const day = Number(dateStr.slice(0, 2));
      const month = Number(dateStr.slice(3, 5));
      const year = Number(dateStr.slice(6, 10));
      const date = new Date(year, month - 1, day);
      if (
        Number.isNaN(date.getTime()) ||
        date.getFullYear() !== year ||
        date.getMonth() !== month - 1 ||
        date.getDate() !== day
      ) {
        return null;
      }
      return date;
    },
    formatDayMonth(date) {
      const day = String(date.getDate()).padStart(2, '0');
      const month = String(date.getMonth() + 1).padStart(2, '0');
      return `${day}-${month}`;
    },
    getVacationForAgent(agent, day) {
      if (this.isTrainingDay(agent, day)) {
        return 'For.';
      }
      if (this.isVacationDay(agent, day)) {
        return 'Con.';
      }
      if (this.isUnavailable(agent, day)) {
        return 'Ind.';
      }
      return this.planningLookup?.[agent]?.[day] || null;
    },
    isVacationDay(agent, day) {
      const vacations = this.dayOff?.[agent] || [];
      const dayPart = this.getDayPart(day);
      if (!dayPart || this.isWeekendLabel(day)) {
        return false;
      }

      for (let i = 0; i < vacations.length; i += 1) {
        const period = vacations[i];
        if (!period || period.length < 2) {
          continue;
        }
        const vacationStartDate = this.parseConfigDate(period[0]);
        const vacationEndDate = this.parseConfigDate(period[1]);
        if (!vacationStartDate || !vacationEndDate || vacationStartDate > vacationEndDate) {
          continue;
        }

        const cursor = new Date(vacationStartDate);
        while (cursor <= vacationEndDate) {
          if (this.formatDayMonth(cursor) === dayPart) {
            return true;
          }
          cursor.setDate(cursor.getDate() + 1);
        }
      }
      return false;
    },
    isUnavailable(agent, day) {
      const unavailableDays = this.unavailable?.[agent] || [];
      const dayPart = this.getDayPart(day);
      if (!dayPart) {
        return false;
      }
      const formattedUnavailableDays = unavailableDays.map((date) => date.slice(0, 5));
      return formattedUnavailableDays.includes(dayPart);
    },
    getVacationColor(agent, day) {
      const vacation = this.getVacationForAgent(agent, day);
      return vacation ? this.vacationColors[vacation] : 'white';
    },
    isHoliday(day) {
      if (this.holidays && Array.isArray(this.holidays)) {
        const datePart = this.getDayPart(day);
        return datePart ? this.holidays.includes(datePart) : false;
      }
      return false;
    },
    isTrainingDay(agent, day) {
      const trainingDays = this.training?.[agent] || [];
      const datePart = this.getDayPart(day);
      if (!datePart) {
        return false;
      }
      const formattedTrainingDays = trainingDays.map((date) => date.slice(0, 5));
      return formattedTrainingDays.includes(datePart);
    },
    getColumnColor(agent, day) {
      if (this.isVacationDay(agent, day)) {
        return '#f2cb05';
      }
      if (this.isUnavailable(agent, day)) {
        return '#f2cb05';
      }
      if (this.isTrainingDay(agent, day)) {
        return '#D93030';
      }

      const vacationColor = this.getVacationColor(agent, day);
      if (vacationColor && vacationColor !== 'white') {
        return vacationColor;
      }

      if (this.isHoliday(day) || this.isWeekendLabel(day)) {
        return '#dedede';
      }
      return 'white';
    },
    calculateTotalHours(agent, days) {
      return days.reduce((total, day) => {
        const vacation = this.getVacationForAgent(agent, day);
        return total + (this.vacationDurations[vacation] || 0);
      }, 0);
    },
    calculateNumberShifts(agent, days) {
      return days.filter((day) => this.getVacationForAgent(agent, day)).length;
    }
  }
};
</script>

<style scoped>
.month-table {
  margin-bottom: 20px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  border: 1px solid black;
  padding: 8px;
  text-align: center;
}

th {
  background-color: #dedede;
}
</style>
