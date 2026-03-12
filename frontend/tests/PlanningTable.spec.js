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
      },
    });

    expect(wrapper.find('table').exists()).toBe(true);
    expect(wrapper.findAll('tr')).toHaveLength(2);
    expect(wrapper.text()).toContain('Agent1');
    expect(wrapper.text()).toContain('Jour');
    expect(wrapper.text()).toContain('8 h');
  });
});
