import { shallowMount } from '@vue/test-utils';
import PlanningTable from '../src/components/PlanningTable.vue';

describe('PlanningTable.vue', () => {
  it('renders the planning table with the current component props', () => {
    const wrapper = shallowMount(PlanningTable, {
      props: {
        planning: {
          Agent1: [['Lun. 01-11', 'Jour']],
        },
        weekSchedule: ['Lun. 01-11'],
        vacationDurations: {
          Jour: 8,
        },
        vacationColors: {
          Jour: '#75FA79',
        },
        holidays: [],
        unavailable: {
          Agent1: [],
        },
        dayOff: {
          Agent1: [],
        },
        training: {
          Agent1: [],
        },
        planningStartDate: '2026-11-01',
      },
    });

    expect(wrapper.find('table').exists()).toBe(true);
    expect(wrapper.findAll('tr')).toHaveLength(2);
    expect(wrapper.text()).toContain('Agent1');
    expect(wrapper.text()).toContain('Jour');
    expect(wrapper.text()).toContain('8 h');
  });

  it('marks leave correctly across year boundary using configured period years', () => {
    const wrapper = shallowMount(PlanningTable, {
      props: {
        planning: {
          Agent1: [['Mer. 31-12', 'Jour'], ['Jeu. 01-01', 'Nuit']],
        },
        weekSchedule: ['Mer. 31-12', 'Jeu. 01-01'],
        vacationDurations: {
          Jour: 8,
          Nuit: 8,
        },
        vacationColors: {
          Jour: '#75FA79',
          Nuit: '#9175FA',
        },
        holidays: [],
        unavailable: {
          Agent1: [],
        },
        dayOff: {
          Agent1: [['31-12-2025', '02-01-2026']],
        },
        training: {
          Agent1: [],
        },
        planningStartDate: '2025-12-31',
      },
    });

    expect(wrapper.text()).toContain('Con.');
    expect(wrapper.text()).not.toContain('Jour');
    expect(wrapper.text()).not.toContain('Nuit');
  });

  it('does not mark leave when day-month matches but leave year is different', () => {
    const wrapper = shallowMount(PlanningTable, {
      props: {
        planning: {
          Agent1: [['Mar. 01-04', 'Jour'], ['Mer. 02-04', 'Nuit']],
        },
        weekSchedule: ['Mar. 01-04', 'Mer. 02-04'],
        vacationDurations: {
          Jour: 8,
          Nuit: 8,
        },
        vacationColors: {
          Jour: '#75FA79',
          Nuit: '#9175FA',
        },
        holidays: [],
        unavailable: {
          Agent1: [],
        },
        dayOff: {
          Agent1: [['01-04-2025', '02-04-2025']],
        },
        training: {
          Agent1: [],
        },
        planningStartDate: '2026-04-01',
      },
    });

    expect(wrapper.text()).not.toContain('Con.');
    expect(wrapper.text()).toContain('Jour');
    expect(wrapper.text()).toContain('Nuit');
  });

  it('marks leave on weekend days included in leave period', () => {
    const wrapper = shallowMount(PlanningTable, {
      props: {
        planning: {
          Agent1: [['Sam. 18-04', 'Jour'], ['Dim. 19-04', 'Nuit']],
        },
        weekSchedule: ['Sam. 18-04', 'Dim. 19-04'],
        vacationDurations: {
          Jour: 8,
          Nuit: 8,
        },
        vacationColors: {
          Jour: '#75FA79',
          Nuit: '#9175FA',
          'Con.': '#f2cb05',
        },
        holidays: [],
        unavailable: {
          Agent1: [],
        },
        dayOff: {
          Agent1: [['18-04-2026', '19-04-2026']],
        },
        training: {
          Agent1: [],
        },
        planningStartDate: '2026-04-18',
      },
    });

    const text = wrapper.text();
    expect(text.match(/Con\./g)?.length || 0).toBeGreaterThanOrEqual(2);
    expect(text).not.toContain('Jour');
    expect(text).not.toContain('Nuit');
  });
});
