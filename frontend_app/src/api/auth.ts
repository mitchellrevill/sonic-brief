import { httpClient } from "@/api/httpClient";
import { LOGIN_API, REGISTER_API } from "@/lib/apiConstants";

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
  const response = await httpClient.post(REGISTER_API, {
    email,
    password,
  });

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
