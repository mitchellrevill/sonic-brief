import {
  ADMIN_DELETED_JOBS_API,
  ADMIN_PERMANENT_DELETE_API,
  CATEGORIES_API,
  JOB_DELETE_API,
  JOB_SHARE_API,
  LOGIN_API,
  PROMPTS_API,
  REGISTER_API,
  SHARED_JOBS_API,
  SUBCATEGORIES_API,
  UPLOAD_API,
  USER_MANAGEMENT_API,
  USER_ANALYTICS_API,
  SYSTEM_ANALYTICS_API,
  ANALYTICS_DASHBOARD_API,
  EXPORT_USERS_API,
  SESSION_TRACKING_API,
  ACTIVE_USERS_API,
  USER_SESSION_DURATION_API,
  JOBS_API
} from "../lib/apiConstants"

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
    body: JSON.stringify({ email, password }),
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

  return data
}

export type User = {
  id: string;
  name: string;
  email: string;
  permission: "Editor" | "Admin" | "User";
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

  return await response.json();
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
  const response = await fetch(UPLOAD_API, {
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

export async function updateUserPermission(userId: string, permission: "User" | "Admin" | "Editor"): Promise<User> {
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

interface DeletedJobsResponse {
  status: string;
  message: string;
  count: number;
  jobs: Array<any>;
}

export async function softDeleteJob(jobId: string): Promise<JobDeleteResponse> {
  try {
    const token = localStorage.getItem("token");
    
    const response = await fetch(`${JOB_DELETE_API}/${jobId}`, {
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
    
    const response = await fetch(`${JOB_DELETE_API}/${jobId}/restore`, {
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

export async function getDeletedJobs(): Promise<DeletedJobsResponse> {
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

    return await response.json();
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
    
    const response = await fetch(`${JOB_SHARE_API}/${jobId}/share`, {
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
    
    const response = await fetch(`${JOB_SHARE_API}/${jobId}/share`, {
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

  const response = await fetch(`${JOB_SHARE_API}/${jobId}/sharing-info`, {
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
      login_count: number;
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

export interface SystemAnalytics {
  period_days: number;
  start_date: string;
  end_date: string;
  analytics: {
    overview: {
      total_users: number;
      active_users: number;
      total_jobs: number;
      total_transcription_minutes: number;
    };
    trends: {
      daily_activity: Record<string, number>;
      daily_active_users: Record<string, number>;
      user_growth: Record<string, number>;
      job_completion_rate: number;
    };
    usage: {
      transcription_methods: Record<string, number>;
      file_vs_text_ratio: { files: number; text: number };
      peak_hours: Record<string, number>;
    };
  };
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

  const response = await fetch(`${USER_ANALYTICS_API}/${userId}?days=${days}`, {
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

export async function getSystemAnalytics(days: number = 30): Promise<SystemAnalytics> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${SYSTEM_ANALYTICS_API}?days=${days}`, {
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

export async function exportUserDetailsPDF(userId: string, includeAnalytics: boolean = true): Promise<Blob> {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No authentication token found. Please log in again.");

  const response = await fetch(`${EXPORT_USERS_API}/${userId}/pdf?include_analytics=${includeAnalytics}`, {
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
  if (!response.ok) throw new Error('Failed to fetch user permissions');
  const result = await response.json();
  if (result.status === 200 && result.data) return result.data;
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
  if (!response.ok) throw new Error('Failed to fetch permission statistics');
  const result = await response.json();
  if (result.status === 200 && result.data) return result.data;
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
  if (!response.ok) throw new Error('Failed to fetch users by permission');
  const result = await response.json();
  if (result.status === 200 && result.data) return result.data;
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
  return await backendResponse.json();
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
  const response = await fetch(`${import.meta.env.VITE_API_URL}/api/jobs`, {
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

