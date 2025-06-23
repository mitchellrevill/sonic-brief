// msalConfig.ts
export const msalConfig = {
  auth: {
    clientId: "dce929ee-8fe7-4936-af18-68c755913d75",
    authority: "https://login.microsoftonline.com/ba6a2471-3340-4314-a969-48d8cdc4c4f8", 
    redirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: "localStorage",
    storeAuthStateInCookie: false,
  },
};

export const loginRequest = {
  scopes: ["openid", "profile", "email"],
};
