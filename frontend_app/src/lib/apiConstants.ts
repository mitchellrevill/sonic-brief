// create .env file and add the following vars, it should be in the root of the project and it should be ignored by git:
// VITE_API_URL

const BASE_URL = import.meta.env.VITE_API_URL;

export const REGISTER_API = `${BASE_URL}/register`;
export const UPLOAD_API = `${BASE_URL}/upload`;
export const JOBS_API = `${BASE_URL}/jobs`;
export const LOGIN_API = `${BASE_URL}/login`;
export const CATEGORIES_API = `${BASE_URL}/categories`;
export const SUBCATEGORIES_API = `${BASE_URL}/subcategories`;
export const PROMPTS_API = `${BASE_URL}/retrieve_prompts`;
export const TRANSCRIPTION_API = `${BASE_URL}/jobs/transcription`;
