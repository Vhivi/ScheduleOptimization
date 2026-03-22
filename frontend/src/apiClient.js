import axios from 'axios';

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://127.0.0.1:5000';

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000
});

export function apiPost(path, payload) {
  return client.post(path, payload);
}

export function normalizeApiError(error, fallbackMessage) {
  const responseError = error?.response?.data?.error;
  const networkMessage = error?.message;
  const message = responseError || networkMessage || 'Erreur réseau inconnue';
  return `${fallbackMessage} : ${message}`;
}

export { API_BASE_URL };
