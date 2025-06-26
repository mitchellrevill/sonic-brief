import { httpClient } from "@/api/httpClient";
import { LOGIN_API, REGISTER_API } from "@/lib/apiConstants";
import { getStorageItem } from "@/lib/storage";

interface RegisterResponse {
  status: number;
  message: string;
}

interface LoginResponse {
  status: number;
  message: string;
  access_token: string;
  token_type: string;
}

export async function registerUser(
  email: string,
  password: string,
): Promise<RegisterResponse> {
  // Check for admin token before making the request
  const token = getStorageItem("token", "");
  if (!token) {
    throw new Error("You must be logged in as an admin to register a new user. Please log in and try again.");
  }

  const response = await httpClient.post(
    REGISTER_API,
    {
      email,
      password,
    },
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  return response.data;
}

export async function loginUser(
  email: string,
  password: string,
): Promise<LoginResponse> {
  const response = await httpClient.post(LOGIN_API, {
    email,
    password,
  });

  return response.data;
}
