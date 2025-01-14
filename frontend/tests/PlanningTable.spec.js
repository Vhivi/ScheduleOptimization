import { shallowMount } from '@vue/test-utils';
import PlanningTable from '../src/components/PlanningTable.vue';

describe('PlanningTable.vue', () => {
    it('renders table when passed props', () => {
        const planning = [
            { day: '2024-11-01', agent: 'Agent1', vacation: 'Jour' },
            { day: '2024-11-02', agent: 'Agent2', vacation: 'Nuit' },
        ];
        const wrapper = shallowMount(PlanningTable, {
            props: { planning },
        });

        expect(wrapper.find('table').exists()).toBe(true);
        expect(wrapper.findAll('tr').length).toBe(planning.length + 1); // +1 for header
    });
});
