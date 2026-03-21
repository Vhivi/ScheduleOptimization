import { normalizeApiError } from '../src/apiClient';

describe('apiClient error normalization', () => {
  it('prefers backend error payload when available', () => {
    const err = { response: { data: { error: 'Invalid date format' } } };
    expect(normalizeApiError(err, 'Erreur')).toBe('Erreur : Invalid date format');
  });

  it('falls back to transport message', () => {
    const err = { message: 'Network Error' };
    expect(normalizeApiError(err, 'Erreur')).toBe('Erreur : Network Error');
  });

  it('falls back to unknown network error when empty', () => {
    expect(normalizeApiError({}, 'Erreur')).toBe('Erreur : Erreur réseau inconnue');
  });
});
