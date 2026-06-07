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
  beforeEach(() => {
    jest.clearAllMocks();
  });

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

  it('renders half-vacation config only for splittable vacations', async () => {
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
      activeMode: 'config',
      configData: {
        agents: [],
        vacations: ['Jour', 'CDP'],
        vacation_durations: {
          Jour: 12,
          CDP: 5.5,
          Conge: 7,
        },
        staffing_requirements: {
          Jour: 1,
          CDP: 1,
        },
        holidays: [],
        solver: {},
        half_vacations: {},
        vacation_colors: {},
      },
    });

    expect(wrapper.findAll('.half-vacation-card')).toHaveLength(1);
    expect(wrapper.text()).toContain('Jour');
    expect(wrapper.text()).toContain("CDP n'est pas decoupable.");
  });

  it('normalizes half-vacations payload and excludes CDP', async () => {
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
      vacationsInput: 'Jour, CDP',
      holidaysInput: '',
      configData: {
        agents: [],
        vacations: ['Jour', 'CDP'],
        vacation_durations: {
          Jour: 12,
          CDP: 5.5,
          Conge: 7,
        },
        staffing_requirements: {
          Jour: 1,
          CDP: 1,
        },
        holidays: [],
        solver: {},
        half_vacations: {
          Jour: {
            enabled: true,
            penalty: 500,
            segments: [
              {
                name: 'Jour matin',
                label: 'J matin',
                duration: 6,
                is_night: false,
                requires_next_day_rest: false,
              },
              {
                name: 'Jour apres-midi',
                label: 'J aprem',
                duration: 6,
                is_night: false,
                requires_next_day_rest: false,
              },
            ],
          },
          CDP: {
            enabled: true,
            penalty: 100,
            segments: [
              { name: 'CDP 1', duration: 2.75 },
              { name: 'CDP 2', duration: 2.75 },
            ],
          },
          Nuit: {
            enabled: false,
            penalty: 700,
            segments: [],
          },
        },
        vacation_colors: {
          'Jour matin': '#B9F6CA',
          'Jour apres-midi': '#00C853',
        },
      },
    });

    const payload = wrapper.vm.buildConfigPayload();

    expect(Object.keys(payload.half_vacations)).toEqual(['Jour']);
    expect(payload.half_vacations.Jour.segments).toEqual([
      { name: 'Jour matin', duration: 6, label: 'J matin' },
      { name: 'Jour apres-midi', duration: 6, label: 'J aprem' },
    ]);
    expect(payload.vacation_colors).toEqual({
      'Jour matin': '#B9F6CA',
      'Jour apres-midi': '#00C853',
    });
  });

  it('renders structured blocking reason segments', async () => {
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
      optimizationBlockingReasons: [
        {
          code: 'STAFFING_REQUIREMENT_UNMET',
          message: 'Le besoin de couverture ne peut pas etre atteint.',
          count: 1,
          segments: [
            {
              date: '2026-01-15',
              vacation: 'Jour',
              segment: 'Jour matin',
              required_agents: 2,
              eligible_agents: 0,
              blockers: {
                status: 2,
                parent_restriction: 1,
              },
              actions: ['free_agent', 'reduce_staffing_requirement'],
              sample_blocked_agents: [
                {
                  agent: 'Agent1',
                  reasons: ['status'],
                },
              ],
            },
          ],
        },
      ],
    });

    const text = wrapper.text();
    expect(text).toContain('2026-01-15 / Jour / Jour matin');
    expect(text).toContain('Besoin: 2');
    expect(text).toContain('Agents possibles: 0');
    expect(text).toContain('statut bloquant (2)');
    expect(text).toContain('restriction parent (1)');
    expect(text).toContain('liberer un agent');
    expect(text).toContain('reduire le besoin de couverture');
    expect(text).toContain('Agent1: statut bloquant');
  });
});
