export interface PromptKeyValue {
  key: string;
  value: string;
}

export function promptsArrayToObject(
  promptsArray: Array<PromptKeyValue>,
): Record<string, string> {
  return Object.fromEntries(
    promptsArray
      .filter((p) => p.key.trim())
      .map((p) => [p.key.trim(), p.value]),
  );
}

export function objectToPromptsArray(
  promptsObject: Record<string, string> | undefined | null,
): Array<PromptKeyValue> {
  const promptsArray = Object.entries(promptsObject || {}).map(
    ([key, value]) => ({
      key,
      value,
    }),
  );
  if (promptsArray.length === 0) {
    promptsArray.push({ key: "", value: "" });
  }
  return promptsArray;
}
