import {
  ADMIN_DELETED_JOBS_API,
  ADMIN_PERMANENT_DELETE_API,
  ADMIN_JOBS_API,
  CATEGORIES_API,

  LOGIN_API,
  PROMPTS_API,
  REGISTER_API,
  SHARED_JOBS_API,
  SUBCATEGORIES_API,

  USER_MANAGEMENT_API,
  USER_ANALYTICS_API,
  SYSTEM_ANALYTICS_API,
  ANALYTICS_API,
  ANALYTICS_DASHBOARD_API,
  EXPORT_USERS_API,
  SESSION_TRACKING_API,
  ACTIVE_USERS_API,
  USER_SESSION_DURATION_API,
  JOBS_API,
  SYSTEM_HEALTH_API
} from "../lib/apiConstants"
import { PermissionLevel, type UserCapabilities } from "../types/permissions"

interface RegisterResponse {
  status: number
  message: string
}

interface LoginResponse {
  status: number
  message: string
  access_token: string
  token_type: string
  permission?: string // Added optional permission property
}

interface UploadResponse {
  job_id?: string
  status: number | string
  message: string
}

interface Prompt {
  [key: string]: string
}

interface Subcategory {
  subcategory_name: string
  subcategory_id: string
  prompts: Prompt
}

interface Category {
  category_name: string
  category_id: string
  subcategories: Array<Subcategory>
}

interface PromptsResponse {
  status: number
  data: Array<Category>
}

interface CategoryResponse {
  category_id: string
  name: string
  created_at: string
  updated_at: string
}

interface SubcategoryResponse {
  id: string
  name: string
  category_id: string
  prompts: Prompt
  created_at: number
  updated_at: number
}

interface JobSharingInfo {
  status: string;
  job_id: string;
  is_owner: boolean;
  user_permission: string;
  shared_with: Array<{
    user_id: string;
    user_email: string;
    permission_level: string;
    shared_at: number;
    shared_by: string;
    message?: string;
  }>;
  total_shares: number;
}

export async function registerUser(email: string, password: string): Promise<RegisterResponse> {
  const token = localStorage.getItem("token");
  if (!token) {
    throw new Error("You must be logged in as an admin to register a new user. Please log in and try again.");
  }
  const response = await fetch(REGISTER_API, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ email, password, permission: PermissionLevel.USER }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json()
}

export async function loginUser(email: string, password: string): Promise<LoginResponse> {
  const response = await fetch(LOGIN_API, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email, password }),
  })

  const data: LoginResponse = await response.json()

  if (!response.ok) {
    return {
      status: response.status,
      message: data.message || "An error occurred during login",
      access_token: "",
      token_type: "",
    }
  }

  // Track successful login event using analytics service
  if (data.access_token) {
    // Set token temporarily to track the login event
    const previousToken = localStorage.getItem("token");
    localStorage.setItem("token", data.access_token);
    
    // Import analytics service dynamically to avoid circular dependencies
    import('./analyticsService').then(({ trackUserLogin }) => {
      trackUserLogin({
        loginMethod: "email_password",
        userAgent: navigator.userAgent
      });
    }).catch(err => console.debug('Login analytics tracking failed:', err));

    // Restore previous token state if needed
    if (!previousToken) {
      // Token will be set properly by the calling code
    }
  }

  return data
}

export type User = {
  id: string;
  name: string;
  email: string;
  permission: PermissionLevel;
  capabilities: string[];
  custom_capabilities?: UserCapabilities;
  transcription_method?: "AZURE_AI_SPEECH" | "GPT4O_AUDIO";
  date?: string;
};



export async function fetchAllUsers(): Promise<User[]> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(USER_MANAGEMENT_API, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const data = await response.json();
  
  // Handle wrapped response format from backend
  if (data.status === 200 && Array.isArray(data.users)) {
    return data.users;
  } else if (Array.isArray(data)) {
    return data;
  } else {
    throw new Error("Invalid response format from server");
  }
}

export async function fetchUserByEmail(email: string): Promise<User> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${USER_MANAGEMENT_API}/by-email?email=${encodeURIComponent(email)}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
  }

  const data = await response.json();
  if (data.status !== 200) {
    throw new Error(data.message || "Failed to fetch user by email");
  }
  return data.user;
}

export async function fetchUserById(userId: string): Promise<User> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${USER_MANAGEMENT_API}/${userId}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const data = await response.json();
  if (data.status !== 200) {
    throw new Error(data.message || "Failed to fetch user");
  }
  return data.user;
}

export async function uploadFile(
  file: File,
  prompt_category_id: string,
  prompt_subcategory_id: string,
  preSessionFormData?: Record<string, any>,
  token?: string,
): Promise<UploadResponse> {
  if (!token) {
    token = localStorage.getItem("token") || undefined;
    if (!token) throw new Error("No authentication token found. Please log in again.");
  }
  const formData = new FormData();
  formData.append("file", file);
  formData.append("prompt_category_id", prompt_category_id);
  formData.append("prompt_subcategory_id", prompt_subcategory_id);
  
  // Add pre-session form data if provided
  if (preSessionFormData && Object.keys(preSessionFormData).length > 0) {
    formData.append("pre_session_form_data", JSON.stringify(preSessionFormData));
  }
  const response = await fetch(JOBS_API, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
  const data: UploadResponse = await response.json();
  if (!response.ok) {
    throw new Error(data.message || `HTTP error! status: ${response.status}`);
  }

  // Track analytics event for successful job creation using the analytics service
  if (response.ok && data.job_id) {
    // Import analytics service dynamically to avoid circular dependencies
    import('./analyticsService').then(({ trackJobCreated }) => {
      trackJobCreated(data.job_id!, {
        hasFile: true,
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type,
        categoryId: prompt_category_id,
        subcategoryId: prompt_subcategory_id,
        // Estimate audio duration if it's an audio file (rough estimate based on file size)
        estimatedDurationMinutes: file.type.startsWith('audio/') ? Math.max(1, file.size / (1024 * 1024) * 2) : undefined
      });
    }).catch(err => console.debug('Analytics tracking failed:', err));
  }

  return data;
}

export async function fetchPrompts(): Promise<PromptsResponse> {
  const token = localStorage.getItem("token")
  if (!token) {
    throw new Error("No authentication token found. Please log in again.")
  }

  const response = await fetch(PROMPTS_API, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  return await response.json()
}
export async function deleteUser(userId: string): Promise<{ status: number; message: string; data?: any }> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${USER_MANAGEMENT_API}/${userId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || data.message || `HTTP error! status: ${response.status}`);
  }

  return data;
}

export async function updateUserPermission(userId: string, permission: PermissionLevel): Promise<User> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${USER_MANAGEMENT_API}/${userId}`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ permission }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
  }

  return await response.json();
}

export async function changeUserPassword(userId: string, newPassword: string): Promise<{ status: number; message: string }> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${USER_MANAGEMENT_API}/${userId}/password`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ new_password: newPassword }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.message || `HTTP error! status: ${response.status}`);
  }

  return data;
}

export async function updateUserTranscriptionMethod(
  userId: string, 
  transcriptionMethod: "AZURE_AI_SPEECH" | "GPT4O_AUDIO"
): Promise<{ status: number; message: string; data: { user_id: string; transcription_method: string; updated_at: string } }> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${USER_MANAGEMENT_API}/${userId}/transcription-method`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ transcription_method: transcriptionMethod }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
  }

  return await response.json();
}

export async function createCategory(name: string): Promise<CategoryResponse> {
  const token = localStorage.getItem("token")
  if (!token) {
    throw new Error("No authentication token found. Please log in again.")
  }

  const response = await fetch(CATEGORIES_API, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ name }),
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  return await response.json()
}

export async function fetchCategories(): Promise<Array<CategoryResponse>> {
  const token = localStorage.getItem("token")
  if (!token) {
    throw new Error("No authentication token found. Please log in again.")
  }

  const response = await fetch(CATEGORIES_API, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  return await response.json()
}

export async function updateCategory(categoryId: string, name: string): Promise<CategoryResponse> {
  if (!categoryId) {
    console.error("Category ID is undefined or empty");
    throw new Error("Invalid category ID. Cannot update category.");
  }

  const token = localStorage.getItem("token")
  if (!token) {
    throw new Error("No authentication token found. Please log in again.")
  }

  console.log("Updating category with ID:", categoryId);
  console.log("New name:", name);
  console.log("Using token:", token.substring(0, 15) + "...");

  try {
    const response = await fetch(`${CATEGORIES_API}/${categoryId}`, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ name }),
    });

    console.log("Update category response status:", response.status);

    if (!response.ok) {
      if (response.status === 401) {
        console.error("Authentication failed (401). Token may be invalid or expired.");
        localStorage.removeItem("token"); // Clear invalid token
        throw new Error("Authentication failed. Please log in again.");
      }

      const errorText = await response.text();
      console.error("Error response body:", errorText);
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error updating category:", error);
    throw error;
  }
}

export async function deleteCategory(categoryId: string): Promise<void> {
  const token = localStorage.getItem("token")
  if (!token) {
    throw new Error("No authentication token found. Please log in again.")
  }

  const response = await fetch(`${CATEGORIES_API}/${categoryId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
}

// Functions for subcategory management
export async function createSubcategory(
  name: string,
  categoryId: string,
  prompts: Record<string, string>,
): Promise<SubcategoryResponse> {
  const token = localStorage.getItem("token")
  if (!token) {
    throw new Error("No authentication token found. Please log in again.")
  }

  const response = await fetch(SUBCATEGORIES_API, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name,
      category_id: categoryId,
      prompts,
    }),
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  return await response.json()
}

export async function fetchSubcategories(categoryId?: string): Promise<Array<SubcategoryResponse>> {
  const token = localStorage.getItem("token")
  if (!token) {
    throw new Error("No authentication token found. Please log in again.")
  }

  const url = categoryId ? `${SUBCATEGORIES_API}?category_id=${categoryId}` : SUBCATEGORIES_API

  const response = await fetch(url, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  return await response.json()
}

export async function updateSubcategory(
  subcategoryId: string,
  name: string,
  prompts: Record<string, string>,
): Promise<SubcategoryResponse> {
  const token = localStorage.getItem("token")
  if (!token) {
    throw new Error("No authentication token found. Please log in again.")
  }

  if (!subcategoryId) {
    console.error("Subcategory ID is undefined or empty");
    throw new Error("Invalid subcategory ID. Cannot update subcategory.");
  }

  console.log("Updating subcategory with ID:", subcategoryId);
  console.log("New name:", name);
  console.log("New prompts:", prompts);
  console.log("Using token:", token.substring(0, 15) + "...");

  try {
    const response = await fetch(`${SUBCATEGORIES_API}/${subcategoryId}`, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name,
        prompts,
      }),
    });

    console.log("Update subcategory response status:", response.status);

    if (!response.ok) {
      if (response.status === 401) {
        console.error("Authentication failed (401). Token may be invalid or expired.");
        localStorage.removeItem("token"); // Clear invalid token
        throw new Error("Authentication failed. Please log in again.");
      }

      if (response.status === 404) {
        console.error("Subcategory not found (404).");
        throw new Error("Subcategory not found. It may have been already deleted.");
      }

      const errorText = await response.text();
      console.error("Error response body:", errorText);
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
    }

    const data = await response.json();
    console.log("Update subcategory response:", data);
    return data;
  } catch (error) {
    console.error("Error updating subcategory:", error);
    throw error;
  }
}

export async function deleteSubcategory(subcategoryId: string): Promise<void> {
  const token = localStorage.getItem("token");
  if (!token) {
    throw new Error("No authentication token found. Please log in again.");
  }

  if (!subcategoryId || typeof subcategoryId !== "string") {
    console.error("Invalid subcategory ID:", subcategoryId);
    throw new Error("Invalid subcategory ID. Cannot delete subcategory.");
  }

  console.log("Deleting subcategory with ID:", subcategoryId);
  console.log("Using token:", token.substring(0, 15) + "...");

  try {
    const response = await fetch(`${SUBCATEGORIES_API}/${subcategoryId}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      }
    });

    console.log("Delete subcategory response status:", response.status);

    if (!response.ok) {
      if (response.status === 401) {
        console.error("Authentication failed (401). Token may be invalid or expired.");
        localStorage.removeItem("token"); // Clear invalid token
        throw new Error("Authentication failed. Please log in again.");
      }

      if (response.status === 404) {
        console.error("Subcategory not found (404).");
        throw new Error("Subcategory not found. It may have been already deleted.");
      }

      const errorText = await response.text();
      console.error("Error response body:", errorText);
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
    }
  } catch (error) {
    console.error("Error deleting subcategory:", error);
    throw error;
  }
}

// Job Soft Delete APIs

interface JobDeleteResponse {
  status: string;
  message: string;
}



// Admin deleted jobs response (newer shape returned by backend admin endpoint)
export interface DeletedJobsAdminResponse {
  status: string;
  message?: string;
  deleted_jobs: Array<any>;
  jobs?: Array<any>;
  total_count: number;
  limit?: number;
  offset?: number;
}

export async function softDeleteJob(jobId: string): Promise<JobDeleteResponse> {
  try {
    const token = localStorage.getItem("token");
    
  const response = await fetch(`${JOBS_API}/${jobId}`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error("Authentication failed. Please log in again.");
      }
      
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error deleting job:", error);
    throw error;
  }
}

export async function restoreJob(jobId: string): Promise<JobDeleteResponse> {
  try {
    const token = localStorage.getItem("token");
    
  const response = await fetch(`${JOBS_API}/${jobId}/restore`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error("Authentication failed. Please log in again.");
      }
      
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error restoring job:", error);
    throw error;
  }
}

export async function getDeletedJobs(): Promise<DeletedJobsAdminResponse> {
  try {
    const token = localStorage.getItem("token");
    
    const response = await fetch(ADMIN_DELETED_JOBS_API, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error("Authentication failed. Please log in again.");
      }
      
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    // Normalize different backend shapes to a consistent format used by the UI
    // Accepts: { deleted_jobs: [...] }, { jobs: [...] }, { items: [...] }, { data: { jobs: [...] } }, or an array of jobs
    let jobs: any[] = [];
    if (!data) {
      jobs = [];
    } else if (Array.isArray(data)) {
      jobs = data;
    } else if (Array.isArray((data as any).deleted_jobs)) {
      jobs = (data as any).deleted_jobs;
    } else if (Array.isArray((data as any).jobs)) {
      jobs = (data as any).jobs;
    } else if (Array.isArray((data as any).items)) {
      jobs = (data as any).items;
    } else if ((data as any).data && Array.isArray((data as any).data.deleted_jobs)) {
      jobs = (data as any).data.deleted_jobs;
    } else if ((data as any).data && Array.isArray((data as any).data.jobs)) {
      jobs = (data as any).data.jobs;
    } else if ((data as any).results && Array.isArray((data as any).results)) {
      jobs = (data as any).results;
    }

    // Debug log which key was used to normalize (only in dev)
    if (typeof window !== 'undefined' && (window as any).__DEV__) {
      try {
        const keys = Object.keys(data || {});
        // eslint-disable-next-line no-console
        console.debug('getDeletedJobs: using keys', keys, 'normalizedCount', jobs.length);
      } catch (e) {
        // ignore
      }
    }

    // Helpful for debugging unexpected shapes in development
    // Use a safe, browser-compatible check
    if (typeof window !== 'undefined' && window && (window as any).__DEV__) {
      // eslint-disable-next-line no-console
      console.debug('getDeletedJobs: normalized jobs length', jobs.length, 'originalShapeKeys', Object.keys(data || {}));
    }

    // Normalize to the application's DeletedJobsResponse shape
    const result: any = {
      status: 'ok',
      message: '',
      count: jobs.length,
      jobs,
      deleted_jobs: jobs,
      total_count: jobs.length,
    };

    return result as DeletedJobsAdminResponse;
  } catch (error) {
    console.error("Error getting deleted jobs:", error);
    throw error;
  }
}

export async function permanentDeleteJob(jobId: string): Promise<JobDeleteResponse> {
  try {
    const token = localStorage.getItem("token");
    
    const response = await fetch(`${ADMIN_PERMANENT_DELETE_API}/${jobId}/permanent`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error("Authentication failed. Please log in again.");
      }
      
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error permanently deleting job:", error);
    throw error;
  }
}

// Job Sharing APIs

interface JobShareRequest {
  target_user_email: string;
  permission_level: "view" | "edit" | "admin";
  message?: string;
}

interface JobShareResponse {
  status: string;
  message: string;
  shared_job_id: string;
  target_user_id: string;
  permission_level: string;
}

interface SharedJobsResponse {
  status: string;
  message: string;  shared_jobs: Array<any>;
  owned_jobs_shared_with_others: Array<any>;
}

export async function shareJob(jobId: string, shareRequest: JobShareRequest): Promise<JobShareResponse> {
  try {
    const token = localStorage.getItem("token");
    
  const response = await fetch(`${JOBS_API}/${jobId}/share`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(shareRequest),
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error("Authentication failed. Please log in again.");
      }
      
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error sharing job:", error);
    throw error;
  }
}

export async function unshareJob(jobId: string, targetUserEmail: string): Promise<{ status: string; message: string }> {
  try {
    const token = localStorage.getItem("token");
    
  const response = await fetch(`${JOBS_API}/${jobId}/share`, {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ target_user_email: targetUserEmail }),
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error("Authentication failed. Please log in again.");
      }
      
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error unsharing job:", error);
    throw error;
  }
}

export async function getSharedJobs(): Promise<SharedJobsResponse> {
  try {
    const token = localStorage.getItem("token");
    
    const response = await fetch(SHARED_JOBS_API, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error("Authentication failed. Please log in again.");
      }
      
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return await response.json();  } catch (error) {
    console.error("Error getting shared jobs:", error);
    throw error;
  }
}

export async function getJobSharingInfo(jobId: string): Promise<JobSharingInfo> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${JOBS_API}/${jobId}/sharing`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

// Analytics API Functions
export interface UserAnalytics {
  user_id: string;
  period_days: number;
  start_date: string;
  end_date: string;
  analytics: {
    transcription_stats: {
      total_minutes: number;
      total_jobs: number;
      average_job_duration: number;
    };
    activity_stats: {
      jobs_created: number;
      last_activity: string | null;
    };
    usage_patterns: {
      most_active_hours: number[];
      most_used_transcription_method: string | null;
      file_upload_count: number;
      text_input_count: number;
    };
  };
}

export interface AnalyticsRecord {
  id: string;
  type: string;
  user_id: string;
  job_id: string;
  event_type: string;
  timestamp: string;
  audio_duration_minutes: number;
  audio_duration_seconds: number;
  file_name: string;
  file_extension: string;
  prompt_category_id: string;
  prompt_subcategory_id: string;
  partition_key: string;
  _rid: string;
  _self: string;
  _etag: string;
  _attachments: string;
  _ts: number;
}

export interface SystemAnalytics {
  period_days: number;
  start_date: string;
  end_date: string;
  active_users?: number; // added for direct backend field
  peak_active_users?: number; // added for direct backend field
  analytics: {
    records: AnalyticsRecord[];
    total_minutes: number;
    total_jobs: number;
    active_users?: number; // surfaced root metric
    peak_active_users?: number; // surfaced root metric
    // Legacy compatibility - computed from records
    overview?: {
      total_users: number;
      active_users: number;
      total_jobs: number;
      total_transcription_minutes: number;
      peak_active_users: number;
    };
    trends?: {
      daily_activity: Record<string, number>;
      daily_transcription_minutes: Record<string, number>;
      daily_active_users: Record<string, number>;
      user_growth: Record<string, number>;
      job_completion_rate: number;
    };
    usage?: {
      transcription_methods: Record<string, number>;
      file_vs_text_ratio: { files: number; text: number };
      peak_hours: Record<string, number>;
    };
    // Optional fields for mock data indication
    _is_mock_data?: boolean;
    _mock_reason?: string;
  };
}

export interface SystemHealthMetrics {
  // Real metrics - actual data from system
  api_response_time_ms: number;           // Real: JSON serialization timing
  database_response_time_ms: number;     // Real: Cosmos DB query timing (-1 if unavailable)
  memory_usage_percentage: number;       // Real: psutil memory data (0 if unavailable)
  
  // Unused metrics - always 0, kept for API compatibility
  storage_response_time_ms: number;      // Always 0
  uptime_percentage: number;             // Always 0
  active_connections: number;            // Always 0
  disk_usage_percentage: number;         // Always 0
}

export interface SystemHealthResponse {
  status: string;
  timestamp: string;
  metrics: SystemHealthMetrics;
  services: Record<string, string>; // service_name: status
}

export interface UserDetails {
  id: string;
  email: string;
  full_name: string | null;
  permission: string;
  source: string;
  microsoft_oid: string | null;
  tenant_id: string | null;
  created_at: string;
  last_login: string | null;
  is_active: boolean;
  permission_changed_at: string;
  permission_changed_by: string;
  permission_history: Array<{
    old_permission: string;
    new_permission: string;
    changed_at: string;
    changed_by: string;
  }>;
  updated_at: string;
  analytics?: UserAnalytics["analytics"];
}

export async function getUserAnalytics(userId: string, days: number = 30): Promise<UserAnalytics> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${USER_ANALYTICS_API}/${userId}/analytics?days=${days}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

export async function getSystemAnalytics(period: number | 'total' = 30): Promise<SystemAnalytics> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const queryParam = period === 'total' ? '' : `?days=${period}`;
  const response = await fetch(`${SYSTEM_ANALYTICS_API}${queryParam}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const rawData = await response.json();
  // Transform the new API response to maintain compatibility with existing components
  return transformSystemAnalytics(rawData);
}

// Utility function to transform new API response into legacy format
export function transformSystemAnalytics(data: SystemAnalytics): SystemAnalytics {
  const records = data.analytics.records || [];
  
  // Extract unique user IDs from records
  const uniqueUsers = new Set(records.map(r => r.user_id));
  
  // Calculate daily activity
  const dailyActivity: Record<string, number> = {};
  const dailyMinutes: Record<string, number> = {};
  const dailyActiveUsers: Record<string, number> = {};
  
  // Initialize all dates in period
  const startDate = new Date(data.start_date);
  const endDate = new Date(data.end_date);
  for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
    const dateStr = d.toISOString().split('T')[0];
    dailyActivity[dateStr] = 0;
    dailyMinutes[dateStr] = 0;
    dailyActiveUsers[dateStr] = 0;
  }
  
  // Process records by date
  if (records.length > 0) {
    records.forEach(record => {
      const date = record.timestamp.split('T')[0];
      dailyActivity[date] = (dailyActivity[date] || 0) + 1;
      dailyMinutes[date] = (dailyMinutes[date] || 0) + record.audio_duration_minutes;
    });
  } else {
    // Fallback: if there are no individual records but totals exist, place the totals on the end_date
    const endDateStr = new Date(data.end_date).toISOString().split('T')[0];
    dailyActivity[endDateStr] = data.analytics.total_jobs || 0;
    dailyMinutes[endDateStr] = data.analytics.total_minutes || 0;
  }
  
  // Calculate active users per day
  const usersByDate: Record<string, Set<string>> = {};
  if (records.length > 0) {
    records.forEach(record => {
      const date = record.timestamp.split('T')[0];
      if (!usersByDate[date]) usersByDate[date] = new Set();
      usersByDate[date].add(record.user_id);
    });

    Object.entries(usersByDate).forEach(([date, users]) => {
      dailyActiveUsers[date] = users.size;
    });
  } else {
    // Fallback: set active users on the end date to the count of unique users from totals
    const endDateStr = new Date(data.end_date).toISOString().split('T')[0];
    dailyActiveUsers[endDateStr] = uniqueUsers.size || 0;
  }
  
  const backendActive = (data as any).active_users ?? (data.analytics as any).active_users;
  const backendPeak = (data as any).peak_active_users ?? (data.analytics as any).peak_active_users;
  const computedPeak = Math.max(...Object.values(dailyActiveUsers), 0);
  const activeUsersFinal = typeof backendActive === 'number' ? backendActive : (data.analytics as any).overview?.active_users || uniqueUsers.size;
  const peakActiveFinal = typeof backendPeak === 'number' ? backendPeak : computedPeak;

  return {
    ...data,
    active_users: activeUsersFinal,
    peak_active_users: peakActiveFinal,
    analytics: {
      ...data.analytics,
      active_users: activeUsersFinal,
      peak_active_users: peakActiveFinal,
      overview: {
        total_users: uniqueUsers.size,
        active_users: activeUsersFinal,
        total_jobs: data.analytics.total_jobs,
        total_transcription_minutes: data.analytics.total_minutes,
        peak_active_users: peakActiveFinal
      },
      trends: {
        daily_activity: dailyActivity,
        daily_transcription_minutes: dailyMinutes,
        daily_active_users: dailyActiveUsers,
        user_growth: {}, // Not available from current data
        job_completion_rate: 100 // Assume all uploaded jobs are completed
      },
      usage: {
        transcription_methods: { upload: data.analytics.total_jobs }, // All are uploads based on current data
        file_vs_text_ratio: { files: data.analytics.total_jobs, text: 0 },
        peak_hours: {} // Not available from current data
      }
    }
  };
}

export async function getSystemHealth(): Promise<SystemHealthResponse> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${SYSTEM_HEALTH_API}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

export async function getUserDetails(userId: string, includeAnalytics: boolean = true): Promise<UserDetails> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${USER_MANAGEMENT_API}/${userId}/details?include_analytics=${includeAnalytics}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

export async function getAnalyticsDashboard(days: number = 30): Promise<{
  system_analytics: SystemAnalytics;
  permission_stats: Record<string, number>;
  period_days: number;
  generated_at: string;
}> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${ANALYTICS_DASHBOARD_API}?days=${days}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

// Export Functions
export async function exportUsersCSV(filters?: {
  permission?: string;
  is_active?: boolean;
  date_range?: { start: string; end: string };
}): Promise<Blob> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const body = filters ? JSON.stringify({ filters }) : undefined;

  const response = await fetch(`${EXPORT_USERS_API}/csv`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body,
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.blob();
}

export async function exportUserDetailsPDF(userId: string, includeAnalytics: boolean = true, days: number = 30): Promise<Blob> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${EXPORT_USERS_API}/${userId}/pdf?include_analytics=${includeAnalytics}&days=${days}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.blob();
}

export type UserMinuteRecord = {
  job_id: string;
  timestamp: string;
  audio_duration_minutes: number;
  event_type?: string;
  file_name?: string;
  prompt_category_id?: string;
  prompt_subcategory_id?: string;
};

export type UserMinutesResponse = {
  user_id: string;
  period_days: number;
  start_date: string;
  end_date: string;
  total_minutes: number;
  total_records: number;
  records: UserMinuteRecord[];
};

export async function getUserMinutes(userId: string, days: number = 30): Promise<UserMinutesResponse> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const url = `${USER_ANALYTICS_API}/${userId}/minutes?days=${days}`;
  const response = await fetch(url, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Failed to fetch user minutes: ${response.status} ${text}`);
  }
  return response.json();
}

// Session Tracking API Functions
export interface SessionEventRequest {
  action: string;
  page?: string;
  timestamp?: string;
  session_duration?: number;
}

export interface ActiveUsersResponse {
  status: string;
  data: {
    active_users: string[];
    count: number;
    period_minutes: number;
    timestamp: string;
  };
}

export interface UserSessionDurationResponse {
  status: string;
  data: {
    user_id: string;
    total_session_duration_minutes: number;
    period_days: number;
    timestamp: string;
  };
}

export async function trackSessionEvent(sessionData: SessionEventRequest): Promise<{ status: string; session_event_id?: string; message: string }> {
  const token = localStorage.getItem("token");
  if (!token) {
    // Don't throw error for session tracking - fail silently
    return { status: "error", message: "No authentication token found" };
  }

  try {
    const response = await fetch(SESSION_TRACKING_API, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(sessionData),
    });

    const data = await response.json();
    return data;
  } catch (error) {
    // Session tracking should fail silently
    console.debug("Session tracking error:", error);
    return { status: "error", message: "Session tracking failed" };
  }
}

export async function getActiveUsers(minutes: number = 5): Promise<ActiveUsersResponse> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${ACTIVE_USERS_API}?minutes=${minutes}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

export async function getUserSessionDuration(userId: string, days: number = 1): Promise<UserSessionDurationResponse> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${USER_SESSION_DURATION_API}/${userId}?days=${days}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

// Logout API function
export async function logoutUser(): Promise<void> {
  await fetch(`${import.meta.env.VITE_API_URL}/logout`, { method: "POST", credentials: "include" });
}

// Microsoft Profile Image API function
export async function fetchMicrosoftProfileImage(accessToken: string): Promise<string | null> {
  // Check localStorage cache first
  const cached = localStorage.getItem("ms_profile_image");
  if (cached) return cached;
  const res = await fetch("https://graph.microsoft.com/v1.0/me/photo/$value", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) return null;
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  localStorage.setItem("ms_profile_image", url);
  return url;
}

// Microsoft SSO API function
export async function authenticateMicrosoftSSO(accessToken: string): Promise<any> {
  const apiUrl = import.meta.env.VITE_API_URL;
  const response = await fetch(`${apiUrl}/api/auth/microsoft-sso`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ access_token: accessToken }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

// User permissions API functions
export async function fetchUserPermissions(): Promise<any> {
  const API_BASE_URL = import.meta.env.VITE_API_URL;
  const token = localStorage.getItem("token");
  
  if (!token) {
    throw new Error("No authentication token found");
  }

  const response = await fetch(`${API_BASE_URL}/api/auth/users/me/permissions`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

export async function fetchPermissionStats(): Promise<any> {
  const API_BASE_URL = import.meta.env.VITE_API_URL;
  const token = localStorage.getItem("token");
  
  if (!token) {
    throw new Error("No authentication token found");
  }

  const response = await fetch(`${API_BASE_URL}/api/auth/users/permission-stats`, {
    method: "GET", 
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

export async function fetchUsersByPermission(permissionLevel: string, limit: number = 100): Promise<any> {
  const API_BASE_URL = import.meta.env.VITE_API_URL;
  const token = localStorage.getItem("token");
  
  if (!token) {
    throw new Error("No authentication token found");
  }

  const response = await fetch(`${API_BASE_URL}/api/auth/users/by-permission/${permissionLevel}?limit=${limit}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

export async function updateUserPermissionLevel(userId: string, newPermission: string): Promise<any> {
  const API_BASE_URL = import.meta.env.VITE_API_URL;
  const token = localStorage.getItem("token");
  
  if (!token) {
    throw new Error("No authentication token found");
  }

  const response = await fetch(`${API_BASE_URL}/api/auth/users/${userId}/permission`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ permission: newPermission }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

// Permissions API helpers
export async function getUserPermissions() {
  const token = localStorage.getItem('token');
  if (!token) throw new Error('No authentication token found');
  const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/users/me/permissions`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    // Try to surface backend error message if present
    let text = '';
    try { text = await response.text(); } catch (e) { /* ignore */ }
    throw new Error(`Failed to fetch user permissions: ${response.status} ${text}`);
  }

  const result = await response.json();
  // Accept both wrapped { status: 200, data: {...} } and direct user object
  if (result == null) throw new Error('Empty response from permissions endpoint');
  if (typeof result === 'object' && (result.status === 200 || result.status === '200') && result.data) return result.data;
  // If backend returned the user object directly, return it
  if (typeof result === 'object' && (result.user_id || result.userId || result.email)) return result;
  // Some backends return { status: 200, user_id, ... } without wrapping in data
  if (typeof result === 'object' && result.status === 200) {
    // If the backend uses the { status: 200, data: ... } wrapper, prefer data
    if ((result as any).data) return (result as any).data;
    // Remove status and return rest when it looks like a user object
    const { status, ...rest } = result as any;
    if (rest && (rest.user_id || rest.email)) return rest;
    // Newer backend responses include capability fields without user_id/email
    // e.g. { status:200, permission_level: ..., effective_capabilities: {...} }
    if (rest && (rest.effective_capabilities || rest.permission_level)) return rest;
  }

  throw new Error(result.message || 'Failed to fetch user permissions');
}

export async function getPermissionStats() {
  const token = localStorage.getItem('token');
  if (!token) throw new Error('No authentication token found');
  const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/users/permission-stats`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    let text = '';
    try { text = await response.text(); } catch (e) { /* ignore */ }
    throw new Error(`Failed to fetch permission statistics: ${response.status} ${text}`);
  }

  const result = await response.json();
  if (result == null) throw new Error('Empty response from permission-stats endpoint');
  if (typeof result === 'object' && (result.status === 200 || result.status === '200') && result.data) return result.data;
  if (typeof result === 'object' && (result.total_users || result.by_permission)) return result;
  throw new Error(result.message || 'Failed to fetch permission statistics');
}

export async function getUsersByPermission(permissionLevel: string, limit: number = 100) {
  const token = localStorage.getItem('token');
  if (!token) throw new Error('No authentication token found');
  const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/users/by-permission/${permissionLevel}?limit=${limit}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    let text = '';
    try { text = await response.text(); } catch (e) { /* ignore */ }
    throw new Error(`Failed to fetch users by permission: ${response.status} ${text}`);
  }

  const result = await response.json();
  if (result == null) throw new Error('Empty response from by-permission endpoint');
  if (typeof result === 'object' && (result.status === 200 || result.status === '200') && result.data) return result.data;
  if (Array.isArray(result)) return result;
  if (typeof result === 'object' && result.users) return result.users;
  throw new Error(result.message || 'Failed to fetch users by permission');
}

export async function updateUserPermissionApi(userId: string, newPermission: string) {
  const token = localStorage.getItem('token');
  if (!token) throw new Error('No authentication token found');
  const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/users/${userId}/permission`, {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ permission: newPermission }),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || result.message || 'Failed to update user permission');
  if (result.status === 200) return result.data;
  throw new Error(result.message || 'Failed to update user permission');
}

// New function to fetch audio blobs from URLs
export async function fetchAudioBlob(audioURL: string): Promise<Blob> {
  const response = await fetch(audioURL);
  return await response.blob();
}

// Microsoft SSO Login function
export async function microsoftSsoLogin(mappedResponse: any): Promise<any> {
  const apiUrl = import.meta.env.VITE_API_URL || "";
  const backendResponse = await fetch(`${apiUrl}/api/auth/microsoft-sso`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(mappedResponse),
  });
  if (!backendResponse.ok) {
    const errorData = await backendResponse.json();
    throw new Error(errorData.message || "Login failed");
  }
  const result = await backendResponse.json();
  // Ensure base permission is 'User' if not set by backend
  if (!result.permission) {
    result.permission = PermissionLevel.USER;
  }
  return result;
}

// New function to fetch audio recordings
export async function fetchAudioRecordingsApi(token: string) {
  const response = await fetch(JOBS_API, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return await response.json();
}

// New function to fetch job data with filters
export async function fetchJobDataApi(token: string, filters?: { job_id?: string; status?: string; created_at?: string }) {
  const params = new URLSearchParams({
    job_id: filters?.job_id || "",
    status: filters?.status && filters.status !== "all" ? filters.status : "",
    created_at: filters?.created_at || "",
  });
  const response = await fetch(`${JOBS_API}?${params.toString()}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });
  const data = await response.json();
  return data.jobs || [];
}

// New function to fetch transcription text from a URL
export async function fetchTranscriptionText(url: string): Promise<string> {
  const response = await fetch(url);
  return await response.text();
}

// New function to fetch a single recording by ID
export async function fetchRecordingByIdApi(token: string, recordingId: string) {
  const response = await fetch(`${JOBS_API}/${recordingId}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });
  if (!response.ok) throw new Error("Failed to fetch recording by ID");
  const data = await response.json();
  return data.job || data;
}

// New function to fetch all jobs (admin endpoint)
export async function fetchAllJobsApi(token: string) {
  const response = await fetch(`${ADMIN_JOBS_API}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return await response.json();
}

// Capability management functions
export async function updateUserCapabilities(userId: string, capabilityData: {
  permission?: PermissionLevel;
  custom_capabilities?: UserCapabilities;
}): Promise<User> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${USER_MANAGEMENT_API}/${userId}/capabilities`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(capabilityData),
  });

  const data = await response.json();
  
  if (!response.ok) {
    throw new Error(data.message || "Failed to update user capabilities");
  }

  return data.data;
}

export async function getUserCapabilities(userId: string): Promise<{
  effective_capabilities: UserCapabilities;
  base_capabilities: UserCapabilities;
  custom_capabilities: UserCapabilities;
}> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${USER_MANAGEMENT_API}/${userId}/capabilities`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await response.json();
  
  if (!response.ok) {
    throw new Error(data.message || "Failed to get user capabilities");
  }

  return data.data;
}

export async function getCapabilityDefinitions(): Promise<{
  capabilities: Record<string, {
    name: string;
    description: string;
    category: string;
  }>;
  permission_levels: Record<string, string[]>;
}> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${USER_MANAGEMENT_API}/capabilities/definitions`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const data = await response.json();
  
  if (!response.ok) {
    throw new Error(data.message || "Failed to get capability definitions");
  }

  return data.data;
}

// Analytics Event Tracking
export interface AnalyticsEventRequest {
  event_type: string;
  metadata?: Record<string, any>;
  job_id?: string;
}

export async function trackAnalyticsEvent(eventData: AnalyticsEventRequest): Promise<{ status: string; event_id?: string; message: string }> {
  const token = localStorage.getItem("token");
  if (!token) {
    console.warn("No authentication token found for analytics tracking");
    return { status: "error", message: "No authentication token" };
  }

  try {
    const response = await fetch(`${ANALYTICS_API}/event`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(eventData),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    // Analytics tracking should fail silently
    console.debug("Analytics tracking error:", error);
    return { status: "error", message: "Analytics tracking failed" };
  }
}

// Analysis Document Update Types
interface AnalysisDocumentUpdateRequest {
  html_content: string;
  format?: string; // "docx" or "html"
}

interface AnalysisDocumentUpdateResponse {
  status: string;
  message: string;
  document_url: string;
  updated_at: string;
}

/**
 * Update an analysis document for a job
 */
export async function updateAnalysisDocument(
  jobId: string, 
  textContent: string
): Promise<AnalysisDocumentUpdateResponse> {
  const token = localStorage.getItem("token");
  
  if (!token) {
    throw new Error("Authentication token not found");
  }

  // Convert plain text to basic HTML for the backend
  const htmlContent = textContent
    .split('\n\n')
    .map(section => {
      const lines = section.split('\n');
      if (lines.length === 0) return '';
      
      const firstLine = lines[0].trim();
      const isHeading = firstLine.endsWith(':') || 
                       firstLine.length < 100 || 
                       /^[A-Z][A-Z\s]*:?$/.test(firstLine);
      
      if (isHeading) {
        const heading = `<h3>${firstLine.replace(':', '')}</h3>`;
        const content = lines.slice(1)
          .filter(line => line.trim())
          .map(line => {
            if (line.startsWith('•') || line.startsWith('-') || /^\d+\./.test(line)) {
              return `<li>${line.replace(/^[•\-\d+\.]\s*/, '')}</li>`;
            }
            return `<p>${line}</p>`;
          });
        
        const hasListItems = content.some(c => c.startsWith('<li>'));
        if (hasListItems) {
          const listItems = content.filter(c => c.startsWith('<li>')).join('');
          const paragraphs = content.filter(c => c.startsWith('<p>')).join('');
          return `${heading}${paragraphs ? paragraphs : ''}<ul>${listItems}</ul>`;
        }
        return `${heading}${content.join('')}`;
      } else {
        return lines
          .filter(line => line.trim())
          .map(line => {
            if (line.startsWith('•') || line.startsWith('-') || /^\d+\./.test(line)) {
              return `<li>${line.replace(/^[•\-\d+\.]\s*/, '')}</li>`;
            }
            return `<p>${line}</p>`;
          })
          .join('');
      }
    })
    .filter(section => section.trim())
    .join('');

  const requestBody: AnalysisDocumentUpdateRequest = {
    html_content: htmlContent,
    format: "docx"
  };

  try {
    const response = await fetch(`${JOBS_API}/${jobId}/analysis-document`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `HTTP ${response.status}: Failed to update analysis document`);
    }

    const result: AnalysisDocumentUpdateResponse = await response.json();
    return result;
  } catch (error) {
    console.error("Error updating analysis document:", error);
    throw error;
  }
}

// User Audit Logs API Functions
export interface UserAuditLogRecord {
  id: string;
  timestamp: string | null;
  event_type: string;
  resource_type?: string;
  resource_id?: string;
  metadata?: Record<string, any>;
}

export interface UserAuditLogsResponse {
  user_id: string;
  period_days: number;
  start_date: string;
  end_date: string;
  records: UserAuditLogRecord[];
}

export async function getUserAuditLogs(userId: string, days: number = 30): Promise<UserAuditLogsResponse> {
  const token = localStorage.getItem("token");
  const url = `${USER_ANALYTICS_API}/${userId}/detailed-sessions?days=${days}&include_audit=true`;
  const response = await fetch(url, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: token ? `Bearer ${token}` : "",
    },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch user audit logs (${response.status})`);
  }
  return response.json();
}

// Update job displayname
export async function updateJobDisplayName(jobId: string, displayname: string) {
  const token = localStorage.getItem("token");
  if (!token) {
    throw new Error("No authentication token found");
  }

  const response = await fetch(`${JOBS_API}/${jobId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ displayname }),
  });

  if (!response.ok) {
    throw new Error("Failed to update job name");
  }

  return response.json();
}

