import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "@tanstack/react-router";
import { useForm } from "react-hook-form";

import "@radix-ui/themes/styles.css";

import type { LoginValues, RegisterValues } from "@/schema/auth.schema";
import { loginUser, registerUser } from "@/api/auth";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { setStorageItem } from "@/lib/storage";
import { loginSchema, registerSchema } from "@/schema/auth.schema";
import { useMutation } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

export function AuthForm() {
  const [activeTab, setActiveTab] = useState<"login" | "register">("login");
  const router = useRouter();

  const loginForm = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const registerForm = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      email: "",
      password: "",
      confirmPassword: "",
    },
  });

  const { mutateAsync: loginMutation, isPending: isLoginPending } = useMutation(
    {
      mutationKey: ["user/login"],
      mutationFn: async (values: LoginValues) =>
        await loginUser(values.email, values.password),
      onSuccess: (data) => {
        toast.success(data.message);
        setStorageItem("token", data.access_token);
        router.navigate({ to: "/audio-upload" });
      },
      onError: (error) => {
        toast.error(error instanceof Error ? error.message : "Login failed");
      },
    },
  );

  async function onLoginSubmit(values: LoginValues) {
    await loginMutation(values);
  }

  const { mutateAsync: registerMutation, isPending: isRegisterPending } =
    useMutation({
      mutationKey: ["user/register"],
      mutationFn: async (values: RegisterValues) =>
        await registerUser(values.email, values.password),
      onSuccess: (data) => {
        toast.success(data.message);
        setActiveTab("login");
      },
      onError: (error) => {
        toast.error(
          error instanceof Error ? error.message : "Registration failed",
        );
      },
    });

  async function onRegisterSubmit(values: RegisterValues) {
    await registerMutation(values);
  }

  return (
    <div className="space-y-6">
      <Tabs
        className="w-full"
        onValueChange={(value) => setActiveTab(value as "login" | "register")}
        value={activeTab}
      >
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="login">Login</TabsTrigger>
          <TabsTrigger value="register">Register</TabsTrigger>
        </TabsList>
        <TabsContent value="login">
          <Form {...loginForm}>
            <form
              onSubmit={loginForm.handleSubmit(onLoginSubmit)}
              className="space-y-4"
            >
              <FormField
                control={loginForm.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input placeholder="Enter your email" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={loginForm.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Password</FormLabel>
                    <FormControl>
                      <Input
                        type="password"
                        placeholder="Enter your password"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button
                type="submit"
                className="w-full"
                disabled={isLoginPending || isRegisterPending}
              >
                {isLoginPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Logging in...
                  </>
                ) : (
                  "Login"
                )}
              </Button>
            </form>
          </Form>
        </TabsContent>
        <TabsContent value="register">
          <Form {...registerForm}>
            <form
              onSubmit={registerForm.handleSubmit(onRegisterSubmit)}
              className="space-y-4"
            >
              <FormField
                control={registerForm.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input placeholder="Enter your email" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={registerForm.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Password</FormLabel>
                    <FormControl>
                      <Input
                        type="password"
                        placeholder="Create a password"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={registerForm.control}
                name="confirmPassword"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Confirm Password</FormLabel>
                    <FormControl>
                      <Input
                        type="password"
                        placeholder="Confirm your password"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button
                type="submit"
                className="w-full"
                disabled={isRegisterPending}
              >
                {isRegisterPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Registering...
                  </>
                ) : (
                  "Register"
                )}
              </Button>
            </form>
          </Form>
        </TabsContent>
      </Tabs>
    </div>
  );
}
