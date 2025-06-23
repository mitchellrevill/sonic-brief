// create .env file and add the following vars, it should be in the root of the project and it should be ignored by git:
// VITE_API_URL

const BASE_URL = import.meta.env.VITE_API_URL;

export const REGISTER_API = `${BASE_URL}/api/auth/register`;
export const UPLOAD_API = `${BASE_URL}/api/upload`;
export const JOBS_API = `${BASE_URL}/api/jobs`;
export const LOGIN_API = `${BASE_URL}/api/auth/login`;
export const CATEGORIES_API = `${BASE_URL}/api/categories`;
export const SUBCATEGORIES_API = `${BASE_URL}/api/subcategories`;
export const PROMPTS_API = `${BASE_URL}/api/retrieve_prompts`;
export const TRANSCRIPTION_API = `${BASE_URL}/api/jobs/transcription`;
export const USER_MANAGEMENT_API = `${BASE_URL}/api/auth/users`;

// Job Sharing APIs
export const JOB_SHARE_API = `${BASE_URL}/api/jobs`;
export const SHARED_JOBS_API = `${BASE_URL}/api/jobs/shared`;

// Job Soft Delete APIs
export const JOB_DELETE_API = `${BASE_URL}/api/jobs`;
export const ADMIN_DELETED_JOBS_API = `${BASE_URL}/api/admin/deleted-jobs`;
export const ADMIN_PERMANENT_DELETE_API = `${BASE_URL}/api/admin/jobs`;