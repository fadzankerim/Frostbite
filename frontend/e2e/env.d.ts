// Bez @types/node: E2E kod koristi samo process.env.
declare const process: { env: Record<string, string | undefined> };
