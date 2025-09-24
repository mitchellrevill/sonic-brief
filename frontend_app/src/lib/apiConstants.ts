const BASE_URL = import.meta.env.VITE_API_URL || '';

// Root endpoints
export const ROOT_API = `${BASE_URL}/`;
export const ECHO_API = `${BASE_URL}/echo`;

// Auth / User management
export const AUTH_API = `${BASE_URL}/api/auth`;
export const LOGIN_API = `${AUTH_API}/login`;
export const MICROSOFT_SSO_API = `${AUTH_API}/microsoft-sso`;
export const REGISTER_API = `${AUTH_API}/users/register`;
export const USER_MANAGEMENT_API = `${AUTH_API}/users`;
export const MY_PERMISSIONS_API = `${USER_MANAGEMENT_API}/me/permissions`;
export const USER_PERMISSIONS_API = (userId: string) => `${USER_MANAGEMENT_API}/${userId}/permission`;
export const USER_CAPABILITIES_API = (userId: string) => `${USER_MANAGEMENT_API}/${userId}/capabilities`;
export const USER_DETAILS_API = (userId: string) => `${USER_MANAGEMENT_API}/${userId}`;

// Prompts (categories & subcategories)
export const PROMPTS_BASE = `${BASE_URL}/api/prompts`;
export const CATEGORIES_API = `${PROMPTS_BASE}/categories`;
export const CATEGORY_BY_ID = (categoryId: string) => `${CATEGORIES_API}/${categoryId}`;
export const SUBCATEGORIES_API = `${PROMPTS_BASE}/subcategories`;
export const SUBCATEGORY_BY_ID = (subcategoryId: string) => `${SUBCATEGORIES_API}/${subcategoryId}`;
export const PROMPTS_RETRIEVE_API = `${PROMPTS_BASE}/retrieve_prompts`;
// Backwards-compatible alias (older code imports `PROMPTS_API`)
export const PROMPTS_API = PROMPTS_RETRIEVE_API;

// Jobs
export const JOBS_API = `${BASE_URL}/api/jobs`;
export const JOB_BY_ID = (jobId: string) => `${JOBS_API}/${jobId}`;
export const JOB_TRANSCRIPTION_API = (jobId: string) => `${JOBS_API}/${jobId}/transcription`;
export const JOB_SHARE_API = (jobId: string) => `${JOBS_API}/${jobId}/share`;
export const JOB_SHARING_INFO_API = (jobId: string) => `${JOBS_API}/${jobId}/sharing`;
export const SHARED_JOBS_API = `${JOBS_API}/shared`;
export const JOB_RESTORE_API = (jobId: string) => `${JOBS_API}/${jobId}/restore`;

// Admin / job-admin
export const ADMIN_JOBS_API = `${BASE_URL}/api/admin/jobs`;
export const ADMIN_DELETED_JOBS_API = `${ADMIN_JOBS_API}/deleted`;
export const ADMIN_JOB_RESTORE_API = (jobId: string) => `${ADMIN_JOBS_API}/${jobId}/restore`;
export const ADMIN_JOB_PERMANENT_DELETE_API = (jobId: string) => `${ADMIN_JOBS_API}/${jobId}/permanent`;
export const ADMIN_JOB_REPROCESS_API = (jobId: string) => `${ADMIN_JOBS_API}/${jobId}/reprocess`;
export const ADMIN_USER_JOBS_API = (userId: string) => `${ADMIN_JOBS_API}/user/${userId}`;
export const ADMIN_JOBS_STATS_API = `${ADMIN_JOBS_API}/stats`;

// Analytics
export const ANALYTICS_API = `${BASE_URL}/api/analytics`;
export const SYSTEM_ANALYTICS_API = `${ANALYTICS_API}/system`;
export const ANALYTICS_DASHBOARD_API = `${ANALYTICS_API}/dashboard`;
export const USER_ANALYTICS_API = `${ANALYTICS_API}/users`;
export const USER_MINUTES_API = (userId: string) => `${USER_ANALYTICS_API}/${userId}/minutes`;
export const SESSION_TRACKING_API = `${ANALYTICS_API}/session`;
export const ACTIVE_USERS_API = `${ANALYTICS_API}/active-users`;
export const USER_SESSION_DURATION_API = `${ANALYTICS_API}/user-session-duration`;

// System health / readiness
export const SYSTEM_HEALTH_API = `${BASE_URL}/api/system/health`;
export const HEALTH_ROOT = `${BASE_URL}/health/`;
export const HEALTH_READY = `${BASE_URL}/health/ready`;

// Export APIs
export const EXPORT_BASE_API = `${BASE_URL}/api/analytics/export`;
export const EXPORT_SYSTEM_CSV_API = `${EXPORT_BASE_API}/system/csv`;
export const EXPORT_USERS_API = `${EXPORT_BASE_API}/users`;
export const EXPORT_USERS_FORMAT_API = (format: string) => `${EXPORT_USERS_API}/${format}`;
export const EXPORT_USER_PDF_API = (userId: string) => `${EXPORT_USERS_API}/${userId}/pdf`;

// Backwards-compatible / misc
export const UPLOAD_API = `${BASE_URL}/api/upload`;
export const TRANSCRIPTION_API = (jobId: string) => `${JOBS_API}/${jobId}/transcription`;

// Convenience alias
export const ADMIN_JOBS_LISTING = ADMIN_JOBS_API;
// Backwards-compatible alias name used in some files
export const ADMIN_PERMANENT_DELETE_API = ADMIN_JOB_PERMANENT_DELETE_API;