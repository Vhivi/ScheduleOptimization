import { shallowMount } from '@vue/test-utils';
import App from '../src/App.vue';

jest.mock('../src/apiClient', () => ({
  apiGet: jest.fn(() => Promise.resolve({
    data: {
      agents: [],
      vacations: ['Jour', 'Nuit'],
      vacation_durations: {
        Jour: 12,
        Nuit: 12,
        Conge: 7,
      },
      staffing_requirements: {
        Jour: 1,
        Nuit: 1,
      },
      holidays: [],
      solver: {},
      half_vacations: {},
      vacation_colors: {},
    },
  })),
  apiPost: jest.fn(),
  apiPut: jest.fn(),
  normalizeApiError: jest.fn((error, fallback) => fallback),
}));

describe('App.vue', () => {
  it('renders modified existing assignments with labels', async () => {
    const wrapper = shallowMount(App, {
      global: {
        stubs: {
          PlanningTable: true,
        },
      },
    });

    await Promise.resolve();
    await wrapper.vm.$nextTick();

    await wrapper.setData({
      activeMode: 'planning',
      generationMode: 'existing',
      assignmentLabels: {
        'Jour matin': 'J matin',
      },
      optimizationModifiedAssignments: [
        {
          agent: 'Agent1',
          date: '2026-01-05',
          initial_value: 'Jour matin',
          final_value: 'Nuit',
          change_type: 'changed_to_full',
        },
      ],
    });

    const text = wrapper.text();
    expect(text).toContain('Agent1');
    expect(text).toContain('J matin');
    expect(text).toContain('Nuit');
    expect(text).toContain('2026-01-05');
  });
});
